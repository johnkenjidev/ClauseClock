"""Iteration 13 fix: superseded_by_finding_id pointer must refresh correctly
after every re-analysis so 'Review amendment changes' stays visible."""
import os
import time
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL",
                          "https://clock-continue.preview.emergentagent.com").rstrip("/")
EMAIL = "test@clauseclock.app"
PASSWORD = "Test1234!"
CONTRACT_ID = "6a8c968f38ffe86939d74f51"


def _login():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return s


def _get_renewal(s):
    r = s.get(f"{BASE_URL}/api/contracts/{CONTRACT_ID}/findings", timeout=30)
    r.raise_for_status()
    for f in r.json().get("findings", []):
        if f.get("type") == "renewal_notice":
            return f
    return None


def _history(s):
    r = s.get(f"{BASE_URL}/api/contracts/{CONTRACT_ID}/superseded-history", timeout=30)
    r.raise_for_status()
    return r.json()


def test_repeated_reanalysis_keeps_pointer_fresh():
    s = _login()
    # ensure fixture exists
    r = s.get(f"{BASE_URL}/api/contracts/{CONTRACT_ID}", timeout=30)
    assert r.status_code == 200, r.text

    # Make sure we have a confirmed renewal finding, then correct it back to
    # 10-day notice so subsequent re-analysis produces a genuine replacement.
    f = _get_renewal(s)
    if not f:
        r = s.post(f"{BASE_URL}/api/contracts/{CONTRACT_ID}/analyze", timeout=180)
        r.raise_for_status()
        f = _get_renewal(s)
    assert f, "no renewal finding available"
    if f["state"] not in ("confirmed", "corrected"):
        r = s.post(f"{BASE_URL}/api/findings/{f['id']}/confirm", timeout=30)
        assert r.status_code in (200, 204), r.text
        f = _get_renewal(s)

    ext = f.get("extracted") or {}
    # Force notice window to 10-day so re-analyze extraction (30-day) differs
    payload = {
        "effective_date": ext.get("effective_date"),
        "initial_term_value": ext.get("initial_term_value"),
        "initial_term_unit": ext.get("initial_term_unit"),
        "renewal_type": ext.get("renewal_type"),
        "renewal_period_value": ext.get("renewal_period_value"),
        "renewal_period_unit": ext.get("renewal_period_unit"),
        "notice_days_min": 10,
        "notice_days_max": 10,
        "notice_basis": ext.get("notice_basis"),
        "business_day_definition": ext.get("business_day_definition"),
        "notice_measured_to": ext.get("notice_measured_to"),
        "deemed_receipt_rule": ext.get("deemed_receipt_rule"),
        "notice_method": ext.get("notice_method"),
        "notice_recipient": ext.get("notice_recipient"),
        "notice_anchor_type": ext.get("notice_anchor_type"),
    }
    r = s.post(f"{BASE_URL}/api/findings/{f['id']}/correct",
               json=payload, timeout=60)
    assert r.status_code == 200, r.text

    baseline = _get_renewal(s)
    assert baseline["state"] == "corrected", baseline["state"]
    baseline_id = baseline["id"]
    print("Baseline corrected finding:", baseline_id,
          "notice_days_min=", baseline["extracted"].get("notice_days_min"))

    seen_replacement_ids = set()
    for i in range(3):
        r = s.post(f"{BASE_URL}/api/contracts/{CONTRACT_ID}/analyze", timeout=180)
        assert r.status_code == 200, r.text
        superseded_changes = r.json().get("superseded_changes")
        time.sleep(1)

        current = _get_renewal(s)
        assert current, "no current visible renewal after re-analyze"
        assert current["state"] == "unconfirmed", (
            f"iter {i+1}: expected an unconfirmed replacement, got state={current['state']}")

        hist = _history(s)
        entries = hist.get("history") or (hist if isinstance(hist, list) else [])
        rec = next((h for h in entries if h.get("id") == baseline_id), None)
        assert rec, f"iter {i+1}: no history record linking baseline {baseline_id}"
        rr = rec.get("replacement_relationship") or {}
        ptr = rr.get("superseded_by_finding_id")
        replacement_from_rec = (rec.get("replacement_finding") or {}).get("id")
        print(f"iter {i+1}: current_id={current['id']} state={current['state']} "
              f"ptr={ptr} rep_from_history={replacement_from_rec} "
              f"superseded_changes={superseded_changes}")
        assert ptr == current["id"], (
            f"iter {i+1}: stale pointer {ptr}, current visible id is {current['id']}")
        if replacement_from_rec:
            assert replacement_from_rec == current["id"], (
                f"iter {i+1}: history replacement_finding.id {replacement_from_rec} != "
                f"current visible id {current['id']}")
        seen_replacement_ids.add(current["id"])

    print("Distinct replacement finding ids observed:", seen_replacement_ids)


if __name__ == "__main__":
    test_repeated_reanalysis_keeps_pointer_fresh()
    print("PASS")
