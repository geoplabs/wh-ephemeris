"""
GPU Acceleration for Yearly Forecast Calculations (DEV ONLY)

Uses CuPy for CUDA-accelerated array operations.
Falls back to NumPy if GPU is not available.

Install: pip install cupy-cuda12x  (or appropriate CUDA version)
"""
import os
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Try to import CuPy for GPU acceleration
GPU_AVAILABLE = False
USE_GPU = os.getenv("USE_GPU_ACCELERATION", "false").lower() in ("true", "1", "yes")

try:
    if USE_GPU:
        import cupy as cp
        GPU_AVAILABLE = True
        logger.info(f"🎮 GPU acceleration ENABLED - Using device: {cp.cuda.Device()}")
    else:
        cp = np
        logger.info("GPU acceleration disabled via USE_GPU_ACCELERATION=false")
except ImportError:
    cp = np
    if USE_GPU:
        logger.warning("⚠️ CuPy not installed. Install with: pip install cupy-cuda12x")
        logger.info("Falling back to CPU (NumPy)")
except Exception as e:
    cp = np
    logger.warning(f"GPU initialization failed: {e}. Falling back to CPU.")


class GPUAccelerator:
    """GPU-accelerated calculations for yearly forecasts"""
    
    def __init__(self, use_gpu: bool = USE_GPU):
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.xp = cp if self.use_gpu else np
        
    def batch_angle_differences(
        self, 
        transit_lons: List[float], 
        natal_lons: List[float]
    ) -> np.ndarray:
        """
        Calculate angle differences between all transit-natal pairs.
        
        GPU: Processes all combinations in parallel
        CPU: Sequential NumPy operations
        
        Returns: 2D array of shape (len(transit_lons), len(natal_lons))
        """
        if not transit_lons or not natal_lons:
            return np.array([])
        
        # Convert to GPU arrays
        transit_arr = self.xp.array(transit_lons, dtype=self.xp.float32)
        natal_arr = self.xp.array(natal_lons, dtype=self.xp.float32)
        
        # Broadcast to create all combinations
        t = transit_arr[:, self.xp.newaxis]  # Shape: (n_transit, 1)
        n = natal_arr[self.xp.newaxis, :]     # Shape: (1, n_natal)
        
        # Calculate differences
        diff = t - n
        
        # Normalize to [-180, 180]
        diff = self.xp.where(diff > 180, diff - 360, diff)
        diff = self.xp.where(diff < -180, diff + 360, diff)
        
        # Convert back to CPU numpy array
        if self.use_gpu:
            return cp.asnumpy(diff)
        return diff
    
    def batch_aspect_detection(
        self,
        transit_lons: np.ndarray,
        natal_lons: np.ndarray,
        aspect_angles: List[float],
        orb_limits: np.ndarray
    ) -> List[Tuple[int, int, int, float]]:
        """
        Detect aspects between transit and natal positions.
        
        Returns: List of (transit_idx, natal_idx, aspect_idx, orb)
        """
        if len(transit_lons) == 0 or len(natal_lons) == 0:
            return []
        
        # Calculate all angle differences
        diffs = self.batch_angle_differences(transit_lons.tolist(), natal_lons.tolist())
        
        # Move to GPU for aspect checking
        diffs_gpu = self.xp.array(diffs, dtype=self.xp.float32)
        aspects_gpu = self.xp.array(aspect_angles, dtype=self.xp.float32)
        orbs_gpu = self.xp.array(orb_limits, dtype=self.xp.float32)
        
        results = []
        
        # Check each aspect type
        for aspect_idx, aspect_angle in enumerate(aspect_angles):
            # Calculate orb for this aspect
            orb_from_aspect = self.xp.abs(diffs_gpu - aspect_angle)
            
            # Broadcast orb limits to match shape
            if orbs_gpu.ndim == 1:
                # Orb limits per natal body
                orb_limit_broadcast = orbs_gpu[self.xp.newaxis, :]
            else:
                orb_limit_broadcast = orbs_gpu
            
            # Find where aspect is within orb
            valid_mask = orb_from_aspect <= orb_limit_broadcast
            
            # Get indices of valid aspects
            if self.use_gpu:
                valid_indices = cp.asnumpy(cp.argwhere(valid_mask))
                orb_values = cp.asnumpy(orb_from_aspect[valid_mask])
            else:
                valid_indices = np.argwhere(valid_mask)
                orb_values = orb_from_aspect[valid_mask]
            
            # Add to results
            for idx, (t_idx, n_idx) in enumerate(valid_indices):
                results.append((int(t_idx), int(n_idx), aspect_idx, float(orb_values[idx])))
        
        return results
    
    def batch_declination_parallels(
        self,
        transit_declinations: np.ndarray,
        natal_declinations: np.ndarray,
        orb_limit: float = 1.0
    ) -> List[Tuple[int, int, float, str]]:
        """
        Detect declination parallels and contraparallels.
        
        Returns: List of (transit_idx, natal_idx, orb, type)
        """
        if len(transit_declinations) == 0 or len(natal_declinations) == 0:
            return []
        
        # Move to GPU
        t_dec = self.xp.array(transit_declinations, dtype=self.xp.float32)
        n_dec = self.xp.array(natal_declinations, dtype=self.xp.float32)
        
        # Broadcast
        t = t_dec[:, self.xp.newaxis]
        n = n_dec[self.xp.newaxis, :]
        
        # Check parallels (same declination)
        parallel_diff = self.xp.abs(t - n)
        parallel_mask = parallel_diff <= orb_limit
        
        # Check contraparallels (opposite declination)
        contraparallel_diff = self.xp.abs(t + n)
        contraparallel_mask = contraparallel_diff <= orb_limit
        
        results = []
        
        # Process parallels
        if self.use_gpu:
            p_indices = cp.asnumpy(cp.argwhere(parallel_mask))
            p_orbs = cp.asnumpy(parallel_diff[parallel_mask])
            cp_indices = cp.asnumpy(cp.argwhere(contraparallel_mask))
            cp_orbs = cp.asnumpy(contraparallel_diff[contraparallel_mask])
        else:
            p_indices = np.argwhere(parallel_mask)
            p_orbs = parallel_diff[parallel_mask]
            cp_indices = np.argwhere(contraparallel_mask)
            cp_orbs = contraparallel_diff[contraparallel_mask]
        
        for idx, (t_idx, n_idx) in enumerate(p_indices):
            results.append((int(t_idx), int(n_idx), float(p_orbs[idx]), "parallel"))
        
        for idx, (t_idx, n_idx) in enumerate(cp_indices):
            results.append((int(t_idx), int(n_idx), float(cp_orbs[idx]), "contraparallel"))
        
        return results
    
    def batch_midpoint_crossings(
        self,
        transit_lons: np.ndarray,
        midpoint_lons: List[float],
        orb_limit: float = 1.5
    ) -> List[Tuple[int, int, float]]:
        """
        Detect when transit bodies cross midpoints.
        
        Returns: List of (transit_idx, midpoint_idx, orb)
        """
        if len(transit_lons) == 0 or len(midpoint_lons) == 0:
            return []
        
        # Move to GPU
        t_lons = self.xp.array(transit_lons, dtype=self.xp.float32)
        m_lons = self.xp.array(midpoint_lons, dtype=self.xp.float32)
        
        # Broadcast
        t = t_lons[:, self.xp.newaxis]
        m = m_lons[self.xp.newaxis, :]
        
        # Calculate differences
        diff = t - m
        diff = self.xp.where(diff > 180, diff - 360, diff)
        diff = self.xp.where(diff < -180, diff + 360, diff)
        
        # Find crossings within orb
        orb = self.xp.abs(diff)
        mask = orb <= orb_limit
        
        # Extract results
        if self.use_gpu:
            indices = cp.asnumpy(cp.argwhere(mask))
            orbs = cp.asnumpy(orb[mask])
        else:
            indices = np.argwhere(mask)
            orbs = orb[mask]
        
        results = []
        for idx, (t_idx, m_idx) in enumerate(indices):
            results.append((int(t_idx), int(m_idx), float(orbs[idx])))
        
        return results
    
    def batch_score_calculation(
        self,
        orbs: np.ndarray,
        orb_limits: np.ndarray,
        aspect_weights: np.ndarray,
        planet_weights: np.ndarray
    ) -> np.ndarray:
        """
        Vectorized scoring calculation.
        
        Returns: Array of scores
        """
        # Move to GPU
        orbs_gpu = self.xp.array(orbs, dtype=self.xp.float32)
        limits_gpu = self.xp.array(orb_limits, dtype=self.xp.float32)
        aspect_w = self.xp.array(aspect_weights, dtype=self.xp.float32)
        planet_w = self.xp.array(planet_weights, dtype=self.xp.float32)
        
        # Calculate orb strength (1.0 at exact, 0.0 at limit)
        orb_strength = 1.0 - (orbs_gpu / limits_gpu)
        orb_strength = self.xp.clip(orb_strength, 0.0, 1.0)
        
        # Apply weights
        scores = orb_strength * aspect_w * planet_w
        
        # Convert back
        if self.use_gpu:
            return cp.asnumpy(scores)
        return scores
    
    def optimize_timeline_batch(
        self,
        positions: List[Dict[str, float]],
        batch_size: int = 100
    ) -> np.ndarray:
        """
        Process timeline positions in GPU-optimized batches.
        """
        if not positions:
            return np.array([])
        
        # Extract longitudes
        lons = [p.get('lon', 0.0) for p in positions]
        
        # Process in batches
        results = []
        for i in range(0, len(lons), batch_size):
            batch = lons[i:i+batch_size]
            batch_gpu = self.xp.array(batch, dtype=self.xp.float32)
            
            # Perform GPU operations here
            # (This is a placeholder - actual operations depend on use case)
            processed = batch_gpu  # Replace with actual processing
            
            if self.use_gpu:
                results.append(cp.asnumpy(processed))
            else:
                results.append(processed)
        
        return np.concatenate(results) if results else np.array([])
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get GPU device information"""
        info = {
            "gpu_available": GPU_AVAILABLE,
            "use_gpu": self.use_gpu,
            "backend": "CuPy (CUDA)" if self.use_gpu else "NumPy (CPU)"
        }
        
        if self.use_gpu and GPU_AVAILABLE:
            try:
                device = cp.cuda.Device()
                info.update({
                    "device_id": device.id,
                    "device_name": device.attributes.get("Name", "Unknown"),
                    "compute_capability": f"{device.compute_capability}",
                    "total_memory_gb": device.mem_info[1] / (1024**3),
                    "free_memory_gb": device.mem_info[0] / (1024**3),
                })
            except Exception as e:
                info["error"] = str(e)
        
        return info


# Global accelerator instance
_accelerator: Optional[GPUAccelerator] = None

def get_accelerator() -> GPUAccelerator:
    """Get or create the global GPU accelerator instance"""
    global _accelerator
    if _accelerator is None:
        _accelerator = GPUAccelerator()
    return _accelerator


def log_gpu_status():
    """Log GPU status at module import"""
    acc = get_accelerator()
    info = acc.get_device_info()
    
    if info["use_gpu"]:
        logger.info(f"🎮 GPU Acceleration ACTIVE: {info.get('device_name', 'Unknown GPU')}")
        logger.info(f"   Compute Capability: {info.get('compute_capability', 'N/A')}")
        logger.info(f"   Memory: {info.get('free_memory_gb', 0):.2f}GB / {info.get('total_memory_gb', 0):.2f}GB")
    else:
        logger.info(f"💻 Running on CPU (NumPy)")


# Log status on import
log_gpu_status()

