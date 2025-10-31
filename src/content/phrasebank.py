from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from hashlib import blake2b
from pathlib import Path
from typing import Iterable, Mapping

from .variation import (
    VariationContext,
    VariationEngine,
    VariationGroup,
    VariationItem,
    VariationResult,
)


DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "phrasebank"
PHRASES_PATH = DATA_ROOT / "phrases.json"


_TONE_LIBRARY: dict[str, dict[str, tuple[str, ...]]] = {}
_AREA_LEXICON: dict[str, dict[str, tuple[str, ...]]] = {}
_CONSTRAINTS: dict[str, object] = {}
_RECENT_SELECTIONS: list[str] = []  # Track recent clause selections for deduplication
_ACTION_OVERRIDES: dict[str, str] = {
    "allow": "allowing space for",
    "lean toward": "leaning toward",
    "keep": "keeping to",
    "tend": "tending to",
    "commit": "committing to",
    "drive": "driving toward",
    "push": "pushing toward",
    "ship": "shipping",
}

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


def _normalize_word(value: object) -> str:
    text = str(value or "").strip()
    return text


def _initialize_tone(config: Mapping[str, object] | None) -> None:
    global _TONE_LIBRARY
    _TONE_LIBRARY = {}
    if not config:
        return
    adjectives = config.get("adjectives") if isinstance(config, Mapping) else None
    verbs = config.get("verbs") if isinstance(config, Mapping) else None
    adjective_map = adjectives if isinstance(adjectives, Mapping) else {}
    verb_map = verbs if isinstance(verbs, Mapping) else {}
    intensities = set(adjective_map) | set(verb_map)
    tone: dict[str, dict[str, tuple[str, ...]]] = {}
    for intensity in intensities:
        adj_values = tuple(
            _normalize_word(word)
            for word in (adjective_map.get(intensity) or ())
            if _normalize_word(word)
        )
        verb_values = tuple(
            _normalize_word(word)
            for word in (verb_map.get(intensity) or ())
            if _normalize_word(word)
        )
        tone[str(intensity)] = {
            "adjectives": adj_values,
            "verbs": verb_values,
        }
    _TONE_LIBRARY = tone


def _initialize_area_lexicon(config: Mapping[str, object] | None) -> None:
    global _AREA_LEXICON
    _AREA_LEXICON = {}
    if not config:
        return
    lexicon: dict[str, dict[str, tuple[str, ...]]] = {}
    for area, area_data in config.items():
        if not isinstance(area_data, Mapping):
            continue
        area_dict: dict[str, tuple[str, ...]] = {}
        for category, items in area_data.items():
            if isinstance(items, (list, tuple)):
                area_dict[str(category)] = tuple(
                    _normalize_word(item) for item in items if _normalize_word(item)
                )
        lexicon[str(area)] = area_dict
    _AREA_LEXICON = lexicon


def _initialize_constraints(config: Mapping[str, object] | None) -> None:
    global _CONSTRAINTS
    _CONSTRAINTS = {}
    if not config:
        return
    _CONSTRAINTS = dict(config)


def _gerund_word(word: str) -> str:
    lower = word.lower()
    if not lower:
        return ""
    if lower in {"be", "see"}:
        return f"{lower}ing"
    if lower.endswith("ie"):
        return f"{lower[:-2]}ying"
    if lower in {"commit", "ship"}:
        return f"{lower}{lower[-1]}ing"
    if lower.endswith("e") and not lower.endswith("ee"):
        return f"{lower[:-1]}ing"
    vowels = "aeiou"
    if (
        len(lower) >= 3
        and lower[-1] not in "aeiouwxy"
        and lower[-2] in vowels
        and lower[-3] not in vowels
    ):
        return f"{lower}{lower[-1]}ing"
    return f"{lower}ing"


def _tone_action(verb: str) -> str:
    lower = verb.strip().lower()
    if not lower:
        return ""
    override = _ACTION_OVERRIDES.get(lower)
    if override:
        return override
    pieces = lower.split()
    head, *tail = pieces
    gerund = _gerund_word(head)
    if not gerund:
        return ""
    return " ".join([gerund, *tail]).strip()


def _tone_defaults(intensity: str) -> dict[str, str]:
    palette = _tone_palette(intensity)
    adjectives = palette.get("adjectives", ())
    verbs = palette.get("verbs", ())
    defaults: dict[str, str] = {}
    if adjectives:
        defaults["tone_adjective"] = adjectives[0]
    if verbs:
        verb = verbs[0]
        defaults["tone_verb"] = verb
        action = _tone_action(verb)
        if action:
            defaults["tone_action"] = action
        defaults["tone_directive"] = verb.capitalize()
    return defaults


def _tone_variations(engine: VariationEngine, intensity: str) -> dict[str, VariationResult]:
    palette = _tone_palette(intensity)
    if not palette:
        return {}
    results: dict[str, VariationResult] = {}
    adjectives = palette.get("adjectives", ())
    if adjectives:
        selection = engine.choice(f"tone_adjective:{intensity}", adjectives, pick=1)
        if selection:
            results["tone_adjective"] = VariationResult(
                name="tone_adjective", selections=selection, mode="choice"
            )
    verbs = palette.get("verbs", ())
    if verbs:
        selection = engine.choice(f"tone_verb:{intensity}", verbs, pick=1)
        if selection:
            verb = selection[0]
            results["tone_verb"] = VariationResult(
                name="tone_verb", selections=(verb,), mode="choice"
            )
            action = _tone_action(verb)
            if action:
                results["tone_action"] = VariationResult(
                    name="tone_action", selections=(action,), mode="choice"
                )
            results["tone_directive"] = VariationResult(
                name="tone_directive",
                selections=(verb.capitalize(),),
                mode="choice",
            )
    return results


def _area_lexicon_variations(engine: VariationEngine, area: str) -> dict[str, VariationResult]:
    """Generate variation results from area-specific lexicon."""
    lexicon = _area_lexicon_for(area)
    if not lexicon:
        return {}
    results: dict[str, VariationResult] = {}
    
    # Add direct access to each category (actions, nouns, contexts)
    for category, items in lexicon.items():
        if not items:
            continue
        selection = engine.choice(f"area_{category}:{area}", items, pick=1)
        if selection:
            results[f"area_{category}"] = VariationResult(
                name=f"area_{category}",
                selections=selection,
                mode="choice"
            )
            # Also add with area prefix for explicit access like {career.actions}
            results[f"{area}.{category}"] = VariationResult(
                name=f"{area}.{category}",
                selections=selection,
                mode="choice"
            )
    
    return results


def _tone_palette(intensity: str) -> dict[str, tuple[str, ...]]:
    palette = _TONE_LIBRARY.get(intensity)
    if palette:
        return palette
    if intensity == "surge":
        return _TONE_LIBRARY.get("strong", {})
    return {}


def _area_lexicon_for(area: str) -> dict[str, tuple[str, ...]]:
    """Get lexicon entries for a specific area."""
    return _AREA_LEXICON.get(area, _AREA_LEXICON.get("general", {}))


def _contains_banned_content(text: str) -> bool:
    """Check if text contains banned bigrams or phrases."""
    if not _CONSTRAINTS:
        return False
    
    # Check banned bigrams (case-insensitive)
    banned_bigrams = _CONSTRAINTS.get("banned_bigrams", [])
    for bigram in banned_bigrams:
        if isinstance(bigram, str) and bigram.lower() in text.lower():
            return True
    
    # Check banned phrases (case-insensitive)
    banned_phrases = _CONSTRAINTS.get("banned_phrases", [])
    for phrase in banned_phrases:
        if isinstance(phrase, str) and phrase.lower() in text.lower():
            return True
    
    return False


def _is_recent_duplicate(text: str) -> bool:
    """Check if text was recently selected (within dedupe_window)."""
    if not _CONSTRAINTS:
        return False
    
    dedupe_window = _CONSTRAINTS.get("dedupe_window", 0)
    if not isinstance(dedupe_window, int) or dedupe_window <= 0:
        return False
    
    # Check last N selections
    recent = _RECENT_SELECTIONS[-dedupe_window:] if len(_RECENT_SELECTIONS) >= dedupe_window else _RECENT_SELECTIONS
    return text.strip().lower() in [s.strip().lower() for s in recent]


def _validate_sentence(text: str) -> bool:
    """Validate sentence against constraints."""
    if not text or not text.strip():
        return False
    
    if not _CONSTRAINTS:
        return True
    
    # Check max word count
    max_word_count = _CONSTRAINTS.get("max_word_count")
    if isinstance(max_word_count, int) and max_word_count > 0:
        word_count = len(text.split())
        if word_count > max_word_count:
            return False
    
    # Check max sentence length (in words, not characters)
    max_sentence_length = _CONSTRAINTS.get("max_sentence_length")
    if isinstance(max_sentence_length, int) and max_sentence_length > 0:
        word_count = len(text.split())
        if word_count > max_sentence_length:
            return False
    
    # Check min sentence length
    min_sentence_length = _CONSTRAINTS.get("min_sentence_length", 3)
    if isinstance(min_sentence_length, int) and min_sentence_length > 0:
        word_count = len(text.split())
        if word_count < min_sentence_length:
            return False
    
    # Check banned content
    if _contains_banned_content(text):
        return False
    
    # Check for recent duplicates
    if _is_recent_duplicate(text):
        return False
    
    return True


def _apply_constraints(text: str) -> str:
    """Apply formatting constraints to text."""
    if not text or not _CONSTRAINTS:
        return text
    
    result = text.strip()
    
    # Capitalize first letter
    capitalize_first = _CONSTRAINTS.get("capitalize_first", True)
    if capitalize_first and result:
        result = result[0].upper() + result[1:] if len(result) > 1 else result.upper()
    
    # End with period
    end_with_period = _CONSTRAINTS.get("end_with_period", True)
    if end_with_period and result and not result.endswith((".", "!", "?")):
        result = result + "."
    
    return result


def _record_selection(text: str) -> None:
    """Record a selection for deduplication tracking."""
    global _RECENT_SELECTIONS
    if not text:
        return
    
    dedupe_window = _CONSTRAINTS.get("dedupe_window", 0)
    if not isinstance(dedupe_window, int) or dedupe_window <= 0:
        return
    
    _RECENT_SELECTIONS.append(text.strip())
    
    # Keep only the last (dedupe_window * 2) items to avoid unbounded growth
    max_history = max(dedupe_window * 2, 10)
    if len(_RECENT_SELECTIONS) > max_history:
        _RECENT_SELECTIONS = _RECENT_SELECTIONS[-max_history:]


@dataclass(frozen=True)
class PhraseRequirements:
    """Grammatical requirements for phrase placeholders in templates."""
    expected_types: tuple[str, ...]
    fallback: str
    lowercase: bool
    add_article: bool


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
        base_context = engine.evaluate(self.variation_groups)
        results = {name: base_context[name] for name in base_context}
        for key, result in _tone_variations(engine, self.intensity).items():
            results.setdefault(key, result)
        for key, result in _area_lexicon_variations(engine, self.area).items():
            results.setdefault(key, result)
        return VariationContext(results)


def _load_raw() -> Mapping[str, object]:
    with PHRASES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _asset_map() -> Mapping[tuple[str, str, str], PhraseAsset]:
    payload = _load_raw()
    _initialize_tone(payload.get("tone"))
    _initialize_area_lexicon(payload.get("area_lexicon"))
    _initialize_constraints(payload.get("constraints"))
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
            raw_items = config.get("items") or []
            parsed_items: list[VariationItem] = []
            for item in raw_items:
                if isinstance(item, Mapping):
                    text = _normalize_word(item.get("text"))
                    if not text:
                        continue
                    weight_value = item.get("weight", 1)
                    try:
                        weight = float(weight_value)
                    except (TypeError, ValueError):
                        weight = 1.0
                    tag = item.get("tag")
                    tag_str = str(tag) if tag else None
                    parsed_items.append(VariationItem(text=text, weight=weight, tag=tag_str))
                else:
                    text = _normalize_word(item)
                    if not text:
                        continue
                    parsed_items.append(VariationItem(text=text))
            
            # Extract weights from parsed items
            weights = tuple(item.weight for item in parsed_items) if parsed_items else None
            
            disallow_same_tag_twice = bool(config.get("disallow_same_tag_twice", False))
            
            variation_groups[str(name)] = VariationGroup(
                name=str(name),
                mode=str(config.get("mode", "choice")),
                items=tuple(parsed_items),
                pick=(config.get("pick") if config.get("pick") is not None else None),
                minimum=(config.get("minimum") if config.get("minimum") is not None else None),
                maximum=(config.get("maximum") if config.get("maximum") is not None else None),
                weights=weights,
                disallow_same_tag_twice=disallow_same_tag_twice,
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
        tokens = _tone_defaults(asset.intensity)
        tokens.setdefault("area", area)
        result = clauses[0].format_map(_FormatTokens(tokens))
        result = _apply_constraints(result)
        _record_selection(result)
        return result
    
    context = asset.variations(seed)
    tokens = context.tokens()
    tokens.setdefault("area", area)
    for key, value in _tone_defaults(asset.intensity).items():
        tokens.setdefault(key, value)
    
    # Try to get clause from variation context
    clause_template = context.first("clauses", clauses[0]) if "clauses" in context else None
    if clause_template:
        result = clause_template.format_map(_FormatTokens(tokens))
        # Validate against constraints
        if _validate_sentence(result):
            result = _apply_constraints(result)
            _record_selection(result)
            return result
    
    # Fallback: try clauses in order until one passes validation
    engine = VariationEngine(seed)
    for attempt in range(len(clauses)):
        selection = engine.choice(f"clauses_attempt_{attempt}", clauses, pick=1)
        if not selection:
            continue
        result = selection[0].format_map(_FormatTokens(tokens))
        if _validate_sentence(result):
            result = _apply_constraints(result)
            _record_selection(result)
            return result
    
    # Last resort: use first clause with constraints applied
    result = clauses[0].format_map(_FormatTokens(tokens))
    result = _apply_constraints(result)
    _record_selection(result)
    return result


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
    "PhraseRequirements",
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
