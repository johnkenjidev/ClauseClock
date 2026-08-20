"""
Stage 4 tests — What Matters ranking + provenance-bound explanations.

Ranking is pure/deterministic and refreshed on read. Explanations are only
generated for validated findings, strictly from validated source quotes +
server-computed facts. Needs_review findings never receive an explanation.
"""
import os
import time
import uuid
from datetime import date, datetime, timedelta

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient
from dateutil.relativedelta import relativedelta

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]


# --------------------------------------------------------------------------
# helpers (mirror Stage 3 seed pattern)
# --------------------------------------------------------------------------
def _register(email=None, password="Test1234!"):
    email = email or f"t4_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
    return s, me["id"], email


def _seed_contract(user_id, annual_value=None):
    cid = ObjectId()
    db.contracts.insert_one({
        "_id": cid, "user_id": user_id,
        "name": f"TEST_{uuid.uuid4().hex[:6]}", "counterparty": None,
        "status": "analysed", "annual_value": annual_value,
        "currency": "USD" if annual_value else None,
        "created_at": datetime.utcnow().isoformat(),
    })
    return str(cid)


def _seed_finding(user_id, contract_id, extracted=None, sources=None,
                  validation_status="needs_review", state="unconfirmed",
                  action_required=True, money_amount=None, money_kind=None,
                  plain_english=None, why_it_matters=None,
                  suggested_action=None, explanation_generated_at=None):
    fid = ObjectId()
    doc = {
        "_id": fid, "contract_id": contract_id, "user_id": user_id,
        "type": "renewal_notice",
        "extracted": extracted or {
            "effective_date": None, "initial_term_value": None,
            "initial_term_unit": None, "renewal_type": "automatic",
            "renewal_period_value": 1, "renewal_period_unit": "years",
            "notice_days_min": 30, "notice_days_max": None,
            "notice_basis": "calendar", "business_day_definition": None,
            "notice_measured_to": "sent", "deemed_receipt_rule": None,
            "notice_method": "written", "notice_recipient": "Counterparty",
            "next_renewal_date": None, "action_deadline": None,
            "earliest_action_date": None, "effective_action_deadline": None,
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
        "confidence": "medium", "action_required": action_required,
        "money_amount": money_amount, "money_currency": "USD" if money_amount else None,
        "money_kind": money_kind,
        "rank_category": "informational", "rank_score": 0, "rank_basis": {},
        "plain_english": plain_english, "why_it_matters": why_it_matters,
        "suggested_action": suggested_action,
        "explanation_generated_at": explanation_generated_at,
        "validation_status": validation_status, "validation_notes": [],
        "state": state, "original_values": {}, "corrected_fields": [],
        "confirmed_at": None, "superseded_by_finding_id": None,
        "related_finding_ids": [], "is_composite": False, "composite_of": [],
        "created_at": datetime.utcnow().isoformat(),
    }
    db.findings.insert_one(doc)
    return str(fid)


def _validated_extracted(days_until_deadline):
    today = date.today()
    dl = today + timedelta(days=days_until_deadline)
    renewal = dl + timedelta(days=30)
    return {
        "effective_date": (renewal - relativedelta(years=1)).isoformat(),
        "initial_term_value": 1, "initial_term_unit": "years",
        "renewal_type": "automatic",
        "renewal_period_value": 1, "renewal_period_unit": "years",
        "notice_days_min": 30, "notice_days_max": None,
        "notice_basis": "calendar", "business_day_definition": None,
        "notice_measured_to": "sent", "deemed_receipt_rule": None,
        "notice_method": "written", "notice_recipient": "Counterparty",
        "next_renewal_date": renewal.isoformat(),
        "action_deadline": dl.isoformat(),
        "earliest_action_date": None,
        "effective_action_deadline": dl.isoformat(),
        "days_remaining": days_until_deadline,
    }


@pytest.fixture(scope="module")
def user_a():
    s, uid, email = _register()
    yield s, uid, email
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
# 1. Ranking reproducibility & determinism
# --------------------------------------------------------------------------
def test_ranking_reproducible_and_days_refreshed(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid, annual_value=50000)
    ext = _validated_extracted(days_until_deadline=45)
    # Persist a *stale* days_remaining to prove read-time refresh
    ext_stale = dict(ext); ext_stale["days_remaining"] = 9999
    fid = _seed_finding(uid, cid, extracted=ext_stale,
                        validation_status="validated", state="confirmed",
                        money_amount=50000, money_kind="contract_value")

    r1 = s.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    r2 = s.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    assert r1.status_code == 200 and r2.status_code == 200
    f1 = next(f for f in r1.json()["findings"] if f["id"] == fid)
    f2 = next(f for f in r2.json()["findings"] if f["id"] == fid)

    # Reproducibility
    assert f1["rank_score"] == f2["rank_score"]
    assert f1["rank_category"] == f2["rank_category"]
    assert f1["rank_basis"] == f2["rank_basis"]

    # Basis includes as_of_date + inputs
    b = f1["rank_basis"]
    assert b["as_of_date"] == date.today().isoformat()
    assert b["days_remaining"] == 45
    assert b["action_required"] is True
    assert b["money_amount"] == 50000
    assert b["validation_status"] == "validated"

    # days_remaining refreshed from effective_action_deadline
    dl = datetime.strptime(ext["effective_action_deadline"], "%Y-%m-%d").date()
    assert f1["extracted"]["days_remaining"] == (dl - date.today()).days


# --------------------------------------------------------------------------
# 2. Rank ordering + categories
# --------------------------------------------------------------------------
def test_rank_ordering_and_categories(user_b):
    s, uid, _ = user_b
    cid = _seed_contract(uid)

    # a) validated + action + near deadline (10 days) -> urgent, top
    urgent_id = _seed_finding(uid, cid, extracted=_validated_extracted(10),
                              validation_status="validated", state="confirmed",
                              action_required=True)
    # b) validated + action + far deadline (200 days) -> risk
    risk_id = _seed_finding(uid, cid, extracted=_validated_extracted(200),
                            validation_status="validated", state="confirmed",
                            action_required=True)
    # c) validated + money, no action -> money
    money_ext = _validated_extracted(150)
    money_ext["renewal_type"] = "manual"
    money_ext["effective_action_deadline"] = None
    money_ext["action_deadline"] = None
    money_ext["days_remaining"] = None
    money_id = _seed_finding(uid, cid, extracted=money_ext,
                             validation_status="validated", state="confirmed",
                             action_required=False,
                             money_amount=25000, money_kind="contract_value")
    # d) needs_review
    review_id = _seed_finding(uid, cid, validation_status="needs_review",
                              state="unconfirmed")

    r = s.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    assert r.status_code == 200
    order = [f["id"] for f in r.json()["findings"]]
    cats = {f["id"]: f["rank_category"] for f in r.json()["findings"]}

    # DESC by rank_score; validated actionable/near-deadline first
    assert order[0] == urgent_id
    # needs_review last
    assert order[-1] == review_id
    # urgent outranks needs_review
    assert order.index(urgent_id) < order.index(review_id)

    # Category assertions
    assert cats[urgent_id] == "urgent"
    assert cats[risk_id] == "risk"
    assert cats[money_id] == "money"
    # needs_review with action + no deadline days -> "risk" (action True, days None)
    # per compute_rank: action True + days None -> "risk"
    assert cats[review_id] == "risk"


# --------------------------------------------------------------------------
# 3. needs_review suppression — no explanation ever
# --------------------------------------------------------------------------
def test_needs_review_no_explanation(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    fid = _seed_finding(uid, cid, validation_status="needs_review")

    r = s.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    f = next(f for f in r.json()["findings"] if f["id"] == fid)
    assert f["plain_english"] is None
    assert f["why_it_matters"] is None
    assert f["suggested_action"] is None
    assert f["explanation_generated_at"] is None


# --------------------------------------------------------------------------
# 4. Explanation caching, correct flow (validated -> needs_review clears)
# --------------------------------------------------------------------------
def test_correct_to_validated_generates_and_regress_clears(user_a):
    """Correcting needs_review -> validated generates+caches an explanation;
    correcting validated back to needs_review CLEARS cached fields."""
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    fid = _seed_finding(uid, cid, validation_status="needs_review")

    # -> validated
    payload = {
        "effective_date": "2025-06-01", "initial_term_value": 1,
        "initial_term_unit": "years", "renewal_type": "automatic",
        "renewal_period_value": 1, "renewal_period_unit": "years",
        "notice_days_min": 30, "notice_days_max": None,
        "notice_basis": "calendar", "business_day_definition": None,
        "notice_measured_to": "sent", "deemed_receipt_rule": None,
        "notice_method": "written", "notice_recipient": "Counterparty",
    }
    r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=90)
    assert r.status_code == 200, r.text
    f = r.json()["finding"]
    assert f["validation_status"] == "validated"
    assert f["plain_english"], f"plain_english missing: {f}"
    assert f["why_it_matters"]
    assert f["suggested_action"]
    assert f["explanation_generated_at"] is not None

    # Provenance: explanation must not invent a party/date absent from sources.
    # sources reference "either party" and "thirty (30) days"; deadline computed.
    combined = " ".join([f["plain_english"], f["why_it_matters"],
                         f["suggested_action"]]).lower()
    # Should NOT invent an unrelated recipient not in the seeded sources
    # (sources say "Counterparty" via extracted, quotes say "either party").
    # Sanity: must reference at least one grounded token.
    assert ("30" in combined or "thirty" in combined or "notice" in combined
            or "renew" in combined)

    # -> back to needs_review (blank out effective_date)
    payload2 = dict(payload)
    payload2["effective_date"] = None
    r2 = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload2, timeout=30)
    assert r2.status_code == 200, r2.text
    f2 = r2.json()["finding"]
    assert f2["validation_status"] == "needs_review"
    assert f2["plain_english"] is None
    assert f2["why_it_matters"] is None
    assert f2["suggested_action"] is None
    assert f2["explanation_generated_at"] is None


# --------------------------------------------------------------------------
# 5. No-change correct is a true no-op (Stage 3 regression)
# --------------------------------------------------------------------------
def test_correct_nochange_noop(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    ext = _validated_extracted(45)
    fid = _seed_finding(uid, cid, extracted=ext,
                        validation_status="validated", state="confirmed",
                        plain_english="cached PE",
                        why_it_matters="cached WIM",
                        suggested_action="cached SA",
                        explanation_generated_at="2025-01-01T00:00:00+00:00")
    payload = {
        "effective_date": ext["effective_date"],
        "initial_term_value": ext["initial_term_value"],
        "initial_term_unit": ext["initial_term_unit"],
        "renewal_type": ext["renewal_type"],
        "renewal_period_value": ext["renewal_period_value"],
        "renewal_period_unit": ext["renewal_period_unit"],
        "notice_days_min": ext["notice_days_min"],
        "notice_days_max": ext["notice_days_max"],
        "notice_basis": ext["notice_basis"],
        "business_day_definition": ext["business_day_definition"],
        "notice_measured_to": ext["notice_measured_to"],
        "deemed_receipt_rule": ext["deemed_receipt_rule"],
        "notice_method": ext["notice_method"],
        "notice_recipient": ext["notice_recipient"],
    }
    r = s.post(f"{BASE_URL}/api/findings/{fid}/correct", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("no_change") is True
    assert body["changed_fields"] == []
    # Cached explanation preserved
    assert body["finding"]["plain_english"] == "cached PE"
    assert body["finding"]["explanation_generated_at"] == "2025-01-01T00:00:00+00:00"


# --------------------------------------------------------------------------
# 6. Cross-user isolation
# --------------------------------------------------------------------------
def test_cross_user_findings_404(user_a, user_b):
    sa, ua, _ = user_a
    sb, ub, _ = user_b
    cid = _seed_contract(ua)
    fid = _seed_finding(ua, cid, validation_status="needs_review")

    # user_b cannot see A's contract findings list (empty or 404)
    r = sb.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    assert r.status_code == 404
    # user_b cannot correct A's finding
    r2 = sb.post(f"{BASE_URL}/api/findings/{fid}/correct", json={
        "effective_date": None, "initial_term_value": None,
        "initial_term_unit": None, "renewal_type": None,
        "renewal_period_value": None, "renewal_period_unit": None,
        "notice_days_min": None, "notice_days_max": None,
        "notice_basis": None, "business_day_definition": None,
        "notice_measured_to": None, "deemed_receipt_rule": None,
        "notice_method": None, "notice_recipient": None,
    }, timeout=15)
    assert r2.status_code == 404


# --------------------------------------------------------------------------
# 7. Evidence primary — sources are still returned intact with locations
# --------------------------------------------------------------------------
def test_sources_preserved_alongside_explanation(user_a):
    s, uid, _ = user_a
    cid = _seed_contract(uid)
    ext = _validated_extracted(45)
    fid = _seed_finding(uid, cid, extracted=ext,
                        validation_status="validated", state="confirmed",
                        plain_english="cached", why_it_matters="cached",
                        suggested_action="cached",
                        explanation_generated_at="2025-01-01T00:00:00+00:00")
    r = s.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    f = next(x for x in r.json()["findings"] if x["id"] == fid)
    assert f["sources"] and len(f["sources"]) >= 2
    for src in f["sources"]:
        assert src.get("quote")
        assert src.get("location")
        assert src.get("document_id")
        assert src.get("purpose")
