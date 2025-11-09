import importlib
import json
import re
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
_apply_special_sky_events = daily_template._apply_special_sky_events
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


_ROOT_STOPWORDS = {
    "avoid",
    "clarity",
    "choose",
    "focus",
    "hold",
    "keep",
    "momentum",
    "note",
    "plan",
    "set",
    "skip",
    "stay",
    "support",
    "today",
    "track",
    "trust",
    "with",
    "your",
}


def _root_tokens(sentences):
    tokens: set[str] = set()
    for sentence in sentences:
        for token in re.findall(r"[A-Za-z]+", sentence.lower()):
            if token in _ROOT_STOPWORDS or len(token) <= 2:
                continue
            base = token
            if base.endswith("ing") and len(base) > 4:
                base = base[:-3]
            elif base.endswith("ies") and len(base) > 4:
                base = base[:-3] + "y"
            elif base.endswith("s") and len(base) > 3:
                base = base[:-1]
            tokens.add(base)
    return tokens


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
    assert lucky_affirmation.endswith(".")
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


def test_sanitize_payload_preserves_caution_and_remedies():
    payload = {
        "profile_name": "Ethan",
        "date": "2025-10-30",
        "mood": "motivated",
        "theme": "Radiant focus",
        "opening_summary": "A focused day awaits.",
        "morning_mindset": {"paragraph": "Stay steady.", "mantra": "I choose clarity."},
        "career": {"paragraph": "Share progress.", "bullets": ["Send an update."]},
        "love": {
            "paragraph": "Listen closely.",
            "attached": "Offer a kind word.",
            "single": "Stay open to conversation.",
        },
        "health": {"paragraph": "Stretch mindfully.", "good_options": ["Hydrate well."]},
        "finance": {"paragraph": "Review budgets.", "bullets": ["Check expenses."]},
        "do_today": ["Outline priorities."],
        "avoid_today": ["Skip impulsive decisions."],
        "caution_window": {"time_window": "13:00-14:00", "note": "Double-check commitments."},
        "remedies": ["Take three deep breaths.", "Review your calendar."],
        "lucky": {
            "color": "royal blue",
            "time_window": "08:00-10:00",
            "direction": "North",
            "affirmation": "I act with purpose.",
        },
        "one_line_summary": "Lead with balance.",
    }

    sanitized = daily_template._sanitize_payload(payload)

    assert sanitized["caution_window"] == {
        "time_window": "13:00-14:00",
        "note": "Double-check commitments.",
    }
    assert sanitized["remedies"] == [
        "Take three deep breaths.",
        "Review your calendar.",
    ]


def test_fallback_do_and_avoid_focus_are_distinct():
    fallback = _build_fallback(_sample_daily_payload()).model_dump(mode="python")
    do_roots = _root_tokens(fallback["do_today"])
    avoid_roots = _root_tokens(fallback["avoid_today"])
    assert do_roots
    assert avoid_roots
    assert not do_roots.intersection(avoid_roots)


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


def test_special_sky_events_are_injected_into_output():
    payload = _sample_daily_payload()
    special_events = [
        {
            "event_type": "lunar_phase",
            "phase_name": "full_moon",
            "note": "Full Moon: Insight peaks around relationships",
            "special_moon": {
                "has_special_moon": True,
                "banner": "Supermoon",
                "description": "Emotions and events amplify—move intentionally",
            },
            "score": 1.2,
        },
        {
            "event_type": "void_of_course",
            "note": "Void-of-course Moon from 14:00-17:00 UTC invites gentle pacing.",
            "score": 0.4,
        },
    ]

    payload["events"] = special_events
    payload["top_events"] = special_events

    fallback = _build_fallback(payload).model_dump(mode="json")
    updated = _apply_special_sky_events(fallback, payload)

    assert "Special sky watch:" in updated["opening_summary"]
    assert "Special sky watch:" in updated["morning_mindset"]["paragraph"]
    assert "Supermoon" in updated["opening_summary"]
    assert "Void-of-course Moon" in updated["opening_summary"]
    assert "Special sky watch:" in updated["one_line_summary"]


def test_special_sky_events_skip_when_none_present():
    payload = _sample_daily_payload()
    fallback = _build_fallback(payload).model_dump(mode="json")
    updated = _apply_special_sky_events(fallback, payload)

    assert updated is fallback
    assert "Special sky watch:" not in updated["opening_summary"]


def test_eclipse_with_personalization_formatting():
    """Test that eclipse events show personalization and visibility boosts."""
    from datetime import datetime
    payload = _sample_daily_payload()
    payload["events"] = [
        {
            "event_type": "eclipse",
            "note": "Total Solar Eclipse - major new chapter begins",
            "eclipse_info": {
                "banner": "Solar Eclipse (Total)",
                "tone_line": "Sun reboot – destiny hands you a blank page.",
                "eclipse_category": "solar",
                "eclipse_type": "total",
                "personalization_boost": 0.4,  # 40% boost
                "visibility_boost": 0.15,
            },
            "score": 3.54,
        }
    ]
    
    fallback = _build_fallback(payload).model_dump(mode="json")
    updated = _apply_special_sky_events(fallback, payload)
    
    opening = updated["opening_summary"]
    assert "Solar Eclipse" in opening
    assert "Sun reboot" in opening
    assert "activates your natal chart powerfully" in opening  # Personalization mention


def test_eclipse_with_visibility_boost():
    """Test that visible eclipses mention visibility."""
    payload = _sample_daily_payload()
    payload["events"] = [
        {
            "event_type": "eclipse",
            "eclipse_info": {
                "banner": "Lunar Eclipse (Partial)",
                "tone_line": "Lunar spotlight – revelations surface.",
                "eclipse_category": "lunar",
                "eclipse_type": "partial",
                "personalization_boost": 0.0,  # No personal boost
                "visibility_boost": 0.15,  # But visible
            },
            "score": 1.68,
        }
    ]
    
    fallback = _build_fallback(payload).model_dump(mode="json")
    updated = _apply_special_sky_events(fallback, payload)
    
    opening = updated["opening_summary"]
    assert "Lunar Eclipse" in opening
    assert "Visible from your location" in opening


def test_blood_moon_alias_included_in_summary():
    payload = _sample_daily_payload()
    payload["events"] = [
        {
            "event_type": "eclipse",
            "eclipse_info": {
                "banner": "Blood Moon Lunar Eclipse (Total)",
                "tone_line": "Blood Moon peak – emotional tides surge.",
                "aliases": ["Blood Moon"],
                "eclipse_category": "lunar",
                "eclipse_type": "total",
                "personalization_boost": 0.0,
                "visibility_boost": 0.0,
            },
            "score": 2.4,
        }
    ]

    fallback = _build_fallback(payload).model_dump(mode="json")
    updated = _apply_special_sky_events(fallback, payload)

    opening = updated["opening_summary"]
    assert "Blood Moon" in opening
    assert "Lunar Eclipse" in opening


def test_eclipse_without_detailed_info_infers_labels():
    payload = _sample_daily_payload()
    payload["events"] = [
        {
            "event_type": "eclipse",
            "note": "Eclipse",
            "eclipse_category": "lunar",
            "eclipse_type": "total",
            "aliases": ["Blood Moon"],
            "score": 1.9,
        }
    ]

    fallback = _build_fallback(payload).model_dump(mode="json")
    updated = _apply_special_sky_events(fallback, payload)

    opening = updated["opening_summary"]
    assert "Lunar Eclipse (Total)" in opening
    assert "Blood Moon" in opening


def test_void_of_course_with_time_window():
    """Test that VoC Moon displays time windows."""
    from datetime import datetime
    payload = _sample_daily_payload()
    voc_start = datetime(2025, 11, 15, 18, 30)
    voc_end = datetime(2025, 11, 16, 2, 15)
    payload["events"] = [
        {
            "event_type": "void_of_course",
            "note": "Void-of-course Moon invites gentle pacing.",
            "voc_info": {
                "banner": "Void of Course Moon",
                "tone_line": "Low-signal window – prep/review beats go-time.",
                "window": {
                    "start": voc_start,
                    "end": voc_end,
                    "total_hours": 7.75,
                },
            },
            "score": -0.3,
        }
    ]
    
    fallback = _build_fallback(payload).model_dump(mode="json")
    updated = _apply_special_sky_events(fallback, payload)
    
    opening = updated["opening_summary"]
    assert "Void of Course Moon" in opening or "Void-of-course Moon" in opening
    assert "18:30-02:15 UTC" in opening  # Time window displayed


def test_void_of_course_with_iso_string_times():
    """Test that VoC Moon handles ISO string dates correctly."""
    payload = _sample_daily_payload()
    payload["events"] = [
        {
            "event_type": "void_of_course",
            "voc_info": {
                "banner": "Void of Course Moon",
                "tone_line": "Low-signal window.",
                "window": {
                    "start": "2025-11-15T14:00:00+00:00",
                    "end": "2025-11-15T17:30:00+00:00",
                },
            },
            "score": -0.3,
        }
    ]
    
    fallback = _build_fallback(payload).model_dump(mode="json")
    updated = _apply_special_sky_events(fallback, payload)
    
    opening = updated["opening_summary"]
    assert "14:00-17:30 UTC" in opening  # Parsed from ISO strings


def test_duplicate_detection_with_word_overlap():
    """Test improved duplicate detection based on word overlap."""
    base = "The Full Moon brings powerful energy for relationships and growth."
    addition = "Full Moon brings energy for relationships."  # >70% word overlap
    
    result = daily_template._append_sentence(base, addition)
    
    # Should NOT append because of high word overlap
    assert result == base.rstrip() + "."  # Just the base, ensured as sentence


def test_duplicate_detection_allows_different_content():
    """Test that different content is appended."""
    base = "The Full Moon brings powerful energy for relationships."
    addition = "Void of Course Moon from 14:00-17:00 UTC."  # Completely different
    
    result = daily_template._append_sentence(base, addition)
    
    # Should append because content is different
    assert "Full Moon" in result
    assert "Void of Course" in result
    assert result.count(".") >= 2  # Two sentences


def test_special_event_priority_sorting():
    """Test that events are sorted by priority (eclipse > lunar > voc > oob)."""
    payload = _sample_daily_payload()
    payload["events"] = [
        {"event_type": "out_of_bounds", "score": 0.3},
        {"event_type": "void_of_course", "score": 0.5},
        {"event_type": "eclipse", "eclipse_info": {"banner": "Solar Eclipse"}, "score": 2.0},
        {"event_type": "lunar_phase", "phase_name": "full_moon", "score": 1.0},
    ]
    
    mentions = daily_template._special_event_mentions(payload["events"])
    
    # Should have max 2 mentions
    assert len(mentions) <= 2
    
    # Eclipse should be first (priority 0)
    assert "Eclipse" in mentions[0] or "Solar" in mentions[0]
    
    # Lunar phase should be second (priority 1)
    if len(mentions) > 1:
        assert "Moon" in mentions[1] or "Lunar" in mentions[1]


def test_special_event_strength_sorting_within_priority():
    """Test that within same priority, stronger events come first."""
    payload = _sample_daily_payload()
    payload["events"] = [
        {
            "event_type": "lunar_phase",
            "phase_name": "first_quarter",
            "lunar_phase_info": {"banner": "First Quarter Moon"},
            "score": 0.5,
        },
        {
            "event_type": "lunar_phase",
            "phase_name": "full_moon",
            "lunar_phase_info": {"banner": "Full Moon"},
            "score": 1.2,
        },
    ]
    
    mentions = daily_template._special_event_mentions(payload["events"])
    
    # Full moon (stronger score 1.2) should appear before first quarter (0.5)
    assert len(mentions) >= 1
    assert "Full" in mentions[0]