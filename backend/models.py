"""
ClauseClock data models — Prompt 0 scaffolding.

These Pydantic models mirror the collections defined in PART 1.1 of the
specification exactly. No Stage 1+ behaviour (extraction, analysis, ranking,
explanation, reminders, drafting) is implemented here — only the shapes that
those later stages will read from and write to.

Conventions:
- ObjectId (BSON) is never returned raw. `PyObjectId` coerces ObjectId -> str.
- All documents extend `BaseDocument`, which maps `_id` <-> `id` and provides
  `from_mongo()` / `to_mongo()` helpers.
- Contractual dates are ISO `YYYY-MM-DD` calendar STRINGS. They are never
  BSON dates and never timezone-converted. A deadline is a calendar day.
- Server timestamps (created_at, uploaded_at, logged_at ...) are stored as
  ISO 8601 strings in UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _validate_object_id(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        return v
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[str, BeforeValidator(_validate_object_id)]


def utc_now_iso() -> str:
    """Server timestamp as an ISO 8601 UTC string."""
    return datetime.now(timezone.utc).isoformat()


class BaseDocument(BaseModel):
    """Base for every persisted document. Maps Mongo `_id` to `id`."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc: Optional[Dict[str, Any]]):
        if doc is None:
            return None
        return cls(**doc)

    def to_mongo(self, *, exclude_none: bool = False) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=exclude_none)
        # Let Mongo generate _id on insert when we have not set one.
        if data.get("_id") is None:
            data.pop("_id", None)
        return data


# ---------------------------------------------------------------------------
# users  (PART 1.1)
# ---------------------------------------------------------------------------
class User(BaseDocument):
    """
    user_id is ALWAYS derived from the authenticated session server-side and
    NEVER accepted from the client. Every query in every collection is scoped
    by it.
    """

    email: str
    password_hash: str
    created_at: str = Field(default_factory=utc_now_iso)


# ---------------------------------------------------------------------------
# contracts  (PART 1.1)
# ---------------------------------------------------------------------------
class Contract(BaseDocument):
    user_id: PyObjectId

    name: str
    counterparty: Optional[str] = None
    annual_value: Optional[float] = None
    currency: Optional[str] = None

    value_source: Optional[Literal["extracted", "user_entered"]] = None
    # required when value_source == "extracted"
    value_source_quote: Optional[str] = None
    value_source_document_id: Optional[PyObjectId] = None
    value_source_location: Optional[str] = None
    value_source_char_offset: Optional[int] = None

    status: Literal["processing", "analysed", "failed"] = "processing"
    primary_document_id: Optional[PyObjectId] = None
    last_analysed_at: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)


# ---------------------------------------------------------------------------
# documents  (PART 1.1)
# ---------------------------------------------------------------------------
class Document(BaseDocument):
    contract_id: PyObjectId
    user_id: PyObjectId

    filename: str
    file_type: Literal["pdf", "docx"]
    storage_key: Optional[str] = None          # path/key of the stored original
    sha256: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None

    doc_role: Literal["primary", "amendment", "order_form", "exhibit", "sla"] = "primary"
    effective_date: Optional[str] = None        # ISO YYYY-MM-DD

    page_count: Optional[int] = None
    raw_text: Optional[str] = None

    extraction_method: Optional[str] = None
    extraction_warnings: List[str] = Field(default_factory=list)
    supersedes_document_ids: List[PyObjectId] = Field(default_factory=list)

    uploaded_at: str = Field(default_factory=utc_now_iso)
    # Note: chunks (chunk_id, document_id, char_start, char_end, marker) are
    # held transiently during analysis and are NOT persisted.


# ---------------------------------------------------------------------------
# findings  (PART 1.1 / 1.2 / 1.2a-c)
# ---------------------------------------------------------------------------
FindingType = Literal[
    "renewal_notice",
    "termination_right",
    "price_increase",
    "service_credit",
    "invoice_dispute",
    "rebate_or_refund",
    "warranty_claim",
    "fee_or_penalty",
    "notice_requirement",
]


class FindingSource(BaseModel):
    """
    Provenance entry. `sources[]` is never empty. Document identity comes from
    `chunk_id` (resolved server-side), NEVER from the model. Each entry names
    which part of the finding it supports via `purpose`.
    """

    purpose: str                       # shared + type-specific purposes (1.2a)
    chunk_id: str                      # echoed by the model
    document_id: Optional[PyObjectId] = None  # resolved server-side FROM chunk_id
    quote: str = Field(max_length=400)        # verbatim, max 400 chars
    location: Optional[str] = None            # "Page 12" / "Section 8.2"
    char_offset: Optional[int] = None


class Finding(BaseDocument):
    contract_id: PyObjectId
    user_id: PyObjectId

    type: FindingType
    extracted: Dict[str, Any] = Field(default_factory=dict)  # polymorphic per type

    # provenance — array, never empty (1.2a)
    sources: List[FindingSource] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"

    # normalised layer — derived server-side from `extracted`, never by model (1.2b)
    action_required: bool = False
    money_amount: Optional[float] = None
    money_currency: Optional[str] = None
    money_kind: Optional[
        Literal["cost", "saving_opportunity", "credit", "contract_value"]
    ] = None

    # ranking — computed server-side (1.3)
    rank_category: Literal[
        "urgent", "money", "risk", "opportunity", "informational"
    ] = "informational"
    rank_score: int = 0
    rank_basis: Dict[str, Any] = Field(default_factory=dict)  # inputs incl. as_of_date

    # explanation — from validated sources[].quote only (1.4)
    plain_english: Optional[str] = None
    why_it_matters: Optional[str] = None
    suggested_action: Optional[str] = None
    explanation_generated_at: Optional[str] = None

    # dual status axes — never collapse these (1.2)
    validation_status: Literal["validated", "needs_review"] = "needs_review"
    validation_notes: List[str] = Field(default_factory=list)
    state: Literal["unconfirmed", "confirmed", "corrected", "dismissed"] = "unconfirmed"

    original_values: Dict[str, Any] = Field(default_factory=dict)
    corrected_fields: List[str] = Field(default_factory=list)
    confirmed_at: Optional[str] = None
    superseded_by_finding_id: Optional[PyObjectId] = None

    related_finding_ids: List[PyObjectId] = Field(default_factory=list)  # (1.2c)
    is_composite: bool = False
    composite_of: List[PyObjectId] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)


# ---------------------------------------------------------------------------
# actions  (PART 1.1)
# ---------------------------------------------------------------------------
class Action(BaseDocument):
    finding_id: PyObjectId
    contract_id: PyObjectId
    user_id: PyObjectId

    action_type: Literal[
        "notice_sent", "objection_sent", "claim_submitted", "dispute_raised"
    ]
    sent_date: str                     # ISO YYYY-MM-DD string
    delivery_method: Optional[str] = None
    method_matches_contract: Optional[bool] = None
    evidence_files: List[str] = Field(default_factory=list)
    evidence_sha256: List[str] = Field(default_factory=list)
    logged_at: str = Field(default_factory=utc_now_iso)  # server timestamp


# ---------------------------------------------------------------------------
# outcomes  (PART 1.1)
# ---------------------------------------------------------------------------
class Outcome(BaseDocument):
    finding_id: PyObjectId
    contract_id: PyObjectId
    user_id: PyObjectId

    result: Literal[
        "terminated",
        "renegotiated",
        "credit_received",
        "dispute_resolved",
        "reviewed_and_kept",
        "missed",
    ]
    confirmed: bool = False
    confirmation_evidence_file: Optional[str] = None
    term_value_avoided: Optional[float] = None
    term_length_months: Optional[int] = None
    renegotiated_annual_delta: Optional[float] = None
    amount_recovered: Optional[float] = None
    notes: Optional[str] = None
    recorded_at: str = Field(default_factory=utc_now_iso)


# ---------------------------------------------------------------------------
# reminders  (PART 1.1)
# ---------------------------------------------------------------------------
class Reminder(BaseDocument):
    finding_id: PyObjectId
    user_id: PyObjectId

    fire_date: str                     # ISO YYYY-MM-DD string
    days_before: Optional[int] = None
    sent: bool = False
    sent_at: Optional[str] = None


# Registry consumed by index setup / meta endpoint.
COLLECTIONS: Dict[str, type] = {
    "users": User,
    "contracts": Contract,
    "documents": Document,
    "findings": Finding,
    "actions": Action,
    "outcomes": Outcome,
    "reminders": Reminder,
}
