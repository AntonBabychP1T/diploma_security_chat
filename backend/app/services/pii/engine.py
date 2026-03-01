from __future__ import annotations

import bisect
import re
from typing import List, Sequence, Tuple

from .types import MatchCandidate, PatternSpec

_ISO_COUNTRY_CODES = {
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AR", "AT", "AU", "AZ",
    "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BN", "BO", "BR",
    "BS", "BT", "BW", "BY", "BZ", "CA", "CD", "CF", "CG", "CH", "CI", "CL",
    "CM", "CN", "CO", "CR", "CU", "CV", "CY", "CZ", "DE", "DK", "DM", "DO",
    "DZ", "EC", "EE", "EG", "ES", "ET", "FI", "FJ", "FM", "FR", "GA", "GB",
    "GD", "GE", "GH", "GM", "GN", "GQ", "GR", "GT", "GW", "GY", "HK", "HN",
    "HR", "HT", "HU", "ID", "IE", "IL", "IN", "IQ", "IR", "IS", "IT", "JM",
    "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KR", "KW", "KZ", "LA",
    "LB", "LC", "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC",
    "MD", "ME", "MG", "MK", "ML", "MM", "MN", "MR", "MT", "MU", "MV", "MW",
    "MX", "MY", "MZ", "NA", "NE", "NG", "NI", "NL", "NO", "NP", "NZ", "OM",
    "PA", "PE", "PG", "PH", "PK", "PL", "PT", "PY", "QA", "RO", "RS", "RU",
    "RW", "SA", "SC", "SD", "SE", "SG", "SI", "SK", "SL", "SM", "SN", "SO",
    "SR", "SS", "SV", "SY", "TD", "TG", "TH", "TJ", "TL", "TM", "TN", "TR",
    "TT", "TW", "TZ", "UA", "UG", "US", "UY", "UZ", "VA", "VC", "VE", "VN",
    "YE", "ZA", "ZM", "ZW",
}


def _luhn_valid(value: str) -> bool:
    digits = [int(ch) for ch in value if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    checksum = 0
    parity = len(digits) % 2
    for idx, num in enumerate(digits):
        if idx % 2 == parity:
            num *= 2
            if num > 9:
                num -= 9
        checksum += num
    return checksum % 10 == 0


def _swift_valid(value: str) -> bool:
    if len(value) not in (8, 11):
        return False
    country = value[4:6]
    return country in _ISO_COUNTRY_CODES


class PIIEngine:
    def __init__(self, contextual_numeric_ids: bool = True):
        self.contextual_numeric_ids = contextual_numeric_ids
        self._patterns: List[Tuple[PatternSpec, re.Pattern[str]]] = [
            (spec, re.compile(spec.pattern, spec.flags))
            for spec in self._build_pattern_specs(contextual_numeric_ids)
        ]

    def _build_pattern_specs(self, contextual_numeric_ids: bool) -> Sequence[PatternSpec]:
        numeric_context = contextual_numeric_ids

        return [
            PatternSpec("JWT", r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", priority=100, specificity=100),
            PatternSpec("OPENAI_KEY", r"sk-[A-Za-z0-9_\-]{20,}", priority=95, specificity=95),
            PatternSpec("AWS_KEY", r"(?:AKIA|ASIA)[0-9A-Z]{16}", priority=92, specificity=92),
            PatternSpec("IBAN", r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", priority=85, specificity=86),
            PatternSpec(
                "SWIFT",
                r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",
                priority=84,
                specificity=88,
                value_validator=_swift_valid,
            ),
            PatternSpec("CARD", r"\b(?:\d[ -]*?){13,19}\b", priority=83, specificity=89, value_validator=_luhn_valid),
            PatternSpec("PASSPORT_UA_OLD", r"\b[A-Z]{2}\d{6}\b", priority=75, specificity=80),
            PatternSpec(
                "RNOKPP",
                r"\b\d{10}\b",
                priority=70,
                specificity=70,
                context_keywords=("rnokpp", "inn", "ipn", "tax id") if numeric_context else (),
            ),
            PatternSpec(
                "PASSPORT_ID",
                r"\b\d{9}\b",
                priority=69,
                specificity=69,
                context_keywords=("passport", "id card", "id-card") if numeric_context else (),
            ),
            PatternSpec(
                "EDRPOU",
                r"\b\d{8}\b",
                priority=68,
                specificity=68,
                context_keywords=("edrpou", "company code", "company id", "registration code") if numeric_context else (),
            ),
            PatternSpec(
                "EMAIL",
                r"(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b",
                flags=re.IGNORECASE,
                priority=65,
                specificity=66,
            ),
            PatternSpec("PHONE", r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]\d{3}[-.\s]\d{2,4}\b", priority=64, specificity=63),
            PatternSpec(
                "COORDS",
                r"[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)",
                priority=63,
                specificity=62,
            ),
            PatternSpec(
                "CREDENTIAL",
                r"(?i)(?:password|passwd|pwd|secret|token|api[_-]?key|login)\s*[:=]\s*(\S+)",
                flags=re.IGNORECASE,
                group_index=1,
                priority=62,
                specificity=74,
            ),
            PatternSpec("ADDRESS", r"\b\d+\s+[A-Za-z]+\s+(?:St|Street|Ave|Avenue|Road|Rd|Blvd|Lane|Ln)\b", priority=58, specificity=58),
            PatternSpec(
                "ADDRESS_UA",
                r"\b(?:vul\.|vulytsia|prospekt|bulvar|prov\.)\s+[A-Za-z0-9\-\s]+\b",
                flags=re.IGNORECASE,
                priority=57,
                specificity=57,
            ),
        ]

    def select_matches(self, text: str) -> List[MatchCandidate]:
        if not text:
            return []

        candidates = self._collect_candidates(text)
        if not candidates:
            return []
        return self._resolve_overlaps(candidates)

    def _collect_candidates(self, text: str) -> List[MatchCandidate]:
        collected: List[MatchCandidate] = []
        lower_text = text.lower()

        for spec, pattern in self._patterns:
            for match in pattern.finditer(text):
                try:
                    value = match.group(spec.group_index)
                    start, end = match.span(spec.group_index)
                except IndexError:
                    continue

                if not value or start < 0 or end <= start:
                    continue

                if spec.value_validator and not spec.value_validator(value):
                    continue

                if spec.context_keywords and not self._has_context(lower_text, start, end, spec):
                    continue

                collected.append(
                    MatchCandidate(
                        type_name=spec.type_name,
                        start=start,
                        end=end,
                        value=value,
                        priority=spec.priority,
                        specificity=spec.specificity,
                    )
                )

        return collected

    def _has_context(self, lower_text: str, start: int, end: int, spec: PatternSpec) -> bool:
        left = max(0, start - spec.context_window)
        right = min(len(lower_text), end + spec.context_window)
        window = lower_text[left:right]
        return any(keyword in window for keyword in spec.context_keywords)

    def _resolve_overlaps(self, candidates: Sequence[MatchCandidate]) -> List[MatchCandidate]:
        ranked = sorted(
            candidates,
            key=lambda c: (
                -c.specificity,
                -(c.end - c.start),
                -c.priority,
                c.start,
                c.end,
            ),
        )

        selected: List[MatchCandidate] = []
        intervals: List[Tuple[int, int]] = []
        for candidate in ranked:
            if self._overlaps(intervals, candidate.start, candidate.end):
                continue
            bisect.insort(intervals, (candidate.start, candidate.end))
            selected.append(candidate)

        selected.sort(key=lambda c: c.start)
        return selected

    def _overlaps(self, intervals: Sequence[Tuple[int, int]], start: int, end: int) -> bool:
        idx = bisect.bisect_left(intervals, (start, end))
        if idx > 0 and intervals[idx - 1][1] > start:
            return True
        if idx < len(intervals) and intervals[idx][0] < end:
            return True
        return False
