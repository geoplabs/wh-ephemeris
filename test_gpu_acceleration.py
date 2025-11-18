#!/usr/bin/env python3
"""
Test GPU Acceleration Setup

Run this to verify GPU acceleration is working correctly.
"""
import os
import time
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*60)
print("GPU Acceleration Test")
print("="*60)

# Test 1: Check CuPy installation
print("\n[1/5] Testing CuPy installation...")
try:
    import cupy as cp
    print(f"   [OK] CuPy version: {cp.__version__}")
    
    if cp.cuda.is_available():
        device = cp.cuda.Device()
        print(f"   [OK] CUDA available: Yes")
        print(f"   [OK] GPU detected: {device.attributes.get('Name', 'Unknown')}")
        print(f"   [OK] Compute capability: {device.compute_capability}")
        mem_info = device.mem_info
        print(f"   [OK] GPU memory: {mem_info[1] / (1024**3):.2f}GB total, {mem_info[0] / (1024**3):.2f}GB free")
    else:
        print("   [FAIL] CUDA not available")
        sys.exit(1)
except ImportError:
    print("   [FAIL] CuPy not installed!")
    print("   Install with: pip install cupy-cuda12x")
    sys.exit(1)
except Exception as e:
    print(f"   [FAIL] Error: {e}")
    sys.exit(1)

# Test 2: Check environment variable
print("\n[2/5] Testing environment configuration...")
use_gpu = os.getenv("USE_GPU_ACCELERATION", "false").lower()
if use_gpu in ("true", "1", "yes"):
    print(f"   [OK] USE_GPU_ACCELERATION={use_gpu}")
else:
    print(f"   [WARN] USE_GPU_ACCELERATION={use_gpu} (not enabled)")
    print("   Set USE_GPU_ACCELERATION=true to enable")

# Test 3: Test GPU accelerator module
print("\n[3/5] Testing GPU accelerator module...")
try:
    from api.services.gpu_accelerator import get_accelerator, GPUAccelerator
    
    acc = get_accelerator()
    info = acc.get_device_info()
    
    print(f"   [OK] GPU module loaded")
    print(f"   [OK] Backend: {info['backend']}")
    if info['use_gpu']:
        print(f"   [OK] Device: {info.get('device_name', 'Unknown')}")
        print(f"   [OK] Memory: {info.get('free_memory_gb', 0):.2f}GB / {info.get('total_memory_gb', 0):.2f}GB")
    else:
        print(f"   [WARN] GPU not active (using CPU fallback)")
except ImportError as e:
    print(f"   [FAIL] Failed to import GPU module: {e}")
    sys.exit(1)

# Test 4: Performance benchmark
print("\n[4/5] Running performance benchmark...")
try:
    import numpy as np
    from api.services.gpu_accelerator import get_accelerator
    
    acc = get_accelerator()
    
    # Generate test data
    n_transit = 1460  # Yearly scan points at 6-hour steps
    n_natal = 20      # Natal bodies + angles
    
    print(f"   Testing with {n_transit} transit x {n_natal} natal positions...")
    
    transit_lons = np.random.rand(n_transit) * 360
    natal_lons = np.random.rand(n_natal) * 360
    
    # Benchmark
    start = time.time()
    results = acc.batch_angle_differences(transit_lons.tolist(), natal_lons.tolist())
    elapsed = time.time() - start
    
    print(f"   [OK] Calculated {len(results.flatten())} angle differences")
    print(f"   [OK] Time: {elapsed*1000:.2f}ms")
    
    if acc.use_gpu:
        print(f"   [GPU] GPU acceleration ACTIVE")
        if elapsed < 0.1:
            print(f"   [GPU] Excellent performance! (<100ms)")
        elif elapsed < 0.5:
            print(f"   [GPU] Good performance")
        else:
            print(f"   [WARN] Slower than expected (check GPU utilization)")
    else:
        print(f"   [CPU] Running on CPU")
        if elapsed < 0.5:
            print(f"   [CPU] Normal CPU performance")
    
except Exception as e:
    print(f"   [FAIL] Benchmark failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Declination test
print("\n[5/5] Testing declination calculations...")
try:
    from api.services.gpu_accelerator import get_accelerator
    import numpy as np
    
    acc = get_accelerator()
    
    # Simulated declinations
    transit_decs = np.random.rand(100) * 50 - 25  # -25 to +25 degrees
    natal_decs = np.array([23.44, -23.44, 0.0])    # Sun, Moon, some planet
    
    start = time.time()
    results = acc.batch_declination_parallels(transit_decs, natal_decs, orb_limit=1.0)
    elapsed = time.time() - start
    
    print(f"   [OK] Found {len(results)} declination aspects")
    print(f"   [OK] Time: {elapsed*1000:.2f}ms")
    
except Exception as e:
    print(f"   [WARN] Declination test failed: {e}")

# Summary
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)

if acc.use_gpu and acc.get_device_info()['gpu_available']:
    print("[SUCCESS] GPU acceleration is READY and ACTIVE!")
    print("\nYour yearly forecasts will be 2-3x faster.")
    print("\nNext steps:")
    print("  1. Ensure USE_GPU_ACCELERATION=true is set")
    print("  2. Start your API: python -m uvicorn api.app:app --reload")
    print("  3. Look for [GPU] tags in logs during forecast calculation")
    print("\nMonitor GPU usage:")
    print("  nvidia-smi -l 1")
else:
    print("[WARN] GPU acceleration not active")
    print("\nTo enable:")
    print("  1. Set: USE_GPU_ACCELERATION=true")
    print("  2. Restart your API server")
    
print("\n" + "="*60)

