"""The twice-monthly run: pull -> snapshot to container -> analyze -> GATE -> deliver.

Delivery sits strictly behind the gate: a failing list produces a report and a
nonzero exit, never an email. In Azure this function body runs on the timer
trigger in function_app.py; locally it runs from the CLI with identical logic.
"""
import datetime
import json
import pathlib

from . import pull, analyze, gate
from .storage import get_container

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_config():
    return json.loads((ROOT / "markets.json").read_text())


def run(source="fixture", today=None, deliver=True):
    config = load_config()
    today = today or datetime.date.today()
    if source == "nppes":
        rows = []
        for m in config["markets"]:
            for tax in m["taxonomies"]:
                rows.extend(pull.pull_nppes(m["state"], tax))
    else:
        rows = pull.pull_fixture("corrupted_nppes.jsonl" if source == "corrupted"
                                 else "synthetic_nppes.jsonl")
    snapshot_date = today.isoformat()
    container = get_container()
    container.put(f"providers-{snapshot_date}.json",
                  {"as_of": snapshot_date, "source": source, "rows": rows})
    lists = analyze.build_lists(rows, config)
    code = gate.check(rows, lists, snapshot_date, config, today=today)
    if code != 0:
        print("DELIVERY: BLOCKED - nothing was sent.")
        return code
    if deliver:
        from .agent import run_agent, grounding_gate, get_model, previous_rows
        brief, _ = run_agent(get_model(), rows, previous_rows())
        summary = analyze.summarize(lists)
        if grounding_gate(brief, rows, previous_rows()) == 0:
            summary = summary + "\n\n" + brief
        else:
            summary = summary + "\n\n(Analyst brief withheld: failed grounding.)"
        from .emailer import deliver as send
        channel = send(lists, summary, snapshot_date)
        print(f"DELIVERY: sent via {channel} - "
              f"{sum(len(m['targets']) for m in lists)} targets across {len(lists)} markets.")
    return 0
