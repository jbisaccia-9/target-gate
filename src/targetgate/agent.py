"""The analysis agent: a real tool-calling loop over the snapshot data.

The agent's job is the network-change brief: what moved in each market since
the last snapshot. It works through TOOLS - list snapshots, pull one, diff a
market - and the loop is the standard OpenAI-style cycle: model returns
tool_calls, harness executes them, results go back, repeat until the model
emits the brief.

Two model backends, same loop:
  * FoundryModel  - an Azure AI Foundry / Azure OpenAI chat-completions
                    deployment (env: FOUNDRY_ENDPOINT, FOUNDRY_API_KEY,
                    FOUNDRY_DEPLOYMENT). The production path.
  * ScriptedModel - a deterministic backend for CI: it emits a fixed tool-call
                    sequence, but the brief it writes is composed from the
                    REAL tool results the loop hands back. The loop, the
                    tools, and the data flow are fully exercised; only the
                    decision policy is canned.

Whatever the backend, the brief must pass the GROUNDING GATE before it ships:
every 10-digit identifier in the text must exist in the snapshots it claims to
describe. An agent that invents providers does not get published to marketing.
"""
import json
import os
import re
import urllib.request

from . import pull
from .storage import get_container

SYSTEM = ("You are the market analyst for a provider-targeting program. "
          "Use the tools to compare the current snapshot with the previous one "
          "and write a short network-change brief per market: providers newly "
          "appearing, providers gone, coverage shifts. Cite NPIs for every "
          "specific claim. When done, reply with the brief text only.")


# ---------------------------------------------------------------- tools
def make_tools(current_rows, previous_rows):
    markets = sorted({r["state"] for r in current_rows})

    def list_markets():
        return {"states": markets}

    def diff_market(state):
        cur = {r["npi"]: r for r in current_rows if r["state"] == state}
        prev = {r["npi"]: r for r in previous_rows if r["state"] == state}
        return {"state": state,
                "added": [cur[n] for n in cur.keys() - prev.keys()],
                "dropped": [prev[n] for n in prev.keys() - cur.keys()],
                "current_count": len(cur), "previous_count": len(prev)}

    registry = {"list_markets": (list_markets, {}),
                "diff_market": (diff_market, {"state": {"type": "string"}})}
    schema = [{"type": "function",
               "function": {"name": name, "description": name.replace("_", " "),
                            "parameters": {"type": "object", "properties": params,
                                           "required": list(params)}}}
              for name, (_, params) in registry.items()]
    return registry, schema


# ---------------------------------------------------------------- backends
class FoundryModel:
    name = "foundry"

    def complete(self, messages, tools):
        url = (f"{os.environ['FOUNDRY_ENDPOINT'].rstrip('/')}/openai/deployments/"
               f"{os.environ['FOUNDRY_DEPLOYMENT']}/chat/completions"
               f"?api-version=2024-10-21")
        req = urllib.request.Request(
            url, data=json.dumps({"messages": messages, "tools": tools}).encode(),
            headers={"api-key": os.environ["FOUNDRY_API_KEY"],
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())["choices"][0]["message"]


class ScriptedModel:
    """Deterministic policy: survey markets, diff each, then write the brief
    from the tool results it actually received."""
    name = "scripted"

    def __init__(self):
        self.step = 0
        self.diffs = []

    def complete(self, messages, tools):
        last = messages[-1]
        if last.get("role") == "tool":
            payload = json.loads(last["content"])
            if "added" in payload:
                self.diffs.append(payload)
            if "states" in payload:
                self._states = payload["states"]
        if self.step == 0:
            self.step += 1
            return {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c0", "type": "function",
                 "function": {"name": "list_markets", "arguments": "{}"}}]}
        if self.step <= len(getattr(self, "_states", [])):
            state = self._states[self.step - 1]
            self.step += 1
            return {"role": "assistant", "content": None, "tool_calls": [
                {"id": f"c{self.step}", "type": "function",
                 "function": {"name": "diff_market",
                              "arguments": json.dumps({"state": state})}}]}
        lines = ["Network-change brief (scripted analyst; data from live tool calls):"]
        for d in self.diffs:
            lines.append(f"- {d['state']}: {d['previous_count']} -> {d['current_count']} providers.")
            for r in d["added"]:
                lines.append(f"    new: {r['name']} ({r['taxonomy']}, NPI {r['npi']})")
            for r in d["dropped"]:
                lines.append(f"    gone: {r['name']} (NPI {r['npi']})")
        return {"role": "assistant", "content": "\n".join(lines)}


class HallucinatingModel(ScriptedModel):
    """The failure case the grounding gate exists for: same policy, but the
    brief cites one provider that appears in no snapshot."""
    name = "hallucinating"

    def complete(self, messages, tools):
        msg = super().complete(messages, tools)
        if msg.get("content"):
            msg["content"] += "\n    new: Dr. Invented Person (Cardiology, NPI 9123456780)"
        return msg


# ---------------------------------------------------------------- loop + gate
def run_agent(model, current_rows, previous_rows, max_turns=12):
    registry, schema = make_tools(current_rows, previous_rows)
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": "Produce the network-change brief."}]
    for _ in range(max_turns):
        msg = model.complete(messages, schema)
        messages.append(msg)
        calls = msg.get("tool_calls")
        if not calls:
            return msg.get("content", ""), messages
        for call in calls:
            fn, _ = registry[call["function"]["name"]]
            args = json.loads(call["function"]["arguments"] or "{}")
            result = fn(**args)
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(result)})
    raise RuntimeError("agent exceeded max turns without producing a brief")


def grounding_gate(brief, current_rows, previous_rows):
    known = {r["npi"] for r in current_rows} | {r["npi"] for r in previous_rows}
    cited = set(re.findall(r"\b\d{10}\b", brief))
    ghosts = sorted(cited - known)
    print(f"  {'PASS' if not ghosts else 'FAIL'}  brief grounding: "
          f"{len(cited)} NPIs cited, {len(ghosts)} not present in any snapshot")
    for g in ghosts:
        print(f"    HALLUCINATED: {g}")
    if ghosts:
        print("BRIEF GATE: FAILED - the agent invented providers; brief not published.")
        return 1
    print("BRIEF GATE: PASSED - every cited identifier exists in the data.")
    return 0


def get_model(kind=None):
    kind = kind or ("foundry" if os.environ.get("FOUNDRY_ENDPOINT") else "scripted")
    return {"foundry": FoundryModel, "scripted": ScriptedModel,
            "hallucinating": HallucinatingModel}[kind]()


def previous_rows():
    return pull.pull_fixture("previous_snapshot.jsonl")
