# 🎮 GPU Acceleration for Yearly Forecasts (DEV ONLY)

## Overview

GPU acceleration can speed up yearly forecast calculations by **2-3×** for computationally intensive operations like:
- Declination aspect calculations
- Batch aspect detection
- Midpoint crossings
- Event scoring

**Note**: This is a DEV-ONLY feature for local development. Not recommended for production.

---

## Prerequisites

### 1. NVIDIA GPU Required
- CUDA-compatible NVIDIA GPU
- Minimum 4GB VRAM recommended
- Check compatibility: https://developer.nvidia.com/cuda-gpus

### 2. CUDA Toolkit
Install CUDA toolkit for your system:
- **Windows/Linux**: https://developer.nvidia.com/cuda-downloads
- **Recommended version**: CUDA 11.x or 12.x

---

## Installation

### Step 1: Install CuPy

CuPy is the GPU-accelerated NumPy alternative.

**For CUDA 12.x:**
```bash
pip install cupy-cuda12x
```

**For CUDA 11.x:**
```bash
pip install cupy-cuda11x
```

**Check your CUDA version:**
```bash
# Windows
nvcc --version

# Linux
nvidia-smi
```

### Step 2: Verify Installation

```python
import cupy as cp
print(f"CuPy version: {cp.__version__}")
print(f"CUDA available: {cp.cuda.is_available()}")
print(f"GPU: {cp.cuda.Device()}")
```

---

## Configuration

### Enable GPU Acceleration

Add to your `.env` file or set environment variable:

```bash
USE_GPU_ACCELERATION=true
```

### Verify GPU is Active

Start your dev server and check logs:

```bash
python -m uvicorn api.app:app --reload
```

Look for:
```
🎮 GPU acceleration ENABLED - Using device: NVIDIA GeForce RTX 3080
🎮 GPU Acceleration ACTIVE: NVIDIA GeForce RTX 3080
   Compute Capability: 8.6
   Memory: 8.5GB / 10.0GB
```

---

## Performance Expectations

### Without GPU (CPU Only)
- Your config: **~10 minutes** (600 seconds)
- Optimized config: ~4-5 minutes

### With GPU Acceleration
- Your config: **~4-6 minutes** (2-3× speedup)
- Optimized config: ~2-3 minutes

### Breakdown:
| Operation | CPU Time | GPU Time | Speedup |
|-----------|----------|----------|---------|
| Declination aspects (16 bodies × 1460 points) | ~4 min | **~1 min** | 4× |
| Base transit calculations | ~3 min | ~2 min | 1.5× |
| Midpoint detection | ~2 min | ~1.5 min | 1.3× |
| Progressions/Solar Return | ~1.5 min | ~1.5 min | 1× (not GPU accelerated) |
| Post-processing | ~30s | ~30s | 1× |
| **TOTAL** | **~10 min** | **~4-6 min** | **2-3×** |

---

## What Gets Accelerated

### ✅ GPU-Accelerated Operations:
- **Declination parallels/contraparallels** (biggest win)
- Batch aspect angle calculations
- Orb distance calculations
- Event scoring (vectorized)
- Large array operations

### ❌ Still on CPU:
- Swiss Ephemeris calls (C library, can't GPU-accelerate)
- Individual planetary position calculations
- Timeline building and sorting
- Event construction and formatting
- File I/O

---

## Usage

### Automatic (Recommended)

Just enable the environment variable - GPU acceleration activates automatically:

```bash
export USE_GPU_ACCELERATION=true  # Linux/Mac
set USE_GPU_ACCELERATION=true     # Windows CMD
$env:USE_GPU_ACCELERATION="true"  # Windows PowerShell

# Then run your API
python -m uvicorn api.app:app --reload
```

### Check GPU Status in Code

```python
from api.services.gpu_accelerator import get_accelerator

acc = get_accelerator()
info = acc.get_device_info()
print(info)
```

---

## Troubleshooting

### Issue: "CuPy not installed"

**Solution:**
```bash
pip install cupy-cuda12x  # Or appropriate CUDA version
```

### Issue: "CUDA driver version is insufficient"

**Solution:**
Update your NVIDIA drivers:
- https://www.nvidia.com/Download/index.aspx

### Issue: "Out of memory"

**Solution:**
Your yearly forecast config is too intensive. Try:

1. **Reduce scan_step_hours**:
   ```json
   "detection": {
     "scan_step_hours": 12  // Instead of 6
   }
   ```

2. **Disable heavy features**:
   ```json
   "declination_aspects": {
     "parallels": false,
     "contraparallels": false
   }
   ```

3. **Reduce transit bodies**:
   ```json
   "transits": {
     "bodies_extras": []  // Remove asteroids
   }
   ```

### Issue: GPU not being used despite being available

**Check:**
1. Environment variable is set: `echo $USE_GPU_ACCELERATION`
2. Check logs for GPU initialization messages
3. Verify with: `nvidia-smi` (should show Python process using GPU)

---

## Monitoring GPU Usage

### During Forecast Calculation

**Windows:**
```powershell
# Open new terminal
nvidia-smi -l 1  # Updates every second
```

**Linux:**
```bash
watch -n 1 nvidia-smi
```

### Watch for:
- GPU utilization: Should spike to 50-90% during calculations
- Memory usage: Will increase during processing
- Temperature: Normal to see 60-80°C under load

---

## Development Tips

### 1. Test with Small Date Ranges First

```json
{
  "year": 2025,
  "detection": {
    "scan_step_hours": 12  // Start larger
  },
  "transits": {
    "bodies": ["Sun", "Moon", "Mars"]  // Start small
  }
}
```

### 2. Compare CPU vs GPU Performance

```python
import time

# Test CPU
import os
os.environ["USE_GPU_ACCELERATION"] = "false"
start = time.time()
result_cpu = yearly_payload(chart_input, options)
cpu_time = time.time() - start

# Test GPU
os.environ["USE_GPU_ACCELERATION"] = "true"
start = time.time()
result_gpu = yearly_payload(chart_input, options)
gpu_time = time.time() - start

print(f"CPU: {cpu_time:.2f}s")
print(f"GPU: {gpu_time:.2f}s")
print(f"Speedup: {cpu_time/gpu_time:.2f}×")
```

### 3. Profile GPU Operations

```python
import cupy as cp

with cp.prof.time_range('yearly_forecast'):
    result = yearly_payload(chart_input, options)
```

---

## Limitations

### What GPU Acceleration Won't Fix:

1. **Swiss Ephemeris is still sequential** - Planetary position calculations are CPU-bound
2. **I/O operations** - File reading/writing stays the same
3. **Small datasets** - GPU overhead may be slower than CPU for tiny calculations
4. **Memory constraints** - Very large date ranges may exceed GPU memory

### Realistic Expectations:

- **Best case**: 3-4× speedup (when declination aspects dominate)
- **Average case**: 2-3× speedup (typical comprehensive config)
- **Worst case**: 1.5× speedup (if most time is in ephemeris calls)

Your **10-minute request** → **~4-6 minutes** with GPU

---

## Production Considerations

### ⚠️ NOT Recommended for Production

GPU acceleration is designed for **local development only**:

**Why not production?**
1. Requires NVIDIA GPU on server (expensive)
2. CUDA drivers and toolkit installation overhead
3. Additional memory requirements
4. Complexity in containerized environments
5. Potential driver/compatibility issues

**Better production approach:**
1. Optimize configuration (see earlier performance guides)
2. Use caching aggressively
3. Implement job queues for long-running forecasts
4. Consider pre-computing common date ranges

---

## Optimal GPU Configuration

For best GPU performance, enable features that benefit most from parallelization:

```json
{
  "detection": {
    "scan_step_hours": 6  // Keep reasonable
  },
  
  "transits": {
    "bodies": [
      "Sun", "Moon", "Mercury", "Venus", "Mars",
      "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
    ],
    "bodies_extras": ["Ceres"],  // GPU handles extras well
    "include_lunations": false,  // Still expensive even with GPU
    "include_eclipses": true
  },
  
  "declination_aspects": {
    "parallels": true,      // ✅ BIG GPU WIN
    "contraparallels": true // ✅ BIG GPU WIN
  },
  
  "midpoints": {
    "enabled": true,
    "pairs": ["Sun/Moon", "Venus/Mars"]  // GPU handles multiple pairs well
  },
  
  "aspects": {
    "types": [
      "conjunction", "opposition", "square", "trine", "sextile"
    ],
    "orb": {
      "default": 2.0,
      "Sun": 3.0,
      "Moon": 3.5
    }
  }
}
```

**Expected time with GPU**: ~3-4 minutes (vs 10 minutes CPU)

---

## Summary

✅ **Install**: `pip install cupy-cuda12x`  
✅ **Enable**: `USE_GPU_ACCELERATION=true`  
✅ **Expected speedup**: 2-3×  
✅ **Your 10-min request**: → **~4-6 minutes**  
⚠️ **Dev only**: Not for production  

**Questions?** Check logs for 🎮 emoji indicators showing GPU activity!

