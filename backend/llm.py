"""
LLM abstraction for ClauseClock analysis — Stage 2.

Model-agnostic wrapper over emergentintegrations so the provider/model can be
swapped via env (LLM_PROVIDER / LLM_MODEL) without touching the pipeline.
Default: Anthropic Claude Sonnet 4.6. Uses the Emergent Universal LLM key.

Two internal, non-streaming calls (server-side extraction, not user-facing):
  - locate(...)  -> list[chunk_id] that may contain renewal/term/notice language
  - extract(...) -> strict renewal_notice JSON
"""

import json
import os
import re
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage

DEFAULT_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")


def _new_chat(system_message: str) -> LlmChat:
    key = os.environ["EMERGENT_LLM_KEY"]
    return LlmChat(
        api_key=key,
        session_id=f"clauseclock-{uuid.uuid4()}",
        system_message=system_message,
    ).with_model(DEFAULT_PROVIDER, DEFAULT_MODEL)


def _parse_json(text: str):
    """Strip code fences / prose and parse the first JSON value present."""
    if text is None:
        raise ValueError("empty LLM response")
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    # Fall back to the outermost {...} or [...] if extra prose slipped in.
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", t, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(1))


LOCATE_SYSTEM = (
    "You are a contract-analysis locator. You receive numbered chunks of a "
    "contract. Identify ONLY the chunks that may contain language about: the "
    "contract term, effective date, expiry, renewal, automatic renewal, "
    "non-renewal or cancellation notice, or notice requirements relevant to "
    "renewal. Return STRICT JSON: {\"chunk_ids\": [\"c_01\", ...]}. Return the "
    "ids of possibly-relevant chunks only. No prose, no explanation."
)

EXTRACT_SYSTEM = (
    "You extract a single renewal_notice finding from the supplied contract "
    "chunks. Output STRICT JSON only, no prose.\n"
    "HARD RULES:\n"
    "- Anything not explicitly stated in the supplied text is null. Never "
    "infer, estimate, repair, or reconstruct missing contract language.\n"
    "- Numbers and units are SEPARATE fields.\n"
    "- notice_days_max is null unless the contract explicitly states an upper "
    "bound.\n"
    "- Every source quote is copied VERBATIM from the supplied chunk, max 400 "
    "characters, and must echo the chunk_id it came from.\n"
    "- Never output document_id, page number, section number, or char_offset "
    "— those are resolved by the server.\n"
    "- Every populated field must have a supporting source purpose. The SAME "
    "verbatim quote and SAME chunk_id MUST be repeated as separate entries in "
    "sources[] when one clause supports multiple concepts — do NOT force a "
    "quote to carry only one purpose, and do NOT drop a purpose because its "
    "quote was already used for another purpose. Do not fabricate a source "
    "just to fill a slot.\n"
    "- Any extracted date, including effective_date, requires its own source.\n"
    "- If there is no renewal/term/notice content at all, return "
    "{\"found\": false}.\n"
    "EXAMPLES of one clause supporting multiple purposes (repeat quote+chunk_id "
    "once per purpose):\n"
    "  \"...shall automatically renew for successive one-year terms unless "
    "written notice is given at least 60 days prior...\" -> emit BOTH "
    "{purpose:renewal_term} AND {purpose:notice_period} (and "
    "{purpose:renewal_term} again also covers renewal_period) with the SAME "
    "chunk_id and SAME quote.\n"
    "  \"...notice shall be in writing and sent by certified mail to the "
    "General Counsel...\" -> emit BOTH {purpose:notice_method} AND "
    "{purpose:notice_recipient} with the same quote/chunk_id.\n"
    "  \"...initial term of twelve (12) months, renewing for twelve (12) month "
    "terms...\" -> emit BOTH {purpose:renewal_term} (initial term) AND "
    "{purpose:renewal_term} covering the renewal period with the same quote.\n"
    "NOTICE ANCHOR (safety-critical): classify what the notice deadline counts "
    "back FROM into notice_anchor_type, and emit the anchoring language VERBATIM "
    "as a source with purpose \"notice_anchor\".\n"
    "  - \"term_end\": notice is measured to the END / COMPLETION / EXPIRATION of "
    "the current term. Examples: \"...prior to the completion of the DMTA "
    "Term...\", \"...before the end of the then-current term...\", \"...prior to "
    "expiration of the term...\".\n"
    "  - \"renewal_start\": notice is measured to the START / COMMENCEMENT of the "
    "renewal/next term. Examples: \"...prior to the start date of the Renewal "
    "Term...\", \"...before the commencement of the renewal term...\".\n"
    "  - \"unknown\": the clause does not clearly anchor to term end OR renewal "
    "start (e.g. an anniversary or a fixed calendar date, or it is ambiguous). "
    "Do NOT guess and do NOT default; return \"unknown\".\n"
    "The term end and the renewal start are usually one day apart — do not treat "
    "them as interchangeable.\n"
    "Schema when found:\n"
    "{\"found\": true, \"effective_date\": \"YYYY-MM-DD|null\", "
    "\"initial_term_value\": int|null, \"initial_term_unit\": "
    "\"days|months|years|null\", \"renewal_type\": "
    "\"automatic|manual|none|null\", \"renewal_period_value\": int|null, "
    "\"renewal_period_unit\": \"days|months|years|null\", \"notice_days_min\": "
    "int|null, \"notice_days_max\": int|null, \"notice_basis\": "
    "\"calendar|business|null\", \"business_day_definition\": str|null, "
    "\"notice_measured_to\": \"sent|received|unspecified|null\", "
    "\"deemed_receipt_rule\": str|null, \"notice_method\": str|null, "
    "\"notice_recipient\": str|null, \"annual_value\": number|null, "
    "\"notice_anchor_type\": \"term_end|renewal_start|unknown|null\", "
    "\"sources\": [{\"purpose\": \"effective_date|renewal_term|notice_period|"
    "notice_method|notice_recipient|business_day_definition|deemed_receipt|"
    "notice_anchor|value\", \"chunk_id\": \"c_xx\", \"quote\": \"verbatim <=400 chars\"}], "
    "\"confidence\": \"high|medium|low\"}"
)


def _render_chunks(chunks: list[dict], include_text: bool = True) -> str:
    parts = []
    for c in chunks:
        if include_text:
            parts.append(f"[{c['chunk_id']}]\n{c['text']}")
        else:
            preview = c["text"][:600]
            parts.append(f"[{c['chunk_id']}]\n{preview}")
    return "\n\n----\n\n".join(parts)


async def locate(chunks: list[dict]) -> list[str]:
    chat = _new_chat(LOCATE_SYSTEM)
    prompt = (
        "Chunks:\n\n" + _render_chunks(chunks, include_text=False) +
        "\n\nReturn JSON {\"chunk_ids\": [...]} listing only possibly-relevant "
        "chunk ids."
    )
    resp = await chat.send_message(UserMessage(text=prompt))
    data = _parse_json(resp)
    ids = data.get("chunk_ids", []) if isinstance(data, dict) else []
    valid = {c["chunk_id"] for c in chunks}
    return [i for i in ids if i in valid]


async def extract(chunks: list[dict]) -> dict:
    chat = _new_chat(EXTRACT_SYSTEM)
    prompt = (
        "Extract the renewal_notice finding from these chunks. Quote verbatim "
        "and echo chunk_ids.\n\n" + _render_chunks(chunks, include_text=True)
    )
    resp = await chat.send_message(UserMessage(text=prompt))
    return _parse_json(resp)


# --------------------------------------------------------------------------
# Stage 7A — price_increase
# --------------------------------------------------------------------------
LOCATE_PRICE_SYSTEM = (
    "You are a contract-analysis locator. You receive numbered chunks of a "
    "contract. Identify ONLY the chunks that may contain language about a PRICE "
    "or FEE INCREASE: automatic annual increases, escalation, uplift, indexation "
    "(CPI/RPI/index-linked), rate changes, price adjustment, a cap or maximum on "
    "increases, or a right to object to a price increase. Return STRICT JSON: "
    "{\"chunk_ids\": [\"c_01\", ...]}. Only possibly-relevant ids. No prose."
)

EXTRACT_PRICE_SYSTEM = (
    "You extract a single price_increase finding from the supplied contract "
    "chunks. Output STRICT JSON only, no prose.\n"
    "HARD RULES:\n"
    "- Anything not explicitly stated in the supplied text is null. Never "
    "infer, estimate, repair, or reconstruct missing contract language.\n"
    "- Extract only what the contract explicitly states about how the price/fee "
    "can change. Do NOT invent numbers, percentages, dates, or an index.\n"
    "- increase_type must be one of: \"fixed_automatic\" (a set percentage or "
    "amount that applies automatically), \"capped\" (increases allowed only up "
    "to a stated maximum), \"formula\" (tied to an external index/formula such "
    "as CPI), or \"unspecified\" (an increase is mentioned but the type or "
    "amount is not clear).\n"
    "- increase_percent is a NUMBER of percent (e.g. 3 for 3%). For a capped "
    "increase, increase_percent is the MAXIMUM permitted percent.\n"
    "- increase_amount is an absolute money amount ONLY if the contract states a "
    "fixed money increase instead of a percentage.\n"
    "- increase_formula is the verbatim formula/index text (e.g. \"CPI + 2%\").\n"
    "- price_change_date / objection_deadline_stated are ISO YYYY-MM-DD ONLY if "
    "an explicit calendar date is stated; otherwise null.\n"
    "- Every source quote is copied VERBATIM from the supplied chunk, max 400 "
    "characters, and must echo the chunk_id it came from.\n"
    "- Never output document_id, page number, section number, or char_offset — "
    "the server resolves those.\n"
    "- Every populated field must have a supporting source purpose. Repeat the "
    "SAME quote+chunk_id once per purpose when one clause supports several.\n"
    "- If there is no price/fee increase content at all, return "
    "{\"found\": false}.\n"
    "Schema when found:\n"
    "{\"found\": true, \"increase_type\": "
    "\"fixed_automatic|capped|formula|unspecified|null\", "
    "\"increase_percent\": number|null, \"increase_amount\": number|null, "
    "\"increase_formula\": str|null, \"increase_basis\": str|null, "
    "\"price_change_date\": \"YYYY-MM-DD|null\", "
    "\"objection_window_value\": int|null, \"objection_window_unit\": "
    "\"days|months|years|null\", \"objection_basis\": \"calendar|business|null\", "
    "\"objection_measured_to\": \"sent|received|unspecified|null\", "
    "\"objection_deadline_stated\": \"YYYY-MM-DD|null\", \"objection_recipient\": "
    "str|null, \"objection_method\": str|null, \"sources\": [{\"purpose\": "
    "\"increase|objection|effective_date|increase_basis|value\", \"chunk_id\": "
    "\"c_xx\", \"quote\": \"verbatim <=400 chars\"}], \"confidence\": "
    "\"high|medium|low\"}"
)


async def locate_price(chunks: list[dict]) -> list[str]:
    chat = _new_chat(LOCATE_PRICE_SYSTEM)
    prompt = (
        "Chunks:\n\n" + _render_chunks(chunks, include_text=False) +
        "\n\nReturn JSON {\"chunk_ids\": [...]} listing only chunks that may "
        "contain price/fee increase language."
    )
    resp = await chat.send_message(UserMessage(text=prompt))
    data = _parse_json(resp)
    ids = data.get("chunk_ids", []) if isinstance(data, dict) else []
    valid = {c["chunk_id"] for c in chunks}
    return [i for i in ids if i in valid]


async def extract_price(chunks: list[dict]) -> dict:
    chat = _new_chat(EXTRACT_PRICE_SYSTEM)
    prompt = (
        "Extract the price_increase finding from these chunks. Quote verbatim "
        "and echo chunk_ids.\n\n" + _render_chunks(chunks, include_text=True)
    )
    resp = await chat.send_message(UserMessage(text=prompt))
    return _parse_json(resp)


# --------------------------------------------------------------------------
# Stage 7C — termination_right
# --------------------------------------------------------------------------
LOCATE_TERMINATION_SYSTEM = (
    "You are a contract-analysis locator. You receive numbered chunks of a "
    "contract. Identify ONLY the chunks that may contain an EARLY-TERMINATION or "
    "TERMINATION-FOR-CONVENIENCE right: a right to terminate/cancel the agreement "
    "before its natural expiry (with or without cause), an early-exit or break "
    "right, the notice required to terminate, when termination takes effect, or a "
    "termination/early-exit fee. Do NOT select clauses that are only about "
    "non-renewal at the end of the term or ordinary expiry. Return STRICT JSON: "
    "{\"chunk_ids\": [\"c_01\", ...]}. Only possibly-relevant ids. No prose."
)

EXTRACT_TERMINATION_SYSTEM = (
    "You extract a single termination_right finding from the supplied contract "
    "chunks. Output STRICT JSON only, no prose.\n"
    "HARD RULES:\n"
    "- Extract ONLY an explicit right to terminate/cancel the agreement EARLY "
    "(termination for convenience or an early-exit/break right). NEVER infer a "
    "termination right from generic notice, non-renewal, or ordinary expiry "
    "language. If the text only covers non-renewal or expiry, return "
    "{\"found\": false}.\n"
    "- Anything not explicitly stated is null. Never infer, estimate, or "
    "reconstruct missing contract language. Do not invent notice periods, dates, "
    "fees, methods, or recipients.\n"
    "- termination_type must be one of: \"for_convenience\" (may terminate "
    "without cause), \"early_exit\" (a break/early-exit right on stated "
    "conditions), \"for_cause\" (only on breach/default), or \"unspecified\".\n"
    "- notice_period_value is a NUMBER with notice_period_unit days|months|years.\n"
    "- cure_period_value/cure_period_unit apply ONLY when the contract gives a "
    "period to remedy a breach before a for-cause termination takes effect; do "
    "not confuse it with the notice period.\n"
    "- termination_fee_stated is true ONLY if the contract explicitly states a "
    "fee/charge for terminating early; termination_fee_amount is an absolute "
    "money amount only if explicitly stated; termination_fee_percent only if the "
    "fee is stated as a percentage.\n"
    "- effective_date / earliest_termination_date are ISO YYYY-MM-DD ONLY if an "
    "explicit calendar date is stated; otherwise null.\n"
    "- Every source quote is copied VERBATIM from the supplied chunk, max 400 "
    "characters, and must echo the chunk_id it came from. Never output "
    "document_id, page number, section number, or char_offset.\n"
    "- Every populated field must have a supporting source purpose.\n"
    "Schema when found:\n"
    "{\"found\": true, \"termination_type\": "
    "\"for_convenience|early_exit|for_cause|unspecified|null\", "
    "\"who_may_terminate\": \"customer|supplier|either|null\", "
    "\"notice_period_value\": int|null, \"notice_period_unit\": "
    "\"days|months|years|null\", \"notice_basis\": \"calendar|business|null\", "
    "\"notice_measured_to\": \"sent|received|unspecified|null\", "
    "\"effective_date\": \"YYYY-MM-DD|null\", \"min_term_value\": int|null, "
    "\"min_term_unit\": \"days|months|years|null\", "
    "\"earliest_termination_date\": \"YYYY-MM-DD|null\", "
    "\"cure_period_value\": int|null, \"cure_period_unit\": "
    "\"days|months|years|null\", "
    "\"termination_fee_stated\": true|false, \"termination_fee_amount\": "
    "number|null, \"termination_fee_percent\": number|null, "
    "\"termination_fee_basis\": str|null, \"method\": str|null, \"recipient\": "
    "str|null, \"sources\": [{\"purpose\": \"termination_right|notice_period|"
    "effective_timing|cure_period|termination_fee|method\", \"chunk_id\": \"c_xx\", "
    "\"quote\": \"verbatim <=400 chars\"}], \"confidence\": \"high|medium|low\"}"
)


async def locate_termination(chunks: list[dict]) -> list[str]:
    chat = _new_chat(LOCATE_TERMINATION_SYSTEM)
    prompt = (
        "Chunks:\n\n" + _render_chunks(chunks, include_text=False) +
        "\n\nReturn JSON {\"chunk_ids\": [...]} listing only chunks that may "
        "contain an early-termination / termination-for-convenience right."
    )
    resp = await chat.send_message(UserMessage(text=prompt))
    data = _parse_json(resp)
    ids = data.get("chunk_ids", []) if isinstance(data, dict) else []
    valid = {c["chunk_id"] for c in chunks}
    return [i for i in ids if i in valid]


async def extract_termination(chunks: list[dict]) -> dict:
    chat = _new_chat(EXTRACT_TERMINATION_SYSTEM)
    prompt = (
        "Extract the termination_right finding from these chunks. Quote verbatim "
        "and echo chunk_ids.\n\n" + _render_chunks(chunks, include_text=True)
    )
    resp = await chat.send_message(UserMessage(text=prompt))
    return _parse_json(resp)


# --------------------------------------------------------------------------
# Stage 8/10 — shared obligations pipeline (6 additional finding types).
# One locate + one extract classify each detected clause into ONE of:
#   service_credit, invoice_dispute, notice_requirement, fee_or_penalty,
#   rebate_or_refund, warranty_claim. Returns a LIST of findings.
# --------------------------------------------------------------------------
LOCATE_OBLIGATIONS_SYSTEM = (
    "You are a contract-analysis locator. You receive numbered chunks of a "
    "contract. Identify ONLY the chunks that may contain language about any of "
    "these: (1) SERVICE CREDITS / SLA credits — a credit owed to the customer "
    "when a service level is missed; (2) INVOICE DISPUTE — a right or window to "
    "dispute, query, or withhold a disputed invoice; (3) NOTICE REQUIREMENT — a "
    "general formal-notice provision (how/where notices must be delivered, "
    "addresses, methods); (4) FEE OR PENALTY — a non-routine cost the customer "
    "can avoid by acting (e.g. paying) before a date, or by NOT acting (e.g. "
    "not terminating early) before a date — NOT the ordinary contract/"
    "subscription price, a price-increase/escalation clause, or a tax; "
    "(5) REBATE OR REFUND — a volume rebate, refund, or credit owed back; "
    "(6) WARRANTY CLAIM — a warranty and the window/process to make a "
    "warranty claim. Return STRICT JSON: "
    "{\"chunk_ids\": [\"c_01\", ...]}. Only possibly-relevant ids. No prose."
)

EXTRACT_OBLIGATIONS_SYSTEM = (
    "You extract obligation/right findings from the supplied contract chunks. "
    "Output STRICT JSON only, no prose. Return a LIST of findings — one per "
    "distinct clause you can ground in the text.\n"
    "HARD RULES:\n"
    "- Each finding's finding_type MUST be exactly one of: \"service_credit\", "
    "\"invoice_dispute\", \"notice_requirement\", \"fee_or_penalty\", "
    "\"rebate_or_refund\", \"warranty_claim\". If a clause fits none of these, "
    "do NOT emit it.\n"
    "- fee_or_penalty is ONLY a non-routine cost the customer can PREVENT by "
    "taking an action (e.g. paying by a date) or by RESTRAINING from an "
    "action (e.g. not terminating early) relative to a boundary date. Do NOT "
    "emit fee_or_penalty for: the ordinary contract/subscription/service "
    "price, recurring service charges, per-unit or usage rates, taxes, "
    "damages/indemnities/liability caps, a fee already incurred with no way "
    "to avoid it, a fee triggered by an event outside the customer's control, "
    "or any price-escalation/increase clause — that belongs to price_increase "
    "(a separate pipeline), never to fee_or_penalty. If in doubt, do not emit "
    "a fee_or_penalty finding.\n"
    "- For fee_or_penalty ONLY, timing_effect is REQUIRED (never null): "
    "\"deadline\" if the fee is avoided by acting/paying BEFORE the resolved "
    "boundary date; \"restriction_lifts\" if the fee/risk applies only until "
    "the boundary date and there is nothing to do — it simply ends after that "
    "date (the customer avoids it by NOT acting before then); \"unknown\" if "
    "the clause's timing polarity genuinely cannot be determined from the "
    "text. For every other finding_type, timing_effect is always null.\n"
    "- Anything not explicitly stated is null. NEVER infer, estimate, repair, or "
    "reconstruct missing contract language. Do not invent numbers, percentages, "
    "dates, windows, or parties.\n"
    "- amount is an absolute money amount ONLY if explicitly stated. "
    "amount_percent is a NUMBER of percent ONLY if a percentage is stated. "
    "rate_text is the verbatim rate phrase (e.g. \"1.5% per month\") ONLY if "
    "stated. NEVER calculate a dollar amount from a percentage or formula — "
    "if only a percentage/formula is stated, amount stays null and rate_text "
    "carries the verbatim rate/formula.\n"
    "- window_value + window_unit (days|months|years) capture a RELATIVE window "
    "(e.g. \"within 30 days\"). window_reference is the verbatim short phrase "
    "the window is measured from (e.g. \"the invoice date\", \"delivery\"). "
    "deadline_stated is an ISO YYYY-MM-DD ONLY if an explicit calendar date is "
    "stated. Never output trigger_date — the server/user provides it.\n"
    "- who is who benefits/must act: \"customer\", \"supplier\", \"either\", or "
    "null.\n"
    "- Every source quote is copied VERBATIM from the supplied chunk, max 400 "
    "characters, and must echo the chunk_id it came from. Never output "
    "document_id, page number, section number, or char_offset.\n"
    "- Every finding MUST include at least one source with purpose "
    "\"obligation\". Every populated field must have a supporting source "
    "purpose. Repeat the SAME quote+chunk_id once per purpose when one clause "
    "supports several.\n"
    "- If there is no relevant content at all, return {\"findings\": []}.\n"
    "Schema:\n"
    "{\"findings\": [{\"finding_type\": \"service_credit|invoice_dispute|"
    "notice_requirement|fee_or_penalty|rebate_or_refund|warranty_claim\", "
    "\"who\": \"customer|supplier|either|null\", \"amount\": number|null, "
    "\"amount_percent\": number|null, \"rate_text\": str|null, "
    "\"window_value\": int|null, \"window_unit\": \"days|months|years|null\", "
    "\"window_basis\": \"calendar|business|null\", \"window_reference\": "
    "str|null, \"deadline_stated\": \"YYYY-MM-DD|null\", \"timing_effect\": "
    "\"deadline|restriction_lifts|unknown|null\", \"sources\": "
    "[{\"purpose\": \"obligation|window|amount|party|method\", \"chunk_id\": "
    "\"c_xx\", \"quote\": \"verbatim <=400 chars\"}], \"confidence\": "
    "\"high|medium|low\"}]}"
)


async def locate_obligations(chunks: list[dict]) -> list[str]:
    chat = _new_chat(LOCATE_OBLIGATIONS_SYSTEM)
    prompt = (
        "Chunks:\n\n" + _render_chunks(chunks, include_text=False) +
        "\n\nReturn JSON {\"chunk_ids\": [...]} listing only chunks that may "
        "contain service-credit, invoice-dispute, notice-requirement, "
        "fee/penalty, rebate/refund, or warranty-claim language."
    )
    resp = await chat.send_message(UserMessage(text=prompt))
    data = _parse_json(resp)
    ids = data.get("chunk_ids", []) if isinstance(data, dict) else []
    valid = {c["chunk_id"] for c in chunks}
    return [i for i in ids if i in valid]


async def extract_obligations(chunks: list[dict]) -> list[dict]:
    chat = _new_chat(EXTRACT_OBLIGATIONS_SYSTEM)
    prompt = (
        "Extract the obligation/right findings from these chunks. Quote verbatim "
        "and echo chunk_ids.\n\n" + _render_chunks(chunks, include_text=True)
    )
    data = _parse_json(await chat.send_message(UserMessage(text=prompt)))
    if isinstance(data, dict):
        return data.get("findings", []) or []
    if isinstance(data, list):
        return data
    return []




EXPLAIN_SYSTEM = (
    "You write a plain-English explanation of a contract finding using "
    "ONLY the verbatim source quotes provided. STRICT RULES: do not add any "
    "legal conclusion, right, obligation, date, number, party, or recommendation "
    "that is not directly supported by the quotes. Do not infer or invent. If a "
    "detail is not in the quotes, do not state it. This is not legal advice.\n"
    "Return STRICT JSON: {\"plain_english\": str, \"why_it_matters\": str, "
    "\"suggested_action\": str}. Each value is 1-3 short factual sentences."
)


async def explain(sources: list[dict], facts: dict) -> dict:
    chat = _new_chat(EXPLAIN_SYSTEM)
    quotes = "\n".join(f"[{s.get('purpose')}] \"{s.get('quote')}\"" for s in sources)
    prompt = (
        "Server-computed facts (already derived from these same validated "
        f"clauses; you may reference them, do not add others): {facts}\n\n"
        f"Validated source quotes (your ONLY basis):\n{quotes}\n\n"
        "Write the JSON explanation."
    )
    return _parse_json(await chat.send_message(UserMessage(text=prompt)))


DRAFT_SYSTEM = (
    "You draft a NON-RENEWAL notice letter for a customer to send to a vendor, "
    "using ONLY the provided validated contract quotes and server-computed "
    "facts. STRICT RULES: use only the recipient, method, and timing given; do "
    "NOT invent addresses, dates, names, or clause references not provided; use "
    "clearly bracketed placeholders like [Your Name], [Your Company], [Date] "
    "for anything not provided. Do NOT assert legal validity, compliance, or "
    "that the notice satisfies any requirement. Do NOT give legal advice. "
    "Return PLAIN TEXT only (no JSON, no markdown), a ready-to-edit letter that "
    "states the sender does not intend to renew and references the contract's "
    "own notice terms as quoted."
)


async def draft_notice(sources: list[dict], facts: dict) -> str:
    chat = _new_chat(DRAFT_SYSTEM)
    quotes = "\n".join(f"[{s.get('purpose')}] \"{s.get('quote')}\"" for s in sources)
    prompt = (
        f"Server-computed facts: {facts}\n\n"
        f"Validated contract quotes (your ONLY basis):\n{quotes}\n\n"
        "Draft the non-renewal notice letter as plain text with bracketed "
        "placeholders for anything not provided."
    )
    return (await chat.send_message(UserMessage(text=prompt))).strip()
