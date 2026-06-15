# ID: AX27      |  Local: A11Y1         |  Module: X12 (M11)
# Functions: A11Y1F1–A11Y1F12
# Processes: XN01
from __future__ import annotations

from apps.api.app.services.i18n_service import t


class InlineKeyboards:
    """Low-level inline keyboard primitives."""

    # ── Primitives ──────────────────────────────────────────────────────────

    @staticmethod
    def button(text: str, callback_data: str) -> dict:
        """A11Y1F1: Single inline button (callback_data capped at 64 chars)."""
        return {"text": text, "callback_data": callback_data[:64]}

    @staticmethod
    def url_button(text: str, url: str) -> dict:
        """URL-launch button."""
        return {"text": text, "url": url}

    @staticmethod
    def web_app_button(text: str, url: str) -> dict:
        """WebApp launch button."""
        return {"text": text, "web_app": {"url": url}}

    @staticmethod
    def from_rows(rows: list[list[dict]]) -> dict:
        """A11Y1F2: Build InlineKeyboardMarkup from rows of buttons."""
        return {"inline_keyboard": rows}

    # ── Navigation rows ──────────────────────────────────────────────────

    @staticmethod
    def back_menu_row(locale: str = "bn") -> list[dict]:
        """A11Y1F3: [◀ Back] [🏠 Menu] nav row."""
        return [
            InlineKeyboards.button(t("button.back", locale), "menu:back"),
            InlineKeyboards.button(t("button.menu", locale), "menu:main"),
        ]

    @staticmethod
    def back_row(callback: str, locale: str = "bn") -> list[dict]:
        """Single [◀ Back] button row pointing to a specific callback."""
        return [InlineKeyboards.button(t("button.back", locale), callback)]

    @staticmethod
    def menu_row(locale: str = "bn") -> list[dict]:
        """Single [🏠 Menu] row."""
        return [InlineKeyboards.button(t("button.menu", locale), "menu:main")]

    @staticmethod
    def prev_next_row(prefix: str, page: int, has_prev: bool, has_next: bool, locale: str = "bn") -> list[dict]:
        """Pagination prev/next row."""
        row: list[dict] = []
        if has_prev:
            row.append(InlineKeyboards.button(t("button.prev", locale), f"{prefix}:{page - 1}"))
        if has_next:
            row.append(InlineKeyboards.button(t("button.next", locale), f"{prefix}:{page + 1}"))
        return row

    # ── Common keyboards ────────────────────────────────────────────────

    @staticmethod
    def confirm_cancel(locale: str = "bn") -> dict:
        """A11Y1F4: [✅ Confirm] [❌ Cancel]."""
        return InlineKeyboards.from_rows([[
            InlineKeyboards.button(t("button.confirm", locale), "confirm:yes"),
            InlineKeyboards.button(t("button.cancel", locale), "confirm:no"),
        ]])

    @staticmethod
    def menu_only(locale: str = "bn") -> dict:
        """Just [🏠 Menu]."""
        return InlineKeyboards.from_rows([[
            InlineKeyboards.button(t("button.menu", locale), "menu:main")
        ]])

    @staticmethod
    def yes_no(yes_cb: str, no_cb: str, locale: str = "bn") -> dict:
        """[✅ Yes] [❌ No] with custom callbacks."""
        return InlineKeyboards.from_rows([[
            InlineKeyboards.button(t("button.yes", locale), yes_cb),
            InlineKeyboards.button(t("button.no", locale), no_cb),
        ]])

    # ── Analytics ───────────────────────────────────────────────────────

    @staticmethod
    def analytics_period_tabs(active: str, locale: str = "bn") -> dict:
        """A11Y1F5: Period tabs for analytics view (today/week/month/all)."""
        periods = [
            ("today", t("analytics_menu.today", locale)),
            ("week",  t("analytics_menu.week", locale)),
            ("month", t("analytics_menu.month", locale)),
            ("all",   t("analytics_menu.all_time", locale)),
        ]
        row = [
            InlineKeyboards.button(
                f"{'▶ ' if p == active else ''}{label}",
                f"analytics:period:{p}",
            )
            for p, label in periods
        ]
        return InlineKeyboards.from_rows([row, InlineKeyboards.back_menu_row(locale)])

    @staticmethod
    def leaderboard_actions(project_id: str, locale: str = "bn") -> dict:
        """A11Y1F6: Leaderboard — refresh + export row."""
        return InlineKeyboards.from_rows([
            [
                InlineKeyboards.button(t("button.refresh", locale), f"leaderboard:refresh:{project_id}"),
                InlineKeyboards.button(t("button.export_csv", locale), f"leaderboard:export:{project_id}"),
            ],
            InlineKeyboards.back_menu_row(locale),
        ])

    # ── Rewards / Achievements ───────────────────────────────────────────

    @staticmethod
    def badge_detail(badge_id: str, locale: str = "bn") -> dict:
        """A11Y1F7: Badge detail — share button + back."""
        return InlineKeyboards.from_rows([
            [InlineKeyboards.button(t("button.share_badge", locale), f"badge:share:{badge_id}")],
            InlineKeyboards.back_menu_row(locale),
        ])

    @staticmethod
    def milestones_list(milestones: list[dict], locale: str = "bn") -> dict:
        """Milestone list — each as a row showing progress."""
        rows: list[list[dict]] = []
        for m in milestones:
            done = "✅ " if m.get("achieved") else "⏳ "
            label = f"{done}{m['name']} — {m.get('progress', 0)}/{m['target']}"
            rows.append([InlineKeyboards.button(label, f"milestone:{m['id']}")])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    # ── Points / Wallet ─────────────────────────────────────────────────

    @staticmethod
    def points_history_nav(page: int, has_more: bool, locale: str = "bn") -> dict:
        """A11Y1F8: Points history pagination."""
        rows: list[list[dict]] = []
        nav: list[dict] = []
        if page > 0:
            nav.append(InlineKeyboards.button(t("button.prev", locale), f"points:history:{page - 1}"))
        if has_more:
            nav.append(InlineKeyboards.button(t("button.next", locale), f"points:history:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    @staticmethod
    def referral_actions(ref_link: str, locale: str = "bn") -> dict:
        """Referral link share actions."""
        return InlineKeyboards.from_rows([
            [InlineKeyboards.url_button(t("button.share_referral", locale), f"https://t.me/share/url?url={ref_link}")],
            [InlineKeyboards.button(t("button.refresh", locale), "referral:refresh")],
            InlineKeyboards.back_menu_row(locale),
        ])

    # ── Search ──────────────────────────────────────────────────────────

    @staticmethod
    def search_results(tasks: list[dict], query: str, locale: str = "bn") -> dict:
        """A11Y1F9: Search result list keyboard."""
        rows: list[list[dict]] = []
        TYPE_EMOJI = {"twitter": "🐦", "discord": "💬", "onchain": "🔗", "form": "📝", "other": "📋"}
        for task in tasks[:10]:
            emoji = TYPE_EMOJI.get(task.get("task_type", "other"), "📋")
            label = f"{emoji} {task.get('title', '—')[:38]}"
            rows.append([InlineKeyboards.button(label, f"task:{task['id']}")])
        if not tasks:
            rows.append([InlineKeyboards.button(t("search.no_results_btn", locale), "search:new")])
        rows.append([InlineKeyboards.button(t("button.new_search", locale), "search:new")])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    # ── Pins ────────────────────────────────────────────────────────────

    @staticmethod
    def pin_list(pinned_tasks: list[dict], locale: str = "bn") -> dict:
        """A11Y1F10: Pinned task list with unpin option."""
        rows: list[list[dict]] = []
        for task in pinned_tasks:
            rows.append([
                InlineKeyboards.button(f"📌 {task.get('title', '—')[:36]}", f"task:{task['id']}"),
                InlineKeyboards.button("🗑", f"pin:remove:{task['id']}"),
            ])
        if not pinned_tasks:
            rows.append([InlineKeyboards.button(t("pin.empty_btn", locale), "tasks:all")])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    @staticmethod
    def task_detail_actions(
        task_id: str,
        locale: str = "bn",
        target_url: str | None = None,
        is_pinned: bool = False,
        can_pin: bool = True,
    ) -> dict:
        """A11Y1F11: Extended task detail — submit, pin, share, target."""
        rows: list[list[dict]] = []
        rows.append([
            InlineKeyboards.button(t("task.submit_single", locale), f"task_action:single:{task_id}"),
            InlineKeyboards.button(t("task.submit_batch", locale), f"task_action:batch:{task_id}"),
        ])
        if target_url:
            rows.append([InlineKeyboards.url_button(t("task.go_to_target", locale), target_url)])
        pin_label = t("button.unpin", locale) if is_pinned else t("button.pin", locale)
        pin_cb = f"pin:remove:{task_id}" if is_pinned else f"pin:add:{task_id}"
        share_cb = f"task:share:{task_id}"
        row2: list[dict] = []
        if can_pin:
            row2.append(InlineKeyboards.button(pin_label, pin_cb))
        row2.append(InlineKeyboards.button(t("button.share", locale), share_cb))
        if row2:
            rows.append(row2)
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    # ── Admin ───────────────────────────────────────────────────────────

    @staticmethod
    def admin_member_actions(member_id: str, role: str, locale: str = "bn") -> dict:
        """A11Y1F12: Member management actions."""
        rows: list[list[dict]] = []
        if role != "manager":
            rows.append([InlineKeyboards.button(t("admin.promote_manager", locale), f"admin:role:manager:{member_id}")])
        if role != "member":
            rows.append([InlineKeyboards.button(t("admin.demote_member", locale), f"admin:role:member:{member_id}")])
        rows.append([InlineKeyboards.button(t("admin.remove_member", locale), f"admin:remove:{member_id}")])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    @staticmethod
    def admin_export_options(project_id: str, locale: str = "bn") -> dict:
        """Export format selection."""
        return InlineKeyboards.from_rows([
            [
                InlineKeyboards.button(t("export.csv", locale), f"export:csv:{project_id}"),
                InlineKeyboards.button(t("export.pdf", locale), f"export:pdf:{project_id}"),
            ],
            [InlineKeyboards.button(t("button.cancel", locale), "menu:main")],
        ])

    @staticmethod
    def admin_task_quick(task_id: str, locale: str = "bn") -> dict:
        """Quick task actions from admin view."""
        return InlineKeyboards.from_rows([
            [
                InlineKeyboards.button(t("admin.task_edit", locale), f"admin:task:edit:{task_id}"),
                InlineKeyboards.button(t("admin.task_delete", locale), f"admin:task:delete:{task_id}"),
            ],
            InlineKeyboards.back_menu_row(locale),
        ])

    @staticmethod
    def language_picker(current: str) -> dict:
        """Language selection keyboard."""
        langs = [("bn", "বাংলা 🇧🇩"), ("en", "English 🇬🇧"), ("tr", "Türkçe 🇹🇷")]
        rows: list[list[dict]] = []
        for code, label in langs:
            prefix = "✅ " if code == current else ""
            rows.append([InlineKeyboards.button(f"{prefix}{label}", f"settings:lang:{code}")])
        rows.append([InlineKeyboards.button("◀ Back", "menu:back")])
        return InlineKeyboards.from_rows(rows)

    @staticmethod
    def notification_settings(prefs: dict, locale: str = "bn") -> dict:
        """Toggle notification types."""
        items = [
            ("deadline",   t("notif.deadline_label", locale),   "notify:deadline"),
            ("assignment", t("notif.assignment_label", locale),  "notify:assignment"),
            ("broadcast",  t("notif.broadcast_label", locale),   "notify:broadcast"),
            ("digest",     t("notif.digest_label", locale),      "notify:digest"),
        ]
        rows: list[list[dict]] = []
        for key, label, cb in items:
            enabled = prefs.get(key, True)
            icon = "✅" if enabled else "❌"
            rows.append([InlineKeyboards.button(f"{icon} {label}", cb)])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    @staticmethod
    def quiet_hours_picker(locale: str = "bn") -> dict:
        """Quick-select quiet hours windows."""
        windows = [
            ("22:00–08:00", "22:00", "08:00"),
            ("23:00–07:00", "23:00", "07:00"),
            ("00:00–06:00", "00:00", "06:00"),
        ]
        rows: list[list[dict]] = []
        for label, start, end in windows:
            rows.append([InlineKeyboards.button(f"🔕 {label}", f"qh:set:{start}:{end}")])
        rows.append([InlineKeyboards.button(t("settings_menu.quiet_hours_off", locale), "qh:off")])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)
