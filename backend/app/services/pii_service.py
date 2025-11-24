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
        ("EMAIL", r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 0),
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

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Masks PII in the text and returns the masked text and a mapping of tokens to original values.
        """
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
                
                count = len([k for k in mapping.keys() if k.startswith(f"{{{{{type_prefix}")]) + 1
                token = f"{{{{{type_prefix}_{count}}}}}"
                mapping[token] = original
                return f"{prefix}{token}{suffix}"
            else:
                # Mask the whole match
                original = full_match
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
        """
        unmasked_text = text
        # Sort keys by length descending to avoid partial replacements
        for token, original in mapping.items():
            unmasked_text = unmasked_text.replace(token, original)
        
        return unmasked_text
