"""Quick test to check GPU status in the app"""
import os
from dotenv import load_dotenv

print("=" * 60)
print("GPU Status Check")
print("=" * 60)

# Load .env
load_dotenv()

# Check environment variable
use_gpu = os.getenv("USE_GPU_ACCELERATION")
print(f"\n1. Environment Variable:")
print(f"   USE_GPU_ACCELERATION = {use_gpu}")

# Check GPU accelerator
try:
    from api.services.gpu_accelerator import get_accelerator
    acc = get_accelerator()
    info = acc.get_device_info()
    
    print(f"\n2. GPU Accelerator Status:")
    print(f"   GPU Available: {info['gpu_available']}")
    print(f"   Use GPU: {info['use_gpu']}")
    print(f"   Backend: {info['backend']}")
    
    if info['use_gpu']:
        print(f"   Device: {info.get('device_name', 'Unknown')}")
        print(f"   Memory: {info.get('free_memory_gb', 0):.2f}GB / {info.get('total_memory_gb', 0):.2f}GB")
except Exception as e:
    print(f"\n   ERROR: {e}")

# Check if yearly_western_gpu would activate
print(f"\n3. GPU Module Status:")
try:
    from api.services import yearly_western_gpu
    print(f"   GPU_ENABLED: {yearly_western_gpu.GPU_ENABLED}")
    print(f"   USE_GPU: {yearly_western_gpu.USE_GPU}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 60)

if use_gpu == "true" and info.get('use_gpu'):
    print("✅ GPU IS CONFIGURED AND READY")
    print("\nRestart your server to see GPU logs:")
    print("  python -m uvicorn api.app:app --reload --port 8081")
else:
    print("❌ GPU IS NOT ACTIVE")
    if use_gpu != "true":
        print(f"\n   Issue: USE_GPU_ACCELERATION={use_gpu} (should be 'true')")
    if not info.get('use_gpu'):
        print(f"\n   Issue: GPU accelerator not using GPU")

print("=" * 60)

