# Results

Generated 2026-08-21 by `scripts/make_results.py` — every block below is captured command output, not prose.

## Unit tests

`python -m pytest -q` — exit 0, OK

```
........                                                                 [100%]
8 passed in 0.03s
```

## Clean fixture: gate + delivery

`python -m targetgate run fixture` — exit 0, OK

```
PASS  every NPI passes its checksum (0 bad)
  PASS  no duplicate NPIs (0 dupes)
  PASS  snapshot fresh: 0d old (max 16)
  PASS  field coverage 98% (min 80%)
  PASS  every market has targets (0 empty)
GATE: PASSED - list is cleared for sales and marketing.
DELIVERY: sent via outbox - 15 targets across 3 markets.
```

## Corrupted fixture: refused, nothing sent

`python -m targetgate run corrupted` — expected non-zero exit, OK

```
FAIL  every NPI passes its checksum (1 bad)
  FAIL  no duplicate NPIs (1 dupes)
  PASS  snapshot fresh: 0d old (max 16)
  PASS  field coverage 87% (min 80%)
  FAIL  every market has targets (1 empty)
GATE: FAILED - this list must not be sent.
DELIVERY: BLOCKED - nothing was sent.
```
