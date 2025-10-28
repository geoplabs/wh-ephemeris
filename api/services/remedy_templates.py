"""Shared remedy template helpers for daily guidance content."""

from __future__ import annotations

from typing import Mapping, Sequence


_PLANETARY_REMEDIES: Mapping[str, Sequence[str]] = {
    "Sun": (
        "Spend ten mindful minutes in sunlight to honor your {sign} vitality.",
        "Wear warm tones or gold accents to spotlight your confidence.",
        "Share gratitude with a guide or mentor to brighten your {theme} focus.",
    ),
    "Moon": (
        "Brew a calming tea ritual to soothe your {sign} sensitivities.",
        "Journal feelings for five minutes to clear emotional tides.",
        "Invite gentle stretches or breathwork to settle your {theme} intentions.",
    ),
    "Mercury": (
        "Organize your workspace so {sign} thoughts have a clear lane.",
        "Practice a mindful breathing count before important conversations.",
        "Review top priorities aloud to anchor today's {theme}.",
    ),
    "Venus": (
        "Add art or music that reflects your {sign} aesthetic to the day.",
        "Offer a sincere compliment to keep relationships graceful.",
        "Prepare a nourishing meal to support your {theme} balance.",
    ),
    "Mars": (
        "Channel extra energy into focused movement that respects {sign} drive.",
        "Count to five before reacting so actions stay intentional.",
        "Break big goals into steps to guide your {theme} momentum.",
    ),
    "Jupiter": (
        "Read an inspiring passage to expand your {sign} outlook.",
        "Offer a small act of generosity to keep optimism grounded.",
        "Set one bold intention that supports your {theme} growth.",
    ),
    "Saturn": (
        "Block focused work time to honor your {sign} discipline.",
        "Light a calming candle and breathe through any tension.",
        "Review a long-term plan to support your {theme} stability.",
    ),
}

_DEFAULT_REMEDIES: Sequence[str] = (
    "Ground yourself with three slow breaths whenever plans feel rushed.",
    "Keep water nearby and hydrate steadily through the day.",
    "Note one supportive action that reinforces your {theme} focus.",
)


def remedy_templates_for_planet(planet: str) -> Sequence[str]:
    """Return remedy templates for the provided planet name."""

    normalized = (planet or "").strip().title()
    return _PLANETARY_REMEDIES.get(normalized, _DEFAULT_REMEDIES)

