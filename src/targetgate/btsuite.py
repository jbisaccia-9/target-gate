"""Braintrust-shaped eval suite: data -> task -> scorers.

Cases pin the pipeline's two verdicts (clean fixture clears, corrupted fixture
is refused) and the agent's grounding. Deterministic components get evals to
catch regression - a changed threshold or a reordered gate announces itself
before it ships.
"""
import datetime

from .pipeline import run

TODAY = datetime.date(2026, 8, 21)   # fixed: suites must not drift with the clock

CASES = [
    {"id": "clean-fixture", "source": "fixture", "expected": 0},
    {"id": "corrupted-fixture", "source": "corrupted", "expected": 1},
]


def task(case):
    return {"exit": run(source=case["source"], today=TODAY, deliver=False)}


def gate_expected(case, out):
    return 1.0 if out["exit"] == case["expected"] else 0.0


def agent_grounding():
    from .agent import run_agent, grounding_gate, get_model, previous_rows
    from .pull import pull_fixture
    rows = pull_fixture()
    brief, _ = run_agent(get_model("scripted"), rows, previous_rows())
    return 1.0 if grounding_gate(brief, rows, previous_rows()) == 0 else 0.0


def run_local():
    scores = {c["id"]: gate_expected(c, task(c)) for c in CASES}
    scores["agent_grounding"] = agent_grounding()
    for k, v in scores.items():
        print(f"  {k}: {v}")
    ok = all(v == 1.0 for v in scores.values())
    print("SUITE: PASS - no regressions." if ok else "SUITE: FAIL - a scorer regressed.")
    return 0 if ok else 1


def push_braintrust():
    import braintrust  # optional extra
    braintrust.Eval("target-gate",
                    data=lambda: [{"input": c, "expected": c["expected"]} for c in CASES],
                    task=task,
                    scores=[lambda input, expected, output:
                            braintrust.Score(name="gate_expected",
                                             score=gate_expected(input, output))])
