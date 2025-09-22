"""Extended festivals helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List


def load_feeds() -> List[Dict[str, object]]:
    return [
        {"title": "Generic Observance", "type": "cultural", "month": 1, "day": 1},
        {"title": "Monthly Sankranti", "type": "festival", "month": None, "day": None},
    ]


def _normalise(entry: object) -> Dict[str, object]:
    if hasattr(entry, "model_dump"):
        return entry.model_dump()
    if isinstance(entry, dict):
        return entry
    raise TypeError("Unsupported observance entry type")


def festivals_for_date(
    date_local: datetime,
    tzinfo,
    lat: float,
    lon: float,
) -> List[Dict[str, object]]:
    local_date = date_local.astimezone(tzinfo).date()
    results: List[Dict[str, object]] = []
    for item in load_feeds():
        month = item.get("month")
        day = item.get("day")
        if month is not None and month != local_date.month:
            continue
        if day is not None and day != local_date.day:
            continue
        results.append({"title": item["title"], "type": item.get("type", "general")})
    return results


def merge_observances(
    vm_observances: Iterable[object],
    addl: Iterable[Dict[str, object]],
) -> List[Dict[str, object]]:
    merged: List[Dict[str, object]] = []
    seen = set()
    for entry in list(vm_observances) + list(addl):
        try:
            data = _normalise(entry)
        except TypeError:
            continue
        key = (data.get("title"), data.get("date"), data.get("start_ts"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(data)
    return merged
