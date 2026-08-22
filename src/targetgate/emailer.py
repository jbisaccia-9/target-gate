"""Outbound delivery: Microsoft Graph sendMail in production, a local outbox
of markdown files everywhere else.

Live mode POSTs to Graph's /v1.0/users/{sender}/sendMail with a bearer token
(the Office 365 connector path); local mode writes outbox/*.md so the exact
content that WOULD have been sent is inspectable. Both are called only from
behind the gate - there is no code path that sends an ungated list.
"""
import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]


def render_sales(lists, snapshot_date):
    lines = [f"# Sales target lists — snapshot {snapshot_date}", ""]
    for m in lists:
        lines += [f"## {m['market']} ({m['state']}) — {len(m['targets'])} targets", "",
                  "| provider | taxonomy | city | phone | NPI |", "|---|---|---|---|---|"]
        for t in m["targets"]:
            lines.append(f"| {t['name']} | {t['taxonomy']} | {t['city']} | "
                         f"{t['phone'] or '—'} | {t['npi']} |")
        lines.append("")
    return "\n".join(lines)


def render_marketing(lists, summary, snapshot_date):
    return (f"# Market coverage brief — snapshot {snapshot_date}\n\n{summary}\n\n"
            "Lists attached for campaign build; every row passed the list gate "
            "(checksum, dedupe, freshness, coverage).\n")


def deliver(lists, summary, snapshot_date):
    sales = render_sales(lists, snapshot_date)
    marketing = render_marketing(lists, summary, snapshot_date)
    if os.environ.get("GRAPH_TOKEN") and os.environ.get("GRAPH_SENDER"):
        for subject, body, to_env in [("Sales target lists", sales, "SALES_TO"),
                                      ("Market coverage brief", marketing, "MARKETING_TO")]:
            _send_graph(subject, body, os.environ.get(to_env, ""))
        return "graph"
    outbox = ROOT / "outbox"
    outbox.mkdir(exist_ok=True)
    (outbox / f"{snapshot_date}-sales.md").write_text(sales)
    (outbox / f"{snapshot_date}-marketing.md").write_text(marketing)
    return "outbox"


def _send_graph(subject, body, to):
    payload = {"message": {"subject": subject,
                           "body": {"contentType": "Text", "content": body},
                           "toRecipients": [{"emailAddress": {"address": to}}]}}
    req = urllib.request.Request(
        f"https://graph.microsoft.com/v1.0/users/{os.environ['GRAPH_SENDER']}/sendMail",
        data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Bearer {os.environ['GRAPH_TOKEN']}",
                 "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60)
