"""ClauseClock Stage 2 — FIX A verification (marker-tolerant STRICT verbatim).

Pure-function unit tests on /app/backend/analysis.py. NO LLM, NO DB.
Verifies:
  1. Page-marker defect fixed: marker-tolerant returns int where strict returns None.
  2. Bridges [Table..], [§..], [loc:..], and DOCX '¶N |' prefixes.
  3. Normal (non-marker-spanning) contiguous quote still returns correct offset,
     equal to plain substring / whitespace-normalized position.
  4. False/non-verbatim: unknown word -> None; correct tokens in wrong order -> None.
     (Strict — NO fuzzy/edit-distance/semantic acceptance.)
  5. Stored quote + char_offset: offset indexes ORIGINAL raw_text; _display_quote
     strips markers, collapses whitespace, caps at 400 chars, preserves verbatim
     words in order.
  6. End-to-end via analysis.validate_sources with a small in-memory chunk_map +
     docs_by_id where the source quote spans a page marker — validated source has
     (a) server-resolved document_id from chunk_id,
     (b) integer char_offset into that document's raw_text,
     (c) marker-free stored quote,
     (d) server-resolved location string (p.N).
  7. _location_at maps the marker-spanning match to the page the quote STARTS
     on (page before the marker), not the page after.
"""
import re
import sys

import pytest

sys.path.insert(0, "/app/backend")
import analysis  # noqa: E402


# ---------------------------------------------------------------- 1. defect FIX
class TestPageMarkerDefectFixed:
    def test_strict_fails_tolerant_succeeds_across_page_marker(self):
        raw = (
            "========== Page 1 ==========\n"
            "TERM AND RENEWAL. This Agreement shall automatically renew\n"
            "========== Page 2 ==========\n"
            "for successive one-year terms unless written notice is given.\n"
        )
        quote = ("This Agreement shall automatically renew for successive "
                 "one-year terms unless written notice is given.")
        strict = analysis.find_quote_offset(raw, quote)
        tolerant = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert strict is None, "OLD strict matcher must fail across page marker"
        assert isinstance(tolerant, int)
        # Offset indexes the ORIGINAL raw_text
        assert raw[tolerant:tolerant + len("This Agreement")] == "This Agreement"


# --------------------------------------------------------- 2. bridges markers
class TestBridgesAllInjectedMarkers:
    def test_bridges_table_marker(self):
        raw = "The fees are set forth [Table 1] in the schedule attached."
        quote = "The fees are set forth in the schedule attached."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 3] == "The"

    def test_bridges_section_marker(self):
        raw = "Payment obligations [§ 4.1] survive termination of this Agreement."
        quote = "Payment obligations survive termination of this Agreement."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 7] == "Payment"

    def test_bridges_loc_marker(self):
        raw = "The parties agree [loc: p3 para2] that all disputes shall be arbitrated."
        quote = "The parties agree that all disputes shall be arbitrated."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 3] == "The"

    def test_bridges_docx_paragraph_prefix(self):
        raw = "¶12 | Either party may terminate ¶13 | this Agreement with notice."
        quote = "Either party may terminate this Agreement with notice."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 6] == "Either"

    def test_bridges_multiple_marker_types_mixed(self):
        raw = (
            "========== Page 3 ==========\n"
            "¶4 | Vendor shall provide services [Table 2] as described "
            "[§ 5] and the fees [loc: p3] are due within thirty days.\n"
        )
        quote = ("Vendor shall provide services as described and the fees "
                 "are due within thirty days.")
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 6] == "Vendor"


# ------------------------------------------------------ 3. normal quote works
class TestNormalMatchStillWorks:
    def test_no_marker_quote_matches_plain_substring_position(self):
        raw = ("PREAMBLE. This Agreement is made as of March 15, 2026. "
               "TERM. The initial term is twelve (12) months.")
        quote = "The initial term is twelve (12) months."
        tolerant = analysis.find_quote_offset_marker_tolerant(raw, quote)
        strict = analysis.find_quote_offset(raw, quote)
        plain = raw.find(quote)
        assert tolerant is not None
        assert tolerant == strict == plain

    def test_whitespace_normalized_match_still_works(self):
        raw = "Notice must be   given\nat  least sixty  days prior."
        quote = "Notice must be given at least sixty days prior."
        tolerant = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(tolerant, int)
        assert raw[tolerant:tolerant + 6] == "Notice"


# ------------------------------------- 4. NO fuzzy — false quotes return None
class TestNoFuzzyOrSemantic:
    def test_unknown_word_returns_none(self):
        raw = "The Agreement shall automatically renew for one year."
        quote = "The Agreement shall MAGICALLY renew for one year."
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_hallucinated_paraphrase_returns_none(self):
        raw = "This contract renews for successive one-year terms."
        quote = "This contract auto-renews annually."  # paraphrase
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_wrong_token_order_returns_none(self):
        raw = "sixty days prior to the end of the term"
        quote = "prior sixty days to the end of the term"  # reordered
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_missing_word_from_middle_returns_none(self):
        raw = "at least sixty days prior to renewal"
        quote = "at least days prior to renewal"  # 'sixty' dropped — still verbatim subset? No — order matters, but tokens must all match consecutively
        # Actually the tokens 'at least' then 'days' would need consecutive match; not present.
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_extra_word_in_quote_returns_none(self):
        raw = "notice of non-renewal"
        quote = "written notice of non-renewal"  # 'written' not in raw at that position
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None


# -------------------------------------- 5. stored quote & display invariants
class TestDisplayQuoteAndOffset:
    def test_offset_indexes_original_raw(self):
        raw = ("========== Page 1 ==========\n"
               "Alpha beta gamma\n"
               "========== Page 2 ==========\n"
               "delta epsilon zeta.")
        quote = "Alpha beta gamma delta epsilon zeta."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 5] == "Alpha"

    def test_display_quote_strips_all_marker_types(self):
        q = (
            "This Agreement shall automatically renew\n"
            "========== Page 2 ==========\n"
            "for successive terms [§3.2] [Table 1] [loc: p2] ¶7 | "
            "unless notice is given."
        )
        d = analysis._display_quote(q)
        assert "==========" not in d
        assert "Page" not in d or "Page" not in re.findall(r"=+\s*Page\s+\d+\s*=+", d)
        assert "[§" not in d
        assert "[Table" not in d
        assert "[loc:" not in d
        assert "¶" not in d
        # verbatim words preserved in order, whitespace collapsed
        assert "automatically renew for successive terms" in d
        assert "unless notice is given" in d
        # no double spaces
        assert "  " not in d

    def test_display_quote_caps_at_400_chars(self):
        long_q = "word " * 200  # 1000 chars
        d = analysis._display_quote(long_q)
        assert len(d) <= 400


# ------------------------------ 6. end-to-end validate_sources with markers
class TestValidateSourcesEndToEnd:
    def test_validate_sources_marker_spanning_quote(self):
        raw_text = (
            "========== Page 1 ==========\n"
            "PREAMBLE. This Agreement is made as of March 15, 2026.\n"
            "TERM AND RENEWAL. This Agreement shall automatically renew\n"
            "========== Page 2 ==========\n"
            "for successive one-year terms unless written notice of "
            "non-renewal is given at least sixty days prior.\n"
        )
        doc_id = "doc_abc"
        chunk_map = {
            "c_01": {"document_id": doc_id, "char_start": 0,
                     "char_end": len(raw_text)}
        }
        docs_by_id = {doc_id: {"id": doc_id, "raw_text": raw_text,
                                "file_type": "pdf"}}
        sources = [{
            "purpose": "renewal_term",
            "chunk_id": "c_01",
            "quote": ("This Agreement shall automatically renew for successive "
                      "one-year terms unless written notice of non-renewal is "
                      "given at least sixty days prior."),
        }]
        validated, purposes = analysis.validate_sources(
            sources, chunk_map, docs_by_id)
        assert len(validated) == 1, f"expected 1 validated, got {validated}"
        v = validated[0]
        # (a) server-resolved document_id from chunk_id
        assert v["document_id"] == doc_id
        # (b) integer char_offset into raw_text
        assert isinstance(v["char_offset"], int)
        assert raw_text[v["char_offset"]:v["char_offset"] + len("This Agreement")] == "This Agreement"
        # (c) marker-free stored quote
        assert "==========" not in v["quote"]
        assert "Page 2" not in v["quote"]
        assert "automatically renew" in v["quote"]
        # (d) server-resolved location string — quote STARTS on page 1
        assert v["location"] == "p.1", (
            f"location should map to page BEFORE marker, got {v['location']}")
        assert "renewal_term" in purposes

    def test_validate_sources_drops_non_verbatim(self):
        raw_text = "The Agreement shall renew annually."
        doc_id = "doc_xyz"
        chunk_map = {"c_01": {"document_id": doc_id, "char_start": 0,
                              "char_end": len(raw_text)}}
        docs_by_id = {doc_id: {"id": doc_id, "raw_text": raw_text,
                                "file_type": "pdf"}}
        sources = [{
            "purpose": "renewal_term", "chunk_id": "c_01",
            "quote": "The Agreement shall renew MAGICALLY.",
        }]
        validated, purposes = analysis.validate_sources(
            sources, chunk_map, docs_by_id)
        assert validated == []
        assert purposes == set()


# ---------------------------------------- 7. location maps to STARTING page
class TestLocationAtStartingPage:
    def test_location_maps_to_page_before_marker(self):
        raw = (
            "========== Page 1 ==========\n"
            "Alpha content on page one.\n"
            "========== Page 2 ==========\n"
            "Beta content on page two.\n"
            "========== Page 3 ==========\n"
            "Gamma content.\n"
        )
        # A quote that STARTS on page 1 but continues past the p.2 marker
        quote = "Alpha content on page one. Beta content on page two."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        loc = analysis._location_at(raw, off, "pdf")
        assert loc == "p.1", f"expected p.1 (start page), got {loc}"

    def test_location_page_two_when_quote_starts_on_p2(self):
        raw = (
            "========== Page 1 ==========\n"
            "Alpha content.\n"
            "========== Page 2 ==========\n"
            "Beta content spanning\n"
            "========== Page 3 ==========\n"
            "into page three.\n"
        )
        quote = "Beta content spanning into page three."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        loc = analysis._location_at(raw, off, "pdf")
        assert loc == "p.2"
