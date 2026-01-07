"""Test that list items with malformed markdown are fixed."""

import sys
import requests
import json

# Set UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_basic_compatibility():
    """Test basic compatibility endpoint for markdown fixes."""
    print("\n" + "="*70)
    print("TEST: Basic Compatibility - List Item Markdown")
    print("="*70)
    
    url = "http://localhost:8081/v1/compatibility/basic"
    
    payload = {
        "person1_sign": "Aquarius",
        "person2_sign": "Sagittarius",
        "compatibility_type": "love",
        "llm": True
    }
    
    print("\n📤 Sending request...")
    print(f"   URL: {url}")
    print(f"   Signs: Aquarius ♒ + Sagittarius ♐")
    print(f"   Type: Love")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        print("\n✅ Response received!")
        print(f"   Status: {response.status_code}")
        if 'score' in data:
            print(f"   Overall score: {data['score']['overall']}/100")
        elif 'overall_score' in data:
            print(f"   Overall score: {data['overall_score']}/100")
        
        # Check for malformed markdown in lists
        malformed_found = False
        
        import re
        # Patterns to detect malformed markdown
        pattern1 = r'(?<!\*)\*(?!\*)([^\*]+)\*\*'  # Match: single * followed by text followed by **
        pattern2 = r'\*\*([^\*]+)\*(?!\*)'  # Match: ** followed by text followed by single *
        
        print("\n🔍 Checking strengths for malformed markdown:")
        for i, strength in enumerate(data.get('strengths', []), 1):
            has_malformed = bool(re.search(pattern1, strength)) or bool(re.search(pattern2, strength))
            
            status = "❌ MALFORMED" if has_malformed else "✅ OK"
            print(f"   {i}. {strength[:60]}... {status}")
            
            if has_malformed:
                malformed_found = True
        
        print("\n🔍 Checking challenges for malformed markdown:")
        for i, challenge in enumerate(data.get('challenges', []), 1):
            has_malformed = bool(re.search(pattern1, challenge)) or bool(re.search(pattern2, challenge))
            
            status = "❌ MALFORMED" if has_malformed else "✅ OK"
            print(f"   {i}. {challenge[:60]}... {status}")
            
            if has_malformed:
                malformed_found = True
        
        print("\n🔍 Checking advice for malformed markdown:")
        for i, advice_item in enumerate(data.get('advice', []), 1):
            has_malformed = bool(re.search(pattern1, advice_item)) or bool(re.search(pattern2, advice_item))
            
            status = "❌ MALFORMED" if has_malformed else "✅ OK"
            print(f"   {i}. {advice_item[:60]}... {status}")
            
            if has_malformed:
                malformed_found = True
        
        # Print sample output
        print("\n📄 Sample output:")
        print("\nStrengths (first 3):")
        for strength in data.get('strengths', [])[:3]:
            print(f"  • {strength}")
        
        print("\nChallenges (first 3):")
        for challenge in data.get('challenges', [])[:3]:
            print(f"  • {challenge}")
        
        if malformed_found:
            print("\n" + "="*70)
            print("❌ TEST FAILED - Malformed markdown still present")
            print("="*70)
            return False
        else:
            print("\n" + "="*70)
            print("✅ TEST PASSED - All markdown properly formatted")
            print("="*70)
            return True
        
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out (60s)")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error - is the API running?")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run markdown fix tests."""
    print("\n" + "🧪 " * 35)
    print("LIST ITEM MARKDOWN FIX TEST")
    print("🧪 " * 35)
    
    print("\n⏳ Waiting for API to be ready...")
    import time
    time.sleep(3)
    
    try:
        # Test basic endpoint
        test_passed = test_basic_compatibility()
        
        if test_passed:
            print("\n" + "🎉 " * 35)
            print("ALL TESTS PASSED - READY FOR AWS DEPLOYMENT")
            print("🎉 " * 35)
            print("\nThe malformed markdown fix is working correctly!")
            print("List items now have proper **bold** formatting.")
            return 0
        else:
            print("\n⚠️  Tests failed - DO NOT deploy to AWS yet")
            return 1
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

