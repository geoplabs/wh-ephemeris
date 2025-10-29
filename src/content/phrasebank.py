from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from hashlib import blake2b
from pathlib import Path
from typing import Iterable, Mapping

from .variation import VariationContext, VariationEngine, VariationGroup


DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "phrasebank"
PHRASES_PATH = DATA_ROOT / "phrases.json"

ARCHETYPES: tuple[str, ...] = (
    "Radiant Expansion",
    "Prosperity Build",
    "Heart-Centered Calibration",
    "Disciplined Crossroads",
    "Visionary Alignment",
    "Phoenix Reframe",
    "Steady Integration",
)

INTENSITIES: tuple[str, ...] = ("background", "gentle", "steady", "strong", "surge")
AREAS: tuple[str, ...] = ("general", "career", "love", "health", "finance")


@dataclass(frozen=True)
class PhraseRequirements:
    """Requirements for phrase grammatical transformations."""
    expected_types: tuple[str, ...]  # e.g., ("gerund", "noun")
    fallback: str  # Fallback phrase if transformation fails
    lowercase: bool = False
    add_article: bool = False


@dataclass(frozen=True)
class PhraseAsset:
    archetype: str
    intensity: str
    area: str
    clause_variants: tuple[str, ...]
    bullet_templates: Mapping[str, tuple[str, ...]]
    variation_groups: Mapping[str, VariationGroup]
    phrase_requirements: PhraseRequirements | None = None

    def clause_cycle(self) -> tuple[str, ...]:
        return tuple(c.strip() for c in self.clause_variants if c and c.strip())

    def templates_for(self, mode: str) -> tuple[str, ...]:
        templates = self.bullet_templates.get(mode, ())
        return tuple(t.strip() for t in templates if t and t.strip())

    def variations(self, seed: int | None) -> VariationContext:
        if seed is None:
            return VariationContext()
        engine = VariationEngine(seed)
        return engine.evaluate(self.variation_groups)


def _load_raw() -> Mapping[str, object]:
    with PHRASES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _asset_map() -> Mapping[tuple[str, str, str], PhraseAsset]:
    payload = _load_raw()
    entries = payload.get("entries", [])
    assets: dict[tuple[str, str, str], PhraseAsset] = {}
    for entry in entries:
        archetype = str(entry.get("archetype"))
        intensity = str(entry.get("intensity"))
        area = str(entry.get("area"))
        clause_variants = tuple(entry.get("clause_variants", ()))
        bullet_templates = {
            str(mode): tuple(values)
            for mode, values in (entry.get("bullet_templates") or {}).items()
        }
        variation_groups = {}
        for name, config in (entry.get("variation_groups") or {}).items():
            items = tuple(
                str(item).strip()
                for item in (config.get("items") or [])
                if str(item or "").strip()
            )
            variation_groups[str(name)] = VariationGroup(
                name=str(name),
                mode=str(config.get("mode", "choice")),
                items=items,
                pick=(config.get("pick") if config.get("pick") is not None else None),
                minimum=(config.get("minimum") if config.get("minimum") is not None else None),
                maximum=(config.get("maximum") if config.get("maximum") is not None else None),
            )
        
        # Parse phrase_requirements if present
        phrase_requirements = None
        if "phrase_requirements" in entry:
            req_data = entry["phrase_requirements"]
            expected_types = tuple(req_data.get("expected_types", ["noun"]))
            fallback = str(req_data.get("fallback", "focused progress"))
            transform = req_data.get("transform", {})
            lowercase = bool(transform.get("lowercase", False))
            add_article = bool(transform.get("add_article", False))
            phrase_requirements = PhraseRequirements(
                expected_types=expected_types,
                fallback=fallback,
                lowercase=lowercase,
                add_article=add_article,
            )
        
        asset = PhraseAsset(
            archetype=archetype,
            intensity=intensity,
            area=area,
            clause_variants=clause_variants,
            bullet_templates=bullet_templates,
            variation_groups=variation_groups,
            phrase_requirements=phrase_requirements,
        )
        assets[(archetype, intensity, area)] = asset
    return assets


def assets() -> Mapping[tuple[str, str, str], PhraseAsset]:
    return _asset_map()


def get_asset(archetype: str, intensity: str, area: str) -> PhraseAsset:
    key = (archetype, intensity, area)
    asset_map = _asset_map()
    if key in asset_map:
        return asset_map[key]
    # Fallback to steady integration for the requested area/intensity
    steady_key = ("Steady Integration", intensity, area)
    if steady_key in asset_map:
        return asset_map[steady_key]
    # Fallback to steady integration steady intensity for area
    default_key = ("Steady Integration", "steady", area)
    if default_key in asset_map:
        return asset_map[default_key]
    # As a last resort, return the first asset matching the area
    for candidate_key, candidate in asset_map.items():
        if candidate_key[2] == area:
            return candidate
    raise KeyError(f"No phrase assets available for area='{area}'")


def select_clause(archetype: str, intensity: str, area: str, *, seed: int | None = None) -> str:
    asset = get_asset(archetype, intensity, area)
    clauses = asset.clause_cycle()
    if not clauses:
        return ""
    if seed is None:
        return clauses[0]
    context = asset.variations(seed)
    tokens = context.tokens()
    tokens.setdefault("area", area)
    clause_template = context.first("clauses", clauses[0]) if "clauses" in context else None
    if clause_template:
        return clause_template.format_map(_FormatTokens(tokens))
    engine = VariationEngine(seed)
    selection = engine.choice("clauses", clauses, pick=1)
    return selection[0] if selection else ""


class _FormatTokens(dict[str, str]):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return ""


def bullet_templates_for(area: str, mode: str, *, archetype: str | None = None, intensity: str | None = None) -> tuple[str, ...]:
    if archetype and intensity:
        asset = get_asset(archetype, intensity, area)
    else:
        asset = None
    if asset:
        templates = asset.templates_for(mode)
        if templates:
            return templates
    fallback = get_asset("Steady Integration", "steady", area)
    return fallback.templates_for(mode)


def seed_from_event(area: str, event: Mapping[str, object] | None, *, salt: str | None = None) -> int:
    base_parts: list[str] = [area]
    if salt:
        base_parts.append(salt)
    if event:
        for key in ("id", "date", "transit_body", "natal_body", "aspect"):
            value = event.get(key)
            if value:
                base_parts.append(str(value))
        score = event.get("score")
        if score is not None:
            base_parts.append(str(score))
    digest = blake2b("|".join(base_parts).encode("utf-8"), digest_size=8)
    return int.from_bytes(digest.digest(), "big")


def coverage_matrix(areas: Iterable[str] | None = None) -> set[tuple[str, str, str]]:
    target_areas = tuple(areas) if areas else AREAS
    combos = set()
    for archetype in ARCHETYPES:
        for intensity in INTENSITIES:
            for area in target_areas:
                combos.add((archetype, intensity, area))
    return combos


__all__ = [
    "PhraseAsset",
    "ARCHETYPES",
    "INTENSITIES",
    "AREAS",
    "assets",
    "get_asset",
    "select_clause",
    "bullet_templates_for",
    "seed_from_event",
    "coverage_matrix",
]
