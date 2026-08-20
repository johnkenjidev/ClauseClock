"""Focused Stage 6C2 check: value accounting totals vs a small known set."""
import asyncio, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import analysis

MONGO = os.environ["MONGO_URL"]
DB = os.environ["DB_NAME"]


async def main():
    client = AsyncIOMotorClient(MONGO)
    db = client[DB]
    user = await db.users.find_one({"email": "test@clauseclock.app"})
    uid = str(user["_id"])

    cid = "check6c2-contract"
    fid = "check6c2-finding"
    await db.outcomes.delete_many({"finding_id": fid})

    # Known set:
    #  confirmed terminated  -> term_value_avoided 40000  (avoided next term only)
    #  confirmed renegotiated -> annual_delta 12000       (annual savings only)
    #  confirmed credit       -> amount_recovered 5000
    #  confirmed reviewed_kept -> $0 (not a failure)
    #  UNconfirmed dispute    -> amount_recovered 9000 (pending, not headline)
    #  confirmed missed       -> $0, windows_missed +1
    outcomes = [
        {"result": "terminated", "confirmed": True, "term_value_avoided": 40000.0},
        {"result": "renegotiated", "confirmed": True, "renegotiated_annual_delta": 12000.0},
        {"result": "credit_received", "confirmed": True, "amount_recovered": 5000.0},
        {"result": "reviewed_and_kept", "confirmed": True},
        {"result": "dispute_resolved", "confirmed": False, "amount_recovered": 9000.0},
        {"result": "missed", "confirmed": True},
    ]
    for o in outcomes:
        o.update({"finding_id": fid, "contract_id": cid, "user_id": uid,
                  "currency": "USD", "recorded_at": "2026-06-01T00:00:00Z"})
    await db.outcomes.insert_many(outcomes)

    # Recompute exactly like the endpoint.
    confirmed = pending = 0.0
    missed = 0
    async for o in db.outcomes.find({"user_id": uid, "finding_id": fid}):
        v = analysis.outcome_protected_value(o)
        if o.get("confirmed"):
            confirmed += v
        else:
            pending += v
        if o["result"] == "missed":
            missed += 1

    exp_confirmed = 40000 + 12000 + 5000  # 57000 (reviewed_kept & missed add 0)
    exp_pending = 9000
    exp_missed = 1
    assert confirmed == exp_confirmed, (confirmed, exp_confirmed)
    assert pending == exp_pending, (pending, exp_pending)
    assert missed == exp_missed, (missed, exp_missed)
    print("PASS confirmed=%s pending=%s missed=%s" % (confirmed, pending, missed))

    await db.outcomes.delete_many({"finding_id": fid})
    client.close()


asyncio.run(main())
