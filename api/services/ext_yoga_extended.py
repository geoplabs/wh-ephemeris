"""Mapping helpers for Anandadi and Tamil yogas."""

from __future__ import annotations


ANANDADI_YOGAS = [
    "Dhata",
    "Mitra",
    "Pitri",
    "Vasu",
    "Varuna",
    "Ajita",
    "Siddhi",
    "Vyatipata",
    "Harshana",
    "Vajra",
    "Siddha",
    "Vyatipata",
    "Variyan",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
    "Dhata",
    "Mitra",
    "Pitri",
    "Vasu",
    "Varuna",
]


TAMIL_YOGAS = [
    "Amrita",
    "Siddha",
    "Subha",
    "Amrita",
    "Roga",
    "Mrityu",
    "Kaala",
    "Siddha",
    "Subha",
    "Amrita",
    "Roga",
    "Mrityu",
    "Kaala",
    "Siddha",
    "Subha",
    "Amrita",
    "Roga",
    "Mrityu",
    "Kaala",
    "Siddha",
    "Subha",
    "Amrita",
    "Roga",
    "Mrityu",
    "Kaala",
    "Siddha",
    "Subha",
]


def anandadi_from_yoga(yoga_number: int) -> str:
    index = max(0, min(len(ANANDADI_YOGAS) - 1, (yoga_number - 1) % 27))
    return ANANDADI_YOGAS[index]


def tamil_yoga_from_yoga(yoga_number: int) -> str:
    index = max(0, min(len(TAMIL_YOGAS) - 1, (yoga_number - 1) % 27))
    return TAMIL_YOGAS[index]


def build_yoga_extended(yoga_number: int) -> dict:
    return {
        "anandadi": anandadi_from_yoga(yoga_number),
        "tamil": tamil_yoga_from_yoga(yoga_number),
        "notes": [],
    }
