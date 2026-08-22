"""Focused verification for the notice-anchor defect fix (not a regression run).

Proves the deterministic calculator anchors correctly and refuses on unknown:
  1. DealMaker    — term_end,  term ends 2028-03-31, 60d -> 2028-01-31 (leap Feb).
  2. Meridian     — term_end,  term ends 2028-11-30, 60d -> 2028-10-01.
  3. InvoiceCloud — renewal_start, renewal 2028-04-01, 60d -> 2028-02-01.
  4. unknown / legacy-absent anchor -> refuse (no deadline, needs_review).

Also proves the vocabulary-profile classifier maps the real clause wordings to
the right anchor type, so two clause semantics yield two anchor types.
"""
import sys
from datetime import date

sys.path.insert(0, "/app/backend")
import analysis  # noqa: E402


def _renewal_extracted(effective_date, anchor):
    # effective + 12 months = renewal_start; term_end = renewal_start - 1 day.
    return {
        "effective_date": effective_date,
        "initial_term_value": 12, "initial_term_unit": "months",
        "renewal_type": "automatic",
        "renewal_period_value": 1, "renewal_period_unit": "years",
        "notice_days_min": 60, "notice_days_max": None,
        "notice_basis": "calendar", "business_day_definition": None,
        "notice_measured_to": "sent", "deemed_receipt_rule": None,
        "notice_anchor_type": anchor,
    }


def check(name, got, expected):
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got={got} expected={expected}")
    return ok


def main():
    today = date(2026, 8, 1)  # before all renewals so no roll-forward
    all_ok = True

    print("1) DealMaker — 'prior to the completion of the DMTA Term' (term_end)")
    # renewal_start 2028-04-01 (eff 2027-04-01 +12m) -> term_end 2028-03-31
    out, notes, review = analysis.compute_dates(
        _renewal_extracted("2027-04-01", "term_end"), today)
    all_ok &= check("next_renewal_date", out["next_renewal_date"], "2028-04-01")
    all_ok &= check("current_term_end", out["current_term_end"], "2028-03-31")
    all_ok &= check("deadline (60d, leap Feb)", out["effective_action_deadline"], "2028-01-31")
    all_ok &= check("needs_review", review, False)
    cls = analysis._profile_classify_anchor("prior to the completion of the DMTA Term")
    all_ok &= check("profile classifies quote", cls, "term_end")

    print("2) Meridian — 'prior to the end of the then-current term' (term_end)")
    # renewal_start 2028-12-01 (eff 2027-12-01 +12m) -> term_end 2028-11-30
    out, notes, review = analysis.compute_dates(
        _renewal_extracted("2027-12-01", "term_end"), today)
    all_ok &= check("current_term_end", out["current_term_end"], "2028-11-30")
    all_ok &= check("deadline (60d)", out["effective_action_deadline"], "2028-10-01")
    all_ok &= check("needs_review", review, False)
    cls = analysis._profile_classify_anchor(
        "not less than sixty (60) days prior to the end of the then-current term")
    all_ok &= check("profile classifies quote", cls, "term_end")

    print("3) InvoiceCloud — 'prior to the start date of the Renewal Term' (renewal_start)")
    out, notes, review = analysis.compute_dates(
        _renewal_extracted("2027-04-01", "renewal_start"), today)
    all_ok &= check("next_renewal_date", out["next_renewal_date"], "2028-04-01")
    all_ok &= check("deadline (60d, anchored to renewal start)",
                    out["effective_action_deadline"], "2028-02-01")
    all_ok &= check("needs_review", review, False)
    cls = analysis._profile_classify_anchor("prior to the start date of the Renewal Term")
    all_ok &= check("profile classifies quote", cls, "renewal_start")

    print("   => two semantics -> two anchor types -> two different deadlines "
          "(2028-01-31 vs 2028-02-01)")

    print("4) unknown / unsupported / absent anchor -> refuse")
    for label, val in [("unknown", "unknown"), ("absent(None)", None),
                       ("anniversary(future-unmodeled)", "anniversary")]:
        out, notes, review = analysis.compute_dates(
            _renewal_extracted("2027-04-01", val), today)
        refused = (review is True
                   and out["effective_action_deadline"] is None
                   and "notice_anchor_unknown" in notes)
        all_ok &= check(f"refuses ({label})", refused, True)

    print("5) resolve_notice_anchor — no default, needs a validated quote")
    all_ok &= check("model says term_end but no validated quote -> unknown",
                    analysis.resolve_notice_anchor("term_end", "", False), "unknown")
    all_ok &= check("validated quote overrides via profile",
                    analysis.resolve_notice_anchor(
                        "renewal_start", "prior to the completion of the Term", True),
                    "term_end")

    print("\nRESULT:", "ALL PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
