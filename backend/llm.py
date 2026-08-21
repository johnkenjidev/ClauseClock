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
    "\"sources\": [{\"purpose\": \"effective_date|renewal_term|notice_period|"
    "notice_method|notice_recipient|business_day_definition|deemed_receipt|"
    "value\", \"chunk_id\": \"c_xx\", \"quote\": \"verbatim <=400 chars\"}], "
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
    "\"termination_fee_stated\": true|false, \"termination_fee_amount\": "
    "number|null, \"termination_fee_percent\": number|null, "
    "\"termination_fee_basis\": str|null, \"method\": str|null, \"recipient\": "
    "str|null, \"sources\": [{\"purpose\": \"termination_right|notice_period|"
    "effective_timing|termination_fee|method\", \"chunk_id\": \"c_xx\", "
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
