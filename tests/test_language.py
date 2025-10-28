from api.services.option_b_cleaner.language import (
    _ensure_sentence,
    build_career_paragraph,
    build_love_status,
    build_opening_summary,
)
from src.content.phrasebank import select_clause


def test_opening_summary_backdrop():
    clause = select_clause("Radiant Expansion", "gentle", "general", seed=42)
    out = build_opening_summary(
        "Notably radiant energy in drive",
        "Powerfully harmonizing energy in emotional rhythms.",
        ["Libra", "Scorpio"],
        clause=clause,
    )
    assert clause.lower().rstrip(".") in out.lower()
    assert "Cardinal Air (Libra)" in out
    assert "Fixed Water (Scorpio)" in out


def test_career_paragraph_micro_phrase():
    clause = select_clause("Radiant Expansion", "steady", "career", seed=7)
    out = build_career_paragraph("Radiant focus supports progress at work.", clause=clause)
    sentences = [s for s in out.split(".") if s.strip()]
    assert len(sentences) >= 2
    assert clause.strip() in out
    assert out.endswith(clause)


def test_love_status_voice():
    attached = build_love_status("Channel this focus with intention.", "attached")
    single = build_love_status("Channel this focus with intention.", "single")
    assert attached.startswith("If you're attached, you")
    assert single.startswith("If you're single, you")


def test_ensure_sentence_collapses_repeated_words():
    sentence = _ensure_sentence("Money choices choices support the plan")
    assert "choices choices" not in sentence
    assert sentence.endswith(".")
