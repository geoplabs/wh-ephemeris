"""Placeholder SVG builder for Panchang day strip assets."""

from __future__ import annotations

from typing import Optional


def build_day_strip_svg() -> Optional[str]:
    """Return ``None`` for now.

    The day strip visualisation is optional for the development build. The
    helper exists so the orchestrator can call into it without guarding on
    optional imports.
    """

    return None

