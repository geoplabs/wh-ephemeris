from __future__ import annotations

from src.content.variation import VariationEngine, VariationGroup, VariationItem


def test_permutation_is_seeded():
    items = ("alpha", "beta", "gamma", "delta")
    engine_a = VariationEngine(99)
    engine_b = VariationEngine(99)
    first = engine_a.permutation("clauses", items)
    second = engine_b.permutation("clauses", items)
    assert first == second

    seen = {first}
    for seed in range(100, 111):
        seen.add(VariationEngine(seed).permutation("clauses", items))
    assert len(seen) > 1


def test_variation_context_tokens_and_subset():
    engine = VariationEngine(42)
    groups = {
        "clauses": VariationGroup(
            name="clauses",
            mode="permutation",
            items=(
                VariationItem(text="one"),
                VariationItem(text="two"),
                VariationItem(text="three"),
            ),
        ),
        "adjective": VariationGroup(
            name="adjective",
            mode="choice",
            items=(VariationItem(text="radiant"), VariationItem(text="steady")),
            pick=1,
        ),
        "optional_sentences": VariationGroup(
            name="optional_sentences",
            mode="subset",
            items=(VariationItem(text="Carry a {adjective} note forward"),),
            minimum=1,
            maximum=1,
        ),
    }
    context = engine.evaluate(groups)
    tokens = context.tokens()
    assert context.first("clauses") in {"one", "two", "three"}
    assert tokens["adjective"] in {"radiant", "steady"}
    extra = context.selections("optional_sentences")
    assert extra
    sentence = extra[0].format(adjective=tokens["adjective"])
    assert sentence.startswith("Carry a ")
