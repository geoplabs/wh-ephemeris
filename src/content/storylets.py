from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "phrasebank" / "storylets.json"


def _normalize_sequence(items: Sequence[object]) -> tuple[str, ...]:
    return tuple(
        str(item).strip()
        for item in items
        if isinstance(item, (str, int, float)) and str(item).strip()
    )


def _normalize_storylets(raw: Mapping[str, object]) -> dict[str, dict[str, object]]:
    pools: dict[str, dict[str, object]] = {}
    for area, sections in raw.items():
        area_key = str(area)
        normalized_sections: dict[str, object] = {}
        if not isinstance(sections, Mapping):
            continue
        for section, options in sections.items():
            section_key = str(section)
            if isinstance(options, Mapping):
                tone_map: dict[str, tuple[str, ...]] = {}
                for tone, phrases in options.items():
                    if isinstance(phrases, Sequence) and not isinstance(phrases, (str, bytes)):
                        normalized = _normalize_sequence(phrases)
                    else:
                        normalized = ()
                    if normalized:
                        tone_map[str(tone)] = normalized
                normalized_sections[section_key] = tone_map
            elif isinstance(options, Sequence) and not isinstance(options, (str, bytes)):
                normalized_sections[section_key] = _normalize_sequence(options)
        pools[area_key] = normalized_sections
    return pools


@lru_cache(maxsize=1)
def storylet_pools() -> Mapping[str, Mapping[str, object]]:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    raw = payload.get("storylets", payload)
    return _normalize_storylets(raw)


__all__ = ["storylet_pools"]
