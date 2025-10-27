#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.content.phrasebank import assets
from src.content.variation import VariationEngine


def _sample_range(seed: int, count: int) -> Iterable[int]:
    for offset in range(count):
        yield seed + offset


def summarize_variations(samples: int, seed: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (archetype, intensity, area), asset in sorted(assets().items()):
        clause_seen: set[str] = set()
        adjective_seen: set[str] = set()
        optional_counts: Counter[int] = Counter()
        for current in _sample_range(seed, samples):
            engine = VariationEngine(current)
            context = engine.evaluate(asset.variation_groups)
            clause = context.first("clauses", asset.clause_cycle()[0] if asset.clause_cycle() else "")
            clause_seen.add(clause)
            tokens = context.tokens()
            adjective = tokens.get("adjective")
            if adjective:
                adjective_seen.add(adjective)
            optional_counts[len(context.selections("optional_sentences"))] += 1
        rows.append(
            {
                "archetype": archetype,
                "intensity": intensity,
                "area": area,
                "unique_clauses": len(clause_seen),
                "unique_adjectives": len(adjective_seen),
                "optional_histogram": dict(optional_counts),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Report variation coverage across phrase assets.")
    parser.add_argument("--samples", type=int, default=30, help="Number of consecutive seeds to evaluate (default: 30)")
    parser.add_argument("--seed", type=int, default=10_000, help="Base seed for sampling (default: 10000)")
    args = parser.parse_args()

    rows = summarize_variations(args.samples, args.seed)
    widest = max(len(row["archetype"]) for row in rows)
    header = f"{'Archetype'.ljust(widest)}  Intensity  Area      Clauses  Adjectives  Optional"  # noqa: E501
    print(header)
    print("-" * len(header))
    for row in rows:
        optional = ", ".join(f"{count}x{freq}" for count, freq in sorted(row["optional_histogram"].items()))
        print(
            f"{row['archetype'].ljust(widest)}  {row['intensity']:<9}  {row['area']:<8}  "
            f"{row['unique_clauses']:<7}  {row['unique_adjectives']:<11}  {optional or '0x0'}"
        )


if __name__ == "__main__":  # pragma: no cover - CLI utility
    main()
