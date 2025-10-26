import sys
import types

if "redis" not in sys.modules:
    sys.modules["redis"] = types.SimpleNamespace(
        Redis=type(
            "_StubRedis",
            (),
            {"from_url": staticmethod(lambda *args, **kwargs: None)},
        )
    )

if "jsonschema" not in sys.modules:
    sys.modules["jsonschema"] = types.SimpleNamespace(
        Draft7Validator=type(
            "_StubValidator",
            (),
            {
                "__init__": lambda self, *args, **kwargs: None,
                "iter_errors": staticmethod(lambda *args, **kwargs: []),
            },
        )
    )

if "api.schemas" not in sys.modules:
    sys.modules["api.schemas"] = types.ModuleType("api.schemas")

if "api.schemas.forecasts" not in sys.modules:
    forecasts_module = types.ModuleType("api.schemas.forecasts")

    class _StubDailyTemplatedResponse:
        def __init__(self, **data):
            self._data = data

        @classmethod
        def model_validate(cls, data):
            return cls(**data)

        def model_dump(self, mode="python"):
            return dict(self._data)

    forecasts_module.DailyTemplatedResponse = _StubDailyTemplatedResponse
    sys.modules["api.schemas"].forecasts = forecasts_module
    sys.modules["api.schemas.forecasts"] = forecasts_module

from api.services.daily_template import _build_fallback, _trim_for_display


def _sample_daily_payload():
    long_note = (
        "Powerfully harmonizing energy in emotional rhythms. Channel this focus with intention. "
        "Applying conjunction at 0.03° orb. Venus in Libra; Moon in Libra."
    )
    return {
        "meta": {"profile_name": "Ethan", "date": "2025-10-28"},
        "summary": long_note,
        "focus_areas": [
            {
                "area": "career",
                "headline": "Notably radiant energy in drive with supportive focus and intention",
                "guidance": "Channel this focus with intention.",
                "events": [
                    {
                        "note": long_note,
                    }
                ],
            },
            {
                "area": "health",
                "headline": "Notably curious period for inner growth with compassionate choices",
                "guidance": "Trust the momentum and share your gifts.",
                "events": [
                    {
                        "note": "Notably curious period for inner growth. Trust the momentum and share your gifts."
                    }
                ],
            },
        ],
        "events": [
            {"aspect": "Conjunction", "note": long_note},
            {
                "aspect": "Square",
                "note": "Gently disciplined challenges around relationships. Take decisive steps to work through the tension.",
            },
        ],
        "lucky": {
            "color": "soft rose with rose quartz accents",
            "time_window": "17:00–19:00 (twilight)",
            "direction": "South-East",
            "affirmation": "I let my relationships and emotional rhythms move as one focused current.",
        },
    }


def _collect_strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        collected = []
        for item in value.values():
            collected.extend(_collect_strings(item))
        return collected
    if isinstance(value, list):
        collected = []
        for item in value:
            collected.extend(_collect_strings(item))
        return collected
    return []


def test_trim_for_display_avoids_ellipses():
    text = "One. Two sentences follow with extra detail that would have been clipped."
    trimmed = _trim_for_display(text, width=40, ensure_sentence=True)
    assert "..." not in trimmed and "…" not in trimmed
    assert trimmed.endswith(".")


def test_build_fallback_has_no_ellipses():
    fallback = _build_fallback(_sample_daily_payload())
    for text in _collect_strings(fallback.model_dump(mode="python")):
        if not text:
            continue
        assert "..." not in text
        assert "…" not in text
