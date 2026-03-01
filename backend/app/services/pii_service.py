from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

from app.services.pii import PIIEngine, PIISession
from app.services.pii.compat import TOKEN_FORMAT_V1, normalize_token_format


def _to_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


class PIIService:
    """
    Compatibility facade over PIISession/PIIEngine.
    Legacy methods `mask` and `unmask` are preserved.
    """

    def __init__(
        self,
        token_format: Optional[str] = None,
        pii_v2_enabled: Optional[bool] = None,
        contextual_numeric_ids: Optional[bool] = None,
        stream_buffering: Optional[bool] = None,
    ):
        cfg = self._load_settings_flags()

        self.pii_v2_enabled = _to_bool(
            pii_v2_enabled if pii_v2_enabled is not None else cfg.get("PII_V2_ENABLED"),
            True,
        )
        self.contextual_numeric_ids = _to_bool(
            contextual_numeric_ids if contextual_numeric_ids is not None else cfg.get("PII_CONTEXTUAL_NUMERIC_IDS"),
            True,
        )
        self.stream_buffering = _to_bool(
            stream_buffering if stream_buffering is not None else cfg.get("PII_STREAM_BUFFERING"),
            True,
        )

        configured_format = token_format or cfg.get("PII_TOKEN_FORMAT") or "v2"
        resolved_format = normalize_token_format(configured_format)
        if not self.pii_v2_enabled:
            resolved_format = TOKEN_FORMAT_V1
        self.token_format = resolved_format

        self.engine = PIIEngine(contextual_numeric_ids=self.contextual_numeric_ids)

    def create_session(self, mapping: Optional[Dict[str, str]] = None) -> PIISession:
        return PIISession(
            engine=self.engine,
            token_format=self.token_format,
            initial_mapping=mapping,
        )

    def mask(self, text: str, mapping: Dict[str, str] = None) -> Tuple[str, Dict[str, str]]:
        session = self.create_session(mapping=mapping or {})
        masked_text = session.mask_text(text or "")
        return masked_text, session.export_mapping()

    def unmask(self, text: str, mapping: Dict[str, str]) -> str:
        if not text or not mapping:
            return text or ""
        session = self.create_session(mapping=mapping)
        return session.unmask_text(text)

    def _load_settings_flags(self) -> Dict[str, object]:
        # Use Settings when available in app runtime, fallback to env vars for standalone scripts/tests.
        try:
            from app.core.config import get_settings

            settings = get_settings()
            return {
                "PII_V2_ENABLED": getattr(settings, "PII_V2_ENABLED", None),
                "PII_TOKEN_FORMAT": getattr(settings, "PII_TOKEN_FORMAT", None),
                "PII_CONTEXTUAL_NUMERIC_IDS": getattr(settings, "PII_CONTEXTUAL_NUMERIC_IDS", None),
                "PII_STREAM_BUFFERING": getattr(settings, "PII_STREAM_BUFFERING", None),
            }
        except Exception:
            return {
                "PII_V2_ENABLED": os.getenv("PII_V2_ENABLED"),
                "PII_TOKEN_FORMAT": os.getenv("PII_TOKEN_FORMAT"),
                "PII_CONTEXTUAL_NUMERIC_IDS": os.getenv("PII_CONTEXTUAL_NUMERIC_IDS"),
                "PII_STREAM_BUFFERING": os.getenv("PII_STREAM_BUFFERING"),
            }
