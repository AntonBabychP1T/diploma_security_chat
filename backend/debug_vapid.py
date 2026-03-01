from dotenv import load_dotenv
import os
import base64

load_dotenv()

pub = os.getenv("VAPID_PUBLIC_KEY")
if not pub:
    print("VAPID_PUBLIC_KEY not found in .env")
else:
    print(f"Raw string length: {len(pub)}")
    print(f"Raw string: '{pub}'")
    
    # Try decoding
    try:
        # Simulate frontend logic
        base64_string = pub.strip()
        padding = "=" * ((4 - (len(base64_string) % 4)) % 4)
        base64_full = (base64_string + padding).replace("-", "+").replace("_", "/")
        decoded = base64.b64decode(base64_full)
        print(f"Decoded bytes length: {len(decoded)}")
        print(f"First byte: {decoded[0] if len(decoded) > 0 else 'None'}")
    except Exception as e:
        print(f"Decoding failed: {e}")
