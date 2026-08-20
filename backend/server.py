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
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import (APIRouter, Depends, FastAPI, File, Form, HTTPException,
                     Request, Response, UploadFile)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pydantic import BaseModel, EmailStr
from pymongo.errors import DuplicateKeyError
from starlette.middleware.cors import CORSMiddleware

import auth
import ingestion
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
