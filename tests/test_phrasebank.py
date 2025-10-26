import json
from pathlib import Path

import pytest

from src.content.phrasebank import assets, select_clause

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _read_snapshot(name: str):
    path = SNAPSHOT_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_phrasebank_coverage_snapshot():
    key_list = sorted(assets().keys())
    filtered = [key for key in key_list if key[2] in ("career", "love", "health", "finance")]
    expected = _read_snapshot("phrasebank_coverage.json")
    assert [list(key) for key in filtered] == expected


@pytest.mark.parametrize(
    "archetype,intensity,area,seed",
    [
        ("Radiant Expansion", "gentle", "career", 1042),
        ("Prosperity Build", "strong", "finance", 8821),
        ("Heart-Centered Calibration", "steady", "love", 3311),
        ("Disciplined Crossroads", "surge", "health", 7755),
        ("Visionary Alignment", "background", "general", 6420),
    ],
)
def test_phrase_selection_snapshot(archetype, intensity, area, seed):
    expected = _read_snapshot("phrase_selection.json")
    key = f"{archetype}|{intensity}|{area}|{seed}"
    value = select_clause(archetype, intensity, area, seed=seed)
    assert value == expected[key]
    # Determinism check
    assert select_clause(archetype, intensity, area, seed=seed) == value
