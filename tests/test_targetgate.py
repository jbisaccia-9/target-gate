import datetime
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from targetgate.npi import valid, synthetic, luhn_check_digit
from targetgate.pull import pull_fixture
from targetgate.analyze import build_lists, completeness
from targetgate.gate import check
from targetgate.pipeline import run, load_config

TODAY = datetime.date(2026, 8, 21)


def test_npi_checksum_roundtrip():
    for seed in (1, 42, 99999999):
        assert valid(synthetic(seed))
    good = synthetic(7)
    flipped = good[:9] + str((int(good[9]) + 1) % 10)
    assert not valid(flipped)


def test_synthetic_npis_are_non_issuable():
    assert all(r["npi"].startswith("9") and valid(r["npi"]) for r in pull_fixture())


def test_fixture_clears_gate():
    config = load_config()
    rows = pull_fixture()
    lists = build_lists(rows, config)
    assert check(rows, lists, TODAY.isoformat(), config, today=TODAY) == 0


def test_corrupted_fixture_refused():
    config = load_config()
    rows = pull_fixture("corrupted_nppes.jsonl")
    lists = build_lists(rows, config)
    assert check(rows, lists, TODAY.isoformat(), config, today=TODAY) == 1


def test_stale_snapshot_refused():
    config = load_config()
    rows = pull_fixture()
    lists = build_lists(rows, config)
    stale = (TODAY - datetime.timedelta(days=30)).isoformat()
    assert check(rows, lists, stale, config, today=TODAY) == 1


def test_ranking_prefers_complete_contacts():
    config = load_config()
    lists = build_lists(pull_fixture(), config)
    for m in lists:
        scores = [completeness(t) for t in m["targets"]]
        assert scores == sorted(scores, reverse=True)


def test_blocked_run_sends_nothing(tmp_path, monkeypatch):
    import targetgate.pipeline as pl
    outbox = pathlib.Path(pl.ROOT / "outbox")
    before = set(outbox.glob("*.md")) if outbox.exists() else set()
    assert run(source="corrupted", today=TODAY) == 1
    after = set(outbox.glob("*.md")) if outbox.exists() else set()
    assert after == before        # gate failure produced zero outbound files


def test_clean_run_delivers_to_outbox():
    import targetgate.pipeline as pl
    assert run(source="fixture", today=TODAY) == 0
    sales = pathlib.Path(pl.ROOT / "outbox" / f"{TODAY}-sales.md")
    assert sales.exists() and "| provider |" in sales.read_text()
