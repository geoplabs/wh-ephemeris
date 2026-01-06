"""
Compatibility Constants - Shared Data

This module contains shared constants used by both compatibility_service and compatibility_helpers
to avoid circular imports.
"""

from typing import Dict, Tuple

# Element compatibility matrix
ELEMENT_COMPATIBILITY: Dict[Tuple[str, str], Tuple[str, str]] = {
    ("Fire", "Fire"): ("high", "Both share enthusiasm, passion, and dynamic energy"),
    ("Fire", "Air"): ("high", "Fire inspires Air; Air fuels Fire with ideas and communication"),
    ("Fire", "Earth"): ("medium", "Fire can energize Earth, but may overwhelm; Earth grounds Fire"),
    ("Fire", "Water"): ("low", "Fire and Water can clash; Water may dampen Fire's enthusiasm"),
    ("Air", "Air"): ("high", "Intellectual connection, great communication, shared ideas"),
    ("Air", "Earth"): ("medium", "Air brings ideas; Earth provides structure, but may feel too grounded"),
    ("Air", "Water"): ("medium", "Air can feel detached; Water seeks emotional depth"),
    ("Earth", "Earth"): ("high", "Both value stability, practicality, and tangible results"),
    ("Earth", "Water"): ("high", "Earth provides security; Water brings emotional nurturing"),
    ("Water", "Water"): ("high", "Deep emotional understanding and intuitive connection"),
}

# Modality compatibility matrix
MODALITY_COMPATIBILITY: Dict[Tuple[str, str], Tuple[str, str]] = {
    ("Cardinal", "Cardinal"): ("medium", "Both are initiators; may compete for leadership"),
    ("Cardinal", "Fixed"): ("medium", "Cardinal starts; Fixed sustains, but can be stubborn"),
    ("Cardinal", "Mutable"): ("high", "Cardinal leads; Mutable adapts, creating good balance"),
    ("Fixed", "Fixed"): ("low", "Both are stubborn; resistance to change can cause friction"),
    ("Fixed", "Mutable"): ("high", "Fixed provides stability; Mutable brings flexibility"),
    ("Mutable", "Mutable"): ("medium", "Both adaptable but may lack direction and stability"),
}

# Zodiac sign data
SIGN_DATA: Dict[str, Dict[str, str]] = {
    "Aries": {"element": "Fire", "modality": "Cardinal", "ruler": "Mars", "traditional_ruler": "Mars"},
    "Taurus": {"element": "Earth", "modality": "Fixed", "ruler": "Venus", "traditional_ruler": "Venus"},
    "Gemini": {"element": "Air", "modality": "Mutable", "ruler": "Mercury", "traditional_ruler": "Mercury"},
    "Cancer": {"element": "Water", "modality": "Cardinal", "ruler": "Moon", "traditional_ruler": "Moon"},
    "Leo": {"element": "Fire", "modality": "Fixed", "ruler": "Sun", "traditional_ruler": "Sun"},
    "Virgo": {"element": "Earth", "modality": "Mutable", "ruler": "Mercury", "traditional_ruler": "Mercury"},
    "Libra": {"element": "Air", "modality": "Cardinal", "ruler": "Venus", "traditional_ruler": "Venus"},
    "Scorpio": {"element": "Water", "modality": "Fixed", "ruler": "Mars", "traditional_ruler": "Mars"},
    "Sagittarius": {"element": "Fire", "modality": "Mutable", "ruler": "Jupiter", "traditional_ruler": "Jupiter"},
    "Capricorn": {"element": "Earth", "modality": "Cardinal", "ruler": "Saturn", "traditional_ruler": "Saturn"},
    "Aquarius": {"element": "Air", "modality": "Fixed", "ruler": "Saturn", "traditional_ruler": "Saturn"},
    "Pisces": {"element": "Water", "modality": "Mutable", "ruler": "Jupiter", "traditional_ruler": "Jupiter"},
}

