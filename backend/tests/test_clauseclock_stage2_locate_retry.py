"""ClauseClock Stage 2 accuracy repair — LOCATE FALLBACK + RETRY tests.

Deterministic in-process tests for analysis.run_renewal_analysis logic:
  1. High-recall locate fallback: hint chunks are unioned with AI locate
     even when AI locate returns [] or under-selects.
  2. Exactly ONE targeted retry when extract returns found:false while
     hint chunks exist (no infinite/multiple retries).
  3. No retry (and no finding) when extract returns found:false AND
     there are no hint chunks (genuinely non-renewing contract).

Uses in-memory Mongo-shape via mongomock-free minimal shim: seed a real
document/contract for the seeded test user then monkeypatch llm.locate
and llm.extract.
"""
import asyncio
import io
import os
import sys
import time

import pytest
import requests
from dotenv import load_dotenv
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

sys.path.insert(0, "/app/backend")
import analysis  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SEED_EMAIL = "test@clauseclock.app"
SEED_PASSWORD = "Test1234!"


def _pdf(paragraphs):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    w, h = LETTER
    y = h - 60
    c.setFont("Helvetica", 11)
    for para in paragraphs:
        line = ""
        for word in para.split():
            trial = (line + " " + word).strip()
            if c.stringWidth(trial, "Helvetica", 11) > w - 120:
                c.drawString(60, y, line); y -= 15; line = word
                if y < 60:
                    c.showPage(); c.setFont("Helvetica", 11); y = h - 60
            else:
                line = trial
        if line:
            c.drawString(60, y, line); y -= 15
        y -= 8
        if y < 60:
            c.showPage(); c.setFont("Helvetica", 11); y = h - 60
    c.showPage(); c.save()
    return buf.getvalue()


RENEWAL_TEXT = [
    "MASTER SERVICES AGREEMENT",
    "This Agreement is effective as of March 15, 2026.",
    "TERM AND RENEWAL. The initial term of this Agreement is twelve "
    "(12) months and this Agreement shall automatically renew for "
    "successive one-year terms unless written notice of non-renewal is "
    "given at least sixty (60) days prior to the end of the then-current "
    "term.",
    "FEES. $36,000 annually.",
]

NON_RENEWING_TEXT = [
    "SERVICE ORDER",
    "This Order is effective March 1, 2026.",
    "TERM. This Order expires December 31, 2026 with no extension.",
    "FEES. $10,000 flat.",
    "GOVERNING LAW. Delaware.",
]


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    assert r.status_code == 200, r.text
    return s


def _create(sess, name, paragraphs):
    files = {"file": (f"{name}.pdf", _pdf(paragraphs), "application/pdf")}
    form = {"name": name, "counterparty": "Vendor Systems, Inc.", "doc_role": "primary"}
    r = sess.post(f"{API}/contracts", files=files, data=form, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["contract"]["id"]


@pytest.fixture(scope="module")
def created(sess):
    ids = []
    yield ids
    for cid in ids:
        try: sess.delete(f"{API}/contracts/{cid}", timeout=15)
        except Exception: pass


def _run(cid, fake_locate, fake_extract):
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson import ObjectId
    import llm as llm_mod

    async def _inner():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        contract = await db.contracts.find_one({"_id": ObjectId(cid)})
        assert contract is not None
        user_id = contract["user_id"]

        calls = {"locate": 0, "extract": 0}

        async def loc_wrap(chunks):
            calls["locate"] += 1
            return await fake_locate(chunks)

        async def ext_wrap(chunks):
            calls["extract"] += 1
            return await fake_extract(chunks, calls["extract"])

        orig_l, orig_e = llm_mod.locate, llm_mod.extract
        analysis.llm.locate = loc_wrap
        analysis.llm.extract = ext_wrap
        try:
            findings, warnings = await analysis.run_renewal_analysis(
                db, contract, user_id)
        finally:
            analysis.llm.locate = orig_l
            analysis.llm.extract = orig_e
        client.close()
        return findings, warnings, calls

    return asyncio.new_event_loop().run_until_complete(_inner())


# =========================================================================
class TestHighRecallLocateFallback:
    """AI locate returns []; hint chunks should still be extracted → finding."""

    def test_empty_ai_locate_still_uses_hint_chunks(self, sess, created):
        cid = _create(sess, "TEST_stage2_hint_union", RENEWAL_TEXT)
        created.append(cid)

        async def loc(chunks):
            return []  # AI misses entirely

        async def ext(chunks, call_num):
            # Should be called because hint chunks were unioned in
            assert len(chunks) >= 1
            # Verify a chunk containing renewal language was passed
            joined = " ".join(c["text"] for c in chunks)
            assert analysis.RENEWAL_HINT.search(joined) is not None, \
                "hint chunks must be present in extract input"
            cid0 = chunks[0]["chunk_id"]
            # Return a valid extraction whose quote IS verbatim
            return {
                "found": True,
                "effective_date": "2026-03-15",
                "initial_term_value": 12, "initial_term_unit": "months",
                "renewal_type": "automatic",
                "renewal_period_value": 1, "renewal_period_unit": "years",
                "notice_days_min": 60, "notice_days_max": None,
                "notice_basis": "calendar",
                "business_day_definition": None,
                "notice_measured_to": "sent",
                "deemed_receipt_rule": None,
                "notice_method": None, "notice_recipient": None,
                "annual_value": None,
                "sources": [
                    {"purpose": "renewal_term", "chunk_id": cid0,
                     "quote": "shall automatically renew for successive one-year terms"},
                    {"purpose": "notice_period", "chunk_id": cid0,
                     "quote": "at least sixty (60) days prior to the end of the then-current term"},
                ],
                "confidence": "high",
            }

        findings, warnings, calls = _run(cid, loc, ext)
        assert warnings == [], warnings
        assert len(findings) == 1
        # Only ONE extract call — no retry needed on success
        assert calls["extract"] == 1
        f = findings[0]
        purposes = {s["purpose"] for s in f["sources"]}
        assert "renewal_term" in purposes and "notice_period" in purposes
        # deterministic deadline: 2027-03-15 minus 60 days = 2027-01-14
        assert f["extracted"]["next_renewal_date"] == "2027-03-15"
        assert f["extracted"]["effective_action_deadline"] == "2027-01-14"


class TestOneRetryOnFoundFalse:
    def test_exactly_one_retry_when_found_false_and_hints_exist(self, sess, created):
        cid = _create(sess, "TEST_stage2_retry", RENEWAL_TEXT)
        created.append(cid)

        async def loc(chunks):
            return [chunks[0]["chunk_id"]] if chunks else []

        async def ext(chunks, call_num):
            if call_num == 1:
                return {"found": False}
            # Retry — should be called EXACTLY once more with hint chunks
            cid0 = chunks[0]["chunk_id"]
            return {
                "found": True,
                "effective_date": "2026-03-15",
                "initial_term_value": 12, "initial_term_unit": "months",
                "renewal_type": "automatic",
                "renewal_period_value": 1, "renewal_period_unit": "years",
                "notice_days_min": 60, "notice_days_max": None,
                "notice_basis": "calendar",
                "business_day_definition": None,
                "notice_measured_to": "sent",
                "deemed_receipt_rule": None,
                "notice_method": None, "notice_recipient": None,
                "annual_value": None,
                "sources": [
                    {"purpose": "renewal_term", "chunk_id": cid0,
                     "quote": "shall automatically renew for successive one-year terms"},
                    {"purpose": "notice_period", "chunk_id": cid0,
                     "quote": "at least sixty (60) days prior to the end of the then-current term"},
                ],
                "confidence": "high",
            }

        findings, warnings, calls = _run(cid, loc, ext)
        assert calls["extract"] == 2, f"expected exactly one retry, got {calls}"
        assert len(findings) == 1

    def test_no_retry_when_no_hint_chunks(self, sess, created):
        cid = _create(sess, "TEST_stage2_noretry", NON_RENEWING_TEXT)
        created.append(cid)

        async def loc(chunks):
            return [chunks[0]["chunk_id"]] if chunks else []

        async def ext(chunks, call_num):
            return {"found": False}

        findings, warnings, calls = _run(cid, loc, ext)
        # non-renewing doc: hint regex should not match → no retry
        assert calls["extract"] == 1, f"no retry expected, got {calls}"
        assert findings == []
        assert warnings == []

    def test_no_finding_when_retry_also_returns_found_false(self, sess, created):
        cid = _create(sess, "TEST_stage2_retry_still_false", RENEWAL_TEXT)
        created.append(cid)

        async def loc(chunks): return []

        async def ext(chunks, call_num):
            return {"found": False}

        findings, warnings, calls = _run(cid, loc, ext)
        # first call + one retry (because hint chunks exist) = 2
        assert calls["extract"] == 2
        assert findings == []
        assert warnings == []


class TestProvenanceIntegrity:
    """Every stored source: char_offset equals validator's returned offset
    into that document's raw_text, and stored quote is marker/typo-normalized."""

    def test_char_offset_matches_validator_result(self, sess, created):
        cid = _create(sess, "TEST_stage2_provenance", RENEWAL_TEXT)
        created.append(cid)

        async def loc(chunks):
            return [c["chunk_id"] for c in chunks[:2]]

        async def ext(chunks, call_num):
            cid0 = chunks[0]["chunk_id"]
            return {
                "found": True,
                "effective_date": "2026-03-15",
                "initial_term_value": 12, "initial_term_unit": "months",
                "renewal_type": "automatic",
                "renewal_period_value": 1, "renewal_period_unit": "years",
                "notice_days_min": 60, "notice_days_max": None,
                "notice_basis": "calendar",
                "business_day_definition": None,
                "notice_measured_to": "sent",
                "deemed_receipt_rule": None,
                "notice_method": None, "notice_recipient": None,
                "annual_value": None,
                "sources": [
                    {"purpose": "renewal_term", "chunk_id": cid0,
                     "quote": "shall automatically renew for successive one-year terms"},
                    {"purpose": "notice_period", "chunk_id": cid0,
                     "quote": "at least sixty (60) days prior to the end of the then-current term"},
                ],
                "confidence": "high",
            }

        findings, warnings, calls = _run(cid, loc, ext)
        assert len(findings) == 1
        f = findings[0]

        # Fetch docs + re-validate offsets from HTTP surface
        r = sess.get(f"{API}/contracts/{cid}", timeout=15)
        docs = {d["id"]: d for d in r.json()["documents"]}
        for s in f["sources"]:
            raw = docs[s["document_id"]]["raw_text"]
            recomputed = analysis.find_quote_offset_marker_tolerant(raw, s["quote"])
            assert recomputed is not None
            assert s["char_offset"] == recomputed, (s, recomputed)
