from api.services.option_b_cleaner.language import (
    build_career_paragraph,
    build_finance_paragraph,
    build_health_paragraph,
)


def test_career_paragraph_with_full_event_details():
    text = build_career_paragraph(
        "",
        tone_hint="challenge",
        event={
            "transit_body": "Saturn",
            "natal_body": "Sun",
            "aspect": "square",
            "natal_house": 10,
        },
    )
    assert "Saturn presses on your Sun in the 10th house" in text
    assert "pressing square influence" in text


def test_career_paragraph_uses_transit_influence_when_details_missing():
    text = build_career_paragraph(
        "",
        tone_hint="support",
        event={"transit_body": "Pluto"},
    )
    assert "Pluto influence" in text


def test_health_paragraph_without_event_uses_base_template():
    text = build_health_paragraph(
        "",
        "",
        tone_hint="support",
        event=None,
    )
    assert text.startswith("You stay present to your energy curve by honoring balanced rhythms.")
    assert "while" not in text


def test_finance_paragraph_without_event_remains_plain():
    text = build_finance_paragraph(
        "",
        "",
        tone_hint="support",
        event=None,
    )
    assert "while" not in text
    assert "influence" not in text
