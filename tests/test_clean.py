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


def test_bullet_cleanup_handles_boundary_priority():
    asset = get_asset("Radiant Expansion", "steady", "career")
    sentence = "Set sensitive responsibility boundaries priorities that highlight your leadership."
    out = imperative_bullet(sentence, order=2, area="career", asset=asset)
    assert "boundaries priorities" not in out
    assert "outer conversations" not in out


def test_bullet_keeps_support_phrase():
    asset = get_asset("Radiant Expansion", "steady", "career")
    sentence = "Choose radiant drive to support professional wins."
    out = imperative_bullet(sentence, order=1, area="career", asset=asset)
    assert "to support professional wins" in out


def test_bullet_prunes_growth_intentions_tail():
    asset = get_asset("Radiant Expansion", "steady", "general")
    sentence = "Choose emotional growth rhythms to anchor your intentions."
    out = imperative_bullet(sentence, order=0, area="general", asset=asset)
    assert out.endswith("growth rhythms today.")


def test_bullet_curiosity_sentence_gets_conversation_action():
    asset = get_asset("Radiant Expansion", "steady", "career")
    sentence = "Choose curious conversations energy to support professional wins."
    out = imperative_bullet(sentence, order=0, area="career", asset=asset)
    assert out == "Start one curious, open-ended conversation that advances a work goal."


def test_bullet_priority_sentence_sets_two_priorities():
    asset = get_asset("Radiant Expansion", "steady", "career")
    sentence = "Set radiant drive personal power priorities that highlight your leadership."
    out = imperative_bullet(sentence, order=0, area="career", asset=asset)
    assert out == "Set two priorities that showcase your initiative."


def test_health_bullet_retains_tune_phrase():
    asset = get_asset("Steady Integration", "steady", "health")
    sentence = "Focus on radiant drive to tune into your body."
    out = imperative_bullet(sentence, order=0, area="health", asset=asset)
    assert out == "Focus on radiant drive to tune into your body."


def test_clamp():
    p = "Sentence one. Sentence two. Sentence three."
    assert clamp_sentences(p, 2).count(".") <= 2


def test_clean_tokens_expose_sanitized_values():
    tokens = clean_tokens("Mars' influence surges—stay ready.")
    assert tokens[:2] == ["Mars", "influence"]


def test_clean_token_phrase_combines_tokens():
    phrase = clean_token_phrase("Neptune's dreamy pull")
    assert phrase == "Neptunes dreamy pull"
