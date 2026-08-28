"""
Verification for:
  1) GET /api/contracts/{contract_id}/superseded-history user-scoped endpoint.
  2) Resolution of document metadata (filename, doc_role, location) in finding sources.
  3) Deduplication of identical source rows in superseded history.
  4) Verification that normal findings endpoints skip superseded findings.
  5) Correct lapsed ranking semantics (days_remaining < 0 are NOT urgent).
"""
import os
import uuid
from datetime import datetime, timezone

import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://clock-continue.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]


def _register():
    email = f"superseded_{uuid.uuid4().hex[:10]}@example.com"
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
        "counterparty": "Test Corp", "status": "analysed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return str(cid)


def _seed_document(user_id, contract_id, filename, doc_role):
    did = ObjectId()
    db.documents.insert_one({
        "_id": did, "user_id": user_id, "contract_id": contract_id,
        "filename": filename, "doc_role": doc_role, "file_type": "pdf",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    return str(did)


def _seed_finding(user_id, contract_id, extracted, state="unconfirmed",
                  validation_status="needs_review", superseded_by_finding_id=None, sources=None):
    fid = ObjectId()
    db.findings.insert_one({
        "_id": fid, "user_id": user_id, "contract_id": contract_id,
        "type": "renewal_notice", "extracted": extracted,
        "sources": sources or [], "confidence": "high",
        "action_required": True, "rank_category": "informational", "rank_score": 0,
        "validation_status": validation_status, "state": state,
        "superseded_by_finding_id": superseded_by_finding_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return str(fid)


def test_superseded_history_and_lapsed_ranking():
    s, uid = _register()
    cid = _seed_contract(uid)
    
    # 1. Seed two documents to resolve source metadata
    doc1_id = _seed_document(uid, cid, "main_agreement.pdf", "primary")
    doc2_id = _seed_document(uid, cid, "amendment_v1.pdf", "amendment")
    
    # 2. Prepare sources (with intentional duplicate rows to test deduplication)
    sources = [
        # Source 1 (unique)
        {
            "purpose": "renewal_period",
            "chunk_id": "chunk_01",
            "document_id": doc1_id,
            "quote": "This agreement shall renew for 12 months.",
            "location": "Section 4.1, Page 3",
            "char_offset": 120
        },
        # Source 2 (unique)
        {
            "purpose": "notice_period",
            "chunk_id": "chunk_02",
            "document_id": doc2_id,
            "quote": "Notice must be given 30 days prior.",
            "location": "Section 1, Page 1",
            "char_offset": 50
        },
        # Source 3 (Duplicate of Source 2: same purpose, quote, document, location)
        {
            "purpose": "notice_period",
            "chunk_id": "chunk_02",
            "document_id": doc2_id,
            "quote": "Notice must be given 30 days prior.",
            "location": "Section 1, Page 1",
            "char_offset": 50
        }
    ]
    
    # 3. Seed finding 1: Current / active finding (not superseded)
    curr_fid = _seed_finding(uid, cid, {"days_remaining": 10}, state="confirmed", validation_status="validated", sources=sources[:2])
    
    # 4. Seed finding 2: Superseded finding (superseded_by_finding_id = curr_fid)
    sup_fid = _seed_finding(
        uid, cid, {"days_remaining": 45}, state="confirmed", validation_status="validated",
        superseded_by_finding_id=curr_fid, sources=sources
    )
    
    # 5. Verify GET /api/contracts/{contract_id}/findings (Normal endpoint)
    # The superseded finding must NOT be returned as current finding, and the current finding must be returned.
    r = s.get(f"{BASE_URL}/api/contracts/{cid}/findings", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    findings = data["findings"]
    assert len(findings) == 1, f"Expected 1 active finding, got {len(findings)}"
    assert findings[0]["id"] == curr_fid
    assert data["superseded_count"] == 1
    
    # 6. Verify GET /api/contracts/{contract_id}/superseded-history
    r = s.get(f"{BASE_URL}/api/contracts/{cid}/superseded-history", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    history = data["history"]
    assert len(history) == 1, f"Expected 1 superseded finding, got {len(history)}"
    
    sup_find = history[0]
    assert sup_find["id"] == sup_fid
    assert sup_find["superseded_by_finding_id"] == curr_fid
    assert sup_find["replacement_relationship"]["superseded_by_finding_id"] == curr_fid
    assert sup_find["replacement_relationship"]["replacement_finding"]["id"] == curr_fid
    
    # 7. Check resolved document metadata and source deduplication
    returned_sources = sup_find["sources"]
    # We started with 3 sources, but 2 was duplicate of 3. So we expect exactly 2 sources.
    assert len(returned_sources) == 2, f"Expected 2 deduplicated sources, got {len(returned_sources)}"
    
    # Verify metadata is resolved
    s1 = next(src for src in returned_sources if src["chunk_id"] == "chunk_01")
    assert s1["document_metadata"] is not None
    assert s1["document_metadata"]["filename"] == "main_agreement.pdf"
    assert s1["document_metadata"]["doc_role"] == "primary"
    
    s2 = next(src for src in returned_sources if src["chunk_id"] == "chunk_02")
    assert s2["document_metadata"] is not None
    assert s2["document_metadata"]["filename"] == "amendment_v1.pdf"
    assert s2["document_metadata"]["doc_role"] == "amendment"
    
    # 8. Test Lapsed Ranking: actionable deadlines with days_remaining < 0 are NOT categorized urgent
    # Let's seed a finding with days_remaining = -5, which is past/lapsed.
    # Note: action_center gets only confirmed/corrected actionable findings.
    lapsed_fid = _seed_finding(uid, cid, {"days_remaining": -5, "effective_action_deadline": "2025-11-20"}, state="confirmed", validation_status="validated")
    
    r = s.get(f"{BASE_URL}/api/action-center", timeout=15)
    assert r.status_code == 200, r.text
    ac_data = r.json()
    buckets = ac_data["buckets"]
    
    # The lapsed finding (days_remaining = -5 < 0) must be in "later", NOT in "urgent"
    urgent_ids = [item["id"] for item in buckets["urgent"]]
    next_30_ids = [item["id"] for item in buckets["next_30_days"]]
    later_ids = [item["id"] for item in buckets["later"]]
    
    assert lapsed_fid not in urgent_ids, f"Lapsed finding {lapsed_fid} should not be in 'urgent' bucket"
    assert lapsed_fid not in next_30_ids, f"Lapsed finding {lapsed_fid} should not be in 'next_30_days' bucket"
    assert lapsed_fid in later_ids, f"Lapsed finding {lapsed_fid} must be in 'later' bucket, but wasn't"
    
    print("ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_superseded_history_and_lapsed_ranking()
