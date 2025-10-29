#!/usr/bin/env python3
"""Check raw API response for Phase 3 evidence."""

import json
import requests

url = "http://localhost:8081/v1/forecasts/daily/forecast"
payload = {
    "chart_input": {
        "system": "western",
        "date": "1995-07-10",
        "time": "12:00:00",
        "time_known": True,
        "place": {"lat": 34.0522, "lon": -118.2437, "tz": "America/Los_Angeles"}
    },
    "options": {
        "date": "2025-10-30",
        "profile_name": "Nut",
        "use_ai": False
    }
}

print("\n" + "="*80)
print(" PHASE 3 RAW OUTPUT ANALYSIS")
print("="*80)

response = requests.post(url, json=payload, timeout=30)
data = response.json()

print("\n📊 OPENERS:")
print("-"*80)

areas = ["career", "love", "health", "finance"]
for area in areas:
    para = data.get(area, {}).get("paragraph", "")
    opener = para.split(". ")[0] if para else ""
    print(f"\n{area.upper()}:")
    print(f"  {opener}")

print("\n" + "="*80)
print("🔍 PHASE 3 LANGUAGE DETECTION:")
print("="*80)

# Phase 3 specific phrases (from storylets.json phase3_templates)
phase3_patterns = {
    "Moon": [
        "emotional",
        "attune to",
        "intuition illuminates",
        "honor.*sensitivity",
        "emotional.*rhythms"
    ],
    "Mercury": [
        "thinking clarifies",
        "communicate.*insights",
        "mental.*agility",
        "process.*information",
        "curiosity guides"
    ],
    "Venus": [
        "values harmonize",
        "appreciate.*beauty",
        "affection shapes",
        "attract.*connections",
        "relational.*grace"
    ],
    "Sun": [
        "vitality powers",
        "radiate.*confidence",
        "core.*identity",
        "express.*authenticity",
        "purpose illuminates"
    ],
    "Mars": [
        "drive activates",
        "assert.*will",
        "courage propels",
        "direct.*energy",
        "initiative shapes"
    ],
    "Jupiter": [
        "optimism expands",
        "explore.*possibilities",
        "wisdom guides",
        "cultivate.*growth",
        "philosophical.*vision"
    ],
    "Saturn": [
        "discipline structures",
        "build.*foundations",
        "responsibility anchors",
        "master.*challenges",
        "maturity guides"
    ]
}

import re

all_openers = []
for area in areas:
    para = data.get(area, {}).get("paragraph", "")
    opener = para.split(". ")[0] if para else ""
    all_openers.append((area, opener))

print("\nDetected Phase 3 patterns:")
found_any = False

for planet, patterns in phase3_patterns.items():
    for area, opener in all_openers:
        opener_lower = opener.lower()
        for pattern in patterns:
            if re.search(pattern, opener_lower):
                print(f"  ✅ {planet}-specific: '{pattern}' in {area}")
                print(f"     Full opener: {opener}")
                found_any = True

if not found_any:
    print("  ⚪ No Phase 3-specific patterns detected")
    print("     (May be using Saturn 'master.*challenges' or generic Phase 2)")

print("\n" + "="*80 + "\n")

