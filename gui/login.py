"""
CivicFix Premium Login & Landing Portal
Implements:
1. Left Section - CivicFix Branding:
   - Civic building illustration & logo
   - Large Title: CIVICFIX
   - Subtitle: Local Civic Issue Reporting & Resolution System
   - Tagline: Report • Track • Resolve
   - Description: Together for a cleaner, safer and better community.
   - Cityscape vector illustration with buildings, trees, and roads on a native Tkinter Canvas.
2. Right Section - Login Card:
   - Modern white card with subtle shadows and borders.
   - Heading: "Welcome to CivicFix"
   - Subtitle: "Please choose your login type"
   - 3 Horizontal Role Selection Cards (Citizen, Field Worker, Admin) with active green highlighting.
   - Input fields with icons (Username/Email, Password with Show/Hide toggle).
   - Role-based authentication connected to existing database and PBKDF2 authentication.
   - Back button, demo credential autofill, and citizen self-registration modal.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any, Optional

from gui.styles import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_BG, COLOR_CARD, COLOR_ACCENT,
    COLOR_SIDEBAR, COLOR_HEADINGS, COLOR_BODY, COLOR_BORDER, COLOR_HOVER,
    COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_LIGHT_BLUE, COLOR_LIGHT_ACCENT, COLOR_TEXT,
    FONT_APP_TITLE, FONT_TITLE, FONT_HEADING, FONT_SECTION, FONT_BODY,
    FONT_BODY_BOLD, FONT_SMALL, FONT_BADGE, apply_button_hover
)
from authentication.auth import authenticate, register_citizen, register_field_worker, current_session
from services.assignment_service import DEPARTMENTS


class LoginScreen(tk.Frame):
    """
    Two-section split desktop login view:
    - Left: Civic building branding, tagline, and vector cityscape illustration.
    - Right: White login card with 3 horizontal role cards and dynamic login form.
    """
    def __init__(
        self,
        parent: tk.Widget,
        on_login_success: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], None],
        on_exit: Callable[[], None],
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_BG, **kwargs)
        self.on_login_success = on_login_success
        self.on_exit = on_exit

        # Default active role
        self.selected_role = "CITIZEN"

        self._build_two_section_ui()

    def _build_two_section_ui(self):
        # Master outer wrapper filling entire screen
        self.outer_container = tk.Frame(self, bg=COLOR_BG)
        self.outer_container.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------------------------
        # LEFT SECTION – CIVICFIX BRANDING & CITYSCAPE ILLUSTRATION (40% width)
        # ----------------------------------------------------------------------
        self.left_hero = tk.Frame(self.outer_container, bg=COLOR_SIDEBAR, width=480)
        self.left_hero.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        self.left_hero.pack_propagate(False)

        # Content frame for text and headers
        brand_content = tk.Frame(self.left_hero, bg=COLOR_SIDEBAR, padx=35, pady=30)
        brand_content.pack(side=tk.TOP, fill=tk.X)

        # Top Civic Icon & Name
        top_brand_row = tk.Frame(brand_content, bg=COLOR_SIDEBAR)
        top_brand_row.pack(anchor="w")

        tk.Label(
            top_brand_row,
            text="🏛️",
            bg=COLOR_SIDEBAR,
            fg="#FFFFFF",
            font=("Segoe UI", 32)
        ).pack(side=tk.LEFT, padx=(0, 10))

        title_box = tk.Frame(top_brand_row, bg=COLOR_SIDEBAR)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="CIVICFIX",
            bg=COLOR_SIDEBAR,
            fg="#FFFFFF",
            font=("Segoe UI", 24, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            title_box,
            text="MUNICIPAL MANAGEMENT PORTAL",
            bg=COLOR_SIDEBAR,
            fg=COLOR_ACCENT,
            font=("Segoe UI", 8, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        # Subtitle
        tk.Label(
            brand_content,
            text="Local Civic Issue Reporting & Resolution System",
            bg=COLOR_SIDEBAR,
            fg=COLOR_ACCENT,
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).pack(fill=tk.X, pady=(16, 4))

        # Tagline: Report • Track • Resolve
        tagline_frame = tk.Frame(brand_content, bg="#33493C", padx=14, pady=6)
        tagline_frame.pack(anchor="w", pady=(2, 12))

        tk.Label(
            tagline_frame,
            text="Report  •  Track  •  Resolve",
            bg="#33493C",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold")
        ).pack()

        # Description
        tk.Label(
            brand_content,
            text="Together for a cleaner, safer and better community.",
            bg=COLOR_SIDEBAR,
            fg=COLOR_BORDER,
            font=("Segoe UI", 10),
            anchor="w",
            wraplength=400,
            justify="left"
        ).pack(fill=tk.X, pady=(0, 10))

        # Cityscape Vector Illustration Canvas
        self.canvas_frame = tk.Frame(self.left_hero, bg=COLOR_SIDEBAR)
        self.canvas_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.city_canvas = tk.Canvas(
            self.canvas_frame,
            bg=COLOR_SIDEBAR,
            highlightthickness=0,
            bd=0
        )
        self.city_canvas.pack(fill=tk.BOTH, expand=True)
        self.city_canvas.bind("<Configure>", self._draw_cityscape)

        # ----------------------------------------------------------------------
        # RIGHT SECTION – LOGIN CARD
        # ----------------------------------------------------------------------
        self.right_section = tk.Frame(self.outer_container, bg=COLOR_BG, padx=40, pady=30)
        self.right_section.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Centered Login Card Frame (Rounded/Bordered with depth)
        self.login_card_outer = tk.Frame(self.right_section, bg=COLOR_CARD, bd=1, relief="solid")
        self.login_card_outer.configure(highlightbackground=COLOR_BORDER)
        self.login_card_outer.place(relx=0.5, rely=0.5, anchor="center", width=720, height=640)

        # Top Accent Header Strip
        self.card_ribbon = tk.Frame(self.login_card_outer, bg=COLOR_PRIMARY, height=5)
        self.card_ribbon.pack(fill=tk.X, side=tk.TOP)

        # Main Card Interior Content
        self.card_body = tk.Frame(self.login_card_outer, bg=COLOR_CARD, padx=40, pady=25)
        self.card_body.pack(fill=tk.BOTH, expand=True)

        # 1. Heading & Subtitle
        tk.Label(
            self.card_body,
            text="Welcome to CivicFix",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 20, "bold"),
            anchor="w"
        ).pack(fill=tk.X)

        tk.Label(
            self.card_body,
            text="Please choose your login type",
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=("Segoe UI", 11),
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 18))

        # 2. Three Role Selection Cards (Horizontal)
        self.roles_row = tk.Frame(self.card_body, bg=COLOR_CARD)
        self.roles_row.pack(fill=tk.X, pady=(0, 20))

        self.role_widgets = {}
        roles_data = [
            (
                "CITIZEN",
                "Citizen Login",
                "👤",
                "Report issues and\ntrack progress."
            ),
            (
                "WORKER",
                "Field Worker Login",
                "👷",
                "Manage and resolve\nreported issues."
            ),
            (
                "ADMIN",
                "Admin Login",
                "🛡️",
                "Manage the system and\noversee operations."
            )
        ]

        for role_id, title, icon, desc in roles_data:
            frame = tk.Frame(
                self.roles_row,
                bg=COLOR_BG,
                bd=1,
                relief="solid",
                padx=12,
                pady=12,
                cursor="hand2"
            )
            frame.configure(highlightbackground=COLOR_BORDER)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

            # Click binding to the whole card and its children
            self._bind_click_recursive(frame, lambda e, r=role_id: self.select_role(r))

            icon_lbl = tk.Label(frame, text=icon, font=("Segoe UI", 22), bg=COLOR_BG)
            icon_lbl.pack(pady=(0, 4))

            title_lbl = tk.Label(frame, text=title, font=("Segoe UI", 10, "bold"), bg=COLOR_BG, fg=COLOR_HEADINGS)
            title_lbl.pack()

            desc_lbl = tk.Label(frame, text=desc, font=("Segoe UI", 8), bg=COLOR_BG, fg=COLOR_BODY, justify="center")
            desc_lbl.pack(pady=(4, 0))

            self.role_widgets[role_id] = {
                "frame": frame,
                "icon": icon_lbl,
                "title": title_lbl,
                "desc": desc_lbl
            }

        # 3. Dynamic Form Container
        self.form_container = tk.Frame(self.card_body, bg=COLOR_CARD)
        self.form_container.pack(fill=tk.BOTH, expand=True)

        self._build_login_form_elements()

        # Apply initial active role styling
        self.select_role("CITIZEN")

    def _bind_click_recursive(self, widget: tk.Widget, callback):
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)

    # --------------------------------------------------------------------------
    # ROLE SELECTION LOGIC & VISUAL HIGHLIGHTING
    # --------------------------------------------------------------------------
    def select_role(self, role_id: str):
        """
        Updates role cards styling:
        - Selected card highlighted in Primary Sage Green (#789B83).
        - Unselected cards in warm background (#F7F5EF) with border (#E7E3D8).
        """
        self.selected_role = role_id

        for r_id, w in self.role_widgets.items():
            if r_id == role_id:
                # Active Highlighted Card
                w["frame"].configure(bg=COLOR_PRIMARY, highlightbackground=COLOR_HEADINGS)
                w["icon"].configure(bg=COLOR_PRIMARY, fg="#FFFFFF")
                w["title"].configure(bg=COLOR_PRIMARY, fg="#FFFFFF")
                w["desc"].configure(bg=COLOR_PRIMARY, fg="#FFFFFF")
            else:
                # Inactive Card
                w["frame"].configure(bg=COLOR_BG, highlightbackground=COLOR_BORDER)
                w["icon"].configure(bg=COLOR_BG, fg=COLOR_HEADINGS)
                w["title"].configure(bg=COLOR_BG, fg=COLOR_HEADINGS)
                w["desc"].configure(bg=COLOR_BG, fg=COLOR_BODY)

        # Update Role Indicator Banner
        role_labels = {
            "CITIZEN": ("Citizen Authentication", "👤 Logging in as Citizen", "citizen_rahul", "Citizen@123"),
            "WORKER": ("Field Worker Authentication", "👷 Logging in as Field Worker", "worker_raj", "Worker@123"),
            "ADMIN": ("System Administrator Authentication", "🛡️ Logging in as Administrator", "admin", "Admin@123"),
        }
        title_text, badge_text, demo_u, demo_p = role_labels.get(role_id, ("Authentication", "", "admin", "Admin@123"))

        self.form_role_badge.configure(text=badge_text)
        self.login_btn.configure(text=f"Login as {role_id.title()} →")
        self.error_lbl.configure(text="")

        # Update demo credentials label
        self.demo_user_str = demo_u
        self.demo_pass_str = demo_p
        self.demo_info_lbl.configure(text=f"⚡ Demo Credentials: {demo_u} / {demo_p}")

        # Show or hide registration link
        if role_id == "CITIZEN":
            self.register_link_btn.configure(text="New Citizen? Register here")
            self.register_link_btn.pack(side=tk.RIGHT)
        elif role_id == "WORKER":
            self.register_link_btn.configure(text="New Field Worker? Register here")
            self.register_link_btn.pack(side=tk.RIGHT)
        else:
            self.register_link_btn.pack_forget()

    # --------------------------------------------------------------------------
    # LOGIN FORM UI ELEMENTS
    # --------------------------------------------------------------------------
    def _build_login_form_elements(self):
        # Header Row for Active Form
        form_header = tk.Frame(self.form_container, bg=COLOR_CARD)
        form_header.pack(fill=tk.X, pady=(0, 10))

        self.form_role_badge = tk.Label(
            form_header,
            text="👤 Logging in as Citizen",
            bg=COLOR_ACCENT,
            fg=COLOR_HEADINGS,
            font=FONT_BADGE,
            padx=10,
            pady=4
        )
        self.form_role_badge.pack(side=tk.LEFT)

        # Field 1: Username / Email with icon
        tk.Label(
            self.form_container,
            text="Username or Email",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_BODY_BOLD
        ).pack(anchor="w", pady=(0, 2))

        user_input_box = tk.Frame(self.form_container, bg=COLOR_CARD, bd=1, relief="solid")
        user_input_box.configure(highlightbackground=COLOR_BORDER)
        user_input_box.pack(fill=tk.X, pady=(0, 12))

        tk.Label(user_input_box, text=" 👤 ", bg=COLOR_CARD, fg=COLOR_MUTED, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(6, 2))

        self.user_entry = tk.Entry(
            user_input_box,
            font=FONT_BODY,
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            insertbackground=COLOR_HEADINGS,
            bd=0,
            highlightthickness=0
        )
        self.user_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=7, padx=(0, 8))

        # Field 2: Password with icon & show/hide toggle
        tk.Label(
            self.form_container,
            text="Password",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_BODY_BOLD
        ).pack(anchor="w", pady=(0, 2))

        pass_input_box = tk.Frame(self.form_container, bg=COLOR_CARD, bd=1, relief="solid")
        pass_input_box.configure(highlightbackground=COLOR_BORDER)
        pass_input_box.pack(fill=tk.X, pady=(0, 8))

        tk.Label(pass_input_box, text=" 🔒 ", bg=COLOR_CARD, fg=COLOR_MUTED, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(6, 2))

        self.pass_entry = tk.Entry(
            pass_input_box,
            font=FONT_BODY,
            show="•",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            insertbackground=COLOR_HEADINGS,
            bd=0,
            highlightthickness=0
        )
        self.pass_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=7)

        self.is_password_visible = False
        self.toggle_eye_btn = tk.Button(
            pass_input_box,
            text="👁",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            bd=0,
            cursor="hand2",
            padx=8,
            command=self._toggle_password_visibility
        )
        self.toggle_eye_btn.pack(side=tk.RIGHT)

        # Inline Error Message Label
        self.error_lbl = tk.Label(
            self.form_container,
            text="",
            bg=COLOR_CARD,
            fg=COLOR_DANGER,
            font=FONT_SMALL,
            anchor="w"
        )
        self.error_lbl.pack(fill=tk.X, pady=(0, 8))

        # Action Buttons Row (Login button & Back button)
        action_row = tk.Frame(self.form_container, bg=COLOR_CARD)
        action_row.pack(fill=tk.X, pady=(0, 12))

        self.login_btn = tk.Button(
            action_row,
            text="Login as Citizen →",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_HOVER,
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            cursor="hand2",
            pady=10,
            command=self._handle_login_submit
        )
        self.login_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        apply_button_hover(self.login_btn, COLOR_PRIMARY, COLOR_HOVER)

        self.back_btn = tk.Button(
            action_row,
            text="← Reset Fields",
            bg=COLOR_BG,
            fg=COLOR_HEADINGS,
            activebackground=COLOR_BORDER,
            activeforeground=COLOR_HEADINGS,
            font=FONT_BODY,
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=14,
            pady=9,
            command=self._handle_back_reset
        )
        self.back_btn.pack(side=tk.RIGHT)
        apply_button_hover(self.back_btn, COLOR_BG, COLOR_BORDER, COLOR_HEADINGS, COLOR_HEADINGS)

        # Bind Enter Key
        self.user_entry.bind("<Return>", lambda e: self._handle_login_submit())
        self.pass_entry.bind("<Return>", lambda e: self._handle_login_submit())

        # Bottom Utilities: 1-Click Demo Fill & Citizen Register Link
        bottom_row = tk.Frame(self.form_container, bg=COLOR_CARD)
        bottom_row.pack(fill=tk.X, pady=(4, 0))

        demo_fill_box = tk.Frame(bottom_row, bg=COLOR_ACCENT, bd=1, relief="solid", padx=10, pady=5)
        demo_fill_box.configure(highlightbackground=COLOR_BORDER)
        demo_fill_box.pack(side=tk.LEFT)

        self.demo_info_lbl = tk.Label(
            demo_fill_box,
            text="⚡ Demo Credentials: citizen_rahul / Citizen@123",
            bg=COLOR_ACCENT,
            fg=COLOR_HEADINGS,
            font=("Segoe UI", 8)
        )
        self.demo_info_lbl.pack(side=tk.LEFT, padx=(0, 8))

        autofill_btn = tk.Button(
            demo_fill_box,
            text="Fill",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            activebackground=COLOR_PRIMARY,
            activeforeground="#FFFFFF",
            font=("Segoe UI", 8, "bold"),
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=6,
            command=self._autofill_demo
        )
        autofill_btn.pack(side=tk.LEFT)
        apply_button_hover(autofill_btn, COLOR_CARD, COLOR_BG, COLOR_HEADINGS, COLOR_HEADINGS)

        self.register_link_btn = tk.Button(
            bottom_row,
            text="New Citizen? Register here",
            bg=COLOR_CARD,
            fg=COLOR_SIDEBAR,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_PRIMARY,
            font=FONT_SMALL,
            relief="flat",
            cursor="hand2",
            command=self._open_register_modal
        )
        self.register_link_btn.pack(side=tk.RIGHT)

    def _toggle_password_visibility(self):
        if self.is_password_visible:
            self.pass_entry.configure(show="•")
            self.toggle_eye_btn.configure(text="👁")
            self.is_password_visible = False
        else:
            self.pass_entry.configure(show="")
            self.toggle_eye_btn.configure(text="🔒")
            self.is_password_visible = True

    def _autofill_demo(self):
        self.user_entry.delete(0, tk.END)
        self.user_entry.insert(0, getattr(self, "demo_user_str", "citizen_rahul"))
        self.pass_entry.delete(0, tk.END)
        self.pass_entry.insert(0, getattr(self, "demo_pass_str", "Citizen@123"))
        self.error_lbl.configure(text="")

    def _handle_back_reset(self):
        self.user_entry.delete(0, tk.END)
        self.pass_entry.delete(0, tk.END)
        self.error_lbl.configure(text="")

    # --------------------------------------------------------------------------
    # AUTHENTICATION EXECUTION
    # --------------------------------------------------------------------------
    def _handle_login_submit(self):
        ident = self.user_entry.get().strip()
        pwd = self.pass_entry.get()

        if not ident or not pwd:
            self.error_lbl.configure(text="Please enter both username/email and password.")
            return

        # Authenticate against database with PBKDF2
        success, user, profile, msg = authenticate(ident, pwd)
        if not success:
            self.error_lbl.configure(text=f"✗ {msg}")
            return

        # Validate that account role matches the selected role card
        user_role = user.get("role", "").upper()
        if user_role != self.selected_role:
            role_names = {"CITIZEN": "Citizen", "WORKER": "Field Worker", "ADMIN": "Administrator"}
            self.error_lbl.configure(
                text=f"✗ Role Mismatch: Account '{ident}' is a {role_names.get(user_role, user_role)}, not a {role_names.get(self.selected_role, self.selected_role)}."
            )
            return

        self.error_lbl.configure(text="")
        current_session.login(user, profile)
        self.on_login_success(user, profile)

    # --------------------------------------------------------------------------
    # CITYSCAPE VECTOR ILLUSTRATION (Native Tkinter Canvas)
    # --------------------------------------------------------------------------
    def _draw_cityscape(self, event=None):
        """
        Draws an aesthetic civic building and urban cityscape
        with buildings, windows, streetlights, trees, and roads.
        """
        w = self.city_canvas.winfo_width()
        h = self.city_canvas.winfo_height()
        if w < 50 or h < 50:
            return

        self.city_canvas.delete("all")

        # Background Night / Twilight Sky in deep pine twilight
        sky_color = "#1F2E25"
        self.city_canvas.create_rectangle(0, 0, w, h, fill=sky_color, outline="")

        # Stars / Subtle Dots in Sky
        star_positions = [(0.15, 0.15), (0.35, 0.08), (0.55, 0.18), (0.75, 0.1), (0.88, 0.22)]
        for sx, sy in star_positions:
            self.city_canvas.create_oval(w * sx - 2, h * sy - 2, w * sx + 2, h * sy + 2, fill=COLOR_ACCENT, outline="")

        # Horizon ground line
        ground_y = h * 0.78
        road_y = h * 0.88

        # 1. Background Buildings (Darker Silhouette)
        bg_buildings = [
            (0.05, 0.22, 0.35),
            (0.24, 0.18, 0.45),
            (0.44, 0.25, 0.32),
            (0.70, 0.20, 0.40),
            (0.86, 0.14, 0.50),
        ]
        for bx, bw, bh_ratio in bg_buildings:
            x1 = w * bx
            x2 = w * (bx + bw)
            y1 = ground_y - (h * bh_ratio)
            self.city_canvas.create_rectangle(x1, y1, x2, ground_y, fill="#283C30", outline="")

        # 2. Foreground Buildings (Soft Forest Green with Glowing Windows)
        fg_buildings = [
            (0.08, 0.18, 0.28, "#32493A"),
            (0.30, 0.22, 0.38, "#375040"),
            (0.58, 0.16, 0.32, "#32493A"),
            (0.78, 0.18, 0.25, "#3A5543"),
        ]
        for bx, bw, bh_ratio, b_col in fg_buildings:
            x1 = w * bx
            x2 = w * (bx + bw)
            y1 = ground_y - (h * bh_ratio)
            self.city_canvas.create_rectangle(x1, y1, x2, ground_y, fill=b_col, outline="#4A6A55", width=1)

            # Windows grid
            win_rows = 4
            win_cols = 3
            for r in range(win_rows):
                for c in range(win_cols):
                    wx1 = x1 + (x2 - x1) * (0.2 + c * 0.28)
                    wy1 = y1 + 12 + r * 18
                    win_color = "#FFFFFF" if (r + c) % 2 == 0 else COLOR_ACCENT
                    self.city_canvas.create_rectangle(wx1, wy1, wx1 + 7, wy1 + 10, fill=win_color, outline="")

        # 3. Central Municipal / Civic Building Feature
        cx = w * 0.48
        cw = w * 0.36
        ch = h * 0.42
        cy1 = ground_y - ch
        self.city_canvas.create_rectangle(cx - cw/2, cy1, cx + cw/2, ground_y, fill=COLOR_SIDEBAR, outline=COLOR_PRIMARY, width=2)

        # Classical Pediment (Triangle Top)
        self.city_canvas.create_polygon(
            cx - cw/2 - 6, cy1,
            cx, cy1 - 25,
            cx + cw/2 + 6, cy1,
            fill=COLOR_PRIMARY,
            outline=COLOR_ACCENT,
            width=1
        )
        # Civic Dome / Clock Emblem
        self.city_canvas.create_oval(cx - 10, cy1 - 18, cx + 10, cy1 - 2, fill="#FFFFFF", outline=COLOR_HEADINGS)

        # Pillars on Civic Building
        pillar_count = 4
        for p in range(pillar_count):
            px = (cx - cw/2 + 15) + p * ((cw - 30) / (pillar_count - 1))
            self.city_canvas.create_line(px, cy1 + 10, px, ground_y - 2, fill=COLOR_ACCENT, width=4)

        # 4. Trees / Greenery
        trees = [0.03, 0.26, 0.74, 0.94]
        for tx in trees:
            gx = w * tx
            # Trunk
            self.city_canvas.create_rectangle(gx - 2, ground_y - 15, gx + 2, ground_y, fill="#5C4033", outline="")
            # Leaves
            self.city_canvas.create_oval(gx - 10, ground_y - 32, gx + 10, ground_y - 12, fill=COLOR_PRIMARY, outline="")

        # 5. Grass Ground Strip
        self.city_canvas.create_rectangle(0, ground_y, w, road_y, fill="#2F4637", outline="")

        # 6. Paved Street Road with Dash Markings
        self.city_canvas.create_rectangle(0, road_y, w, h, fill="#1B2820", outline="")
        dash_y = (road_y + h) / 2
        for dx in range(10, int(w), 35):
            self.city_canvas.create_line(dx, dash_y, dx + 18, dash_y, fill=COLOR_ACCENT, width=2)

    # --------------------------------------------------------------------------
    # CITIZEN & FIELD WORKER REGISTRATION MODAL
    # --------------------------------------------------------------------------
    def _open_register_modal(self, target_role: Optional[str] = None):
        modal = tk.Toplevel(self)
        modal.title("Account Registration - CivicFix")
        modal.geometry("580x640")
        modal.configure(bg=COLOR_BG)
        modal.transient(self)
        modal.grab_set()

        card = tk.Frame(modal, bg=COLOR_CARD, padx=25, pady=20, bd=1, relief="solid")
        card.configure(highlightbackground=COLOR_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Header with Role Tabs
        header_row = tk.Frame(card, bg=COLOR_CARD)
        header_row.pack(fill=tk.X, pady=(0, 10))

        title_lbl = tk.Label(header_row, text="Create New Account", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_TITLE)
        title_lbl.pack(side=tk.LEFT)

        # Role switcher buttons
        current_reg_role = [target_role if target_role in ("CITIZEN", "WORKER") else self.selected_role]

        tab_bar = tk.Frame(card, bg=COLOR_BG, bd=1, relief="solid")
        tab_bar.configure(highlightbackground=COLOR_BORDER)
        tab_bar.pack(fill=tk.X, pady=(0, 15))

        btn_cit = tk.Button(tab_bar, text="👤  Citizen Registration", font=FONT_BODY_BOLD, bd=0, relief="flat", padx=12, pady=7, cursor="hand2")
        btn_cit.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_wrk = tk.Button(tab_bar, text="👷  Field Worker Registration", font=FONT_BODY_BOLD, bd=0, relief="flat", padx=12, pady=7, cursor="hand2")
        btn_wrk.pack(side=tk.LEFT, fill=tk.X, expand=True)

        form_body = tk.Frame(card, bg=COLOR_CARD)
        form_body.pack(fill=tk.BOTH, expand=True)

        err_lbl = tk.Label(card, text="", bg=COLOR_CARD, fg=COLOR_DANGER, font=FONT_SMALL, anchor="w")
        err_lbl.pack(fill=tk.X, pady=(4, 6))

        def switch_tab(role: str):
            current_reg_role[0] = role
            err_lbl.configure(text="")
            for child in form_body.winfo_children():
                child.destroy()

            if role == "CITIZEN":
                btn_cit.configure(bg=COLOR_PRIMARY, fg="#FFFFFF")
                btn_wrk.configure(bg=COLOR_BG, fg=COLOR_HEADINGS)
                title_lbl.configure(text="Citizen Registration")
                render_citizen_form()
            else:
                btn_wrk.configure(bg=COLOR_PRIMARY, fg="#FFFFFF")
                btn_cit.configure(bg=COLOR_BG, fg=COLOR_HEADINGS)
                title_lbl.configure(text="Field Worker Registration (Pending Approval)")
                render_worker_form()

        btn_cit.configure(command=lambda: switch_tab("CITIZEN"))
        btn_wrk.configure(command=lambda: switch_tab("WORKER"))

        def render_citizen_form():
            tk.Label(form_body, text="Register as a local citizen to report neighborhood issues and track resolution.", bg=COLOR_CARD, fg=COLOR_BODY, font=FONT_SMALL).pack(anchor="w", pady=(0, 10))

            grid = tk.Frame(form_body, bg=COLOR_CARD)
            grid.pack(fill=tk.X, pady=(0, 10))

            tk.Label(grid, text="Full Name *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=0, column=0, sticky="w")
            name_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            name_e.grid(row=1, column=0, sticky="ew", padx=(0, 8), ipady=4, pady=(2, 6))

            tk.Label(grid, text="Username *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=0, column=1, sticky="w")
            user_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            user_e.grid(row=1, column=1, sticky="ew", ipady=4, pady=(2, 6))

            tk.Label(grid, text="Email Address *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=2, column=0, sticky="w")
            email_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            email_e.grid(row=3, column=0, sticky="ew", padx=(0, 8), ipady=4, pady=(2, 6))

            tk.Label(grid, text="Phone Number *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=2, column=1, sticky="w")
            phone_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            phone_e.grid(row=3, column=1, sticky="ew", ipady=4, pady=(2, 6))

            tk.Label(grid, text="Locality / Ward *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=4, column=0, sticky="w")
            loc_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            loc_e.grid(row=5, column=0, sticky="ew", padx=(0, 8), ipady=4, pady=(2, 6))

            tk.Label(grid, text="Street Address", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=4, column=1, sticky="w")
            addr_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            addr_e.grid(row=5, column=1, sticky="ew", ipady=4, pady=(2, 6))

            tk.Label(grid, text="Password (min 8 chars) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=6, column=0, sticky="w")
            pwd_e = tk.Entry(grid, font=FONT_BODY, show="•", bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            pwd_e.grid(row=7, column=0, sticky="ew", padx=(0, 8), ipady=4, pady=(2, 6))

            tk.Label(grid, text="Confirm Password *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=6, column=1, sticky="w")
            cpwd_e = tk.Entry(grid, font=FONT_BODY, show="•", bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            cpwd_e.grid(row=7, column=1, sticky="ew", ipady=4, pady=(2, 6))

            grid.columnconfigure(0, weight=1)
            grid.columnconfigure(1, weight=1)

            def execute_citizen_reg():
                ok, uid, msg = register_citizen(
                    full_name=name_e.get(),
                    email=email_e.get(),
                    phone=phone_e.get(),
                    username=user_e.get(),
                    password=pwd_e.get(),
                    confirm_password=cpwd_e.get(),
                    address=addr_e.get(),
                    locality=loc_e.get()
                )
                if not ok:
                    err_lbl.configure(text=f"✗ {msg}")
                    return

                messagebox.showinfo("Registration Successful", "Citizen account created successfully!\nYou may now log in.")
                modal.destroy()
                self.select_role("CITIZEN")
                self.user_entry.delete(0, tk.END)
                self.user_entry.insert(0, user_e.get().strip().lower())
                self.pass_entry.delete(0, tk.END)
                self.pass_entry.insert(0, pwd_e.get())

            reg_btn = tk.Button(
                form_body,
                text="Complete Citizen Registration ✓",
                bg=COLOR_PRIMARY,
                fg="#FFFFFF",
                activebackground=COLOR_HOVER,
                activeforeground="#FFFFFF",
                font=FONT_BODY_BOLD,
                relief="flat",
                pady=10,
                cursor="hand2",
                command=execute_citizen_reg
            )
            reg_btn.pack(fill=tk.X, pady=(5, 0))
            apply_button_hover(reg_btn, COLOR_PRIMARY, COLOR_HOVER)

        def render_worker_form():
            info_box = tk.Frame(form_body, bg=COLOR_ACCENT, padx=10, pady=8, bd=1, relief="solid")
            info_box.configure(highlightbackground=COLOR_BORDER)
            info_box.pack(fill=tk.X, pady=(0, 10))

            tk.Label(
                info_box,
                text="⏳ Notice: Field worker accounts are subject to administrative review. After registering, your account will have PENDING status until an administrator reviews and approves your application.",
                bg=COLOR_ACCENT,
                fg=COLOR_HEADINGS,
                font=FONT_SMALL,
                wraplength=480,
                justify="left"
            ).pack(fill=tk.X)

            grid = tk.Frame(form_body, bg=COLOR_CARD)
            grid.pack(fill=tk.X, pady=(0, 10))

            tk.Label(grid, text="Worker Full Name *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=0, column=0, sticky="w")
            w_name_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            w_name_e.grid(row=1, column=0, sticky="ew", padx=(0, 8), ipady=4, pady=(2, 6))

            tk.Label(grid, text="Username *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=0, column=1, sticky="w")
            w_user_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            w_user_e.grid(row=1, column=1, sticky="ew", ipady=4, pady=(2, 6))

            tk.Label(grid, text="Email Address *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=2, column=0, sticky="w")
            w_email_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            w_email_e.grid(row=3, column=0, sticky="ew", padx=(0, 8), ipady=4, pady=(2, 6))

            tk.Label(grid, text="Contact Phone *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=2, column=1, sticky="w")
            w_phone_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            w_phone_e.grid(row=3, column=1, sticky="ew", ipady=4, pady=(2, 6))

            tk.Label(grid, text="Department *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=4, column=0, sticky="w")
            w_dept_cmb = ttk.Combobox(grid, values=DEPARTMENTS, state="readonly", font=FONT_BODY)
            w_dept_cmb.set(DEPARTMENTS[0])
            w_dept_cmb.grid(row=5, column=0, sticky="ew", padx=(0, 8), ipady=3, pady=(2, 6))

            tk.Label(grid, text="Specialization / Trade Skills", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=4, column=1, sticky="w")
            w_spec_e = tk.Entry(grid, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            w_spec_e.grid(row=5, column=1, sticky="ew", ipady=4, pady=(2, 6))

            tk.Label(grid, text="Password (min 8 chars) *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=6, column=0, sticky="w")
            w_pwd_e = tk.Entry(grid, font=FONT_BODY, show="•", bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            w_pwd_e.grid(row=7, column=0, sticky="ew", padx=(0, 8), ipady=4, pady=(2, 6))

            tk.Label(grid, text="Confirm Password *", bg=COLOR_CARD, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).grid(row=6, column=1, sticky="w")
            w_cpwd_e = tk.Entry(grid, font=FONT_BODY, show="•", bg=COLOR_CARD, fg=COLOR_HEADINGS, insertbackground=COLOR_HEADINGS, bd=1, relief="solid")
            w_cpwd_e.grid(row=7, column=1, sticky="ew", ipady=4, pady=(2, 6))

            grid.columnconfigure(0, weight=1)
            grid.columnconfigure(1, weight=1)

            def execute_worker_reg():
                ok, uid, msg = register_field_worker(
                    full_name=w_name_e.get(),
                    email=w_email_e.get(),
                    phone=w_phone_e.get(),
                    username=w_user_e.get(),
                    password=w_pwd_e.get(),
                    confirm_password=w_cpwd_e.get(),
                    department=w_dept_cmb.get(),
                    specialization=w_spec_e.get()
                )
                if not ok:
                    err_lbl.configure(text=f"✗ {msg}")
                    return

                messagebox.showinfo(
                    "Registration Submitted",
                    "Field worker registration submitted successfully!\n\n"
                    "Your application has been received and is waiting for administrator approval.\n\n"
                    "Once approved by an administrator, you will be able to log in to the Field Worker Portal."
                )
                modal.destroy()
                self.select_role("WORKER")
                self.user_entry.delete(0, tk.END)
                self.user_entry.insert(0, w_user_e.get().strip().lower())
                self.pass_entry.delete(0, tk.END)
                self.pass_entry.insert(0, w_pwd_e.get())

            sub_btn = tk.Button(
                form_body,
                text="Submit Worker Registration (Pending Approval) →",
                bg=COLOR_PRIMARY,
                fg="#FFFFFF",
                activebackground=COLOR_HOVER,
                activeforeground="#FFFFFF",
                font=FONT_BODY_BOLD,
                relief="flat",
                pady=10,
                cursor="hand2",
                command=execute_worker_reg
            )
            sub_btn.pack(fill=tk.X, pady=(5, 0))
            apply_button_hover(sub_btn, COLOR_PRIMARY, COLOR_HOVER)

        # Trigger initial view
        switch_tab(current_reg_role[0])
        apply_button_hover(reg_btn, COLOR_PRIMARY, COLOR_HOVER)
