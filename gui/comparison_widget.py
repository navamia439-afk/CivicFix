"""
CivicFix Before/After Side-by-Side Resolution Verification Widget
Renders side-by-side comparison of initial citizen evidence photo (Before)
and verified field worker physical repair photo (After) with turnaround analytics
and interactive high-resolution zoom inspection.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional

from gui.styles import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SECONDARY,
    COLOR_ACCENT, COLOR_SIDEBAR, COLOR_HEADINGS, COLOR_BODY,
    COLOR_BORDER, COLOR_TEXT, COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_LIGHT_BLUE, COLOR_LIGHT_ACCENT,
    FONT_TITLE, FONT_HEADING, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_BADGE, STATUS_COLORS, apply_button_hover
)
from utils.image_handler import load_thumbnail, get_absolute_path
from services.complaint_service import get_complaint_details


class BeforeAfterComparisonWidget(tk.Frame):
    """
    Reusable side-by-side photographic inspection component comparing
    initial complaint evidence (Before) with field repair proof (After).
    """

    def __init__(
        self,
        parent: tk.Widget,
        complaint_data: Optional[Dict[str, Any]] = None,
        complaint_id_or_code: Optional[Any] = None,
        max_photo_width: int = 340,
        max_photo_height: int = 220,
        db_path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_CARD, bd=1, relief="solid", **kwargs)
        self.configure(highlightbackground=COLOR_BORDER)

        self.max_photo_width = max_photo_width
        self.max_photo_height = max_photo_height
        self.db_path = db_path
        self._image_cache = []  # Keep references so Python doesn't garbage collect Tk PhotoImages

        self.data: Optional[Dict[str, Any]] = None
        if complaint_data:
            self.data = complaint_data
        elif complaint_id_or_code:
            self.data = get_complaint_details(complaint_id_or_code)

        self._build_ui()

    def set_complaint(self, complaint_data_or_id: Any):
        """Dynamically reloads the comparison view with a new complaint."""
        if isinstance(complaint_data_or_id, dict):
            self.data = complaint_data_or_id
        else:
            self.data = get_complaint_details(complaint_data_or_id)

        self._image_cache.clear()
        for child in self.winfo_children():
            child.destroy()
        self._build_ui()

    def _build_ui(self):
        if not self.data:
            self._render_empty_state("No complaint selected for visual audit.")
            return

        c = self.data
        cid = c.get("complaint_id", "CFX-???")
        title = c.get("title", "")
        status = c.get("status", "NEW")

        # Top Header Banner
        header = tk.Frame(self, bg=COLOR_CARD, padx=16, pady=12)
        header.pack(fill=tk.X)

        title_row = tk.Frame(header, bg=COLOR_CARD)
        title_row.pack(fill=tk.X)

        tk.Label(
            title_row,
            text="📸  Side-by-Side Resolution Verification",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_HEADING
        ).pack(side=tk.LEFT)

        # Status badge on right using STATUS_COLORS
        st_cfg = STATUS_COLORS.get(status, {"bg": COLOR_ACCENT, "fg": COLOR_HEADINGS, "dot": COLOR_PRIMARY})
        formatted_status = status.replace("_", " ").title()

        tk.Label(
            title_row,
            text=f" • {formatted_status} ",
            bg=st_cfg["bg"],
            fg=st_cfg["fg"],
            font=FONT_BADGE,
            padx=8,
            pady=3
        ).pack(side=tk.RIGHT)

        # Turnaround Time Calculation
        sub_text = f"Auditing {cid} — {title}"
        turnaround_str = self._calculate_turnaround_time(c)
        if turnaround_str:
            sub_text += f"   •   ⏱ Resolution Turnaround: {turnaround_str}"

        tk.Label(
            header,
            text=sub_text,
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=FONT_SMALL,
            anchor="w"
        ).pack(fill=tk.X, pady=(2, 0))

        # Thin divider
        tk.Frame(self, bg=COLOR_BORDER, height=1).pack(fill=tk.X)

        # Dual Column Split: Left = BEFORE, Right = AFTER
        dual_box = tk.Frame(self, bg=COLOR_BG, padx=14, pady=14)
        dual_box.pack(fill=tk.BOTH, expand=True)

        images = c.get("images", [])
        before_img = next((img for img in images if img.get("image_type") == "EVIDENCE"), None)
        after_img = next((img for img in images if img.get("image_type") == "COMPLETION"), None)

        # 1. Left Card: BEFORE
        left_card = tk.Frame(dual_box, bg=COLOR_CARD, bd=1, relief="solid", padx=12, pady=12)
        left_card.configure(highlightbackground=COLOR_BORDER)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))

        self._render_photo_card(
            parent=left_card,
            banner_text="🔴 BEFORE (Citizen Evidence)",
            banner_bg="#FDF2F2",
            banner_fg="#991B1B",
            img_data=before_img,
            empty_title="📝 No Evidence Photo",
            empty_msg="Citizen submitted issue without initial photographic evidence.",
            sub_info=f"Reported on: {c.get('submitted_at', 'N/A')}\nCitizen: {c.get('citizen', {}).get('full_name', 'Citizen')}"
        )

        # 2. Right Card: AFTER
        right_card = tk.Frame(dual_box, bg=COLOR_CARD, bd=1, relief="solid", padx=12, pady=12)
        right_card.configure(highlightbackground=COLOR_BORDER)
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(7, 0))

        worker_name = c.get("assignment", {}).get("worker_name") or "Assigned Field Worker"
        completed_at = c.get("completed_at") or c.get("resolved_at") or "Pending"
        completion_remarks = c.get("assignment", {}).get("completion_remarks") or c.get("admin_remarks") or "Physical repair completed."

        self._render_photo_card(
            parent=right_card,
            banner_text="🟢 AFTER (Field Worker Resolution Proof)",
            banner_bg="#EEF8F1",
            banner_fg="#1E542E",
            img_data=after_img,
            empty_title="⏳ Pending Field Resolution",
            empty_msg="Field repair is currently in progress. Resolution photo has not been uploaded yet.",
            sub_info=f"Completed: {completed_at}\nWorker: {worker_name}\nRemarks: {completion_remarks}"
        )

    def _render_photo_card(
        self,
        parent: tk.Widget,
        banner_text: str,
        banner_bg: str,
        banner_fg: str,
        img_data: Optional[Dict[str, Any]],
        empty_title: str,
        empty_msg: str,
        sub_info: str
    ):
        # Card Banner Tag
        tag = tk.Label(
            parent,
            text=f"  {banner_text}  ",
            bg=banner_bg,
            fg=banner_fg,
            font=FONT_BODY_BOLD,
            anchor="w",
            padx=8,
            pady=4
        )
        tag.pack(fill=tk.X, pady=(0, 8))

        # Photo Frame Container
        photo_box = tk.Frame(
            parent,
            bg=COLOR_BG,
            bd=1,
            relief="solid",
            width=self.max_photo_width,
            height=self.max_photo_height
        )
        photo_box.configure(highlightbackground=COLOR_BORDER)
        photo_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        photo_box.pack_propagate(False)

        img_path = img_data.get("image_path") if img_data else None

        if img_path:
            photo = load_thumbnail(
                img_path,
                max_width=self.max_photo_width,
                max_height=self.max_photo_height
            )
            if photo:
                self._image_cache.append(photo)
                lbl = tk.Label(photo_box, image=photo, bg=COLOR_BG, cursor="hand2")
                lbl.pack(expand=True)
                lbl.bind("<Button-1>", lambda e, p=img_path, b=banner_text: self._open_fullscreen_photo(p, b))
            else:
                tk.Label(
                    photo_box,
                    text=f"[Image File: {os.path.basename(img_path)}]\n(Preview unavailable)",
                    bg=COLOR_BG,
                    fg=COLOR_MUTED,
                    font=FONT_SMALL
                ).pack(expand=True)

            # Enlarge button
            zoom_btn = tk.Button(
                parent,
                text="🔍  Click to Enlarge / Full View",
                bg=COLOR_ACCENT,
                fg=COLOR_HEADINGS,
                activebackground=COLOR_SECONDARY,
                activeforeground="#FFFFFF",
                font=FONT_SMALL,
                relief="flat",
                pady=5,
                cursor="hand2",
                command=lambda p=img_path, b=banner_text: self._open_fullscreen_photo(p, b)
            )
            zoom_btn.pack(fill=tk.X, pady=(0, 6))
            apply_button_hover(zoom_btn, COLOR_ACCENT, COLOR_SECONDARY, COLOR_HEADINGS, "#FFFFFF")

        else:
            # Informative Placeholder State
            tk.Label(
                photo_box,
                text=empty_title,
                bg=COLOR_BG,
                fg=COLOR_HEADINGS,
                font=FONT_BODY_BOLD
            ).pack(pady=(self.max_photo_height // 3, 4))

            tk.Label(
                photo_box,
                text=empty_msg,
                bg=COLOR_BG,
                fg=COLOR_BODY,
                font=FONT_SMALL,
                wraplength=self.max_photo_width - 30,
                justify="center"
            ).pack()

        # Metadata Footer
        info_lbl = tk.Label(
            parent,
            text=sub_info,
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=FONT_SMALL,
            anchor="w",
            justify="left"
        )
        info_lbl.pack(fill=tk.X)

    def _open_fullscreen_photo(self, image_rel_path: str, title: str):
        """Displays full resolution photo in an aesthetic inspection dialog."""
        abs_path = get_absolute_path(image_rel_path)
        if not abs_path or not os.path.exists(abs_path):
            messagebox.showwarning("File Missing", f"Image file not found on disk:\n{image_rel_path}")
            return

        modal = tk.Toplevel(self)
        modal.title(f"Visual Audit Preview — {title}")
        modal.geometry("780x640")
        modal.configure(bg=COLOR_BG)
        modal.transient(self)
        modal.grab_set()

        top_bar = tk.Frame(modal, bg=COLOR_SIDEBAR, padx=16, pady=10)
        top_bar.pack(fill=tk.X)

        tk.Label(
            top_bar,
            text=f"🔍  {title}",
            bg=COLOR_SIDEBAR,
            fg="#FFFFFF",
            font=FONT_HEADING
        ).pack(side=tk.LEFT)

        close_btn = tk.Button(
            top_bar,
            text="✕ Close Preview",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_HOVER,
            activeforeground="#FFFFFF",
            font=FONT_BODY_BOLD,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=modal.destroy
        )
        close_btn.pack(side=tk.RIGHT)
        apply_button_hover(close_btn, COLOR_PRIMARY, COLOR_HOVER)

        card = tk.Frame(modal, bg=COLOR_CARD, padx=16, pady=16, bd=1, relief="solid")
        card.configure(highlightbackground=COLOR_BORDER)
        card.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        big_photo = load_thumbnail(image_rel_path, max_width=720, max_height=480)
        if big_photo:
            self._image_cache.append(big_photo)
            tk.Label(card, image=big_photo, bg=COLOR_CARD).pack(expand=True)
        else:
            tk.Label(card, text="[High-resolution image preview could not be rendered]", bg=COLOR_CARD, fg=COLOR_MUTED).pack(expand=True)

        tk.Label(
            card,
            text=f"File Source: {image_rel_path}",
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=FONT_SMALL
        ).pack(pady=(8, 0))

    def _calculate_turnaround_time(self, complaint: Dict[str, Any]) -> Optional[str]:
        """Calculates elapsed turnaround from submission to completion or resolution."""
        start_str = complaint.get("submitted_at")
        end_str = complaint.get("completed_at") or complaint.get("resolved_at")

        if not start_str or not end_str:
            return None

        try:
            import datetime
            fmt = "%Y-%m-%d %H:%M:%S"
            t_start = datetime.datetime.strptime(start_str.split(".")[0], fmt)
            t_end = datetime.datetime.strptime(end_str.split(".")[0], fmt)
            diff = t_end - t_start

            total_hours = diff.total_seconds() / 3600.0
            if total_hours < 24:
                return f"{total_hours:.1f} hours"
            days = total_hours / 24.0
            return f"{days:.1f} days ({total_hours:.0f} hrs)"
        except Exception:
            return None

    def _render_empty_state(self, msg: str):
        tk.Label(
            self,
            text="📸 Photographic Resolution Verification",
            bg=COLOR_CARD,
            fg=COLOR_HEADINGS,
            font=FONT_HEADING
        ).pack(anchor="w", padx=16, pady=(12, 4))

        tk.Label(
            self,
            text=msg,
            bg=COLOR_CARD,
            fg=COLOR_BODY,
            font=FONT_BODY
        ).pack(padx=16, pady=24)
