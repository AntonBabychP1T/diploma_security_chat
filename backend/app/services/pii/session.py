from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern, Tuple

from .compat import build_token, parse_token, token_variants
from .engine import PIIEngine
from .types import MatchCandidate

_INCOMPLETE_BARE_V2_RE = re.compile(r"PII:[A-Z0-9_]*(:\d{0,4})?$")
_FLEX_V2_RE = re.compile(r"<<\s*PII\s*:\s*([A-Z0-9_]+)\s*:\s*0*(\d{1,4})\s*>>")
_FLEX_V2_SINGLE_RE = re.compile(r"<\s*PII\s*:\s*([A-Z0-9_]+)\s*:\s*0*(\d{1,4})\s*>")
_FLEX_V2_BARE_RE = re.compile(r"PII\s*:\s*([A-Z0-9_]+)\s*:\s*0*(\d{1,4})")


class PIISession:
    def __init__(
        self,
        engine: Optional[PIIEngine] = None,
        token_format: str = "v2",
        initial_mapping: Optional[Dict[str, str]] = None,
    ):
        self.engine = engine or PIIEngine()
        self.token_format = token_format

        self.token_to_value: Dict[str, str] = {}
        self.value_to_token: Dict[Tuple[str, str], str] = {}
        self.type_counters: Dict[str, int] = {}

        self._tail_buffer = ""
        self._unmask_regex: Optional[Pattern[str]] = None
        self._unmask_lookup: Dict[str, str] = {}

        if initial_mapping:
            self.import_mapping(initial_mapping)

    def import_mapping(self, mapping: Dict[str, str]) -> None:
        for token, original in mapping.items():
            self.token_to_value[token] = original

            parsed = parse_token(token)
            if not parsed:
                continue

            type_name, idx = parsed
            self.type_counters[type_name] = max(self.type_counters.get(type_name, 0), idx)
            self.value_to_token[(type_name, original)] = token

        self._invalidate_unmask_cache()

    def export_mapping(self) -> Dict[str, str]:
        return dict(self.token_to_value)

    def mask_text(self, text: str) -> str:
        if not text:
            return text

        matches = self.engine.select_matches(text)
        if not matches:
            return text

        out: List[str] = []
        cursor = 0
        for match in matches:
            out.append(text[cursor:match.start])
            out.append(self._resolve_token(match))
            cursor = match.end
        out.append(text[cursor:])
        return "".join(out)

    def unmask_text(self, text: str) -> str:
        if not text or not self.token_to_value:
            return text

        self._ensure_unmask_cache()
        if not self._unmask_regex:
            return text
        return self._unmask_regex.sub(
            lambda m: self._unmask_lookup[self._normalize_unmask_key(m.group(0))],
            text,
        )

    def unmask_chunk(self, chunk: str) -> str:
        if not chunk:
            return ""

        combined = self._tail_buffer + chunk
        safe_part, new_tail = self._split_tail(combined)
        self._tail_buffer = new_tail
        return self.unmask_text(safe_part)

    def flush_unmask_tail(self) -> str:
        if not self._tail_buffer:
            return ""
        result = self.unmask_text(self._tail_buffer)
        self._tail_buffer = ""
        return result

    def reset_stream_buffer(self) -> None:
        self._tail_buffer = ""

    def _resolve_token(self, match: MatchCandidate) -> str:
        key = (match.type_name, match.value)
        existing = self.value_to_token.get(key)
        if existing:
            return existing

        next_counter = self.type_counters.get(match.type_name, 0) + 1
        token = build_token(match.type_name, next_counter, self.token_format)

        while token in self.token_to_value and self.token_to_value[token] != match.value:
            next_counter += 1
            token = build_token(match.type_name, next_counter, self.token_format)

        self.type_counters[match.type_name] = next_counter
        self.token_to_value[token] = match.value
        self.value_to_token[key] = token
        self._invalidate_unmask_cache()
        return token

    def _ensure_unmask_cache(self) -> None:
        if self._unmask_regex is not None:
            return

        lookup: Dict[str, str] = {}
        patterns: List[str] = []
        for token, value in self.token_to_value.items():
            for variant in token_variants(token):
                lookup.setdefault(variant, value)

            parsed = parse_token(token)
            if parsed:
                type_name, counter = parsed
                normalized_keys = (
                    f"<<PII:{type_name}:{counter}>>",
                    f"<PII:{type_name}:{counter}>",
                    f"PII:{type_name}:{counter}",
                )
                for key in normalized_keys:
                    lookup.setdefault(key, value)

                escaped_type = re.escape(type_name)
                patterns.extend(
                    [
                        rf"<<\s*PII\s*:\s*{escaped_type}\s*:\s*0*{counter}\s*>>",
                        rf"<\s*PII\s*:\s*{escaped_type}\s*:\s*0*{counter}\s*>",
                        rf"PII\s*:\s*{escaped_type}\s*:\s*0*{counter}",
                    ]
                )

        if not lookup:
            self._unmask_regex = None
            self._unmask_lookup = {}
            return

        keys = sorted(lookup.keys(), key=len, reverse=True)
        patterns.extend(re.escape(item) for item in keys)
        pattern = "|".join(patterns)
        self._unmask_regex = re.compile(pattern)
        self._unmask_lookup = lookup

    def _normalize_unmask_key(self, token: str) -> str:
        compact = re.sub(r"\s+", "", token)

        for regex, template in (
            (_FLEX_V2_RE, "<<PII:{type_name}:{counter}>>"),
            (_FLEX_V2_SINGLE_RE, "<PII:{type_name}:{counter}>"),
            (_FLEX_V2_BARE_RE, "PII:{type_name}:{counter}"),
        ):
            match = regex.fullmatch(compact)
            if match:
                return template.format(type_name=match.group(1), counter=int(match.group(2)))

        return token

    def _invalidate_unmask_cache(self) -> None:
        self._unmask_regex = None
        self._unmask_lookup = {}

    def _split_tail(self, text: str) -> Tuple[str, str]:
        if not text:
            return "", ""

        double_pos = text.rfind("<<")
        if double_pos >= 0 and self._is_incomplete_flexible_v2_suffix(text[double_pos:]):
            return text[:double_pos], text[double_pos:]

        single_pos_flex = text.rfind("<")
        while single_pos_flex > 0 and text[single_pos_flex - 1] == "<":
            single_pos_flex = text.rfind("<", 0, single_pos_flex)
        if single_pos_flex >= 0 and self._is_incomplete_flexible_v2_suffix(text[single_pos_flex:]):
            return text[:single_pos_flex], text[single_pos_flex:]

        bare_pos_flex = text.rfind("PII")
        while bare_pos_flex > 0 and "<" in text[max(0, bare_pos_flex - 4):bare_pos_flex]:
            bare_pos_flex = text.rfind("PII", 0, bare_pos_flex)
        if bare_pos_flex >= 0 and self._is_incomplete_flexible_v2_suffix(text[bare_pos_flex:]):
            return text[:bare_pos_flex], text[bare_pos_flex:]

        bare_pos = text.rfind("PII:")
        while bare_pos >= 1 and text[bare_pos - 1] == "<":
            bare_pos = text.rfind("PII:", 0, bare_pos)

        single_pos = text.rfind("<PII:")
        while single_pos > 0 and text[single_pos - 1] == "<":
            single_pos = text.rfind("<PII:", 0, single_pos)

        split_candidates = [
            (text.rfind("<<PII:"), "v2"),
            (single_pos, "v2_single"),
            (text.rfind("{{"), "v1"),
            (bare_pos, "bare_v2"),
        ]
        split_candidates = [item for item in split_candidates if item[0] >= 0]
        if not split_candidates:
            return text, ""

        pos, marker = max(split_candidates, key=lambda item: item[0])
        suffix = text[pos:]
        if marker == "v2":
            if ">>" in suffix:
                return text, ""
            return text[:pos], suffix

        if marker == "v2_single":
            if ">" in suffix:
                return text, ""
            return text[:pos], suffix

        if marker == "v1":
            if "}}" in suffix:
                return text, ""
            return text[:pos], suffix

        if _INCOMPLETE_BARE_V2_RE.match(suffix):
            return text[:pos], suffix
        return text, ""

    def _is_incomplete_flexible_v2_suffix(self, suffix: str) -> bool:
        compact = re.sub(r"\s+", "", suffix)
        if not compact:
            return False

        if compact.startswith("<<PII"):
            if ">>" in compact:
                return False
            return bool(re.fullmatch(r"<<PII(?::[A-Z0-9_]*)?(?::\d{0,4})?", compact))

        if compact.startswith("<PII"):
            if ">" in compact[1:]:
                return False
            return bool(re.fullmatch(r"<PII(?::[A-Z0-9_]*)?(?::\d{0,4})?", compact))

        if compact.startswith("PII"):
            return bool(re.fullmatch(r"PII(?::[A-Z0-9_]*)?(?::\d{0,4})?", compact))

        return False
