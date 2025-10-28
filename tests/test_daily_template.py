import importlib
import json
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

if "jinja2" not in sys.modules:
    class _StubTemplate:
        def __init__(self, source=""):
            self.source = source

        def render(self, **kwargs):
            return self.source

    class _StubEnvironment:
        def __init__(self, *args, **kwargs):
            pass

        def from_string(self, source):
            return _StubTemplate(source)

        def get_template(self, source):  # pragma: no cover - simple stub
            return _StubTemplate(source)

    class _StubFileSystemLoader:
        def __init__(self, *args, **kwargs):
            pass

    def _stub_autoescape(*args, **kwargs):  # pragma: no cover - simple stub
        return lambda *a, **kw: False

    sys.modules["jinja2"] = types.SimpleNamespace(
        Environment=_StubEnvironment,
        Template=_StubTemplate,
        FileSystemLoader=_StubFileSystemLoader,
        select_autoescape=_stub_autoescape,
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

daily_template = importlib.import_module("api.services.daily_template")

_build_fallback = daily_template._build_fallback
_ensure_sentence = daily_template._ensure_sentence
_trim_for_display = daily_template._trim_for_display
generate_daily_template = daily_template.generate_daily_template


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


def test_trim_for_display_returns_full_text_when_width_disabled():
    text = "A long sentence that should remain intact even when a traditional width limit would cut it."
    trimmed = _trim_for_display(text, width=None, ensure_sentence=True)
    assert trimmed == _ensure_sentence(text)


def test_build_fallback_has_no_ellipses():
    fallback = _build_fallback(_sample_daily_payload())
    for text in _collect_strings(fallback.model_dump(mode="python")):
        if not text:
            continue
        assert "..." not in text
        assert "…" not in text
        assert "—" not in text
        assert "–" not in text


def test_fallback_mantra_differs_from_affirmation():
    payload = _sample_daily_payload()
    fallback = _build_fallback(payload).model_dump(mode="python")
    assert fallback["morning_mindset"]["mantra"]
    assert fallback["morning_mindset"]["mantra"] != fallback["lucky"]["affirmation"]


def test_fallback_mantra_replaces_matching_affirmation():
    payload = _sample_daily_payload()
    shared_text = "I stand steady — even when plans shift."
    payload["lucky"]["affirmation"] = shared_text
    payload["morning_mindset"] = {"mantra": shared_text}

    fallback = _build_fallback(payload).model_dump(mode="python")

    lucky_affirmation = fallback["lucky"]["affirmation"]
    mantra = fallback["morning_mindset"]["mantra"]

    assert "—" not in lucky_affirmation and "–" not in lucky_affirmation
    assert "—" not in mantra and "–" not in mantra
    assert lucky_affirmation.endswith("plans shift.")
    assert mantra != lucky_affirmation


def test_fallback_adds_caution_and_remedies():
    fallback = _build_fallback(_sample_daily_payload()).model_dump(mode="python")
    caution = fallback["caution_window"]
    assert caution["time_window"]
    assert caution["note"].endswith(".")
    assert "—" not in caution["time_window"] and "–" not in caution["time_window"]
    remedies = fallback["remedies"]
    assert remedies and len(remedies) <= 4
    for item in remedies:
        assert item.endswith(".")
        assert "—" not in item and "–" not in item


def test_generate_daily_template_skips_llm_when_use_ai_false(monkeypatch):
    payload = _sample_daily_payload()
    payload["meta"]["use_ai"] = False

    def fail_get_client():
        raise AssertionError("OpenAI client should not be created when use_ai is false")

    def fail_render(*args, **kwargs):
        raise AssertionError("LLM renderer should not be invoked when use_ai is false")

    monkeypatch.setattr(daily_template, "_get_openai_client", fail_get_client)
    monkeypatch.setattr(daily_template, "_render_with_llm", fail_render)

    result = generate_daily_template(payload, {})

    assert result.payload is not None
    assert result.cache_hit is False


def test_generate_daily_template_uses_llm_when_use_ai_true(monkeypatch):
    payload = _sample_daily_payload()
    payload["meta"]["use_ai"] = True

    fake_client = object()
    monkeypatch.setattr(daily_template, "_get_openai_client", lambda: fake_client)

    expected_payload = _build_fallback(payload).model_dump(mode="json")

    def fake_validate(data):
        return True, []

    def fake_sanitize(data):
        return data

    render_calls = {"count": 0}

    def fake_render(client, daily, retry_payload=None):
        assert client is fake_client
        assert retry_payload is None
        render_calls["count"] += 1
        return expected_payload, json.dumps(expected_payload), 123

    monkeypatch.setattr(daily_template, "_validate_payload", fake_validate)
    monkeypatch.setattr(daily_template, "_sanitize_payload", fake_sanitize)
    original_build = daily_template._build_fallback

    def fail_fallback(*args, **kwargs):
        raise AssertionError("Fallback should not be used when the LLM succeeds")

    monkeypatch.setattr(daily_template, "_build_fallback", fail_fallback)
    monkeypatch.setattr(daily_template, "_render_with_llm", fake_render)

    try:
        result = generate_daily_template(payload, {})
    finally:
        monkeypatch.setattr(daily_template, "_build_fallback", original_build)

    assert render_calls["count"] == 1
    assert result.payload == expected_payload
