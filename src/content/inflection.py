"""Grammatical inflection helpers for phrase transformations.

Converts phrases into grammatically correct forms (gerunds, nouns, adjectives, etc.)
to ensure templates like "Plan {phrase} moves" work correctly regardless of phrase type.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Mapping

# Common verb → gerund mappings
VERB_TO_GERUND: Mapping[str, str] = {
    "focus": "focusing",
    "plan": "planning",
    "prioritize": "prioritizing",
    "review": "reviewing",
    "build": "building",
    "create": "creating",
    "develop": "developing",
    "explore": "exploring",
    "maintain": "maintaining",
    "organize": "organizing",
    "strengthen": "strengthening",
    "clarify": "clarifying",
    "anchor": "anchoring",
    "align": "aligning",
    "stabilize": "stabilizing",
    "balance": "balancing",
    "nurture": "nurturing",
    "cultivate": "cultivating",
    "honor": "honoring",
    "trust": "trusting",
    "release": "releasing",
    "transform": "transforming",
    "integrate": "integrating",
    "refine": "refining",
    "expand": "expanding",
    "deepen": "deepening",
}

# Soft H words (take "an")
SOFT_H_WORDS = {"honor", "honest", "hour", "heir"}

# Hard vowel starts (take "a" not "an")
HARD_VOWEL_STARTS = {"uni", "eu", "one", "use"}


def _starts_with_vowel_sound(word: str) -> bool:
    """Check if word starts with a vowel sound (for a/an determination)."""
    if not word:
        return False
    
    lower = word.lower()
    
    # Check soft H words
    if any(lower.startswith(h) for h in SOFT_H_WORDS):
        return True
    
    # Check hard vowel starts (sound like consonant)
    if any(lower.startswith(prefix) for prefix in HARD_VOWEL_STARTS):
        return False
    
    # Standard vowel check
    return word[0].lower() in "aeiou"


def add_article(phrase: str, force_lowercase: bool = False) -> str:
    """Add appropriate indefinite article (a/an) to phrase.
    
    Args:
        phrase: The phrase to add article to
        force_lowercase: If True, return lowercase article
        
    Returns:
        Phrase with article prepended
        
    Examples:
        >>> add_article("radiant approach")
        "a radiant approach"
        >>> add_article("emotional rhythm")
        "an emotional rhythm"
        >>> add_article("honest conversation")
        "an honest conversation"
    """
    if not phrase:
        return phrase
    
    words = phrase.strip().split()
    if not words:
        return phrase
    
    first_word = words[0]
    article = "an" if _starts_with_vowel_sound(first_word) else "a"
    
    if not force_lowercase and phrase[0].isupper():
        article = article.capitalize()
    
    return f"{article} {phrase}"


def to_gerund(phrase: str) -> str:
    """Convert phrase to gerund form (verb-ing).
    
    Args:
        phrase: The phrase to convert (e.g., "focus", "emotional growth")
        
    Returns:
        Gerund form of phrase
        
    Examples:
        >>> to_gerund("focus")
        "focusing"
        >>> to_gerund("emotional growth")
        "emotional growth"  # Already a noun phrase, no change
        >>> to_gerund("plan strategic moves")
        "planning strategic moves"
    """
    if not phrase:
        return phrase
    
    words = phrase.strip().split()
    if not words:
        return phrase
    
    first_word = words[0].lower()
    
    # Check explicit mappings first
    if first_word in VERB_TO_GERUND:
        gerund = VERB_TO_GERUND[first_word]
        if phrase[0].isupper():
            gerund = gerund.capitalize()
        return f"{gerund} {' '.join(words[1:])}" if len(words) > 1 else gerund
    
    # If already ends in -ing, assume it's already a gerund
    if first_word.endswith("ing"):
        return phrase
    
    # If it looks like an adjective + noun (has multiple words), leave as-is
    if len(words) >= 2:
        return phrase
    
    # Simple gerund formation rules
    word = words[0]
    preserve_case = word[0].isupper()
    word_lower = word.lower()
    
    # Drop final 'e' and add 'ing' (make → making)
    if word_lower.endswith("e") and not word_lower.endswith("ee"):
        gerund = word_lower[:-1] + "ing"
    # Double final consonant for CVC pattern (plan → planning)
    elif len(word_lower) >= 3 and word_lower[-1] not in "aeiouy" and word_lower[-2] in "aeiou" and word_lower[-3] not in "aeiou":
        gerund = word_lower + word_lower[-1] + "ing"
    else:
        gerund = word_lower + "ing"
    
    if preserve_case:
        gerund = gerund.capitalize()
    
    return gerund


def to_noun_phrase(phrase: str) -> str:
    """Ensure phrase is in noun form.
    
    Args:
        phrase: The phrase to convert
        
    Returns:
        Noun phrase form
        
    Examples:
        >>> to_noun_phrase("radiant energy")
        "radiant energy"
        >>> to_noun_phrase("focus")
        "focus"
    """
    # Most phrases are already noun phrases or can be used as nouns
    # This function is mostly for consistency and future expansion
    return phrase.strip()


def to_adjective_noun(phrase: str) -> str:
    """Ensure phrase is in adjective+noun form.
    
    Args:
        phrase: The phrase to convert
        
    Returns:
        Adjective+noun phrase
        
    Examples:
        >>> to_adjective_noun("radiant energy")
        "radiant energy"
        >>> to_adjective_noun("focus")
        "clear focus"  # Add default adjective if single noun
    """
    words = phrase.strip().split()
    
    # If already 2+ words, assume adjective+noun
    if len(words) >= 2:
        return phrase
    
    # Single word - could add default adjective, but safer to leave as-is
    # The caller should handle the fallback
    return phrase


def phrase_type_from_text(phrase: str) -> str:
    """Determine the grammatical type of a phrase.
    
    Args:
        phrase: The phrase to analyze
        
    Returns:
        One of: "gerund", "adjective_noun", "noun", "unknown"
        
    Examples:
        >>> phrase_type_from_text("focusing")
        "gerund"
        >>> phrase_type_from_text("radiant energy")
        "adjective_noun"
        >>> phrase_type_from_text("focus")
        "noun"
    """
    if not phrase:
        return "unknown"
    
    words = phrase.strip().split()
    if not words:
        return "unknown"
    
    first_word = words[0].lower()
    
    # Check if gerund (-ing form)
    if first_word.endswith("ing"):
        return "gerund"
    
    # Check if adjective+noun (2+ words)
    if len(words) >= 2:
        return "adjective_noun"
    
    # Single word - assume noun
    return "noun"


@lru_cache(maxsize=256)
def transform_phrase(
    phrase: str,
    target_type: str,
    *,
    lowercase: bool = False,
    add_article_prefix: bool = False,
    fallback: str = "focused progress"
) -> str:
    """Transform phrase to target grammatical type with safety checks.
    
    Args:
        phrase: The phrase to transform
        target_type: Target type ("gerund", "noun", "adjective_noun")
        lowercase: Force lowercase output
        add_article_prefix: Add a/an prefix
        fallback: Fallback phrase if transformation fails
        
    Returns:
        Transformed phrase, or fallback if transformation fails
        
    Examples:
        >>> transform_phrase("focus", "gerund")
        "focusing"
        >>> transform_phrase("radiant energy", "noun")
        "radiant energy"
        >>> transform_phrase("focus", "gerund", lowercase=True)
        "focusing"
    """
    if not phrase or not phrase.strip():
        return fallback
    
    phrase = phrase.strip()
    
    # Determine source type
    source_type = phrase_type_from_text(phrase)
    
    # Apply transformation based on target type
    try:
        if target_type == "gerund":
            result = to_gerund(phrase)
        elif target_type == "noun":
            result = to_noun_phrase(phrase)
        elif target_type == "adjective_noun":
            result = to_adjective_noun(phrase)
        else:
            result = phrase
        
        # Apply modifiers
        if lowercase:
            result = result.lower()
        
        if add_article_prefix:
            result = add_article(result, force_lowercase=lowercase)
        
        # Validate result
        if not result or not result.strip() or len(result.split()) > 6:
            return fallback
        
        return result
        
    except Exception:
        return fallback


def safe_phrase_for_template(
    phrase: str,
    template: str,
    *,
    fallback: str = "focused progress"
) -> str:
    """Intelligently transform phrase based on template context.
    
    Analyzes the template to determine the appropriate phrase type,
    then transforms the phrase accordingly.
    
    Args:
        phrase: The phrase to transform
        template: The template containing the phrase placeholder
        fallback: Fallback phrase if transformation fails
        
    Returns:
        Grammatically safe phrase for the template
        
    Examples:
        >>> safe_phrase_for_template("focus", "Plan {phrase} moves...")
        "focus"  # noun works here
        >>> safe_phrase_for_template("emotional growth", "Avoid {phrase} today")
        "emotional growth"  # already safe
    """
    if not phrase or not template:
        return fallback
    
    template_lower = template.lower()
    
    # Check template context for hints about expected type
    # Patterns that suggest gerund: "Focus on {phrase}", "Keep {phrase}"
    gerund_triggers = [
        r"focus\s+on\s+\{phrase\}",
        r"keep\s+\{phrase\}",
        r"practice\s+\{phrase\}",
        r"avoid\s+\{phrase\}\s+(if|when|until)",
        r"skip\s+\{phrase\}\s+(if|when|until)",
        r"hold\s+back\s+from\s+\{phrase\}",
    ]
    
    for pattern in gerund_triggers:
        if re.search(pattern, template_lower):
            return transform_phrase(phrase, "gerund", fallback=fallback)
    
    # Patterns that suggest adjective+noun: "Set {phrase} priorities", "Plan {phrase} moves"
    adj_noun_triggers = [
        r"set\s+\{phrase\}\s+(priorities|moves|boundaries|goals)",
        r"plan\s+\{phrase\}\s+(moves|steps|actions)",
        r"choose\s+\{phrase\}\s+(priorities|moves|actions)",
    ]
    
    for pattern in adj_noun_triggers:
        if re.search(pattern, template_lower):
            # For these contexts, noun form works better than trying to force adj+noun
            return transform_phrase(phrase, "noun", fallback=fallback)
    
    # Default: use as-is (noun form)
    return transform_phrase(phrase, "noun", fallback=fallback)

