"""Seed a contract + document with crafted price-increase text for a live e2e
analyze run. Prints the contract_id."""
import asyncio, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from motor.motor_asyncio import AsyncIOMotorClient
from models import Contract, Document

RAW = """===== Page 1 =====
MASTER SERVICES AGREEMENT

1. Term. This Agreement is effective as of January 1, 2025 and shall continue
for an initial term of twelve (12) months.

4. Fees. The annual fee for the Services is one hundred thousand dollars
($100,000).

5. Price Adjustment. Commencing on each anniversary of the Effective Date, the
annual fees shall automatically increase by three percent (3%) per annum. The
next such increase shall take effect on June 1, 2026. Customer may object to the
increase by providing written notice to the Vendor's Account Manager no later
than thirty (30) days prior to the effective date of the increase.
"""


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    user = await db.users.find_one({"email": "test@clauseclock.app"})
    uid = str(user["_id"])

    # clean any prior e2e contract
    old = await db.contracts.find_one({"user_id": uid, "name": "E2E Price Increase Co"})
    if old:
        cid = str(old["_id"])
        await db.documents.delete_many({"contract_id": cid})
        await db.findings.delete_many({"contract_id": cid})
        await db.contracts.delete_one({"_id": old["_id"]})

    c = Contract(user_id=uid, name="E2E Price Increase Co", counterparty="Vendor Inc",
                 annual_value=100000.0, currency="USD", value_source="user_entered",
                 status="processing")
    res = await db.contracts.insert_one(c.to_mongo())
    cid = str(res.inserted_id)
    d = Document(contract_id=cid, user_id=uid, filename="msa.pdf", file_type="pdf",
                 doc_role="primary", raw_text=RAW, page_count=1,
                 extraction_method="pdfplumber")
    await db.documents.insert_one(d.to_mongo())
    print(cid)
    client.close()

asyncio.run(main())
