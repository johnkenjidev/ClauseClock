"""
Stage 2 analysis pipeline — renewal_notice extraction.

Flow (per contract, over its readable documents only):
  1. chunk raw_text (~3000 chars, ~200 overlap), each chunk bound server-side
     to document_id + char range + location. Chunks are transient.
  2. locate (AI)  -> candidate chunk_ids
  3. extract (AI) -> strict renewal_notice JSON with verbatim source quotes
  4. validate sources server-side (resolve document_id from chunk_id, verify
     quote against that document's raw_text, store char_offset + location)
  5. deterministic date computation in Python (never the model)
  6. normalized layer + annual-value provenance

Conservative by construction: ambiguity lowers confidence or sets
needs_review; it never manufactures contract terms.
"""

import re
from datetime import date, datetime, timedelta

import numpy as np
from bson import ObjectId
from dateutil.relativedelta import relativedelta

import llm

CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200
REQUIRED_PURPOSES = {"renewal_term", "notice_period"}
RENEWAL_HINT = re.compile(
    r"automatic(ally)?\s+renew|renew(s|al)?\s+(for|term|automatically)|"
    r"non[- ]renewal|not\s+to\s+renew|renewal\s+term|successive\s+.{0,12}\s*terms",
    re.I)
PDF_PAGE_RE = re.compile(r"=+\s*Page\s+(\d+)\s*=+")
DOCX_SEC_RE = re.compile(r"\[§\s*(.+?)\]")


def normalize_unit(value, unit):
    if value is None or unit is None:
        return None
    unit = unit.lower().rstrip("s")
    return {"day": relativedelta(days=value),
            "month": relativedelta(months=value),
            "year": relativedelta(years=value)}.get(unit)


# ---------------------------------------------------------------------------
# Notice-deadline ANCHOR (safety-critical). READ THIS beside the calculator.
#
# The term end / completion of the current term and the renewal start / start of
# the next term are DISTINCT dates, usually one day apart. Anchoring the notice
# window to the wrong one fails UNSAFE (hands the user an extra day). Therefore:
#
#   * There is intentionally NO default notice anchor. The deterministic
#     calculator consumes a CLASSIFIED anchor value ONLY; it never re-reads the
#     clause to infer the anchor. An unknown/unsupported anchor MUST refuse the
#     calculation rather than guess. Do NOT add catch-all logic (default to
#     renewal date, default to term end, pick the closest date, or silently
#     convert null/unknown into a supported anchor).
#   * Future unsupported anchors (anniversary-based, fixed calendar date, ...)
#     remain "unknown" until explicitly modeled.
#
# Anchor is three-valued and MUST NOT collapse:
#   - Finding.anchor_version is None  -> LEGACY / never-classified (do not treat
#     as "unknown"; do not recompute or erase its stored deadline here).
#   - notice_anchor_type == "unknown" -> classification ran, not confident.
#   - notice_anchor_type in NOTICE_ANCHORS -> confidently classified.
NOTICE_ANCHORS = ("term_end", "renewal_start")
ANCHOR_VERSION = 1

# Vocabulary profiles: CONFIGURATION data (not calculator branching). Phrase
# families that explicitly anchor the notice window. Used to (a) inform the
# extraction prompt and (b) deterministically corroborate the model's
# classification from the validated anchor quote. Not an exhaustive literal
# list — the extraction model still classifies semantically.
NOTICE_ANCHOR_PROFILES = {
    "term_end": [
        r"completion of the .{0,40}\bterm\b", r"conclusion of the .{0,40}\bterm\b",
        r"end of the (then[- ]?current |current )?term",
        r"expir(y|ation) of the .{0,40}\bterm\b", r"prior to (the )?expir",
        r"\bterm\b\s+(ends?|expires?)",
    ],
    "renewal_start": [
        r"start date of the renewal term", r"commencement of the renewal term",
        r"beginning of the (next|renewal) term", r"renewal term (start|commencement)",
        r"start of the (next|renewal) term",
    ],
}
_ANCHOR_PROFILE_RE = {k: [re.compile(p, re.I) for p in pats]
                      for k, pats in NOTICE_ANCHOR_PROFILES.items()}


def _profile_classify_anchor(quote: str) -> str:
    """Deterministic classification from the validated anchor QUOTE via the
    vocabulary profiles. Returns 'term_end' | 'renewal_start' | 'unknown'.
    Ambiguous (matches both) or no-match => 'unknown'. Never defaults."""
    q = _norm(_strip_markers(quote or ""))
    matched = [k for k, regs in _ANCHOR_PROFILE_RE.items()
               if any(r.search(q) for r in regs)]
    return matched[0] if len(matched) == 1 else "unknown"


def resolve_notice_anchor(model_value, anchor_quote: str, quote_validated: bool) -> str:
    """Classification step (NOT the calculator). Prefer the deterministic
    profile match on the validated quote; otherwise accept the model's semantic
    classification ONLY if it is a supported anchor corroborated by a validated
    verbatim quote. Anything else is 'unknown'. There is no default."""
    if quote_validated:
        prof = _profile_classify_anchor(anchor_quote)
        if prof in NOTICE_ANCHORS:
            return prof
        if model_value in NOTICE_ANCHORS:
            return model_value
    return "unknown"


def _location_at(raw_text: str, offset: int, file_type: str) -> str:
    head = raw_text[:offset]
    if file_type == "pdf":
        matches = list(PDF_PAGE_RE.finditer(head))
        if matches:
            return f"p.{matches[-1].group(1)}"
        return "p.1"
    matches = list(DOCX_SEC_RE.finditer(head))
    if matches:
        return f"§{matches[-1].group(1).strip()}"
    return "(preamble)"


def build_chunks(documents: list[dict]) -> tuple[list[dict], dict]:
    """Return (chunks, chunk_map). Only readable documents are chunked."""
    chunks, chunk_map = [], {}
    counter = 0
    for doc in documents:
        if doc.get("extraction_method") == "failed_no_text":
            continue
        raw = doc.get("raw_text") or ""
        if not raw.strip():
            continue
        doc_id = doc["id"] if "id" in doc else str(doc["_id"])
        file_type = doc.get("file_type", "pdf")
        start = 0
        n = len(raw)
        while start < n:
            end = min(start + CHUNK_SIZE, n)
            counter += 1
            cid = f"c_{counter:02d}"
            text = raw[start:end]
            chunks.append({
                "chunk_id": cid, "document_id": doc_id,
                "char_start": start, "char_end": end,
                "location": _location_at(raw, start, file_type), "text": text,
            })
            chunk_map[cid] = {"document_id": doc_id, "char_start": start,
                              "char_end": end}
            if end == n:
                break
            start = end - CHUNK_OVERLAP
    return chunks, chunk_map


def find_quote_offset(raw_text: str, quote: str):
    """Verbatim match after whitespace normalization. Returns offset or None."""
    q = (quote or "").strip()
    tokens = q.split()
    if not tokens:
        return None
    pattern = r"\s+".join(re.escape(tok) for tok in tokens)
    m = re.search(pattern, raw_text)
    return m.start() if m else None


# ClauseClock's own inserted location markers. These are NOT contract text; a
# verbatim clause can be split by one (e.g. a page break falling mid-sentence).
# We remove ONLY these — consistently on both the document and the quote — for
# validation. This is not fuzzy/semantic matching: the words must still match
# exactly and in order.
_MARKER_RE = re.compile(
    r"=+\s*Page\s+\d+\s*=+"        # PDF page markers
    r"|\[Table[^\]]*\]"            # table markers
    r"|\[§[^\]]*\]"                # DOCX section/heading markers
    r"|\[loc:[^\]]*\]"             # DOCX location annotations
    r"|¶\d+\s*\|"                  # DOCX paragraph prefixes
)


def _strip_markers(text: str) -> str:
    return _MARKER_RE.sub(" ", text or "")


# Typographic normalization. PDF text extraction yields Unicode curly quotes,
# apostrophes and dashes where the model echoes plain ASCII (or vice versa).
# These are the SAME characters typographically — normalizing them is NOT fuzzy
# matching (words must still match exactly and in order). All mappings are 1:1
# so character offsets are preserved.
_TYPO_TABLE = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",   # single quotes
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',   # double quotes
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",   # hyphens/dashes
    "\u2014": "-", "\u2015": "-", "\u2212": "-",
    "\u00a0": " ", "\u2007": " ", "\u2009": " ", "\u202f": " ",   # nbsp/thin spaces
    "\u2060": " ", "\ufeff": " ",                                  # word joiner/bom
})


def _norm(text: str) -> str:
    return (text or "").translate(_TYPO_TABLE)


def _clean_with_map(raw: str):
    """Return (cleaned_raw, offset_map) where offset_map[i] is the original
    index in `raw` of cleaned_raw[i]. Injected markers become a single space."""
    cleaned, omap = [], []
    i, n = 0, len(raw)
    for m in _MARKER_RE.finditer(raw):
        for j in range(i, m.start()):
            cleaned.append(raw[j]); omap.append(j)
        cleaned.append(" "); omap.append(m.start())
        i = m.end()
    for j in range(i, n):
        cleaned.append(raw[j]); omap.append(j)
    return "".join(cleaned), omap


def find_quote_offset_marker_tolerant(raw_text: str, quote: str):
    """Like find_quote_offset but ignores ClauseClock's injected markers and
    normalizes typographic variants (curly quotes/dashes). Returns the offset
    in the ORIGINAL raw_text, or None. Not fuzzy: words must match exactly."""
    q = _norm(_strip_markers(quote)).strip()
    tokens = q.split()
    if not tokens:
        return None
    # 1:1 typographic normalization preserves offsets vs the original raw_text.
    cleaned, omap = _clean_with_map(_norm(raw_text))
    pattern = r"\s+".join(re.escape(tok) for tok in tokens)
    m = re.search(pattern, cleaned)
    if not m:
        return None
    return omap[m.start()]


def _display_quote(quote: str) -> str:
    """Quote for storage/display with injected markers removed (still verbatim
    contract wording, just without our page/section artifacts)."""
    return re.sub(r"\s+", " ", _norm(_strip_markers(quote))).strip()[:400]


def validate_sources(sources: list[dict], chunk_map: dict,
                     docs_by_id: dict) -> tuple[list[dict], set]:
    """Resolve + verify each source. Returns (validated_sources, valid_purposes)."""
    validated, valid_purposes = [], set()
    for src in sources or []:
        cid = src.get("chunk_id")
        purpose = src.get("purpose")
        quote = (src.get("quote") or "")[:400]
        binding = chunk_map.get(cid)
        if not binding or not purpose or not quote:
            continue
        doc_id = binding["document_id"]           # server-resolved, never model
        doc = docs_by_id.get(doc_id)
        if not doc:
            continue
        raw = doc.get("raw_text") or ""
        offset = find_quote_offset_marker_tolerant(raw, quote)
        if offset is None:
            continue                              # failed validation -> dropped
        validated.append({
            "purpose": purpose, "chunk_id": cid, "document_id": doc_id,
            "quote": _display_quote(quote),
            "location": _location_at(raw, offset, doc.get("file_type", "pdf")),
            "char_offset": offset,
        })
        valid_purposes.add(purpose)
    return validated, valid_purposes


def _parse_deemed_days(rule: str):
    if not rule:
        return None, False
    m = re.search(r"(\d+)\s*(business\s+)?day", rule.lower())
    if not m:
        return None, False
    return int(m.group(1)), bool(m.group(2))


def _sub_days(d: date, days: int, business: bool) -> date:
    if business:
        return np.busday_offset(d, -days, roll="backward").astype("datetime64[D]").astype(date)
    return d - timedelta(days=days)


def compute_dates(extracted: dict, today: date) -> dict:
    """Deterministic date arithmetic. Returns computed fields + review flags.

    The calculator consumes the CLASSIFIED notice_anchor_type ONLY (see the
    ANCHOR safety note above). It never inspects clause prose. An unknown or
    unsupported anchor refuses the deadline calculation (fail-safe)."""
    out = {"next_renewal_date": None, "current_term_end": None,
           "action_deadline": None, "earliest_action_date": None,
           "effective_action_deadline": None, "days_remaining": None}
    notes, needs_review = [], False

    eff = extracted.get("effective_date")
    if not eff:
        notes.append("Confirm the effective date to calculate this deadline.")
        return out, ["effective_date_missing"], True

    try:
        eff_date = datetime.strptime(eff, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return out, ["effective_date_unparseable"], True

    init = normalize_unit(extracted.get("initial_term_value"),
                          extracted.get("initial_term_unit"))
    period = normalize_unit(extracted.get("renewal_period_value"),
                            extracted.get("renewal_period_unit"))
    if init is None:
        notes.append("Initial term not stated; cannot project the renewal date.")
        return out, notes + ["initial_term_missing"], True

    renewal = eff_date + init
    if period is not None:
        while renewal <= today:
            renewal = renewal + period
    out["next_renewal_date"] = renewal.isoformat()
    # The current term completes the day before the next term begins.
    current_term_end = renewal - timedelta(days=1)
    out["current_term_end"] = current_term_end.isoformat()

    nmin = extracted.get("notice_days_min")
    nmax = extracted.get("notice_days_max")
    if nmin is None:
        notes.append("Notice period not stated; deadline cannot be calculated.")
        return out, notes + ["notice_days_min_missing"], True

    # Resolve the classified anchor. No default: refuse rather than guess.
    anchor_type = extracted.get("notice_anchor_type")
    if anchor_type == "renewal_start":
        anchor_date = renewal
    elif anchor_type == "term_end":
        anchor_date = current_term_end
    else:
        notes.append("This contract's notice window is not clearly anchored to "
                     "the term end or the renewal start, so ClauseClock will not "
                     "calculate this deadline. Confirm which date the notice "
                     "counts back from.")
        return out, notes + ["notice_anchor_unknown"], True

    basis = extracted.get("notice_basis")
    business = basis == "business"
    if business and not extracted.get("business_day_definition"):
        needs_review = True
        notes.append("This contract counts in business days but does not define "
                     "which days count. Confirm this deadline.")

    action_deadline = _sub_days(anchor_date, nmin, business)
    out["action_deadline"] = action_deadline.isoformat()
    if nmax is not None:
        out["earliest_action_date"] = _sub_days(anchor_date, nmax, business).isoformat()

    # deemed receipt: apply only when explicitly stated and measured to receipt
    measured = extracted.get("notice_measured_to")
    effective_deadline = action_deadline
    if measured == "received":
        buf_days, buf_business = _parse_deemed_days(extracted.get("deemed_receipt_rule"))
        if buf_days is not None:
            effective_deadline = _sub_days(action_deadline, buf_days, buf_business)
        else:
            notes.append("Notice is measured to receipt with no deemed-receipt "
                         "rule; set your own send-by date before this deadline.")
    out["effective_action_deadline"] = effective_deadline.isoformat()
    out["days_remaining"] = (effective_deadline - today).days
    return out, notes, needs_review


# Fields a user may edit via Correct. Computed/derived fields are excluded.
EDITABLE_FIELDS = [
    "effective_date", "initial_term_value", "initial_term_unit", "renewal_type",
    "renewal_period_value", "renewal_period_unit", "notice_days_min",
    "notice_days_max", "notice_basis", "business_day_definition",
    "notice_measured_to", "deemed_receipt_rule", "notice_method",
    "notice_recipient", "notice_anchor_type",
]


def recompute_derived(edits: dict, today: date = None) -> dict:
    """Recompute server-derived dates + normalized fields from edited values
    using the SAME deterministic Stage 2 logic (no LLM). Used by Correct."""
    today = today or date.today()
    computed, notes, review = compute_dates(edits, today)
    validation_status = "needs_review" if review else "validated"
    fields = {k: edits.get(k) for k in EDITABLE_FIELDS}
    fields.update(computed)
    if validation_status == "needs_review":
        for k in ("action_deadline", "earliest_action_date",
                  "effective_action_deadline", "days_remaining"):
            fields[k] = None
    return {
        "extracted": fields,
        "validation_status": validation_status,
        "validation_notes": notes,
        "action_required": edits.get("renewal_type") == "automatic",
    }


# --------------------------------------------------------------------------
# Stage 6C2 — value accounting
# --------------------------------------------------------------------------
def outcome_protected_value(outcome: dict) -> float:
    """Value protected/recovered by a single recorded outcome.

    Rules (server-side, deterministic; never annualized beyond what happened):
      - terminated / avoided renewal -> only the value of the avoided next term
        (`term_value_avoided`); do NOT annualize beyond it.
      - renegotiated -> the confirmed annual savings/delta
        (`renegotiated_annual_delta`), NOT the full contract value.
      - credit_received / dispute_resolved -> `amount_recovered`.
      - reviewed_and_kept -> $0 (a valid, non-failure outcome).
      - missed -> $0.
    """
    result = outcome.get("result")
    if result == "terminated":
        return float(outcome.get("term_value_avoided") or 0.0)
    if result == "renegotiated":
        return float(outcome.get("renegotiated_annual_delta") or 0.0)
    if result in ("credit_received", "dispute_resolved"):
        return float(outcome.get("amount_recovered") or 0.0)
    return 0.0  # reviewed_and_kept, missed





# --------------------------------------------------------------------------
# Stage 4 — deterministic ranking + provenance-bound explanations
# --------------------------------------------------------------------------
def compute_rank(finding: dict, today: date = None):
    """Deterministic rank from normalized data. Time-dependent (days_remaining)
    so it is refreshed on read. Returns (score, category, basis, days_remaining)."""
    today = today or date.today()
    e = finding.get("extracted", {}) or {}
    vs = finding.get("validation_status")
    action = bool(finding.get("action_required"))
    money = finding.get("money_amount")
    days = None
    dl = e.get("effective_action_deadline")
    if vs == "validated" and dl:
        try:
            days = (datetime.strptime(dl, "%Y-%m-%d").date() - today).days
        except (ValueError, TypeError):
            days = e.get("days_remaining")

    score = 0
    if vs == "validated":
        score += 1_000_000
    if action:
        score += 100_000
    if days is not None and days >= 0:
        score += max(0, 100_000 - days * 100)
    if money is not None:
        score += min(int(money), 100_000)

    if action and days is not None and 0 <= days <= 30:
        cat = "urgent"
    elif action:
        cat = "risk"
    elif finding.get("money_kind") == "saving_opportunity":
        cat = "opportunity"
    elif money is not None:
        cat = "money"
    else:
        cat = "informational"

    basis = {"as_of_date": today.isoformat(), "days_remaining": days,
             "action_required": action, "money_amount": money,
             "validation_status": vs}
    return score, cat, basis, days


def apply_ranking(findings: list[dict], today: date = None) -> list[dict]:
    """Recompute rank (and refresh days_remaining) for each finding, then sort
    by rank_score descending. Pure read-time computation."""
    today = today or date.today()
    for f in findings:
        score, cat, basis, days = compute_rank(f, today)
        f["rank_score"] = score
        f["rank_category"] = cat
        f["rank_basis"] = basis
        if f.get("extracted") is not None and basis["validation_status"] == "validated":
            f["extracted"]["days_remaining"] = days
    return sorted(findings, key=lambda x: x.get("rank_score", 0), reverse=True)


async def generate_explanation(db, finding: dict, user_id: str) -> dict:
    """Generate plain_english / why_it_matters / suggested_action ONLY from the
    finding's validated source quotes, and cache them. Never for needs_review."""
    from models import utc_now_iso
    if finding.get("validation_status") != "validated" or not finding.get("sources"):
        return finding
    if finding.get("type") == "price_increase":
        fact_keys = ("increase_type", "increase_percent", "increase_amount",
                     "increase_formula", "next_term_amount", "max_permitted_amount",
                     "objection_deadline", "effective_action_deadline")
    elif finding.get("type") == "termination_right":
        fact_keys = ("termination_type", "who_may_terminate", "notice_period_value",
                     "notice_period_unit", "earliest_termination_date",
                     "termination_fee_amount", "termination_fee_percent")
    elif finding.get("type") in GENERIC_TYPES:
        fact_keys = ("who", "amount", "amount_percent", "rate_text",
                     "window_value", "window_unit", "window_reference",
                     "effective_action_deadline")
    else:
        fact_keys = ("next_renewal_date", "effective_action_deadline",
                     "notice_days_min", "notice_days_max", "notice_basis",
                     "renewal_type")
    facts = {k: (finding.get("extracted") or {}).get(k) for k in fact_keys}
    try:
        ex = await llm.explain(finding["sources"], facts)
    except Exception:
        return finding
    upd = {
        "plain_english": ex.get("plain_english"),
        "why_it_matters": ex.get("why_it_matters"),
        "suggested_action": ex.get("suggested_action"),
        "explanation_generated_at": utc_now_iso(),
    }
    await db.findings.update_one(
        {"_id": ObjectId(finding["id"]), "user_id": user_id}, {"$set": upd})
    finding.update(upd)
    return finding


async def run_renewal_analysis(db, contract: dict, user_id: str) -> tuple[list[dict], list[str]]:
    """Orchestrate the pipeline and persist renewal_notice finding(s).
    Returns (findings, warnings)."""
    from models import Finding, FindingSource

    contract_id = str(contract["_id"])
    documents = [d async for d in db.documents.find(
        {"contract_id": contract_id, "user_id": user_id})]
    docs_by_id = {str(d["_id"]): {**d, "id": str(d["_id"])} for d in documents}

    chunks, chunk_map = build_chunks(list(docs_by_id.values()))

    # Remove prior renewal_notice findings for idempotent re-analysis.
    # Stage 9: preserve reviewed findings (confirmed/corrected) so re-analysis
    # never silently overwrites them; only clear regenerable ones.
    await db.findings.delete_many(
        {"contract_id": contract_id, "user_id": user_id, "type": "renewal_notice",
         "state": {"$in": ["unconfirmed", "dismissed"]}})

    if not chunks:
        return [], []

    # Deterministic high-recall fallback: always include chunks that contain
    # explicit renewal language, in case the AI locate pass misses them.
    hint_ids = [c["chunk_id"] for c in chunks if RENEWAL_HINT.search(c["text"])]

    candidate_ids = await llm.locate(chunks)
    candidate_ids = list(dict.fromkeys((candidate_ids or []) + hint_ids))
    if not candidate_ids:
        return [], []
    candidates = [c for c in chunks if c["chunk_id"] in candidate_ids]

    extracted = await llm.extract(candidates)
    # At most one targeted retry when the model returns found:false despite
    # explicit candidate renewal language being present.
    if (not isinstance(extracted, dict) or not extracted.get("found")) and hint_ids:
        focus = [c for c in chunks if c["chunk_id"] in set(hint_ids)]
        if focus:
            extracted = await llm.extract(focus)
    if not isinstance(extracted, dict) or not extracted.get("found"):
        return [], []

    validated, valid_purposes = validate_sources(
        extracted.get("sources", []), chunk_map, docs_by_id)

    # Invariant: sources[] is never empty. A finding with no validated sources
    # is not a finding — do not persist or display it.
    if not validated:
        return [], ["Candidate renewal language was detected, but no source "
                    "quote could be validated."]

    validation_notes = []
    needs_review = False

    # Required purposes must each have a validated source.
    missing_required = REQUIRED_PURPOSES - valid_purposes
    if missing_required:
        needs_review = True
        validation_notes.append(
            "Missing validated source for: " + ", ".join(sorted(missing_required)))

    if extracted.get("notice_days_min") is None:
        needs_review = True
        validation_notes.append("Notice period (minimum days) not stated.")

    # ---- notice-anchor classification (see ANCHOR safety note) ----
    # Resolve deterministically from the validated anchor quote (vocabulary
    # profile), falling back to the model's supported classification only when a
    # verbatim anchor quote validated. No default: otherwise "unknown".
    anchor_src = next((s for s in validated if s["purpose"] == "notice_anchor"), None)
    notice_anchor_type = resolve_notice_anchor(
        extracted.get("notice_anchor_type"),
        anchor_src["quote"] if anchor_src else "",
        anchor_src is not None)
    extracted["notice_anchor_type"] = notice_anchor_type

    # Confidence: multi-document provenance caps at medium; low if reviews needed.
    doc_ids_in_sources = {s["document_id"] for s in validated}
    confidence = extracted.get("confidence") or "low"
    if len(doc_ids_in_sources) > 1 and confidence == "high":
        confidence = "medium"

    today = date.today()
    computed, date_notes, date_review = compute_dates(extracted, today)
    if date_review:
        needs_review = True
    validation_notes.extend(date_notes)

    validation_status = "needs_review" if needs_review else "validated"
    if needs_review and confidence == "high":
        confidence = "medium"

    # ---- normalized layer (server-side only) ----
    renewal_type = extracted.get("renewal_type")
    action_required = renewal_type == "automatic"

    # ---- annual-value provenance (never overwrite user-entered) ----
    value_source = extracted.get("annual_value")
    value_src = next((s for s in validated if s["purpose"] == "value"), None)
    if value_source is not None and value_src and contract.get("value_source") != "user_entered":
        await db.contracts.update_one(
            {"_id": contract["_id"], "user_id": user_id},
            {"$set": {
                "annual_value": float(value_source),
                "value_source": "extracted",
                "value_source_quote": value_src["quote"],
                "value_source_document_id": value_src["document_id"],
                "value_source_location": value_src["location"],
                "value_source_char_offset": value_src["char_offset"],
            }})
        contract["annual_value"] = float(value_source)
        contract["currency"] = contract.get("currency") or "USD"

    money_amount = contract.get("annual_value")
    money_currency = contract.get("currency") if money_amount is not None else None
    money_kind = "contract_value" if money_amount is not None else None

    # ---- assemble the extracted object stored on the finding ----
    extracted_fields = {
        "effective_date": extracted.get("effective_date"),
        "initial_term_value": extracted.get("initial_term_value"),
        "initial_term_unit": extracted.get("initial_term_unit"),
        "renewal_type": renewal_type,
        "renewal_period_value": extracted.get("renewal_period_value"),
        "renewal_period_unit": extracted.get("renewal_period_unit"),
        "notice_days_min": extracted.get("notice_days_min"),
        "notice_days_max": extracted.get("notice_days_max"),
        "notice_basis": extracted.get("notice_basis"),
        "business_day_definition": extracted.get("business_day_definition"),
        "notice_measured_to": extracted.get("notice_measured_to"),
        "deemed_receipt_rule": extracted.get("deemed_receipt_rule"),
        "notice_method": extracted.get("notice_method"),
        "notice_recipient": extracted.get("notice_recipient"),
        "notice_anchor_type": notice_anchor_type,
        "notice_anchor_quote": anchor_src["quote"] if anchor_src else None,
        "notice_anchor_location": anchor_src["location"] if anchor_src else None,
        **computed,
    }
    # If not validated, do not expose a computed deadline.
    if validation_status == "needs_review":
        for k in ("action_deadline", "earliest_action_date",
                  "effective_action_deadline", "days_remaining"):
            extracted_fields[k] = None

    finding = Finding(
        contract_id=contract_id, user_id=user_id, type="renewal_notice",
        extracted=extracted_fields,
        sources=[FindingSource(**s) for s in validated],
        confidence=confidence,
        action_required=action_required,
        money_amount=money_amount, money_currency=money_currency,
        money_kind=money_kind,
        validation_status=validation_status,
        validation_notes=validation_notes,
        state="unconfirmed",
        anchor_version=ANCHOR_VERSION,
    )
    result = await db.findings.insert_one(finding.to_mongo())
    finding.id = str(result.inserted_id)
    fd = finding.model_dump()
    if validation_status == "validated":
        fd = await generate_explanation(db, fd, user_id)
    return [fd], []


# --------------------------------------------------------------------------
# Stage 7A — price_increase (reuses chunking / validation / ranking / review)
# --------------------------------------------------------------------------
PRICE_HINT = re.compile(
    r"price\s+increase|fee\s+increase|increase\s+(in|of|the)\s+(price|fees?|rates?|charges?)|"
    r"annual(ly)?\s+increase|escalat|uplift|indexation|index[- ]linked|"
    r"\bCPI\b|\bRPI\b|consumer\s+price\s+index|price\s+adjustment|"
    r"shall\s+increase|may\s+increase|not\s+(to\s+)?exceed|no\s+more\s+than|"
    r"up\s+to\s+\d+\s*%|\d+\s*%\s+(per\s+annum|annually|increase|each\s+year)",
    re.I)

PRICE_INCREASE_TYPES = {"fixed_automatic", "capped", "formula", "unspecified"}
REQUIRED_PRICE_PURPOSES = {"increase"}

PRICE_EDITABLE_FIELDS = [
    "increase_type", "increase_percent", "increase_amount", "increase_formula",
    "increase_basis", "price_change_date", "objection_window_value",
    "objection_window_unit", "objection_basis", "objection_measured_to",
    "objection_deadline_stated", "objection_recipient", "objection_method",
]


def _pct_frac(p):
    return float(p) / 100.0


def compute_price(extracted: dict, today: date, current_annual_value):
    """Deterministic price-increase math. Server-side only; never invents an
    index value or a projection the contract does not support.

    Returns (computed, notes, needs_review, money_amount, money_kind, action_required).
    """
    out = {"objection_deadline": None, "effective_action_deadline": None,
           "days_remaining": None, "next_term_amount": None,
           "max_permitted_amount": None}
    notes, needs_review = [], False
    money_amount, money_kind = None, None

    itype = extracted.get("increase_type")
    pct = extracted.get("increase_percent")
    amt = extracted.get("increase_amount")
    formula = extracted.get("increase_formula")

    if itype not in ("fixed_automatic", "capped", "formula"):
        needs_review = True
        notes.append("The increase type is not clearly stated; confirm how the "
                     "price can change.")
        itype = "unspecified"

    if itype == "fixed_automatic":
        # A fixed automatic increase may calculate the next-term amount.
        if pct is not None and current_annual_value is not None:
            money_amount = round(float(current_annual_value) * _pct_frac(pct), 2)
            out["next_term_amount"] = round(float(current_annual_value) + money_amount, 2)
            money_kind = "cost"
        elif amt is not None:
            money_amount = float(amt)
            money_kind = "cost"
            if current_annual_value is not None:
                out["next_term_amount"] = round(float(current_annual_value) + money_amount, 2)
        else:
            needs_review = True
            notes.append("A fixed increase applies but its percentage or amount "
                         "is not stated.")
    elif itype == "capped":
        # Show the MAXIMUM permitted increase only — never a guaranteed one.
        if pct is not None and current_annual_value is not None:
            money_amount = round(float(current_annual_value) * _pct_frac(pct), 2)
            out["max_permitted_amount"] = round(float(current_annual_value) + money_amount, 2)
            money_kind = "cost"
            notes.append("This is the maximum permitted increase, not a "
                         "guaranteed increase.")
        elif pct is not None:
            notes.append("This is the maximum permitted increase, not a "
                         "guaranteed increase.")
        else:
            needs_review = True
            notes.append("A cap on increases applies but the maximum is not stated.")
    elif itype == "formula":
        # Formula-based: show the formula until its external index is known.
        if formula:
            notes.append("The increase follows a formula; the amount is unknown "
                         "until the external index or value is published.")
        else:
            needs_review = True
            notes.append("A formula-based increase applies but the formula is "
                         "not stated.")

    # objection window / deadline
    ow_val = extracted.get("objection_window_value")
    ow_unit = extracted.get("objection_window_unit")
    ref = extracted.get("price_change_date")
    stated = extracted.get("objection_deadline_stated")
    deadline_date = None
    if stated:
        try:
            deadline_date = datetime.strptime(stated, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            deadline_date = None
    if deadline_date is None and ow_val and ow_unit and ref:
        try:
            ref_date = datetime.strptime(ref, "%Y-%m-%d").date()
            rel = normalize_unit(ow_val, ow_unit)
            if rel is not None:
                deadline_date = ref_date - rel  # object before the increase takes effect
        except (ValueError, TypeError):
            deadline_date = None
    if (ow_val or stated) and deadline_date is None:
        needs_review = True
        notes.append("An objection window is stated but there is no reference "
                     "date to calculate the deadline; confirm the dates.")

    action_required = False
    if deadline_date is not None:
        out["objection_deadline"] = deadline_date.isoformat()
        out["effective_action_deadline"] = deadline_date.isoformat()
        out["days_remaining"] = (deadline_date - today).days
        action_required = True

    return out, notes, needs_review, money_amount, money_kind, action_required


def recompute_price_derived(edits: dict, current_annual_value, today: date = None) -> dict:
    """Recompute price-increase derived fields from edited values using the same
    deterministic logic (no LLM). Used by Correct for price_increase findings."""
    today = today or date.today()
    computed, notes, review, money_amount, money_kind, action_required = compute_price(
        edits, today, current_annual_value)
    validation_status = "needs_review" if review else "validated"
    fields = {k: edits.get(k) for k in PRICE_EDITABLE_FIELDS}
    fields.update(computed)
    if validation_status == "needs_review":
        for k in ("objection_deadline", "effective_action_deadline", "days_remaining"):
            fields[k] = None
    return {
        "extracted": fields,
        "validation_status": validation_status,
        "validation_notes": notes,
        "action_required": action_required if validation_status == "validated" else False,
        "money_amount": money_amount,
        "money_kind": money_kind,
    }


OBJECTION_FIELDS = (
    "objection_window_value", "objection_window_unit", "objection_basis",
    "objection_measured_to", "objection_deadline_stated",
    "objection_recipient", "objection_method",
)

_INDEX_TERMS = ("consumer price index", "cpi", "rpi", "cost of living",
                "cost-of-living", "price index")
_CEIL_RE = re.compile(
    r"lesser of|whichever is (?:less|lower)|not to exceed|shall not exceed|"
    r"no(?:t)? more than|never (?:be )?more than|no greater than|"
    r"in no event[^.]{0,60}(?:more than|exceed)", re.I)
_FLOOR_RE = re.compile(
    r"higher of|greater of|no(?:t)? less than|never (?:be )?less than|"
    r"whichever is (?:greater|higher)", re.I)


def _strip_unsupported_objection(extracted: dict, valid_purposes: set) -> bool:
    """An objection window/method may survive ONLY with a validated `objection`
    source. Otherwise clear all objection fields so no deadline/action can be
    derived from them. Never infer a window from a percentage or other number."""
    if "objection" in valid_purposes:
        return False
    stripped = any(extracted.get(k) is not None for k in OBJECTION_FIELDS)
    for k in OBJECTION_FIELDS:
        extracted[k] = None
    return stripped


def refine_increase_semantics(extracted: dict, sources: list) -> None:
    """Correct floor/cap/collar semantics deterministically from grounded text
    (validated increase quotes + the extracted formula). Precise keyword/regex
    logic only — no fuzzy matching, no new projection logic.

      - "higher of X% or index" (floor) or a collar (floor+ceiling) -> formula;
        preserve the floor/collar in increase_formula; no projected amount.
      - "lesser of X% or index" / a pure ceiling -> capped.
      - index-only language -> formula.
    """
    itype = extracted.get("increase_type")
    if itype not in ("capped", "formula", "fixed_automatic", "unspecified", None):
        return
    grounded = [s.get("quote") for s in sources
                if s.get("purpose") in ("increase", "increase_basis") and s.get("quote")]
    blob = " ".join([extracted.get("increase_formula") or ""] + grounded)
    if not blob.strip():
        return
    low = blob.lower()
    has_index = any(t in low for t in _INDEX_TERMS)
    has_floor = bool(_FLOOR_RE.search(blob))
    has_ceiling = bool(_CEIL_RE.search(blob))

    def to_formula():
        extracted["increase_type"] = "formula"
        if not (extracted.get("increase_formula") or "").strip() and grounded:
            extracted["increase_formula"] = grounded[0]
        extracted["increase_percent"] = None
        extracted["increase_amount"] = None

    if has_floor and (has_index or has_ceiling):
        to_formula()                       # floor ("higher of") or collar
    elif has_ceiling and not has_floor:
        extracted["increase_type"] = "capped"
    elif has_index and not has_ceiling and not has_floor:
        to_formula()                       # index-only



# --------------------------------------------------------------------------
# Stage 7C — termination_right
# --------------------------------------------------------------------------
TERMINATION_HINT = re.compile(
    r"terminat(e|ion)\s+(this\s+agreement|for\s+convenience|without\s+cause|"
    r"early|the\s+agreement|prior\s+to)|for\s+convenience|early\s+(exit|termination)|"
    r"break\s+(clause|right)|without\s+cause|right\s+to\s+terminate|"
    r"cancel\s+(this\s+)?agreement|termination\s+(fee|charge|penalty)|"
    r"early\s+termination\s+(fee|charge)", re.I)

TERMINATION_TYPES = {"for_convenience", "early_exit", "for_cause", "unspecified"}
REQUIRED_TERMINATION_PURPOSES = {"termination_right"}

TERMINATION_EDITABLE_FIELDS = [
    "termination_type", "who_may_terminate", "notice_period_value",
    "notice_period_unit", "notice_basis", "notice_measured_to", "effective_date",
    "min_term_value", "min_term_unit", "earliest_termination_date",
    "cure_period_value", "cure_period_unit",
    "termination_fee_stated", "termination_fee_amount", "termination_fee_percent",
    "termination_fee_basis", "method", "recipient",
]


def compute_termination(extracted: dict, today: date):
    """Deterministic termination-right normalization. Server-side only; never
    infers a right and never projects a fee that is not explicitly stated.

    Returns (computed, notes, needs_review, money_amount, money_kind, action_required).
    """
    out = {"earliest_termination_date": None, "effective_action_deadline": None,
           "days_remaining": None}
    notes, needs_review = [], False
    money_amount, money_kind = None, None

    ttype = extracted.get("termination_type")
    if ttype not in ("for_convenience", "early_exit", "for_cause"):
        needs_review = True
        notes.append("The termination right is not clearly stated; confirm "
                     "whether and how the contract can be ended early.")
        ttype = "unspecified"

    npv = extracted.get("notice_period_value")
    if ttype in ("for_convenience", "early_exit") and npv is None:
        needs_review = True
        notes.append("An early-exit right applies but the required notice "
                     "period is not stated.")

    # Earliest exit: explicit date, else effective_date + minimum term (lock-in).
    ed = extracted.get("earliest_termination_date")
    if not ed:
        eff = extracted.get("effective_date")
        mtv, mtu = extracted.get("min_term_value"), extracted.get("min_term_unit")
        if eff and mtv and mtu:
            try:
                base = datetime.strptime(eff, "%Y-%m-%d").date()
                rel = normalize_unit(mtv, mtu)
                if rel is not None:
                    ed = (base + rel).isoformat()
            except (ValueError, TypeError):
                ed = None
    out["earliest_termination_date"] = ed

    # Termination fee — explicit only, never projected from a percentage.
    fee = extracted.get("termination_fee_amount")
    pct = extracted.get("termination_fee_percent")
    if extracted.get("termination_fee_stated"):
        if fee is not None:
            money_amount, money_kind = float(fee), "cost"
        elif pct is not None:
            notes.append("A termination fee applies as a percentage; the amount "
                         "depends on the remaining term.")
        else:
            needs_review = True
            notes.append("A termination fee applies but the amount is not stated.")
    elif fee is not None:
        money_amount, money_kind = float(fee), "cost"

    # Actionable notice deadline: to exit at the earliest permitted date you must
    # give notice by (earliest exit - notice period). Deterministic; computed
    # ONLY when an early-exit right, a notice period, AND a concrete earliest-exit
    # date are all known. Otherwise the right stays a standing (non-dated) right.
    action_required = False
    npv = extracted.get("notice_period_value")
    npu = extracted.get("notice_period_unit")
    if ttype in ("for_convenience", "early_exit") and ed and npv and npu:
        try:
            exit_date = datetime.strptime(ed, "%Y-%m-%d").date()
            rel = normalize_unit(npv, npu)
            if rel is not None:
                deadline = exit_date - rel
                out["effective_action_deadline"] = deadline.isoformat()
                out["days_remaining"] = (deadline - today).days
                action_required = True
        except (ValueError, TypeError):
            pass

    return out, notes, needs_review, money_amount, money_kind, action_required


def recompute_termination_derived(edits: dict, today: date = None) -> dict:
    today = today or date.today()
    computed, notes, review, money_amount, money_kind, action_required = compute_termination(
        edits, today)
    validation_status = "needs_review" if review else "validated"
    fields = {k: edits.get(k) for k in TERMINATION_EDITABLE_FIELDS}
    fields.update(computed)
    return {
        "extracted": fields,
        "validation_status": validation_status,
        "validation_notes": notes,
        "action_required": action_required,
        "money_amount": money_amount,
        "money_kind": money_kind,
    }


async def run_termination_analysis(db, contract: dict, user_id: str) -> tuple[list[dict], list[str]]:
    """Orchestrate the termination_right pipeline and persist finding(s)."""
    from models import Finding, FindingSource

    contract_id = str(contract["_id"])
    documents = [d async for d in db.documents.find(
        {"contract_id": contract_id, "user_id": user_id})]
    docs_by_id = {str(d["_id"]): {**d, "id": str(d["_id"])} for d in documents}
    chunks, chunk_map = build_chunks(list(docs_by_id.values()))

    await db.findings.delete_many(
        {"contract_id": contract_id, "user_id": user_id, "type": "termination_right",
         "state": {"$in": ["unconfirmed", "dismissed"]}})
    if not chunks:
        return [], []

    hint_ids = [c["chunk_id"] for c in chunks if TERMINATION_HINT.search(c["text"])]
    candidate_ids = await llm.locate_termination(chunks)
    candidate_ids = list(dict.fromkeys((candidate_ids or []) + hint_ids))
    if not candidate_ids:
        return [], []
    candidates = [c for c in chunks if c["chunk_id"] in candidate_ids]

    extracted = await llm.extract_termination(candidates)
    if (not isinstance(extracted, dict) or not extracted.get("found")) and hint_ids:
        focus = [c for c in chunks if c["chunk_id"] in set(hint_ids)]
        if focus:
            extracted = await llm.extract_termination(focus)
    if not isinstance(extracted, dict) or not extracted.get("found"):
        return [], []

    validated, valid_purposes = validate_sources(
        extracted.get("sources", []), chunk_map, docs_by_id)
    if not validated:
        return [], ["Candidate termination language was detected, but no source "
                    "quote could be validated."]

    validation_notes = []
    needs_review = False
    missing_required = REQUIRED_TERMINATION_PURPOSES - valid_purposes
    if missing_required:
        needs_review = True
        validation_notes.append(
            "Missing validated source for: " + ", ".join(sorted(missing_required)))

    confidence = extracted.get("confidence") or "low"
    doc_ids_in_sources = {s["document_id"] for s in validated}
    if len(doc_ids_in_sources) > 1 and confidence == "high":
        confidence = "medium"

    today = date.today()
    computed, term_notes, term_review, money_amount, money_kind, action_required = compute_termination(
        extracted, today)
    if term_review:
        needs_review = True
    validation_notes.extend(term_notes)

    validation_status = "needs_review" if needs_review else "validated"
    if needs_review and confidence == "high":
        confidence = "medium"

    extracted_fields = {k: extracted.get(k) for k in TERMINATION_EDITABLE_FIELDS}
    extracted_fields.update(computed)

    finding = Finding(
        contract_id=contract_id, user_id=user_id, type="termination_right",
        extracted=extracted_fields,
        sources=[FindingSource(**s) for s in validated],
        confidence=confidence,
        action_required=action_required,
        money_amount=money_amount,
        money_currency=(contract.get("currency") or "USD") if money_amount is not None else None,
        money_kind=money_kind,
        validation_status=validation_status,
        validation_notes=validation_notes,
        state="unconfirmed",
    )
    result = await db.findings.insert_one(finding.to_mongo())
    finding.id = str(result.inserted_id)
    fd = finding.model_dump()
    if validation_status == "validated":
        fd = await generate_explanation(db, fd, user_id)
    return [fd], []



async def run_price_increase_analysis(db, contract: dict, user_id: str) -> tuple[list[dict], list[str]]:
    """Orchestrate the price_increase pipeline and persist finding(s)."""
    from models import Finding, FindingSource

    contract_id = str(contract["_id"])
    documents = [d async for d in db.documents.find(
        {"contract_id": contract_id, "user_id": user_id})]
    docs_by_id = {str(d["_id"]): {**d, "id": str(d["_id"])} for d in documents}
    chunks, chunk_map = build_chunks(list(docs_by_id.values()))

    # Idempotent re-analysis.
    await db.findings.delete_many(
        {"contract_id": contract_id, "user_id": user_id, "type": "price_increase",
         "state": {"$in": ["unconfirmed", "dismissed"]}})
    if not chunks:
        return [], []

    hint_ids = [c["chunk_id"] for c in chunks if PRICE_HINT.search(c["text"])]
    candidate_ids = await llm.locate_price(chunks)
    candidate_ids = list(dict.fromkeys((candidate_ids or []) + hint_ids))
    if not candidate_ids:
        return [], []
    candidates = [c for c in chunks if c["chunk_id"] in candidate_ids]

    extracted = await llm.extract_price(candidates)
    if (not isinstance(extracted, dict) or not extracted.get("found")) and hint_ids:
        focus = [c for c in chunks if c["chunk_id"] in set(hint_ids)]
        if focus:
            extracted = await llm.extract_price(focus)
    if not isinstance(extracted, dict) or not extracted.get("found"):
        return [], []

    validated, valid_purposes = validate_sources(
        extracted.get("sources", []), chunk_map, docs_by_id)
    if not validated:
        return [], ["Candidate price-increase language was detected, but no "
                    "source quote could be validated."]

    validation_notes = []
    needs_review = False
    missing_required = REQUIRED_PRICE_PURPOSES - valid_purposes
    if missing_required:
        needs_review = True
        validation_notes.append(
            "Missing validated source for: " + ", ".join(sorted(missing_required)))

    # Objection window/method survives only with a validated objection source.
    _strip_unsupported_objection(extracted, valid_purposes)
    # Correct floor/cap/collar semantics from grounded text before any math.
    refine_increase_semantics(extracted, validated)

    doc_ids_in_sources = {s["document_id"] for s in validated}
    confidence = extracted.get("confidence") or "low"
    if len(doc_ids_in_sources) > 1 and confidence == "high":
        confidence = "medium"

    today = date.today()
    current_annual_value = contract.get("annual_value")
    computed, price_notes, price_review, money_amount, money_kind, action_required = compute_price(
        extracted, today, current_annual_value)
    if price_review:
        needs_review = True
    validation_notes.extend(price_notes)

    validation_status = "needs_review" if needs_review else "validated"
    if needs_review and confidence == "high":
        confidence = "medium"

    extracted_fields = {
        "increase_type": extracted.get("increase_type"),
        "increase_percent": extracted.get("increase_percent"),
        "increase_amount": extracted.get("increase_amount"),
        "increase_formula": extracted.get("increase_formula"),
        "increase_basis": extracted.get("increase_basis"),
        "price_change_date": extracted.get("price_change_date"),
        "objection_window_value": extracted.get("objection_window_value"),
        "objection_window_unit": extracted.get("objection_window_unit"),
        "objection_basis": extracted.get("objection_basis"),
        "objection_measured_to": extracted.get("objection_measured_to"),
        "objection_deadline_stated": extracted.get("objection_deadline_stated"),
        "objection_recipient": extracted.get("objection_recipient"),
        "objection_method": extracted.get("objection_method"),
        **computed,
    }
    if validation_status == "needs_review":
        for k in ("objection_deadline", "effective_action_deadline", "days_remaining"):
            extracted_fields[k] = None
        action_required = False

    finding = Finding(
        contract_id=contract_id, user_id=user_id, type="price_increase",
        extracted=extracted_fields,
        sources=[FindingSource(**s) for s in validated],
        confidence=confidence,
        action_required=action_required,
        money_amount=money_amount,
        money_currency=(contract.get("currency") or "USD") if money_amount is not None else None,
        money_kind=money_kind,
        validation_status=validation_status,
        validation_notes=validation_notes,
        state="unconfirmed",
    )
    result = await db.findings.insert_one(finding.to_mongo())
    finding.id = str(result.inserted_id)
    fd = finding.model_dump()
    if validation_status == "validated":
        fd = await generate_explanation(db, fd, user_id)
    return [fd], []


# --------------------------------------------------------------------------
# Stage 8/10 — shared obligations pipeline (service_credit, invoice_dispute,
# notice_requirement, fee_or_penalty, rebate_or_refund, warranty_claim).
# Reuses chunking / provenance validation / ranking / review / explanations.
# --------------------------------------------------------------------------
GENERIC_TYPES = [
    "service_credit", "invoice_dispute", "notice_requirement",
    "fee_or_penalty", "rebate_or_refund", "warranty_claim",
]
_CREDIT_TYPES = {"service_credit", "rebate_or_refund"}
_COST_TYPES = {"fee_or_penalty"}
REQUIRED_GENERIC_PURPOSES = {"obligation"}

OBLIGATION_HINT = re.compile(
    r"service\s+credit|SLA\s+credit|service\s+level\s+credit|"
    r"dispute(d)?\s+(the\s+)?invoice|invoice.{0,20}dispute|good\s+faith\s+dispute|"
    r"withhold(ing)?\s+(disputed\s+)?payment|"
    r"late\s+(payment\s+)?(fee|charge|interest)|default\s+interest|"
    r"penalt(y|ies)|interest\s+(shall|will|may)\s+accrue|"
    r"rebate|refund|credit\s+note|volume\s+discount|"
    r"warrant(y|ies)|warranty\s+claim|warranty\s+period|"
    r"notice(s)?\s+(shall|must|will)\s+be\s+(given|sent|delivered|in\s+writing)|"
    r"any\s+notice\s+(under|required)",
    re.I)

GENERIC_EDITABLE_FIELDS = [
    "who", "amount", "amount_percent", "rate_text",
    "window_value", "window_unit", "window_basis", "window_reference",
    "trigger_date", "deadline_stated",
]


def compute_generic(extracted: dict, ftype: str, today: date):
    """Deterministic normalization for the shared obligation finding types.
    Server-side only; never invents an amount, a window, or a date.

    Deadline (all math server-side):
      - explicit calendar deadline_stated -> tracked;
      - relative window + a known trigger_date -> compute trigger + window;
      - relative window with no verified trigger date -> preserve the rule and
        mark timing needs_review (no invented date).

    Returns (computed, notes, needs_review, money_amount, money_kind, action_required).
    """
    out = {"effective_action_deadline": None, "days_remaining": None}
    notes, needs_review = [], False
    money_amount, money_kind = None, None

    amt = extracted.get("amount")
    if amt is not None:
        money_amount = float(amt)
        money_kind = ("credit" if ftype in _CREDIT_TYPES
                      else "cost" if ftype in _COST_TYPES else None)

    wv = extracted.get("window_value")
    wu = extracted.get("window_unit")
    stated = extracted.get("deadline_stated")
    trigger = extracted.get("trigger_date")

    deadline_date = None
    if stated:
        try:
            deadline_date = datetime.strptime(stated, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            deadline_date = None
    elif trigger and wv and wu:
        try:
            base = datetime.strptime(trigger, "%Y-%m-%d").date()
            rel = normalize_unit(wv, wu)
            if rel is not None:
                deadline_date = base + rel  # act within the window after the trigger
        except (ValueError, TypeError):
            deadline_date = None

    action_required = False
    if deadline_date is not None:
        out["effective_action_deadline"] = deadline_date.isoformat()
        out["days_remaining"] = (deadline_date - today).days
        action_required = True
    elif wv and wu:
        needs_review = True
        ref = extracted.get("window_reference")
        notes.append(
            "This window is measured from a trigger date"
            + (f" ({ref})" if ref else " (e.g. the invoice or delivery date)")
            + " that is not stated. Add that date to track this deadline.")

    return out, notes, needs_review, money_amount, money_kind, action_required


def recompute_generic_derived(edits: dict, ftype: str, today: date = None) -> dict:
    today = today or date.today()
    computed, notes, review, money_amount, money_kind, action_required = compute_generic(
        edits, ftype, today)
    validation_status = "needs_review" if review else "validated"
    fields = {k: edits.get(k) for k in GENERIC_EDITABLE_FIELDS}
    fields.update(computed)
    if validation_status == "needs_review":
        for k in ("effective_action_deadline", "days_remaining"):
            fields[k] = None
        action_required = False
    return {
        "extracted": fields,
        "validation_status": validation_status,
        "validation_notes": notes,
        "action_required": action_required,
        "money_amount": money_amount,
        "money_kind": money_kind,
    }


_RENEWAL_TOPIC_HINTS = ("renew", "non-renewal", "current term", "then-current term", "term end")


def _shares_renewal_topic(rf: dict, validated_sources: list[dict]) -> bool:
    """Confirms the notice_requirement is actually ABOUT the same non-renewal
    notice provision (not just a coincidental day-count + document match)."""
    text = " ".join(
        [str(rf.get("window_reference") or "")] + [s.get("quote", "") for s in validated_sources]
    ).lower()
    return any(h in text for h in _RENEWAL_TOPIC_HINTS)


def _is_duplicate_notice_requirement(rf: dict, validated_sources: list[dict],
                                     renewal_finding: dict | None) -> bool:
    """A notice_requirement candidate is a duplicate of the contract's own
    renewal_notice non-renewal clause when it states the SAME day count and
    (when available) the same notice_basis, is grounded in a document the
    renewal finding's own notice_period / notice_anchor sources already
    cite, AND is actually about the same non-renewal notice provision.
    Deterministic overlap check only — never suppresses an unrelated
    notice_requirement (different day count, basis, document, or topic)."""
    if not renewal_finding:
        return False
    r_extracted = renewal_finding.get("extracted") or {}
    r_days = r_extracted.get("notice_days_min")
    if r_days is None:
        return False
    wv = rf.get("window_value")
    wu = (rf.get("window_unit") or "days").rstrip("s")
    if wv != r_days or wu != "day":
        return False
    r_basis = r_extracted.get("notice_basis")
    n_basis = rf.get("window_basis")
    if r_basis and n_basis and r_basis != n_basis:
        return False
    if not _shares_renewal_topic(rf, validated_sources):
        return False
    r_doc_ids = {s.get("document_id") for s in (renewal_finding.get("sources") or [])
                 if s.get("purpose") in ("notice_period", "notice_anchor")}
    n_doc_ids = {s.get("document_id") for s in validated_sources}
    return bool(r_doc_ids & n_doc_ids)


async def run_obligations_analysis(db, contract: dict, user_id: str,
                                   renewal_finding: dict | None = None) -> tuple[list[dict], list[str]]:
    """Orchestrate the shared obligations pipeline; persist 0-N findings across
    the 6 generic types. One locate + one extract (returns a list)."""
    from models import Finding, FindingSource

    contract_id = str(contract["_id"])
    documents = [d async for d in db.documents.find(
        {"contract_id": contract_id, "user_id": user_id})]
    docs_by_id = {str(d["_id"]): {**d, "id": str(d["_id"])} for d in documents}
    chunks, chunk_map = build_chunks(list(docs_by_id.values()))

    # Idempotent re-analysis; Stage 9 preserves reviewed findings.
    await db.findings.delete_many(
        {"contract_id": contract_id, "user_id": user_id,
         "type": {"$in": GENERIC_TYPES},
         "state": {"$in": ["unconfirmed", "dismissed"]}})
    if not chunks:
        return [], []

    hint_ids = [c["chunk_id"] for c in chunks if OBLIGATION_HINT.search(c["text"])]
    candidate_ids = await llm.locate_obligations(chunks)
    candidate_ids = list(dict.fromkeys((candidate_ids or []) + hint_ids))
    if not candidate_ids:
        return [], []
    candidates = [c for c in chunks if c["chunk_id"] in candidate_ids]

    raw_findings = await llm.extract_obligations(candidates)
    if not raw_findings and hint_ids:
        focus = [c for c in chunks if c["chunk_id"] in set(hint_ids)]
        if focus:
            raw_findings = await llm.extract_obligations(focus)
    if not raw_findings:
        return [], []

    today = date.today()
    persisted = []
    for rf in raw_findings:
        if not isinstance(rf, dict):
            continue
        ftype = rf.get("finding_type")
        if ftype not in GENERIC_TYPES:
            continue

        validated, valid_purposes = validate_sources(
            rf.get("sources", []), chunk_map, docs_by_id)
        if not validated:
            continue  # invariant: sources[] never empty

        # A notice_requirement that merely restates the renewal_notice's own
        # non-renewal clause competes with it rather than adding new
        # information — suppress it here, before persistence.
        if ftype == "notice_requirement" and _is_duplicate_notice_requirement(
                rf, validated, renewal_finding):
            continue

        validation_notes = []
        needs_review = False
        missing_required = REQUIRED_GENERIC_PURPOSES - valid_purposes
        if missing_required:
            needs_review = True
            validation_notes.append(
                "Missing validated source for: " + ", ".join(sorted(missing_required)))

        confidence = rf.get("confidence") or "low"
        doc_ids_in_sources = {s["document_id"] for s in validated}
        if len(doc_ids_in_sources) > 1 and confidence == "high":
            confidence = "medium"

        computed, gen_notes, gen_review, money_amount, money_kind, action_required = compute_generic(
            rf, ftype, today)
        if gen_review:
            needs_review = True
        validation_notes.extend(gen_notes)

        validation_status = "needs_review" if needs_review else "validated"
        if needs_review and confidence == "high":
            confidence = "medium"

        extracted_fields = {k: rf.get(k) for k in GENERIC_EDITABLE_FIELDS}
        extracted_fields.update(computed)
        if validation_status == "needs_review":
            for k in ("effective_action_deadline", "days_remaining"):
                extracted_fields[k] = None
            action_required = False

        finding = Finding(
            contract_id=contract_id, user_id=user_id, type=ftype,
            extracted=extracted_fields,
            sources=[FindingSource(**s) for s in validated],
            confidence=confidence,
            action_required=action_required,
            money_amount=money_amount,
            money_currency=(contract.get("currency") or "USD") if money_amount is not None else None,
            money_kind=money_kind,
            validation_status=validation_status,
            validation_notes=validation_notes,
            state="unconfirmed",
        )
        result = await db.findings.insert_one(finding.to_mongo())
        finding.id = str(result.inserted_id)
        fd = finding.model_dump()
        if validation_status == "validated":
            fd = await generate_explanation(db, fd, user_id)
        persisted.append(fd)

    return persisted, []


# --------------------------------------------------------------------------
# Stage 7B — Rate Shock Composite (renewal_with_escalation)
# --------------------------------------------------------------------------
COMPOSITE_TYPE = "renewal_with_escalation"
_CONF_ORDER = {"low": 0, "medium": 1, "high": 2}


def _composite_qualifies(f: dict) -> bool:
    """A constituent may feed the composite only if it is validated, not
    dismissed, and actually supported by validated sources."""
    return (f.get("validation_status") == "validated"
            and f.get("state") != "dismissed"
            and not f.get("superseded_by_finding_id")
            and bool(f.get("sources")))


def _union_sources(*groups) -> list:
    seen, out = set(), []
    for g in groups:
        for s in g or []:
            key = (s.get("chunk_id"), s.get("purpose"), s.get("quote"))
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
    return out


async def refresh_rate_shock_composite(db, contract: dict, user_id: str):
    """Rebuild (or remove) the renewal_with_escalation composite for a contract.
    Server-derived only — unions ALREADY-validated constituent sources, never
    invents quotes or runs the LLM. Removes itself unless BOTH a validated
    renewal and a validated price_increase exist."""
    from models import Finding, FindingSource, utc_now_iso

    contract_id = str(contract["_id"])
    await db.findings.delete_many(
        {"contract_id": contract_id, "user_id": user_id, "type": COMPOSITE_TYPE})

    renewal = price = None
    async for f in db.findings.find(
            {"contract_id": contract_id, "user_id": user_id, "type": "renewal_notice"}):
        rf = Finding.from_mongo(f).model_dump()
        if _composite_qualifies(rf):
            renewal = rf
            break
    async for f in db.findings.find(
            {"contract_id": contract_id, "user_id": user_id, "type": "price_increase"}):
        pf = Finding.from_mongo(f).model_dump()
        if _composite_qualifies(pf):
            price = pf
            break
    if not (renewal and price):
        return None

    re_, pe = renewal["extracted"] or {}, price["extracted"] or {}
    itype = pe.get("increase_type")
    pct = pe.get("increase_percent")

    # Escalation figures — strictly what the price finding already supports.
    next_term = pe.get("next_term_amount") if itype == "fixed_automatic" else None
    max_permitted = pe.get("max_permitted_amount") if itype == "capped" else None
    # Only fixed_automatic and capped carry a money figure; formula/collar/floor
    # never projects an amount until the external index value is known.
    money_amount = price.get("money_amount") if itype in ("fixed_automatic", "capped") else None
    money_kind = "cost" if money_amount is not None else None
    currency = price.get("money_currency") or contract.get("currency") or "USD"

    composite_extracted = {
        "next_renewal_date": re_.get("next_renewal_date"),
        "renewal_type": re_.get("renewal_type"),
        "effective_action_deadline": re_.get("effective_action_deadline"),
        "earliest_action_date": re_.get("earliest_action_date"),
        "notice_days_min": re_.get("notice_days_min"),
        "notice_days_max": re_.get("notice_days_max"),
        "days_remaining": re_.get("days_remaining"),
        "increase_type": itype,
        "increase_percent": pct,
        "increase_amount": pe.get("increase_amount"),
        "increase_formula": pe.get("increase_formula"),
        "next_term_amount": next_term,
        "max_permitted_amount": max_permitted,
        "escalation_delta": money_amount,
        "objection_deadline": pe.get("objection_deadline"),
        "renewal_finding_id": renewal["id"],
        "price_finding_id": price["id"],
    }

    # Deterministic, grounded explanation (no LLM).
    def _money(v):
        return f"{currency} {v:,.0f}" if v is not None else None
    if itype == "fixed_automatic":
        esc = f"a fixed automatic increase of {pct}% applies"
        if next_term is not None:
            esc += f", taking the annual value to {_money(next_term)} (up {_money(money_amount)})"
    elif itype == "capped":
        esc = (f"the price may rise by up to {pct}% — a maximum of "
               f"{_money(max_permitted)}, not a guaranteed increase" if pct is not None
               else "a capped increase applies")
    elif itype == "formula":
        esc = (f"the price is adjusted by a formula ({pe.get('increase_formula')}); "
               "the exact amount is unknown until the external index is published")
    else:
        esc = "a price increase applies"
    nrd = re_.get("next_renewal_date") or "the renewal date"
    plain = f"This contract renews on {nrd}. At renewal, {esc}."
    action_required = bool(renewal.get("action_required"))
    dl = re_.get("effective_action_deadline")
    suggested = (f"Give notice by {dl} to avoid renewing into the higher price."
                 if action_required and dl else
                 "Review the renewal and the escalation together before the renewal date.")

    confidence = min([renewal.get("confidence", "low"), price.get("confidence", "low")],
                     key=lambda c: _CONF_ORDER.get(c, 0))

    finding = Finding(
        contract_id=contract_id, user_id=user_id, type=COMPOSITE_TYPE,
        extracted=composite_extracted,
        sources=[FindingSource(**s) for s in _union_sources(
            renewal.get("sources"), price.get("sources"))],
        confidence=confidence,
        action_required=action_required,
        money_amount=money_amount,
        money_currency=currency if money_amount is not None else None,
        money_kind=money_kind,
        validation_status="validated",
        validation_notes=[],
        state="unconfirmed",
        is_composite=True,
        composite_of=[renewal["id"], price["id"]],
        related_finding_ids=[renewal["id"], price["id"]],
        plain_english=plain,
        why_it_matters=("A renewal and a price increase land together, so the cost "
                        "of missing the notice window is higher than either alone."),
        suggested_action=suggested,
        explanation_generated_at=utc_now_iso(),
    )
    result = await db.findings.insert_one(finding.to_mongo())
    finding.id = str(result.inserted_id)
    return finding.model_dump()



async def draft_non_renewal_notice(finding: dict) -> str:
    """Draft a non-renewal notice grounded ONLY in the confirmed finding's
    validated sources + server-computed timing. No legal-validity claims."""
    e = finding.get("extracted", {}) or {}
    facts = {
        "notice_method": e.get("notice_method"),
        "notice_recipient": e.get("notice_recipient"),
        "notice_days_min": e.get("notice_days_min"),
        "notice_basis": e.get("notice_basis"),
        "next_renewal_date": e.get("next_renewal_date"),
        "action_deadline": e.get("effective_action_deadline"),
    }
    return await llm.draft_notice(finding.get("sources", []), facts)

