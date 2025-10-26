from api.services.option_b_cleaner.language import (
    build_career_paragraph,
    build_love_status,
    build_opening_summary,
)


def test_opening_summary_backdrop():
    out = build_opening_summary(
        "Notably radiant energy in drive",
        "Powerfully harmonizing energy in emotional rhythms.",
        ["Libra", "Scorpio"],
    )
    assert "Harness this radiant push toward progress." in out
    assert "Cardinal Air (Libra)" in out
    assert "Fixed Water (Scorpio)" in out


def test_career_paragraph_micro_phrase():
    out = build_career_paragraph("Radiant focus supports progress at work.")
    sentences = [s for s in out.split(".") if s.strip()]
    assert len(sentences) == 2
    assert out.endswith("Let this focused drive move your intentions into form.")


def test_love_status_voice():
    attached = build_love_status("Channel this focus with intention.", "attached")
    single = build_love_status("Channel this focus with intention.", "single")
    assert attached.startswith("If you're attached, you")
    assert single.startswith("If you're single, you")
