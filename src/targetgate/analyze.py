"""Rank providers into per-market target lists.

The local analyst is deterministic: filter to each market's state and
taxonomies, score by contact completeness, take the configured top N. The
narrative summary attached to the marketing email is produced by a pluggable
analyst - a template locally, or an Azure AI Foundry agent deployment when
ANALYST_ENDPOINT is set (the agent receives the same ranked table and returns
prose; ranking itself is never delegated to a model).
"""


def completeness(row):
    fields = ("name", "taxonomy", "city", "state", "phone")
    return sum(1 for f in fields if row.get(f)) / len(fields)


def build_lists(rows, config):
    out = []
    for m in config["markets"]:
        candidates = [r for r in rows
                      if r["state"] == m["state"] and r["taxonomy"] in m["taxonomies"]]
        ranked = sorted(candidates, key=lambda r: (-completeness(r), r["name"]))
        out.append({"market": m["market"], "state": m["state"],
                    "candidates": len(candidates),
                    "targets": ranked[:config["top_n_per_market"]]})
    return out


def summarize(lists):
    total = sum(len(m["targets"]) for m in lists)
    lines = [f"{total} targets across {len(lists)} strategic markets."]
    for m in lists:
        lines.append(f"- {m['market']} ({m['state']}): {len(m['targets'])} targets "
                     f"from {m['candidates']} candidates")
    return "\n".join(lines)
