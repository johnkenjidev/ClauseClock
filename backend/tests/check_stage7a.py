"""Focused Stage 7A checks: price_increase value/date math + review flags."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analysis

TODAY = date(2026, 1, 1)


def check_happy():
    # fixed automatic 3% with known current value + objection window with a
    # reference (price change) date -> quantified next term + computed deadline.
    e = {
        "increase_type": "fixed_automatic", "increase_percent": 3,
        "price_change_date": "2026-06-01",
        "objection_window_value": 30, "objection_window_unit": "days",
    }
    out, notes, review, money, kind, action = analysis.compute_price(e, TODAY, 100000.0)
    assert not review, notes
    assert money == 3000.0, money
    assert kind == "cost"
    assert out["next_term_amount"] == 103000.0, out
    assert out["objection_deadline"] == "2026-05-02", out  # 30 days before Jun 1
    assert out["days_remaining"] == (date(2026, 5, 2) - TODAY).days
    assert action is True
    print("PASS happy: +3% -> +$3,000 next-term $103,000, objection deadline 2026-05-02")


def check_cap_and_ambiguity():
    # capped 5% -> maximum permitted, NOT guaranteed; validated (not review).
    e = {"increase_type": "capped", "increase_percent": 5}
    out, notes, review, money, kind, action = analysis.compute_price(e, TODAY, 100000.0)
    assert not review, notes
    assert out["max_permitted_amount"] == 105000.0, out
    assert money == 5000.0 and kind == "cost"
    assert any("maximum permitted" in n for n in notes), notes
    assert out["next_term_amount"] is None  # never a guaranteed increase
    print("PASS cap: up to 5% -> max permitted $105,000 (not guaranteed)")

    # ambiguity 1: unspecified type -> needs_review
    _, _, r1, _, _, _ = analysis.compute_price({"increase_type": None}, TODAY, 100000.0)
    assert r1 is True
    # ambiguity 2: formula w/o formula text -> needs_review
    _, _, r2, _, _, _ = analysis.compute_price({"increase_type": "formula"}, TODAY, 100000.0)
    assert r2 is True
    # ambiguity 3: objection window with no reference date -> needs_review
    _, n3, r3, _, _, _ = analysis.compute_price(
        {"increase_type": "capped", "increase_percent": 5,
         "objection_window_value": 30, "objection_window_unit": "days"}, TODAY, 100000.0)
    assert r3 is True and any("reference date" in n for n in n3), n3
    print("PASS ambiguity: unspecified / bare formula / window-without-date all -> needs_review")


if __name__ == "__main__":
    check_happy()
    check_cap_and_ambiguity()
    print("ALL PRICE MATH CHECKS PASSED")
