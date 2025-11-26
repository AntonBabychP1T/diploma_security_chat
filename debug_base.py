import sys
import os

print(f"CWD: {os.getcwd()}")
env_path = os.path.join(os.getcwd(), ".env")
print(f".env exists: {os.path.exists(env_path)}")

# If running from root, add backend to path
if os.path.exists("backend"):
    sys.path.append(os.path.join(os.getcwd(), "backend"))
else:
    # If running from backend, current dir is already in path usually
    pass

print("Importing Base...")
try:
    from app.core.database import Base
    print("✅ Base imported")
except Exception as e:
    print(f"❌ Base import failed: {e}")
    # import traceback
    # traceback.print_exc()
