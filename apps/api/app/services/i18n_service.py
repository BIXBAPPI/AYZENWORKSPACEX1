# ID: AX12      |  Local: A2Y3          |  Module: X03 (M02)
# Functions: A2Y3F1 A2Y3F2 A2Y3F3 A2Y3F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("ayzen.i18n")

_translations: dict[str, dict[str, str]] = {}
_LOCALE_DIR = Path(__file__).parent.parent / "i18n"
_MD2_ESCAPE = re.compile(r"([_*\[\]()~`>#+=|{}.!\\-])")


def load_translations() -> None:
    """Load all locale JSON files into memory at startup."""
    for path in _LOCALE_DIR.glob("*.json"):
        locale = path.stem
        try:
            _translations[locale] = json.loads(path.read_text(encoding="utf-8"))
            logger.info("Loaded i18n locale: %s (%d keys)", locale, len(_translations[locale]))
        except Exception as exc:
            logger.error("Failed to load locale %s: %s", locale, exc)


# XN01  Translation Lookup + Cache
@lru_cache(maxsize=2048)
def t(key: str, locale: str = "bn", **kwargs: Any) -> str:
    """
    Look up translation key for locale; fallback to 'en' if missing;
    format with kwargs. LRU-cached per (key, locale).
    """
    locale_dict = _translations.get(locale, {})
    text = locale_dict.get(key)

    if text is None and locale != "en":
        text = _translations.get("en", {}).get(key)

    if text is None:
        logger.warning("Missing i18n key: %s for locale: %s", key, locale)
        return key

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError) as exc:
            logger.warning("i18n format error key=%s: %s", key, exc)

    return text


# XN02  Locale Registry
def get_active_locales() -> list[str]:
    """Return list of locale codes that have translation files loaded in memory."""
    return list(_translations.keys())


# XN03  Cache Invalidation
def invalidate_cache(locale: str | None = None) -> None:
    """Flush LRU cache for specified locale or all locales if locale=None."""
    t.cache_clear()
    logger.debug("i18n cache invalidated for locale=%s", locale or "ALL")


# XN04  MarkdownV2 Escape Helper
def escape_md(text: str) -> str:
    """
    Escape all Telegram MarkdownV2 special characters:
    _ * [ ] ( ) ~ ` > # + - = | { } . !
    Used in every outgoing Telegram message.
    """
    return _MD2_ESCAPE.sub(r"\\\1", str(text))


# Initialize at import time (also called explicitly during app startup)
load_translations()
