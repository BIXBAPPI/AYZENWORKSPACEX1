# ID: AX28      |  Local: A11Y2         |  Module: X12 (M11)
# Functions: A11Y2F1–A11Y2F10
# Processes: XN01
from __future__ import annotations

from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards
from apps.api.app.services.i18n_service import t

PAGE_SIZE = 8
TASK_PAGE_SIZE = 6


class KeyboardBuilders:
    """Higher-level paginated and contextual keyboard builders."""

    # ── Pagination helper ────────────────────────────────────────────────

    @staticmethod
    def _paginate(
        items: list[dict],
        page: int,
        page_size: int,
        prefix: str,
        locale: str,
        label_fn,
        id_key: str = "id",
        nav_prefix: str | None = None,
    ) -> dict:
        total = len(items)
        start = page * page_size
        end = start + page_size
        page_items = items[start:end]
        nav_prefix = nav_prefix or prefix + "_page"

        rows: list[list[dict]] = []
        for item in page_items:
            rows.append([InlineKeyboards.button(label_fn(item), f"{prefix}:{item[id_key]}")])

        nav = InlineKeyboards.prev_next_row(nav_prefix, page, page > 0, end < total, locale)
        if nav:
            rows.append(nav)

        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    # ── Standard lists ───────────────────────────────────────────────────

    @staticmethod
    def project_list(projects: list[dict], page: int, locale: str = "bn") -> dict:
        """A11Y2F1: Paginated project list."""
        return KeyboardBuilders._paginate(
            items=projects,
            page=page,
            page_size=PAGE_SIZE,
            prefix="project",
            locale=locale,
            label_fn=lambda p: f"📁 {p.get('name', '—')[:40]}",
            nav_prefix="proj_page",
        )

    @staticmethod
    def task_list(tasks: list[dict], page: int, locale: str = "bn", filter_tag: str = "") -> dict:
        """A11Y2F2: Paginated task list with type emoji."""
        TYPE_EMOJI = {
            "twitter": "🐦", "discord": "💬",
            "onchain": "🔗", "form": "📝", "other": "📋",
        }
        deadline_marker = " ⚠️"

        def label(task: dict) -> str:
            import datetime
            emoji = TYPE_EMOJI.get(task.get("task_type", "other"), "📋")
            title = task.get("title", "—")[:36]
            suffix = ""
            if task.get("deadline"):
                try:
                    dl = datetime.datetime.fromisoformat(str(task["deadline"]))
                    if dl - datetime.datetime.utcnow() < datetime.timedelta(hours=24):
                        suffix = deadline_marker
                except Exception:
                    pass
            return f"{emoji} {title}{suffix}"

        total = len(tasks)
        start = page * TASK_PAGE_SIZE
        end = start + TASK_PAGE_SIZE
        page_items = tasks[start:end]

        rows: list[list[dict]] = []
        cb_prefix = f"task_filter:{filter_tag}" if filter_tag else "task"
        for task in page_items:
            rows.append([InlineKeyboards.button(label(task), f"task:{task['id']}")])

        nav = InlineKeyboards.prev_next_row(
            f"task_page:{filter_tag}" if filter_tag else "task_page",
            page, page > 0, end < total, locale,
        )
        if nav:
            rows.append(nav)

        # Filter shortcut row
        rows.append([
            InlineKeyboards.button(t("button.filter", locale), "task_filter:open"),
            InlineKeyboards.button(t("button.search_tasks", locale), "search:new"),
        ])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    @staticmethod
    def member_list(members: list[dict], page: int, locale: str = "bn") -> dict:
        """A11Y2F3: Admin member list."""
        ROLE_EMOJI = {"owner": "👑", "manager": "🔑", "member": "👤"}

        def label(m: dict) -> str:
            role_icon = ROLE_EMOJI.get(m.get("role", "member"), "👤")
            name = m.get("display_name") or m.get("telegram_username") or str(m.get("id", ""))
            pts = m.get("total_points", 0)
            return f"{role_icon} {name[:28]} · {pts}pts"

        return KeyboardBuilders._paginate(
            items=members, page=page, page_size=PAGE_SIZE,
            prefix="admin_member", locale=locale, label_fn=label,
            nav_prefix="member_page",
        )

    # ── Batch / Slot pickers ─────────────────────────────────────────────

    @staticmethod
    def batch_toggle(
        items: list[dict],
        selected_ids: list[str],
        prefix: str,
        locale: str = "bn",
        label_key: str = "slot_name",
        id_key: str = "id",
    ) -> dict:
        """A11Y2F4: Batch checkbox selection keyboard."""
        rows: list[list[dict]] = []
        for item in items:
            item_id = str(item[id_key])
            is_sel = item_id in selected_ids
            label = ("☑ " if is_sel else "☐ ") + str(item.get(label_key, item_id))
            rows.append([InlineKeyboards.button(label, f"{prefix}toggle:{item_id}")])

        rows.append([
            InlineKeyboards.button(t("submit.select_all", locale), f"{prefix}select_all"),
            InlineKeyboards.button(t("submit.clear", locale), f"{prefix}clear"),
        ])
        if selected_ids:
            confirm_label = t("submit.confirm", locale, count=len(selected_ids))
            rows.append([InlineKeyboards.button(confirm_label, f"{prefix}confirm")])

        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    @staticmethod
    def slot_picker(
        slots: list[dict],
        task_id: str,
        locale: str = "bn",
        submitted_ids: list[str] | None = None,
    ) -> dict:
        """A11Y2F5: Single-submit slot picker."""
        submitted_ids = submitted_ids or []
        rows: list[list[dict]] = []
        for slot in slots:
            slot_id = str(slot["id"])
            done = slot_id in submitted_ids
            icon = "✅ " if done else "🔘 "
            label = f"{icon}{slot.get('slot_name', slot_id)}"
            cb = "submit:already_done" if done else f"submit:{task_id}:{slot_id}"
            rows.append([InlineKeyboards.button(label, cb)])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    # ── Analytics ────────────────────────────────────────────────────────

    @staticmethod
    def analytics_chart(stats: dict, period: str, locale: str = "bn") -> dict:
        """A11Y2F6: Analytics detail view — chart period tabs + export."""
        return InlineKeyboards.from_rows([
            [
                InlineKeyboards.button(t("analytics_menu.today", locale),    "analytics:period:today"),
                InlineKeyboards.button(t("analytics_menu.week", locale),     "analytics:period:week"),
                InlineKeyboards.button(t("analytics_menu.month", locale),    "analytics:period:month"),
            ],
            [
                InlineKeyboards.button(t("button.export_csv", locale),       f"analytics:export:{period}"),
                InlineKeyboards.button(t("button.refresh", locale),          f"analytics:refresh:{period}"),
            ],
            InlineKeyboards.back_menu_row(locale),
        ])

    # ── Task Filters ─────────────────────────────────────────────────────

    @staticmethod
    def task_filter_menu(active_filter: str, locale: str = "bn") -> dict:
        """A11Y2F7: Task filter selection panel."""
        filters = [
            ("all",      t("tasks_menu.all", locale),           "📋"),
            ("deadline", t("tasks_menu.deadline_soon", locale), "⏰"),
            ("twitter",  t("tasks_menu.twitter", locale),       "🐦"),
            ("discord",  t("tasks_menu.discord", locale),       "💬"),
            ("onchain",  t("tasks_menu.onchain", locale),       "🔗"),
            ("form",     t("tasks_menu.form", locale),          "📝"),
        ]
        rows: list[list[dict]] = []
        row: list[dict] = []
        for i, (key, label, _emoji) in enumerate(filters):
            prefix = "▶ " if key == active_filter else ""
            row.append(InlineKeyboards.button(f"{prefix}{label}", f"task_filter:set:{key}"))
            if len(row) == 2 or i == len(filters) - 1:
                rows.append(row)
                row = []
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    # ── Points history ───────────────────────────────────────────────────

    @staticmethod
    def points_history(entries: list[dict], page: int, has_more: bool, locale: str = "bn") -> dict:
        """A11Y2F8: Points transaction history list."""
        rows: list[list[dict]] = []
        for e in entries:
            pts = e.get("points", 0)
            sign = "+" if pts >= 0 else ""
            label = f"{sign}{pts} · {e.get('reason', '—')[:32]}"
            rows.append([InlineKeyboards.button(label, f"points:detail:{e.get('id', 0)}")])
        nav = InlineKeyboards.prev_next_row("points:history", page, page > 0, has_more, locale)
        if nav:
            rows.append(nav)
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    # ── Badges ───────────────────────────────────────────────────────────

    @staticmethod
    def badge_list(badges: list[dict], locale: str = "bn") -> dict:
        """A11Y2F9: Earned badge gallery."""
        rows: list[list[dict]] = []
        earned = [b for b in badges if b.get("achieved")]
        locked = [b for b in badges if not b.get("achieved")]
        for b in earned:
            rows.append([InlineKeyboards.button(f"✅ {b['name']}", f"badge:detail:{b['id']}")])
        for b in locked[:5]:
            pct = int(b.get("progress", 0) / max(b.get("target", 1), 1) * 100)
            rows.append([InlineKeyboards.button(f"🔒 {b['name']} {pct}%", f"badge:detail:{b['id']}")])
        rows.append(InlineKeyboards.back_menu_row(locale))
        return InlineKeyboards.from_rows(rows)

    # ── Owner Transfer ───────────────────────────────────────────────────

    @staticmethod
    def transfer_candidate_list(candidates: list[dict], locale: str = "bn") -> dict:
        """A11Y2F10: Candidate list for ownership transfer."""
        return KeyboardBuilders._paginate(
            items=candidates,
            page=0,
            page_size=PAGE_SIZE,
            prefix="transfer_to",
            locale=locale,
            label_fn=lambda m: f"🔑 {m.get('display_name') or m.get('telegram_username', '—')[:38]}",
            nav_prefix="transfer_page",
        )
