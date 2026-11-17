"""
CivicFix Field Worker Operations Portal GUI Module
Provides field workers with task lists, acknowledgment, category-specific checklists,
progress updates, material requisitions, delay reporting, and completion proof uploads.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict, Any, List

from gui.styles import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_BG, COLOR_CARD, COLOR_ACCENT,
    COLOR_SIDEBAR, COLOR_HEADINGS, COLOR_BODY, COLOR_BORDER, COLOR_HOVER,
    COLOR_SIDEBAR_HOVER, COLOR_SIDEBAR_TEXT,
    COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_LIGHT_BLUE, COLOR_LIGHT_ACCENT, COLOR_TEXT,
    STATUS_COLOR_PENDING, STATUS_COLOR_IN_PROGRESS, STATUS_COLOR_RESOLVED, STATUS_COLOR_REJECTED,
    FONT_APP_TITLE, FONT_TITLE, FONT_HEADING, FONT_SECTION, FONT_BODY,
    FONT_BODY_BOLD, FONT_SMALL, FONT_BADGE, STATUS_COLORS, PRIORITY_COLORS,
    apply_button_hover
)
from gui.components import (
    StatCard, DataTable, SearchBar, StatusBadge, PriorityBadge, ScrollableFrame
)
from modules.field_worker import WorkerController
from utils.image_handler import save_image_to_uploads, load_thumbnail
from gui.comparison_widget import BeforeAfterComparisonWidget


class WorkerDashboard(tk.Frame):
    """
    Main Field Worker Portal managing Sidebar navigation and 8 distinct operational views:
    - Overview Dashboard & Deadlines
    - Assigned Tasks
    - Pending Tasks
    - In Progress
    - Delayed Tasks
    - Completed Tasks
    - Notifications
    - Worker Profile
    """
    def __init__(self, parent: tk.Widget, user: Dict[str, Any], profile: Dict[str, Any], **kwargs):
        super().__init__(parent, bg=COLOR_BG, **kwargs)
        self.user = user
        self.profile = profile or {}
        self.controller = WorkerController(worker_user_id=self.user["id"])
        self._image_tk_cache = []

        self._build_ui()

    def _build_ui(self):
        # Sidebar on Left, Content Area on Right
        self.sidebar = tk.Frame(self, bg=COLOR_SIDEBAR, width=240, bd=0)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.content_area = tk.Frame(self, bg=COLOR_BG)
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._nav_buttons = {}
        self._active_tab = None

        self._build_sidebar()
        self.navigate_to("dashboard")

    # --------------------------------------------------------------------------
    # SIDEBAR NAVIGATION
    # --------------------------------------------------------------------------
    def _build_sidebar(self):
        # Worker Profile Header in Sidebar
        w_card = tk.Frame(self.sidebar, bg="#33493C", padx=15, pady=15, bd=1, relief="solid")
        w_card.configure(highlightbackground="#4A6A55")
        w_card.pack(fill=tk.X, padx=12, pady=(15, 12))

        tk.Label(
            w_card,
            text="👷  FIELD OPERATIONS",
            bg="#33493C",
            fg=COLOR_ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        name = self.profile.get("full_name") or self.user.get("username", "Worker")
        tk.Label(
            w_card,
            text=name,
            bg="#33493C",
            fg="#FFFFFF",
            font=FONT_HEADING,
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 0))

        dept = self.profile.get("department", "Operations")
        tk.Label(
            w_card,
            text=f"Dept: {dept}",
            bg="#33493C",
            fg=COLOR_BORDER,
            font=FONT_SMALL,
            anchor="w"
        ).pack(fill=tk.X)

        # 8 Navigation Items as specified in Section 9
        menu_items = [
            ("dashboard", "📊  Dashboard"),
            ("all_tasks", "📌  Assigned Tasks"),
            ("pending", "⏳  Pending Tasks"),
            ("in_progress", "🔧  In Progress"),
            ("delayed", "⚠️  Delayed Tasks"),
            ("completed", "✓  Completed Tasks"),
            ("notifications", "🔔  Notifications"),
            ("profile", "👤  My Profile"),
        ]

        for tab_id, text in menu_items:
            btn = tk.Button(
                self.sidebar,
                text=text,
                bg=COLOR_SIDEBAR,
                fg=COLOR_SIDEBAR_TEXT,
                activebackground=COLOR_SIDEBAR_HOVER,
                activeforeground="#FFFFFF",
                font=FONT_BODY,
                relief="flat",
                anchor="w",
                padx=20,
                pady=11,
                cursor="hand2",
                command=lambda t=tab_id: self.navigate_to(t)
            )
            btn.pack(fill=tk.X, pady=1)

            def _bind_w_btn(b=btn, tid=tab_id):
                def on_enter(e):
                    if self._active_tab != tid:
                        b.configure(bg=COLOR_SIDEBAR_HOVER)
                def on_leave(e):
                    if self._active_tab != tid:
                        b.configure(bg=COLOR_SIDEBAR)
                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
            _bind_w_btn()

            self._nav_buttons[tab_id] = btn

    def navigate_to(self, tab_name: str, **kwargs):
        """Switches active view and updates sidebar highlight."""
        self._active_tab = tab_name

        for t_id, btn in self._nav_buttons.items():
            if t_id == tab_name:
                btn.configure(bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD)
            else:
                btn.configure(bg=COLOR_SIDEBAR, fg=COLOR_SIDEBAR_TEXT, font=FONT_BODY)

        # Clear Content
        for child in self.content_area.winfo_children():
            child.destroy()

        try:
            if tab_name == "dashboard":
                self._render_dashboard()
            elif tab_name == "all_tasks":
                self._render_task_list("ALL")
            elif tab_name == "pending":
                self._render_task_list("PENDING")
            elif tab_name == "in_progress":
                self._render_task_list("IN_PROGRESS")
            elif tab_name == "delayed":
                self._render_task_list("DELAYED")
            elif tab_name == "completed":
                self._render_task_list("COMPLETED")
            elif tab_name == "notifications":
                self._render_notifications()
            elif tab_name == "profile":
                self._render_profile()
            elif tab_name == "details":
                self._render_task_details(kwargs.get("complaint_id"))
        except Exception as exc:
            import traceback
            err = traceback.format_exc()
            print(f"[Worker Portal View Error] {err}")
            for child in self.content_area.winfo_children():
                child.destroy()
            err_box = tk.Frame(self.content_area, bg=COLOR_CARD, padx=30, pady=30, bd=1, relief="solid")
            err_box.configure(highlightbackground=COLOR_BORDER)
            err_box.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
            tk.Label(err_box, text="⚠️  View Rendering Error", bg=COLOR_CARD, fg=STATUS_COLOR_REJECTED, font=FONT_TITLE).pack(anchor="w")
            tk.Label(err_box, text=f"Error in view '{tab_name}': {exc}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(8, 12))
            retry_btn = tk.Button(
                err_box,
                text="🔄  Reload View",
                bg=COLOR_PRIMARY,
                fg="#FFFFFF",
                font=FONT_BODY_BOLD,
                relief="flat",
                padx=15,
                pady=6,
                cursor="hand2",
                command=lambda: self.navigate_to(tab_name, **kwargs)
            )
            retry_btn.pack(anchor="w")
            apply_button_hover(retry_btn, COLOR_PRIMARY, COLOR_HOVER)

    # --------------------------------------------------------------------------
    # 1. OVERVIEW DASHBOARD
    # --------------------------------------------------------------------------
    def _render_dashboard(self):
        scroll = ScrollableFrame(self.content_area, bg=COLOR_BG)
        scroll.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = scroll.scrollable_content

        # Header Title
        tk.Label(
            content,
            text=f"Field Worker Dashboard  •  {self.profile.get('full_name', self.user['username'])}",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 18, "bold"),
            anchor="w"
        ).pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            content,
            text=f"Department: {self.profile.get('department', 'General')}  |  Specialization: {self.profile.get('specialization', 'Maintenance')}",
            bg=COLOR_BG,
            fg=COLOR_BODY,
            font=FONT_BODY,
            anchor="w"
        ).pack(fill=tk.X, pady=(0, 15))

        # KPI Metric Cards
        kpi = self.controller.get_worker_kpi_summary()
        stats_row = tk.Frame(content, bg=COLOR_BG)
        stats_row.pack(fill=tk.X, pady=(0, 20))

        StatCard(stats_row, "Total Assigned", value=kpi["total_assigned"], subtitle="Dispatched tasks", accent_color=COLOR_PRIMARY, icon="📌").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(stats_row, "New / Unacknowledged", value=kpi["new_assigned"], subtitle="Needs acknowledgment", accent_color=STATUS_COLOR_PENDING, icon="⏳").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(stats_row, "In Progress", value=kpi["in_progress"], subtitle="Active on field", accent_color=STATUS_COLOR_IN_PROGRESS, icon="🔧").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(stats_row, "Completed", value=kpi["completed"], subtitle="Proof submitted", accent_color=STATUS_COLOR_RESOLVED, icon="✓").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(stats_row, "Overdue Deadlines", value=kpi["overdue"], subtitle="Passed due date", accent_color=STATUS_COLOR_REJECTED, icon="⚠️").pack(side=tk.LEFT)

        # Urgent Tasks / Upcoming Deadlines Alert Banner
        active_tasks = self.controller.get_assigned_tasks(status_filter="PENDING") + self.controller.get_assigned_tasks(status_filter="IN_PROGRESS")
        if active_tasks:
            alert_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=15)
            alert_card.configure(highlightbackground=COLOR_BORDER)
            alert_card.pack(fill=tk.X, pady=(0, 20))

            top_a = tk.Frame(alert_card, bg=COLOR_CARD)
            top_a.pack(fill=tk.X)

            tk.Label(top_a, text="⚡ Active Tasks Requiring Action", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(side=tk.LEFT)

            def open_first():
                self.navigate_to("details", complaint_id=active_tasks[0]["complaint_id"])

            next_btn = tk.Button(top_a, text="Open Next Task →", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=12, pady=4, cursor="hand2", command=open_first)
            next_btn.pack(side=tk.RIGHT)
            apply_button_hover(next_btn, COLOR_PRIMARY, COLOR_HOVER)

            next_task = active_tasks[0]
            tk.Label(
                alert_card,
                text=f"Priority: {next_task['priority']}  |  {next_task['complaint_id']}: {next_task['title']}\nLocation: {next_task['location']}, {next_task['locality']}  |  Due Date: {next_task.get('due_date') or 'No deadline'}",
                bg=COLOR_CARD,
                fg=COLOR_HEADINGS,
                font=FONT_BODY,
                anchor="w",
                justify="left"
            ).pack(fill=tk.X, pady=(8, 0))

        # Recent Assigned Tasks Table
        recent_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        recent_card.configure(highlightbackground=COLOR_BORDER)
        recent_card.pack(fill=tk.X)

        tk.Label(recent_card, text="Recent Task Assignments", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w", pady=(0, 10))

        cols = [
            ("complaint_id", "Complaint ID", 130),
            ("title", "Task Title", 260),
            ("category", "Category", 180),
            ("location", "Location Landmark", 180),
            ("priority", "Priority", 110),
            ("due_date", "Target Deadline", 150),
            ("status", "Current Status", 150),
        ]

        table = DataTable(recent_card, columns=cols, on_double_click=lambda r: self.navigate_to("details", complaint_id=r["complaint_id"]))
        table.pack(fill=tk.X, pady=(0, 8))
        table.set_rows(self.controller.get_assigned_tasks()[:6])

        tk.Label(recent_card, text="💡 Double-click any task to view original citizen evidence, open work checklists, and submit completion proof.", bg=COLOR_CARD, fg=COLOR_MUTED, font=FONT_SMALL, anchor="w").pack(fill=tk.X)

    # --------------------------------------------------------------------------
    # 2. ASSIGNED / FILTERED TASK LISTS
    # --------------------------------------------------------------------------
    def _render_task_list(self, filter_type: str):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        titles = {
            "ALL": "All Assigned Tasks",
            "PENDING": "Pending Tasks (Awaiting Acknowledgment or Start)",
            "IN_PROGRESS": "In-Progress Tasks (Active on Field)",
            "DELAYED": "Delayed Tasks",
            "COMPLETED": "Completed Task History",
        }
        tk.Label(container, text=titles.get(filter_type, "Assigned Tasks"), bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X)

        # Search Bar
        toolbar = tk.Frame(container, bg=COLOR_BG)
        toolbar.pack(fill=tk.X, pady=(8, 12))

        search_box = SearchBar(
            toolbar,
            placeholder="Search by ID, Street, or Title...",
            on_search=lambda q: apply_filters()
        )
        search_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        cols = [
            ("complaint_id", "ID", 130),
            ("title", "Task Title", 260),
            ("category", "Category", 180),
            ("location", "Location Landmark", 180),
            ("priority", "Priority", 110),
            ("due_date", "Deadline", 150),
            ("status", "Status", 150),
        ]

        table = DataTable(container, columns=cols, on_double_click=lambda r: self.navigate_to("details", complaint_id=r["complaint_id"]))
        table.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        def apply_filters():
            q = search_box.get_text()
            data = self.controller.get_assigned_tasks(status_filter=filter_type, search_query=q)
            table.set_rows(data)

        # Action Buttons
        act_bar = tk.Frame(container, bg=COLOR_BG)
        act_bar.pack(fill=tk.X)

        def open_details():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Task", "Please select a task from the list.")
                return
            self.navigate_to("details", complaint_id=sel["complaint_id"])

        det_btn = tk.Button(act_bar, text="🔍  Open Task Details & Actions →", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=7, cursor="hand2", command=open_details)
        det_btn.pack(side=tk.LEFT)
        apply_button_hover(det_btn, COLOR_PRIMARY, COLOR_HOVER)

        apply_filters()

    # --------------------------------------------------------------------------
    # 3. TASK DETAILS, CHECKLIST, PROGRESS & COMPLETION INSPECTOR
    # --------------------------------------------------------------------------
    def _render_task_details(self, complaint_id_or_code: Any):
        scroll = ScrollableFrame(self.content_area, bg=COLOR_BG)
        scroll.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = scroll.scrollable_content

        task = self.controller.get_task_details(complaint_id_or_code)
        if not task:
            tk.Label(content, text="Task not found or not assigned to you.", bg=COLOR_BG, fg=STATUS_COLOR_REJECTED, font=FONT_TITLE).pack(pady=40)
            return

        cid = task["id"]
        asgn_id = task["assignment_id"]
        code = task["complaint_id"]

        # Back link & Header
        top_nav = tk.Frame(content, bg=COLOR_BG)
        top_nav.pack(fill=tk.X, pady=(0, 10))

        tk.Button(top_nav, text="← Back to Tasks", bg=COLOR_BG, fg=COLOR_PRIMARY, font=FONT_BODY_BOLD, relief="flat", cursor="hand2", command=lambda: self.navigate_to("all_tasks")).pack(side=tk.LEFT)

        # Main Task Information Card
        main_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=25, pady=20)
        main_card.configure(highlightbackground=COLOR_BORDER)
        main_card.pack(fill=tk.X, pady=(0, 15))

        title_row = tk.Frame(main_card, bg=COLOR_CARD)
        title_row.pack(fill=tk.X)

        tk.Label(title_row, text=f"{code} : {task['title']}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=("Segoe UI", 15, "bold"), anchor="w").pack(side=tk.LEFT)

        badges_box = tk.Frame(title_row, bg=COLOR_CARD)
        badges_box.pack(side=tk.RIGHT)
        PriorityBadge(badges_box, task["priority"]).pack(side=tk.LEFT, padx=3)
        StatusBadge(badges_box, task["status"]).pack(side=tk.LEFT, padx=3)

        sub_info = tk.Frame(main_card, bg=COLOR_CARD)
        sub_info.pack(fill=tk.X, pady=(6, 10))
        tk.Label(
            sub_info,
            text=f"📂 Category: {task['category']}  |  📍 Location: {task['location']}, {task['locality']}  |  📅 Deadline: {task.get('due_date') or 'None'}",
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=FONT_SMALL,
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(main_card, text=f"Description: {task['description']}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY, justify="left", anchor="w").pack(fill=tk.X, pady=(0, 6))

        if task.get("admin_remarks"):
            tk.Label(main_card, text=f"Admin Instructions: {task['admin_remarks']}", bg=COLOR_ACCENT, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD, padx=8, pady=4).pack(fill=tk.X, pady=(4, 0))

        # Action Buttons Toolbar for Field Operations
        action_toolbar = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=12)
        action_toolbar.configure(highlightbackground=COLOR_BORDER)
        action_toolbar.pack(fill=tk.X, pady=(0, 15))

        tk.Label(action_toolbar, text="Field Action Operations:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 15))

        # 1. Acknowledge button
        is_ack = bool(task.get("acknowledged_at"))
        def on_ack():
            ok, msg = self.controller.acknowledge_task(asgn_id, cid)
            if ok:
                messagebox.showinfo("Acknowledged", msg)
                self.navigate_to("details", complaint_id=code)
            else:
                messagebox.showerror("Error", msg)

        ack_btn = tk.Button(
            action_toolbar,
            text="✓ Acknowledge Task" if not is_ack else "✓ Acknowledged",
            bg=COLOR_PRIMARY if not is_ack else COLOR_BG,
            fg="#FFFFFF" if not is_ack else COLOR_BODY,
            activebackground=COLOR_HOVER if not is_ack else COLOR_BG,
            activeforeground="#FFFFFF" if not is_ack else COLOR_BODY,
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2" if not is_ack else "arrow",
            state=tk.NORMAL if not is_ack else tk.DISABLED,
            command=on_ack
        )
        ack_btn.pack(side=tk.LEFT, padx=(0, 8))
        if not is_ack:
            apply_button_hover(ack_btn, COLOR_PRIMARY, COLOR_HOVER)

        # 2. Update Progress / In Progress button
        def on_progress_click():
            self._show_progress_modal(asgn_id, cid, code)

        prog_btn = tk.Button(
            action_toolbar,
            text="🚀  Update Progress / Notes",
            bg=STATUS_COLOR_IN_PROGRESS,
            fg="#FFFFFF",
            activebackground="#58837B",
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=on_progress_click
        )
        prog_btn.pack(side=tk.LEFT, padx=(0, 8))
        apply_button_hover(prog_btn, STATUS_COLOR_IN_PROGRESS, "#58837B")

        # 3. Report Delay button
        def on_delay_click():
            self._show_delay_modal(asgn_id, cid, code)

        del_btn = tk.Button(
            action_toolbar,
            text="⚠️  Report Delay Reason",
            bg=STATUS_COLOR_PENDING,
            fg="#FFFFFF",
            activebackground="#D38F2E",
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=on_delay_click
        )
        del_btn.pack(side=tk.LEFT, padx=(0, 8))
        apply_button_hover(del_btn, STATUS_COLOR_PENDING, "#D38F2E")

        # 4. Complete Task button
        def on_complete_click():
            self._show_complete_modal(asgn_id, cid, code)

        comp_btn = tk.Button(
            action_toolbar,
            text="🏆  Complete Task & Upload Proof",
            bg=STATUS_COLOR_RESOLVED,
            fg="#FFFFFF",
            activebackground="#3F7A52",
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=on_complete_click
        )
        comp_btn.pack(side=tk.LEFT)
        apply_button_hover(comp_btn, STATUS_COLOR_RESOLVED, "#3F7A52")

        # Split 2-Column: Left = Evidence Photos, Right = Checklist & Materials
        split_row = tk.Frame(content, bg=COLOR_BG)
        split_row.pack(fill=tk.BOTH, expand=True)

        # Left Column: Photographic Evidence
        left_col = tk.Frame(split_row, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        left_col.configure(highlightbackground=COLOR_BORDER)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Side-by-Side Before/After Photo Resolution Inspection
        comp_widget = BeforeAfterComparisonWidget(
            left_col,
            complaint_data=task,
            max_photo_width=200,
            max_photo_height=140
        )
        comp_widget.pack(fill=tk.BOTH, expand=True)

        # Right Column: Checklist & Material Requisitions
        right_col = tk.Frame(split_row, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        right_col.configure(highlightbackground=COLOR_BORDER)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # Category-Specific Checklist
        tk.Label(right_col, text=f"📋  Work Checklist ({task['category']})", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE, anchor="w").pack(fill=tk.X, pady=(0, 8))

        checklist_items = task.get("checklist", [])
        for item in checklist_items:
            chk_row = tk.Frame(right_col, bg=COLOR_CARD)
            chk_row.pack(fill=tk.X, pady=3)

            var = tk.BooleanVar(value=bool(item["is_completed"]))
            def on_toggle(it_id=item["id"], v=var):
                self.controller.toggle_checklist_item(it_id, v.get())

            cb = tk.Checkbutton(
                chk_row,
                text=item["item_text"],
                variable=var,
                bg=COLOR_CARD,
                fg=COLOR_HEADINGS,
                activebackground=COLOR_CARD,
                font=FONT_BODY,
                command=on_toggle
            )
            cb.pack(side=tk.LEFT, anchor="w")

        # Material Requirements Requisition Box
        tk.Label(right_col, text="🛠️  Material & Equipment Requisitions", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE, anchor="w").pack(fill=tk.X, pady=(18, 6))

        mats = task.get("materials", [])
        if mats:
            for m in mats:
                tk.Label(right_col, text=f"• {m['item_name']} (Qty: {m['quantity']}) - {m.get('notes') or 'Standard'}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_SMALL, anchor="w").pack(fill=tk.X)
        else:
            tk.Label(right_col, text="No extra materials requisitioned yet.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL, anchor="w").pack(fill=tk.X)

        def add_mat_popup():
            modal = tk.Toplevel(self)
            modal.title("Requisition Material")
            modal.geometry("400x260")
            modal.configure(bg=COLOR_BG)
            modal.transient(self)
            modal.grab_set()

            b = tk.Frame(modal, bg=COLOR_CARD, padx=20, pady=15, bd=1, relief="solid")
            b.configure(highlightbackground=COLOR_BORDER)
            b.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

            tk.Label(b, text="Add Material Requisition", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_HEADING).pack(anchor="w")
            tk.Label(b, text="Item Name *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(8, 2))
            i_ent = tk.Entry(b, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            i_ent.pack(fill=tk.X, ipady=4)

            tk.Label(b, text="Quantity / Units *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(6, 2))
            q_ent = tk.Entry(b, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            q_ent.pack(fill=tk.X, ipady=4)

            def save_m():
                ok, msg = self.controller.add_material_requirement(asgn_id, cid, i_ent.get(), q_ent.get())
                if ok:
                    modal.destroy()
                    self.navigate_to("details", complaint_id=code)
                else:
                    messagebox.showerror("Error", msg)

            s_btn = tk.Button(b, text="Add Material ✓", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", pady=6, cursor="hand2", command=save_m)
            s_btn.pack(fill=tk.X, pady=(12, 0))
            apply_button_hover(s_btn, COLOR_PRIMARY, COLOR_HOVER)

        req_btn = tk.Button(right_col, text="➕ Requisition New Material", bg=COLOR_ACCENT, fg=COLOR_HEADINGS, font=FONT_SMALL, relief="solid", bd=1, cursor="hand2", command=add_mat_popup)
        req_btn.pack(anchor="w", pady=(8, 0))
        apply_button_hover(req_btn, COLOR_ACCENT, COLOR_SECONDARY, COLOR_HEADINGS, "#FFFFFF")

    # --------------------------------------------------------------------------
    # MODAL DIALOGS: PROGRESS, DELAY, AND COMPLETION
    # --------------------------------------------------------------------------
    def _show_progress_modal(self, assignment_id: int, complaint_id: int, complaint_code: str):
        modal = tk.Toplevel(self)
        modal.title(f"Update Progress - {complaint_code}")
        modal.geometry("520x400")
        modal.configure(bg=COLOR_BG)
        modal.transient(self)
        modal.grab_set()

        card = tk.Frame(modal, bg=COLOR_CARD, padx=25, pady=20, bd=1, relief="solid")
        card.configure(highlightbackground=COLOR_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(card, text="Update Work Progress Notes", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w")
        tk.Label(card, text=f"Record field status for {complaint_code}. Sets status to IN_PROGRESS.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(2, 10))

        tk.Label(card, text="Progress Notes (Required) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        notes_txt = tk.Text(card, height=4, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid", wrap="word")
        notes_txt.pack(fill=tk.X, pady=(0, 10))

        tk.Label(card, text="Estimated Completion Date (YYYY-MM-DD)", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        est_ent = tk.Entry(card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        est_ent.pack(fill=tk.X, ipady=4, pady=(0, 15))

        def save_p():
            n = notes_txt.get("1.0", tk.END).strip()
            e = est_ent.get().strip() or None
            ok, msg = self.controller.update_task_progress(assignment_id, complaint_id, n, e)
            if ok:
                messagebox.showinfo("Progress Recorded", msg)
                modal.destroy()
                self.navigate_to("details", complaint_id=complaint_code)
            else:
                messagebox.showerror("Error", msg)

        save_btn = tk.Button(card, text="Save Progress & Set IN_PROGRESS 🚀", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", pady=8, cursor="hand2", command=save_p)
        save_btn.pack(fill=tk.X)
        apply_button_hover(save_btn, COLOR_PRIMARY, COLOR_HOVER)

    def _show_delay_modal(self, assignment_id: int, complaint_id: int, complaint_code: str):
        modal = tk.Toplevel(self)
        modal.title(f"Report Delay - {complaint_code}")
        modal.geometry("520x380")
        modal.configure(bg=COLOR_BG)
        modal.transient(self)
        modal.grab_set()

        card = tk.Frame(modal, bg=COLOR_CARD, padx=25, pady=20, bd=1, relief="solid")
        card.configure(highlightbackground=COLOR_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(card, text="Report Delay Reason", bg=COLOR_CARD, fg="#900C1E", font=FONT_TITLE).pack(anchor="w")
        tk.Label(card, text=f"Explain unavoidable delays for {complaint_code}. Sets status to DELAYED.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(2, 10))

        tk.Label(card, text="Common Delay Preset:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        presets = [
            "Material or replacement component unavailable in municipal stock",
            "Severe weather / heavy rainfall halted field operations",
            "Equipment / excavator breakdown undergoing maintenance",
            "Additional excavation or structural reinforcement required",
            "Site access blocked by parked vehicles or utility lines"
        ]
        pre_cmb = ttk.Combobox(card, values=presets, state="readonly")
        pre_cmb.set(presets[0])
        pre_cmb.pack(fill=tk.X, pady=(0, 10))

        tk.Label(card, text="Detailed Explanation (min 10 characters) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        txt = tk.Text(card, height=4, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid", wrap="word")
        txt.insert("1.0", presets[0])
        txt.pack(fill=tk.X, pady=(0, 15))

        pre_cmb.bind("<<ComboboxSelected>>", lambda e: (txt.delete("1.0", tk.END), txt.insert("1.0", pre_cmb.get())))

        def save_d():
            r = txt.get("1.0", tk.END).strip()
            ok, msg = self.controller.report_delay_reason(assignment_id, complaint_id, r)
            if ok:
                messagebox.showinfo("Delay Recorded", msg)
                modal.destroy()
                self.navigate_to("details", complaint_id=complaint_code)
            else:
                messagebox.showerror("Error", msg)

        d_btn = tk.Button(card, text="Confirm Delay Report ⚠️", bg=STATUS_COLOR_PENDING, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", pady=8, cursor="hand2", command=save_d)
        d_btn.pack(fill=tk.X)
        apply_button_hover(d_btn, STATUS_COLOR_PENDING, "#D38F2E")

    def _show_complete_modal(self, assignment_id: int, complaint_id: int, complaint_code: str):
        modal = tk.Toplevel(self)
        modal.title(f"Task Completion Proof - {complaint_code}")
        modal.geometry("540x510")
        modal.configure(bg=COLOR_BG)
        modal.transient(self)
        modal.grab_set()

        card = tk.Frame(modal, bg=COLOR_CARD, padx=25, pady=20, bd=1, relief="solid")
        card.configure(highlightbackground=COLOR_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(card, text="Submit Resolution Proof & Finish Task", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w")
        tk.Label(card, text="Resolution requires an uploaded proof photo and final summary remarks.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(2, 10))

        # Photo Picker & Preview
        selected_rel = [None]
        photo_box = tk.Frame(card, bg=COLOR_BG, bd=1, relief="solid", padx=12, pady=10)
        photo_box.configure(highlightbackground=COLOR_BORDER)
        photo_box.pack(fill=tk.X, pady=(0, 12))

        prev_lbl = tk.Label(photo_box, text="No resolution photo selected yet *", bg=COLOR_BG, fg=COLOR_MUTED)
        prev_lbl.pack(pady=10)

        def pick_proof():
            f = filedialog.askopenfilename(
                title="Select Resolution Proof Photo",
                filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp")]
            )
            if f:
                saved = save_image_to_uploads(f, subfolder="completion_images")
                if saved:
                    selected_rel[0] = saved
                    th = load_thumbnail(saved, max_width=220, max_height=130)
                    if th:
                        self._image_tk_cache.append(th)
                        prev_lbl.configure(image=th, text="")
                    else:
                        prev_lbl.configure(text=f"✓ Photo uploaded: {os.path.basename(saved)}")

        p_btn = tk.Button(photo_box, text="📁 Select Resolution Proof Photo (JPG, PNG) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD, relief="solid", bd=1, cursor="hand2", command=pick_proof)
        p_btn.pack(fill=tk.X)
        apply_button_hover(p_btn, COLOR_CARD, COLOR_ACCENT, COLOR_HEADINGS, COLOR_HEADINGS)

        # Remarks
        tk.Label(card, text="Final Completion Remarks *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 2))
        rem_txt = tk.Text(card, height=3, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid", wrap="word")
        rem_txt.insert("1.0", "Physical maintenance and cleanup completed on site. Proof photo attached.")
        rem_txt.pack(fill=tk.X, pady=(0, 15))

        def finish():
            img = selected_rel[0]
            r = rem_txt.get("1.0", tk.END).strip()
            if not img:
                messagebox.showerror("Proof Required", "You must select and upload a completion proof photo before closing the task.")
                return

            ok, msg = self.controller.submit_task_completion(assignment_id, complaint_id, img, r)
            if ok:
                messagebox.showinfo("Task Completed", msg)
                modal.destroy()
                self.navigate_to("completed")
            else:
                messagebox.showerror("Error", msg)

        c_btn = tk.Button(card, text="Submit Resolution for Admin Verification ✓", bg=STATUS_COLOR_RESOLVED, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", pady=9, cursor="hand2", command=finish)
        c_btn.pack(fill=tk.X)
        apply_button_hover(c_btn, STATUS_COLOR_RESOLVED, "#3F7A52")

    # --------------------------------------------------------------------------
    # 7. NOTIFICATIONS & 8. PROFILE
    # --------------------------------------------------------------------------
    def _render_notifications(self):
        container = ScrollableFrame(self.content_area, bg=COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = container.scrollable_content

        tk.Label(content, text="Field Operations Notifications & Reminders", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X, pady=(0, 15))

        notes = self.controller.get_notifications()
        if not notes:
            tk.Label(content, text="No new notifications.", bg=COLOR_BG, fg=COLOR_BODY).pack(pady=20)
            return

        for n in notes:
            c = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=15, pady=12)
            c.configure(highlightbackground=COLOR_BORDER)
            c.pack(fill=tk.X, pady=4)

            top = tk.Frame(c, bg=COLOR_CARD)
            top.pack(fill=tk.X)
            tk.Label(top, text=n["title"], bg=COLOR_CARD, fg=COLOR_PRIMARY, font=FONT_BODY_BOLD).pack(side=tk.LEFT)
            tk.Label(top, text=n["created_at"], bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(side=tk.RIGHT)

            tk.Label(c, text=n["message"], bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_BODY, anchor="w", wraplength=900, justify="left").pack(fill=tk.X, pady=(4, 0))

    def _render_profile(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=30, pady=25)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Field Worker Profile", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X, pady=(0, 15))

        card = tk.Frame(container, bg=COLOR_CARD, bd=1, relief="solid", padx=25, pady=20)
        card.configure(highlightbackground=COLOR_BORDER)
        card.pack(fill=tk.X)

        p = self.controller.get_profile() or {}
        kpi = self.controller.get_worker_kpi_summary()

        fields = [
            ("Worker Name", p.get("full_name", self.user.get("username"))),
            ("Username", self.user.get("username")),
            ("Department", p.get("department", "Operations")),
            ("Specialization", p.get("specialization", "General Maintenance")),
            ("Phone Number", p.get("phone", "N/A")),
            ("Email Address", self.user.get("email", "N/A")),
            ("Total Tasks Handled", str(kpi["total_assigned"])),
            ("Active Pending Tasks", str(kpi["in_progress"] + kpi["new_assigned"])),
            ("Completed Tasks", str(kpi["completed"])),
        ]

        for label, val in fields:
            row = tk.Frame(card, bg=COLOR_CARD)
            row.pack(fill=tk.X, pady=6)
            tk.Label(row, text=f"{label}:", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_BODY_BOLD, width=22, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=str(val), bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY, anchor="w").pack(side=tk.LEFT)
