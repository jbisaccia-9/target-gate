"""Provider discovery: the NPPES NPI Registry (public, keyless) in live mode,
a committed synthetic fixture everywhere else.

Live results are real people's public registry entries, so they are written to
the (gitignored) container and never committed - the repo ships only the
generated fixture with non-issuable NPIs.
"""
import json
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
NPPES = "https://npiregistry.cms.hhs.gov/api/?version=2.1"


def pull_fixture(name="synthetic_nppes.jsonl"):
    return [json.loads(l) for l in
            (ROOT / "data" / name).read_text().splitlines() if l.strip()]


def pull_nppes(state, taxonomy, limit=50):
    q = urllib.parse.urlencode({"state": state, "taxonomy_description": taxonomy,
                                "limit": limit})
    with urllib.request.urlopen(f"{NPPES}&{q}", timeout=60) as r:
        results = json.loads(r.read()).get("results", [])
    rows = []
    for p in results:
        basic, addr = p.get("basic", {}), (p.get("addresses") or [{}])[0]
        tax = next((t for t in p.get("taxonomies", []) if t.get("primary")), {})
        rows.append({"npi": str(p.get("number", "")),
                     "name": (basic.get("organization_name")
                              or f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()),
                     "taxonomy": tax.get("desc", ""),
                     "city": addr.get("city", ""), "state": addr.get("state", ""),
                     "phone": addr.get("telephone_number", "")})
    return rows
