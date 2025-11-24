import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.pii_service import PIIService

def test_masking():
    service = PIIService()
    
    text = "My email is test@example.com and phone is 555-0199. Card: 1234 5678 1234 5678"
    print(f"Original: {text}")
    
    masked, mapping = service.mask(text)
    print(f"Masked: {masked}")
    print(f"Mapping: {mapping}")
    
    unmasked = service.unmask(masked, mapping)
    print(f"Unmasked: {unmasked}")
    
    assert "test@example.com" not in masked
    assert "{{EMAIL_1}}" in masked
    assert unmasked == text
    print("Test Passed!")

if __name__ == "__main__":
    test_masking()
