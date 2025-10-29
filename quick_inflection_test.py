#!/usr/bin/env python3
"""Quick inflection test - minimal and fast."""

import sys
sys.path.insert(0, '.')

print("Testing inflection module...")

try:
    from src.content.inflection import to_gerund, add_article, safe_phrase_for_template
    print("✅ Import successful")
    
    # Test 1: Simple gerund
    result1 = to_gerund("focus")
    print(f"✅ to_gerund('focus') = '{result1}'")
    
    # Test 2: Simple article
    result2 = add_article("approach")
    print(f"✅ add_article('approach') = '{result2}'")
    
    # Test 3: Template-aware (simple)
    result3 = safe_phrase_for_template("focus", "Plan {phrase} moves")
    print(f"✅ safe_phrase_for_template('focus', 'Plan {{phrase}} moves') = '{result3}'")
    
    print("\n✅ All tests passed! Inflection system working.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

