#!/usr/bin/env python3
"""Detailed Phase 3 test showing transit-planet matching."""

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
print(" PHASE 3 DETAILED ANALYSIS")
print("="*80)

response = requests.post(url, json=payload, timeout=30)
data = response.json()

# Extract tech notes to see which transits are being used
tech_notes = data.get("tech_notes", {})
career_event = tech_notes.get("area_events", {}).get("career", {}).get("primary", {})
love_event = tech_notes.get("area_events", {}).get("love", {}).get("primary", {})
health_event = tech_notes.get("area_events", {}).get("health", {}).get("primary", {})
finance_event = tech_notes.get("area_events", {}).get("finance", {}).get("primary", {})

# Extract openers
career_para = data.get("career", {}).get("paragraph", "")
love_para = data.get("love", {}).get("paragraph", "")
health_para = data.get("health", {}).get("paragraph", "")
finance_para = data.get("finance", {}).get("paragraph", "")

def show_area(name, event, paragraph):
    transit_body = event.get("transit_body", "Unknown")
    opener = paragraph.split(". ")[0] if paragraph else ""
    
    print(f"\n{name.upper()}:")
    print(f"  Transit planet: {transit_body}")
    print(f"  Opener: {opener}")
    
    # Check for planet-specific language
    planet_keywords = {
        "Sun": ["vitality", "radiate", "identity", "express", "purpose"],
        "Moon": ["emotional", "attune", "intuition", "sensitivity", "feelings"],
        "Mercury": ["thinking", "communicate", "mental", "process", "curiosity"],
        "Venus": ["values", "appreciate", "affection", "attract", "grace"],
        "Mars": ["drive", "assert", "courage", "energy", "initiative"],
        "Jupiter": ["optimism", "explore", "wisdom", "growth", "vision"],
        "Saturn": ["discipline", "foundations", "responsibility", "master", "maturity"]
    }
    
    opener_lower = opener.lower()
    matches = []
    if transit_body in planet_keywords:
        for keyword in planet_keywords[transit_body]:
            if keyword in opener_lower:
                matches.append(keyword)
    
    if matches:
        print(f"  ✅ Phase 3 match: {', '.join(matches)} ({transit_body}-specific)")
    else:
        print(f"  ⚪ Generic template (Phase 2 fallback)")

show_area("Career", career_event, career_para)
show_area("Love", love_event, love_para)
show_area("Health", health_event, health_para)
show_area("Finance", finance_event, finance_para)

print("\n" + "="*80)
print("💡 Phase 3 matches language to the transiting planet!")
print("="*80 + "\n")

