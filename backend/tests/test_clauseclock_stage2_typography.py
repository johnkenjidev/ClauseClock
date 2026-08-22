"""ClauseClock Stage 2 accuracy repair — TYPOGRAPHIC NORMALIZATION tests.

Pure-function unit tests (NO LLM, NO DB) verifying that:
  1. analysis._norm is 1:1 (character-length preserved -> offsets preserved).
  2. find_quote_offset_marker_tolerant matches ASCII quote vs Unicode raw
     and vice versa (curly quotes, apostrophes, en/em/nb hyphens, nbsp,
     thin/word-joiner spaces).
  3. STRICT semantics preserved: normalization does NOT enable fuzzy /
     edit-distance / paraphrase / reorder matching.
  4. Marker + typography combined: a quote spanning a page marker AND
     using ASCII typography while raw has Unicode still returns the
     correct offset into the ORIGINAL raw_text.
  5. compute_dates arithmetic is deterministic: effective + initial
     term (- renewal_period roll forward if past) - notice_days_min
     produces effective_action_deadline (including a leap year case).
  6. RENEWAL_HINT regex matches common explicit renewal wordings and
     does NOT match unrelated wordings.
"""
import re
import sys
from datetime import date

import pytest

sys.path.insert(0, "/app/backend")
import analysis  # noqa: E402


# ------------------------------------------------- 1. _norm is 1:1
class TestNormIsOneToOne:
    def test_len_preserved_for_all_mapped_chars(self):
        # every char in _TYPO_TABLE mapped to a single ASCII char
        src = "".join(chr(k) for k in analysis._TYPO_TABLE.keys())
        norm = analysis._norm(src)
        assert len(src) == len(norm), (len(src), len(norm))

    def test_len_preserved_mixed_string(self):
        s = "\u201cEffective Date\u201d thirty\u2011six days\u00a0now."
        assert len(s) == len(analysis._norm(s))

    def test_curly_double_quotes_become_ascii(self):
        assert analysis._norm("\u201cx\u201d") == '"x"'

    def test_curly_single_and_apostrophe_become_ascii(self):
        assert analysis._norm("it\u2019s \u2018x\u2019") == "it's 'x'"

    def test_dashes_normalize_to_ascii_hyphen(self):
        for ch in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212":
            assert analysis._norm(f"a{ch}b") == "a-b", ch

    def test_spaces_normalize_to_ascii_space(self):
        for ch in "\u00a0\u2007\u2009\u202f\u2060\ufeff":
            assert analysis._norm(f"a{ch}b") == "a b", ch

    def test_plain_ascii_unchanged(self):
        s = 'The "Effective Date" is thirty-six months.'
        assert analysis._norm(s) == s


# --------------------------------- 2. ASCII quote vs Unicode raw & reverse
class TestTypographyMatching:
    def test_ascii_quote_matches_unicode_curly_double_raw(self):
        raw = "This Agreement (the \u201cEffective Date\u201d) is signed."
        quote = 'This Agreement (the "Effective Date") is signed.'
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        # offset indexes ORIGINAL raw
        assert raw[off:off + 4] == "This"

    def test_ascii_quote_matches_unicode_apostrophe_raw(self):
        raw = "Vendor\u2019s obligations shall survive."
        quote = "Vendor's obligations shall survive."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 6] == "Vendor"

    def test_ascii_hyphen_matches_unicode_non_breaking_hyphen(self):
        raw = "The initial term is thirty\u2011six months."
        quote = "The initial term is thirty-six months."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 3] == "The"

    def test_ascii_hyphen_matches_unicode_en_and_em_dash(self):
        for ch in ("\u2013", "\u2014", "\u2010", "\u2012", "\u2015", "\u2212"):
            raw = f"non{ch}renewal notice must be given"
            quote = "non-renewal notice must be given"
            off = analysis.find_quote_offset_marker_tolerant(raw, quote)
            assert isinstance(off, int), ch
            assert raw[off:off + 3] == "non"

    def test_ascii_space_matches_unicode_nbsp_and_thin_space(self):
        for ch in ("\u00a0", "\u2009", "\u202f", "\u2007"):
            raw = f"at{ch}least{ch}sixty{ch}days"
            quote = "at least sixty days"
            off = analysis.find_quote_offset_marker_tolerant(raw, quote)
            assert isinstance(off, int), repr(ch)

    def test_reverse_unicode_quote_ascii_raw(self):
        # model echoes Unicode, raw is ASCII
        raw = 'The "Effective Date" is thirty-six months.'
        quote = "The \u201cEffective Date\u201d is thirty\u2011six months."
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 3] == "The"

    def test_combined_multiple_typographic_variants(self):
        raw = ("This Agreement\u2019s \u201cEffective Date\u201d is\u00a0"
               "March\u00a015, 2026\u2014the parties agree to a thirty\u2011"
               "six month term.")
        quote = ("This Agreement's \"Effective Date\" is March 15, 2026-the "
                 "parties agree to a thirty-six month term.")
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        assert raw[off:off + 4] == "This"


# ---------------------- 3. STRICT — normalization must NOT become fuzzy
class TestStillStrictAfterNormalization:
    def test_wrong_word_with_curly_quotes_still_none(self):
        raw = "The Agreement shall automatically renew for one year."
        quote = "The Agreement shall MAGICALLY renew for one year."
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_paraphrase_with_typography_still_none(self):
        raw = "This contract renews for successive one\u2011year terms."
        quote = "This contract auto-renews annually."
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_wrong_order_with_typography_still_none(self):
        raw = "sixty days prior to the end of the term"
        # reorder tokens but keep every ASCII/unicode variant "normalized"
        quote = "prior sixty days to the end of the term"
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_extra_word_still_none_even_with_curly_quotes(self):
        raw = "notice of non\u2011renewal"
        quote = "written notice of non-renewal"  # extra 'written'
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None

    def test_absent_word_still_none(self):
        raw = "notice of non\u2011renewal"
        quote = "notice of renewal"  # 'non-' missing
        assert analysis.find_quote_offset_marker_tolerant(raw, quote) is None


# ------------------------- 4. Marker + typography combined (Fix A preserved)
class TestMarkerPlusTypography:
    def test_marker_and_curly_quotes_returns_correct_original_offset(self):
        raw = (
            "========== Page 1 ==========\n"
            "This Agreement\u2019s \u201cEffective Date\u201d shall be March 15, 2026\n"
            "========== Page 2 ==========\n"
            "and shall automatically renew for successive one\u2011year terms.\n"
        )
        quote = ("This Agreement's \"Effective Date\" shall be March 15, 2026 "
                 "and shall automatically renew for successive one-year terms.")
        off = analysis.find_quote_offset_marker_tolerant(raw, quote)
        assert isinstance(off, int)
        # offset indexes ORIGINAL raw — verify the original bytes match
        assert raw[off:off + 4] == "This"
        # And Fix A alone (strict) would fail on the marker
        assert analysis.find_quote_offset(raw, quote) is None

    def test_end_to_end_validate_sources_marker_and_typography(self):
        raw = (
            "========== Page 1 ==========\n"
            "TERM. The \u201cInitial Term\u201d is thirty\u2011six (36) months.\n"
            "========== Page 2 ==========\n"
            "The Agreement shall automatically renew for one\u2011year terms.\n"
        )
        doc_id = "doc_typo"
        chunk_map = {"c_01": {"document_id": doc_id, "char_start": 0,
                              "char_end": len(raw)}}
        docs_by_id = {doc_id: {"id": doc_id, "raw_text": raw,
                                "file_type": "pdf"}}
        sources = [{
            "purpose": "renewal_term",
            "chunk_id": "c_01",
            "quote": ('The "Initial Term" is thirty-six (36) months. '
                      'The Agreement shall automatically renew for '
                      'one-year terms.'),
        }]
        validated, purposes = analysis.validate_sources(
            sources, chunk_map, docs_by_id)
        assert len(validated) == 1
        v = validated[0]
        assert v["document_id"] == doc_id
        assert isinstance(v["char_offset"], int)
        # Offset indexes ORIGINAL raw_text (with Unicode)
        assert raw[v["char_offset"]:v["char_offset"] + 3] == "The"
        # stored quote is marker-free
        assert "==========" not in v["quote"]
        # location resolves to starting page (p.1)
        assert v["location"] == "p.1"
        assert "renewal_term" in purposes


# --------------------------------- 5. deterministic deadline arithmetic
class TestComputeDatesDeterminism:
    def _extracted(self, **overrides):
        base = {
            "effective_date": "2026-03-15",
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
            # These cases assert renewal-start semantics (subtract from the
            # next_renewal_date), so the classified anchor is renewal_start.
            "notice_anchor_type": "renewal_start",
        }
        base.update(overrides)
        return base

    def test_basic_deadline_60_days_before_renewal(self):
        today = date(2026, 1, 1)
        out, notes, review = analysis.compute_dates(self._extracted(), today)
        assert review is False, notes
        assert out["next_renewal_date"] == "2027-03-15"
        # 2027-03-15 minus 60 calendar days
        assert out["effective_action_deadline"] == "2027-01-14"
        assert out["action_deadline"] == "2027-01-14"

    def test_leap_year_february(self):
        # renewal falls on 2028-03-31; 60 days earlier crosses Feb 29 (leap)
        today = date(2027, 1, 1)
        e = self._extracted(effective_date="2027-03-31",
                            initial_term_value=12, initial_term_unit="months",
                            notice_days_min=60)
        out, notes, review = analysis.compute_dates(e, today)
        assert review is False, notes
        assert out["next_renewal_date"] == "2028-03-31"
        # 2028 is a leap year — 60 days before 2028-03-31 = 2028-01-31
        assert out["effective_action_deadline"] == "2028-01-31"

    def test_rolls_forward_past_today(self):
        # today is well beyond initial renewal; roll forward using period=1yr
        today = date(2030, 6, 1)
        e = self._extracted(effective_date="2026-03-15")
        out, notes, review = analysis.compute_dates(e, today)
        assert review is False
        # First renewal 2027-03-15, roll: 2028, 2029, 2030-03-15 <= today,
        # then 2031-03-15
        assert out["next_renewal_date"] == "2031-03-15"

    def test_needs_review_when_notice_days_missing(self):
        e = self._extracted(notice_days_min=None)
        out, notes, review = analysis.compute_dates(e, date(2026, 1, 1))
        assert review is True
        assert out["effective_action_deadline"] is None

    def test_needs_review_when_initial_term_missing(self):
        e = self._extracted(initial_term_value=None, initial_term_unit=None)
        out, notes, review = analysis.compute_dates(e, date(2026, 1, 1))
        assert review is True
        assert out["next_renewal_date"] is None


# ------------------------------ 6. RENEWAL_HINT regex sanity
class TestRenewalHintRegex:
    @pytest.mark.parametrize("text", [
        "This Agreement shall automatically renew for successive one-year terms.",
        "The contract automatically renews annually.",
        "Renewal term shall be one (1) year.",
        "renews for successive one-year terms",
        "Non-renewal notice must be given.",
        "non renewal is subject to sixty days notice",
        "either party may elect not to renew",
        "The contract will renew automatically each year.",
    ])
    def test_matches_common_renewal_language(self, text):
        assert analysis.RENEWAL_HINT.search(text) is not None, text

    @pytest.mark.parametrize("text", [
        "The parties shall meet quarterly to review performance.",
        "Confidentiality obligations shall survive termination.",
        "Governing law shall be Delaware.",
        "Payment is due within thirty days of invoice.",
    ])
    def test_does_not_match_unrelated_language(self, text):
        assert analysis.RENEWAL_HINT.search(text) is None, text
