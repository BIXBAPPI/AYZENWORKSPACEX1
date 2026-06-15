# ID: AX30      |  Local: A13Y1         |  Module: X14 (M13)
# Functions: A13Y1F1 A13Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.help")


async def help_handler(update: dict, ctx: dict) -> None:
    """A13Y1F1: /help — send help message with command list."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")

    text = (
        t("help.main", locale)
        + "\n\n"
        + t("help.commands", locale)
        + "\n\n"
        + t("help.contact_admin", locale)
    )

    keyboard = InlineKeyboards.from_rows([
        [InlineKeyboards.button(t("button.menu", locale), "menu:main")]
    ])

    await client.send_message(chat_id, text, reply_markup=keyboard)
