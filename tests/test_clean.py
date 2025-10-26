from api.services.option_b_cleaner.clean import (
    clamp_sentences,
    de_jargon,
    imperative_bullet,
    to_you_pov,
)


def test_de_jargon():
    s = "Applying conjunction at 0.03° orb. Venus in Libra; Moon in Libra."
    out = de_jargon(s)
    assert "Applying" not in out and "0.03" not in out and "in Libra" not in out


def test_pov():
    out = to_you_pov("Ethan can focus on results.", "Ethan")
    assert out.startswith("You can")


def test_bullet():
    out = imperative_bullet("Notably radiant energy in drive. Applying…", order=0)
    assert out.startswith(("Focus", "Choose", "Set", "Plan"))
    assert "Applying" not in out and "…" not in out
    assert 3 <= len(out.rstrip(".").split()) <= 10


def test_avoid_bullet():
    out = imperative_bullet("Avoid overextending emotional energy…", order=1, mode="avoid")
    assert out.startswith(("Avoid", "Skip", "Hold", "Delay"))
    assert 3 <= len(out.rstrip(".").split()) <= 10


def test_clamp():
    p = "Sentence one. Sentence two. Sentence three."
    assert clamp_sentences(p, 2).count(".") <= 2
