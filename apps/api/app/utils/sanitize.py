# ID: AX90      |  Local: A67Y1         |  Module: X71 (M70)
# Functions: A67Y1F1 A67Y1F2 A67Y1F3 A67Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import html
import re
import unicodedata

_MAX_FIELD_LEN = 500
_MAX_URL_LEN = 2048
_ALLOWED_URL_SCHEMES = frozenset(("https", "http"))
_SLUG_RE = re.compile(r"[^a-z0-9\-_]")


def sanitize_text(value: str, max_len: int = _MAX_FIELD_LEN) -> str:
    """
    A67Y1F1: Strip HTML, normalize Unicode, trim whitespace, truncate.
    Safe for DB insertion and display.
    """
    if not isinstance(value, str):
        value = str(value)
    # Normalize Unicode (NFC)
    value = unicodedata.normalize("NFC", value)
    # Strip HTML
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", "", value)
    # Collapse whitespace
    value = re.sub(r"\s+", " ", value).strip()
    # Truncate
    return value[:max_len]


def sanitize_url(value: str) -> str | None:
    """
    A67Y1F2: Validate URL scheme (https/http only) and length.
    Returns None if invalid.
    """
    if not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) > _MAX_URL_LEN:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(value)
        if parsed.scheme not in _ALLOWED_URL_SCHEMES:
            return None
        if not parsed.netloc:
            return None
        return value
    except Exception:
        return None


def sanitize_username(value: str, provider: str = "twitter") -> str | None:
    """
    A67Y1F3: Validate and normalize social username.
    twitter: strips @ prefix, alphanumeric+underscore, 1-50 chars
    discord: 2-50 chars
    """
    if not isinstance(value, str):
        return None
    value = value.strip()

    if provider == "twitter":
        value = value.lstrip("@")
        if re.fullmatch(r"[A-Za-z0-9_]{1,50}", value):
            return value
        return None

    if provider == "discord":
        if 2 <= len(value) <= 50:
            return value
        return None

    return value[:50] if value else None


def sanitize_wallet(value: str) -> str | None:
    """
    A67Y1F4: Basic wallet address validation.
    Accepts EVM (0x...), Bitcoin, and generic base58/hex addresses.
    """
    if not isinstance(value, str):
        return None
    value = value.strip()

    # EVM
    if re.fullmatch(r"0x[a-fA-F0-9]{40}", value):
        return value
    # Bitcoin legacy/segwit
    if re.fullmatch(r"[13][a-km-zA-HJ-NP-Z1-9]{25,34}", value):
        return value
    # Solana / generic base58
    if re.fullmatch(r"[a-zA-Z0-9]{32,64}", value):
        return value
    return None


def to_slug(value: str) -> str:
    """Convert display name to URL-safe slug."""
    value = unicodedata.normalize("NFC", value).lower()
    value = re.sub(r"\s+", "-", value)
    value = _SLUG_RE.sub("", value)
    return value[:80]
