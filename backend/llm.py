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
