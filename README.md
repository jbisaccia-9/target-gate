# target-gate

[![ci](https://github.com/jbisaccia-9/target-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/jbisaccia-9/target-gate/actions) · [captured results](RESULTS.md)

**A twice-monthly provider-targeting pipeline where no list reaches sales
until it passes the gate.**

Growth pipelines fail expensively in a specific way: not by missing a target,
but by shipping a *wrong* one — a mistyped identifier, a stale snapshot, a
duplicate that gets two reps calling the same office. This repo wires the
outbound email step strictly **behind** a list gate; a failing list produces a
report and a nonzero exit, and there is no code path that sends it.

```
NPPES registry (public)          markets.json (strategic markets)
        │                                │
        ▼                                ▼
   pull ──► snapshot ──► analyze ──► GATE ──► sales.md / marketing.md
            (Blob or     (rank by    │ pass        (Graph sendMail
             ./container) coverage)  │              or ./outbox)
                                     └ fail ──► report + exit 1, nothing sent
```

## The list gate

| check | refuses when |
|---|---|
| NPI checksum | any identifier fails its own Luhn check digit — a typo or a fabrication |
| dedupe | the same NPI appears twice |
| freshness | the snapshot is older than the twice-monthly cadence allows (16 days) |
| field coverage | contact completeness falls below 80% |
| market coverage | any strategic market produced zero targets |

CI runs both paths: the clean fixture must clear and deliver, and the
corrupted fixture must be refused with zero outbound files
(`! python -m targetgate run corrupted`).

## Azure shape

This is an Azure Functions app (Python v2 model): `function_app.py` carries a
timer trigger — `0 0 6 1,15 * *`, 06:00 UTC on the 1st and 15th — whose body
is the same pipeline the CLI runs. Storage is an adapter: an Azure Blob
container when `AZURE_STORAGE_CONNECTION_STRING` is set, a local `./container/`
directory otherwise. Outbound mail is Microsoft Graph `sendMail` when
`GRAPH_TOKEN`/`GRAPH_SENDER` are set, a local `./outbox/` of inspectable
markdown otherwise. The analyst narrative is pluggable the same way — a
deterministic template locally, an Azure AI Foundry agent deployment when
pointed at one; **ranking is never delegated to a model.**
Deploy with `func azure functionapp publish <app>` and `requirements-azure.txt`.

## Data honesty

The committed fixture is fully synthetic: names are obvious fakes, and every
NPI **starts with 9 — outside the issued range — while still passing its
checksum**, so the data is structurally valid and provably not a real
provider. Live mode queries the public NPPES registry; those results are real
public registry entries, so they land only in the gitignored container and are
never committed. No employer data, market strategy, or payer logic appears
anywhere in this repo.

## Quickstart

```
python -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m targetgate run fixture
.venv/bin/python -m targetgate run corrupted
```

Part of the *-gate* family — [github.com/jbisaccia-9](https://github.com/jbisaccia-9).
MIT license.
