import pytest

pytest.importorskip("jinja2")

from api.services.option_b_cleaner.render import build_context


def _base_option_b():
    return {
        "profile_name": "Taylor",
        "date": "2024-04-01",
        "mood": "steady",
        "theme": "balance",
        "opening_summary": "Focus arrives.",
        "morning_mindset": {"paragraph": "", "mantra": ""},
        "career": {"paragraph": "Progress at work is possible.", "bullets": []},
        "love": {"paragraph": "Share your heart.", "attached": "", "single": ""},
        "health": {"paragraph": "Rest matters.", "good_options": []},
        "finance": {"paragraph": "Budget carefully.", "bullets": []},
    }


def test_build_context_includes_classifier_and_tones():
    option_b = _base_option_b()
    option_b["events"] = [
        {
            "date": "2024-04-01",
            "transit_body": "Saturn",
            "natal_body": "Sun",
            "aspect": "square",
            "score": -65,
            "natal_house": 10,
        },
        {
            "date": "2024-04-01",
            "transit_body": "Venus",
            "natal_body": "Moon",
            "aspect": "trine",
            "score": 58,
            "natal_house": 7,
        },
    ]

    ctx = build_context(option_b)

    classifier_notes = ctx["tech_notes"]["classifier"]
    assert classifier_notes["section_tones"]["career"] == "challenge"
    assert classifier_notes["section_tones"]["love"] == "support"

    top_event = classifier_notes["top_event"]
    assert top_event["archetype"] == "Disciplined Crossroads"
    assert top_event["intensity"] in {"strong", "surge"}

    assert "Saturn presses on your Sun" in ctx["career_paragraph"]
    assert "Venus flows with your Moon" in ctx["love_paragraph"]
    assert classifier_notes["section_tones"]["finance"] == "neutral"


def test_area_rankings_pick_distinct_events():
    option_b = _base_option_b()
    option_b["events"] = [
        {
            "transit_body": "Saturn",
            "natal_body": "Sun",
            "aspect": "square",
            "score": -82,
            "natal_house": 10,
        },
        {
            "transit_body": "Venus",
            "natal_body": "Moon",
            "aspect": "trine",
            "score": 68,
            "natal_house": 7,
        },
        {
            "transit_body": "Mars",
            "natal_body": "Mercury",
            "aspect": "conjunction",
            "score": 59,
            "natal_house": 6,
        },
        {
            "transit_body": "Jupiter",
            "natal_body": "Venus",
            "aspect": "sextile",
            "score": 54,
            "natal_house": 2,
        },
    ]

    ctx = build_context(option_b)
    area_summary = ctx["tech_notes"]["areas"]

    assert area_summary["career"]["selected"]["event"]["natal_house"] == 10
    assert area_summary["love"]["selected"]["event"]["natal_house"] == 7
    assert area_summary["health"]["selected"]["event"]["natal_house"] == 6
    assert area_summary["finance"]["selected"]["event"]["natal_house"] in {2, 10}

    selected_houses = {
        area_summary[area]["selected"]["event"]["natal_house"]
        for area in ("career", "love", "health", "finance")
    }
    assert {10, 7, 6}.issubset(selected_houses)


def test_area_rankings_handle_empty_events():
    option_b = _base_option_b()
    option_b["events"] = []

    ctx = build_context(option_b)
    area_summary = ctx["tech_notes"]["areas"]

    for area in ("career", "love", "health", "finance"):
        assert area_summary[area]["selected"] is None
        assert area_summary[area]["ranking"] == []
        area_state = ctx["area_events"][area]
        assert area_state["event"] is None
        assert area_state["supporting"] is None
        assert ctx.get(f"{area}_event") is None


def test_area_rankings_apply_fallback_when_no_hints():
    option_b = _base_option_b()
    option_b["events"] = [
        {
            "transit_body": "Lilith",
            "aspect": "square",
            "score": -88,
        }
    ]

    ctx = build_context(option_b)
    area_summary = ctx["tech_notes"]["areas"]

    for area in ("career", "love", "health", "finance"):
        selected = area_summary[area]["selected"]
        assert selected is not None
        assert selected.get("is_fallback") is True
        assert selected["event"]["transit_body"] == "Lilith"
        assert ctx["area_events"][area]["event"]["transit_body"] == "Lilith"


def test_paragraphs_embed_event_details():
    option_b = _base_option_b()
    option_b["events"] = [
        {
            "transit_body": "Saturn",
            "natal_body": "Sun",
            "aspect": "square",
            "score": -92,
            "natal_house": 10,
        },
        {
            "transit_body": "Venus",
            "natal_body": "Moon",
            "aspect": "trine",
            "score": 78,
            "natal_house": 7,
        },
        {
            "transit_body": "Mars",
            "natal_body": "Mercury",
            "aspect": "conjunction",
            "score": 65,
            "natal_house": 6,
        },
        {
            "transit_body": "Jupiter",
            "natal_body": "Venus",
            "aspect": "sextile",
            "score": 62,
            "natal_house": 2,
        },
    ]

    ctx = build_context(option_b)

    assert "Saturn presses on your Sun" in ctx["career_paragraph"]
    assert "Venus flows with your Moon" in ctx["love_paragraph"]
    assert "Mars aligns with your Mercury" in ctx["health_paragraph"]
    assert "Jupiter supports your Venus" in ctx["finance_paragraph"]
    assert "Saturn presses on your Sun" in ctx["morning_paragraph"]
