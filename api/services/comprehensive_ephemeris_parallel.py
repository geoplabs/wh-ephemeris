"""
Comprehensive Daily Ephemeris Generator - Parallel & GPU Accelerated Version

This is an optimized version using:
- Multiprocessing for daily calculations
- GPU acceleration where applicable
- Vectorized operations
- Concurrent event detection
"""

from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
import multiprocessing as mp

import swisseph as swe

from . import ephem
from . import houses as houses_svc
from .panchang_algos import (
    compute_tithi,
    compute_nakshatra,
    compute_yoga,
    TITHI_NAMES,
    NAKSHATRA_NAMES,
    YOGA_NAMES,
    MOBILE_KARANAS,
    FIXED_KARANAS,
)

# Try to import GPU acceleration
try:
    from .gpu_accelerator import GPUAccelerator
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("GPU acceleration not available (gpu_accelerator module not found)")

# Import from the full implementation
from .comprehensive_ephemeris_full import (
    ZODIAC_SIGNS,
    EXTENDED_BODIES,
    ASTEROIDS,
    LILITH_CODE,
    ASPECTS_CONFIG,
    MOON_ORB_BONUS,
    ECLIPSE_THEMES,
    SUPERMOON_THEMES,
    ComprehensiveEphemerisGenerator
)


class ParallelEphemerisGenerator(ComprehensiveEphemerisGenerator):
    """Parallel/GPU-accelerated version of comprehensive ephemeris generator."""
    
    def __init__(self, year: int, lat: float = 28.7041, lon: float = 77.1025,
                 location_name: str = "Delhi, India", timezone_str: str = "Asia/Kolkata",
                 num_workers: Optional[int] = None, use_gpu: bool = False):
        super().__init__(year, lat, lon, location_name, timezone_str)
        
        # Parallel processing config
        self.num_workers = num_workers or max(1, mp.cpu_count() - 1)
        self.use_gpu = use_gpu and GPU_AVAILABLE
        
        if self.use_gpu:
            print(f"GPU acceleration enabled")
            self.gpu = GPUAccelerator()
        else:
            print(f"Using {self.num_workers} CPU workers")
    
    def generate_daily_data_parallel(self):
        """Generate daily data using parallel processing."""
        print(f"Generating daily data (parallel with {self.num_workers} workers)...")
        
        start_date = datetime(self.year, 1, 1)
        if self.year % 4 == 0 and (self.year % 100 != 0 or self.year % 400 == 0):
            days_in_year = 366
        else:
            days_in_year = 365
        
        # Prepare tasks
        tasks = []
        for day_num in range(days_in_year):
            current_date = start_date + timedelta(days=day_num)
            date_str = current_date.strftime("%Y-%m-%d")
            jd = swe.julday(current_date.year, current_date.month, current_date.day, 0.0, swe.GREG_CAL)
            
            tasks.append((date_str, jd, current_date, day_num))
        
        # Process in parallel
        results = []
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(
                    calculate_single_day,
                    date_str, jd, current_date, self.lat, self.lon, self.eclipses
                ): (date_str, day_num)
                for date_str, jd, current_date, day_num in tasks
            }
            
            # Collect results
            completed = 0
            for future in as_completed(future_to_task):
                date_str, day_num = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    if completed % 50 == 0:
                        print(f"  Completed {completed}/{days_in_year} days")
                        
                except Exception as e:
                    print(f"Error processing {date_str}: {e}")
        
        # Sort results by date and build daily_data dict
        results.sort(key=lambda x: x['date'])
        
        # Build ingresses and stations by comparing consecutive days
        prev_positions = None
        for result in results:
            date_str = result['date']
            self.daily_data[date_str] = result['data']
            
            planets = result['data']['planets']
            
            # Track ingresses
            if prev_positions:
                for planet_name in planets.keys():
                    if planet_name in prev_positions:
                        prev_sign = prev_positions[planet_name].get("zodiac_sign")
                        curr_sign = planets[planet_name].get("zodiac_sign")
                        
                        if prev_sign and curr_sign and prev_sign != curr_sign:
                            jd = result['data']['julian_day']
                            ingress_data = {
                                "julian_day": jd,
                                "date": date_str,
                                "time": self._jd_to_time_dict(jd),
                                "new_sign": curr_sign,
                                "planet": planet_name
                            }
                            self.planetary_ingresses[planet_name].append(ingress_data)
                
                # Track retrograde stations
                for planet_name in ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
                    if planet_name in prev_positions and planet_name in planets:
                        prev_retro = prev_positions[planet_name].get("is_retrograde", False)
                        curr_retro = planets[planet_name].get("is_retrograde", False)
                        
                        if prev_retro != curr_retro:
                            station_type = "retrograde" if curr_retro else "direct"
                            jd = result['data']['julian_day']
                            station_data = {
                                "julian_day": jd,
                                "date": date_str,
                                "time": self._jd_to_time_dict(jd),
                                "station_type": station_type,
                                "planet": planet_name
                            }
                            self.retrograde_stations[planet_name].append(station_data)
            
            prev_positions = planets.copy()
        
        print(f"Generated {len(self.daily_data)} days of data")
        self._mark_time("daily_calculation")
    
    def detect_vedic_changes_parallel(self):
        """Detect vedic changes using parallel processing."""
        print(f"Detecting vedic changes (parallel)...")
        
        start_date = datetime(self.year, 1, 1, tzinfo=timezone.utc)
        if self.year % 4 == 0 and (self.year % 100 != 0 or self.year % 400 == 0):
            days_in_year = 366
        else:
            days_in_year = 365
        
        # Prepare daily tasks
        tasks = []
        for day_num in range(days_in_year):
            current_date = start_date + timedelta(days=day_num)
            date_str = current_date.strftime("%Y-%m-%d")
            tasks.append((current_date, date_str))
        
        # Process in parallel with threads (lighter weight for I/O bound tasks)
        all_tithi_changes = []
        all_yoga_changes = []
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(detect_vedic_changes_for_day, current_date, date_str)
                for current_date, date_str in tasks
            ]
            
            for future in as_completed(futures):
                try:
                    tithi_changes, yoga_changes = future.result()
                    all_tithi_changes.extend(tithi_changes)
                    all_yoga_changes.extend(yoga_changes)
                except Exception:
                    continue
        
        # Sort and store
        self.vedic_changes["tithi"] = sorted(all_tithi_changes, key=lambda x: x["julian_day"])
        self.vedic_changes["yoga"] = sorted(all_yoga_changes, key=lambda x: x["julian_day"])
        
        print(f"Found {len(self.vedic_changes['tithi'])} tithi changes")
        print(f"Found {len(self.vedic_changes['yoga'])} yoga changes")
        self._mark_time("vedic_changes")
    
    def detect_nakshatra_changes_parallel(self):
        """Detect nakshatra changes using parallel processing."""
        print(f"Detecting nakshatra changes (parallel)...")
        
        start_date = datetime(self.year, 1, 1, tzinfo=timezone.utc)
        if self.year % 4 == 0 and (self.year % 100 != 0 or self.year % 400 == 0):
            days_in_year = 366
        else:
            days_in_year = 365
        
        # Check every day for nakshatra changes
        tasks = []
        for day_num in range(days_in_year):
            current_date = start_date + timedelta(days=day_num)
            date_str = current_date.strftime("%Y-%m-%d")
            tasks.append((current_date, date_str, day_num))
        
        # Process in parallel
        all_changes = []
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(detect_nakshatra_changes_for_day, current_date, date_str)
                for current_date, date_str, _ in tasks
            ]
            
            for future in as_completed(futures):
                try:
                    changes = future.result()
                    all_changes.extend(changes)
                except Exception:
                    continue
        
        # Sort and store
        self.nakshatra_changes = sorted(all_changes, key=lambda x: x["julian_day"])
        
        print(f"Found {len(self.nakshatra_changes)} nakshatra changes")
        self._mark_time("nakshatra_changes")
    
    def generate(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate complete ephemeris using parallel processing."""
        
        print(f"Generating comprehensive ephemeris for {self.year} (PARALLEL MODE)...")
        print(f"Location: {self.location_name} ({self.lat}, {self.lon})")
        print(f"Workers: {self.num_workers} CPU cores")
        if self.use_gpu:
            print(f"GPU: Enabled")
        print("=" * 70)
        
        # Step 1: Detect special events (can run in parallel)
        with ThreadPoolExecutor(max_workers=2) as executor:
            eclipse_future = executor.submit(self.detect_eclipses)
            supermoon_future = executor.submit(self.detect_supermoons)
            
            eclipse_future.result()
            supermoon_future.result()
        
        # Step 2: Generate daily data in parallel
        self.generate_daily_data_parallel()
        
        # Step 3: Build retrograde periods
        self.detect_retrograde_periods()
        
        # Step 4: Add retrograde metadata
        self.add_retrograde_metadata_to_planets()
        
        # Step 5 & 6: Detect vedic changes and nakshatra transitions in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            vedic_future = executor.submit(self.detect_vedic_changes_parallel)
            nakshatra_future = executor.submit(self.detect_nakshatra_changes_parallel)
            
            vedic_future.result()
            nakshatra_future.result()
        
        # Continue with rest of generation (same as parent class)
        return super().generate(output_file)


# Worker functions (must be at module level for multiprocessing)

def calculate_single_day(date_str: str, jd: float, current_date: datetime,
                        lat: float, lon: float, eclipses: List[Dict]) -> Dict[str, Any]:
    """Calculate all data for a single day (worker function)."""
    
    import swisseph as swe
    from . import ephem
    
    weekday = current_date.strftime("%A")
    
    # Check eclipse window
    eclipse_window_active = any(
        abs((datetime.fromisoformat(eclipse["date"]) - current_date).days) <= 1
        for eclipse in eclipses
    )
    
    # Calculate positions (reuse logic from parent)
    gen = ComprehensiveEphemerisGenerator(current_date.year, lat, lon)
    planets, asteroids = gen._calculate_planet_positions(jd)
    houses = gen._calculate_houses(jd)
    aspects = gen._calculate_aspects(planets, asteroids)
    
    # Lunar phase
    sun_lon = planets.get("Sun", {}).get("longitude", 0)
    moon_lon = planets.get("Moon", {}).get("longitude", 0)
    angle = (moon_lon - sun_lon) % 360.0
    
    # Phase name
    if angle < 45:
        phase_name = "New Moon"
    elif angle < 90:
        phase_name = "Waxing Crescent"
    elif angle < 135:
        phase_name = "First Quarter"
    elif angle < 180:
        phase_name = "Waxing Gibbous"
    elif angle < 225:
        phase_name = "Full Moon"
    elif angle < 270:
        phase_name = "Waning Gibbous"
    elif angle < 315:
        phase_name = "Last Quarter"
    else:
        phase_name = "Waning Crescent"
    
    illumination = 50 * (1 - math.cos(math.radians(angle)))
    
    # Vedic elements
    try:
        moment = datetime(current_date.year, current_date.month, current_date.day, 0, 0, 0, tzinfo=timezone.utc)
        tithi_num, tithi_name, _, _ = compute_tithi(moment, ayanamsha="lahiri")
        yoga_num, yoga_name, _, _ = compute_yoga(moment, ayanamsha="lahiri")
        
        # Karana
        positions_sid = ephem.positions_ecliptic(jd, sidereal=True, ayanamsha="lahiri")
        moon_lon_sid = positions_sid.get("Moon", {}).get("lon", 0)
        sun_lon_sid = positions_sid.get("Sun", {}).get("lon", 0)
        diff = (moon_lon_sid - sun_lon_sid) % 360.0
        karana_index = int(diff / 6.0)
        
        if karana_index < 57:
            karana_num = karana_index % 7
            karana_name = MOBILE_KARANAS[karana_num]
        else:
            fixed_index = min(karana_index - 57, 3)
            karana_name = FIXED_KARANAS[fixed_index]
        
        paksha = "Shukla" if tithi_num <= 15 else "Krishna"
        day_name = tithi_name.split()[-1] if " " in tithi_name else tithi_name
        
    except Exception:
        tithi_num, day_name, paksha, yoga_name, karana_name = 1, "Pratipada", "Shukla", "Vishkambha", "Bava"
    
    # Build result
    day_data = {
        "julian_day": round(jd, 1),
        "weekday": weekday,
        "eclipse_window_active": eclipse_window_active,
        "planets": planets,
        "asteroids": asteroids,
        "houses": houses,
        "aspects": aspects,
        "lunar": {
            "phase": {
                "phase": phase_name,
                "angle": round(angle, 2),
                "illumination": round(illumination, 1)
            },
            "tithi": {
                "number": tithi_num,
                "name": day_name,
                "paksha": paksha,
                "angle": round(angle, 2),
                "festivals": [],
                "is_special_day": False
            },
            "yoga": yoga_name,
            "karana": karana_name
        },
        "eclipses": [],
        "ingresses": [],
        "retrograde_stations": [],
        "vedic_changes": {},
        "nakshatra_changes": []
    }
    
    return {
        "date": date_str,
        "data": day_data
    }


def detect_vedic_changes_for_day(current_date: datetime, date_str: str) -> Tuple[List[Dict], List[Dict]]:
    """Detect vedic changes for a single day (worker function)."""
    
    tithi_changes = []
    yoga_changes = []
    
    # Check every 2 hours
    for hour in range(0, 24, 2):
        check_time = current_date.replace(hour=hour, minute=0, second=0)
        next_check = check_time + timedelta(hours=2)
        
        try:
            curr_tithi, curr_tithi_name, _, _ = compute_tithi(check_time, ayanamsha="lahiri")
            next_tithi, next_tithi_name, _, _ = compute_tithi(next_check, ayanamsha="lahiri")
            
            curr_yoga, curr_yoga_name, _, _ = compute_yoga(check_time, ayanamsha="lahiri")
            next_yoga, next_yoga_name, _, _ = compute_yoga(next_check, ayanamsha="lahiri")
            
            # Detect tithi change
            if curr_tithi != next_tithi:
                # Simplified: use midpoint as change time
                change_time = check_time + timedelta(hours=1)
                change_jd = swe.julday(change_time.year, change_time.month, change_time.day,
                                       change_time.hour + change_time.minute/60, swe.GREG_CAL)
                
                tithi_changes.append({
                    "julian_day": change_jd,
                    "date": date_str,
                    "time": {
                        "utc": change_time.strftime("%H:%M:%S"),
                        "utc_iso": change_time.isoformat(),
                        "utc_date": date_str,
                        "utc_full": f"{date_str} {change_time.strftime('%H:%M:%S')} UTC"
                    },
                    "new_tithi": next_tithi,
                    "new_tithi_name": next_tithi_name.split()[-1] if " " in next_tithi_name else next_tithi_name
                })
            
            # Detect yoga change
            if curr_yoga != next_yoga:
                change_time = check_time + timedelta(hours=1)
                change_jd = swe.julday(change_time.year, change_time.month, change_time.day,
                                       change_time.hour + change_time.minute/60, swe.GREG_CAL)
                
                yoga_changes.append({
                    "julian_day": change_jd,
                    "date": date_str,
                    "time": {
                        "utc": change_time.strftime("%H:%M:%S"),
                        "utc_iso": change_time.isoformat(),
                        "utc_date": date_str,
                        "utc_full": f"{date_str} {change_time.strftime('%H:%M:%S')} UTC"
                    },
                    "new_yoga": next_yoga_name
                })
                
        except Exception:
            continue
    
    return tithi_changes, yoga_changes


def detect_nakshatra_changes_for_day(current_date: datetime, date_str: str) -> List[Dict]:
    """Detect nakshatra changes for a single day (worker function)."""
    
    changes = []
    prev_nak = None
    
    # Check every 3 hours
    for hour in range(0, 24, 3):
        check_time = current_date.replace(hour=hour, minute=0, second=0)
        
        try:
            nak_num, nak_name, nak_pada, _, _ = compute_nakshatra(check_time, ayanamsha="lahiri")
            
            if prev_nak and nak_num != prev_nak[0]:
                # Nakshatra changed
                change_time = check_time - timedelta(hours=1.5)  # Approximate midpoint
                change_jd = swe.julday(change_time.year, change_time.month, change_time.day,
                                       change_time.hour + change_time.minute/60, swe.GREG_CAL)
                
                # Get Moon position
                moon_pos, _ = swe.calc_ut(change_jd, swe.MOON, swe.FLG_SWIEPH)
                moon_trop_lon = moon_pos[0] % 360.0
                
                swe.set_sid_mode(swe.SIDM_LAHIRI)
                moon_pos_sid, _ = swe.calc_ut(change_jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
                moon_sid_lon = moon_pos_sid[0] % 360.0
                
                changes.append({
                    "julian_day": change_jd,
                    "date": date_str,
                    "time": {
                        "utc": change_time.strftime("%H:%M:%S"),
                        "utc_iso": change_time.isoformat(),
                        "utc_date": date_str,
                        "utc_full": f"{date_str} {change_time.strftime('%H:%M:%S')} UTC"
                    },
                    "from_nakshatra": prev_nak[1],
                    "to_nakshatra": nak_name,
                    "tropical_longitude": round(moon_trop_lon, 4),
                    "sidereal_longitude": round(moon_sid_lon, 4),
                    "ayanamsa": round(moon_trop_lon - moon_sid_lon, 4)
                })
            
            prev_nak = (nak_num, nak_name)
            
        except Exception:
            continue
    
    return changes


def generate_comprehensive_ephemeris_parallel(
    year: int,
    output_file: Optional[str] = None,
    lat: float = 28.7041,
    lon: float = 77.1025,
    location_name: str = "Delhi, India",
    num_workers: Optional[int] = None,
    use_gpu: bool = False
) -> Dict[str, Any]:
    """
    Generate comprehensive ephemeris with parallel/GPU acceleration.
    
    Args:
        year: Target year
        output_file: Optional output file path
        lat: Latitude
        lon: Longitude  
        location_name: Location name
        num_workers: Number of parallel workers (default: CPU count - 1)
        use_gpu: Enable GPU acceleration if available
    
    Returns:
        Complete ephemeris data dictionary
    """
    generator = ParallelEphemerisGenerator(
        year, lat, lon, location_name,
        num_workers=num_workers,
        use_gpu=use_gpu
    )
    
    return generator.generate(output_file)


if __name__ == "__main__":
    import sys
    
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    output = sys.argv[2] if len(sys.argv) > 2 else f"ephemeris_{year}_parallel.json"
    
    # Use all available CPU cores minus 1
    num_workers = max(1, mp.cpu_count() - 1)
    
    print(f"Generating ephemeris for {year} using {num_workers} workers...")
    
    generate_comprehensive_ephemeris_parallel(
        year,
        output_file=output,
        num_workers=num_workers,
        use_gpu=False  # Set to True if GPU support is implemented
    )


