from api.services.option_b_cleaner.clean import (
    clamp_sentences,
    clean_token_phrase,
    clean_tokens,
    de_jargon,
    imperative_bullet,
    to_you_pov,
)
from src.content.phrasebank import get_asset


def test_de_jargon():
    s = "Applying conjunction at 0.03° orb. Venus in Libra; Moon in Libra."
    out = de_jargon(s)
    assert "Applying" not in out and "0.03" not in out and "in Libra" not in out


def test_pov():
    out = to_you_pov("Ethan can focus on results.", "Ethan")
    assert out.startswith("You can")


def test_bullet():
    asset = get_asset("Radiant Expansion", "steady", "career")
    out = imperative_bullet(
        "Notably radiant energy in drive. Applying…",
        order=0,
        area="career",
        asset=asset,
    )
    assert out.startswith("Focus")
    assert "Applying" not in out and "…" not in out
    assert 3 <= len(out.rstrip(".").split()) <= 10


def test_avoid_bullet():
    asset = get_asset("Phoenix Reframe", "strong", "love")
    out = imperative_bullet(
        "Avoid overextending emotional energy…",
        order=1,
        mode="avoid",
        area="love",
        asset=asset,
    )
    assert out.startswith("Skip")
    assert 3 <= len(out.rstrip(".").split()) <= 10


def test_clamp():
    p = "Sentence one. Sentence two. Sentence three."
    assert clamp_sentences(p, 2).count(".") <= 2


def test_clean_tokens_expose_sanitized_values():
    tokens = clean_tokens("Mars' influence surges—stay ready.")
    assert tokens[:2] == ["Mars", "influence"]


def test_clean_token_phrase_combines_tokens():
    phrase = clean_token_phrase("Neptune's dreamy pull")
    assert phrase == "Neptunes dreamy pull"
