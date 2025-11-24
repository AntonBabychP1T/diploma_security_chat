import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.services.pii_service import PIIService

def test_pii_expansion():
    service = PIIService()
    
    test_cases = [
        ("My INN is 1234567890", "RNOKPP"),
        ("Company EDRPOU: 12345678", "EDRPOU"),
        ("Passport: AA123456", "PASSPORT_UA_OLD"),
        ("ID Card: 123456789", "PASSPORT_ID"),
        ("IBAN: UA123456789012345678901234567", "IBAN"),
        ("SWIFT: BANKUA2X", "SWIFT"),
        ("Location: 50.4501, 30.5234", "COORDS"),
        ("API Key: sk-1234567890abcdef1234567890abcdef1234567890abcdef", "OPENAI_KEY"),
        ("Login: password: mysecretpassword123", "CREDENTIAL"),
        ("Address: вул. Хрещатик 1", "ADDRESS_UA"),
        ("JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", "JWT")
    ]
    
    print("Testing PII Expansion...")
    for text, expected_type in test_cases:
        masked, mapping = service.mask(text)
        print(f"\nOriginal: {text}")
        print(f"Masked:   {masked}")
        print(f"Mapping:  {mapping}")
        
        # Check if masked
        if "{{" + expected_type in masked:
            print(f"✅ Detected {expected_type}")
        else:
            print(f"❌ Failed to detect {expected_type}")
            
        # Check unmasking
        unmasked = service.unmask(masked, mapping)
        if unmasked == text:
            print("✅ Unmasking successful")
        else:
            print(f"❌ Unmasking failed: {unmasked}")

if __name__ == "__main__":
    test_pii_expansion()
