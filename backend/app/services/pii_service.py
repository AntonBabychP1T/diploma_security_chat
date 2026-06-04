import re
from typing import Dict, Match, Optional, Tuple


class PIIService:
    TOKEN_RE = re.compile(r"<([A-Z][A-Z0-9_]*_\d+)>|\{\{([A-Z][A-Z0-9_]*_\d+)\}\}")
    BARE_TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9_]*_\d+$")

    UA_UPPER = "А-ЯІЇЄҐ"
    UA_LOWER = "а-яіїєґ"
    UA_LETTERS = "А-Яа-яІіЇїЄєҐґ"

    UA_NAME_WORD = rf"[{UA_UPPER}][{UA_LOWER}]+(?:[-'’][{UA_UPPER}{UA_LOWER}][{UA_LOWER}]+)*"
    EN_NAME_WORD = r"[A-Z][a-z]+(?:[-'][A-Z]?[a-z]+)*"

    UA_STREET_TYPE = (
        r"(?:вул\.?|вулиця|просп\.?|проспект|бул\.?|бульвар|пров\.?|провулок|"
        r"пл\.?|площа|узвіз|шосе|алея|набережна)"
    )
    UA_LOCALITY = rf"(?:(?:м\.|місто|с\.|село|смт)\s*)?[{UA_UPPER}][{UA_LETTERS}'’.\- ]{{1,40}}"
    UA_STREET_NAME = rf"[{UA_UPPER}A-Z0-9][{UA_LETTERS}A-Za-z0-9'’.\- ]{{1,80}}?"
    UA_BUILDING = rf"(?:буд\.?\s*)?\d+[{UA_LETTERS}A-Za-z]?(?:\s*(?:/|-)\s*\d+[{UA_LETTERS}A-Za-z]?)?"
    UA_APARTMENT = rf"(?:\s*,?\s*(?:кв\.?|квартира|оф\.?|офіс|apt\.?|apartment)\s*\d+[{UA_LETTERS}A-Za-z]?)?"

    # Regex patterns: (Name, Pattern, GroupIndex)
    PATTERNS = [
        # 1. JWT & Tokens
        ("JWT", r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+", 0),
        ("OPENAI_KEY", r"sk-[a-zA-Z0-9]{32,}", 0),
        ("AWS_KEY", r"(?:AKIA|ASIA)[0-9A-Z]{16}", 0),

        # 2. Financial
        ("IBAN", r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", 0),
        ("SWIFT", r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", 0),
        ("CARD", r"\b(?:\d[ -]*?){13,19}\b", 0),

        # 3. Specific IDs
        ("PASSPORT_UA_OLD", r"\b[A-ZА-ЯІЇЄҐ]{2}\d{6}\b", 0),
        ("RNOKPP", r"\b\d{10}\b", 0),
        ("PASSPORT_ID", r"\b\d{9}\b", 0),
        ("EDRPOU", r"\b\d{8}\b", 0),

        # 4. Contact & Location
        ("EMAIL", r"(?i)<[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}>", 0),
        ("EMAIL", r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", 0),
        (
            "PHONE",
            r"(?<!\w)(?:"
            r"\+?380[\s.\-]?\(?\d{2}\)?[\s.\-]?\d{3}[\s.\-]?\d{2}[\s.\-]?\d{2}|"
            r"0\d{2}[\s.\-]?\d{3}[\s.\-]?\d{2}[\s.\-]?\d{2}|"
            r"\+?\d{1,3}[\s.\-]?\(?\d{2,4}\)?(?:[\s.\-]?\d{2,4}){2,4}"
            r")(?!\w)",
            0,
        ),
        (
            "COORDS",
            r"[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?"
            r"(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)",
            0,
        ),

        # 5. Credentials (contextual: capture value only)
        (
            "CREDENTIAL",
            r"(?i)(?:password|passwd|pwd|secret|token|api[_-]?key|login)\s*[:=]\s*"
            r"(?:(?:password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*)?(\S+)",
            1,
        ),

        # 6. Dates and times
        ("DATE", r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2})\b", 0),
        (
            "DATE",
            r"(?i)\b\d{1,2}\s+(?:січня|лютого|березня|квітня|травня|червня|липня|"
            r"серпня|вересня|жовтня|листопада|грудня|january|february|march|april|"
            r"may|june|july|august|september|october|november|december)\s+\d{4}\b",
            0,
        ),
        ("TIME", r"(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?:\s?(?:[AaPp]\.?[Mm]\.?))?(?!\d)", 0),
        ("TIME", r"\b(?:1[0-2]|0?[1-9])\s?(?:[AaPp]\.?[Mm]\.?)\b", 0),

        # 7. Address
        (
            "ADDRESS",
            rf"(?<!\w)(?:(?:{UA_LOCALITY})\s*,\s*)?{UA_STREET_TYPE}\s+"
            rf"{UA_STREET_NAME}\s*,?\s+{UA_BUILDING}{UA_APARTMENT}(?!\w)",
            0,
        ),
        (
            "ADDRESS",
            r"\b\d{1,6}\s+(?:[A-Z][A-Za-z0-9'’.\-]*\s+){1,6}"
            r"(?:St|Street|Ave|Avenue|Road|Rd|Blvd|Boulevard|Lane|Ln|Drive|Dr|Way|Court|Ct)\.?"
            r"(?:\s*(?:Apt|Apartment|Unit|Suite|#)\s*[A-Za-z0-9\-]+)?\b",
            0,
        ),

        # 8. Person names. Keep after addresses so street names are not split into PERSON tokens.
        ("PERSON", rf"(?<![\w<{{]){UA_NAME_WORD}(?:\s+{UA_NAME_WORD}){{1,2}}(?![\w>}}])", 0),
        ("PERSON", rf"(?<![\w<{{]){EN_NAME_WORD}(?:\s+{EN_NAME_WORD}){{1,2}}(?![\w>}}])", 0),
    ]

    def mask(self, text: str, mapping: Optional[Dict[str, str]] = None) -> Tuple[str, Dict[str, str]]:
        """
        Masks PII in the text and returns the masked text and a mapping of tokens to original values.
        Existing mapping values are reused to keep token numbering stable across a conversation.
        """
        if mapping is None:
            mapping = {}
        else:
            self._canonicalize_mapping(mapping)

        masked_text = self._normalize_legacy_tokens(text)
        reserved_tokens = self._reserved_token_bodies(masked_text, mapping)

        def replace_match(match: Match[str], type_prefix: str, group_index: int) -> str:
            full_match = match.group(0)

            if group_index > 0:
                original = match.group(group_index)
                if not original:
                    return full_match
                if self._token_body(original):
                    return full_match

                start, end = match.span(group_index)
                group_start = start - match.start()
                group_end = end - match.start()

                prefix = full_match[:group_start]
                suffix = full_match[group_end:]
                token = self._token_for_value(type_prefix, original, mapping, reserved_tokens)
                return f"{prefix}{token}{suffix}"

            if self._token_body(full_match):
                return full_match

            return self._token_for_value(type_prefix, full_match, mapping, reserved_tokens)

        for type_name, pattern, group_index in self.PATTERNS:
            masked_text = re.sub(pattern, lambda m, t=type_name, g=group_index: replace_match(m, t, g), masked_text)

        return masked_text, mapping

    def unmask(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Restores original values from tokens in the text.
        Handles <EMAIL_1>, legacy {{EMAIL_1}}, and bare EMAIL_1 variants.
        """
        if not text or not mapping:
            return text

        unmasked_text = text
        variants = []

        for token, original in mapping.items():
            body = self._token_body(token)
            if not body:
                variants.append((token, original, False))
                continue

            variants.append((f"{{{{{body}}}}}", original, False))
            variants.append((f"<{body}>", original, False))
            variants.append((body, original, True))

        variants.sort(key=lambda item: len(item[0]), reverse=True)

        for key, original, bare in variants:
            if bare:
                unmasked_text = re.sub(rf"(?<![A-Z0-9_]){re.escape(key)}(?![A-Z0-9_])", original, unmasked_text)
            else:
                unmasked_text = unmasked_text.replace(key, original)

        return unmasked_text

    def _token_for_value(
        self,
        type_prefix: str,
        original: str,
        mapping: Dict[str, str],
        reserved_tokens: set[str],
    ) -> str:
        existing_token = self._existing_token(type_prefix, original, mapping)
        if existing_token:
            return existing_token

        token = self._next_token(type_prefix, mapping, reserved_tokens)
        mapping[token] = original
        reserved_tokens.add(self._token_body(token) or token)
        return token

    def _existing_token(self, type_prefix: str, original: str, mapping: Dict[str, str]) -> Optional[str]:
        prefix = f"{type_prefix}_"
        for token, value in mapping.items():
            body = self._token_body(token)
            if body and body.startswith(prefix) and value == original:
                return f"<{body}>"
        return None

    def _next_token(self, type_prefix: str, mapping: Dict[str, str], reserved_tokens: set[str]) -> str:
        prefix = f"{type_prefix}_"
        numbers = []

        for token in list(mapping.keys()) + list(reserved_tokens):
            body = self._token_body(token) or token
            if not body.startswith(prefix):
                continue
            suffix = body.removeprefix(prefix)
            if suffix.isdigit():
                numbers.append(int(suffix))

        next_number = max(numbers, default=0) + 1
        return f"<{type_prefix}_{next_number}>"

    def _canonicalize_mapping(self, mapping: Dict[str, str]) -> None:
        canonical = {}
        for token, original in mapping.items():
            body = self._token_body(token)
            if body:
                canonical[f"<{body}>"] = original
            else:
                canonical[token] = original

        mapping.clear()
        mapping.update(canonical)

    def _normalize_legacy_tokens(self, text: str) -> str:
        return self.TOKEN_RE.sub(lambda match: f"<{match.group(1) or match.group(2)}>", text)

    def _reserved_token_bodies(self, text: str, mapping: Dict[str, str]) -> set[str]:
        tokens = {match.group(1) or match.group(2) for match in self.TOKEN_RE.finditer(text)}
        for token in mapping:
            body = self._token_body(token)
            if body:
                tokens.add(body)
        return tokens

    def _token_body(self, token: str) -> Optional[str]:
        match = self.TOKEN_RE.fullmatch(token)
        if match:
            return match.group(1) or match.group(2)
        if self.BARE_TOKEN_RE.fullmatch(token):
            return token
        return None
