"""
CivicFix Graphical User Interface Styles & Aesthetic Theme Configuration
Implements the professional, accessible Civic Green palette, typography hierarchy,
and ttk style definitions across the entire desktop application.
"""

import tkinter as tk
from tkinter import ttk

# ==============================================================================
# COLOR PALETTE — MODERN ACCESSIBLE CIVIC PALETTE 🌿
# ==============================================================================
# Main System Colors (from Specification Section 4)
COLOR_PRIMARY = "#789B83"       # Sage / Laurel Green (Primary Actions & Branding)
COLOR_SECONDARY = "#A3B18A"     # Soft Olive / Khaki Green (Secondary Highlights)
COLOR_BG = "#F7F5EF"            # Warm Alabaster / Cream (Page Background)
COLOR_CARD = "#FFFFFF"          # Pure White (Card & Form Surfaces)
COLOR_ACCENT = "#DDE8D5"        # Soft Celadon / Pistachio (Subtle Accents & Badges)
COLOR_SIDEBAR = "#405B4A"       # Deep Pine Forest Green (Navigation Menus)
COLOR_HEADINGS = "#263A32"      # Deep Cypress Green (Titles & Section Headers)
COLOR_BODY = "#4B5563"          # Neutral Slate Gray (Body Text & Descriptions)
COLOR_BORDER = "#E7E3D8"        # Warm Sand (Borders & Dividers)

# Interactive States
COLOR_HOVER = "#62826C"           # Darker Sage (Button Hover State)
COLOR_SECONDARY_HOVER = "#8E9C76" # Darker Olive (Secondary Hover State)
COLOR_SIDEBAR_HOVER = "#4C6B57"   # Subtle Pine Highlight (Sidebar Item Hover State)
COLOR_SIDEBAR_ACTIVE = "#33493C"  # Darker Pine (Sidebar Active Item State)
COLOR_SIDEBAR_TEXT = "#F7F5EF"    # Cream White for Sidebar Navigation Items
COLOR_MUTED = "#6B7280"           # Muted Slate Gray (Help text, captions)
COLOR_DARK_TEXT = "#1E2C26"       # Deep Charcoal
COLOR_INPUT_BG = "#FFFFFF"        # Clean White Input Fields

# Backward-Compatibility Aliases
COLOR_TEXT = "#263A32"          # Primary Text (matches Headings)
COLOR_LIGHT_BLUE = "#DDE8D5"    # Maps to Celadon Accent
COLOR_LIGHT_ACCENT = "#DDE8D5"  # Maps to Celadon Accent
COLOR_LIGHT_GREEN = "#DDE8D5"   # Maps to Celadon Accent

# Complaint Status Colors (from Specification Section 4)
STATUS_COLOR_PENDING = "#E9A23B"     # Warm Amber (Pending, New, Under Review, Assigned, Reopened)
STATUS_COLOR_IN_PROGRESS = "#6B9A91" # Teal Slate (Acknowledged, In Progress, Delayed, Completed Verification)
STATUS_COLOR_RESOLVED = "#4F9565"    # Forest / Leaf Green (Resolved, Closed)
STATUS_COLOR_REJECTED = "#D66B6B"    # Soft Coral Red (Rejected)

COLOR_SUCCESS = STATUS_COLOR_RESOLVED
COLOR_WARNING = STATUS_COLOR_PENDING
COLOR_DANGER = STATUS_COLOR_REJECTED

# Complaint Status Badge Color Mapping (Soft Tint Background + High-Contrast Text + Status Dot)
STATUS_COLORS = {
    "NEW": {"bg": "#FEF7ED", "fg": "#92400E", "dot": STATUS_COLOR_PENDING},
    "UNDER_REVIEW": {"bg": "#FEF7ED", "fg": "#92400E", "dot": STATUS_COLOR_PENDING},
    "VERIFIED": {"bg": "#FEF7ED", "fg": "#92400E", "dot": STATUS_COLOR_PENDING},
    "ASSIGNED": {"bg": "#FEF7ED", "fg": "#92400E", "dot": STATUS_COLOR_PENDING},
    "ACKNOWLEDGED": {"bg": "#F0F7F6", "fg": "#1E4D45", "dot": STATUS_COLOR_IN_PROGRESS},
    "IN_PROGRESS": {"bg": "#F0F7F6", "fg": "#1E4D45", "dot": STATUS_COLOR_IN_PROGRESS},
    "DELAYED": {"bg": "#F0F7F6", "fg": "#1E4D45", "dot": STATUS_COLOR_IN_PROGRESS},
    "COMPLETED_PENDING_VERIFICATION": {"bg": "#F0F7F6", "fg": "#1E4D45", "dot": STATUS_COLOR_IN_PROGRESS},
    "RESOLVED": {"bg": "#EEF8F1", "fg": "#1E542E", "dot": STATUS_COLOR_RESOLVED},
    "CLOSED": {"bg": "#EEF8F1", "fg": "#1E542E", "dot": STATUS_COLOR_RESOLVED},
    "REJECTED": {"bg": "#FDF2F2", "fg": "#991B1B", "dot": STATUS_COLOR_REJECTED},
    "REOPENED": {"bg": "#FEF7ED", "fg": "#92400E", "dot": STATUS_COLOR_PENDING},
}

# Priority Badge Color Mapping
PRIORITY_COLORS = {
    "LOW": {"bg": "#DDE8D5", "fg": "#263A32"},
    "MEDIUM": {"bg": "#FEF7ED", "fg": "#92400E"},
    "HIGH": {"bg": "#FEE2E2", "fg": "#991B1B"},
    "EMERGENCY": {"bg": "#D66B6B", "fg": "#FFFFFF"},
}

# ==============================================================================
# TYPOGRAPHY HIERARCHY — MODERN, HIGHLY READABLE & ACCESSIBLE
# ==============================================================================
FONT_APP_TITLE = ("Segoe UI", 16, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_SUBTITLE = ("Segoe UI", 10)
FONT_HEADING = ("Segoe UI", 12, "bold")
FONT_SECTION = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_BODY_BOLD = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_BADGE = ("Segoe UI", 9, "bold")
FONT_STAT_NUMBER = ("Segoe UI", 22, "bold")


def apply_button_hover(
    button: tk.Button,
    normal_bg: str,
    hover_bg: str,
    normal_fg: str = "#FFFFFF",
    hover_fg: str = "#FFFFFF"
):
    """Binds mouse enter and leave events to provide smooth, subtle hover effects."""
    def on_enter(e):
        try:
            if button.cget("state") != "disabled":
                button.configure(bg=hover_bg, fg=hover_fg)
        except Exception:
            pass

    def on_leave(e):
        try:
            if button.cget("state") != "disabled":
                button.configure(bg=normal_bg, fg=normal_fg)
        except Exception:
            pass

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)


def apply_ttk_styles(root: tk.Tk):
    """
    Applies custom Civic Green Theme styling to standard ttk widgets.
    """
    style = ttk.Style(root)
    style.theme_use("clam")

    # Base Frame styling
    style.configure("TFrame", background=COLOR_BG)
    style.configure("Card.TFrame", background=COLOR_CARD, relief="flat")
    style.configure("BorderCard.TFrame", background=COLOR_CARD, relief="solid", borderwidth=1)

    # Label styling
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_BODY, font=FONT_BODY)
    style.configure("Card.TLabel", background=COLOR_CARD, foreground=COLOR_BODY, font=FONT_BODY)
    style.configure("Header.TLabel", background=COLOR_PRIMARY, foreground="#FFFFFF", font=FONT_TITLE)
    style.configure("Heading.TLabel", background=COLOR_CARD, foreground=COLOR_HEADINGS, font=FONT_HEADING)
    style.configure("Muted.TLabel", background=COLOR_CARD, foreground=COLOR_MUTED, font=FONT_SMALL)

    # Primary Button (#789B83)
    style.configure(
        "TButton",
        background=COLOR_PRIMARY,
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        borderwidth=0,
        focuscolor="none",
        padding=(14, 8)
    )
    style.map(
        "TButton",
        background=[("active", COLOR_HOVER), ("pressed", COLOR_HOVER)],
        foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")]
    )

    # Secondary Button (#A3B18A)
    style.configure(
        "Secondary.TButton",
        background=COLOR_SECONDARY,
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        borderwidth=0,
        padding=(14, 8)
    )
    style.map(
        "Secondary.TButton",
        background=[("active", COLOR_SECONDARY_HOVER), ("pressed", COLOR_SECONDARY_HOVER)],
        foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")]
    )

    # Success Button (#4F9565)
    style.configure(
        "Success.TButton",
        background=STATUS_COLOR_RESOLVED,
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        borderwidth=0,
        padding=(14, 8)
    )
    style.map(
        "Success.TButton",
        background=[("active", "#3F7A52"), ("pressed", "#3F7A52")],
        foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")]
    )

    # Warning Button (#E9A23B)
    style.configure(
        "Warning.TButton",
        background=STATUS_COLOR_PENDING,
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        borderwidth=0,
        padding=(14, 8)
    )
    style.map(
        "Warning.TButton",
        background=[("active", "#D38F2E"), ("pressed", "#D38F2E")],
        foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")]
    )

    # Danger Button (#D66B6B)
    style.configure(
        "Danger.TButton",
        background=STATUS_COLOR_REJECTED,
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        borderwidth=0,
        padding=(14, 8)
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#B85555"), ("pressed", "#B85555")],
        foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")]
    )

    # Modern Treeview Styling (Tables)
    style.configure(
        "Treeview",
        background=COLOR_CARD,
        foreground=COLOR_HEADINGS,
        rowheight=34,
        fieldbackground=COLOR_CARD,
        font=FONT_BODY,
        borderwidth=0
    )
    style.configure(
        "Treeview.Heading",
        background=COLOR_ACCENT,
        foreground=COLOR_HEADINGS,
        font=FONT_BODY_BOLD,
        padding=(10, 8),
        borderwidth=1,
        relief="flat"
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#CEDEC5")]
    )
    style.map(
        "Treeview",
        background=[("selected", COLOR_ACCENT)],
        foreground=[("selected", COLOR_HEADINGS)]
    )

    # Entry & Combobox styling
    style.configure(
        "TCombobox",
        background=COLOR_CARD,
        foreground=COLOR_HEADINGS,
        fieldbackground=COLOR_CARD,
        font=FONT_BODY,
        padding=6
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLOR_CARD)],
        selectbackground=[("readonly", COLOR_ACCENT)],
        selectforeground=[("readonly", COLOR_HEADINGS)]
    )

    # Scrollbar
    style.configure(
        "Vertical.TScrollbar",
        background=COLOR_BORDER,
        troughcolor=COLOR_BG,
        borderwidth=0,
        arrowsize=14
    )
