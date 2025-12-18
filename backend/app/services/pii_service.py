import re
from typing import Tuple, Dict, List

class PIIService:
    # Regex patterns: (Name, Pattern, GroupIndex)
    PATTERNS = [
        # 1. JWT & Tokens
        ("JWT", r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+', 0),
        ("OPENAI_KEY", r'sk-[a-zA-Z0-9]{32,}', 0),
        ("AWS_KEY", r'(?:AKIA|ASIA)[0-9A-Z]{16}', 0),
        
        # 2. Financial
        ("IBAN", r'\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b', 0),
        ("SWIFT", r'\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b', 0), # Non-capturing group
        ("CARD", r'\b(?:\d[ -]*?){13,19}\b', 0),
        
        # 3. Specific IDs (Prioritize over generic Phone/Email)
        ("PASSPORT_UA_OLD", r'\b[A-Z]{2}\d{6}\b', 0),
        ("RNOKPP", r'\b\d{10}\b', 0),
        ("PASSPORT_ID", r'\b\d{9}\b', 0),
        ("EDRPOU", r'\b\d{8}\b', 0),
        
        # 4. Contact & Location
        ("EMAIL", r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', 0),
        ("PHONE", r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', 0),
        ("COORDS", r'[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)', 0),
        
        # 5. Credentials (Contextual - capture value only)
        ("CREDENTIAL", r'(?i)(?:password|passwd|pwd|secret|token|api[_-]?key|login)\s*[:=]\s*(\S+)', 1),
        
        # 6. Address
        ("ADDRESS", r'\b\d+\s+[A-Za-z]+\s+(?:St|Street|Ave|Avenue|Road|Rd|Blvd|Lane|Ln)\b', 0),
        ("ADDRESS_UA", r'\b(?:вул\.|вулиця|просп\.|проспект|бул\.|бульвар|пров\.|провулок)\s+[А-Яа-яIiЇїЄє0-9\-\s]+\b', 0),
    ]

    def __init__(self):
        pass

    def mask(self, text: str, mapping: Dict[str, str] = None) -> Tuple[str, Dict[str, str]]:
        """
        Masks PII in the text and returns the masked text and a mapping of tokens to original values.
        If a mapping is provided, it uses it to maintain consistent token numbering and returns the updated mapping.
        """
        if mapping is None:
            mapping = {}
        
        masked_text = text

        # Helper to replace and store mapping
        def replace_match(match, type_prefix, group_index):
            full_match = match.group(0)
            
            if group_index > 0:
                # We want to mask only a specific group
                original = match.group(group_index)
                if not original: # Optional group might be None
                    return full_match
                
                # Find where the group is within the full match
                start, end = match.span(group_index)
                g_start = start - match.start()
                g_end = end - match.start()
                
                prefix = full_match[:g_start]
                suffix = full_match[g_end:]
                
                # Check if this exact value is already mapped (deduplication)
                existing_token = next((k for k, v in mapping.items() if v == original and k.startswith(f"{{{{{type_prefix}")), None)
                if existing_token:
                    return f"{prefix}{existing_token}{suffix}"

                count = len([k for k in mapping.keys() if k.startswith(f"{{{{{type_prefix}")]) + 1
                token = f"{{{{{type_prefix}_{count}}}}}"
                mapping[token] = original
                return f"{prefix}{token}{suffix}"
            else:
                # Mask the whole match
                original = full_match
                
                # Check dedup
                existing_token = next((k for k, v in mapping.items() if v == original and k.startswith(f"{{{{{type_prefix}")), None)
                if existing_token:
                    return existing_token

                count = len([k for k in mapping.keys() if k.startswith(f"{{{{{type_prefix}")]) + 1
                token = f"{{{{{type_prefix}_{count}}}}}"
                mapping[token] = original
                return token

        for type_name, pattern, group_index in self.PATTERNS:
            masked_text = re.sub(pattern, lambda m, t=type_name, g=group_index: replace_match(m, t, g), masked_text)

        return masked_text, mapping

    def unmask(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Restores original values from tokens in the text.
        Handles cases where LLM might have stripped braces (e.g. EMAIL_1 instead of {{EMAIL_1}}).
        """
        unmasked_text = text
        
        # Sort keys by length descending to avoid partial replacements (longer tokens first)
        # We also want to handle bare tokens, so we generate them too
        
        # Create a extended mapping with bare keys
        extended_mapping = []
        for token, original in mapping.items():
            extended_mapping.append((token, original))
            # Extract content inside {{...}}
            if token.startswith("{{") and token.endswith("}}"):
                bare_token = token[2:-2] # e.g. EMAIL_1
                extended_mapping.append((bare_token, original))
        
        # Sort by key length descending
        extended_mapping.sort(key=lambda x: len(x[0]), reverse=True)
        
        for key, original in extended_mapping:
            # We use distinct checks to avoid replacing substrings incorrectly if possible,
            # but for EMAIL_1 it is usually safe.
            if key in unmasked_text:
                unmasked_text = unmasked_text.replace(key, original)
        
        return unmasked_text
