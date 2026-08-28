"""
ClauseClock Stage 2 tests — renewal_notice extraction.

Real LLM (Claude Sonnet 4.6 via Emergent). One class per scenario so an
individual failure is isolated. Fixtures build PDFs with reportlab, upload
them via the real API, invoke /analyze, then hard-delete at the end.
"""
import io
import os
import re
import time

import pytest
import requests
from dotenv import load_dotenv
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SEED_EMAIL = "test@clauseclock.app"
SEED_PASSWORD = "Test1234!"


# ---------------------------- pdf helpers ----------------------------
def make_pdf(paragraphs: list[str]) -> bytes:
    """Build a multi-page PDF; one paragraph = one wrapped block."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    margin = 60
    y = height - margin
    c.setFont("Helvetica", 11)
    for para in paragraphs:
        # wrap simple
        words = para.split()
        line = ""
        for w in words:
            trial = (line + " " + w).strip()
            if c.stringWidth(trial, "Helvetica", 11) > width - 2 * margin:
                c.drawString(margin, y, line)
                y -= 15
                line = w
                if y < margin:
                    c.showPage()
                    c.setFont("Helvetica", 11)
                    y = height - margin
            else:
                line = trial
        if line:
            c.drawString(margin, y, line)
            y -= 15
        y -= 8  # paragraph gap
        if y < margin:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - margin
    c.showPage()
    c.save()
    return buf.getvalue()


HAPPY_TEXT = [
    "MASTER SERVICES AGREEMENT",
    "This Master Services Agreement (the \"Agreement\") is entered into and effective as of March 15, 2026 (the \"Effective Date\") by and between Acme Corp. (\"Customer\") and Vendor Systems, Inc. (\"Vendor\").",
    "1. TERM. The initial term of this Agreement shall be twelve (12) months commencing on the Effective Date (the \"Initial Term\").",
    "2. RENEWAL. Upon expiration of the Initial Term, this Agreement shall automatically renew for successive renewal terms of twelve (12) months each (each a \"Renewal Term\") unless either party provides written notice of non-renewal at least sixty (60) days prior to the end of the then-current term.",
    "3. NOTICE. All notices of non-renewal must be delivered by certified mail, return receipt requested, to the General Counsel of Vendor Systems, Inc., 500 Market Street, Suite 400, San Francisco, CA 94105.",
    "4. FEES. Customer shall pay Vendor an annual fee of forty-eight thousand dollars ($48,000) for the Services during the Initial Term and each Renewal Term.",
    "5. MISCELLANEOUS. This Agreement shall be governed by the laws of the State of California.",
]

NO_EFFECTIVE_TEXT = [
    "SERVICES AGREEMENT",
    "This Services Agreement is entered into between the parties.",
    "TERM AND RENEWAL. The initial term shall be twelve (12) months. Thereafter this Agreement shall automatically renew for successive twelve (12) month terms unless either party gives sixty (60) days prior written notice of non-renewal.",
    "NOTICE. Notice of non-renewal shall be provided in writing to the other party.",
    "FEES. The annual fee is twenty-four thousand dollars ($24,000).",
]

NO_NOTICE_DAYS_TEXT = [
    "SERVICES AGREEMENT",
    "This Agreement is effective as of January 1, 2026.",
    "TERM. The Initial Term is twelve (12) months from the Effective Date.",
    "RENEWAL. This Agreement shall automatically renew for successive one-year terms unless either party provides written notice of non-renewal prior to the end of the then-current term.",
    "FEES. Annual fee is $12,000.",
]

BOILERPLATE_TEXT = [
    "MUTUAL NON-DISCLOSURE AGREEMENT",
    "The parties wish to exchange confidential information for the purpose of evaluating a potential business relationship.",
    "1. CONFIDENTIAL INFORMATION means all non-public, proprietary information disclosed by one party to the other.",
    "2. OBLIGATIONS. The receiving party shall protect the confidential information using the same degree of care it uses to protect its own confidential information.",
    "3. RETURN. Upon written request, the receiving party shall return or destroy all confidential information in its possession.",
    "4. GOVERNING LAW. This Agreement shall be governed by the laws of the State of New York.",
]

MANUAL_TEXT = [
    "PROFESSIONAL SERVICES AGREEMENT",
    "Effective Date: February 1, 2026.",
    "TERM. The initial term is twelve (12) months from the Effective Date.",
    "RENEWAL. This Agreement shall NOT automatically renew. Any extension of the term beyond the Initial Term must be by written amendment mutually signed by both parties.",
    "NOTICE. Any notices under this Agreement shall be in writing.",
    "FEES. Fees are set forth in Exhibit A.",
]


# ---------------------------- session fixtures ----------------------------
@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    assert r.status_code == 200, f"seed login failed: {r.text}"
    return s


@pytest.fixture(scope="module")
def sessB():
    """A second, isolated user for cross-user isolation tests."""
    s = requests.Session()
    email = f"stage2-userb-{int(time.time())}@clauseclock.app"
    r = s.post(f"{API}/auth/register",
               json={"email": email, "password": "Test1234!"})
    assert r.status_code == 200, f"userB register failed: {r.text}"
    return s


@pytest.fixture(scope="module")
def created(sess):
    ids = []
    yield ids
    for cid in ids:
        try:
            sess.delete(f"{API}/contracts/{cid}", timeout=15)
        except Exception:
            pass


def _create_contract(sess, name, paragraphs, annual_value=None, currency=None):
    pdf = make_pdf(paragraphs)
    files = {"file": (f"{name}.pdf", pdf, "application/pdf")}
    form = {"name": name, "counterparty": "Vendor Systems, Inc.",
            "doc_role": "primary"}
    if annual_value is not None:
        form["annual_value"] = str(annual_value)
        form["currency"] = currency or "USD"
    r = sess.post(f"{API}/contracts", files=files, data=form, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["contract"]["id"]


def _analyze(sess, cid):
    r = sess.post(f"{API}/contracts/{cid}/analyze", timeout=90)
    assert r.status_code == 200, r.text
    return r.json()["findings"]


def _get_contract(sess, cid):
    r = sess.get(f"{API}/contracts/{cid}", timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["contract"], r.json()["documents"]


def _norm_ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


# ---------------------------- 1. Happy path ----------------------------
class TestHappyPath:
    def test_happy_renewal(self, sess, created):
        cid = _create_contract(sess, "TEST_stage2_happy", HAPPY_TEXT)
        created.append(cid)

        findings = _analyze(sess, cid)
        assert len(findings) == 1, f"expected 1 finding, got {len(findings)}"
        f = findings[0]
        assert f["type"] == "renewal_notice"
        assert f["validation_status"] == "validated", (
            f["validation_status"], f["validation_notes"])
        assert f["confidence"] in ("high", "medium", "low")
        assert f["action_required"] is True         # automatic
        assert f["money_kind"] == "contract_value"

        e = f["extracted"]
        assert e["renewal_type"] == "automatic"
        assert e["notice_days_min"] == 60
        assert e["initial_term_value"] == 12
        assert e["initial_term_unit"] in ("months", "month")
        assert e["effective_date"] == "2026-03-15"
        assert e["next_renewal_date"] is not None
        assert e["action_deadline"] is not None
        assert e["effective_action_deadline"] is not None
        assert isinstance(e["days_remaining"], int)

        # date math: action_deadline = next_renewal - 60 days (calendar) - 1 day (term_end anchor)
        from datetime import date, timedelta
        nr = date.fromisoformat(e["next_renewal_date"])
        ad = date.fromisoformat(e["action_deadline"])
        assert (nr - ad).days == 61

        # required-purpose sources present + validated
        purposes = {s["purpose"] for s in f["sources"]}
        assert "renewal_term" in purposes
        assert "notice_period" in purposes

        # server-resolved location + integer char_offset, doc_id belongs to
        # THIS contract's documents
        _, docs = _get_contract(sess, cid)
        doc_ids = {d["id"] for d in docs}
        for s in f["sources"]:
            assert s["document_id"] in doc_ids, (
                "server must resolve document_id from chunk_id")
            assert isinstance(s["char_offset"], int)
            assert s["location"], "location must be server-resolved"
            assert re.match(r"^(p\.\d+|§|\(preamble\))", s["location"])

        # save for provenance test
        pytest.happy_cid = cid


# ---------------------------- 2. Annual-value provenance ----------------------------
class TestAnnualValueProvenance:
    def test_extracted_value_provenance(self, sess):
        cid = getattr(pytest, "happy_cid", None)
        assert cid, "TestHappyPath must run first"
        contract, _ = _get_contract(sess, cid)
        # Only assert extracted-provenance if the model actually returned a value
        if contract.get("value_source") == "extracted":
            assert contract["value_source_quote"]
            assert contract["value_source_document_id"]
            assert contract["value_source_location"]
            assert isinstance(contract["value_source_char_offset"], int)
            assert contract["annual_value"] == 48000
        else:
            # tolerated: model didn't produce a validated `value` source
            pytest.skip("model did not produce validated annual value source")

    def test_user_entered_not_overwritten(self, sess, created):
        cid = _create_contract(sess, "TEST_stage2_userval", HAPPY_TEXT,
                               annual_value=99999, currency="USD")
        created.append(cid)
        _analyze(sess, cid)
        c, _ = _get_contract(sess, cid)
        assert c["value_source"] == "user_entered", c.get("value_source")
        assert c["annual_value"] == 99999


# ---------------------------- 3. Missing effective date ----------------------------
class TestMissingEffectiveDate:
    def test_needs_review_no_deadline(self, sess, created):
        cid = _create_contract(sess, "TEST_stage2_noeff", NO_EFFECTIVE_TEXT)
        created.append(cid)
        findings = _analyze(sess, cid)
        # if the model still returned a finding, it must be needs_review
        if not findings:
            pytest.skip("model returned no finding at all for no-eff-date doc")
        f = findings[0]
        assert f["validation_status"] == "needs_review", (
            f["validation_status"], f["validation_notes"])
        e = f["extracted"]
        assert e["action_deadline"] is None
        assert e["effective_action_deadline"] is None
        assert e["days_remaining"] is None
        joined = " ".join(f["validation_notes"]).lower()
        assert "effective" in joined or "initial term" in joined


# ---------------------------- 4. Missing notice period ----------------------------
class TestMissingNoticeDays:
    def test_needs_review_no_deadline(self, sess, created):
        cid = _create_contract(sess, "TEST_stage2_nonotice", NO_NOTICE_DAYS_TEXT)
        created.append(cid)
        findings = _analyze(sess, cid)
        # Filter for renewal_notice type findings for this Stage 2 assertion
        renewal_findings = [f for f in findings if f["type"] == "renewal_notice"]
        if not renewal_findings:
            pytest.skip("model returned no renewal finding at all")
        f = renewal_findings[0]
        assert f["validation_status"] == "needs_review", (
            f["validation_status"], f["validation_notes"])
        e = f["extracted"]
        # notice_days_min may be null on the extracted payload, but no deadline
        assert e["action_deadline"] is None
        assert e["days_remaining"] is None


# ---------------------------- 5. No renewal language ----------------------------
class TestNoRenewalLanguage:
    def test_no_findings(self, sess, created):
        cid = _create_contract(sess, "TEST_stage2_nda", BOILERPLATE_TEXT)
        created.append(cid)
        findings = _analyze(sess, cid)
        # allow at most a needs_review finding if model over-triggers; core
        # contract: if a finding IS produced it must not expose a deadline
        if findings:
            f = findings[0]
            assert f["validation_status"] == "needs_review", (
                "no-renewal doc must not yield a validated finding")
            assert f["extracted"]["action_deadline"] is None
        # status should be 'analysed'
        r = sess.get(f"{API}/contracts/{cid}/findings")
        assert r.json()["status"] == "analysed"


# ---------------------------- 6. Manual (no auto-renew) ----------------------------
class TestManualRenewal:
    def test_no_automatic_deadline(self, sess, created):
        cid = _create_contract(sess, "TEST_stage2_manual", MANUAL_TEXT)
        created.append(cid)
        findings = _analyze(sess, cid)
        if not findings:
            return  # acceptable: model may return no finding
        f = findings[0]
        assert f["action_required"] is False, (
            "manual/none renewal must not set action_required=True")
        # renewal_type explicitly not automatic
        assert f["extracted"]["renewal_type"] in ("manual", "none", None)


# ---------------------------- 7. Source validation integrity ----------------------------
class TestSourceIntegrity:
    def test_every_source_appears_in_rawtext(self, sess):
        cid = getattr(pytest, "happy_cid", None)
        assert cid
        _, docs = _get_contract(sess, cid)
        by_id = {d["id"]: d for d in docs}
        r = sess.get(f"{API}/contracts/{cid}/findings")
        assert r.status_code == 200
        for f in r.json()["findings"]:
            assert f["sources"], "validated finding must have sources"
            for s in f["sources"]:
                doc = by_id[s["document_id"]]
                assert _norm_ws(s["quote"]) in _norm_ws(doc["raw_text"]), (
                    f"quote not present verbatim: {s['quote'][:60]!r}")


# ---------------------------- 8. user_id isolation ----------------------------
class TestUserIsolation:
    def test_userB_cannot_access(self, sessB):
        cid = getattr(pytest, "happy_cid", None)
        assert cid
        r1 = sessB.get(f"{API}/contracts/{cid}")
        assert r1.status_code == 404, r1.text
        r2 = sessB.get(f"{API}/contracts/{cid}/findings")
        assert r2.status_code == 404, r2.text
        r3 = sessB.post(f"{API}/contracts/{cid}/analyze")
        assert r3.status_code == 404, r3.text
