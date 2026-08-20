"""
Stage 3 tests — Confirm / Correct / Dismiss on renewal_notice findings +
/accuracy instrumentation. We seed findings directly via Mongo (same DB
the backend uses) so we don't have to rerun the LLM. All state transitions
are exercised over HTTPS via the public backend URL.
"""
import os
import time
import uuid
from datetime import date, datetime

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient
from dateutil.relativedelta import relativedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://crazy-babbage-9.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _register(email=None, password="Test1234!"):
    email = email or f"t3_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
    return s, me["id"], email


def _seed_contract(user_id):
    cid = ObjectId()
    db.contracts.insert_one({
        "_id": cid,
        "user_id": user_id,  # stored as string per backend
        "name": f"TEST_{uuid.uuid4().hex[:6]}",
        "counterparty": None,
        "status": "analysed",
        "created_at": datetime.utcnow().isoformat(),
    })
    return str(cid)


def _seed_finding(user_id, contract_id, extracted=None, sources=None,
                  validation_status="needs_review", state="unconfirmed"):
    """Insert a renewal_notice finding directly."""
    fid = ObjectId()
    doc = {
        "_id": fid,
        "contract_id": contract_id,
        "user_id": user_id,
        "type": "renewal_notice",
        "extracted": extracted or {
            "effective_date": None,
            "initial_term_value": None,
            "initial_term_unit": None,
            "renewal_type": "automatic",
            "renewal_period_value": 1,
            "renewal_period_unit": "years",
            "notice_days_min": 30,
            "notice_days_max": None,
            "notice_basis": "calendar",
            "business_day_definition": None,
            "notice_measured_to": "sent",
            "deemed_receipt_rule": None,
            "notice_method": "written",
            "notice_recipient": "Counterparty",
            "next_renewal_date": None,
            "action_deadline": None,
            "earliest_action_date": None,
            "effective_action_deadline": None,
            "days_remaining": None,
        },
        "sources": sources or [{
            "purpose": "renewal_term", "chunk_id": "c_01",
            "document_id": str(ObjectId()),
            "quote": "This Agreement automatically renews for successive one-year terms.",
            "location": "p.3", "char_offset": 100,
        }, {
            "purpose": "notice_period", "chunk_id": "c_02",
            "document_id": str(ObjectId()),
            "quote": "unless either party gives written notice at least thirty (30) days before renewal.",
            "location": "p.3", "char_offset": 250,
        }],
        "confidence": "medium",
        "action_required": True,
        "money_amount": None, "money_currency": None, "money_kind": None,
        "rank_category": "informational", "rank_score": 0, "rank_basis": {},
        "plain_english": None, "why_it_matters": None,
        "suggested_action": None, "explanation_generated_at": None,
        "validation_status": validation_status, "validation_notes": [],
        "state": state,
        "original_values": {}, "corrected_fields": [],
        "confirmed_at": None, "superseded_by_finding_id": None,
        "related_finding_ids": [], "is_composite": False, "composite_of": [],
        "created_at": datetime.utcnow().isoformat(),
    }
    db.findings.insert_one(doc)
    return str(fid)


@pytest.fixture(scope="module")
def user_a():
    s, uid, email = _register()
    yield s, uid, email
    # cleanup
    db.findings.delete_many({"user_id": uid})
    db.contracts.delete_many({"user_id": uid})
    db.users.delete_one({"_id": ObjectId(uid)})


@pytest.fixture(scope="module")
def user_b():
    s, uid, email = _register()
    yield s, uid, email
    db.findings.delete_many({"user_id": uid})
    db.contracts.delete_many({"user_id": uid})
    db.users.delete_one({"_id": ObjectId(uid)})


# --------------------------------------------------------------------------
# Confirm
# --------------------------------------------------------------------------
def test_confirm_sets_state_and_preserves_extracted(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    fid = _seed_finding(uid, cid)

    before = db.findings.find_one({"_id": ObjectId(fid)})["extracted"]

    r = s.post(f"{BASE_URL}/api/findings/{fid}/confirm", timeout=15)
    assert r.status_code == 200, r.text
    f = r.json()["finding"]
    assert f["state"] == "confirmed"
    assert f["confirmed_at"] is not None

    after = db.findings.find_one({"_id": ObjectId(fid)})["extracted"]
    assert before == after, "extracted must be byte-for-byte unchanged after confirm"


# --------------------------------------------------------------------------
# Correct — recompute unblocks deadline
# --------------------------------------------------------------------------
def test_correct_recompute_unblocks_deadline(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    # Daktronics-style: effective_date null, automatic, 1yr renewal, 30d notice
    fid = _seed_finding(uid, cid)

    payload = {
        "effective_date": "2025-06-01",
        "initial_term_value": 1,
        "initial_term_unit": "years",
        "renewal_type": "automatic",
        "renewal_period_value": 1,
        "renewal_period_unit": "years",
        "notice_days_min": 30,
        "notice_days_max": None,
        "notice_basis": "calendar",
        "business_day_definition": None,
        "notice_measured_to": "sent",
        "deemed_receipt_rule": None,
        "notice_method": "written",
        "notice_recipient": "Counterparty",
    }
    r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    resp = r.json()
    f = resp["finding"]

    assert f["state"] == "corrected"
    assert f["validation_status"] == "validated"

    e = f["extracted"]
    today = date.today()
    renewal = date(2025, 6, 1) + relativedelta(years=1)
    while renewal <= today:
        renewal = renewal + relativedelta(years=1)
    from datetime import timedelta
    expected_deadline = renewal - timedelta(days=30)

    assert e["next_renewal_date"] == renewal.isoformat()
    assert e["effective_action_deadline"] == expected_deadline.isoformat()
    assert e["days_remaining"] == (expected_deadline - today).days

    # original_values preserved (effective_date was null pre-edit)
    assert f["original_values"]["effective_date"] is None
    assert f["original_values"]["initial_term_value"] is None
    assert f["original_values"]["initial_term_unit"] is None

    # corrected_fields lists exactly the changed field names
    changed = set(resp["changed_fields"])
    assert changed == {"effective_date", "initial_term_value", "initial_term_unit"}
    assert set(f["corrected_fields"]) == changed


# --------------------------------------------------------------------------
# Correct with NO changes doesn't fabricate corrected_fields
# --------------------------------------------------------------------------
def test_correct_no_changes_is_noop_on_corrected_fields(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    # Seed a finding already partially corrected
    extracted = {
        "effective_date": "2025-01-01",
        "initial_term_value": 1, "initial_term_unit": "years",
        "renewal_type": "automatic",
        "renewal_period_value": 1, "renewal_period_unit": "years",
        "notice_days_min": 30, "notice_days_max": None,
        "notice_basis": "calendar", "business_day_definition": None,
        "notice_measured_to": "sent", "deemed_receipt_rule": None,
        "notice_method": "written", "notice_recipient": "Counterparty",
    }
    fid = _seed_finding(uid, cid, extracted=extracted, validation_status="validated")
    # Add prior corrected_fields
    db.findings.update_one({"_id": ObjectId(fid)},
                           {"$set": {"corrected_fields": ["effective_date"],
                                     "original_values": {"effective_date": None}}})

    # Send SAME values -> no changes
    r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=extracted, timeout=15)
    assert r.status_code == 200, r.text
    resp = r.json()
    assert resp["changed_fields"] == []
    # corrected_fields unchanged (not overwritten/duplicated)
    assert resp["finding"]["corrected_fields"] == ["effective_date"]


# --------------------------------------------------------------------------
# Invalid values rejected (422), no persistence
# --------------------------------------------------------------------------
@pytest.mark.parametrize("payload", [
    {"effective_date": "2024-13-40"},
    {"notice_days_min": -5},
    {"renewal_type": "foo"},
    {"initial_term_unit": "fortnights"},
    {"notice_basis": "lunar"},
])
def test_correct_rejects_invalid(user_a, payload):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    fid = _seed_finding(uid, cid)
    before = db.findings.find_one({"_id": ObjectId(fid)})

    r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=15)
    assert r.status_code == 422, f"expected 422 got {r.status_code}: {r.text}"

    after = db.findings.find_one({"_id": ObjectId(fid)})
    assert before == after, "finding must be unchanged on validation failure"


# --------------------------------------------------------------------------
# Dismiss preserves finding + provenance
# --------------------------------------------------------------------------
def test_dismiss_preserves_provenance(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    fid = _seed_finding(uid, cid)
    src_len_before = len(db.findings.find_one({"_id": ObjectId(fid)})["sources"])

    r = s.post(f"{BASE_URL}/api/findings/{fid}/dismiss", timeout=15)
    assert r.status_code == 200, r.text
    f = r.json()["finding"]
    assert f["state"] == "dismissed"
    assert len(f["sources"]) == src_len_before

    # Still listed on GET
    r2 = s.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    assert r2.status_code == 200
    listing = r2.json()["findings"]
    assert any(x["id"] == fid and x["state"] == "dismissed" for x in listing)


# --------------------------------------------------------------------------
# Persistence across refresh (simulated with a fresh GET)
# --------------------------------------------------------------------------
def test_persistence_after_actions(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    f1 = _seed_finding(uid, cid)
    f2 = _seed_finding(uid, cid)
    f3 = _seed_finding(uid, cid)

    s.post(f"{BASE_URL}/api/findings/{f1}/confirm", timeout=15)
    s.post(f"{BASE_URL}/api/findings/{f2}/correct", json={
        "effective_date": "2025-03-01",
        "initial_term_value": 1, "initial_term_unit": "years",
        "renewal_type": "automatic",
        "renewal_period_value": 1, "renewal_period_unit": "years",
        "notice_days_min": 30, "notice_days_max": None,
        "notice_basis": "calendar", "business_day_definition": None,
        "notice_measured_to": "sent", "deemed_receipt_rule": None,
        "notice_method": "written", "notice_recipient": "X",
    }, timeout=15)
    s.post(f"{BASE_URL}/api/findings/{f3}/dismiss", timeout=15)

    r = s.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    assert r.status_code == 200
    by_id = {x["id"]: x for x in r.json()["findings"]}
    assert by_id[f1]["state"] == "confirmed"
    assert by_id[f2]["state"] == "corrected"
    assert by_id[f2]["extracted"]["effective_action_deadline"] is not None
    assert by_id[f3]["state"] == "dismissed"


# --------------------------------------------------------------------------
# User isolation
# --------------------------------------------------------------------------
def test_isolation_between_users(user_a, user_b):
    sa, uid_a, _ = user_a
    sb, uid_b, _ = user_b
    cid = _seed_contract(uid_a)
    fid = _seed_finding(uid_a, cid)

    # user B cannot confirm/correct/dismiss user A's finding
    assert sb.post(f"{BASE_URL}/api/findings/{fid}/confirm", timeout=15).status_code == 404
    assert sb.post(f"{BASE_URL}/api/findings/{fid}/correct", json={"effective_date": "2025-01-01"}, timeout=15).status_code == 404
    assert sb.post(f"{BASE_URL}/api/findings/{fid}/dismiss", timeout=15).status_code == 404

    # user B cannot list findings on user A's contract
    assert sb.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15).status_code == 404


# --------------------------------------------------------------------------
# /accuracy correctness (deterministic, fresh user)
# --------------------------------------------------------------------------
def test_accuracy_correctness():
    s, uid, _ = _register()
    try:
        # Fresh user: /accuracy is zeros
        r = s.get(f"{BASE_URL}/api/accuracy", timeout=15)
        assert r.status_code == 200
        d0 = r.json()
        assert d0["findings_reviewed"] == 0
        assert d0["confirmed_no_edits"] == 0
        assert d0["corrected"] == 0
        assert d0["correction_rate_pct"] == 0.0

        cid = _seed_contract(uid)

        # 3 confirmed, 2 corrected (fields chosen deterministically)
        for _ in range(3):
            fid = _seed_finding(uid, cid)
            assert s.post(f"{BASE_URL}/api/findings/{fid}/confirm", timeout=15).status_code == 200

        for _ in range(2):
            fid = _seed_finding(uid, cid)
            r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json={
                "effective_date": "2025-06-01",
                "initial_term_value": 1, "initial_term_unit": "years",
                "renewal_type": "automatic",
                "renewal_period_value": 1, "renewal_period_unit": "years",
                "notice_days_min": 30, "notice_days_max": None,
                "notice_basis": "calendar", "business_day_definition": None,
                "notice_measured_to": "sent", "deemed_receipt_rule": None,
                "notice_method": "written", "notice_recipient": "Counterparty",
            }, timeout=15)
            assert r.status_code == 200, r.text

        # Add a dismissed one — must NOT be counted as reviewed
        fid_d = _seed_finding(uid, cid)
        assert s.post(f"{BASE_URL}/api/findings/{fid_d}/dismiss", timeout=15).status_code == 200

        r = s.get(f"{BASE_URL}/api/accuracy", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["findings_reviewed"] == 5
        assert d["confirmed_no_edits"] == 3
        assert d["corrected"] == 2
        assert d["correction_rate_pct"] == round(100 * 2 / 5, 1) == 40.0
        # each correction changed 3 fields => tally=2 for each
        freq = d["corrected_field_frequency"]
        assert freq.get("effective_date") == 2
        assert freq.get("initial_term_value") == 2
        assert freq.get("initial_term_unit") == 2
        # by_type
        bt = d["by_type"]["renewal_notice"]
        assert bt == {"reviewed": 5, "confirmed_no_edits": 3, "corrected": 2}
    finally:
        db.findings.delete_many({"user_id": uid})
        db.contracts.delete_many({"user_id": uid})
        db.users.delete_one({"_id": ObjectId(uid)})


# --------------------------------------------------------------------------
# Not-found & unauth guardrails
# --------------------------------------------------------------------------
def test_unauth_endpoints_reject():
    r = requests.post(f"{BASE_URL}/api/findings/deadbeefdeadbeefdeadbeef/confirm", timeout=15)
    assert r.status_code == 401
    r = requests.get(f"{BASE_URL}/api/accuracy", timeout=15)
    assert r.status_code == 401


def test_invalid_finding_id_returns_404(user_a):
    s, _, _ = user_a
    r = s.post(f"{BASE_URL}/api/findings/not-a-real-id/confirm", timeout=15)
    assert r.status_code == 404
    # syntactically valid but nonexistent
    r = s.post(f"{BASE_URL}/api/findings/{ObjectId()}/confirm", timeout=15)
    assert r.status_code == 404
