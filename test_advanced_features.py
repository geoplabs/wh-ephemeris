"""
Test script for Advanced Astrological Features
"""
import json
from datetime import datetime
from api.services import transits_engine, advanced_transits
from api.services.ephem import positions_ecliptic, to_jd_utc

def test_advanced_features():
    print("\n" + "="*70)
    print("TESTING ADVANCED ASTROLOGICAL FEATURES")
    print("="*70)
    
    # Test chart
    chart_input = {
        "system": "western",
        "date": "1997-02-12",
        "time": "00:19:59",
        "place": {
            "lat": 28.6138,
            "lon": 77.2090,
            "tz": "Asia/Kolkata"
        }
    }
    
    # Test date: 2025-11-15
    opts = {
        "from_date": "2025-11-15",
        "to_date": "2025-11-15",
        "step_days": 1,
    }
    
    print(f"\nChart: {chart_input['date']}")
    print(f"Forecast Date: {opts['from_date']}")
    
    # Compute transits with advanced features
    events = transits_engine.compute_transits(chart_input, opts)
    
    print(f"\n✅ Generated {len(events)} transit events")
    
    # Check for advanced features in first 5 events
    features_found = {
        "station": 0,
        "retrograde_bias": 0,
        "ingress": 0,
        "solar_relationship": 0,
        "enhanced_window": 0,
    }
    
    print("\n" + "-"*70)
    print("CHECKING FIRST 10 EVENTS FOR ADVANCED FEATURES:")
    print("-"*70)
    
    for i, event in enumerate(events[:10]):
        print(f"\nEvent {i+1}: {event['transit_body']} {event['aspect']} {event['natal_body']}")
        print(f"  Base Score: {event.get('base_score', 'N/A'):.2f}")
        print(f"  Adjusted Score: {event['score']:.2f}")
        
        # Check station
        if event.get('station_info'):
            features_found['station'] += 1
            print(f"  ✅ STATION: {event['station_info']['station_type']}")
        
        # Check retrograde bias
        if event.get('retrograde_bias', {}).get('has_bias'):
            features_found['retrograde_bias'] += 1
            bias = event['retrograde_bias']
            print(f"  ✅ RETROGRADE BIAS: {bias['planet']} - {bias['description']}")
            print(f"     Modifier: +{bias['modifier']}, Areas: {', '.join(bias['areas'])}")
        
        # Check ingress
        if event.get('ingress_info'):
            features_found['ingress'] += 1
            ing = event['ingress_info']
            print(f"  ✅ INGRESS: {ing['leaving_sign']} → {ing['entering_sign']}")
            if ing['hit_natal_points']:
                print(f"     Hits: {', '.join(ing['hit_natal_points'])}")
        
        # Check solar relationship
        solar_rel = event.get('solar_relationship')
        if solar_rel and solar_rel.get('has_solar_relationship'):
            features_found['solar_relationship'] += 1
            print(f"  ✅ SOLAR RELATIONSHIP: {solar_rel['type'].upper()} - {solar_rel['description']}")
            print(f"     Distance: {solar_rel['distance_to_sun']:.2f}°, Modifier: {solar_rel['score_modifier']}")
        
        # Check enhanced window
        if event.get('enhanced_window_hours', 0) > 0:
            features_found['enhanced_window'] += 1
            print(f"  ✅ ENHANCED WINDOW: ±{event['enhanced_window_hours']} hours")
    
    print("\n" + "="*70)
    print("SUMMARY OF FEATURES FOUND:")
    print("="*70)
    for feature, count in features_found.items():
        status = "✅" if count > 0 else "⚪"
        print(f"{status} {feature.replace('_', ' ').title()}: {count} events")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_advanced_features()

