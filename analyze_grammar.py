#!/usr/bin/env python3
"""Analyze narrative grammar size and detect issues."""

import json
from pathlib import Path
from collections import Counter

def analyze_storylets():
    """Analyze storylets.json for size and duplicates."""
    filepath = Path("data/phrasebank/storylets.json")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    storylets = data.get("storylets", {})
    
    all_templates = []
    stats = {
        "areas": len(storylets),
        "openers": 0,
        "coaching": 0,
        "closers": 0,
    }
    
    for area_name, area_data in storylets.items():
        # Openers
        if "openers" in area_data:
            for tone, templates in area_data["openers"].items():
                stats["openers"] += len(templates)
                all_templates.extend(templates)
        
        # Coaching
        if "coaching" in area_data:
            stats["coaching"] += len(area_data["coaching"])
            all_templates.extend(area_data["coaching"])
        
        # Closers
        if "closers" in area_data:
            for tone, templates in area_data["closers"].items():
                stats["closers"] += len(templates)
                all_templates.extend(templates)
    
    total = stats["openers"] + stats["coaching"] + stats["closers"]
    unique = len(set(all_templates))
    duplicates = total - unique
    
    print("\n=== STORYLETS.JSON ANALYSIS ===")
    print(f"File size: {filepath.stat().st_size / 1024:.2f} KB")
    print(f"Areas: {stats['areas']}")
    print(f"Openers: {stats['openers']}")
    print(f"Coaching: {stats['coaching']}")
    print(f"Closers: {stats['closers']}")
    print(f"TOTAL TEMPLATES: {total}")
    print(f"Unique templates: {unique}")
    print(f"Duplicates: {duplicates}")
    
    if duplicates > 0:
        print("\n❌ DUPLICATE TEMPLATES FOUND:")
        counter = Counter(all_templates)
        for template, count in counter.most_common():
            if count > 1:
                print(f"  [{count}x] {template[:80]}...")
    
    return stats, all_templates


def analyze_phrases():
    """Analyze phrases.json for size."""
    filepath = Path("data/phrasebank/phrases.json")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_items = 0
    categories = len(data)
    
    for key, value in data.items():
        if isinstance(value, list):
            total_items += len(value)
        elif isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, list):
                    total_items += len(subvalue)
    
    print("\n=== PHRASES.JSON ANALYSIS ===")
    print(f"File size: {filepath.stat().st_size / 1024:.2f} KB")
    print(f"Categories: {categories}")
    print(f"Total phrase items: {total_items}")
    
    return categories, total_items


def check_fragmentation():
    """Check for fragmented/incomplete content."""
    filepath = Path("data/phrasebank/storylets.json")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    storylets = data.get("storylets", {})
    
    print("\n=== FRAGMENTATION CHECK ===")
    issues = []
    
    for area_name, area_data in storylets.items():
        # Check if area has all required sections
        has_openers = "openers" in area_data
        has_coaching = "coaching" in area_data
        has_closers = "closers" in area_data
        
        if not has_openers:
            issues.append(f"  ❌ {area_name}: Missing 'openers'")
        if not has_coaching:
            issues.append(f"  ⚠️  {area_name}: Missing 'coaching' (optional)")
        if not has_closers:
            issues.append(f"  ❌ {area_name}: Missing 'closers'")
        
        # Check if openers/closers have all 3 tones
        if has_openers:
            tones = set(area_data["openers"].keys())
            expected_tones = {"support", "challenge", "neutral"}
            missing_tones = expected_tones - tones
            if missing_tones:
                issues.append(f"  ⚠️  {area_name}.openers: Missing tones {missing_tones}")
        
        if has_closers:
            tones = set(area_data["closers"].keys())
            expected_tones = {"support", "challenge", "neutral"}
            missing_tones = expected_tones - tones
            if missing_tones:
                issues.append(f"  ⚠️  {area_name}.closers: Missing tones {missing_tones}")
    
    if issues:
        print("Issues found:")
        for issue in issues:
            print(issue)
    else:
        print("✅ No fragmentation issues found")


def check_abstraction():
    """Check for overly abstract or vague templates."""
    filepath = Path("data/phrasebank/storylets.json")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    storylets = data.get("storylets", {})
    all_templates = []
    
    for area_name, area_data in storylets.items():
        if "openers" in area_data:
            for tone, templates in area_data["openers"].items():
                for t in templates:
                    all_templates.append((area_name, "opener", tone, t))
        
        if "coaching" in area_data:
            for t in area_data["coaching"]:
                all_templates.append((area_name, "coaching", "neutral", t))
        
        if "closers" in area_data:
            for tone, templates in area_data["closers"].items():
                for t in templates:
                    all_templates.append((area_name, "closer", tone, t))
    
    print("\n=== ABSTRACTION CHECK ===")
    
    # Check for templates that don't use {descriptor} or {focus} placeholders
    no_placeholders = []
    for area, section, tone, template in all_templates:
        if section in ["opener", "closer"]:
            if "{descriptor}" not in template and "{focus}" not in template:
                no_placeholders.append((area, section, template))
    
    if no_placeholders:
        print(f"⚠️  {len(no_placeholders)} templates without placeholders (may be too generic):")
        for area, section, template in no_placeholders[:5]:
            print(f"  [{area}.{section}] {template[:80]}...")
    else:
        print("✅ All openers/closers use placeholders")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("NARRATIVE GRAMMAR ANALYSIS")
    print("="*60)
    
    storylet_stats, _ = analyze_storylets()
    phrase_stats = analyze_phrases()
    check_fragmentation()
    check_abstraction()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    total_grammar_items = (
        storylet_stats["openers"] + 
        storylet_stats["coaching"] + 
        storylet_stats["closers"] + 
        phrase_stats[1]
    )
    print(f"Total Grammar Items: {total_grammar_items}")
    print(f"Is it exhaustive? ⚠️  NO - Limited to ~{total_grammar_items} templates")
    print(f"Recommendation: Expand each area with more variations")
    print("="*60 + "\n")

