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
    assert top_event["intensity"] == "strong"

    assert ctx["career_paragraph"].startswith("You steady")
    assert ctx["love_paragraph"].startswith("You nurture")
    assert classifier_notes["section_tones"]["finance"] == "neutral"
