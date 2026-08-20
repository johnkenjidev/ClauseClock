"""
ClauseClock backend — Prompt 0 scaffolding.

This wires up the app, connects to MongoDB, creates the collections defined in
PART 1.1 with user_id-scoped indexes, and exposes the auth dependency stub.

Deliberately NOT implemented (later stages, per the prompt):
  extraction, clause analysis, deadline computation, ranking, explanations,
  reminders, notice drafting, Action Center logic, dashboard logic, /demo data.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

from auth import get_current_user_id
from models import COLLECTIONS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="ClauseClock")
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("clauseclock")


@api_router.get("/")
async def root():
    return {"service": "clauseclock", "stage": "prompt-0", "status": "ok"}


@api_router.get("/meta/collections")
async def meta_collections():
    """Report the collections that exist and their model field names."""
    existing = set(await db.list_collection_names())
    return {
        "collections": {
            name: {
                "exists": name in existing,
                "fields": list(model.model_fields.keys()),
            }
            for name, model in COLLECTIONS.items()
        }
    }


@api_router.get("/meta/whoami")
async def whoami(user_id: str = Depends(get_current_user_id)):
    """Demonstrates the isolation dependency. user_id is server-derived only."""
    return {"user_id": user_id, "source": "server-derived"}


async def ensure_collections_and_indexes():
    """
    Create each collection if absent and the user_id-scoped indexes that make
    hard isolation cheap. Idempotent — safe to run on every startup.
    """
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
    logger.info("Collections and indexes ensured: %s", ", ".join(COLLECTIONS))


@app.on_event("startup")
async def on_startup():
    await ensure_collections_and_indexes()


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
