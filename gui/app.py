"""
CivicFix Master Desktop Application
Manages the single root Tk window, theme styling, screen routing,
session state, universal Topbar, and Sidebar navigation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional

from gui.styles import (
    apply_ttk_styles, apply_button_hover,
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_BG, COLOR_CARD, COLOR_ACCENT,
    COLOR_SIDEBAR, COLOR_HEADINGS, COLOR_BODY, COLOR_BORDER, COLOR_HOVER,
    COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_LIGHT_BLUE, COLOR_LIGHT_ACCENT, COLOR_LIGHT_GREEN, COLOR_TEXT,
    FONT_APP_TITLE, FONT_TITLE, FONT_HEADING, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_BADGE
)
from gui.login import LoginScreen
from gui.components import StatCard
from gui.citizen_dashboard import CitizenDashboard
from gui.admin_dashboard import AdminDashboard
from gui.worker_dashboard import WorkerDashboard
from authentication.auth import current_session
from database.database_operations import get_table_counts, fetch_all


class CivicFixApp:
    """
    Main Application Window and Screen Router.
    Enforces single Tk root window, responsive layouts, and consistent styling.
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CivicFix - Local Issue Reporting & Resolution Tracking System")

        # Responsive Dimensions: 1366x768 default, 1100x650 minimum
        default_width = 1366
        default_height = 768
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = max(0, int((screen_w - default_width) / 2))
        pos_y = max(0, int((screen_h - default_height) / 2))
        self.root.geometry(f"{default_width}x{default_height}+{pos_x}+{pos_y}")
        self.root.minsize(1100, 650)
        self.root.configure(bg=COLOR_BG)

        # Apply pastel ttk styling
        apply_ttk_styles(self.root)

        # Root Content Container
        self.container = tk.Frame(self.root, bg=COLOR_BG)
        self.container.pack(fill=tk.BOTH, expand=True)

        # Active Screen Reference
        self.current_screen: Optional[tk.Widget] = None

        # Start at Login Screen
        self.show_login()

    def _clear_container(self):
        """Safely removes the active screen widget."""
        if self.current_screen is not None:
            self.current_screen.destroy()
            self.current_screen = None

    def show_login(self):
        """Displays the Welcome & Authentication Screen."""
        self._clear_container()
        current_session.logout()
        self.current_screen = LoginScreen(
            parent=self.container,
            on_login_success=self._on_login_success,
            on_exit=self.root.destroy
        )
        self.current_screen.pack(fill=tk.BOTH, expand=True)

    def _on_login_success(self, user: Dict[str, Any], profile: Optional[Dict[str, Any]]):
        """Routes the user to their appropriate role dashboard."""
        role = user.get("role", "").upper()
        if role == "CITIZEN":
            self.show_citizen_dashboard()
        elif role == "ADMIN":
            self.show_admin_dashboard()
        elif role == "WORKER":
            self.show_worker_dashboard()
        else:
            messagebox.showerror("Error", f"Unrecognized user role: {role}")
            self.show_login()

    def confirm_logout(self):
        """Prompts the user before logging out."""
        confirm = messagebox.askyesno(
            "Confirm Sign Out",
            "Are you sure you want to log out of CivicFix?",
            parent=self.root
        )
        if confirm:
            self.show_login()

    # --------------------------------------------------------------------------
    # UNIVERSAL TOPBAR HELPER
    # --------------------------------------------------------------------------
    def _create_topbar(self, parent: tk.Widget, section_title: str) -> tk.Frame:
        topbar = tk.Frame(parent, bg=COLOR_PRIMARY, height=70)
        topbar.pack(fill=tk.X, side=tk.TOP)
        topbar.pack_propagate(False)

        # Left branding and breadcrumb
        left_brand = tk.Frame(topbar, bg=COLOR_PRIMARY)
        left_brand.pack(side=tk.LEFT, padx=25, pady=12)

        tk.Label(
            left_brand,
            text="🏛️  CivicFix",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            font=FONT_APP_TITLE
        ).pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(
            left_brand,
            text=f"|   {section_title}",
            bg=COLOR_PRIMARY,
            fg=COLOR_LIGHT_ACCENT,
            font=FONT_HEADING
        ).pack(side=tk.LEFT)

        # Right user session info and sign out button
        right_info = tk.Frame(topbar, bg=COLOR_PRIMARY)
        right_info.pack(side=tk.RIGHT, padx=25, pady=14)

        # Role Badge
        role_name = current_session.role or "USER"
        role_badge_bg = COLOR_SECONDARY if role_name == "WORKER" else (COLOR_LIGHT_ACCENT if role_name == "CITIZEN" else "#FFFFFF")
        role_badge_fg = "#FFFFFF" if role_name == "WORKER" else COLOR_TEXT

        role_badge = tk.Label(
            right_info,
            text=f" {role_name} ",
            bg=role_badge_bg,
            fg=role_badge_fg,
            font=FONT_BADGE,
            padx=9,
            pady=3
        )
        role_badge.pack(side=tk.LEFT, padx=(0, 12))

        # Full Name / Username
        display_name = current_session.profile.get("full_name") or current_session.username or "User"
        tk.Label(
            right_info,
            text=f"Welcome, {display_name}",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            font=FONT_BODY_BOLD
        ).pack(side=tk.LEFT, padx=(0, 15))

        # Logout Button
        logout_btn = tk.Button(
            right_info,
            text="Sign Out ↪",
            bg=COLOR_DANGER,
            fg="#FFFFFF",
            activebackground="#B85555",
            activeforeground="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=5,
            command=self.confirm_logout
        )
        logout_btn.pack(side=tk.LEFT)
        apply_button_hover(logout_btn, COLOR_DANGER, "#B85555")

        # Bottom subtle border
        tk.Frame(parent, bg=COLOR_BORDER, height=1).pack(fill=tk.X, side=tk.TOP)

        return topbar

    # --------------------------------------------------------------------------
    # CITIZEN DASHBOARD (PHASE 5 INTEGRATED)
    # --------------------------------------------------------------------------
    def show_citizen_dashboard(self):
        self._clear_container()
        screen = tk.Frame(self.container, bg=COLOR_BG)
        screen.pack(fill=tk.BOTH, expand=True)
        self.current_screen = screen

        self._create_topbar(screen, "Citizen Service Portal")

        user_data = {
            "id": current_session.user_id,
            "username": current_session.username,
            "email": current_session.email,
            "role": current_session.role,
            "is_active": 1,
            "created_at": current_session.profile.get("created_at", "2026-11-11")
        }
        citizen_ui = CitizenDashboard(
            parent=screen,
            user=user_data,
            profile=current_session.profile
        )
        citizen_ui.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # ADMINISTRATOR DASHBOARD (PHASE 6 INTEGRATED)
    # --------------------------------------------------------------------------
    def show_admin_dashboard(self):
        self._clear_container()
        screen = tk.Frame(self.container, bg=COLOR_BG)
        screen.pack(fill=tk.BOTH, expand=True)
        self.current_screen = screen

        self._create_topbar(screen, "Administrator Command Center")

        user_data = {
            "id": current_session.user_id,
            "username": current_session.username,
            "email": current_session.email,
            "role": current_session.role
        }
        admin_ui = AdminDashboard(parent=screen, user=user_data)
        admin_ui.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # FIELD WORKER DASHBOARD (PHASE 7 INTEGRATED)
    # --------------------------------------------------------------------------
    def show_worker_dashboard(self):
        self._clear_container()
        screen = tk.Frame(self.container, bg=COLOR_BG)
        screen.pack(fill=tk.BOTH, expand=True)
        self.current_screen = screen

        self._create_topbar(screen, "Field Worker Operations")

        user_data = {
            "id": current_session.user_id,
            "username": current_session.username,
            "email": current_session.email,
            "role": current_session.role
        }
        try:
            worker_ui = WorkerDashboard(
                parent=screen,
                user=user_data,
                profile=current_session.profile
            )
            worker_ui.pack(fill=tk.BOTH, expand=True)
        except Exception as exc:
            import traceback
            err = traceback.format_exc()
            print(f"[Worker Dashboard Error] {err}")
            messagebox.showerror(
                "Worker Dashboard Error",
                f"Failed to load Field Worker Operations Portal:\n{exc}\n\nPlease check logs."
            )
