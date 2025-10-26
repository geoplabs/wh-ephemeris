from src.content.archetype_router import classify_event


def test_classifier_radiant_expansion_supportive():
    event = {
        "date": "2024-02-10",
        "transit_body": "Jupiter",
        "natal_body": "Venus",
        "aspect": "trine",
        "orb": 0.4,
        "score": 72,
        "natal_house": 2,
    }
    result = classify_event(event)
    assert result["archetype"] == "Radiant Expansion"
    assert result["intensity"] == "strong"
    assert "tone:support" in result["tags"]
    assert "growth" in result["tags"]
    assert "money" in result["tags"]


def test_classifier_disciplined_crossroads_challenge():
    event = {
        "date": "2024-03-01",
        "transit_body": "Saturn",
        "natal_body": "Sun",
        "aspect": "square",
        "orb": 1.1,
        "score": -68,
        "natal_house": 10,
    }
    result = classify_event(event)
    assert result["archetype"] == "Disciplined Crossroads"
    assert result["intensity"] == "strong"
    assert "tone:challenge" in result["tags"]
    assert "discipline" in result["tags"]
    assert "career" in result["tags"]


def test_classifier_fallback_is_deterministic():
    event = {
        "date": "2024-01-05",
        "transit_body": "Mercury",
        "natal_body": "Vertex",
        "aspect": "novile",
        "orb": 0.2,
        "score": 5,
    }
    first = classify_event(event)
    second = classify_event(event)
    assert first == second
    assert first["archetype"] == "Steady Integration"
    assert "tone:neutral" in first["tags"]
