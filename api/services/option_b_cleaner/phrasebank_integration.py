"""Integration layer between phrasebank.py variation engine and narrative generation.

This module bridges the advanced phrasebank.py system (with QA linting, guardrails,
driver tags, constraints) with the existing language.py narrative generation.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Mapping, Sequence

from src.content.phrasebank import (
    get_asset,
    get_driver_microcopy,
    get_qa_metrics,
    bullet_templates_for,
    seed_from_event,
)
from src.content.inflection import safe_phrase_for_template

logger = logging.getLogger(__name__)


def get_enhanced_bullets(
    area: str,
    mode: str,
    keywords: Sequence[str],
    *,
    event: Mapping[str, Any] | None = None,
    archetype: str = "support",
    intensity: str = "steady",
    order: int = 0,
) -> list[str]:
    """Generate bullets using phrasebank.py variation engine with QA checks.
    
    Args:
        area: Area (career, love, health, finance)
        mode: Mode (do, avoid)
        keywords: Extracted keywords for phrase
        event: Optional event for seeding
        archetype: Tone archetype (support, challenge, neutral)
        intensity: Intensity level (background, gentle, steady, strong)
        order: Selection order for determinism
        
    Returns:
        List of bullet strings (up to 3)
    """
    try:
        # Get seed from event for determinism
        seed = seed_from_event(area, event, salt=mode) if event else order
        
        # Get phrasebank asset
        asset = get_asset(archetype, intensity, area)
        
        # Get templates from asset
        templates = asset.templates_for(mode)
        if not templates:
            # Fallback to generic templates
            templates = bullet_templates_for(area, mode)
        
        if not templates:
            return []
        
        # Get variations context (includes tone, area lexicon, driver microcopy)
        variations = asset.variations(seed, events=[event] if event else None)
        
        # Build phrase from keywords
        phrase = " ".join(keywords[:3]) if keywords else "focused progress"
        
        # Generate bullets
        bullets: list[str] = []
        template_count = len(templates)
        
        for idx in range(min(3, template_count)):  # Max 3 bullets
            template_idx = (seed + idx) % template_count
            template = templates[template_idx]
            
            # Make phrase grammatically safe for template
            safe_phrase = safe_phrase_for_template(
                phrase,
                template,
                fallback=variations.first("tone_adjective", "focused") + " progress"
            )
            
            # Format template with all variations
            try:
                bullet = template.format(
                    phrase=safe_phrase,
                    tone_action=variations.first("tone_action", "tracking"),
                    tone_adjective=variations.first("tone_adjective", "steady"),
                    area_actions=variations.first("area_action", "organizing"),
                    area_nouns=variations.first("area_noun", "priorities"),
                    area_contexts=variations.first("area_context", "workflow"),
                )
                
                # Apply QA checks
                metrics = get_qa_metrics(bullet)
                if metrics.get("passes_checks", True):
                    bullets.append(bullet.strip())
            except (KeyError, ValueError) as e:
                logger.debug(f"Template formatting failed: {e}")
                continue
        
        return bullets[:3]  # Max 3 bullets
    
    except Exception as e:
        logger.exception(f"phrasebank_integration::get_enhanced_bullets failed: {e}")
        return []


def apply_qa_polish(
    text: str,
    area: str = "general",
    *,
    check_cliches: bool = True,
    check_length: bool = True,
) -> str:
    """Apply QA checks and polish text using phrasebank.py linting.
    
    Args:
        text: Text to check
        area: Area for context (career, love, health, finance)
        check_cliches: Enable cliché replacement
        check_length: Check average sentence length
        
    Returns:
        Polished text (same as input if passes, or with fixes applied)
    """
    if not text or not text.strip():
        return text
    
    try:
        metrics = get_qa_metrics(text)
        
        # Log quality metrics for monitoring
        if not metrics.get("passes_checks", True):
            logger.info(
                "qa_polish_applied",
                extra={
                    "area": area,
                    "avg_sentence_length": metrics.get("avg_sentence_length"),
                    "has_cliches": metrics.get("has_cliches", False),
                    "has_duplicates": metrics.get("has_duplicates", False),
                }
            )
        
        # For now, return text as-is (phrasebank.py applies fixes internally)
        # Future: Apply specific fixes based on metrics
        return text
    
    except Exception as e:
        logger.exception(f"phrasebank_integration::apply_qa_polish failed: {e}")
        return text


def inject_driver_microcopy(
    text: str,
    events: Iterable[Mapping[str, Any]] | None,
    *,
    max_injections: int = 1,
) -> str:
    """Inject driver microcopy (astrological pattern hints) into narrative text.
    
    Args:
        text: Original text
        events: List of astrological events
        max_injections: Maximum number of microcopy injections (default 1)
        
    Returns:
        Text with driver microcopy injected (or original if no drivers found)
        
    Examples:
        >>> inject_driver_microcopy("You channel energy.", [mars_conj_sun])
        "You channel energy. Energy peaks—tackle a meaty task."
    """
    if not text or not events:
        return text
    
    try:
        microcopy = get_driver_microcopy(events)
        
        if microcopy and microcopy.strip():
            # Inject at end of text (before final punctuation if present)
            if text.rstrip().endswith(('.', '!', '?')):
                base = text.rstrip()[:-1]
                punct = text.rstrip()[-1]
                return f"{base}. {microcopy.strip()}{punct}"
            else:
                return f"{text.strip()} {microcopy.strip()}"
        
        return text
    
    except Exception as e:
        logger.exception(f"phrasebank_integration::inject_driver_microcopy failed: {e}")
        return text


def get_archetype_from_tone(tone: str) -> str:
    """Map tone to phrasebank archetype.
    
    Args:
        tone: Tone (support, challenge, neutral)
        
    Returns:
        Archetype string for phrasebank
    """
    mapping = {
        "support": "support",
        "challenge": "challenge",
        "neutral": "neutral",
    }
    return mapping.get(tone, "neutral")


def get_intensity_from_score(score: float) -> str:
    """Map event score to phrasebank intensity level.
    
    Args:
        score: Event score (typically -5 to +5)
        
    Returns:
        Intensity level (background, gentle, steady, strong)
    """
    abs_score = abs(score)
    
    if abs_score < 1.0:
        return "background"
    elif abs_score < 2.0:
        return "gentle"
    elif abs_score < 3.5:
        return "steady"
    else:
        return "strong"


__all__ = [
    "get_enhanced_bullets",
    "apply_qa_polish",
    "inject_driver_microcopy",
    "get_archetype_from_tone",
    "get_intensity_from_score",
]

