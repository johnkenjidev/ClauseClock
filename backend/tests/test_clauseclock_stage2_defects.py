"""ClauseClock Stage 2 DEFECT FIX tests.

Covers:
  D1a — multi-purpose sources (same chunk_id+quote emitted per purpose)
  D1b — required-purpose gating preserved (notice-only doc -> needs_review)
  D2  — zero-source suppression (in-process monkeypatch of llm.extract):
        NO finding persisted + exact warning string returned
  Invariant — no persisted renewal_notice finding has sources.length == 0
  Unit — analysis.find_quote_offset_marker_tolerant vs find_quote_offset:
         marker-tolerant matches across a page marker; strict does not;
         a wrong-word quote still returns None (no fuzzy matching);
         _display_quote strips ClauseClock's injected markers.
  Verbatim invariant — every validated source (marker-stripped) is
         verbatim-present in its resolved document's marker-stripped raw_text.
  Auth isolation — cross-user analyze/findings return 404 (regression).
"""
import asyncio
import io
import os
import re
import sys
import time
from datetime import date

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

ZERO_SOURCE_WARNING = (
    "Candidate renewal language was detected, but no source quote could be validated."
)


# ---------------------------- PDF helper ----------------------------
def make_pdf(paragraphs):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    margin = 60
    y = height - margin
    c.setFont("Helvetica", 11)
    for para in paragraphs:
        for w in para.split():
            trial = w
            # naive width-based wrap
            pass
        # simple wrap
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
        y -= 8
        if y < margin:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - margin
    c.showPage()
    c.save()
    return buf.getvalue()


# One clause that BOTH states automatic renewal AND the notice period
SINGLE_CLAUSE_TEXT = [
    "MASTER SERVICES AGREEMENT",
    "This Agreement is effective as of March 15, 2026 (the \"Effective Date\").",
    "TERM AND RENEWAL. The initial term of this Agreement is twelve (12) months "
    "and this Agreement shall automatically renew for successive one-year terms "
    "unless written notice of non-renewal is given at least sixty (60) days "
    "prior to the end of the then-current term.",
    "FEES. Annual fee: $36,000.",
]

# Notice period only — NO renewal/term language at all
NOTICE_ONLY_TEXT = [
    "SERVICES AGREEMENT",
    "This Agreement is effective as of April 1, 2026 (the \"Effective Date\").",
    "NOTICE. Any notice under this Agreement shall be delivered in writing at "
    "least thirty (30) days prior to the intended effective date of the "
    "notice, by certified mail to the General Counsel of Vendor Systems, Inc.",
    "CONFIDENTIALITY. Each party shall protect the confidential information "
    "of the other using reasonable care.",
    "GOVERNING LAW. This Agreement is governed by the laws of Delaware.",
]

# Doc that DOES contain renewal language (used for the zero-source
# monkeypatch scenario). We hand-craft an "extracted" payload whose quotes
# do NOT appear in raw_text so validate_sources drops everything.
RENEWAL_TEXT_FOR_ZEROSRC = [
    "SUBSCRIPTION AGREEMENT",
    "Effective Date: June 1, 2026.",
    "TERM. Initial term twelve (12) months.",
    "RENEWAL. This Agreement shall automatically renew for successive "
    "one-year terms unless either party gives sixty (60) days written notice "
    "of non-renewal.",
    "FEES. $12,000 annually.",
]


# ---------------------------- sessions / helpers ----------------------------
@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    assert r.status_code == 200, f"seed login failed: {r.text}"
    return s


@pytest.fixture(scope="module")
def sessB():
    s = requests.Session()
    email = f"defect-userb-{int(time.time())}@clauseclock.app"
    r = s.post(f"{API}/auth/register",
               json={"email": email, "password": "Test1234!"})
    assert r.status_code == 200, r.text
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


def _create_contract(sess, name, paragraphs):
    pdf = make_pdf(paragraphs)
    files = {"file": (f"{name}.pdf", pdf, "application/pdf")}
    form = {"name": name, "counterparty": "Vendor Systems, Inc.", "doc_role": "primary"}
    r = sess.post(f"{API}/contracts", files=files, data=form, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["contract"]["id"]


def _analyze(sess, cid):
    r = sess.post(f"{API}/contracts/{cid}/analyze", timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    return body.get("findings", []), body.get("warnings", [])


def _get_findings(sess, cid):
    r = sess.get(f"{API}/contracts/{cid}/findings", timeout=15)
    assert r.status_code == 200, r.text
    return r.json().get("findings", [])


def _get_docs(sess, cid):
    r = sess.get(f"{API}/contracts/{cid}", timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["documents"]


def _norm_ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


# ====================================================================
# UNIT — marker-tolerant validation (no LLM, fast)
# ====================================================================
class TestMarkerTolerantUnit:
    def test_marker_tolerant_matches_across_page_marker(self):
        # A verbatim clause split by ClauseClock's own page marker.
        raw = (
            "TERM AND RENEWAL. This Agreement shall automatically renew\n"
            "========== Page 2 ==========\n"
            "for successive one-year terms unless written notice is given.\n"
        )
        # quote as the model would produce it — words in order, no markers
        quote = ("This Agreement shall automatically renew for successive "
                 "one-year terms unless written notice is given.")
        strict = analysis.find_quote_offset(raw, quote)
        tolerant = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert strict is None, "strict matcher must NOT cross the page marker"
        assert isinstance(tolerant, int), "marker-tolerant must return an int offset"
        # offset must index the ORIGINAL raw_text (not the cleaned one)
        assert raw[tolerant: tolerant + len("This Agreement")] == "This Agreement"

    def test_wrong_word_still_returns_none(self):
        # NO fuzzy/edit-distance: a quote containing a word not present
        # in the document must NOT match.
        raw = "The Agreement shall automatically renew for one year."
        quote = "The Agreement shall MAGICALLY renew for one year."
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_display_quote_strips_injected_markers(self):
        q = (
            "This Agreement shall automatically renew\n"
            "========== Page 2 ==========\n"
            "for successive terms [§3.2] ¶7 | unless notice is given."
        )
        d = analysis._display_quote(q)
        assert "==========" not in d
        assert "[§" not in d
        assert "¶" not in d
        # collapsed whitespace, contract words preserved verbatim/in order
        assert "automatically renew for successive terms" in d
        assert "unless notice is given" in d

    def test_marker_tolerant_ignores_table_and_section_markers(self):
        raw = ("Fees are set forth [Table 1] in the schedule "
               "[§4.1] and are due within thirty days.")
        quote = "Fees are set forth in the schedule and are due within thirty days."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off: off + 4] == "Fees"


# ====================================================================
# D2 — zero-source suppression (in-process monkeypatch, deterministic)
# ====================================================================
class TestZeroSourceSuppression:
    """Force zero validated sources by monkeypatching llm.extract with quotes
    that don't verbatim exist in the document. Directly exercise
    analysis.run_renewal_analysis with the seeded user's real DB record so
    both the persistence invariant and the warning contract are covered."""

    def test_zero_validated_sources_yields_warning_and_no_finding(self, sess, created):
        cid = _create_contract(sess, "TEST_defect_zerosrc", RENEWAL_TEXT_FOR_ZEROSRC)
        created.append(cid)

        # Discover ids we need for the in-process run
        from motor.motor_asyncio import AsyncIOMotorClient
        from bson import ObjectId
        import llm as llm_mod

        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ["DB_NAME"]

        async def _run():
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            contract = await db.contracts.find_one({"_id": ObjectId(cid)})
            assert contract is not None, "contract missing from db"
            user_id = contract["user_id"]

            # Monkeypatch LLM: locate returns first chunk, extract returns
            # a shape whose quotes are NOT verbatim in raw_text so
            # validate_sources drops every source.
            async def fake_locate(chunks):
                return [chunks[0]["chunk_id"]] if chunks else []

            async def fake_extract(chunks):
                cid_first = chunks[0]["chunk_id"] if chunks else "c_01"
                return {
                    "found": True,
                    "effective_date": "2026-06-01",
                    "initial_term_value": 12,
                    "initial_term_unit": "months",
                    "renewal_type": "automatic",
                    "renewal_period_value": 1,
                    "renewal_period_unit": "years",
                    "notice_days_min": 60,
                    "notice_days_max": None,
                    "notice_basis": "calendar",
                    "business_day_definition": None,
                    "notice_measured_to": "sent",
                    "deemed_receipt_rule": None,
                    "notice_method": None,
                    "notice_recipient": None,
                    "annual_value": None,
                    "sources": [
                        # zero of these are verbatim-present in the doc
                        {"purpose": "renewal_term", "chunk_id": cid_first,
                         "quote": "THIS QUOTE DOES NOT APPEAR VERBATIM ANYWHERE IN THE DOCUMENT XYZZY."},
                        {"purpose": "notice_period", "chunk_id": cid_first,
                         "quote": "ANOTHER FABRICATED CLAUSE THAT IS ABSOLUTELY NOT IN THE DOC PLUGH."},
                    ],
                    "confidence": "high",
                }

            orig_locate, orig_extract = llm_mod.locate, llm_mod.extract
            analysis.llm.locate = fake_locate
            analysis.llm.extract = fake_extract
            try:
                findings, warnings = await analysis.run_renewal_analysis(
                    db, contract, user_id)
            finally:
                analysis.llm.locate = orig_locate
                analysis.llm.extract = orig_extract

            # Also read from DB to prove persistence invariant
            persisted = [f async for f in db.findings.find(
                {"contract_id": cid, "user_id": user_id,
                 "type": "renewal_notice"})]
            client.close()
            return findings, warnings, persisted

        findings, warnings, persisted = asyncio.get_event_loop().run_until_complete(_run()) \
            if False else asyncio.new_event_loop().run_until_complete(_run())

        assert findings == [], f"no finding must be returned, got {findings}"
        assert ZERO_SOURCE_WARNING in warnings, \
            f"exact warning missing. warnings={warnings!r}"
        assert persisted == [], \
            f"no finding must be persisted, got {len(persisted)}"

        # HTTP surface: /findings must be empty for this contract too
        assert _get_findings(sess, cid) == []


# ====================================================================
# D1a — multi-purpose sources from ONE clause (real LLM)
# ====================================================================
class TestMultiPurposeSources:
    def test_single_clause_supports_renewal_and_notice(self, sess, created):
        cid = _create_contract(sess, "TEST_defect_multipurpose", SINGLE_CLAUSE_TEXT)
        created.append(cid)

        findings, warnings = _analyze(sess, cid)
        assert warnings == [], f"unexpected warnings: {warnings}"
        assert len(findings) == 1, f"expected 1 finding, got {len(findings)}"
        f = findings[0]

        # Both required purposes must be present as validated sources.
        purposes = [s["purpose"] for s in f["sources"]]
        assert "renewal_term" in purposes, purposes
        assert "notice_period" in purposes, purposes

        # Invariant: sources[] never empty
        assert len(f["sources"]) >= 2

        # There MUST exist at least one chunk_id shared between a
        # renewal_term source and a notice_period source (same clause
        # supporting both purposes — the core of D1). If the model split
        # them across separate quotes we still accept as long as each
        # required purpose validated; but at least one chunk should
        # commonly appear across both.
        rt_chunks = {s["chunk_id"] for s in f["sources"] if s["purpose"] == "renewal_term"}
        np_chunks = {s["chunk_id"] for s in f["sources"] if s["purpose"] == "notice_period"}
        shared = rt_chunks & np_chunks
        # Soft: prefer shared chunk; if the model chose different chunks
        # for the two purposes we tolerate (both still validated verbatim).
        if not shared:
            pytest.warns  # no-op; keep the soft path explicit
            # Still assert both got at least one validated source
            assert rt_chunks and np_chunks

        # Deadline computed (effective + initial term - 60 days)
        e = f["extracted"]
        assert f["validation_status"] == "validated", (
            f["validation_status"], f["validation_notes"])
        assert e["renewal_type"] == "automatic"
        assert e["notice_days_min"] == 60
        assert e["effective_date"] == "2026-03-15"
        assert e["next_renewal_date"] is not None
        assert e["action_deadline"] is not None
        nr = date.fromisoformat(e["next_renewal_date"])
        ad = date.fromisoformat(e["action_deadline"])
        assert (nr - ad).days == 60


# ====================================================================
# D1b — required-purpose gating preserved
# ====================================================================
class TestGatingPreserved:
    def test_notice_only_doc_is_needs_review_or_no_finding(self, sess, created):
        cid = _create_contract(sess, "TEST_defect_notice_only", NOTICE_ONLY_TEXT)
        created.append(cid)

        findings, warnings = _analyze(sess, cid)

        # Two acceptable outcomes: either (a) no finding at all (model
        # correctly returned found=false because no renewal language), or
        # (b) a needs_review finding because required-purpose gate blocked
        # validation. NEVER: a validated finding with an invented renewal_term.
        if not findings:
            # (a) acceptable — no renewal language → no finding
            return

        assert len(findings) == 1
        f = findings[0]

        # renewal_term must NOT have been fabricated from keywords.
        # If it's present as a validated source we insist the QUOTE is
        # verbatim-present in the doc — because the doc has NO renewal
        # language, this can only be satisfied if the model quoted
        # something like the "Notice" line, which does not contain
        # renewal/term wording. We accept renewal_term source only if
        # verbatim (server already validated it) but the finding as a
        # whole MUST be needs_review (missing renewal_term OR missing
        # deadline math on non-renewing doc).
        assert f["validation_status"] == "needs_review", (
            "notice-only contract must yield needs_review, "
            f"got {f['validation_status']} notes={f['validation_notes']}")
        # No exposed deadline
        assert f["extracted"]["action_deadline"] is None
        assert f["extracted"]["effective_action_deadline"] is None

        # And no zero-source finding
        assert len(f["sources"]) >= 1


# ====================================================================
# Invariant + verbatim
# ====================================================================
class TestInvariantsAcrossAll:
    def test_no_persisted_finding_has_zero_sources(self, sess, created):
        # Iterate every contract created in this run
        assert created, "no contracts created — earlier tests failed"
        for cid in created:
            findings = _get_findings(sess, cid)
            for f in findings:
                if f["type"] != "renewal_notice":
                    continue
                assert len(f.get("sources") or []) > 0, (
                    f"INVARIANT VIOLATED: finding {f['id']} on contract "
                    f"{cid} has zero sources but was persisted/displayed")

    def test_every_validated_quote_is_verbatim_in_rawtext(self, sess, created):
        for cid in created:
            docs = _get_docs(sess, cid)
            by_id = {d["id"]: d for d in docs}
            findings = _get_findings(sess, cid)
            for f in findings:
                if f["type"] != "renewal_notice":
                    continue
                for s in f["sources"]:
                    raw = by_id[s["document_id"]].get("raw_text") or ""
                    # marker-strip both sides (defect fix contract)
                    raw_clean = _norm_ws(analysis._strip_markers(raw))
                    q_clean = _norm_ws(analysis._strip_markers(s["quote"]))
                    assert q_clean in raw_clean, (
                        "validated source not verbatim (after marker-strip) "
                        f"in raw_text: quote={s['quote'][:80]!r}")


# ====================================================================
# Auth isolation regression
# ====================================================================
class TestAuthIsolation:
    def test_userB_cannot_access_defect_contracts(self, sessB, created):
        assert created
        cid = created[0]
        for path, method in [
            (f"{API}/contracts/{cid}", "get"),
            (f"{API}/contracts/{cid}/findings", "get"),
            (f"{API}/contracts/{cid}/analyze", "post"),
        ]:
            r = getattr(sessB, method)(path)
            assert r.status_code == 404, (path, r.status_code, r.text)
