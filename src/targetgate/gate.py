"""The list gate: no target list reaches sales or marketing unless it passes.

These checks encode the lesson every outreach pipeline learns exactly once:
the expensive failure is not a missing target, it is a WRONG one - a bad
identifier, a stale snapshot, a duplicate that gets two reps calling the same
office. The email step is wired BEHIND this gate; a failing list cannot be
sent, only reported.
"""
import datetime

from .npi import valid


def check(rows, lists, snapshot_date, config, today=None):
    today = today or datetime.date.today()
    age = (today - datetime.date.fromisoformat(snapshot_date)).days
    bad_npis = [r["npi"] for r in rows if not valid(r["npi"])]
    seen, dupes = set(), []
    for r in rows:
        if r["npi"] in seen:
            dupes.append(r["npi"])
        seen.add(r["npi"])
    from .analyze import completeness
    coverage = (sum(completeness(r) for r in rows) / len(rows)) if rows else 0.0
    empty = [m["market"] for m in lists if not m["targets"]]

    checks = [
        (f"every NPI passes its checksum ({len(bad_npis)} bad)", not bad_npis),
        (f"no duplicate NPIs ({len(dupes)} dupes)", not dupes),
        (f"snapshot fresh: {age}d old (max {config['max_snapshot_age_days']})",
         age <= config["max_snapshot_age_days"]),
        (f"field coverage {coverage:.0%} (min {config['min_field_coverage']:.0%})",
         coverage >= config["min_field_coverage"]),
        (f"every market has targets ({len(empty)} empty)", not empty),
    ]
    failures = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if failures:
        print("GATE: FAILED - this list must not be sent.")
        return 1
    print("GATE: PASSED - list is cleared for sales and marketing.")
    return 0
