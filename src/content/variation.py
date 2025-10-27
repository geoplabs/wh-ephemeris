from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Iterable, Iterator, Mapping, MutableMapping, Sequence, Tuple, TypeVar


T = TypeVar("T")


VariationMode = str


def _hashed_seed(seed: int, key: str) -> int:
    digest = blake2b(f"{seed}|{key}".encode("utf-8"), digest_size=8)
    return int.from_bytes(digest.digest(), "big")


@dataclass(frozen=True)
class VariationGroup:
    """Declarative instructions describing how to derive a variation."""

    name: str
    mode: VariationMode
    items: tuple[str, ...]
    pick: int | None = None
    minimum: int | None = None
    maximum: int | None = None

    def normalized(self) -> "VariationGroup":
        pick = self.pick if (self.pick or 0) > 0 else None
        minimum = max(self.minimum or 0, 0)
        maximum = self.maximum if self.maximum is not None else None
        if maximum is not None and maximum < minimum:
            maximum = minimum
        return VariationGroup(
            name=self.name,
            mode=self.mode,
            items=tuple(self.items),
            pick=pick,
            minimum=minimum,
            maximum=maximum,
        )


@dataclass(frozen=True)
class VariationResult:
    """Resolved value for a variation group."""

    name: str
    selections: tuple[str, ...]
    mode: VariationMode

    def first(self, default: str = "") -> str:
        return self.selections[0] if self.selections else default


class VariationContext(Mapping[str, VariationResult]):
    """Container exposing resolved variation results."""

    def __init__(self, results: Mapping[str, VariationResult] | None = None) -> None:
        self._results: MutableMapping[str, VariationResult] = dict(results or {})

    def __getitem__(self, key: str) -> VariationResult:  # type: ignore[override]
        return self._results[key]

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        return iter(self._results)

    def __len__(self) -> int:  # type: ignore[override]
        return len(self._results)

    def first(self, key: str, default: str = "") -> str:
        result = self._results.get(key)
        if not result:
            return default
        return result.first(default)

    def selections(self, key: str, default: Sequence[str] | None = None) -> tuple[str, ...]:
        result = self._results.get(key)
        if not result:
            return tuple(default or ())
        return result.selections

    def tokens(self) -> dict[str, str]:
        tokens: dict[str, str] = {}
        for name, result in self._results.items():
            if len(result.selections) == 1:
                tokens[name] = result.selections[0]
        return tokens


class VariationEngine:
    """Deterministic helper for clause ordering and other micro-variations."""

    def __init__(self, seed: int) -> None:
        self.seed = seed

    def permutation(self, key: str, items: Sequence[T]) -> tuple[T, ...]:
        values = list(items)
        if len(values) <= 1:
            return tuple(values)
        import random

        rng = random.Random(_hashed_seed(self.seed, key))
        rng.shuffle(values)
        return tuple(values)

    def choice(self, key: str, items: Sequence[T], *, pick: int = 1) -> tuple[T, ...]:
        values = list(dict.fromkeys(items))
        if not values:
            return tuple()
        pick = min(max(int(pick), 1), len(values))
        import random

        rng = random.Random(_hashed_seed(self.seed, key))
        return tuple(rng.sample(values, pick))

    def subset(
        self,
        key: str,
        items: Sequence[T],
        *,
        minimum: int = 0,
        maximum: int | None = None,
    ) -> tuple[T, ...]:
        values = list(dict.fromkeys(items))
        if not values:
            return tuple()
        import random

        rng = random.Random(_hashed_seed(self.seed, key))
        max_pick = len(values) if maximum is None else min(int(maximum), len(values))
        min_pick = max(int(minimum), 0)
        if min_pick > max_pick:
            min_pick = max_pick
        count = rng.randint(min_pick, max_pick)
        if count >= len(values):
            return tuple(values)
        if count == 0:
            return tuple()
        return tuple(rng.sample(values, count))

    def evaluate(self, groups: Mapping[str, VariationGroup] | None) -> VariationContext:
        if not groups:
            return VariationContext()
        results: dict[str, VariationResult] = {}
        for name, group in groups.items():
            normalized = group.normalized()
            if normalized.mode == "permutation":
                selections = self.permutation(name, normalized.items)
            elif normalized.mode == "choice":
                selections = self.choice(name, normalized.items, pick=normalized.pick or 1)
            elif normalized.mode == "subset":
                selections = self.subset(
                    name,
                    normalized.items,
                    minimum=normalized.minimum or 0,
                    maximum=normalized.maximum,
                )
            else:
                raise ValueError(f"Unsupported variation mode '{normalized.mode}' for {name}")
            results[name] = VariationResult(name=name, selections=selections, mode=normalized.mode)
        return VariationContext(results)


__all__ = [
    "VariationContext",
    "VariationEngine",
    "VariationGroup",
    "VariationResult",
]

