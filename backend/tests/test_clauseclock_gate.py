"""ClauseClock Stage 1 GATE verification test.

Uploads 5 deliberately difficult text-based contracts + 1 scanned PDF against
the real ingestion API and asserts readable extraction + usable location
markers. The scanned PDF must trigger the exact SCANNED_MESSAGE.

Fixtures are pre-generated at /app/backend/tests/gate_*.
"""
import os
import re

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SEED_EMAIL = "test@clauseclock.app"
SEED_PASSWORD = "Test1234!"

SCANNED_MSG = (
    "This looks like a scanned or image-based PDF. ClauseClock cannot read it "
    "yet. Upload a text-based version."
)

FIX = "/app/backend/tests"


# ---------------- fixtures ----------------
@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    assert r.status_code == 200, f"seed login failed: {r.text}"
    return s


@pytest.fixture(scope="module")
def created_ids():
    """Collects contract ids so module teardown can hard-delete them all."""
    return []


@pytest.fixture(scope="module")
def gridfs_baseline():
    import pymongo
    mc = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = mc[os.environ["DB_NAME"]]
    baseline = db["fs.files"].count_documents({})
    yield baseline, db
    mc.close()


def _upload(sess, path, doc_role="primary", **form):
    with open(path, "rb") as fh:
        mime = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if path.endswith(".docx") else "application/pdf")
        files = {"file": (os.path.basename(path), fh.read(), mime)}
    data = {"name": f"TEST_gate_{os.path.basename(path)}",
            "doc_role": doc_role, **{k: str(v) for k, v in form.items()}}
    r = sess.post(f"{API}/contracts", files=files, data=data)
    assert r.status_code == 200, f"upload failed {path}: {r.status_code} {r.text}"
    return r.json()


# ---------------- GATE 1: DOCX ----------------
class TestGate1Docx:
    def test_docx_extraction_markers_and_content(self, sess, created_ids):
        body = _upload(sess, f"{FIX}/gate_docx.docx",
                       doc_role="primary", annual_value=24000, currency="USD")
        c, d = body["contract"], body["document"]
        created_ids.append(c["id"])

        assert d["extraction_method"] == "python-docx", d["extraction_method"]
        rt = d["raw_text"] or ""
        assert rt.strip(), "raw_text empty"
        # location markers
        assert "[§" in rt, "missing heading/section marker '[§'"
        assert "¶" in rt, "missing paragraph marker '¶'"
        assert "[Table" in rt, "missing table marker '[Table'"
        # content
        assert "$24,000" in rt or "24,000" in rt, "missing $24,000 fee content"
        assert "Appendix A" in rt or "APPENDIX A" in rt, "missing Appendix A"


# ---------------- GATE 2: Two-column PDF ----------------
class TestGate2TwoCol:
    def test_twocol_pdf_readable_with_page_markers(self, sess, created_ids):
        body = _upload(sess, f"{FIX}/gate_twocol.pdf", doc_role="primary")
        c, d = body["contract"], body["document"]
        created_ids.append(c["id"])

        assert d["extraction_method"] == "pdfplumber", d["extraction_method"]
        assert d["page_count"] == 3, f"expected 3 pages got {d['page_count']}"
        rt = (d["raw_text"] or "").lower()
        assert rt.strip(), "raw_text empty"
        # per-page markers
        for p in (1, 2, 3):
            assert f"page {p}" in rt, f"missing 'Page {p}' marker"
        # renewal / notice clause words (readable, column interleaving accepted)
        assert "automatically renew" in rt, "missing 'automatically renew'"
        assert "sixty (60)" in rt, "missing 'sixty (60)'"
        assert "certified mail" in rt, "missing 'certified mail'"


# ---------------- GATE 3: 40+ pages ----------------
class TestGate3LongPdf:
    def test_40page_pdf_has_all_page_markers(self, sess, created_ids):
        body = _upload(sess, f"{FIX}/gate_40pages.pdf", doc_role="primary")
        c, d = body["contract"], body["document"]
        created_ids.append(c["id"])

        assert d["extraction_method"] == "pdfplumber"
        assert d["page_count"] >= 40, f"expected >=40 pages got {d['page_count']}"
        rt = d["raw_text"] or ""
        assert rt.strip(), "raw_text empty"
        distinct = set(re.findall(r"Page\s+(\d+)", rt))
        assert len(distinct) >= 40, f"expected >=40 distinct Page markers, got {len(distinct)}"


# ---------------- GATE 4: Terms in appendix ----------------
class TestGate4Appendix:
    def test_appendix_page2_captured(self, sess, created_ids):
        body = _upload(sess, f"{FIX}/gate_appendix.pdf",
                       doc_role="primary", annual_value=48000)
        c, d = body["contract"], body["document"]
        created_ids.append(c["id"])

        assert d["extraction_method"] == "pdfplumber"
        rt = d["raw_text"] or ""
        assert rt.strip(), "raw_text empty"
        # locate the Page 2 marker and verify appendix content after it
        m = re.search(r"Page\s+2\b", rt)
        assert m, "missing 'Page 2' marker"
        after_p2 = rt[m.end():]
        assert "APPENDIX B" in after_p2, "APPENDIX B not found after Page 2 marker"
        assert "$48,000" in after_p2, "$48,000 not found after Page 2 marker"
        assert "capped at eight percent (8%)" in after_p2, \
            "'capped at eight percent (8%)' not found after Page 2 marker"


# ---------------- GATE 5: Tables ----------------
class TestGate5Tables:
    def test_tables_extracted(self, sess, created_ids):
        body = _upload(sess, f"{FIX}/gate_tables.pdf", doc_role="primary")
        c, d = body["contract"], body["document"]
        created_ids.append(c["id"])

        assert d["extraction_method"] == "pdfplumber"
        rt = d["raw_text"] or ""
        assert rt.strip(), "raw_text empty"
        assert "[Table" in rt, "missing '[Table' marker"
        for cell in ("Bronze", "$24,000", "Gold", "$48,000", "Cap %"):
            assert cell in rt, f"missing table cell value: {cell}"


# ---------------- SCANNED GUARDRAIL ----------------
class TestScannedGuardrail:
    def test_scanned_pdf_returns_exact_message(self, sess, created_ids):
        body = _upload(sess, f"{FIX}/gate_scanned.pdf", doc_role="primary")
        c, d = body["contract"], body["document"]
        created_ids.append(c["id"])

        assert d["extraction_method"] == "failed_no_text", d["extraction_method"]
        warnings = d.get("extraction_warnings") or []
        # extraction_warnings may be list or string — check exact message present
        if isinstance(warnings, list):
            assert SCANNED_MSG in warnings, f"exact scanned message missing: {warnings}"
        else:
            assert SCANNED_MSG == warnings or SCANNED_MSG in warnings, \
                f"exact scanned message missing: {warnings}"
        # raw_text effectively empty (only auto-inserted page markers, no content)
        cleaned = re.sub(r"={5,}\s*Page\s+\d+\s*={5,}", "",
                         d.get("raw_text") or "").strip()
        assert not cleaned, \
            f"raw_text should be effectively empty for scanned, got: {cleaned!r}"

        # GET contract detail surfaces the same
        r = sess.get(f"{API}/contracts/{c['id']}")
        assert r.status_code == 200
        detail = r.json()
        assert len(detail["documents"]) == 1
        doc = detail["documents"][0]
        assert doc["extraction_method"] == "failed_no_text"
        cleaned2 = re.sub(r"={5,}\s*Page\s+\d+\s*={5,}", "",
                          doc.get("raw_text") or "").strip()
        assert not cleaned2
        dw = doc.get("extraction_warnings") or []
        if isinstance(dw, list):
            assert SCANNED_MSG in dw
        else:
            assert SCANNED_MSG in dw


# ---------------- CLEANUP + GridFS baseline verify ----------------
class TestZZCleanup:
    """Runs last (alphabetical). Deletes every created contract and asserts
    GridFS fs.files returns to pre-run baseline."""

    def test_hard_delete_all_and_verify_gridfs(self, sess, created_ids, gridfs_baseline):
        baseline, db = gridfs_baseline
        assert created_ids, "no contracts were created — earlier tests failed"

        # Delete every contract created in this run
        for cid in created_ids:
            r = sess.delete(f"{API}/contracts/{cid}")
            assert r.status_code == 200, f"delete failed for {cid}: {r.text}"
            assert r.json().get("deleted") is True
            r2 = sess.get(f"{API}/contracts/{cid}")
            assert r2.status_code == 404

        # Belt-and-braces: also purge any dangling TEST_gate contracts owned
        # by the seeded user (e.g. leftovers from a prior interrupted run
        # captured inside `baseline`).
        listing = sess.get(f"{API}/contracts").json().get("contracts", [])
        for c in listing:
            if c["name"].startswith("TEST_gate_"):
                sess.delete(f"{API}/contracts/{c['id']}")

        # Seeded user should now have 0 TEST_ contracts
        remaining = [c for c in sess.get(f"{API}/contracts").json()["contracts"]
                     if c["name"].startswith("TEST_")]
        assert not remaining, f"TEST_ contracts still exist: {remaining}"

        # GridFS baseline restored (allow <= baseline if pre-run baseline itself
        # contained orphaned TEST_gate files we've now cleaned).
        after = db["fs.files"].count_documents({})
        assert after <= baseline, \
            f"GridFS grew: baseline={baseline} after={after}"
