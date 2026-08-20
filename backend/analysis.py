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
    """Deterministic date arithmetic. Returns computed fields + review flags."""
    out = {"next_renewal_date": None, "action_deadline": None,
           "earliest_action_date": None, "effective_action_deadline": None,
           "days_remaining": None}
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

    nmin = extracted.get("notice_days_min")
    nmax = extracted.get("notice_days_max")
    if nmin is None:
        notes.append("Notice period not stated; deadline cannot be calculated.")
        return out, notes + ["notice_days_min_missing"], True

    basis = extracted.get("notice_basis")
    business = basis == "business"
    if business and not extracted.get("business_day_definition"):
        needs_review = True
        notes.append("This contract counts in business days but does not define "
                     "which days count. Confirm this deadline.")

    action_deadline = _sub_days(renewal, nmin, business)
    out["action_deadline"] = action_deadline.isoformat()
    if nmax is not None:
        out["earliest_action_date"] = _sub_days(renewal, nmax, business).isoformat()

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
    "notice_recipient",
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
    if days is not None:
        score += max(0, 100_000 - days * 100)
    if money is not None:
        score += min(int(money), 100_000)

    if action and days is not None and days <= 30:
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
    facts = {k: (finding.get("extracted") or {}).get(k) for k in (
        "next_renewal_date", "effective_action_deadline", "notice_days_min",
        "notice_days_max", "notice_basis", "renewal_type")}
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
    await db.findings.delete_many(
        {"contract_id": contract_id, "user_id": user_id, "type": "renewal_notice"})

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
    )
    result = await db.findings.insert_one(finding.to_mongo())
    finding.id = str(result.inserted_id)
    fd = finding.model_dump()
    if validation_status == "validated":
        fd = await generate_explanation(db, fd, user_id)
    return [fd], []


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

