"""
CivicFix Citizen Portal GUI Module
Implements the complete Citizen desktop experience: issue reporting with photo upload
and Pillow preview, unique CFX ID generation, personal complaint listing with filters,
visual chronological lifecycle tracking, neighborhood issue supporting, and resolution rating.
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
from modules.citizen import CitizenController
from services.complaint_service import CATEGORIES
from utils.image_handler import save_image_to_uploads, load_thumbnail, get_absolute_path
from gui.comparison_widget import BeforeAfterComparisonWidget
from authentication.auth import current_session


class CitizenDashboard(tk.Frame):
    """
    Main Citizen Container managing Sidebar navigation and content views:
    - Overview Dashboard
    - Report an Issue
    - My Complaints
    - Track Complaint (Visual Timeline)
    - Community Issues (Support Existing)
    - Notifications
    - My Profile
    """
    def __init__(self, parent: tk.Widget, user: Dict[str, Any], profile: Dict[str, Any], **kwargs):
        super().__init__(parent, bg=COLOR_BG, **kwargs)
        self.user = user
        self.profile = profile or {}
        self.controller = CitizenController(citizen_id=self.user["id"])

        # Image preview references to prevent Python GC
        self._image_tk_cache = []

        self._build_ui()

    def _build_ui(self):
        # Main Layout: Sidebar on Left, Content Area on Right
        self.sidebar = tk.Frame(self, bg=COLOR_SIDEBAR, width=240, bd=0)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.content_area = tk.Frame(self, bg=COLOR_BG)
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._nav_buttons = {}
        self._active_tab = None

        # Build Navigation Menu
        self._build_sidebar()

        # Start on Overview Dashboard
        self.navigate_to("dashboard")

    # --------------------------------------------------------------------------
    # SIDEBAR NAVIGATION
    # --------------------------------------------------------------------------
    def _build_sidebar(self):
        # Citizen Profile Mini Card in Sidebar
        user_card = tk.Frame(self.sidebar, bg="#33493C", padx=15, pady=15, bd=1, relief="solid")
        user_card.configure(highlightbackground="#4A6A55")
        user_card.pack(fill=tk.X, padx=12, pady=(15, 15))

        tk.Label(
            user_card,
            text="👤  CITIZEN PORTAL",
            bg="#33493C",
            fg=COLOR_ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        name = self.profile.get("full_name") or self.user.get("username", "Citizen")
        tk.Label(
            user_card,
            text=name,
            bg="#33493C",
            fg="#FFFFFF",
            font=FONT_HEADING,
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 0))

        loc = self.profile.get("locality", "Local Citizen")
        tk.Label(
            user_card,
            text=f"📍 {loc}",
            bg="#33493C",
            fg=COLOR_BORDER,
            font=FONT_SMALL,
            anchor="w"
        ).pack(fill=tk.X)

        # Navigation Items
        menu_items = [
            ("dashboard", "📊  Dashboard"),
            ("report", "📝  Report an Issue"),
            ("my_complaints", "📋  My Complaints"),
            ("track", "🔍  Track Complaint"),
            ("support", "👥  Community Issues"),
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

            # Bind hover
            def _bind_btn(b=btn, tid=tab_id):
                def on_enter(e):
                    if self._active_tab != tid:
                        b.configure(bg=COLOR_SIDEBAR_HOVER)
                def on_leave(e):
                    if self._active_tab != tid:
                        b.configure(bg=COLOR_SIDEBAR)
                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
            _bind_btn()

            self._nav_buttons[tab_id] = btn

    def navigate_to(self, tab_name: str, **kwargs):
        """Switches active view and updates sidebar highlight."""
        if self._active_tab == tab_name and not kwargs:
            return

        self._active_tab = tab_name

        # Update button highlights
        for t_id, btn in self._nav_buttons.items():
            if t_id == tab_name:
                btn.configure(bg=COLOR_PRIMARY, fg="#FFFFFF", font=FONT_BODY_BOLD)
            else:
                btn.configure(bg=COLOR_SIDEBAR, fg=COLOR_SIDEBAR_TEXT, font=FONT_BODY)

        # Clear Content Area
        for child in self.content_area.winfo_children():
            child.destroy()

        # Render chosen screen
        if tab_name == "dashboard":
            self._render_dashboard()
        elif tab_name == "report":
            self._render_report_form()
        elif tab_name == "my_complaints":
            self._render_my_complaints()
        elif tab_name == "track":
            target_id = kwargs.get("complaint_id")
            self._render_track_complaint(target_id)
        elif tab_name == "support":
            self._render_community_support()
        elif tab_name == "notifications":
            self._render_notifications()
        elif tab_name == "profile":
            self._render_profile()

    # --------------------------------------------------------------------------
    # 1. OVERVIEW DASHBOARD VIEW
    # --------------------------------------------------------------------------
    def _render_dashboard(self):
        container = ScrollableFrame(self.content_area, bg=COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = container.scrollable_content

        # Welcome Banner Card
        banner = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=25, pady=20)
        banner.configure(highlightbackground=COLOR_BORDER)
        banner.pack(fill=tk.X, pady=(0, 20))

        top_row = tk.Frame(banner, bg=COLOR_CARD)
        top_row.pack(fill=tk.X)

        tk.Label(
            top_row,
            text=f"Welcome back, {self.profile.get('full_name', self.user['username'])}!",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 16, "bold"),
            anchor="w"
        ).pack(side=tk.LEFT)

        report_btn = tk.Button(
            top_row,
            text="➕  Report New Civic Issue",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_HOVER,
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=lambda: self.navigate_to("report")
        )
        report_btn.pack(side=tk.RIGHT)
        apply_button_hover(report_btn, COLOR_PRIMARY, COLOR_HOVER)

        tk.Label(
            banner,
            text=f"Locality: {self.profile.get('locality', 'Indiranagar')}  •  CivicFix Centralized Issue Tracking",
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=FONT_BODY,
            anchor="w"
        ).pack(fill=tk.X, pady=(4, 0))

        # KPI Metrics Row
        stats = self.controller.get_dashboard_metrics()
        stats_frame = tk.Frame(content, bg=COLOR_BG)
        stats_frame.pack(fill=tk.X, pady=(0, 25))

        StatCard(stats_frame, "Total Filed", value=stats["total"], subtitle="All reports submitted by you", accent_color=COLOR_PRIMARY, icon="📋").pack(side=tk.LEFT, padx=(0, 15))
        StatCard(stats_frame, "Pending Review", value=stats["pending"], subtitle="Awaiting admin verification", accent_color=STATUS_COLOR_PENDING, icon="⏳").pack(side=tk.LEFT, padx=(0, 15))
        StatCard(stats_frame, "In Progress", value=stats["in_progress"], subtitle="Field worker assigned", accent_color=STATUS_COLOR_IN_PROGRESS, icon="🔧").pack(side=tk.LEFT, padx=(0, 15))
        StatCard(stats_frame, "Resolved", value=stats["resolved"], subtitle="Fixed and verified", accent_color=STATUS_COLOR_RESOLVED, icon="✓").pack(side=tk.LEFT, padx=(0, 15))
        StatCard(stats_frame, "Reopened", value=stats["reopened"], subtitle="Under re-inspection", accent_color=STATUS_COLOR_PENDING, icon="🔄").pack(side=tk.LEFT)

        # Recent Complaints Section
        recent_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=18)
        recent_card.configure(highlightbackground=COLOR_BORDER)
        recent_card.pack(fill=tk.X, pady=(0, 20))

        sec_header = tk.Frame(recent_card, bg=COLOR_CARD)
        sec_header.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            sec_header,
            text="Recent Complaints",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_TITLE
        ).pack(side=tk.LEFT)

        view_all_btn = tk.Button(
            sec_header,
            text="View All Complaints →",
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            activebackground=COLOR_BG,
            activeforeground=COLOR_HOVER,
            font=FONT_BODY_BOLD,
            relief="flat",
            cursor="hand2",
            command=lambda: self.navigate_to("my_complaints")
        )
        view_all_btn.pack(side=tk.RIGHT)
        apply_button_hover(view_all_btn, COLOR_CARD, COLOR_BG, COLOR_PRIMARY, COLOR_HOVER)

        recent_items = self.controller.fetch_my_complaints()[:5]

        if not recent_items:
            tk.Label(
                recent_card,
                text="You haven't submitted any complaints yet. Click 'Report New Civic Issue' above to get started!",
                bg=COLOR_CARD,
                fg=COLOR_BODY,
                font=FONT_BODY,
                pady=20
            ).pack()
        else:
            table_cols = [
                ("complaint_id", "Complaint ID", 140),
                ("title", "Issue Title", 280),
                ("category", "Category", 180),
                ("locality", "Locality", 140),
                ("priority", "Priority", 110),
                ("status", "Status", 150),
                ("submitted_at", "Date Filed", 140),
            ]
            recent_table = DataTable(
                recent_card,
                columns=table_cols,
                on_double_click=lambda row: self.navigate_to("track", complaint_id=row["complaint_id"])
            )
            recent_table.pack(fill=tk.X, pady=(0, 10))
            recent_table.set_rows(recent_items)

            tk.Label(
                recent_card,
                text="💡 Tip: Double-click any row to view its visual progress timeline and before/after photos.",
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=FONT_SMALL,
                anchor="w"
            ).pack(fill=tk.X)

    # --------------------------------------------------------------------------
    # 2. REPORT NEW ISSUE VIEW
    # --------------------------------------------------------------------------
    def _render_report_form(self):
        scroll_container = ScrollableFrame(self.content_area, bg=COLOR_BG)
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        content = scroll_container.scrollable_content

        # Header Title
        tk.Label(
            content,
            text="Report a New Civic Issue",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 18, "bold"),
            anchor="w"
        ).pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            content,
            text="Submit details regarding road hazards, waste, lighting, or drainage. Your complaint will generate a unique CFX ID.",
            bg=COLOR_BG,
            fg=COLOR_BODY,
            font=FONT_BODY,
            anchor="w"
        ).pack(fill=tk.X, pady=(0, 15))

        # Form Card Container
        form_card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=30, pady=25)
        form_card.configure(highlightbackground=COLOR_BORDER)
        form_card.pack(fill=tk.BOTH, expand=True)

        # 1. Issue Title
        tk.Label(form_card, text="Complaint Title *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        title_entry = tk.Entry(form_card, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        title_entry.pack(fill=tk.X, ipady=4, pady=(0, 12))

        # 2. Category & Locality in 2 Columns
        cat_loc_frame = tk.Frame(form_card, bg=COLOR_CARD)
        cat_loc_frame.pack(fill=tk.X, pady=(0, 12))

        # Left Column: Category
        col_cat = tk.Frame(cat_loc_frame, bg=COLOR_CARD)
        col_cat.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        tk.Label(col_cat, text="Issue Category *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        cat_combo = ttk.Combobox(col_cat, values=CATEGORIES, state="readonly", font=FONT_BODY)
        cat_combo.set(CATEGORIES[0])
        cat_combo.pack(fill=tk.X, ipady=2)

        # Right Column: Locality
        col_loc = tk.Frame(cat_loc_frame, bg=COLOR_CARD)
        col_loc.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        tk.Label(col_loc, text="Locality / Area *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        loc_entry = tk.Entry(col_loc, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        loc_entry.insert(0, self.profile.get("locality", "Indiranagar"))
        loc_entry.pack(fill=tk.X, ipady=4)

        # 3. Location & Ward in 2 Columns
        loc_ward_frame = tk.Frame(form_card, bg=COLOR_CARD)
        loc_ward_frame.pack(fill=tk.X, pady=(0, 12))

        col_locat = tk.Frame(loc_ward_frame, bg=COLOR_CARD)
        col_locat.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        tk.Label(col_locat, text="Specific Location / Landmark *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        location_entry = tk.Entry(col_locat, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        location_entry.pack(fill=tk.X, ipady=4)

        col_ward = tk.Frame(loc_ward_frame, bg=COLOR_CARD)
        col_ward.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        tk.Label(col_ward, text="Ward Number (Optional)", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        ward_entry = tk.Entry(col_ward, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        ward_entry.pack(fill=tk.X, ipady=4)

        # 4. Description Text Area
        tk.Label(form_card, text="Detailed Description *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 3))
        desc_text = tk.Text(form_card, height=4, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid", wrap="word")
        desc_text.pack(fill=tk.X, pady=(0, 15))

        # 5. Image Upload & Pillow Preview Container
        img_section = tk.Frame(form_card, bg=COLOR_BG, bd=1, relief="solid", padx=15, pady=12)
        img_section.configure(highlightbackground=COLOR_BORDER)
        img_section.pack(fill=tk.X, pady=(0, 15))

        selected_image_path = [None]  # Mutable box

        img_btn_row = tk.Frame(img_section, bg=COLOR_BG)
        img_btn_row.pack(fill=tk.X)

        tk.Label(
            img_btn_row,
            text="📷  Evidence Photo Upload:",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=FONT_BODY_BOLD
        ).pack(side=tk.LEFT)

        preview_lbl = tk.Label(img_section, bg=COLOR_BG, text="No image selected yet (Optional)", fg=COLOR_MUTED)
        preview_lbl.pack(pady=8)

        def choose_image():
            fpath = filedialog.askopenfilename(
                title="Select Issue Evidence Photo",
                filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp")]
            )
            if not fpath:
                return

            saved_rel = save_image_to_uploads(fpath, subfolder="complaint_images")
            if saved_rel:
                selected_image_path[0] = saved_rel
                photo = load_thumbnail(saved_rel, max_width=220, max_height=140)
                if photo:
                    self._image_tk_cache.append(photo)
                    preview_lbl.configure(image=photo, text="")
                else:
                    preview_lbl.configure(text=f"✓ Photo saved: {os.path.basename(saved_rel)}")
                clear_img_btn.pack(side=tk.LEFT, padx=10)

        def clear_image():
            selected_image_path[0] = None
            preview_lbl.configure(image="", text="No image selected (Optional)")
            clear_img_btn.pack_forget()

        pick_btn = tk.Button(
            img_btn_row,
            text="Browse Image... (JPG, PNG)",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            activebackground=COLOR_ACCENT,
            activeforeground=COLOR_HEADINGS,
            font=FONT_BODY,
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=10,
            pady=4,
            command=choose_image
        )
        pick_btn.pack(side=tk.LEFT, padx=12)
        apply_button_hover(pick_btn, COLOR_CARD, COLOR_ACCENT, COLOR_HEADINGS, COLOR_HEADINGS)

        clear_img_btn = tk.Button(
            img_btn_row,
            text="✕ Remove Photo",
            bg=COLOR_CARD,
            fg=COLOR_DANGER,
            activebackground="#FDF2F2",
            activeforeground=COLOR_DANGER,
            font=FONT_SMALL,
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=8,
            pady=4,
            command=clear_image
        )

        # 6. Checkboxes: Emergency & Anonymous
        flags_row = tk.Frame(form_card, bg=COLOR_CARD)
        flags_row.pack(fill=tk.X, pady=(0, 20))

        emergency_var = tk.BooleanVar(value=False)
        em_chk = tk.Checkbutton(
            flags_row,
            text="🚨  Mark as EMERGENCY (Severe hazard, electrical spark, or massive flooding)",
            variable=emergency_var,
            bg=COLOR_CARD,
            fg=COLOR_DANGER,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_DANGER,
            font=FONT_BODY_BOLD
        )
        em_chk.pack(anchor="w", pady=(0, 4))

        anon_var = tk.BooleanVar(value=False)
        anon_chk = tk.Checkbutton(
            flags_row,
            text="🔒  Anonymous Reporting (Hide my identity from public issue displays)",
            variable=anon_var,
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_HEADINGS,
            font=FONT_BODY
        )
        anon_chk.pack(anchor="w")

        # Submission Handler
        def handle_submit():
            t = title_entry.get()
            cat = cat_combo.get()
            loc = loc_entry.get()
            landmark = location_entry.get()
            ward = ward_entry.get()
            desc = desc_text.get("1.0", tk.END)
            is_em = emergency_var.get()
            is_an = anon_var.get()
            img_p = selected_image_path[0]

            ok, c_code, c_id, msg = self.controller.submit_issue(
                title=t,
                description=desc,
                category=cat,
                location=landmark,
                locality=loc,
                ward_number=ward,
                image_path=img_p,
                is_emergency=is_em,
                is_anonymous=is_an
            )

            if not ok:
                messagebox.showerror("Submission Error", msg)
                return

            messagebox.showinfo(
                "Complaint Registered",
                f"Your complaint has been successfully submitted!\n\n"
                f"Unique Complaint ID: {c_code}\n\n"
                f"You can now track its progress under 'My Complaints' or 'Track Complaint'."
            )
            self.navigate_to("track", complaint_id=c_code)

        # Submit Button
        submit_btn = tk.Button(
            form_card,
            text="Submit Issue & Generate CFX ID →",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_HOVER,
            activeforeground="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=handle_submit
        )
        submit_btn.pack(fill=tk.X, pady=(5, 0))
        apply_button_hover(submit_btn, COLOR_PRIMARY, COLOR_HOVER)

    # --------------------------------------------------------------------------
    # 3. MY COMPLAINTS VIEW
    # --------------------------------------------------------------------------
    def _render_my_complaints(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Header Title
        tk.Label(
            container,
            text="My Registered Complaints",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 16, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            container,
            text="Track, review, or reopen issues you have reported. Double-click any row to view its visual lifecycle timeline.",
            bg=COLOR_BG,
            fg=COLOR_BODY,
            font=FONT_BODY,
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 12))

        # Filter & Search Bar Row
        toolbar = tk.Frame(container, bg=COLOR_BG)
        toolbar.pack(fill=tk.X, pady=(0, 12))

        # Search box
        search_box = SearchBar(
            toolbar,
            placeholder="Search by Title, ID, or Street...",
            on_search=lambda q: apply_filters()
        )
        search_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Category Filter
        cat_choices = ["All Categories"] + CATEGORIES
        cat_combo = ttk.Combobox(toolbar, values=cat_choices, state="readonly", width=22)
        cat_combo.set("All Categories")
        cat_combo.pack(side=tk.LEFT, padx=(0, 10))
        cat_combo.bind("<<ComboboxSelected>>", lambda e: apply_filters())

        # Status Filter
        status_choices = [
            "All Statuses", "NEW", "VERIFIED", "ASSIGNED",
            "IN_PROGRESS", "COMPLETED_PENDING_VERIFICATION",
            "RESOLVED", "CLOSED", "REOPENED", "REJECTED"
        ]
        status_combo = ttk.Combobox(toolbar, values=status_choices, state="readonly", width=18)
        status_combo.set("All Statuses")
        status_combo.pack(side=tk.LEFT, padx=(0, 10))
        status_combo.bind("<<ComboboxSelected>>", lambda e: apply_filters())

        # Table Component
        table_cols = [
            ("complaint_id", "Complaint ID", 140),
            ("title", "Issue Title", 260),
            ("category", "Category", 180),
            ("location", "Location / Street", 180),
            ("priority", "Priority", 110),
            ("status", "Current Status", 160),
            ("submitted_at", "Date Reported", 140),
        ]

        table = DataTable(
            container,
            columns=table_cols,
            on_double_click=lambda row: self.navigate_to("track", complaint_id=row["complaint_id"])
        )
        table.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        def apply_filters():
            q = search_box.get_text()
            cat = cat_combo.get()
            st = status_combo.get()
            filtered = self.controller.fetch_my_complaints(
                search_query=q,
                category_filter=cat,
                status_filter=st
            )
            table.set_rows(filtered)

        # Action Buttons Row
        action_bar = tk.Frame(container, bg=COLOR_BG)
        action_bar.pack(fill=tk.X)

        def on_track_clicked():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Issue", "Please select a complaint from the table to track.")
                return
            self.navigate_to("track", complaint_id=sel["complaint_id"])

        def on_feedback_clicked():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Issue", "Please select a complaint to rate.")
                return
            if sel["status"] not in ("RESOLVED", "CLOSED"):
                messagebox.showinfo("Not Ready", f"Feedback can only be provided after an issue is resolved.\nCurrent status: {sel['status']}")
                return
            self._show_feedback_modal(sel["complaint_id"])

        def on_reopen_clicked():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Issue", "Please select a complaint to reopen.")
                return
            if sel["status"] not in ("RESOLVED", "CLOSED", "REJECTED"):
                messagebox.showinfo("Not Reopenable", f"Only resolved, closed, or rejected complaints can be reopened.\nCurrent status: {sel['status']}")
                return
            self._show_reopen_modal(sel["complaint_id"])

        track_btn = tk.Button(
            action_bar,
            text="🔍  View Details & Timeline",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_HOVER,
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=on_track_clicked
        )
        track_btn.pack(side=tk.LEFT, padx=(0, 10))
        apply_button_hover(track_btn, COLOR_PRIMARY, COLOR_HOVER)

        rate_btn = tk.Button(
            action_bar,
            text="⭐  Rate & Give Feedback",
            bg=STATUS_COLOR_RESOLVED,
            fg="#FFFFFF",
            activebackground="#3F7A52",
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=on_feedback_clicked
        )
        rate_btn.pack(side=tk.LEFT, padx=(0, 10))
        apply_button_hover(rate_btn, STATUS_COLOR_RESOLVED, "#3F7A52")

        reopen_btn = tk.Button(
            action_bar,
            text="🔄  Request Reopen",
            bg=STATUS_COLOR_PENDING,
            fg="#FFFFFF",
            activebackground="#D38F2E",
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=on_reopen_clicked
        )
        reopen_btn.pack(side=tk.LEFT)
        apply_button_hover(reopen_btn, STATUS_COLOR_PENDING, "#D38F2E")

        # Initial Load
        apply_filters()

    # --------------------------------------------------------------------------
    # 4. TRACK COMPLAINT & VISUAL TIMELINE VIEW
    # --------------------------------------------------------------------------
    def _render_track_complaint(self, target_complaint_id: Optional[str] = None):
        container = ScrollableFrame(self.content_area, bg=COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = container.scrollable_content

        # Header Title
        tk.Label(
            content,
            text="Issue Progress & Visual Lifecycle Timeline",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 16, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        # Selector Row if not pre-selected
        my_list = self.controller.fetch_my_complaints()
        if not my_list:
            tk.Label(
                content,
                text="No complaints recorded under your account to track.",
                bg=COLOR_BG,
                fg=COLOR_BODY,
                font=FONT_BODY,
                pady=20
            ).pack()
            return

        selector_bar = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=15, pady=10)
        selector_bar.configure(highlightbackground=COLOR_BORDER)
        selector_bar.pack(fill=tk.X, pady=(8, 15))

        tk.Label(selector_bar, text="Select Complaint to Track:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(side=tk.LEFT, padx=(0, 10))

        id_options = [f"{c['complaint_id']} - {c['title'][:40]}" for c in my_list]
        selected_code_var = tk.StringVar()

        # Find initial match
        init_idx = 0
        if target_complaint_id:
            for idx, opt in enumerate(id_options):
                if target_complaint_id in opt:
                    init_idx = idx
                    break

        selected_code_var.set(id_options[init_idx])

        combo = ttk.Combobox(selector_bar, textvariable=selected_code_var, values=id_options, state="readonly", width=55)
        combo.pack(side=tk.LEFT)

        # Target card dynamic frame
        details_frame = tk.Frame(content, bg=COLOR_BG)
        details_frame.pack(fill=tk.BOTH, expand=True)

        def load_details(*args):
            for child in details_frame.winfo_children():
                child.destroy()

            chosen_str = selected_code_var.get()
            if not chosen_str:
                return
            chosen_code = chosen_str.split(" - ")[0]

            data = self.controller.fetch_tracking_details(chosen_code)
            if not data:
                tk.Label(details_frame, text="Complaint not found.", bg=COLOR_BG, fg=COLOR_DANGER).pack()
                return

            self._build_complaint_details_panel(details_frame, data)

        combo.bind("<<ComboboxSelected>>", load_details)
        load_details()

    def _build_complaint_details_panel(self, parent: tk.Widget, data: Dict[str, Any]):
        # Metadata Card
        meta_card = tk.Frame(parent, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=15)
        meta_card.configure(highlightbackground=COLOR_BORDER)
        meta_card.pack(fill=tk.X, pady=(0, 15))

        top_info = tk.Frame(meta_card, bg=COLOR_CARD)
        top_info.pack(fill=tk.X)

        tk.Label(
            top_info,
            text=f"{data['complaint_id']} : {data['title']}",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 14, "bold"),
            anchor="w"
        ).pack(side=tk.LEFT)

        badges_box = tk.Frame(top_info, bg=COLOR_CARD)
        badges_box.pack(side=tk.RIGHT)

        PriorityBadge(badges_box, data["priority"]).pack(side=tk.LEFT, padx=4)
        StatusBadge(badges_box, data["status"]).pack(side=tk.LEFT, padx=4)

        # Sub details
        sub_info = tk.Frame(meta_card, bg=COLOR_CARD)
        sub_info.pack(fill=tk.X, pady=(8, 0))

        tk.Label(
            sub_info,
            text=f"📂 Category: {data['category']}   |   📍 Location: {data['location']}, {data['locality']}   |   📅 Filed: {data['submitted_at']}",
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=FONT_SMALL,
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            meta_card,
            text=f"Description: {data['description']}",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_BODY,
            wraplength=950,
            justify="left",
            anchor="w"
        ).pack(fill=tk.X, pady=(10, 0))

        # Side-by-Side Before/After Photo Resolution Inspection
        comp_widget = BeforeAfterComparisonWidget(
            parent,
            complaint_data=data,
            max_photo_width=340,
            max_photo_height=200
        )
        comp_widget.pack(fill=tk.X, pady=(0, 15))

        # Visual Chronological Timeline
        timeline_card = tk.Frame(parent, bg=COLOR_CARD, bd=1, relief="solid", padx=20, pady=15)
        timeline_card.configure(highlightbackground=COLOR_BORDER)
        timeline_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            timeline_card,
            text="⏱️  Chronological Lifecycle History",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_TITLE,
            anchor="w"
        ).pack(fill=tk.X, pady=(0, 10))

        timeline_items = data.get("timeline", [])
        if not timeline_items:
            tk.Label(timeline_card, text="No status transitions logged yet.", bg=COLOR_CARD, fg=COLOR_BODY).pack(pady=10)
        else:
            for idx, entry in enumerate(timeline_items):
                step_box = tk.Frame(timeline_card, bg=COLOR_CARD)
                step_box.pack(fill=tk.X, pady=4)

                # Step index circle
                step_num = tk.Label(
                    step_box,
                    text=f" {idx + 1} ",
                    bg=COLOR_PRIMARY,
                    fg="#FFFFFF",
                    font=("Segoe UI", 9, "bold"),
                    width=3
                )
                step_num.pack(side=tk.LEFT, padx=(0, 12))

                # Step info
                info = tk.Frame(step_box, bg=COLOR_CARD)
                info.pack(side=tk.LEFT, fill=tk.X, expand=True)

                st_row = tk.Frame(info, bg=COLOR_CARD)
                st_row.pack(fill=tk.X)

                StatusBadge(st_row, entry["new_status"]).pack(side=tk.LEFT)

                tk.Label(
                    st_row,
                    text=f"  by {entry.get('changer_username', 'System')} ({entry.get('changer_role', 'SYSTEM')})  •  {entry['changed_at']}",
                    bg=COLOR_CARD,
                    fg=COLOR_BODY,
                    font=FONT_SMALL
                ).pack(side=tk.LEFT)

                if entry.get("remarks"):
                    tk.Label(
                        info,
                        text=f"Remarks: {entry['remarks']}",
                        bg=COLOR_CARD,
                        fg=COLOR_HEADINGS,
                        font=FONT_BODY,
                        anchor="w"
                    ).pack(fill=tk.X, pady=(2, 0))

    # --------------------------------------------------------------------------
    # 5. COMMUNITY ISSUES ("I ALSO FACE THIS ISSUE") VIEW
    # --------------------------------------------------------------------------
    def _render_community_support(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            container,
            text="Community Civic Issues (Support Existing)",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 16, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            container,
            text="Notice an issue already reported in your neighborhood? Click 'I Also Face This Issue' to boost its priority instead of creating a duplicate!",
            bg=COLOR_BG,
            fg=COLOR_BODY,
            font=FONT_BODY,
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 12))

        # Search Bar
        toolbar = tk.Frame(container, bg=COLOR_BG)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        search_box = SearchBar(
            toolbar,
            placeholder="Search neighborhood issues...",
            on_search=lambda q: load_browse_list()
        )
        search_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Table Component
        table_cols = [
            ("complaint_id", "ID", 130),
            ("title", "Issue Title", 280),
            ("category", "Category", 180),
            ("locality", "Locality", 140),
            ("location", "Location Landmark", 180),
            ("support_count", "Supporters", 100),
            ("status", "Status", 140),
        ]

        table = DataTable(container, columns=table_cols)
        table.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        def load_browse_list():
            q = search_box.get_text()
            issues = self.controller.browse_community_issues(search_query=q)
            table.set_rows(issues)

        # Support Action Bar
        action_bar = tk.Frame(container, bg=COLOR_BG)
        action_bar.pack(fill=tk.X)

        def handle_support():
            sel = table.get_selected_row()
            if not sel:
                messagebox.showwarning("Select Issue", "Please select an issue to support.")
                return

            c_id = sel["complaint_id"]
            # Look up internal ID
            comp = self.controller.fetch_tracking_details(c_id)
            if not comp:
                return

            ok, new_cnt, msg = self.controller.support_existing_issue(comp["id"])
            if ok:
                messagebox.showinfo("Support Recorded", msg)
                load_browse_list()
            else:
                messagebox.showwarning("Already Supported", msg)

        sup_btn = tk.Button(
            action_bar,
            text="👍  I Also Face This Issue (+1)",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_HOVER,
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=handle_support
        )
        sup_btn.pack(side=tk.LEFT)
        apply_button_hover(sup_btn, COLOR_PRIMARY, COLOR_HOVER)

        load_browse_list()

    # --------------------------------------------------------------------------
    # 6. NOTIFICATIONS VIEW
    # --------------------------------------------------------------------------
    def _render_notifications(self):
        container = ScrollableFrame(self.content_area, bg=COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        content = container.scrollable_content

        top_row = tk.Frame(content, bg=COLOR_BG)
        top_row.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            top_row,
            text="Notifications & Status Updates",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)

        def mark_read():
            self.controller.mark_all_notifications_read()
            self.navigate_to("notifications")

        mark_btn = tk.Button(
            top_row,
            text="Mark All as Read ✓",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            activebackground=COLOR_ACCENT,
            activeforeground=COLOR_HEADINGS,
            font=FONT_SMALL,
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=10,
            pady=4,
            command=mark_read
        )
        mark_btn.pack(side=tk.RIGHT)
        apply_button_hover(mark_btn, COLOR_CARD, COLOR_ACCENT, COLOR_HEADINGS, COLOR_HEADINGS)

        notes = self.controller.get_notifications()
        if not notes:
            tk.Label(content, text="No notifications yet.", bg=COLOR_BG, fg=COLOR_BODY, font=FONT_BODY).pack(pady=20)
            return

        for n in notes:
            card = tk.Frame(content, bg=COLOR_CARD, bd=1, relief="solid", padx=15, pady=12)
            card.configure(highlightbackground=COLOR_BORDER)
            card.pack(fill=tk.X, pady=4)

            hdr = tk.Frame(card, bg=COLOR_CARD)
            hdr.pack(fill=tk.X)

            unread_pill = " ● NEW " if not n["is_read"] else ""
            tk.Label(
                hdr,
                text=f"{unread_pill}{n['title']}",
                bg=COLOR_CARD,
                fg=COLOR_PRIMARY if not n["is_read"] else COLOR_HEADINGS,
                font=FONT_BODY_BOLD
            ).pack(side=tk.LEFT)

            tk.Label(
                hdr,
                text=n["created_at"],
                bg=COLOR_CARD,
                fg=COLOR_BODY,
                font=FONT_SMALL
            ).pack(side=tk.RIGHT)

            tk.Label(
                card,
                text=n["message"],
                bg=COLOR_CARD,
                fg=COLOR_BODY,
                font=FONT_BODY,
                anchor="w",
                wraplength=950,
                justify="left"
            ).pack(fill=tk.X, pady=(4, 0))

    # --------------------------------------------------------------------------
    # 7. MY PROFILE VIEW
    # --------------------------------------------------------------------------
    def _render_profile(self):
        container = tk.Frame(self.content_area, bg=COLOR_BG, padx=30, pady=25)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            container,
            text="Citizen Profile",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 16, "bold"),
            anchor="w"
        ).pack(fill=tk.X, pady=(0, 15))

        card = tk.Frame(container, bg=COLOR_CARD, bd=1, relief="solid", padx=25, pady=20)
        card.configure(highlightbackground=COLOR_BORDER)
        card.pack(fill=tk.X)

        fields = [
            ("Full Name", self.profile.get("full_name", "N/A")),
            ("Username", self.user.get("username", "N/A")),
            ("Email Address", self.user.get("email", "N/A")),
            ("Phone Number", self.profile.get("phone", "N/A")),
            ("Locality / Ward", self.profile.get("locality", "N/A")),
            ("Street Address", self.profile.get("address", "N/A")),
            ("Role", "Verified Citizen"),
            ("Account Status", "Active" if self.user.get("is_active") else "Inactive"),
            ("Member Since", self.user.get("created_at", "N/A")),
        ]

        for label, val in fields:
            row = tk.Frame(card, bg=COLOR_CARD)
            row.pack(fill=tk.X, pady=6)

            tk.Label(row, text=f"{label}:", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_BODY_BOLD, width=18, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=str(val), bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY, anchor="w").pack(side=tk.LEFT)

    # --------------------------------------------------------------------------
    # MODAL DIALOGS: FEEDBACK & REOPEN
    # --------------------------------------------------------------------------
    def _show_feedback_modal(self, complaint_code: str):
        comp = self.controller.fetch_tracking_details(complaint_code)
        if not comp:
            return

        modal = tk.Toplevel(self)
        modal.title(f"Rate Resolution - {complaint_code}")
        modal.geometry("520x440")
        modal.configure(bg=COLOR_BG)
        modal.transient(self)
        modal.grab_set()

        container = tk.Frame(modal, bg=COLOR_CARD, padx=25, pady=20, bd=1, relief="solid")
        container.configure(highlightbackground=COLOR_BORDER)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(container, text="Citizen Feedback & Rating", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w", pady=(0, 4))
        tk.Label(container, text=f"How satisfied are you with the resolution of {complaint_code}?", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(0, 15))

        # Rating selection (1 to 5 stars)
        tk.Label(container, text="Satisfaction Rating (1 to 5 Stars) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 5))

        star_var = tk.IntVar(value=5)
        star_frame = tk.Frame(container, bg=COLOR_CARD)
        star_frame.pack(fill=tk.X, pady=(0, 15))

        for star in range(1, 6):
            tk.Radiobutton(
                star_frame,
                text=f"{star} ★",
                value=star,
                variable=star_var,
                bg=COLOR_CARD,
                fg=STATUS_COLOR_PENDING,
                activebackground=COLOR_CARD,
                font=("Segoe UI", 11, "bold")
            ).pack(side=tk.LEFT, padx=6)

        # Comments
        tk.Label(container, text="Comments on Resolution:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 2))
        comm_entry = tk.Entry(container, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        comm_entry.pack(fill=tk.X, ipady=4, pady=(0, 10))

        # Suggestions
        tk.Label(container, text="Suggestions for Civic Improvement:", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 2))
        sugg_entry = tk.Entry(container, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
        sugg_entry.pack(fill=tk.X, ipady=4, pady=(0, 15))

        def submit_fb():
            r = star_var.get()
            c = comm_entry.get()
            s = sugg_entry.get()
            ok, msg = self.controller.rate_and_review(comp["id"], r, c, s)
            if ok:
                messagebox.showinfo("Feedback Recorded", msg)
                modal.destroy()
                self._render_my_complaints()
            else:
                messagebox.showerror("Error", msg)

        sub_btn = tk.Button(
            container,
            text="Submit Feedback ✓",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_HOVER,
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            pady=8,
            cursor="hand2",
            command=submit_fb
        )
        sub_btn.pack(fill=tk.X)
        apply_button_hover(sub_btn, COLOR_PRIMARY, COLOR_HOVER)

    def _show_reopen_modal(self, complaint_code: str):
        comp = self.controller.fetch_tracking_details(complaint_code)
        if not comp:
            return

        modal = tk.Toplevel(self)
        modal.title(f"Request Reopen - {complaint_code}")
        modal.geometry("520x380")
        modal.configure(bg=COLOR_BG)
        modal.transient(self)
        modal.grab_set()

        container = tk.Frame(modal, bg=COLOR_CARD, padx=25, pady=20, bd=1, relief="solid")
        container.configure(highlightbackground=COLOR_BORDER)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(container, text="Request Complaint Reopening", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE).pack(anchor="w", pady=(0, 4))
        tk.Label(container, text=f"State why the resolution for {complaint_code} was incomplete or unresolved.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(0, 12))

        tk.Label(container, text="Reopening Reason (Required, min 10 characters) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(anchor="w", pady=(0, 2))
        reason_txt = tk.Text(container, height=4, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid", wrap="word")
        reason_txt.pack(fill=tk.X, pady=(0, 15))

        def submit_ro():
            r = reason_txt.get("1.0", tk.END).strip()
            ok, msg = self.controller.request_reopen(comp["id"], r)
            if ok:
                messagebox.showinfo("Reopened", msg)
                modal.destroy()
                self._render_my_complaints()
            else:
                messagebox.showerror("Validation Error", msg)

        ro_btn = tk.Button(
            container,
            text="Confirm Reopening Request 🔄",
            bg=STATUS_COLOR_PENDING,
            fg="#FFFFFF",
            activebackground="#D38F2E",
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            pady=8,
            cursor="hand2",
            command=submit_ro
        )
        ro_btn.pack(fill=tk.X)
        apply_button_hover(ro_btn, STATUS_COLOR_PENDING, "#D38F2E")
