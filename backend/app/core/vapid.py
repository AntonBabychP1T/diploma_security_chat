import base64
import logging

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)


def _sanitize_base64url(value: str) -> str:
    return "".join(value.strip().split())


def _decode_base64url(value: str) -> bytes:
    padding = "=" * ((4 - (len(value) % 4)) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def is_valid_vapid_public_key(public_key: str | None) -> bool:
    if not public_key:
        return False

    try:
        public_bytes = _decode_base64url(_sanitize_base64url(public_key))
    except Exception:
        return False

    return len(public_bytes) == 65 and public_bytes[0] == 0x04


def derive_vapid_public_key_from_private(private_key: str) -> str:
    private_key_bytes = _decode_base64url(_sanitize_base64url(private_key))
    if len(private_key_bytes) != 32:
        raise ValueError("VAPID private key must decode to 32 bytes.")

    private_value = int.from_bytes(private_key_bytes, byteorder="big")
    private = ec.derive_private_key(private_value, ec.SECP256R1())
    public_bytes = private.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return _encode_base64url(public_bytes)


def resolve_vapid_public_key(
    configured_public_key: str | None,
    private_key: str | None,
) -> str | None:
    if is_valid_vapid_public_key(configured_public_key):
        return _sanitize_base64url(configured_public_key)  # type: ignore[arg-type]

    if not private_key:
        return None

    try:
        derived_key = derive_vapid_public_key_from_private(private_key)
        if configured_public_key:
            logger.warning(
                "Configured VAPID_PUBLIC_KEY is invalid. Using public key derived from VAPID_PRIVATE_KEY."
            )
        return derived_key
    except Exception as exc:
        logger.error("Failed to derive VAPID public key from private key: %s", exc)
        return None
