# ID: AX26      |  Local: A10Y1         |  Module: X11 (M10)
# Functions: A10Y1F1 A10Y1F2 A10Y1F3 A10Y1F4 A10Y1F5 A10Y1F6 A10Y1F7 A10Y1F8
# Processes: XN01 XN02
from __future__ import annotations

from apps.api.app.services.i18n_service import t


class ReplyKeyboards:
    """Persistent bottom reply keyboards for AYZEN bot."""

    # ── Main Menu ────────────────────────────────────────────────────────────

    @staticmethod
    def main_menu(locale: str = "bn", is_admin: bool = False) -> dict:
        """
        A10Y1F1: Main menu keyboard — 5-row advanced layout.
        Row 1: 📋 Tasks        | 📊 Analytics
        Row 2: 💰 Points       | 🏆 Rewards
        Row 3: 🔍 Search       | 📌 Pinned
        Row 4: 👤 Profile      | ⚙️ Settings
        [Admin] 🛠 Admin Panel
        """
        keyboard = [
            [
                {"text": t("menu.tasks", locale)},
                {"text": t("menu.analytics", locale)},
            ],
            [
                {"text": t("menu.points", locale)},
                {"text": t("menu.rewards", locale)},
            ],
            [
                {"text": t("menu.search", locale)},
                {"text": t("menu.pinned", locale)},
            ],
            [
                {"text": t("menu.profile", locale)},
                {"text": t("menu.settings", locale)},
            ],
        ]
        if is_admin:
            keyboard.append([{"text": t("menu.admin", locale)}])
        return {
            "keyboard": keyboard,
            "resize_keyboard": True,
            "persistent": True,
        }

    # ── Sub-menus ─────────────────────────────────────────────────────────

    @staticmethod
    def tasks_submenu(locale: str = "bn") -> dict:
        """A10Y1F2: Tasks sub-menu — filter by type / deadline."""
        keyboard = [
            [
                {"text": t("tasks_menu.all", locale)},
                {"text": t("tasks_menu.deadline_soon", locale)},
            ],
            [
                {"text": t("tasks_menu.twitter", locale)},
                {"text": t("tasks_menu.discord", locale)},
            ],
            [
                {"text": t("tasks_menu.onchain", locale)},
                {"text": t("tasks_menu.form", locale)},
            ],
            [{"text": t("button.back_main", locale)}],
        ]
        return {"keyboard": keyboard, "resize_keyboard": True, "persistent": True}

    @staticmethod
    def analytics_submenu(locale: str = "bn") -> dict:
        """A10Y1F3: Analytics sub-menu."""
        keyboard = [
            [
                {"text": t("analytics_menu.today", locale)},
                {"text": t("analytics_menu.week", locale)},
            ],
            [
                {"text": t("analytics_menu.month", locale)},
                {"text": t("analytics_menu.all_time", locale)},
            ],
            [{"text": t("analytics_menu.leaderboard", locale)}],
            [{"text": t("button.back_main", locale)}],
        ]
        return {"keyboard": keyboard, "resize_keyboard": True, "persistent": True}

    @staticmethod
    def points_submenu(locale: str = "bn") -> dict:
        """A10Y1F4: Points / wallet sub-menu."""
        keyboard = [
            [
                {"text": t("points_menu.balance", locale)},
                {"text": t("points_menu.history", locale)},
            ],
            [
                {"text": t("points_menu.breakdown", locale)},
                {"text": t("points_menu.referral", locale)},
            ],
            [{"text": t("button.back_main", locale)}],
        ]
        return {"keyboard": keyboard, "resize_keyboard": True, "persistent": True}

    @staticmethod
    def rewards_submenu(locale: str = "bn") -> dict:
        """A10Y1F5: Rewards / badges sub-menu."""
        keyboard = [
            [
                {"text": t("rewards_menu.badges", locale)},
                {"text": t("rewards_menu.milestones", locale)},
            ],
            [
                {"text": t("rewards_menu.streak", locale)},
                {"text": t("rewards_menu.top_earners", locale)},
            ],
            [{"text": t("button.back_main", locale)}],
        ]
        return {"keyboard": keyboard, "resize_keyboard": True, "persistent": True}

    @staticmethod
    def settings_submenu(locale: str = "bn") -> dict:
        """A10Y1F6: Settings sub-menu."""
        keyboard = [
            [
                {"text": t("settings_menu.language", locale)},
                {"text": t("settings_menu.notifications", locale)},
            ],
            [
                {"text": t("settings_menu.quiet_hours", locale)},
                {"text": t("settings_menu.slots", locale)},
            ],
            [{"text": t("settings_menu.unlink", locale)}],
            [{"text": t("button.back_main", locale)}],
        ]
        return {"keyboard": keyboard, "resize_keyboard": True, "persistent": True}

    @staticmethod
    def admin_submenu(locale: str = "bn") -> dict:
        """A10Y1F7: Admin sub-menu."""
        keyboard = [
            [
                {"text": t("admin_menu.members", locale)},
                {"text": t("admin_menu.new_task", locale)},
            ],
            [
                {"text": t("admin_menu.broadcast", locale)},
                {"text": t("admin_menu.exports", locale)},
            ],
            [
                {"text": t("admin_menu.analytics", locale)},
                {"text": t("admin_menu.project_settings", locale)},
            ],
            [{"text": t("admin_menu.transfer_ownership", locale)}],
            [{"text": t("button.back_main", locale)}],
        ]
        return {"keyboard": keyboard, "resize_keyboard": True, "persistent": True}

    # ── Utilities ─────────────────────────────────────────────────────────

    @staticmethod
    def remove() -> dict:
        """Remove reply keyboard."""
        return {"remove_keyboard": True}

    @staticmethod
    def cancel_only(locale: str = "bn") -> dict:
        """Cancel-only keyboard (for wizards)."""
        return {
            "keyboard": [[{"text": t("wizard.cancel", locale)}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        }

    @staticmethod
    def back_and_cancel(locale: str = "bn") -> dict:
        """Back + Cancel row (for multi-step wizards)."""
        return {
            "keyboard": [[
                {"text": t("wizard.back", locale)},
                {"text": t("wizard.cancel", locale)},
            ]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        }

    @staticmethod
    def match_menu_text(text: str, locale: str = "bn") -> str | None:
        """
        A10Y1F8: Match user text to a menu/sub-menu button.
        Returns action key or None.
        """
        menu_map: dict[str, str] = {
            # Main menu
            t("menu.tasks", locale):     "tasks",
            t("menu.analytics", locale): "analytics",
            t("menu.points", locale):    "points",
            t("menu.rewards", locale):   "rewards",
            t("menu.search", locale):    "search",
            t("menu.pinned", locale):    "pinned",
            t("menu.profile", locale):   "profile",
            t("menu.settings", locale):  "settings",
            t("menu.admin", locale):     "admin",
            # Tasks sub
            t("tasks_menu.all", locale):           "tasks:all",
            t("tasks_menu.deadline_soon", locale): "tasks:deadline",
            t("tasks_menu.twitter", locale):       "tasks:twitter",
            t("tasks_menu.discord", locale):       "tasks:discord",
            t("tasks_menu.onchain", locale):       "tasks:onchain",
            t("tasks_menu.form", locale):          "tasks:form",
            # Analytics sub
            t("analytics_menu.today", locale):       "analytics:today",
            t("analytics_menu.week", locale):        "analytics:week",
            t("analytics_menu.month", locale):       "analytics:month",
            t("analytics_menu.all_time", locale):    "analytics:all_time",
            t("analytics_menu.leaderboard", locale): "analytics:leaderboard",
            # Points sub
            t("points_menu.balance", locale):   "points:balance",
            t("points_menu.history", locale):   "points:history",
            t("points_menu.breakdown", locale): "points:breakdown",
            t("points_menu.referral", locale):  "points:referral",
            # Rewards sub
            t("rewards_menu.badges", locale):      "rewards:badges",
            t("rewards_menu.milestones", locale):  "rewards:milestones",
            t("rewards_menu.streak", locale):      "rewards:streak",
            t("rewards_menu.top_earners", locale): "rewards:top_earners",
            # Settings sub
            t("settings_menu.language", locale):      "settings:language",
            t("settings_menu.notifications", locale): "settings:notifications",
            t("settings_menu.quiet_hours", locale):   "settings:quiet_hours",
            t("settings_menu.slots", locale):         "settings:slots",
            t("settings_menu.unlink", locale):        "settings:unlink",
            # Admin sub
            t("admin_menu.members", locale):            "admin:members",
            t("admin_menu.new_task", locale):           "admin:new_task",
            t("admin_menu.broadcast", locale):          "admin:broadcast",
            t("admin_menu.exports", locale):            "admin:exports",
            t("admin_menu.analytics", locale):          "admin:analytics",
            t("admin_menu.project_settings", locale):   "admin:project_settings",
            t("admin_menu.transfer_ownership", locale): "admin:transfer",
            # Globals
            t("button.back_main", locale): "back_main",
            t("wizard.cancel", locale):    "cancel",
            t("wizard.back", locale):      "wizard_back",
        }
        return menu_map.get(text)
