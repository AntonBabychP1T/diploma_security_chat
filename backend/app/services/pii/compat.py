from __future__ import annotations

import re
from typing import Optional, Set, Tuple

TOKEN_FORMAT_V1 = "v1"
TOKEN_FORMAT_V2 = "v2"

_TOKEN_V1_RE = re.compile(r"^\{\{([A-Z0-9_]+)_(\d+)\}\}$")
_TOKEN_V2_RE = re.compile(r"^<<PII:([A-Z0-9_]+):(\d{1,4})>>$")
_TOKEN_V2_SINGLE_RE = re.compile(r"^<PII:([A-Z0-9_]+):(\d{1,4})>$")
_TOKEN_V1_BARE_RE = re.compile(r"^([A-Z0-9_]+)_(\d+)$")
_TOKEN_V2_BARE_RE = re.compile(r"^PII:([A-Z0-9_]+):(\d{1,4})$")


def normalize_token_format(token_format: Optional[str]) -> str:
    if (token_format or "").strip().lower() == TOKEN_FORMAT_V1:
        return TOKEN_FORMAT_V1
    return TOKEN_FORMAT_V2


def build_token(type_name: str, counter: int, token_format: str) -> str:
    fmt = normalize_token_format(token_format)
    if fmt == TOKEN_FORMAT_V1:
        return f"{{{{{type_name}_{counter}}}}}"
    return f"<<PII:{type_name}:{counter:04d}>>"


def parse_token(token: str) -> Optional[Tuple[str, int]]:
    if not token:
        return None

    match = _TOKEN_V2_RE.match(token)
    if match:
        return match.group(1), int(match.group(2))

    match = _TOKEN_V2_SINGLE_RE.match(token)
    if match:
        return match.group(1), int(match.group(2))

    match = _TOKEN_V1_RE.match(token)
    if match:
        return match.group(1), int(match.group(2))

    match = _TOKEN_V2_BARE_RE.match(token)
    if match:
        return match.group(1), int(match.group(2))

    match = _TOKEN_V1_BARE_RE.match(token)
    if match:
        return match.group(1), int(match.group(2))

    return None


def token_variants(token: str) -> Set[str]:
    variants = {token}
    parsed = parse_token(token)
    if not parsed:
        return variants

    type_name, counter = parsed
    variants.add(f"{{{{{type_name}_{counter}}}}}")
    variants.add(f"{type_name}_{counter}")
    variants.add(f"<<PII:{type_name}:{counter:04d}>>")
    variants.add(f"<PII:{type_name}:{counter:04d}>")
    variants.add(f"PII:{type_name}:{counter:04d}")
    return variants
