import re
from app.services.pii_service import PIIService

def debug_pii():
    pii = PIIService()
    
    # 1. Test Email Regex
    emails = [
        "noreply@tm.openai.com",
        "no-reply@tax-and-invoicing.us-east-1.amazonaws.com",
        "test.email+tag@example.co.uk",
        "<email@inside.brackets>",
        "mailto:email@link.com"
    ]
    
    print("--- Testing Email Regex ---")
    for email in emails:
        masked, _ = pii.mask(email)
        print(f"'{email}' -> '{masked}' (Matched? {'{{' in masked})")

    # 2. Test Unmasking with missing braces
    print("\n--- Testing Unmasking ---")
    mapping = {"{{EMAIL_1}}": "real@email.com"}
    
    # Case A: Correct format
    text_Correct = "Send to {{EMAIL_1}}"
    unmasked_correct = pii.unmask(text_Correct, mapping)
    print(f"Correct: '{text_Correct}' -> '{unmasked_correct}'")
    
    # Case B: Missing braces (Simulation of LLM stripping them)
    text_broken = "Send to EMAIL_1"
    unmasked_broken = pii.unmask(text_broken, mapping)
    print(f"Broken:  '{text_broken}' -> '{unmasked_broken}'")

if __name__ == "__main__":
    debug_pii()
