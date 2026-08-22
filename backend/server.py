"""
ClauseClock backend — Stage 1 (contract ingestion).

Implemented: session auth (JWT httpOnly cookies), contract create + document
upload, PDF/DOCX text extraction with location markers, scanned-document
detection, annual-value provenance (user_entered only), and real hard deletion.

NOT implemented (Stage 2+ boundary): AI clause extraction, renewal detection,
findings, deadline computation, analysis chunking, ranking, explanations,
Confirm/Correct/Dismiss, reminders, drafting, outcomes, Action Center logic,
dashboard metrics, populated /demo data.
"""

import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import (APIRouter, Body, Depends, FastAPI, File, Form, HTTPException,
                     Request, Response, UploadFile)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pydantic import BaseModel, EmailStr, ValidationError, field_validator
from pymongo.errors import DuplicateKeyError
from starlette.middleware.cors import CORSMiddleware

import auth
import ingestion
import analysis
from models import (COLLECTIONS, Contract, Document, User, utc_now_iso)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]
bucket = AsyncIOMotorGridFSBucket(db)

app = FastAPI(title="ClauseClock")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("clauseclock")

TEST_USER = {"email": "test@clauseclock.app", "password": "Test1234!"}


# --------------------------------------------------------------------------
# Auth dependency — user_id is ALWAYS derived here, never from the client.
# --------------------------------------------------------------------------
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = auth.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    except auth.jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (auth.jwt.InvalidTokenError, InvalidId):
        raise HTTPException(status_code=401, detail="Invalid token")
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"id": str(user["_id"]), "email": user["email"], "created_at": user.get("created_at")}


def current_user_id(user: dict = Depends(get_current_user)) -> str:
    return user["id"]


# --------------------------------------------------------------------------
# Auth request models
# --------------------------------------------------------------------------
class Credentials(BaseModel):
    email: EmailStr
    password: str


def _public_user(user_doc: dict) -> dict:
    return {"id": str(user_doc["_id"]), "email": user_doc["email"],
            "created_at": user_doc.get("created_at")}


async def _issue_session(response: Response, user_id: str, email: str) -> None:
    auth.set_auth_cookies(
        response,
        auth.create_access_token(user_id, email),
        auth.create_refresh_token(user_id),
    )


# --------------------------------------------------------------------------
# Auth endpoints
# --------------------------------------------------------------------------
@api_router.post("/auth/register")
async def register(body: Credentials, response: Response):
    email = body.email.lower().strip()
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    doc = User(email=email, password_hash=auth.hash_password(body.password)).to_mongo()
    try:
        result = await db.users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    doc["_id"] = result.inserted_id
    await _issue_session(response, str(result.inserted_id), email)
    return _public_user(doc)


@api_router.post("/auth/login")
async def login(body: Credentials, response: Response):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not auth.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    await _issue_session(response, str(user["_id"]), email)
    return _public_user(user)


@api_router.post("/auth/logout")
async def logout(response: Response):
    auth.clear_auth_cookies(response)
    return {"ok": True}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# --------------------------------------------------------------------------
# Contract / document helpers
# --------------------------------------------------------------------------
DOC_ROLES = {"primary", "amendment", "order_form", "exhibit", "sla"}


def _resolve_file_type(filename: str, content_type: Optional[str]) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf") or content_type == "application/pdf":
        return "pdf"
    if name.endswith(".docx") or content_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return "docx"
    raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")


async def _oid(user_id: str, contract_id: str) -> ObjectId:
    try:
        return ObjectId(contract_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Contract not found.")


async def _ingest_document(contract_id: str, user_id: str, file: UploadFile,
                           doc_role: str) -> Document:
    if doc_role not in DOC_ROLES:
        raise HTTPException(status_code=400, detail="Invalid document role.")
    file_type = _resolve_file_type(file.filename, file.content_type)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    storage_key = await ingestion.store_original(
        bucket, data, file.filename, file.content_type or "application/octet-stream"
    )
    raw_text, page_count = await asyncio.to_thread(ingestion.extract_text, data, file_type)

    scanned = ingestion.is_scanned(raw_text, page_count)
    if scanned:
        extraction_method = "failed_no_text"
        warnings = [ingestion.SCANNED_MESSAGE]
    else:
        extraction_method = "pdfplumber" if file_type == "pdf" else "python-docx"
        warnings = []

    document = Document(
        contract_id=contract_id, user_id=user_id, filename=file.filename,
        file_type=file_type, storage_key=storage_key,
        sha256=ingestion.sha256_hex(data),
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(data), doc_role=doc_role, page_count=page_count,
        raw_text=raw_text, extraction_method=extraction_method,
        extraction_warnings=warnings,
    )
    result = await db.documents.insert_one(document.to_mongo())
    document.id = str(result.inserted_id)
    return document


# --------------------------------------------------------------------------
# Contract endpoints (every query scoped by the session user_id)
# --------------------------------------------------------------------------
@api_router.post("/contracts")
async def create_contract(
    file: UploadFile = File(...),
    name: str = Form(...),
    counterparty: Optional[str] = Form(None),
    doc_role: str = Form("primary"),
    annual_value: Optional[str] = Form(None),
    currency: Optional[str] = Form(None),
    user_id: str = Depends(current_user_id),
):
    av = None
    value_source = None
    cur = None
    if annual_value not in (None, "", "null"):
        try:
            av = float(annual_value)
        except ValueError:
            raise HTTPException(status_code=400, detail="Annual value must be a number.")
        value_source = "user_entered"           # provenance: user-entered only (Stage 1)
        cur = (currency or "").strip() or None

    contract = Contract(
        user_id=user_id, name=name.strip(), counterparty=(counterparty or "").strip() or None,
        annual_value=av, currency=cur, value_source=value_source, status="processing",
    )
    result = await db.contracts.insert_one(contract.to_mongo())
    contract.id = str(result.inserted_id)

    document = await _ingest_document(contract.id, user_id, file, doc_role)
    if document.doc_role == "primary":
        await db.contracts.update_one(
            {"_id": result.inserted_id, "user_id": user_id},
            {"$set": {"primary_document_id": document.id}},
        )
        contract.primary_document_id = document.id

    return {"contract": contract.model_dump(),
            "document": document.model_dump()}


@api_router.get("/contracts")
async def list_contracts(user_id: str = Depends(current_user_id)):
    cursor = db.contracts.find({"user_id": user_id}).sort("created_at", -1)
    out = []
    async for doc in cursor:
        c = Contract.from_mongo(doc)
        doc_count = await db.documents.count_documents(
            {"contract_id": c.id, "user_id": user_id}
        )
        entry = c.model_dump()
        entry["document_count"] = doc_count
        out.append(entry)
    return {"contracts": out}


@api_router.get("/contracts/{contract_id}")
async def get_contract(contract_id: str, user_id: str = Depends(current_user_id)):
    oid = await _oid(user_id, contract_id)
    doc = await db.contracts.find_one({"_id": oid, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Contract not found.")
    contract = Contract.from_mongo(doc)

    documents = []
    async for d in db.documents.find(
        {"contract_id": contract_id, "user_id": user_id}
    ).sort("uploaded_at", 1):
        documents.append(Document.from_mongo(d).model_dump())

    return {"contract": contract.model_dump(), "documents": documents}


@api_router.post("/contracts/{contract_id}/documents")
async def add_document(
    contract_id: str,
    file: UploadFile = File(...),
    doc_role: str = Form(...),
    user_id: str = Depends(current_user_id),
):
    oid = await _oid(user_id, contract_id)
    contract = await db.contracts.find_one({"_id": oid, "user_id": user_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")
    document = await _ingest_document(contract_id, user_id, file, doc_role)
    return {"document": document.model_dump()}


@api_router.post("/contracts/{contract_id}/analyze")
async def analyze_contract(contract_id: str, user_id: str = Depends(current_user_id)):
    """Stage 2: run renewal_notice extraction over the contract's documents."""
    oid = await _oid(user_id, contract_id)
    contract = await db.contracts.find_one({"_id": oid, "user_id": user_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    readable = await db.documents.count_documents({
        "contract_id": contract_id, "user_id": user_id,
        "extraction_method": {"$ne": "failed_no_text"},
    })
    if readable == 0:
        raise HTTPException(status_code=400,
                            detail="No readable documents to analyse.")

    findings, warnings = await analysis.run_renewal_analysis(db, contract, user_id)
    price_findings, price_warnings = await analysis.run_price_increase_analysis(
        db, contract, user_id)
    term_findings, term_warnings = await analysis.run_termination_analysis(
        db, contract, user_id)
    obl_findings, obl_warnings = await analysis.run_obligations_analysis(
        db, contract, user_id)

    # Stage 9: reconcile regenerated findings against preserved reviewed ones.
    # If a reviewed finding changed, keep it and point superseded_by at the new
    # (unconfirmed) replacement; if unchanged, drop the duplicate replacement.
    superseded_changes = 0
    for ftype in (["renewal_notice", "price_increase", "termination_right"]
                  + analysis.GENERIC_TYPES):
        reviewed = await db.findings.find_one({
            "contract_id": contract_id, "user_id": user_id, "type": ftype,
            "state": {"$in": ["confirmed", "corrected"]},
            "superseded_by_finding_id": None})
        if not reviewed:
            continue
        replacement = await db.findings.find_one({
            "contract_id": contract_id, "user_id": user_id, "type": ftype,
            "state": "unconfirmed"})
        if not replacement:
            continue
        if (reviewed.get("extracted") or {}) == (replacement.get("extracted") or {}):
            await db.findings.delete_one({"_id": replacement["_id"]})  # no change
        else:
            await db.findings.update_one(
                {"_id": reviewed["_id"], "user_id": user_id},
                {"$set": {"superseded_by_finding_id": str(replacement["_id"])}})
            superseded_changes += 1

    await analysis.refresh_rate_shock_composite(db, contract, user_id)
    from models import Finding
    allf = [Finding.from_mongo(f).model_dump()
            async for f in db.findings.find({"contract_id": contract_id, "user_id": user_id})
            if not f.get("superseded_by_finding_id")]
    findings = analysis.apply_ranking(allf)
    await db.contracts.update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": {"status": "analysed", "last_analysed_at": utc_now_iso()}})
    return {"findings": findings, "superseded_changes": superseded_changes,
            "warnings": warnings + price_warnings + term_warnings + obl_warnings}


@api_router.get("/contracts/{contract_id}/findings")
async def list_findings(contract_id: str, user_id: str = Depends(current_user_id)):
    oid = await _oid(user_id, contract_id)
    contract = await db.contracts.find_one({"_id": oid, "user_id": user_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")
    from models import Finding
    findings = []
    superseded_count = 0
    async for f in db.findings.find({"contract_id": contract_id, "user_id": user_id}):
        if f.get("superseded_by_finding_id"):
            superseded_count += 1
            continue
        findings.append(Finding.from_mongo(f).model_dump())
    findings = analysis.apply_ranking(findings)  # refresh time-dependent rank on read
    return {"findings": findings, "status": contract.get("status"),
            "superseded_count": superseded_count}


# ---- Stage 3: Confirm / Correct / Dismiss --------------------------------
_UNITS = {None, "day", "days", "month", "months", "year", "years"}


class CorrectionInput(BaseModel):
    effective_date: Optional[str] = None
    initial_term_value: Optional[int] = None
    initial_term_unit: Optional[str] = None
    renewal_type: Optional[str] = None
    renewal_period_value: Optional[int] = None
    renewal_period_unit: Optional[str] = None
    notice_days_min: Optional[int] = None
    notice_days_max: Optional[int] = None
    notice_basis: Optional[str] = None
    business_day_definition: Optional[str] = None
    notice_measured_to: Optional[str] = None
    deemed_receipt_rule: Optional[str] = None
    notice_method: Optional[str] = None
    notice_recipient: Optional[str] = None
    notice_anchor_type: Optional[str] = None

    @field_validator("notice_anchor_type")
    @classmethod
    def _valid_anchor(cls, v):
        if v not in (None, "term_end", "renewal_start", "unknown"):
            raise ValueError("invalid notice_anchor_type")
        return v

    @field_validator("effective_date")
    @classmethod
    def _valid_date(cls, v):
        if v in (None, ""):
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("effective_date must be YYYY-MM-DD")
        return v

    @field_validator("initial_term_unit", "renewal_period_unit")
    @classmethod
    def _valid_unit(cls, v):
        if v not in _UNITS:
            raise ValueError("unit must be days/months/years")
        return v

    @field_validator("renewal_type")
    @classmethod
    def _valid_rt(cls, v):
        if v not in (None, "automatic", "manual", "none"):
            raise ValueError("invalid renewal_type")
        return v

    @field_validator("notice_basis")
    @classmethod
    def _valid_basis(cls, v):
        if v not in (None, "calendar", "business"):
            raise ValueError("invalid notice_basis")
        return v

    @field_validator("notice_measured_to")
    @classmethod
    def _valid_measured(cls, v):
        if v not in (None, "sent", "received", "unspecified"):
            raise ValueError("invalid notice_measured_to")
        return v

    @field_validator("initial_term_value", "renewal_period_value",
                     "notice_days_min", "notice_days_max")
    @classmethod
    def _non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v


class PriceCorrectionInput(BaseModel):
    increase_type: Optional[str] = None
    increase_percent: Optional[float] = None
    increase_amount: Optional[float] = None
    increase_formula: Optional[str] = None
    increase_basis: Optional[str] = None
    price_change_date: Optional[str] = None
    objection_window_value: Optional[int] = None
    objection_window_unit: Optional[str] = None
    objection_basis: Optional[str] = None
    objection_measured_to: Optional[str] = None
    objection_deadline_stated: Optional[str] = None
    objection_recipient: Optional[str] = None
    objection_method: Optional[str] = None

    @field_validator("increase_type")
    @classmethod
    def _valid_itype(cls, v):
        if v not in (None, "fixed_automatic", "capped", "formula", "unspecified"):
            raise ValueError("invalid increase_type")
        return v

    @field_validator("increase_percent", "increase_amount")
    @classmethod
    def _non_neg_money(cls, v):
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v

    @field_validator("objection_window_value")
    @classmethod
    def _non_neg_window(cls, v):
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v

    @field_validator("objection_window_unit")
    @classmethod
    def _valid_window_unit(cls, v):
        if v not in _UNITS:
            raise ValueError("unit must be days/months/years")
        return v

    @field_validator("objection_basis")
    @classmethod
    def _valid_obj_basis(cls, v):
        if v not in (None, "calendar", "business"):
            raise ValueError("invalid objection_basis")
        return v

    @field_validator("objection_measured_to")
    @classmethod
    def _valid_obj_measured(cls, v):
        if v not in (None, "sent", "received", "unspecified"):
            raise ValueError("invalid objection_measured_to")
        return v

    @field_validator("price_change_date", "objection_deadline_stated")
    @classmethod
    def _valid_price_date(cls, v):
        if v in (None, ""):
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be YYYY-MM-DD")
        return v


class TerminationCorrectionInput(BaseModel):
    termination_type: Optional[str] = None
    who_may_terminate: Optional[str] = None
    notice_period_value: Optional[int] = None
    notice_period_unit: Optional[str] = None
    notice_basis: Optional[str] = None
    notice_measured_to: Optional[str] = None
    effective_date: Optional[str] = None
    min_term_value: Optional[int] = None
    min_term_unit: Optional[str] = None
    earliest_termination_date: Optional[str] = None
    cure_period_value: Optional[int] = None
    cure_period_unit: Optional[str] = None
    termination_fee_stated: Optional[bool] = None
    termination_fee_amount: Optional[float] = None
    termination_fee_percent: Optional[float] = None
    termination_fee_basis: Optional[str] = None
    method: Optional[str] = None
    recipient: Optional[str] = None

    @field_validator("termination_type")
    @classmethod
    def _valid_ttype(cls, v):
        if v not in (None, "for_convenience", "early_exit", "for_cause", "unspecified"):
            raise ValueError("invalid termination_type")
        return v

    @field_validator("who_may_terminate")
    @classmethod
    def _valid_who(cls, v):
        if v not in (None, "customer", "supplier", "either"):
            raise ValueError("invalid who_may_terminate")
        return v

    @field_validator("notice_period_unit", "min_term_unit")
    @classmethod
    def _valid_t_unit(cls, v):
        if v not in _UNITS:
            raise ValueError("unit must be days/months/years")
        return v

    @field_validator("cure_period_unit")
    @classmethod
    def _valid_cure_unit(cls, v):
        if v not in _UNITS:
            raise ValueError("unit must be days/months/years")
        return v

    @field_validator("notice_period_value", "min_term_value", "cure_period_value")
    @classmethod
    def _non_neg_t(cls, v):
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v

    @field_validator("notice_basis")
    @classmethod
    def _valid_t_basis(cls, v):
        if v not in (None, "calendar", "business"):
            raise ValueError("invalid notice_basis")
        return v

    @field_validator("notice_measured_to")
    @classmethod
    def _valid_t_measured(cls, v):
        if v not in (None, "sent", "received", "unspecified"):
            raise ValueError("invalid notice_measured_to")
        return v

    @field_validator("termination_fee_amount", "termination_fee_percent")
    @classmethod
    def _non_neg_fee(cls, v):
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v

    @field_validator("effective_date", "earliest_termination_date")
    @classmethod
    def _valid_t_date(cls, v):
        if v in (None, ""):
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be YYYY-MM-DD")
        return v


class GenericCorrectionInput(BaseModel):
    who: Optional[str] = None
    amount: Optional[float] = None
    amount_percent: Optional[float] = None
    rate_text: Optional[str] = None
    window_value: Optional[int] = None
    window_unit: Optional[str] = None
    window_basis: Optional[str] = None
    window_reference: Optional[str] = None
    trigger_date: Optional[str] = None
    deadline_stated: Optional[str] = None

    @field_validator("who")
    @classmethod
    def _valid_g_who(cls, v):
        if v not in (None, "customer", "supplier", "either"):
            raise ValueError("invalid who")
        return v

    @field_validator("window_unit")
    @classmethod
    def _valid_g_unit(cls, v):
        if v not in _UNITS:
            raise ValueError("unit must be days/months/years")
        return v

    @field_validator("window_basis")
    @classmethod
    def _valid_g_basis(cls, v):
        if v not in (None, "calendar", "business"):
            raise ValueError("invalid window_basis")
        return v

    @field_validator("amount", "amount_percent")
    @classmethod
    def _non_neg_g_money(cls, v):
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v

    @field_validator("window_value")
    @classmethod
    def _non_neg_g_window(cls, v):
        if v is not None and v < 0:
            raise ValueError("value must be >= 0")
        return v

    @field_validator("trigger_date", "deadline_stated")
    @classmethod
    def _valid_g_date(cls, v):
        if v in (None, ""):
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be YYYY-MM-DD")
        return v


async def _get_finding(finding_id: str, user_id: str):
    try:
        oid = ObjectId(finding_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Finding not found.")
    doc = await db.findings.find_one({"_id": oid, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return oid, doc


async def _refresh_composite_for(doc: dict, user_id: str):
    """Recompute/remove the rate-shock composite after a constituent changes."""
    if doc.get("type") not in ("renewal_notice", "price_increase"):
        return
    contract = await db.contracts.find_one(
        {"_id": ObjectId(doc["contract_id"]), "user_id": user_id})
    if contract:
        await analysis.refresh_rate_shock_composite(db, contract, user_id)


@api_router.post("/findings/{finding_id}/confirm")
async def confirm_finding(finding_id: str, user_id: str = Depends(current_user_id)):
    from models import Finding
    oid, doc = await _get_finding(finding_id, user_id)
    await db.findings.update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": {"state": "confirmed", "confirmed_at": utc_now_iso()}})
    await _refresh_composite_for(doc, user_id)
    return {"finding": Finding.from_mongo(
        await db.findings.find_one({"_id": oid, "user_id": user_id})).model_dump()}


def _apply_anchor_provenance(update: dict, prev: dict, sources: list) -> None:
    """Preserve notice-anchor provenance on a renewal Correct.

    If the user changed the anchor away from what was extracted, mark the current
    anchor as user-asserted, keep the original extracted anchor type + quote as
    prior-extraction provenance (audit/history), stop presenting that quote as
    support for the new anchor (demote the source purpose so the clause drawer no
    longer treats it as current evidence), and clear the current anchor quote.
    If the anchor is unchanged, keep the document-derived provenance intact.
    Uses only the existing extracted/sources model — no separate history store."""
    ext = update["extracted"]
    src_list = [dict(s) for s in (sources or [])]
    anchor_src = next((s for s in src_list
                       if s.get("purpose") in ("notice_anchor", "notice_anchor_prior")), None)
    prev_anchor = prev.get("notice_anchor_type")
    new_anchor = ext.get("notice_anchor_type")

    if new_anchor != prev_anchor:
        # User override — record as user-set and preserve the original extraction.
        ext["notice_anchor_origin"] = "user"
        ext["notice_anchor_extracted_type"] = (
            prev.get("notice_anchor_extracted_type") or prev_anchor)
        ext["notice_anchor_extracted_quote"] = (
            prev.get("notice_anchor_extracted_quote")
            or prev.get("notice_anchor_quote")
            or (anchor_src.get("quote") if anchor_src else None))
        ext["notice_anchor_extracted_location"] = (
            prev.get("notice_anchor_extracted_location")
            or prev.get("notice_anchor_location")
            or (anchor_src.get("location") if anchor_src else None))
        # No current supporting quote for a user assertion.
        ext["notice_anchor_quote"] = None
        ext["notice_anchor_location"] = None
        # Demote the extracted anchor source: kept for audit, not current support.
        demoted = False
        for s in src_list:
            if s.get("purpose") == "notice_anchor":
                s["purpose"] = "notice_anchor_prior"
                demoted = True
        if demoted:
            update["sources"] = src_list
    else:
        # Anchor unchanged — keep document-derived provenance visible.
        ext["notice_anchor_origin"] = prev.get("notice_anchor_origin") or "document"
        if anchor_src and anchor_src.get("purpose") == "notice_anchor":
            ext["notice_anchor_quote"] = anchor_src.get("quote")
            ext["notice_anchor_location"] = anchor_src.get("location")
        for k in ("notice_anchor_extracted_type", "notice_anchor_extracted_quote",
                  "notice_anchor_extracted_location"):
            if prev.get(k) is not None:
                ext[k] = prev.get(k)


@api_router.post("/findings/{finding_id}/correct")
async def correct_finding(finding_id: str, body: dict = Body(default={}),
                          user_id: str = Depends(current_user_id)):
    from models import Finding
    oid, doc = await _get_finding(finding_id, user_id)
    ftype = doc.get("type")
    if ftype == "renewal_with_escalation":
        raise HTTPException(status_code=400,
                            detail="Composite findings are derived; correct their renewal or price-increase constituents instead.")
    prev = doc.get("extracted", {}) or {}

    try:
        if ftype == "price_increase":
            edits = PriceCorrectionInput(**body).model_dump()
            editable = analysis.PRICE_EDITABLE_FIELDS
            contract = await db.contracts.find_one(
                {"_id": ObjectId(doc["contract_id"]), "user_id": user_id})
            cav = contract.get("annual_value") if contract else None
            recomputed = analysis.recompute_price_derived(edits, cav)
        elif ftype == "termination_right":
            edits = TerminationCorrectionInput(**body).model_dump()
            editable = analysis.TERMINATION_EDITABLE_FIELDS
            recomputed = analysis.recompute_termination_derived(edits)
        elif ftype in analysis.GENERIC_TYPES:
            edits = GenericCorrectionInput(**body).model_dump()
            editable = analysis.GENERIC_EDITABLE_FIELDS
            recomputed = analysis.recompute_generic_derived(edits, ftype)
        else:
            edits = CorrectionInput(**body).model_dump()
            editable = analysis.EDITABLE_FIELDS
            recomputed = analysis.recompute_derived(edits)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    # Record only fields that actually changed.
    changed = [k for k in editable if edits.get(k) != prev.get(k)]

    # No-change save is a true no-op.
    if not changed:
        return {"finding": Finding.from_mongo(doc).model_dump(),
                "changed_fields": [], "no_change": True}

    update = {
        "extracted": recomputed["extracted"],
        "validation_status": recomputed["validation_status"],
        "validation_notes": recomputed["validation_notes"],
        "action_required": recomputed["action_required"],
        "state": "corrected",
        "confirmed_at": utc_now_iso(),
    }
    if "money_amount" in recomputed:
        update["money_amount"] = recomputed["money_amount"]
        update["money_kind"] = recomputed["money_kind"]
    # Correcting a renewal applies the current anchor classification version.
    if ftype == "renewal_notice":
        update["anchor_version"] = analysis.ANCHOR_VERSION
        _apply_anchor_provenance(update, prev, doc.get("sources", []))
    # Snapshot the original (AI) values once; accumulate changed field names.
    if not doc.get("original_values"):
        update["original_values"] = {k: prev.get(k) for k in editable}
    prior_corrected = doc.get("corrected_fields", []) or []
    update["corrected_fields"] = sorted(set(prior_corrected) | set(changed))

    # Explanations are only for validated findings and are derived from the
    # (unchanged) validated sources. Clear on needs_review; regenerate on validated.
    if recomputed["validation_status"] != "validated":
        update["plain_english"] = None
        update["why_it_matters"] = None
        update["suggested_action"] = None
        update["explanation_generated_at"] = None

    await db.findings.update_one({"_id": oid, "user_id": user_id}, {"$set": update})
    updated = await db.findings.find_one({"_id": oid, "user_id": user_id})
    fd = Finding.from_mongo(updated).model_dump()
    if fd.get("validation_status") == "validated":
        fd = await analysis.generate_explanation(db, fd, user_id)
    await _refresh_composite_for(doc, user_id)
    fd = analysis.apply_ranking([fd])[0]
    return {"finding": fd, "changed_fields": changed}


@api_router.post("/findings/{finding_id}/dismiss")
async def dismiss_finding(finding_id: str, user_id: str = Depends(current_user_id)):
    from models import Finding
    oid, doc = await _get_finding(finding_id, user_id)
    # Preserve the finding and its provenance; only change state.
    await db.findings.update_one(
        {"_id": oid, "user_id": user_id}, {"$set": {"state": "dismissed"}})
    await _refresh_composite_for(doc, user_id)
    return {"finding": Finding.from_mongo(
        await db.findings.find_one({"_id": oid, "user_id": user_id})).model_dump()}


@api_router.get("/action-center")
async def action_center(user_id: str = Depends(current_user_id)):
    """Confirmed, actionable findings with a deterministic deadline, grouped by
    urgency (server-side). Renewal behaviour is unchanged; the 6 obligation
    types join only when validated, actionable, with a computed action deadline,
    and not superseded."""
    from models import Finding
    items = []
    async for f in db.findings.find({
        "user_id": user_id,
        "state": {"$in": ["confirmed", "corrected"]},
        "action_required": True,
        "$or": [
            {"type": "renewal_notice"},
            {"type": {"$in": analysis.GENERIC_TYPES + ["termination_right", "price_increase"]},
             "validation_status": "validated",
             "superseded_by_finding_id": None,
             "extracted.effective_action_deadline": {"$ne": None}},
        ],
    }):
        fd = Finding.from_mongo(f).model_dump()
        fd = analysis.apply_ranking([fd])[0]
        contract = await db.contracts.find_one(
            {"_id": ObjectId(fd["contract_id"]), "user_id": user_id})
        fd["contract_name"] = contract.get("name") if contract else None
        items.append(fd)
    items.sort(key=lambda x: x.get("rank_score", 0), reverse=True)

    buckets = {"urgent": [], "next_30_days": [], "later": []}
    for it in items:
        dr = (it.get("extracted") or {}).get("days_remaining")
        if dr is not None and dr <= 14:
            buckets["urgent"].append(it)
        elif dr is not None and dr <= 30:
            buckets["next_30_days"].append(it)
        else:
            buckets["later"].append(it)
    return {"buckets": buckets, "count": len(items)}


@api_router.get("/findings/{finding_id}/checklist")
async def notice_checklist(finding_id: str, user_id: str = Depends(current_user_id)):
    """Notice checklist built ONLY from the finding's validated sources."""
    from models import Finding
    oid, doc = await _get_finding(finding_id, user_id)
    f = Finding.from_mongo(doc).model_dump()
    e = f.get("extracted", {}) or {}
    by_purpose = {}
    for s in f.get("sources", []):
        by_purpose.setdefault(s["purpose"], []).append(
            {"quote": s["quote"], "location": s["location"]})
    return {
        "method": {"value": e.get("notice_method"), "sources": by_purpose.get("notice_method", [])},
        "recipient": {"value": e.get("notice_recipient"), "sources": by_purpose.get("notice_recipient", [])},
        "timing": {
            "notice_days_min": e.get("notice_days_min"),
            "notice_days_max": e.get("notice_days_max"),
            "notice_basis": e.get("notice_basis"),
            "next_renewal_date": e.get("next_renewal_date"),
            "action_deadline": e.get("effective_action_deadline"),
            "sources": by_purpose.get("notice_period", []),
        },
        "renewal_term": {"sources": by_purpose.get("renewal_term", [])},
        "validation_status": f.get("validation_status"),
        "disclaimer": "ClauseClock does not send this notice. Verify these details "
                      "against your original contract and send the notice yourself.",
    }


@api_router.post("/findings/{finding_id}/draft-notice")
async def draft_notice(finding_id: str, user_id: str = Depends(current_user_id)):
    """Generate a non-renewal notice draft from the confirmed finding +
    validated sources only. ClauseClock does not send it."""
    from models import Finding
    oid, doc = await _get_finding(finding_id, user_id)
    f = Finding.from_mongo(doc).model_dump()
    if f.get("state") not in ("confirmed", "corrected"):
        raise HTTPException(status_code=400, detail="Confirm the finding before drafting a notice.")
    if f.get("validation_status") != "validated":
        raise HTTPException(status_code=400, detail="Finding must be validated to draft a notice.")
    draft = await analysis.draft_non_renewal_notice(f)
    return {"draft": draft,
            "disclaimer": "This is a draft only. ClauseClock does not send notices. "
                          "Review, complete, and send it yourself, and verify the "
                          "method, recipient and timing against your contract. "
                          "This is not legal advice."}


class ActionInput(BaseModel):
    action_type: str
    sent_date: str
    delivery_method: str
    note: Optional[str] = None

    @field_validator("action_type")
    @classmethod
    def _valid_type(cls, v):
        if v not in ("notice_sent", "objection_sent", "claim_submitted", "dispute_raised"):
            raise ValueError("invalid action_type")
        return v

    @field_validator("sent_date")
    @classmethod
    def _valid_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValueError("sent_date must be YYYY-MM-DD")
        return v


_METHOD_KEYWORDS = {"certified", "registered", "email", "mail", "hand",
                    "courier", "written", "post", "fax", "overnight", "delivery"}


def _method_matches(contract_method, delivery_method) -> Optional[bool]:
    if not contract_method:
        return None
    a = set((contract_method or "").lower().split())
    b = set((delivery_method or "").lower().split())
    key_a = {k for k in _METHOD_KEYWORDS if k in " ".join(a)}
    key_b = {k for k in _METHOD_KEYWORDS if k in " ".join(b)}
    if not key_a:
        return None
    return bool(key_a & key_b)


@api_router.post("/findings/{finding_id}/actions")
async def log_action(finding_id: str, body: ActionInput,
                     user_id: str = Depends(current_user_id)):
    from models import Action, Finding
    oid, doc = await _get_finding(finding_id, user_id)
    f = Finding.from_mongo(doc)
    if f.state not in ("confirmed", "corrected"):
        raise HTTPException(status_code=400, detail="Confirm the finding before logging an action.")
    contract_method = (f.extracted or {}).get("notice_method")
    matches = _method_matches(contract_method, body.delivery_method)
    action = Action(
        finding_id=finding_id, contract_id=f.contract_id, user_id=user_id,
        action_type=body.action_type, sent_date=body.sent_date,
        delivery_method=body.delivery_method, method_matches_contract=matches,
        note=body.note,
    )
    result = await db.actions.insert_one(action.to_mongo())
    action.id = str(result.inserted_id)
    return {"action": action.model_dump(), "contract_method": contract_method,
            "method_warning": matches is False}


@api_router.get("/findings/{finding_id}/actions")
async def list_actions(finding_id: str, user_id: str = Depends(current_user_id)):
    from models import Action, Finding
    oid, doc = await _get_finding(finding_id, user_id)
    contract_method = (Finding.from_mongo(doc).extracted or {}).get("notice_method")
    actions = []
    async for a in db.actions.find({"finding_id": finding_id, "user_id": user_id}).sort("logged_at", -1):
        actions.append(Action.from_mongo(a).model_dump())
    return {"actions": actions, "contract_method": contract_method}


@api_router.post("/actions/{action_id}/evidence")
async def upload_evidence(action_id: str, file: UploadFile = File(...),
                          user_id: str = Depends(current_user_id)):
    """Attach an evidence file to a logged action (existing GridFS pattern)."""
    from models import Action
    try:
        oid = ObjectId(action_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Action not found.")
    doc = await db.actions.find_one({"_id": oid, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Action not found.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    storage_key = await ingestion.store_original(
        bucket, data, file.filename, file.content_type or "application/octet-stream")
    sha = ingestion.sha256_hex(data)
    entry = {
        "storage_key": storage_key, "filename": file.filename,
        "mime_type": file.content_type or "application/octet-stream",
        "size_bytes": len(data), "sha256": sha,
        "uploaded_at": utc_now_iso(), "label": "Evidence of action",
    }
    await db.actions.update_one(
        {"_id": oid, "user_id": user_id},
        {"$push": {"evidence_files": entry, "evidence_sha256": sha}})
    return {"evidence": entry}


@api_router.get("/actions/{action_id}/evidence/{index}")
async def download_evidence(action_id: str, index: int,
                            user_id: str = Depends(current_user_id)):
    from fastapi.responses import Response as FileResponse
    try:
        oid = ObjectId(action_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Action not found.")
    doc = await db.actions.find_one({"_id": oid, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Action not found.")
    files = doc.get("evidence_files", []) or []
    if index < 0 or index >= len(files) or not isinstance(files[index], dict):
        raise HTTPException(status_code=404, detail="Evidence not found.")
    meta = files[index]
    data = await ingestion.read_original(bucket, meta["storage_key"])
    return FileResponse(content=data, media_type=meta.get("mime_type", "application/octet-stream"),
                        headers={"Content-Disposition": f'inline; filename="{meta.get("filename","evidence")}"'})


class OutcomeInput(BaseModel):
    result: str
    confirmed: bool = False
    amount_recovered: Optional[float] = None
    renegotiated_annual_delta: Optional[float] = None
    term_value_avoided: Optional[float] = None
    currency: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("result")
    @classmethod
    def _valid_result(cls, v):
        if v not in ("terminated", "renegotiated", "credit_received",
                     "dispute_resolved", "reviewed_and_kept", "missed"):
            raise ValueError("invalid outcome result")
        return v


@api_router.post("/findings/{finding_id}/outcomes")
async def record_outcome(finding_id: str, body: OutcomeInput,
                         user_id: str = Depends(current_user_id)):
    from models import Outcome, Finding
    oid, doc = await _get_finding(finding_id, user_id)
    f = Finding.from_mongo(doc)
    outcome = Outcome(
        finding_id=finding_id, contract_id=f.contract_id, user_id=user_id,
        result=body.result, confirmed=body.confirmed,
        amount_recovered=body.amount_recovered,
        renegotiated_annual_delta=body.renegotiated_annual_delta,
        term_value_avoided=body.term_value_avoided,
        notes=body.notes,
    )
    data = outcome.to_mongo()
    if body.currency:
        data["currency"] = body.currency  # optional, alongside existing fields
    result = await db.outcomes.insert_one(data)
    saved = await db.outcomes.find_one({"_id": result.inserted_id})
    return {"outcome": {**Outcome.from_mongo(saved).model_dump(),
                        "currency": saved.get("currency")}}


@api_router.get("/findings/{finding_id}/outcomes")
async def list_outcomes(finding_id: str, user_id: str = Depends(current_user_id)):
    from models import Outcome
    await _get_finding(finding_id, user_id)
    outcomes = []
    async for o in db.outcomes.find({"finding_id": finding_id, "user_id": user_id}).sort("recorded_at", -1):
        outcomes.append({**Outcome.from_mongo(o).model_dump(), "currency": o.get("currency")})
    return {"outcomes": outcomes}


# --------------------------------------------------------------------------
# Stage 6D.1 — Deadline reminders (in-app; reuses the reminders collection)
# --------------------------------------------------------------------------
class ReminderInput(BaseModel):
    days_before: int

    @field_validator("days_before")
    @classmethod
    def _non_neg(cls, v):
        if v is None or v < 0:
            raise ValueError("days_before must be >= 0")
        return v


@api_router.post("/findings/{finding_id}/reminders")
async def create_reminder(finding_id: str, body: ReminderInput,
                          user_id: str = Depends(current_user_id)):
    from models import Finding, Reminder
    oid, doc = await _get_finding(finding_id, user_id)
    f = Finding.from_mongo(doc)
    deadline = (f.extracted or {}).get("effective_action_deadline")
    if not deadline:
        raise HTTPException(status_code=400,
                            detail="This finding has no actionable deadline to remind you about.")
    d = datetime.strptime(deadline, "%Y-%m-%d").date()
    fire = (d - timedelta(days=body.days_before)).isoformat()
    reminder = Reminder(finding_id=finding_id, user_id=user_id,
                        fire_date=fire, days_before=body.days_before)
    res = await db.reminders.insert_one(reminder.to_mongo())
    reminder.id = str(res.inserted_id)
    return {"reminder": reminder.model_dump()}


@api_router.get("/findings/{finding_id}/reminders")
async def list_finding_reminders(finding_id: str,
                                 user_id: str = Depends(current_user_id)):
    from models import Reminder
    await _get_finding(finding_id, user_id)
    reminders = []
    async for r in db.reminders.find(
            {"finding_id": finding_id, "user_id": user_id}).sort("fire_date", 1):
        reminders.append(Reminder.from_mongo(r).model_dump())
    return {"reminders": reminders}


@api_router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str, user_id: str = Depends(current_user_id)):
    try:
        oid = ObjectId(reminder_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    res = await db.reminders.delete_one({"_id": oid, "user_id": user_id})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return {"deleted": True, "reminder_id": reminder_id}


@api_router.get("/reminders")
async def list_reminders(user_id: str = Depends(current_user_id)):
    """All reminders for the user, each marked `due` when its fire_date has
    arrived and it has not been sent. No background scheduler — reminders are
    surfaced in-app on request (the simplest reliable approach)."""
    from models import Finding, Reminder
    today = date.today().isoformat()
    items = []
    async for r in db.reminders.find({"user_id": user_id}).sort("fire_date", 1):
        rem = Reminder.from_mongo(r).model_dump()
        fdoc = await db.findings.find_one(
            {"_id": ObjectId(rem["finding_id"]), "user_id": user_id})
        if not fdoc:
            continue
        f = Finding.from_mongo(fdoc)
        contract = await db.contracts.find_one(
            {"_id": ObjectId(f.contract_id), "user_id": user_id})
        deadline = (f.extracted or {}).get("effective_action_deadline")
        rem["due"] = (rem["fire_date"] <= today and not rem.get("sent")
                      and (not deadline or deadline >= today))
        rem["contract_id"] = f.contract_id
        rem["contract_name"] = contract.get("name") if contract else None
        rem["finding_type"] = f.type
        rem["deadline"] = deadline
        items.append(rem)
    due = sum(1 for i in items if i["due"])
    return {"reminders": items, "due_count": due}


# --------------------------------------------------------------------------
# Stage 6D.2 — Value by contract (per-contract Stage 6 accounting)
# --------------------------------------------------------------------------
@api_router.get("/dashboard/value-by-contract")
async def value_by_contract(user_id: str = Depends(current_user_id)):
    contracts = {}
    async for c in db.contracts.find({"user_id": user_id}):
        contracts[str(c["_id"])] = {
            "contract_id": str(c["_id"]), "name": c.get("name"),
            "currency": c.get("currency") or "USD",
            "confirmed_value": 0.0, "pending_value": 0.0, "outcome_count": 0,
        }
    async for o in db.outcomes.find({"user_id": user_id}):
        cid = o.get("contract_id")
        row = contracts.get(cid)
        if not row:
            continue
        val = analysis.outcome_protected_value(o)
        row["outcome_count"] += 1
        if o.get("confirmed"):
            row["confirmed_value"] += val
        else:
            row["pending_value"] += val
        if o.get("currency"):
            row["currency"] = o.get("currency")
    rows = sorted(contracts.values(), key=lambda r: r["confirmed_value"], reverse=True)
    return {"contracts": rows}


# --------------------------------------------------------------------------
# Stage 6D.3 — Outcome timeline (findings + actions + evidence + outcomes)
# --------------------------------------------------------------------------
@api_router.get("/contracts/{contract_id}/timeline")
async def contract_timeline(contract_id: str, user_id: str = Depends(current_user_id)):
    from models import Finding, Action, Outcome
    oid = await _oid(user_id, contract_id)
    contract = await db.contracts.find_one({"_id": oid, "user_id": user_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")
    events = []
    async for f in db.findings.find({"contract_id": contract_id, "user_id": user_id}):
        fm = Finding.from_mongo(f)
        label = "renewal" if fm.type == "renewal_notice" else "price increase"
        events.append({"kind": "finding", "date": f.get("created_at"),
                       "title": f"Finding detected — {label}",
                       "detail": fm.validation_status})
    async for a in db.actions.find({"contract_id": contract_id, "user_id": user_id}):
        am = Action.from_mongo(a)
        events.append({"kind": "action", "date": am.sent_date or am.logged_at,
                       "title": f"Action logged — {am.action_type.replace('_', ' ')}",
                       "detail": f"via {am.delivery_method}" if am.delivery_method else None})
        for ev in am.evidence_files or []:
            events.append({"kind": "evidence",
                           "date": (ev.get("uploaded_at") or "")[:10] or am.sent_date,
                           "title": f"Evidence attached — {ev.get('filename')}",
                           "detail": f"SHA-256 {str(ev.get('sha256'))[:10]}…"})
    async for o in db.outcomes.find({"contract_id": contract_id, "user_id": user_id}):
        om = Outcome.from_mongo(o)
        val = analysis.outcome_protected_value(o)
        detail = (f"{o.get('currency') or 'USD'} {val:,.0f}"
                  + (" · confirmed" if om.confirmed else " · pending")) if val else (
                  "confirmed" if om.confirmed else "pending")
        events.append({"kind": "outcome", "date": (om.recorded_at or "")[:10],
                       "title": f"Outcome recorded — {om.result.replace('_', ' ')}",
                       "detail": detail})
    events = [e for e in events if e.get("date")]
    events.sort(key=lambda e: e["date"])
    return {"events": events, "contract_name": contract.get("name")}


# --------------------------------------------------------------------------
# Stage 6D.4 — Savings report (confirmed value only in the headline)
# --------------------------------------------------------------------------
@api_router.get("/reports/savings")
async def savings_report(user_id: str = Depends(current_user_id)):
    from models import Finding, Outcome
    currency = "USD"
    confirmed_total = 0.0
    pending_total = 0.0
    lines = []
    async for o in db.outcomes.find({"user_id": user_id}):
        val = analysis.outcome_protected_value(o)
        cur = o.get("currency") or "USD"
        if o.get("currency"):
            currency = cur
        contract = await db.contracts.find_one(
            {"_id": ObjectId(o["contract_id"]), "user_id": user_id}) if o.get("contract_id") else None
        if o.get("confirmed"):
            confirmed_total += val
        else:
            pending_total += val
        if o.get("confirmed") and val > 0:
            lines.append({
                "contract_name": contract.get("name") if contract else "—",
                "result": o.get("result"),
                "value": val, "currency": cur,
                "recorded_at": (o.get("recorded_at") or "")[:10],
                "notes": o.get("notes"),
            })
    lines.sort(key=lambda x: x["value"], reverse=True)
    return {
        "generated_at": utc_now_iso(),
        "currency": currency,
        "confirmed_value_protected": confirmed_total,  # headline: confirmed ONLY
        "pending_value": pending_total,                # shown separately, never in headline
        "confirmed_outcomes": len(lines),
        "lines": lines,
    }



@api_router.get("/accuracy")
async def accuracy(user_id: str = Depends(current_user_id)):
    """Operator instrumentation over stored findings. Not a learning system."""
    reviewed = confirmed = corrected = 0
    field_freq: dict = {}
    by_type: dict = {}
    async for f in db.findings.find({"user_id": user_id}):
        ftype = f.get("type", "unknown")
        bt = by_type.setdefault(
            ftype, {"reviewed": 0, "confirmed_no_edits": 0, "corrected": 0})
        state = f.get("state")
        if state in ("confirmed", "corrected"):
            reviewed += 1
            bt["reviewed"] += 1
        if state == "confirmed":
            confirmed += 1
            bt["confirmed_no_edits"] += 1
        elif state == "corrected":
            corrected += 1
            bt["corrected"] += 1
            for name in f.get("corrected_fields", []) or []:
                field_freq[name] = field_freq.get(name, 0) + 1
    return {
        "findings_reviewed": reviewed,
        "confirmed_no_edits": confirmed,
        "corrected": corrected,
        "correction_rate_pct": round(100 * corrected / reviewed, 1) if reviewed else 0.0,
        "corrected_field_frequency": dict(
            sorted(field_freq.items(), key=lambda x: (-x[1], x[0]))),
        "by_type": by_type,
    }


@api_router.get("/dashboard/summary")
async def dashboard_summary(user_id: str = Depends(current_user_id)):
    """Stage 6C2 — value accounting for the dashboard (user-scoped).

    Headline protected/recovered value counts CONFIRMED outcomes only. Pending
    value is recorded-but-unconfirmed outcomes. All per-outcome value follows
    analysis.outcome_protected_value (no annualizing a terminated term, only the
    confirmed renegotiation delta, reviewed_and_kept protects $0)."""
    contracts = [c async for c in db.contracts.find({"user_id": user_id})]
    contracts_monitored = len(contracts)
    value_under_tracking = sum(float(c.get("annual_value") or 0.0) for c in contracts)
    currency = next((c.get("currency") for c in contracts if c.get("currency")), None) or "USD"

    confirmed_value_protected = 0.0
    pending_value = 0.0
    windows_missed = 0
    outcomes_recorded = 0
    breakdown: dict = {}
    async for o in db.outcomes.find({"user_id": user_id}):
        outcomes_recorded += 1
        result = o.get("result")
        val = analysis.outcome_protected_value(o)
        b = breakdown.setdefault(
            result, {"count": 0, "confirmed_count": 0, "confirmed_value": 0.0})
        b["count"] += 1
        if o.get("confirmed"):
            b["confirmed_count"] += 1
            b["confirmed_value"] += val
            confirmed_value_protected += val
        else:
            pending_value += val
        if result == "missed":
            windows_missed += 1
        if o.get("currency"):
            currency = o.get("currency")

    return {
        "contracts_monitored": contracts_monitored,
        "value_under_tracking": value_under_tracking,
        "confirmed_value_protected": confirmed_value_protected,
        "pending_value": pending_value,
        "windows_missed": windows_missed,
        "outcomes_recorded": outcomes_recorded,
        "currency": currency,
        "by_result": breakdown,
    }




@api_router.delete("/contracts/{contract_id}")
async def delete_contract(contract_id: str, user_id: str = Depends(current_user_id)):
    oid = await _oid(user_id, contract_id)
    contract = await db.contracts.find_one({"_id": oid, "user_id": user_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    # Hard delete stored originals from GridFS.
    async for d in db.documents.find({"contract_id": contract_id, "user_id": user_id}):
        if d.get("storage_key"):
            await ingestion.delete_original(bucket, d["storage_key"])

    # Cascade dependent records (findings/actions/outcomes exist in later stages).
    finding_ids = [str(f["_id"]) async for f in
                   db.findings.find({"contract_id": contract_id, "user_id": user_id}, {"_id": 1})]
    if finding_ids:
        await db.reminders.delete_many({"finding_id": {"$in": finding_ids}, "user_id": user_id})

    removed = {
        "documents": (await db.documents.delete_many({"contract_id": contract_id, "user_id": user_id})).deleted_count,
        "findings": (await db.findings.delete_many({"contract_id": contract_id, "user_id": user_id})).deleted_count,
        "actions": (await db.actions.delete_many({"contract_id": contract_id, "user_id": user_id})).deleted_count,
        "outcomes": (await db.outcomes.delete_many({"contract_id": contract_id, "user_id": user_id})).deleted_count,
    }
    await db.contracts.delete_one({"_id": oid, "user_id": user_id})
    return {"deleted": True, "contract_id": contract_id, "cascade": removed}


# --------------------------------------------------------------------------
# Meta
# --------------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"service": "clauseclock", "stage": "stage-1", "status": "ok"}


# --------------------------------------------------------------------------
# Startup
# --------------------------------------------------------------------------
async def ensure_collections_and_indexes():
    existing = set(await db.list_collection_names())
    for name in COLLECTIONS:
        if name not in existing:
            await db.create_collection(name)
    await db.users.create_index("email", unique=True)
    await db.contracts.create_index("user_id")
    await db.documents.create_index([("user_id", 1), ("contract_id", 1)])
    await db.findings.create_index([("user_id", 1), ("contract_id", 1)])
    await db.actions.create_index([("user_id", 1), ("contract_id", 1)])
    await db.outcomes.create_index([("user_id", 1), ("contract_id", 1)])
    await db.reminders.create_index([("user_id", 1), ("finding_id", 1)])


async def seed_test_user():
    existing = await db.users.find_one({"email": TEST_USER["email"]})
    if not existing:
        await db.users.insert_one(
            User(email=TEST_USER["email"],
                 password_hash=auth.hash_password(TEST_USER["password"])).to_mongo()
        )
        logger.info("Seeded test user %s", TEST_USER["email"])


@app.on_event("startup")
async def on_startup():
    await ensure_collections_and_indexes()
    await seed_test_user()


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o],
    allow_origin_regex=r"https://.*\.preview\.emergentagent\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
