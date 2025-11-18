"""
GPU-Accelerated Yearly Western Forecast (DEV ONLY)

This module patches the yearly_western module to use GPU acceleration
for computationally intensive operations.

Enable with environment variable: USE_GPU_ACCELERATION=true
"""
import os
import logging
from typing import List, Dict, Any, Sequence, Tuple
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# Only enable in development
USE_GPU = os.getenv("USE_GPU_ACCELERATION", "false").lower() in ("true", "1", "yes")

if USE_GPU:
    try:
        from .gpu_accelerator import get_accelerator, GPUAccelerator
        
        GPU_ENABLED = True
        logger.info("🎮 GPU-accelerated yearly forecast enabled")
    except ImportError as e:
        GPU_ENABLED = False
        logger.warning(f"GPU acceleration requested but failed to load: {e}")
else:
    GPU_ENABLED = False


def patch_declination_detection(engine_instance):
    """
    Patch the declination detection method to use GPU.
    
    This replaces the sequential loop with batched GPU operations.
    """
    if not GPU_ENABLED:
        return
    
    original_method = engine_instance._detect_declination_events
    accelerator = get_accelerator()
    
    def gpu_detect_declination_events(
        timeline: List[Tuple[datetime, Dict[str, Dict[str, float]]]],
        bodies: Sequence[str],
    ) -> List[Dict[str, Any]]:
        """GPU-accelerated declination detection"""
        cfg = engine_instance.config.declination_aspects or {}
        if not (cfg.get("parallels") or cfg.get("contraparallels")):
            return []
        
        # Get natal declinations (cached)
        natal_dec = engine_instance._natal_declinations()
        if not natal_dec:
            return []
        
        logger.info(f"🎮 GPU: Processing declination aspects for {len(bodies)} bodies across {len(timeline)} scan points")
        
        # Build arrays for GPU processing
        all_events = []
        
        # Process in chunks to avoid memory issues
        chunk_size = 100
        for chunk_start in range(0, len(timeline), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(timeline))
            chunk_timeline = timeline[chunk_start:chunk_end]
            
            for body in bodies:
                # Extract declinations for this body across timeline chunk
                transit_decs = []
                timestamps = []
                
                for ts, positions in chunk_timeline:
                    pos = positions.get(body)
                    if not pos:
                        continue
                    decl = pos.get("decl") or pos.get("declination") or pos.get("lat")
                    if decl is not None:
                        transit_decs.append(decl)
                        timestamps.append(ts)
                
                if not transit_decs:
                    continue
                
                # Get natal declinations for Sun and Moon
                natal_values = []
                natal_names = []
                for name in ["Sun", "Moon"]:
                    if name in natal_dec:
                        natal_values.append(natal_dec[name])
                        natal_names.append(name)
                
                if not natal_values:
                    continue
                
                # GPU batch processing
                transit_arr = np.array(transit_decs)
                natal_arr = np.array(natal_values)
                
                results = accelerator.batch_declination_parallels(
                    transit_arr, natal_arr, orb_limit=1.0
                )
                
                # Convert results to events
                for t_idx, n_idx, orb, aspect_type in results:
                    if aspect_type == "parallel" and not cfg.get("parallels", True):
                        continue
                    if aspect_type == "contraparallel" and not cfg.get("contraparallels", True):
                        continue
                    
                    ts = timestamps[t_idx]
                    natal_body = natal_names[n_idx]
                    
                    event = {
                        "event_type": "declination_aspect",
                        "transit_body": body,
                        "natal_body": natal_body,
                        "aspect": aspect_type,
                        "orb": round(orb, 2),
                        "exact_hit_time_utc": ts.isoformat().replace("+00:00", "Z"),
                        "date": ts.date().isoformat(),
                        "note": f"{body} {aspect_type.replace('_', ' ')} natal {natal_body}",
                    }
                    all_events.append(event)
        
        logger.info(f"🎮 GPU: Found {len(all_events)} declination aspects")
        return all_events
    
    # Replace the method
    engine_instance._detect_declination_events = gpu_detect_declination_events


def patch_midpoint_detection(engine_instance):
    """
    Patch midpoint detection to use GPU batch processing.
    """
    if not GPU_ENABLED:
        return
    
    accelerator = get_accelerator()
    original_method = engine_instance._detect_midpoint_events
    
    def gpu_detect_midpoint_events(
        timeline: List[Tuple[datetime, Dict[str, Dict[str, float]]]],
        bodies: Sequence[str],
        step,
    ) -> List[Dict[str, Any]]:
        """GPU-accelerated midpoint detection"""
        cfg = engine_instance.config.midpoints or {}
        if not cfg.get("enabled"):
            return []
        
        pairs = cfg.get("pairs") or []
        if not pairs:
            return []
        
        logger.info(f"🎮 GPU: Processing {len(pairs)} midpoints for {len(bodies)} bodies")
        
        # Use original method for now (midpoints require state tracking)
        # GPU acceleration here is complex due to crossing detection
        return original_method(timeline, bodies, step)
    
    engine_instance._detect_midpoint_events = gpu_detect_midpoint_events


def apply_gpu_acceleration(engine_instance):
    """
    Apply GPU acceleration patches to a WesternYearlyEngine instance.
    
    Call this in the engine's __init__ or run() method.
    """
    if not GPU_ENABLED:
        logger.info("GPU acceleration not enabled (USE_GPU_ACCELERATION not set to true)")
        return
    
    logger.info("=" * 60)
    logger.info("🎮 GPU ACCELERATION ACTIVE")
    logger.info("=" * 60)
    logger.info("Applying GPU acceleration patches to yearly engine...")
    
    # Patch computationally intensive methods
    patch_declination_detection(engine_instance)
    patch_midpoint_detection(engine_instance)
    
    # Log GPU info
    if GPU_ENABLED:
        accelerator = get_accelerator()
        info = accelerator.get_device_info()
        logger.info(f"🎮 GPU Device: {info.get('device_name', 'Unknown')}")
        logger.info(f"🎮 Free Memory: {info.get('free_memory_gb', 0):.2f}GB")
        logger.info("=" * 60)


# Convenience function for enabling GPU in dev environment
def enable_gpu_for_dev():
    """
    Enable GPU acceleration if in development environment.
    
    Add this to your dev startup:
    ```python
    if os.getenv("ENV") == "development":
        from api.services.yearly_western_gpu import enable_gpu_for_dev
        enable_gpu_for_dev()
    ```
    """
    if not GPU_ENABLED:
        logger.info("💻 GPU acceleration not enabled. Set USE_GPU_ACCELERATION=true to enable.")
        return False
    
    logger.info("🎮 GPU acceleration is active for yearly forecasts")
    return True

