"""
CivicFix Administrator Command Center GUI Module
Provides municipal authorities with centralized oversight: verification queue,
AI-assisted priority suggestion, worker dispatching, Matplotlib analytics,
duplicate detection, overdue escalation, and CSV reporting.
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
from modules.administrator import AdministratorController
from services.assignment_service import DEPARTMENTS, get_available_workers, get_default_department_for_category
from services.priority_service import calculate_suggested_priority
from services.report_service import (
    get_status_distribution,
    get_category_distribution,
    get_department_distribution,
    get_department_efficiency,
    get_category_resolution_stats,
    get_locality_distribution,
    get_satisfaction_metrics,
    get_overdue_complaints,
    detect_potential_duplicates,
    export_complaints_to_csv,
    export_worker_performance_csv,
    export_department_kpi_csv,
    get_worker_performance_stats
)
from services.complaint_service import CATEGORIES, get_complaint_details
from utils.image_handler import load_thumbnail
from gui.comparison_widget import BeforeAfterComparisonWidget
from authentication.auth import current_session


class AdminDashboard(tk.Frame):
    """
    Main Administrator Command Center managing Sidebar navigation and 12 distinct views:
    - Overview & Matplotlib Analytics
    - All Complaints
    - New Complaints
    - Verification & Inspection
    - Field Worker Management
    - Assign Complaints
    - Duplicate Detection
    - Overdue Complaints
    - Departments
    - Feedback & Ratings
    - Reports & CSV Export
    - Action History Audit
    """
    def __init__(self, parent: tk.Widget, user: Dict[str, Any], **kwargs):
        super().__init__(parent, bg=COLOR_BG, **kwargs)
        self.user = user
        self.controller = AdministratorController(admin_id=self.user["id"])
        self._image_tk_cache = []

        self._build_ui()

    def _build_ui(self):
        # Sidebar on Left, Content Area on Right
        self.sidebar = tk.Frame(self, bg=COLOR_SIDEBAR, width=250, bd=0)
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
        # Admin Profile Header in Sidebar
        admin_card = tk.Frame(self.sidebar, bg="#33493C", padx=15, pady=15, bd=1, relief="solid")
        admin_card.configure(highlightbackground="#4A6A55")
        admin_card.pack(fill=tk.X, padx=12, pady=(15, 12))

        tk.Label(
            admin_card,
            text="⚙️  ADMINISTRATOR",
            bg="#33493C",
            fg=COLOR_ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            admin_card,
            text=self.user.get("username", "admin").upper(),
            bg="#33493C",
            fg="#FFFFFF",
            font=FONT_HEADING,
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 0))

        tk.Label(
            admin_card,
            text="Municipal Governance Portal",
            bg="#33493C",
            fg=COLOR_BORDER,
            font=FONT_SMALL,
            anchor="w"
        ).pack(fill=tk.X)

        # 12 Navigation Items as specified in Section 8
        menu_items = [
            ("dashboard", "📊  Dashboard & Analytics"),
            ("all_complaints", "📋  All Complaints"),
            ("new_complaints", "🆕  New Complaints Queue"),
            ("verification", "✓  Verification & Inspection"),
            ("workers", "👷  Worker Management"),
            ("assign", "📌  Assign Complaints"),
            ("duplicates", "👥  Duplicate Detection"),
            ("overdue", "⚠️  Overdue Complaints"),
            ("departments", "🏢  Departments"),
            ("feedback", "⭐  Citizen Feedback"),
            ("reports", "📈  Reports & CSV Export"),
            ("audit", "📜  Action Audit Log"),
        ]

        # Use a canvas for the sidebar to ensure all 12 items fit on smaller displays
        canvas = tk.Canvas(self.sidebar, bg=COLOR_SIDEBAR, highlightthickness=0)
        nav_frame = tk.Frame(canvas, bg=COLOR_SIDEBAR)
        canvas.create_window((0, 0), window=nav_frame, anchor="nw", width=248)
        nav_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.pack(fill=tk.BOTH, expand=True)

        for tab_id, text in menu_items:
            btn = tk.Button(
                nav_frame,
                text=text,
                bg=COLOR_SIDEBAR,
                fg=COLOR_SIDEBAR_TEXT,
                activebackground=COLOR_SIDEBAR_HOVER,
                activeforeground="#FFFFFF",
                font=FONT_BODY,
                relief="flat",
                anchor="w",
                padx=18,
                pady=9,
                cursor="hand2",
                command=lambda t=tab_id: self.navigate_to(t)
            )
            btn.pack(fill=tk.X, pady=1)

            def _bind_admin_btn(b=btn, tid=tab_id):
                def on_enter(e):
                    if self._active_tab != tid:
                        b.configure(bg=COLOR_SIDEBAR_HOVER)
                def on_leave(e):
                    if self._active_tab != tid:
                        b.configure(bg=COLOR_SIDEBAR)
                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
            _bind_admin_btn()

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

        if tab_name == "dashboard":
            self._render_dashboard()
        elif tab_name == "all_complaints":
            self._render_all_complaints()
        elif tab_name == "new_complaints":
            self._render_new_complaints()
        elif tab_name == "verification":
            self._render_verification(target_id=kwargs.get("complaint_id"))
        elif tab_name == "workers":
            self._render_worker_management()
        elif tab_name == "assign":
            self._render_assign_complaints(target_id=kwargs.get("complaint_id"))
        elif tab_name == "duplicates":
            self._render_duplicate_detection()
        elif tab_name == "overdue":
            self._render_overdue_complaints()
        elif tab_name == "departments":
            self._render_departments()
        elif tab_name == "feedback":
            self._render_feedback()
        elif tab_name == "reports":
            self._render_reports()
        elif tab_name == "audit":
            self._render_audit_log()

    # --------------------------------------------------------------------------
    # 1. ADMIN DASHBOARD & EMBEDDED MATPLOTLIB CHARTS
    # --------------------------------------------------------------------------
    def _render_dashboard(self):
        scroll = ScrollableFrame(self.content_area, bg=COLOR_BG)
        scroll.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = scroll.scrollable_content

        # Header Title
        tk.Label(
            content,
            text="Municipal Administrator Command Center",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 18, "bold"),
            anchor="w"
        ).pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            content,
            text="City-wide civic oversight, operational metrics, and automated analytics from SQLite.",
            bg=COLOR_BG,
            fg=COLOR_BODY,
            font=FONT_BODY,
            anchor="w"
        ).pack(fill=tk.X, pady=(0, 15))

        # KPI Metrics Cards (Row 1)
        kpi = self.controller.get_dashboard_kpis()
        kpi_row1 = tk.Frame(content, bg=COLOR_BG)
        kpi_row1.pack(fill=tk.X, pady=(0, 10))

        StatCard(kpi_row1, "Total Issues", value=kpi["total"], subtitle="All recorded reports", accent_color=COLOR_PRIMARY, icon="📋").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(kpi_row1, "New / Pending", value=kpi["new"], subtitle="Needs inspection", accent_color=STATUS_COLOR_PENDING, icon="⏳").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(kpi_row1, "Verified", value=kpi["verified"], subtitle="Ready for dispatch", accent_color=COLOR_SECONDARY, icon="✓").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(kpi_row1, "In Progress", value=kpi["in_progress"], subtitle="Field workers active", accent_color=STATUS_COLOR_IN_PROGRESS, icon="🔧").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(kpi_row1, "Resolved / Closed", value=kpi["resolved"] + kpi["closed"], subtitle="Successfully fixed", accent_color=STATUS_COLOR_RESOLVED, icon="✓").pack(side=tk.LEFT)

        # KPI Metrics Cards (Row 2)
        kpi_row2 = tk.Frame(content, bg=COLOR_BG)
        kpi_row2.pack(fill=tk.X, pady=(0, 20))

        StatCard(kpi_row2, "Pending Verification", value=kpi["pending_verification"], subtitle="Worker proof uploaded", accent_color=STATUS_COLOR_IN_PROGRESS, icon="📸").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(kpi_row2, "Reopened", value=kpi["reopened"], subtitle="Unresolved appeal", accent_color=STATUS_COLOR_PENDING, icon="🔄").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(kpi_row2, "Rejected", value=kpi["rejected"], subtitle="Out of scope", accent_color=STATUS_COLOR_REJECTED, icon="✕").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(kpi_row2, "Overdue Issues", value=kpi["overdue"], subtitle="Deadline exceeded", accent_color=STATUS_COLOR_REJECTED, icon="⚠️").pack(side=tk.LEFT, padx=(0, 12))
        StatCard(kpi_row2, "Emergency Flagged", value=kpi["emergency"], subtitle="High-priority alerts", accent_color=STATUS_COLOR_REJECTED, icon="🚨").pack(side=tk.LEFT)

        # Embedded Matplotlib Charts Container (2 Charts side by side)
        charts_container = tk.Frame(content, bg=COLOR_BG)
        charts_container.pack(fill=tk.X, pady=(0, 20))

        # Chart 1: Status Distribution
        chart1_frame = tk.Frame(charts_container, bg=COLOR_CARD, bd=1, relief="solid", padx=15, pady=12)
        chart1_frame.configure(highlightbackground=COLOR_BORDER)
        chart1_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        tk.Label(chart1_frame, text="📊 Complaint Status Distribution", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_HEADING).pack(anchor="w", pady=(0, 8))
        self._embed_status_pie_chart(chart1_frame)

        # Chart 2: Category Breakdown
        chart2_frame = tk.Frame(charts_container, bg=COLOR_CARD, bd=1, relief="solid", padx=15, pady=12)
        chart2_frame.configure(highlightbackground=COLOR_BORDER)
        chart2_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        tk.Label(chart2_frame, text="📈 Category-wise Complaints", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_HEADING).pack(anchor="w", pady=(0, 8))
        self._embed_category_bar_chart(chart2_frame)

    def _embed_status_pie_chart(self, parent: tk.Widget):
        """Generates an embedded Matplotlib Pie/Donut Chart for complaint status."""
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            dist = get_status_distribution()
            if not dist:
                tk.Label(parent, text="No complaints data available.", bg=COLOR_CARD, fg=COLOR_MUTED).pack(pady=40)
                return

            labels = list(dist.keys())
            sizes = list(dist.values())
            colors = [COLOR_PRIMARY, COLOR_SECONDARY, STATUS_COLOR_RESOLVED, STATUS_COLOR_PENDING, STATUS_COLOR_REJECTED, STATUS_COLOR_IN_PROGRESS, COLOR_ACCENT][:len(labels)]

            fig = Figure(figsize=(4.5, 3.2), dpi=95, facecolor="#FFFFFF")
            ax = fig.add_subplot(111)

            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=None,
                autopct='%1.0f%%',
                startangle=140,
                colors=colors,
                textprops=dict(color=COLOR_HEADINGS, size=8, weight="bold"),
                wedgeprops=dict(width=0.45, edgecolor="#FFFFFF", linewidth=1.5)
            )
            ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(0.95, 0.5), fontsize=8, frameon=False)
            fig.subplots_adjust(left=0.05, right=0.65, top=0.95, bottom=0.05)

            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as exc:
            tk.Label(parent, text=f"[Chart Engine Info: {exc}]", bg=COLOR_CARD, fg=COLOR_MUTED).pack(pady=30)

    def _embed_category_bar_chart(self, parent: tk.Widget):
        """Generates an embedded Matplotlib Bar Chart for categories."""
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            cat_dist = get_category_distribution()
            if not cat_dist:
                tk.Label(parent, text="No category data available.", bg=COLOR_CARD, fg=COLOR_MUTED).pack(pady=40)
                return

            # Take top 5 categories
            items = list(cat_dist.items())[:5]
            categories = [it[0][:15] + ".." if len(it[0]) > 15 else it[0] for it in items]
            counts = [it[1] for it in items]

            fig = Figure(figsize=(4.5, 3.2), dpi=95, facecolor="#FFFFFF")
            ax = fig.add_subplot(111)

            y_pos = range(len(categories))
            ax.barh(y_pos, counts, color=COLOR_PRIMARY, edgecolor=COLOR_SECONDARY, height=0.55)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(categories, fontsize=8, color=COLOR_HEADINGS)
            ax.invert_yaxis()
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(COLOR_BORDER)
            ax.spines['bottom'].set_color(COLOR_BORDER)
            ax.tick_params(colors=COLOR_HEADINGS, labelsize=8)
            fig.subplots_adjust(left=0.35, right=0.95, top=0.92, bottom=0.15)

            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as exc:
            tk.Label(parent, text=f"[Chart Engine Info: {exc}]", bg=COLOR_CARD, fg=COLOR_MUTED).pack(pady=30)

    # --------------------------------------------------------------------------
    # 2. ALL COMPLAINTS MASTER TABLE
    # --------------------------------------------------------------------------
    def _render_all_complaints(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            container,
            text="Master Complaints Directory",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 16, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            container,
            text="Search and filter all civic complaints recorded across all localities, departments, and statuses.",
            bg=COLOR_BG,
            fg=COLOR_BODY,
            font=FONT_BODY,
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 12))

        # Toolbar Filters
        toolbar = tk.Frame(container, bg=COLOR_BG)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        search_box = SearchBar(
            toolbar,
            placeholder="Search by ID, Title, Street, Citizen...",
            on_search=lambda q: apply_filters()
        )
        search_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        # Status Filter
        status_opts = ["All Statuses", "NEW", "VERIFIED", "ASSIGNED", "IN_PROGRESS", "COMPLETED_PENDING_VERIFICATION", "RESOLVED", "CLOSED", "REOPENED", "REJECTED"]
        st_combo = ttk.Combobox(toolbar, values=status_opts, state="readonly", width=18)
        st_combo.set("All Statuses")
        st_combo.pack(side=tk.LEFT, padx=(0, 8))
        st_combo.bind("<<ComboboxSelected>>", lambda e: apply_filters())

        # Department Filter
        dept_opts = ["All Departments"] + DEPARTMENTS
        dept_combo = ttk.Combobox(toolbar, values=dept_opts, state="readonly", width=18)
        dept_combo.set("All Departments")
        dept_combo.pack(side=tk.LEFT, padx=(0, 8))
        dept_combo.bind("<<ComboboxSelected>>", lambda e: apply_filters())

        # Priority Filter
        prio_opts = ["All Priorities", "EMERGENCY", "HIGH", "MEDIUM", "LOW"]
        prio_combo = ttk.Combobox(toolbar, values=prio_opts, state="readonly", width=15)
        prio_combo.set("All Priorities")
        prio_combo.pack(side=tk.LEFT, padx=(0, 8))
        prio_combo.bind("<<ComboboxSelected>>", lambda e: apply_filters())

        # Table
        cols = [
            ("complaint_id", "Complaint ID", 130),
            ("citizen_name", "Citizen", 140),
            ("title", "Title", 240),
            ("category", "Category", 160),
            ("location", "Location", 160),
            ("priority", "Priority", 110),
            ("department", "Department", 140),
            ("assigned_worker_name", "Assigned Worker", 150),
            ("status", "Status", 150),
            ("submitted_at", "Date", 130),
        ]

        table = DataTable(
            container,
            columns=cols,
            on_double_click=lambda row: self.navigate_to("verification", complaint_id=row["complaint_id"])
        )
        table.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        def apply_filters():
            q = search_box.get_text()
            st = st_combo.get()
            dep = dept_combo.get()
            pr = prio_combo.get()
            data = self.controller.fetch_all_complaints(
                search_query=q,
                status_filter=st,
                department_filter=dep,
                priority_filter=pr
            )
            table.set_rows(data)

        # Action Bar
        act_bar = tk.Frame(container, bg=COLOR_BG)
        act_bar.pack(fill=tk.X)

        def on_inspect():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Row", "Please select a complaint to inspect.")
                return
            self.navigate_to("verification", complaint_id=sel["complaint_id"])

        def on_assign():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Row", "Please select a complaint to assign.")
                return
            self.navigate_to("assign", complaint_id=sel["complaint_id"])

        def on_close():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Row", "Please select a complaint to close.")
                return
            comp = self.controller.fetch_all_complaints(search_query=sel["complaint_id"])
            if not comp:
                return
            c_id = comp[0]["id"]
            ok = messagebox.askyesno("Confirm Close", f"Verify completion and mark {sel['complaint_id']} as RESOLVED & CLOSED?")
            if ok:
                success, msg = self.controller.close_and_resolve_complaint(c_id, remarks="Direct admin verification and closure.")
                messagebox.showinfo("Result", msg)
                apply_filters()

        insp_btn = tk.Button(act_bar, text="🔍  Inspect / Verify Issue", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=7, cursor="hand2", command=on_inspect)
        insp_btn.pack(side=tk.LEFT, padx=(0, 10))
        apply_button_hover(insp_btn, COLOR_PRIMARY, COLOR_HOVER)

        asgn_btn = tk.Button(act_bar, text="📌  Assign Field Worker", bg=COLOR_SECONDARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=7, cursor="hand2", command=on_assign)
        asgn_btn.pack(side=tk.LEFT, padx=(0, 10))
        apply_button_hover(asgn_btn, COLOR_SECONDARY, "#8E9C76")

        cls_btn = tk.Button(act_bar, text="✓  Verify & Close Complaint", bg=STATUS_COLOR_RESOLVED, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=7, cursor="hand2", command=on_close)
        cls_btn.pack(side=tk.LEFT)
        apply_button_hover(cls_btn, STATUS_COLOR_RESOLVED, "#3F7A52")

        apply_filters()

    # --------------------------------------------------------------------------
    # 3. NEW COMPLAINTS QUEUE
    # --------------------------------------------------------------------------
    def _render_new_complaints(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="🆕  Incoming New Complaints Queue", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(container, text="These complaints require municipal inspection, priority recommendation review, and department assignment.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(2, 12))

        cols = [
            ("complaint_id", "ID", 130),
            ("citizen_name", "Citizen", 150),
            ("title", "Title", 280),
            ("category", "Category", 180),
            ("locality", "Locality", 140),
            ("priority", "Initial Priority", 120),
            ("submitted_at", "Date Reported", 150),
        ]

        table = DataTable(container, columns=cols, on_double_click=lambda r: self.navigate_to("verification", complaint_id=r["complaint_id"]))
        table.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        new_items = self.controller.fetch_new_complaints_queue()
        table.set_rows(new_items)

        def on_verify():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Issue", "Please select a complaint to inspect and verify.")
                return
            self.navigate_to("verification", complaint_id=sel["complaint_id"])

        v_btn = tk.Button(container, text="✓  Inspect & Verify Selected Issue →", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=18, pady=8, cursor="hand2", command=on_verify)
        v_btn.pack(anchor="w")
        apply_button_hover(v_btn, COLOR_PRIMARY, COLOR_HOVER)

    # --------------------------------------------------------------------------
    # 4. VERIFICATION & INSPECTION (WITH AUTO PRIORITY SUGGESTION)
    # --------------------------------------------------------------------------
    def _render_verification(self, target_id: Optional[str] = None):
        scroll = ScrollableFrame(self.content_area, bg=COLOR_BG)
        scroll.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = scroll.scrollable_content

        tk.Label(content, text="Complaint Verification & Inspection Portal", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(content, text="Examine citizen evidence photos, evaluate auto-suggested priority, and approve or reject complaints.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(2, 12))

        # Selectable Dropdown of Complaints
        all_comps = self.controller.fetch_all_complaints()
        if not all_comps:
            tk.Label(content, text="No complaints found in the system.", bg=COLOR_BG, fg=COLOR_MUTED).pack(pady=20)
            return

        selector_bar = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=15, pady=10)
        selector_bar.configure(highlightbackground=COLOR_BORDER)
        selector_bar.pack(fill=tk.X, pady=(0, 15))

        tk.Label(selector_bar, text="Select Complaint:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 10))

        options = [f"{c['complaint_id']} - {c['title'][:40]}" for c in all_comps]
        sel_var = tk.StringVar()

        init_idx = 0
        if target_id:
            for idx, opt in enumerate(options):
                if target_id in opt:
                    init_idx = idx
                    break
        sel_var.set(options[init_idx])

        combo = ttk.Combobox(selector_bar, textvariable=sel_var, values=options, state="readonly", width=55)
        combo.pack(side=tk.LEFT)

        inspect_panel = tk.Frame(content, bg=COLOR_BG)
        inspect_panel.pack(fill=tk.BOTH, expand=True)

        def load_verification_ui(*args):
            for child in inspect_panel.winfo_children():
                child.destroy()

            chosen_code = sel_var.get().split(" - ")[0]
            data = get_complaint_details(chosen_code)
            if not data:
                return

            self._build_verification_detail(inspect_panel, data)

        combo.bind("<<ComboboxSelected>>", load_verification_ui)
        load_verification_ui()

    def _build_verification_detail(self, parent: tk.Widget, data: Dict[str, Any]):
        cid = data["id"]
        code = data["complaint_id"]

        # 2-Column Split: Left = Evidence & Metadata, Right = Decision & Priority Engine
        split_row = tk.Frame(parent, bg=COLOR_BG)
        split_row.pack(fill=tk.BOTH, expand=True)

        # Left Column: Evidence Photo + Metadata
        left_col = tk.Frame(split_row, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        left_col.configure(highlightbackground=COLOR_BORDER)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        tk.Label(left_col, text=f"{code} : {data['title']}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE, anchor="w").pack(fill=tk.X)
        tk.Label(left_col, text=f"Category: {data['category']}  |  Locality: {data['locality']}", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL, anchor="w").pack(fill=tk.X, pady=(2, 8))

        # Side-by-Side Before/After Photo Resolution Inspection
        comp_widget = BeforeAfterComparisonWidget(
            left_col,
            complaint_data=data,
            max_photo_width=180,
            max_photo_height=130
        )
        comp_widget.pack(fill=tk.X, pady=(0, 12))

        # Details text
        tk.Label(left_col, text=f"📍 Location Landmark: {data['location']}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD, anchor="w").pack(fill=tk.X)
        tk.Label(left_col, text=f"📝 Description:\n{data['description']}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY, justify="left", anchor="w").pack(fill=tk.X, pady=(4, 0))

        if data.get("is_emergency"):
            tk.Label(left_col, text="🚨 CITIZEN MARKED AS EMERGENCY", bg="#FFE4E6", fg="#900C1E", font=FONT_BODY_BOLD, padx=8, pady=4).pack(anchor="w", pady=(8, 0))

        # Right Column: Decision Form & Priority Recommendation Engine
        right_col = tk.Frame(split_row, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        right_col.configure(highlightbackground=COLOR_BORDER)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        tk.Label(right_col, text="Decision & Priority Verification", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE, anchor="w").pack(fill=tk.X, pady=(0, 8))

        # Auto-Suggested Priority Card
        sug_prio, sug_reason = calculate_suggested_priority(
            category=data["category"],
            is_emergency=bool(data.get("is_emergency")),
            support_count=data.get("support_count", 0),
            submitted_at=data.get("submitted_at")
        )

        sug_card = tk.Frame(right_col, bg=COLOR_ACCENT, bd=1, relief="solid", padx=12, pady=10)
        sug_card.configure(highlightbackground=COLOR_BORDER)
        sug_card.pack(fill=tk.X, pady=(0, 15))

        tk.Label(sug_card, text=f"💡 Auto-Suggested Priority: {sug_prio}", bg=COLOR_ACCENT, fg=COLOR_HEADINGS, font=FONT_HEADING, anchor="w").pack(fill=tk.X)
        tk.Label(sug_card, text=f"Reason: {sug_reason}", bg=COLOR_ACCENT, fg=COLOR_BODY, font=FONT_SMALL, wraplength=420, justify="left", anchor="w").pack(fill=tk.X, pady=(2, 0))

        # Final Priority Override
        tk.Label(right_col, text="Final Approved Priority *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        prio_combo = ttk.Combobox(right_col, values=["EMERGENCY", "HIGH", "MEDIUM", "LOW"], state="readonly")
        prio_combo.set(sug_prio)
        prio_combo.pack(fill=tk.X, pady=(0, 10))

        # Department Assignment
        rec_dept = get_default_department_for_category(data["category"])
        tk.Label(right_col, text="Assign Municipal Department *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        dept_combo = ttk.Combobox(right_col, values=DEPARTMENTS, state="readonly")
        dept_combo.set(data.get("department") or rec_dept)
        dept_combo.pack(fill=tk.X, pady=(0, 10))

        # Admin Remarks
        tk.Label(right_col, text="Administrator Inspection Remarks *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        remarks_entry = tk.Entry(right_col, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        remarks_entry.insert(0, f"Inspected and verified for {dept_combo.get()} department.")
        remarks_entry.pack(fill=tk.X, ipady=4, pady=(0, 15))

        # Decision Buttons
        def handle_verify():
            rem = remarks_entry.get().strip()
            pr = prio_combo.get()
            dep = dept_combo.get()
            ok, msg = self.controller.verify_complaint(cid, remarks=rem, priority=pr, department=dep)
            if ok:
                messagebox.showinfo("Verified", msg)
                self.navigate_to("assign", complaint_id=code)
            else:
                messagebox.showerror("Error", msg)

        def handle_reject():
            modal = tk.Toplevel(self)
            modal.title(f"Reject Complaint {code}")
            modal.geometry("460x280")
            modal.configure(bg=COLOR_BG)
            modal.transient(self)
            modal.grab_set()

            m_box = tk.Frame(modal, bg=COLOR_CARD, padx=20, pady=15, bd=1, relief="solid")
            m_box.configure(highlightbackground=COLOR_BORDER)
            m_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

            tk.Label(m_box, text=f"Reject Complaint {code}", bg=COLOR_CARD, fg="#900C1E", font=FONT_HEADING).pack(anchor="w")
            tk.Label(m_box, text="Please enter an explicit rejection justification (min 10 chars):", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(2, 8))

            r_txt = tk.Text(m_box, height=4, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            r_txt.pack(fill=tk.X, pady=(0, 12))

            def confirm_rej():
                reason = r_txt.get("1.0", tk.END).strip()
                ok, msg = self.controller.reject_complaint(cid, reason)
                if ok:
                    messagebox.showinfo("Rejected", msg)
                    modal.destroy()
                    self.navigate_to("all_complaints")
                else:
                    messagebox.showerror("Validation Error", msg)

            rej_btn = tk.Button(m_box, text="Confirm Rejection ✕", bg=STATUS_COLOR_REJECTED, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", pady=7, cursor="hand2", command=confirm_rej)
            rej_btn.pack(fill=tk.X)
            apply_button_hover(rej_btn, STATUS_COLOR_REJECTED, "#B85555")

        btn_row = tk.Frame(right_col, bg=COLOR_CARD)
        btn_row.pack(fill=tk.X, pady=(5, 0))

        if data.get("status") == "COMPLETED_PENDING_VERIFICATION":
            def handle_approve_resolution():
                rem = remarks_entry.get().strip() or "Verified completion photo and approved resolution."
                ok, msg = self.controller.close_and_resolve_complaint(cid, remarks=rem)
                if ok:
                    messagebox.showinfo("Resolved", msg)
                    self.navigate_to("all_complaints")
                else:
                    messagebox.showerror("Error", msg)

            def handle_rework():
                modal = tk.Toplevel(self)
                modal.title(f"Request Rework for {code}")
                modal.geometry("460x280")
                modal.configure(bg=COLOR_BG)
                modal.transient(self)
                modal.grab_set()

                m_box = tk.Frame(modal, bg=COLOR_CARD, padx=20, pady=15, bd=1, relief="solid")
                m_box.configure(highlightbackground=COLOR_BORDER)
                m_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

                tk.Label(m_box, text=f"Request Rework for {code}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_HEADING).pack(anchor="w")
                tk.Label(m_box, text="Please enter specific rework instructions for the worker (min 10 chars):", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(2, 8))

                r_txt = tk.Text(m_box, height=4, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
                r_txt.pack(fill=tk.X, pady=(0, 12))

                def confirm_rework():
                    reason = r_txt.get("1.0", tk.END).strip()
                    ok, msg = self.controller.request_rework(cid, reason)
                    if ok:
                        messagebox.showinfo("Rework Sent", msg)
                        modal.destroy()
                        self.navigate_to("all_complaints")
                    else:
                        messagebox.showerror("Validation Error", msg)

                rwk_btn = tk.Button(m_box, text="Send Rework Instructions ↺", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", pady=7, cursor="hand2", command=confirm_rework)
                rwk_btn.pack(fill=tk.X)
                apply_button_hover(rwk_btn, COLOR_PRIMARY, COLOR_HOVER)

            appr_btn = tk.Button(btn_row, text="✓  Approve Completion & Resolve", bg=STATUS_COLOR_RESOLVED, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=8, cursor="hand2", command=handle_approve_resolution)
            appr_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
            apply_button_hover(appr_btn, STATUS_COLOR_RESOLVED, "#3F7A52")

            rewk_btn = tk.Button(btn_row, text="↺  Request Rework", bg=STATUS_COLOR_PENDING, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=8, cursor="hand2", command=handle_rework)
            rewk_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))
            apply_button_hover(rewk_btn, STATUS_COLOR_PENDING, "#D38F2E")
        else:
            v_btn2 = tk.Button(btn_row, text="✓  Verify & Approve Issue", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=8, cursor="hand2", command=handle_verify)
            v_btn2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
            apply_button_hover(v_btn2, COLOR_PRIMARY, COLOR_HOVER)

            rej_btn2 = tk.Button(btn_row, text="✕  Reject Issue", bg=STATUS_COLOR_REJECTED, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=8, cursor="hand2", command=handle_reject)
            rej_btn2.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))
            apply_button_hover(rej_btn2, STATUS_COLOR_REJECTED, "#B85555")

    # --------------------------------------------------------------------------
    # 5. FIELD WORKER MANAGEMENT
    # --------------------------------------------------------------------------
    def _render_worker_management(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        top_row = tk.Frame(container, bg=COLOR_BG)
        top_row.pack(fill=tk.X, pady=(0, 12))

        tk.Label(top_row, text="Field Worker Directory & Workload", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)

        def open_add_worker_modal():
            self._show_add_worker_modal()

        add_btn = tk.Button(top_row, text="➕  Add New Field Worker", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=6, cursor="hand2", command=open_add_worker_modal)
        add_btn.pack(side=tk.RIGHT)
        apply_button_hover(add_btn, COLOR_PRIMARY, COLOR_HOVER)

        # Workers Table
        cols = [
            ("user_id", "ID", 60),
            ("full_name", "Worker Full Name", 200),
            ("username", "Username", 140),
            ("department", "Department", 180),
            ("specialization", "Specialization", 220),
            ("phone", "Contact Phone", 140),
            ("active_tasks", "Active Tasks", 110),
            ("completed_tasks", "Completed", 110),
        ]

        table = DataTable(container, columns=cols)
        table.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        workers = get_available_workers()
        table.set_rows(workers)

        # Bottom Bar: Activate / Deactivate
        act_bar = tk.Frame(container, bg=COLOR_BG)
        act_bar.pack(fill=tk.X)

        def toggle_status():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Worker", "Please select a field worker from the table.")
                return
            w_uid = int(sel["user_id"])
            self.controller.toggle_worker_status(w_uid, is_active=False)
            messagebox.showinfo("Status Updated", f"Worker {sel['full_name']} account status updated.")
            table.set_rows(get_available_workers())

        tgl_btn = tk.Button(act_bar, text="Deactivate / Toggle Worker Account", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_SMALL, relief="solid", bd=1, cursor="hand2", command=toggle_status)
        tgl_btn.pack(side=tk.LEFT)
        apply_button_hover(tgl_btn, COLOR_CARD, COLOR_BG, COLOR_HEADINGS, COLOR_HEADINGS)

    def _show_add_worker_modal(self):
        modal = tk.Toplevel(self)
        modal.title("Add New Field Worker Account")
        modal.geometry("540x540")
        modal.configure(bg=COLOR_BG)
        modal.transient(self)
        modal.grab_set()

        card = tk.Frame(modal, bg=COLOR_CARD, padx=25, pady=20, bd=1, relief="solid")
        card.configure(highlightbackground=COLOR_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(card, text="Provision Field Worker Account", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w")
        tk.Label(card, text="Creates worker credentials with department and specialization.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(0, 12))

        # Fields
        tk.Label(card, text="Full Name *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        name_ent = tk.Entry(card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        name_ent.pack(fill=tk.X, ipady=4, pady=(0, 8))

        tk.Label(card, text="Username *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        user_ent = tk.Entry(card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        user_ent.pack(fill=tk.X, ipady=4, pady=(0, 8))

        tk.Label(card, text="Email Address *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        email_ent = tk.Entry(card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        email_ent.pack(fill=tk.X, ipady=4, pady=(0, 8))

        tk.Label(card, text="Phone Number *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        phone_ent = tk.Entry(card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        phone_ent.pack(fill=tk.X, ipady=4, pady=(0, 8))

        tk.Label(card, text="Department *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        dept_cmb = ttk.Combobox(card, values=DEPARTMENTS, state="readonly")
        dept_cmb.set(DEPARTMENTS[0])
        dept_cmb.pack(fill=tk.X, pady=(0, 8))

        tk.Label(card, text="Specialization (e.g. Asphalt Repair, Cabling)", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        spec_ent = tk.Entry(card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        spec_ent.pack(fill=tk.X, ipady=4, pady=(0, 8))

        tk.Label(card, text="Initial Password (min 8 chars) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        pwd_ent = tk.Entry(card, font=FONT_BODY, show="•", bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        pwd_ent.insert(0, "Worker@123")
        pwd_ent.pack(fill=tk.X, ipady=4, pady=(0, 15))

        def save_worker():
            ok, uid, msg = self.controller.add_worker(
                full_name=name_ent.get(),
                username=user_ent.get(),
                email=email_ent.get(),
                phone=phone_ent.get(),
                department=dept_cmb.get(),
                specialization=spec_ent.get(),
                password=pwd_ent.get()
            )
            if ok:
                messagebox.showinfo("Worker Created", msg)
                modal.destroy()
                self._render_worker_management()
            else:
                messagebox.showerror("Validation Error", msg)

        save_btn = tk.Button(card, text="Create Field Worker Account ✓", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", pady=8, cursor="hand2", command=save_worker)
        save_btn.pack(fill=tk.X)
        apply_button_hover(save_btn, COLOR_PRIMARY, COLOR_HOVER)

    # --------------------------------------------------------------------------
    # 6. ASSIGN COMPLAINTS TO WORKERS
    # --------------------------------------------------------------------------
    def _render_assign_complaints(self, target_id: Optional[str] = None):
        scroll = ScrollableFrame(self.content_area, bg=COLOR_BG)
        scroll.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = scroll.scrollable_content

        tk.Label(content, text="Field Worker Dispatch & Task Assignment", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(content, text="Assign verified civic issues to municipal field crews with workload tracking and resolution deadlines.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(2, 12))

        # Fetch Verified or Reopened Complaints
        queue = self.controller.fetch_all_complaints(status_filter="VERIFIED") + self.controller.fetch_all_complaints(status_filter="REOPENED")
        if not queue:
            # If empty, also allow reassigning all complaints
            queue = self.controller.fetch_all_complaints()

        if not queue:
            tk.Label(content, text="No complaints currently require worker assignment.", bg=COLOR_BG, fg=COLOR_MUTED).pack(pady=20)
            return

        assign_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=25, pady=20)
        assign_card.configure(highlightbackground=COLOR_BORDER)
        assign_card.pack(fill=tk.BOTH, expand=True)

        # 1. Select Issue
        tk.Label(assign_card, text="1. Select Verified Issue to Dispatch *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        issue_opts = [f"{c['complaint_id']} - {c['title']} ({c['category']} | {c['locality']})" for c in queue]
        issue_combo = ttk.Combobox(assign_card, values=issue_opts, state="readonly")

        init_idx = 0
        if target_id:
            for idx, opt in enumerate(issue_opts):
                if target_id in opt:
                    init_idx = idx
                    break
        issue_combo.set(issue_opts[init_idx])
        issue_combo.pack(fill=tk.X, pady=(3, 15))

        # 2. Worker Selection with Workload Indicators
        tk.Label(assign_card, text="2. Select Field Worker (Showing current workload) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        workers = get_available_workers()
        w_opts = [f"{w['full_name']} | Dept: {w['department']} | Active Tasks: {w['active_tasks']}" for w in workers]
        worker_combo = ttk.Combobox(assign_card, values=w_opts, state="readonly")
        if w_opts:
            worker_combo.set(w_opts[0])
        worker_combo.pack(fill=tk.X, pady=(3, 15))

        # 3. Deadline / Due Date
        tk.Label(assign_card, text="3. Target Completion Deadline (YYYY-MM-DD HH:MM:SS) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        import datetime
        default_due = (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d 18:00:00")
        due_entry = tk.Entry(assign_card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        due_entry.insert(0, default_due)
        due_entry.pack(fill=tk.X, ipady=4, pady=(3, 15))

        # 4. Dispatch Notes
        tk.Label(assign_card, text="4. Field Instructions / Material Requisition Notes", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w")
        notes_entry = tk.Entry(assign_card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        notes_entry.insert(0, "Inspect site on priority and upload before-and-after photographic evidence.")
        notes_entry.pack(fill=tk.X, ipady=4, pady=(3, 20))

        def execute_dispatch():
            sel_issue_str = issue_combo.get()
            sel_w_str = worker_combo.get()
            due = due_entry.get().strip()
            notes = notes_entry.get().strip()

            c_code = sel_issue_str.split(" - ")[0]
            comp_obj = get_complaint_details(c_code)
            if not comp_obj:
                messagebox.showerror("Error", "Selected complaint could not be found.")
                return

            # Find worker id
            w_name = sel_w_str.split(" | ")[0]
            matched_w = next((w for w in workers if w["full_name"] == w_name), None)
            if not matched_w:
                messagebox.showerror("Error", "Selected worker could not be found.")
                return

            ok, msg = self.controller.assign_worker(
                complaint_id=comp_obj["id"],
                worker_id=matched_w["user_id"],
                due_date=due,
                notes=notes
            )
            if ok:
                messagebox.showinfo("Task Dispatched", msg)
                self.navigate_to("all_complaints")
            else:
                messagebox.showerror("Dispatch Error", msg)

        disp_btn = tk.Button(assign_card, text="Dispatch Worker & Send Notification 🚀", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", pady=10, cursor="hand2", command=execute_dispatch)
        disp_btn.pack(fill=tk.X)
        apply_button_hover(disp_btn, COLOR_PRIMARY, COLOR_HOVER)

    # --------------------------------------------------------------------------
    # 7. DUPLICATE DETECTION & MERGING
    # --------------------------------------------------------------------------
    def _render_duplicate_detection(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Duplicate Complaint Detection & Merging", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(container, text="Identifies redundant complaint submissions in the same locality using text similarity and category matching.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(2, 12))

        # Select Source Complaint to Check
        all_comps = self.controller.fetch_all_complaints()
        sel_bar = tk.Frame(container, bg=COLOR_CARD, bd=1, relief="solid", padx=15, pady=10)
        sel_bar.configure(highlightbackground=COLOR_BORDER)
        sel_bar.pack(fill=tk.X, pady=(0, 12))

        tk.Label(sel_bar, text="Check Duplicates for Issue:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 10))

        opts = [f"{c['complaint_id']} - {c['title']} ({c['locality']})" for c in all_comps]
        c_var = tk.StringVar()
        if opts:
            c_var.set(opts[0])

        combo = ttk.Combobox(sel_bar, textvariable=c_var, values=opts, state="readonly", width=55)
        combo.pack(side=tk.LEFT)

        # Matches Table
        table_cols = [
            ("complaint_id", "Match ID", 130),
            ("similarity_score", "Similarity %", 110),
            ("title", "Candidate Title", 260),
            ("category", "Category", 180),
            ("locality", "Locality", 140),
            ("citizen_name", "Reported By", 150),
            ("status", "Status", 140),
        ]

        table = DataTable(container, columns=table_cols)
        table.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        def run_detector(*args):
            chosen = c_var.get()
            if not chosen:
                return
            c_code = chosen.split(" - ")[0]
            obj = get_complaint_details(c_code)
            if not obj:
                return
            matches = detect_potential_duplicates(obj["id"])
            table.set_rows(matches)

        combo.bind("<<ComboboxSelected>>", run_detector)

        # Merge Action Bar
        act_bar = tk.Frame(container, bg=COLOR_BG)
        act_bar.pack(fill=tk.X)

        def handle_merge():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Match", "Please select a candidate duplicate from the table to merge.")
                return

            chosen_primary = c_var.get().split(" - ")[0]
            prim_obj = get_complaint_details(chosen_primary)
            dupe_obj = get_complaint_details(sel["complaint_id"])

            confirm = messagebox.askyesno(
                "Confirm Duplicate Merge",
                f"Merge duplicate issue {dupe_obj['complaint_id']} into primary issue {prim_obj['complaint_id']}?\n\n"
                f"• {prim_obj['complaint_id']} will receive +1 support count.\n"
                f"• {dupe_obj['complaint_id']} will be archived as CLOSED.\n"
                f"• Both records will be preserved in the audit log."
            )
            if confirm:
                ok, msg = self.controller.merge_duplicates(prim_obj["id"], dupe_obj["id"])
                if ok:
                    messagebox.showinfo("Merged", msg)
                    run_detector()
                else:
                    messagebox.showerror("Error", msg)

        mrg_btn = tk.Button(act_bar, text="🔗  Merge Selected Duplicate into Primary Issue", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=8, cursor="hand2", command=handle_merge)
        mrg_btn.pack(side=tk.LEFT)
        apply_button_hover(mrg_btn, COLOR_PRIMARY, COLOR_HOVER)

        run_detector()

    # --------------------------------------------------------------------------
    # 8. OVERDUE COMPLAINTS
    # --------------------------------------------------------------------------
    def _render_overdue_complaints(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="⚠️  Overdue Civic Issues", bg=COLOR_BG, fg=STATUS_COLOR_REJECTED, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(container, text="Complaints that have surpassed their target completion deadline without being resolved.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(2, 12))

        cols = [
            ("complaint_id", "ID", 130),
            ("days_overdue", "Days Overdue", 120),
            ("title", "Issue Title", 240),
            ("department", "Department", 160),
            ("worker_name", "Assigned Worker", 160),
            ("worker_phone", "Worker Phone", 130),
            ("status", "Current Status", 140),
            ("due_date", "Target Deadline", 150),
        ]

        table = DataTable(container, columns=cols)
        table.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        overdue_list = get_overdue_complaints()
        table.set_rows(overdue_list)

        act_bar = tk.Frame(container, bg=COLOR_BG)
        act_bar.pack(fill=tk.X)

        def reassign():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Issue", "Please select an overdue complaint to reassign.")
                return
            self.navigate_to("assign", complaint_id=sel["complaint_id"])

        re_btn = tk.Button(act_bar, text="🔄  Reassign Worker / Extend Deadline", bg=STATUS_COLOR_PENDING, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=7, cursor="hand2", command=reassign)
        re_btn.pack(side=tk.LEFT)
        apply_button_hover(re_btn, STATUS_COLOR_PENDING, "#D38F2E")

    # --------------------------------------------------------------------------
    # 9. DEPARTMENTS
    # --------------------------------------------------------------------------
    def _render_departments(self):
        container = ScrollableFrame(self.content_area, bg=COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = container.scrollable_content

        tk.Label(content, text="Municipal Departments Breakdown", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X, pady=(0, 4))
        tk.Label(content, text="Departmental task distribution and active workload volume across municipal wings.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(0, 15))

        dist = get_department_distribution()

        for dept_name in DEPARTMENTS:
            cnt = dist.get(dept_name, 0)
            card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=15)
            card.configure(highlightbackground=COLOR_BORDER)
            card.pack(fill=tk.X, pady=6)

            top = tk.Frame(card, bg=COLOR_CARD)
            top.pack(fill=tk.X)

            tk.Label(top, text=f"🏢  {dept_name}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(side=tk.LEFT)
            tk.Label(top, text=f"{cnt} Assigned Issues", bg=COLOR_ACCENT, fg=COLOR_HEADINGS, font=FONT_BADGE, padx=10, pady=4).pack(side=tk.RIGHT)

            # Workers in this department
            w_list = get_available_workers(department=dept_name)
            w_names = ", ".join([f"{w['full_name']} ({w['active_tasks']} active)" for w in w_list]) if w_list else "No workers enrolled in this department."
            tk.Label(card, text=f"Field Workers: {w_names}", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL, anchor="w").pack(fill=tk.X, pady=(4, 0))

    # --------------------------------------------------------------------------
    # 10. CITIZEN FEEDBACK
    # --------------------------------------------------------------------------
    def _render_feedback(self):
        container = ScrollableFrame(self.content_area, bg=COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = container.scrollable_content

        tk.Label(content, text="Citizen Resolution Ratings & Feedback", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X, pady=(0, 4))
        tk.Label(content, text="Reviews submitted by citizens after complaint resolution.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(0, 15))

        feedbacks = self.controller.fetch_citizen_feedbacks()
        if not feedbacks:
            tk.Label(content, text="No citizen ratings submitted yet.", bg=COLOR_BG, fg=COLOR_BODY).pack(pady=20)
            return

        for fb in feedbacks:
            card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=15)
            card.configure(highlightbackground=COLOR_BORDER)
            card.pack(fill=tk.X, pady=6)

            top = tk.Frame(card, bg=COLOR_CARD)
            top.pack(fill=tk.X)

            stars = "★" * fb["rating"] + "☆" * (5 - fb["rating"])
            tk.Label(top, text=f"{fb['complaint_code']} : {fb['complaint_title']}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_HEADING).pack(side=tk.LEFT)
            tk.Label(top, text=f"{stars} ({fb['rating']}/5)", bg=COLOR_CARD, fg=STATUS_COLOR_PENDING, font=("Segoe UI", 11, "bold")).pack(side=tk.RIGHT)

            tk.Label(card, text=f"Citizen: {fb['citizen_name']}  •  Date: {fb['submitted_at']}", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL, anchor="w").pack(fill=tk.X, pady=(2, 6))

            if fb.get("comments"):
                tk.Label(card, text=f"“{fb['comments']}”", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY, anchor="w").pack(fill=tk.X)
            if fb.get("suggestions"):
                tk.Label(card, text=f"💡 Suggestion: {fb['suggestions']}", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL, anchor="w").pack(fill=tk.X, pady=(3, 0))

    # --------------------------------------------------------------------------
    # 11. REPORTS & CSV EXPORT
    # --------------------------------------------------------------------------
    def _render_reports(self):
        container = ScrollableFrame(self.content_area, bg=COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = container.scrollable_content

        tk.Label(content, text="Municipal Analytics Reports & CSV Export", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X, pady=(0, 4))
        tk.Label(content, text="Generate spreadsheet data exports with date range and department filtering.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(0, 15))

        export_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=25, pady=20)
        export_card.configure(highlightbackground=COLOR_BORDER)
        export_card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(export_card, text="Filter & Export Complaints CSV", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w", pady=(0, 10))

        # Filter Inputs
        grid = tk.Frame(export_card, bg=COLOR_CARD)
        grid.pack(fill=tk.X, pady=(0, 15))

        tk.Label(grid, text="Department Filter:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=0, column=0, sticky="w", pady=4)
        dept_cmb = ttk.Combobox(grid, values=["All Departments"] + DEPARTMENTS, state="readonly", width=22)
        dept_cmb.set("All Departments")
        dept_cmb.grid(row=0, column=1, sticky="w", padx=(10, 20), pady=4)

        tk.Label(grid, text="Status Filter:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=0, column=2, sticky="w", pady=4)
        st_cmb = ttk.Combobox(grid, values=["All Statuses", "NEW", "VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"], state="readonly", width=18)
        st_cmb.set("All Statuses")
        st_cmb.grid(row=0, column=3, sticky="w", padx=(10, 0), pady=4)

        def do_export():
            fpath = filedialog.asksaveasfilename(
                title="Export Complaints to CSV",
                defaultextension=".csv",
                filetypes=[("CSV Spreadsheet", "*.csv")],
                initialfile="CivicFix_Complaints_Report.csv"
            )
            if not fpath:
                return

            ok, cnt, msg = export_complaints_to_csv(
                filepath=fpath,
                department_filter=dept_cmb.get(),
                status_filter=st_cmb.get()
            )
            if ok:
                messagebox.showinfo("Export Complete", msg)
            else:
                messagebox.showerror("Export Failed", msg)

        btn_row = tk.Frame(export_card, bg=COLOR_CARD)
        btn_row.pack(anchor="w", fill=tk.X)

        exp1_btn = tk.Button(btn_row, text="📥  Export Complaints CSV", bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=8, cursor="hand2", command=do_export)
        exp1_btn.pack(side=tk.LEFT, padx=(0, 10))
        apply_button_hover(exp1_btn, COLOR_PRIMARY, COLOR_HOVER)

        def do_export_workers():
            fpath = filedialog.asksaveasfilename(
                title="Export Worker Performance to CSV",
                defaultextension=".csv",
                filetypes=[("CSV Spreadsheet", "*.csv")],
                initialfile="CivicFix_Worker_Performance.csv"
            )
            if not fpath:
                return
            ok, cnt, msg = export_worker_performance_csv(fpath)
            if ok:
                messagebox.showinfo("Export Complete", msg)
            else:
                messagebox.showerror("Export Failed", msg)

        exp2_btn = tk.Button(btn_row, text="📥  Export Workers CSV", bg=COLOR_SECONDARY, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=8, cursor="hand2", command=do_export_workers)
        exp2_btn.pack(side=tk.LEFT, padx=(0, 10))
        apply_button_hover(exp2_btn, COLOR_SECONDARY, "#8E9C76")

        def do_export_depts():
            fpath = filedialog.asksaveasfilename(
                title="Export Department KPIs to CSV",
                defaultextension=".csv",
                filetypes=[("CSV Spreadsheet", "*.csv")],
                initialfile="CivicFix_Department_KPIs.csv"
            )
            if not fpath:
                return
            ok, cnt, msg = export_department_kpi_csv(fpath)
            if ok:
                messagebox.showinfo("Export Complete", msg)
            else:
                messagebox.showerror("Export Failed", msg)

        exp3_btn = tk.Button(btn_row, text="📥  Export Department KPIs CSV", bg=STATUS_COLOR_RESOLVED, fg="#FFFFFF", font=FONT_BODY_BOLD, relief="flat", padx=16, pady=8, cursor="hand2", command=do_export_depts)
        exp3_btn.pack(side=tk.LEFT)
        apply_button_hover(exp3_btn, STATUS_COLOR_RESOLVED, "#3F7A52")

        # Department Efficiency & Turnaround Table
        dept_eff_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        dept_eff_card.configure(highlightbackground=COLOR_BORDER)
        dept_eff_card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(dept_eff_card, text="🏢 Department Resolution Efficiency & Turnaround Time", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w", pady=(0, 4))
        tk.Label(dept_eff_card, text="Departmental turnaround metrics, active workloads, and completion rates.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(0, 10))

        dept_cols = [
            ("department", "Department", 180),
            ("total_complaints", "Total Tasks", 110),
            ("resolved_count", "Resolved", 100),
            ("active_count", "Active Pending", 110),
            ("overdue_count", "Overdue", 100),
            ("resolution_rate_pct", "Resolution %", 110),
            ("avg_turnaround_hours", "Avg Turnaround (Hrs)", 150),
        ]
        dept_table = DataTable(dept_eff_card, columns=dept_cols)
        dept_table.pack(fill=tk.X)
        dept_table.set_rows(get_department_efficiency())

        # Worker Performance Report
        perf_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        perf_card.configure(highlightbackground=COLOR_BORDER)
        perf_card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(perf_card, text="👷 Field Worker Performance Breakdown", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w", pady=(0, 10))

        cols = [
            ("full_name", "Worker Full Name", 200),
            ("department", "Department", 180),
            ("total_assigned", "Total Tasks", 120),
            ("completed", "Resolved Tasks", 130),
            ("pending", "Pending Tasks", 130),
            ("delayed", "Delayed Tasks", 120),
        ]

        table = DataTable(perf_card, columns=cols)
        table.pack(fill=tk.X)
        table.set_rows(get_worker_performance_stats())

        # Locality Hotspots Table
        loc_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        loc_card.configure(highlightbackground=COLOR_BORDER)
        loc_card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(loc_card, text="📍 Locality Hotspots & Grievance Distribution", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w", pady=(0, 4))
        tk.Label(loc_card, text="Geographic frequency of civic complaints and active emergencies across city wards.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(0, 10))

        loc_cols = [
            ("locality", "Locality / Ward", 220),
            ("total_complaints", "Total Issues", 130),
            ("resolved_count", "Resolved", 120),
            ("open_count", "Active Open", 120),
            ("emergency_count", "Emergency Hazards", 140),
        ]
        loc_table = DataTable(loc_card, columns=loc_cols)
        loc_table.pack(fill=tk.X)
        loc_table.set_rows(get_locality_distribution())

        # Citizen Satisfaction Analytics Card
        sat = get_satisfaction_metrics()
        sat_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        sat_card.configure(highlightbackground=COLOR_BORDER)
        sat_card.pack(fill=tk.X)

        tk.Label(sat_card, text="⭐ Citizen Satisfaction & Rating Index", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w", pady=(0, 6))

        sat_row = tk.Frame(sat_card, bg=COLOR_CARD)
        sat_row.pack(fill=tk.X, pady=(4, 0))

        tk.Label(sat_row, text=f"{sat['avg_rating']} / 5.0", bg=COLOR_CARD, fg=STATUS_COLOR_PENDING, font=("Segoe UI", 24, "bold")).pack(side=tk.LEFT, padx=(0, 15))
        tk.Label(sat_row, text=f"Based on {sat['total_feedback']} verified citizen reviews ({sat['satisfaction_pct']}% approval rating)\n5★: {sat['stars_5']}  |  4★: {sat['stars_4']}  |  3★: {sat['stars_3']}  |  2★: {sat['stars_2']}  |  1★: {sat['stars_1']}", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY, justify="left").pack(side=tk.LEFT)

    # --------------------------------------------------------------------------
    # 12. ACTION AUDIT LOG
    # --------------------------------------------------------------------------
    def _render_audit_log(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Administrative Action Audit History", bg=COLOR_BG, fg=COLOR_HEADINGS, font=("Segoe UI", 16, "bold"), anchor="w").pack(fill=tk.X)
        tk.Label(container, text="Immutable chronological audit trail of all administrative decisions, assignments, and approvals.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY, anchor="w").pack(fill=tk.X, pady=(2, 12))

        cols = [
            ("performed_at", "Timestamp", 150),
            ("admin_username", "Administrator", 140),
            ("action_type", "Action", 160),
            ("complaint_code", "Complaint", 130),
            ("details", "Details", 380),
        ]

        table = DataTable(container, columns=cols)
        table.pack(fill=tk.BOTH, expand=True)
        table.set_rows(self.controller.fetch_audit_history())
