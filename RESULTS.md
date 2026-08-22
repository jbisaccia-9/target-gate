# Results

Generated 2026-08-21 by `scripts/make_results.py` — every block below is captured command output, not prose.

## Unit tests

`python -m pytest -q` — exit 0, OK

```
...........                                                              [100%]
11 passed in 0.04s
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
  PASS  brief grounding: 4 NPIs cited, 0 not present in any snapshot
BRIEF GATE: PASSED - every cited identifier exists in the data.
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

## Agent brief: tool loop + grounding gate

`python -m targetgate brief` — exit 0, OK

```
Network-change brief (scripted analyst; data from live tool calls):
- AZ: 12 -> 11 providers.
    gone: Gus Formerly (NPI 9000070018)
- CO: 9 -> 11 providers.
    new: Zoe Fauxman (Pediatrics, NPI 9000010329)
    new: Eli Stubbs (Family Medicine, NPI 9000010337)
- TX: 12 -> 11 providers.
    gone: Ida Departed (NPI 9000070026)
[agent loop: 4 tool calls]
  PASS  brief grounding: 4 NPIs cited, 0 not present in any snapshot
BRIEF GATE: PASSED - every cited identifier exists in the data.
```

## Hallucinating analyst: refused

`python -m targetgate brief hallucinating` — expected non-zero exit, OK

```
Network-change brief (scripted analyst; data from live tool calls):
- AZ: 12 -> 11 providers.
    gone: Gus Formerly (NPI 9000070018)
- CO: 9 -> 11 providers.
    new: Eli Stubbs (Family Medicine, NPI 9000010337)
    new: Zoe Fauxman (Pediatrics, NPI 9000010329)
- TX: 12 -> 11 providers.
    gone: Ida Departed (NPI 9000070026)
    new: Dr. Invented Person (Cardiology, NPI 9123456780)
[agent loop: 4 tool calls]
  FAIL  brief grounding: 5 NPIs cited, 1 not present in any snapshot
    HALLUCINATED: 9123456780
BRIEF GATE: FAILED - the agent invented providers; brief not published.
```
