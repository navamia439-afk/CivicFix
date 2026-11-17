"""
CivicFix Reusable GUI Components
Provides modern, accessible, styled Tkinter/ttk components including Stat Cards, Data Tables,
Search Bars, Status Badges, Form Inputs, and Scrollable Containers.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import calendar
import datetime
from typing import Callable, List, Optional, Tuple, Any

from gui.styles import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_BG, COLOR_CARD, COLOR_ACCENT,
    COLOR_LIGHT_BLUE, COLOR_LIGHT_ACCENT, COLOR_LIGHT_GREEN, COLOR_SUCCESS, COLOR_WARNING,
    COLOR_DANGER, COLOR_TEXT, COLOR_HEADINGS, COLOR_BODY, COLOR_BORDER, COLOR_HOVER, COLOR_MUTED,
    FONT_TITLE, FONT_HEADING, FONT_SECTION, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_BADGE, FONT_STAT_NUMBER, STATUS_COLORS, PRIORITY_COLORS
)


class StatCard(tk.Frame):
    """
    Modern dashboard statistic card displaying a title, large metric,
    subtitle/indicator, and custom civic accent header ribbon.
    """
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        value: str = "0",
        subtitle: str = "",
        accent_color: str = COLOR_PRIMARY,
        icon: str = "📊",
        width: int = 180,
        height: int = 110,
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_CARD, bd=1, relief="solid", highlightthickness=0, **kwargs)
        self.configure(highlightbackground=COLOR_BORDER)
        if width and height:
            self.configure(width=width, height=height)
            self.pack_propagate(False)

        # Top Accent Ribbon (Consistent Brand/Status Indicator)
        ribbon = tk.Frame(self, bg=accent_color, height=5)
        ribbon.pack(fill=tk.X, side=tk.TOP)

        # Content Container
        container = tk.Frame(self, bg=COLOR_CARD, padx=14, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        # Header Row (Icon + Title)
        header_row = tk.Frame(container, bg=COLOR_CARD)
        header_row.pack(fill=tk.X)

        self.title_lbl = tk.Label(
            header_row,
            text=f"{icon}  {title}".upper(),
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Segoe UI", 8, "bold"),
            anchor="w"
        )
        self.title_lbl.pack(side=tk.LEFT)

        # Value Row (Prominent Large Stat Number)
        self.value_lbl = tk.Label(
            container,
            text=str(value),
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_STAT_NUMBER,
            anchor="w"
        )
        self.value_lbl.pack(fill=tk.X, pady=(2, 0))

        # Subtitle Row (Descriptive, Easy-to-Understand Helper Text)
        self.subtitle_lbl = tk.Label(
            container,
            text=subtitle,
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=FONT_SMALL,
            anchor="w"
        )
        self.subtitle_lbl.pack(fill=tk.X)

    def set_value(self, new_value: Any):
        """Updates the metric number."""
        self.value_lbl.configure(text=str(new_value))

    def set_subtitle(self, new_subtitle: str):
        """Updates the subtitle description."""
        self.subtitle_lbl.configure(text=new_subtitle)


class DataTable(tk.Frame):
    """
    Modern table component wrapping ttk.Treeview with scrollbars,
    alternate row coloring (pure white & warm cream), sorting, and row click callbacks.
    """
    def __init__(
        self,
        parent: tk.Widget,
        columns: List[Tuple[str, str, int]],  # (column_id, heading_text, width)
        show_scrollbar: bool = True,
        on_select: Optional[Callable[[dict], None]] = None,
        on_double_click: Optional[Callable[[dict], None]] = None,
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_CARD, bd=1, relief="solid", **kwargs)
        self.configure(highlightbackground=COLOR_BORDER)
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.col_keys = [c[0] for c in columns]

        # Treeview Widget
        self.tree = ttk.Treeview(
            self,
            columns=self.col_keys,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        for col_id, heading, width in columns:
            self.tree.heading(
                col_id,
                text=heading,
                anchor="w",
                command=lambda c=col_id: self._sort_column(c, False)
            )
            self.tree.column(col_id, width=width, anchor="w", stretch=True)

        # Alternating row tag colors (Pure White and Warm Alabaster/Cream)
        self.tree.tag_configure("oddrow", background="#FFFFFF")
        self.tree.tag_configure("evenrow", background=COLOR_BG)

        # Scrollbars
        if show_scrollbar:
            self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=self.vsb.set)
            self.vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Event Bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        if self.on_double_click:
            self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _sort_column(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            # Try numeric sort first
            data.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)

        for index, (_, k) in enumerate(data):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self._sort_column(col, not reverse))

    def _on_tree_select(self, event):
        if not self.on_select:
            return
        selected = self.get_selected_row()
        if selected:
            self.on_select(selected)

    def _on_tree_double_click(self, event):
        if not self.on_double_click:
            return
        selected = self.get_selected_row()
        if selected:
            self.on_double_click(selected)

    def get_selected_row(self) -> Optional[dict]:
        """Returns the dictionary representation of the currently selected row."""
        selected_item = self.tree.focus()
        if not selected_item:
            return None
        values = self.tree.item(selected_item, "values")
        if not values:
            return None
        return dict(zip(self.col_keys, values))

    def clear(self):
        """Clears all rows from the table."""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def set_rows(self, rows: List[dict]):
        """Populates the table with a list of row dictionaries."""
        self.clear()
        for i, row in enumerate(rows):
            vals = ["" if row.get(k) is None else str(row.get(k)) for k in self.col_keys]
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.tree.insert("", tk.END, values=vals, tags=(tag,))


class SearchBar(tk.Frame):
    """
    Search input box with search icon, clear button, and real-time search callback.
    """
    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "Search...",
        on_search: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_CARD, bd=1, relief="solid", **kwargs)
        self.configure(highlightbackground=COLOR_BORDER)
        self.on_search = on_search

        tk.Label(
            self,
            text=" 🔍 ",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Segoe UI", 10)
        ).pack(side=tk.LEFT, padx=(5, 0))

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            self,
            textvariable=self.entry_var,
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_BODY,
            bd=0,
            highlightthickness=0
        )
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, ipady=4)
        self.entry_var.trace_add("write", self._on_change)

        clear_btn = tk.Button(
            self,
            text="✕",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_HEADINGS,
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 8),
            command=self.clear
        )
        clear_btn.pack(side=tk.RIGHT, padx=5)

    def _on_change(self, *args):
        if self.on_search:
            self.on_search(self.entry_var.get().strip())

    def get_text(self) -> str:
        return self.entry_var.get().strip()

    def clear(self):
        self.entry_var.set("")


class StatusBadge(tk.Label):
    """
    Color-coded status badge label for complaint lifecycle states.
    Displays clear, high-contrast, formatted status indicators.
    """
    def __init__(self, parent: tk.Widget, status: str, **kwargs):
        cfg = STATUS_COLORS.get(status, {"bg": COLOR_ACCENT, "fg": COLOR_HEADINGS, "dot": COLOR_SECONDARY})
        formatted_status = status.replace("_", " ").title()
        super().__init__(
            parent,
            text=f" • {formatted_status} ",
            bg=cfg["bg"],
            fg=cfg["fg"],
            font=FONT_BADGE,
            padx=9,
            pady=3,
            bd=1,
            relief="flat",
            **kwargs
        )


class PriorityBadge(tk.Label):
    """
    Color-coded priority badge label (LOW, MEDIUM, HIGH, EMERGENCY).
    """
    def __init__(self, parent: tk.Widget, priority: str, **kwargs):
        cfg = PRIORITY_COLORS.get(priority, {"bg": COLOR_ACCENT, "fg": COLOR_HEADINGS})
        super().__init__(
            parent,
            text=f" {priority} ",
            bg=cfg["bg"],
            fg=cfg["fg"],
            font=FONT_BADGE,
            padx=8,
            pady=3,
            bd=1,
            relief="flat",
            **kwargs
        )


class ScrollableFrame(tk.Frame):
    """
    A smooth scrollable container wrapping Canvas and Scrollbar
    with seamless mousewheel binding.
    """
    def __init__(self, parent: tk.Widget, bg: str = COLOR_BG, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = tk.Frame(self.canvas, bg=bg)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind_mousewheel(self.canvas)
        self.bind_mousewheel(self.scrollable_content)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def bind_mousewheel(self, widget: tk.Widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self.bind_mousewheel(child)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class CalendarDatePicker(tk.Frame):
    """
    Modern Sage & Cream Calendar Date Picker Component.
    Provides an entry field with calendar icon button (📅) that launches an interactive
    calendar popup for month/year navigation, day selection, 'Today' shortcut, and date validation.
    Maintains 'YYYY-MM-DD' (or 'YYYY-MM-DD HH:MM:SS' if include_time=True) format.
    """
    def __init__(
        self,
        parent: tk.Widget,
        default_date: Optional[str] = None,
        placeholder: str = "YYYY-MM-DD",
        include_time: bool = False,
        default_time: str = "18:00:00",
        on_date_selected: Optional[Callable[[str], None]] = None,
        width: int = 16,
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_CARD, bd=1, relief="solid", **kwargs)
        self.configure(highlightbackground=COLOR_BORDER)
        self.include_time = include_time
        self.default_time = default_time
        self.on_date_selected = on_date_selected
        self._popup: Optional[tk.Toplevel] = None

        # Determine initial date
        self.selected_date = None
        if default_date:
            try:
                d_str = default_date.split(" ")[0].strip()
                parsed = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                self.selected_date = parsed
                self.view_year = parsed.year
                self.view_month = parsed.month
            except Exception:
                today = datetime.date.today()
                self.view_year = today.year
                self.view_month = today.month
        else:
            today = datetime.date.today()
            self.view_year = today.year
            self.view_month = today.month

        # Inner text variable and entry
        self.date_var = tk.StringVar(value=default_date or "")
        self.entry = tk.Entry(
            self,
            textvariable=self.date_var,
            font=FONT_BODY,
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            insertbackground=COLOR_HEADINGS,
            bd=0,
            highlightthickness=0,
            width=width
        )
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 4), ipady=4)

        # 📅 Calendar Trigger Button
        self.cal_btn = tk.Button(
            self,
            text="📅",
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            activebackground=COLOR_ACCENT,
            activeforeground=COLOR_HEADINGS,
            font=("Segoe UI", 10),
            bd=0,
            cursor="hand2",
            padx=6,
            command=self.open_calendar
        )
        self.cal_btn.pack(side=tk.RIGHT)

        # Validate on focus out
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Return>", lambda e: self._on_enter())

    def _on_focus_out(self, event=None):
        val = self.get().strip()
        if val:
            if not self.validate_date(val):
                pass
            else:
                try:
                    d_str = val.split(" ")[0]
                    self.selected_date = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                except Exception:
                    pass

    def _on_enter(self, event=None):
        if self.on_date_selected:
            self.on_date_selected(self.get())

    def validate_date(self, val: str) -> bool:
        """Validates if the provided string is a valid date."""
        if not val:
            return True
        try:
            d_part = val.split(" ")[0].strip()
            datetime.datetime.strptime(d_part, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def get(self) -> str:
        """Returns the current date string."""
        return self.date_var.get().strip()

    def set(self, val: str):
        """Sets the date string."""
        self.date_var.set(val)
        if val:
            try:
                d_str = val.split(" ")[0]
                self.selected_date = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                self.view_year = self.selected_date.year
                self.view_month = self.selected_date.month
            except Exception:
                pass

    def delete(self, first, last=None):
        self.entry.delete(first, last)

    def insert(self, index, string):
        self.entry.insert(index, string)

    def open_calendar(self):
        """Opens the Sage & Cream calendar popup."""
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            return

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 3

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        popup_w = 280
        popup_h = 310 if not self.include_time else 350

        if x + popup_w > screen_w:
            x = screen_w - popup_w - 10
        if y + popup_h > screen_h:
            y = self.winfo_rooty() - popup_h - 3

        self._popup = tk.Toplevel(self)
        self._popup.title("Select Date")
        self._popup.geometry(f"{popup_w}x{popup_h}+{x}+{y}")
        self._popup.configure(bg=COLOR_CARD, bd=1, relief="solid")
        self._popup.attributes("-topmost", True)
        self._popup.transient(self.winfo_toplevel())

        self._build_calendar_popup(self._popup)

    def _build_calendar_popup(self, popup: tk.Toplevel):
        for child in popup.winfo_children():
            child.destroy()

        # 1. Header with Month/Year Navigation (Sage Green)
        header = tk.Frame(popup, bg=COLOR_PRIMARY, padx=8, pady=8)
        header.pack(fill=tk.X)

        # Prev Year Button
        py_btn = tk.Button(
            header, text="«", bg=COLOR_PRIMARY, fg="#FFFFFF", bd=0, font=("Segoe UI", 9, "bold"),
            activebackground=COLOR_HOVER, activeforeground="#FFFFFF", cursor="hand2",
            command=lambda: self._change_month(-12)
        )
        py_btn.pack(side=tk.LEFT, padx=(2, 4))

        # Prev Month Button
        pm_btn = tk.Button(
            header, text="‹", bg=COLOR_PRIMARY, fg="#FFFFFF", bd=0, font=("Segoe UI", 11, "bold"),
            activebackground=COLOR_HOVER, activeforeground="#FFFFFF", cursor="hand2",
            command=lambda: self._change_month(-1)
        )
        pm_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Current Month & Year Label
        month_name = calendar.month_name[self.view_month]
        lbl_title = tk.Label(
            header,
            text=f"{month_name} {self.view_year}",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            font=FONT_BODY_BOLD
        )
        lbl_title.pack(side=tk.LEFT, expand=True)

        # Next Month Button
        nm_btn = tk.Button(
            header, text="›", bg=COLOR_PRIMARY, fg="#FFFFFF", bd=0, font=("Segoe UI", 11, "bold"),
            activebackground=COLOR_HOVER, activeforeground="#FFFFFF", cursor="hand2",
            command=lambda: self._change_month(1)
        )
        nm_btn.pack(side=tk.RIGHT, padx=(4, 0))

        # Next Year Button
        ny_btn = tk.Button(
            header, text="»", bg=COLOR_PRIMARY, fg="#FFFFFF", bd=0, font=("Segoe UI", 9, "bold"),
            activebackground=COLOR_HOVER, activeforeground="#FFFFFF", cursor="hand2",
            command=lambda: self._change_month(12)
        )
        ny_btn.pack(side=tk.RIGHT, padx=(4, 2))

        # 2. Day-of-Week Row (Soft Celadon Accent #DDE8D5)
        dow_frame = tk.Frame(popup, bg=COLOR_ACCENT, pady=4)
        dow_frame.pack(fill=tk.X)

        days_abbr = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for d in days_abbr:
            lbl = tk.Label(
                dow_frame, text=d, bg=COLOR_ACCENT, fg=COLOR_HEADINGS,
                font=("Segoe UI", 8, "bold"), width=4
            )
            lbl.pack(side=tk.LEFT, expand=True)

        # 3. Days Grid
        grid_frame = tk.Frame(popup, bg=COLOR_CARD, padx=6, pady=6)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(self.view_year, self.view_month)
        today = datetime.date.today()

        for r_idx, week in enumerate(month_days):
            row_frame = tk.Frame(grid_frame, bg=COLOR_CARD)
            row_frame.pack(fill=tk.X, pady=1)

            for d_idx, day in enumerate(week):
                if day == 0:
                    tk.Label(row_frame, text="", bg=COLOR_CARD, width=4, height=1).pack(side=tk.LEFT, expand=True)
                else:
                    curr_date = datetime.date(self.view_year, self.view_month, day)
                    is_selected = self.selected_date == curr_date
                    is_today = curr_date == today

                    if is_selected:
                        btn_bg = COLOR_PRIMARY
                        btn_fg = "#FFFFFF"
                        fnt = ("Segoe UI", 9, "bold")
                    elif is_today:
                        btn_bg = COLOR_ACCENT
                        btn_fg = COLOR_HEADINGS
                        fnt = ("Segoe UI", 9, "bold")
                    else:
                        btn_bg = COLOR_CARD
                        btn_fg = COLOR_HEADINGS
                        fnt = ("Segoe UI", 9)

                    btn = tk.Button(
                        row_frame,
                        text=str(day),
                        bg=btn_bg,
                        fg=btn_fg,
                        font=fnt,
                        bd=0,
                        relief="flat",
                        width=3,
                        height=1,
                        cursor="hand2",
                        command=lambda dt=curr_date: self._select_date(dt)
                    )
                    btn.pack(side=tk.LEFT, expand=True, padx=1)

                    def _bind_hover(b=btn, sel=is_selected, tod=is_today):
                        def on_enter(e):
                            if not sel:
                                b.configure(bg=COLOR_ACCENT)
                        def on_leave(e):
                            if not sel:
                                b.configure(bg=COLOR_ACCENT if tod else COLOR_CARD)
                        b.bind("<Enter>", on_enter)
                        b.bind("<Leave>", on_leave)
                    _bind_hover()

        # 4. Optional Time Row
        if self.include_time:
            time_frame = tk.Frame(popup, bg=COLOR_BG, padx=8, pady=4, bd=1, relief="solid")
            time_frame.configure(highlightbackground=COLOR_BORDER)
            time_frame.pack(fill=tk.X, padx=6, pady=(0, 4))

            tk.Label(time_frame, text="Time:", bg=COLOR_BG, fg=COLOR_HEADINGS, font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 4))
            self.hour_var = tk.StringVar(value="18")
            self.min_var = tk.StringVar(value="00")

            hours = [f"{h:02d}" for h in range(24)]
            mins = [f"{m:02d}" for m in range(0, 60, 5)]

            h_cb = ttk.Combobox(time_frame, textvariable=self.hour_var, values=hours, width=3, state="readonly")
            h_cb.pack(side=tk.LEFT)
            tk.Label(time_frame, text=":", bg=COLOR_BG, fg=COLOR_HEADINGS, font=FONT_BODY_BOLD).pack(side=tk.LEFT, padx=1)
            m_cb = ttk.Combobox(time_frame, textvariable=self.min_var, values=mins, width=3, state="readonly")
            m_cb.pack(side=tk.LEFT)

        # 5. Bottom Shortcut Controls (Today, Clear, Close)
        footer = tk.Frame(popup, bg=COLOR_BG, padx=8, pady=6)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        today_btn = tk.Button(
            footer, text="Today", bg=COLOR_ACCENT, fg=COLOR_HEADINGS, bd=0, font=("Segoe UI", 8, "bold"),
            cursor="hand2", padx=6, pady=2,
            command=lambda: self._select_date(datetime.date.today())
        )
        today_btn.pack(side=tk.LEFT, padx=(0, 4))

        clear_btn = tk.Button(
            footer, text="Clear", bg=COLOR_CARD, fg=COLOR_MUTED, bd=1, relief="solid", font=("Segoe UI", 8),
            cursor="hand2", padx=6, pady=2,
            command=self._clear_date
        )
        clear_btn.pack(side=tk.LEFT)

        close_btn = tk.Button(
            footer, text="Close", bg=COLOR_CARD, fg=COLOR_HEADINGS, bd=1, relief="solid", font=("Segoe UI", 8),
            cursor="hand2", padx=6, pady=2,
            command=self._close_popup
        )
        close_btn.pack(side=tk.RIGHT)

    def _change_month(self, delta_months: int):
        new_m = self.view_month + delta_months
        new_y = self.view_year
        while new_m > 12:
            new_m -= 12
            new_y += 1
        while new_m < 1:
            new_m += 12
            new_y -= 1
        self.view_month = new_m
        self.view_year = new_y
        if self._popup and self._popup.winfo_exists():
            self._build_calendar_popup(self._popup)

    def _select_date(self, d: datetime.date):
        self.selected_date = d
        date_str = d.strftime("%Y-%m-%d")
        if self.include_time:
            h = getattr(self, "hour_var", None)
            m = getattr(self, "min_var", None)
            h_str = h.get() if h else "18"
            m_str = m.get() if m else "00"
            date_str = f"{date_str} {h_str}:{m_str}:00"

        self.date_var.set(date_str)
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None

        if self.on_date_selected:
            self.on_date_selected(date_str)

    def _clear_date(self):
        self.selected_date = None
        self.date_var.set("")
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
        if self.on_date_selected:
            self.on_date_selected("")

    def _close_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
