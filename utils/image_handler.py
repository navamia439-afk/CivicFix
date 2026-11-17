"""
CivicFix Image Management Utility
Handles image validation, unique file storage in uploads directory,
aspect-ratio preserving thumbnails, and fallback rendering.
"""

import os
import shutil
import uuid
from typing import Tuple, Optional
from tkinter import messagebox

# Supported extensions and maximum size (10 MB)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
COMPLAINT_IMAGES_DIR = os.path.join(UPLOADS_DIR, "complaint_images")
COMPLETION_IMAGES_DIR = os.path.join(UPLOADS_DIR, "completion_images")

# Ensure upload directories exist
os.makedirs(COMPLAINT_IMAGES_DIR, exist_ok=True)
os.makedirs(COMPLETION_IMAGES_DIR, exist_ok=True)


def validate_image_file(file_path: str) -> Tuple[bool, str]:
    """
    Validates that the file exists, is an allowed image format,
    and does not exceed the maximum file size.
    """
    if not file_path or not os.path.exists(file_path):
        return False, "File does not exist."

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported format '{ext}'. Allowed: JPG, JPEG, PNG, BMP."

    try:
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE_BYTES:
            return False, f"File size ({size / (1024*1024):.1f} MB) exceeds maximum limit of 10 MB."
    except Exception as exc:
        return False, f"Unable to read file size: {exc}"

    return True, ""


def save_image_to_uploads(source_path: str, subfolder: str = "complaint_images") -> Optional[str]:
    """
    Copies an uploaded image into the project's uploads directory with a unique UUID filename.
    Returns the relative path from project root (e.g. 'uploads/complaint_images/xyz.jpg').
    """
    valid, err_msg = validate_image_file(source_path)
    if not valid:
        messagebox.showerror("Invalid Image", err_msg)
        return None

    target_dir = os.path.join(UPLOADS_DIR, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    ext = os.path.splitext(source_path)[1].lower()
    unique_filename = f"img_{uuid.uuid4().hex[:12]}{ext}"
    destination_path = os.path.join(target_dir, unique_filename)

    try:
        shutil.copy2(source_path, destination_path)
        # Return relative path using forward slashes for universal portability
        relative_path = os.path.relpath(destination_path, BASE_DIR).replace("\\", "/")
        return relative_path
    except Exception as exc:
        messagebox.showerror("Upload Error", f"Failed to save image: {exc}")
        return None


def get_absolute_path(relative_path: Optional[str]) -> Optional[str]:
    """Converts a relative path to an absolute path."""
    if not relative_path:
        return None
    abs_path = os.path.join(BASE_DIR, relative_path.replace("/", os.sep))
    return abs_path if os.path.exists(abs_path) else None


def load_thumbnail(
    image_path: Optional[str],
    max_width: int = 240,
    max_height: int = 180
):
    """
    Loads an image and creates a PhotoImage thumbnail using Pillow,
    maintaining aspect ratio. Gracefully handles missing files.
    """
    if not image_path:
        return None

    abs_path = get_absolute_path(image_path)
    if not abs_path or not os.path.exists(abs_path):
        return None

    try:
        from PIL import Image, ImageTk

        img = Image.open(abs_path)
        # Preserve original aspect ratio
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        return photo
    except Exception as exc:
        print(f"[Notice] Could not generate thumbnail for {image_path}: {exc}")
        return None
