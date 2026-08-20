"""
Focused verification for the Stage 3 no-op fix on POST /api/findings/{id}/correct:

Cases:
  1) No-change Correct is a true no-op (finding + accuracy unchanged)
  2) Real correction still persists and updates /accuracy by exactly +1
  3) Sequence integrity: real correction, then no-change save must not
     duplicate corrected_fields or double-count accuracy
"""
import os
import uuid
import copy
from datetime import datetime

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://crazy-babbage-9.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]

EDITABLE = [
    "effective_date", "initial_term_value", "initial_term_unit", "renewal_type",
    "renewal_period_value", "renewal_period_unit", "notice_days_min",
    "notice_days_max", "notice_basis", "business_day_definition",
    "notice_measured_to", "deemed_receipt_rule", "notice_method",
    "notice_recipient",
]


def _register():
    email = f"noop_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": "Test1234!"}, timeout=30)
    assert r.status_code == 200, r.text
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
    return s, me["id"]


def _seed_contract(user_id):
    cid = ObjectId()
    db.contracts.insert_one({
        "_id": cid, "user_id": user_id,
        "name": f"TEST_{uuid.uuid4().hex[:6]}",
        "counterparty": None, "status": "analysed",
        "created_at": datetime.utcnow().isoformat(),
    })
    return str(cid)


def _seed_finding(user_id, contract_id, extracted, state="unconfirmed",
                  validation_status="needs_review"):
    fid = ObjectId()
    db.findings.insert_one({
        "_id": fid, "contract_id": contract_id, "user_id": user_id,
        "type": "renewal_notice",
        "extracted": copy.deepcopy(extracted),
        "sources": [{
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
        "confidence": "medium", "action_required": True,
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
    })
    return str(fid)


NULL_EXTRACTED = {
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
}


@pytest.fixture(scope="module")
def user():
    s, uid = _register()
    yield s, uid
    db.findings.delete_many({"user_id": uid})
    db.contracts.delete_many({"user_id": uid})
    try:
        db.users.delete_one({"_id": ObjectId(uid)})
    except Exception:
        pass


# ---------------------------------------------------------------- Case 1
def test_no_change_correct_is_true_noop(user):
    """POST /correct with body equal to current extracted -> no-op."""
    s, uid = user
    cid = _seed_contract(uid)
    # Seed a fully-populated, validated finding
    extracted = {
        "effective_date": "2025-01-01",
        "initial_term_value": 1, "initial_term_unit": "years",
        "renewal_type": "automatic",
        "renewal_period_value": 1, "renewal_period_unit": "years",
        "notice_days_min": 30, "notice_days_max": None,
        "notice_basis": "calendar", "business_day_definition": None,
        "notice_measured_to": "sent", "deemed_receipt_rule": None,
        "notice_method": "written", "notice_recipient": "Counterparty",
        "next_renewal_date": "2027-01-01",
        "action_deadline": "2026-12-02",
        "earliest_action_date": None,
        "effective_action_deadline": "2026-12-02",
        "days_remaining": 365,
    }
    fid = _seed_finding(uid, cid, extracted, state="unconfirmed",
                        validation_status="validated")

    before = db.findings.find_one({"_id": ObjectId(fid)})

    # Body equal to current editable extracted values
    payload = {k: extracted[k] for k in EDITABLE}
    r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    resp = r.json()
    assert resp["changed_fields"] == []
    assert resp.get("no_change") is True

    # Response finding must reflect UNCHANGED state
    f = resp["finding"]
    assert f["state"] == "unconfirmed", f"state must not flip: got {f['state']}"
    assert f["corrected_fields"] == []
    assert f["original_values"] == {}
    assert f["confirmed_at"] is None
    assert f["validation_status"] == "validated"
    assert f["extracted"] == extracted

    # Persisted doc byte-for-byte unchanged
    after = db.findings.find_one({"_id": ObjectId(fid)})
    assert before == after, "no-op must not touch the DB doc"


# ---------------------------------------------------------------- Case 2
def test_no_change_correct_does_not_move_accuracy():
    """Fresh user: accuracy is zero before and after a no-op correct save."""
    s, uid = _register()
    try:
        # Fresh /accuracy
        r0 = s.get(f"{BASE_URL}/api/accuracy", timeout=15)
        assert r0.status_code == 200
        a0 = r0.json()
        assert a0["findings_reviewed"] == 0
        assert a0["corrected"] == 0
        assert a0["correction_rate_pct"] == 0.0
        assert a0["corrected_field_frequency"] == {}

        # Seed one finding (populated so no-change is unambiguous)
        cid = _seed_contract(uid)
        extracted = {
            "effective_date": "2025-01-01",
            "initial_term_value": 1, "initial_term_unit": "years",
            "renewal_type": "automatic",
            "renewal_period_value": 1, "renewal_period_unit": "years",
            "notice_days_min": 30, "notice_days_max": None,
            "notice_basis": "calendar", "business_day_definition": None,
            "notice_measured_to": "sent", "deemed_receipt_rule": None,
            "notice_method": "written", "notice_recipient": "Counterparty",
            "next_renewal_date": "2027-01-01",
            "action_deadline": "2026-12-02",
            "earliest_action_date": None,
            "effective_action_deadline": "2026-12-02",
            "days_remaining": 365,
        }
        fid = _seed_finding(uid, cid, extracted, state="unconfirmed",
                            validation_status="validated")

        payload = {k: extracted[k] for k in EDITABLE}
        r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=15)
        assert r.status_code == 200
        assert r.json()["changed_fields"] == []

        r1 = s.get(f"{BASE_URL}/api/accuracy", timeout=15)
        assert r1.status_code == 200
        a1 = r1.json()
        # The counting fields must be identical (the finding must NOT be
        # counted as corrected/reviewed by the no-op save).
        for key in ("findings_reviewed", "confirmed_no_edits", "corrected",
                    "correction_rate_pct", "corrected_field_frequency"):
            assert a1[key] == a0[key], f"{key} moved on no-op: {a0[key]} -> {a1[key]}"
        bt = a1.get("by_type", {}).get("renewal_notice",
                                       {"reviewed": 0, "confirmed_no_edits": 0, "corrected": 0})
        assert bt == {"reviewed": 0, "confirmed_no_edits": 0, "corrected": 0}, bt
    finally:
        db.findings.delete_many({"user_id": uid})
        db.contracts.delete_many({"user_id": uid})
        try:
            db.users.delete_one({"_id": ObjectId(uid)})
        except Exception:
            pass


# ---------------------------------------------------------------- Case 3
def test_real_correction_updates_state_and_accuracy():
    """Real correction persists state=corrected and bumps /accuracy by 1."""
    s, uid = _register()
    try:
        cid = _seed_contract(uid)
        fid = _seed_finding(uid, cid, NULL_EXTRACTED,
                            state="unconfirmed", validation_status="needs_review")

        # /accuracy baseline
        base = s.get(f"{BASE_URL}/api/accuracy", timeout=15).json()

        payload = {
            "effective_date": "2025-06-01",
            "initial_term_value": 1, "initial_term_unit": "years",
            "renewal_type": "automatic",
            "renewal_period_value": 1, "renewal_period_unit": "years",
            "notice_days_min": 30, "notice_days_max": None,
            "notice_basis": "calendar", "business_day_definition": None,
            "notice_measured_to": "sent", "deemed_receipt_rule": None,
            "notice_method": "written", "notice_recipient": "Counterparty",
        }
        r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        resp = r.json()
        f = resp["finding"]
        assert f["state"] == "corrected"
        assert f["validation_status"] == "validated"
        assert set(resp["changed_fields"]) == {"effective_date",
                                               "initial_term_value",
                                               "initial_term_unit"}
        assert set(f["corrected_fields"]) == set(resp["changed_fields"])
        assert f["original_values"]["effective_date"] is None
        assert f["original_values"]["initial_term_value"] is None
        assert f["original_values"]["initial_term_unit"] is None
        # Derived recomputed deterministically
        assert f["extracted"]["next_renewal_date"] is not None
        assert f["extracted"]["effective_action_deadline"] is not None

        after = s.get(f"{BASE_URL}/api/accuracy", timeout=15).json()
        assert after["corrected"] == base["corrected"] + 1
        assert after["findings_reviewed"] == base["findings_reviewed"] + 1
        freq = after["corrected_field_frequency"]
        assert freq.get("effective_date", 0) == base["corrected_field_frequency"].get("effective_date", 0) + 1
        assert freq.get("initial_term_value", 0) == base["corrected_field_frequency"].get("initial_term_value", 0) + 1
        assert freq.get("initial_term_unit", 0) == base["corrected_field_frequency"].get("initial_term_unit", 0) + 1
    finally:
        db.findings.delete_many({"user_id": uid})
        db.contracts.delete_many({"user_id": uid})
        try:
            db.users.delete_one({"_id": ObjectId(uid)})
        except Exception:
            pass


# ---------------------------------------------------------------- Case 4
def test_real_then_noop_does_not_double_count():
    """After a real correction, a subsequent no-change save is still a no-op:
    corrected_fields unchanged, /accuracy unchanged."""
    s, uid = _register()
    try:
        cid = _seed_contract(uid)
        fid = _seed_finding(uid, cid, NULL_EXTRACTED,
                            state="unconfirmed", validation_status="needs_review")

        # First: real correction
        payload = {
            "effective_date": "2025-06-01",
            "initial_term_value": 1, "initial_term_unit": "years",
            "renewal_type": "automatic",
            "renewal_period_value": 1, "renewal_period_unit": "years",
            "notice_days_min": 30, "notice_days_max": None,
            "notice_basis": "calendar", "business_day_definition": None,
            "notice_measured_to": "sent", "deemed_receipt_rule": None,
            "notice_method": "written", "notice_recipient": "Counterparty",
        }
        r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=15)
        assert r.status_code == 200
        f1 = r.json()["finding"]
        assert f1["state"] == "corrected"
        cf1 = sorted(f1["corrected_fields"])
        ov1 = f1["original_values"]
        conf1 = f1["confirmed_at"]

        acc_mid = s.get(f"{BASE_URL}/api/accuracy", timeout=15).json()
        doc_mid = db.findings.find_one({"_id": ObjectId(fid)})

        # Second: identical payload -> should be no-op
        r2 = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=15)
        assert r2.status_code == 200
        resp2 = r2.json()
        assert resp2["changed_fields"] == []
        assert resp2.get("no_change") is True
        f2 = resp2["finding"]
        assert f2["state"] == "corrected"  # remains corrected
        assert sorted(f2["corrected_fields"]) == cf1  # no duplicates
        assert f2["original_values"] == ov1
        assert f2["confirmed_at"] == conf1

        # Accuracy unchanged
        acc_after = s.get(f"{BASE_URL}/api/accuracy", timeout=15).json()
        assert acc_after == acc_mid

        # DB doc unchanged by the no-op
        doc_after = db.findings.find_one({"_id": ObjectId(fid)})
        assert doc_after == doc_mid
    finally:
        db.findings.delete_many({"user_id": uid})
        db.contracts.delete_many({"user_id": uid})
        try:
            db.users.delete_one({"_id": ObjectId(uid)})
        except Exception:
            pass
