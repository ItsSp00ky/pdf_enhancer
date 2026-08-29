# Ahmed Gali
# Copyright (c) 2025 Ahmed Gali
# Licensed under the MIT License

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image, ImageOps
import os
import sys
import threading
import webbrowser
import subprocess
from urllib.parse import unquote, urlparse
import customtkinter as ctk
from tkinter import filedialog, messagebox, TclError

from tkinterdnd2 import TkinterDnD, DND_FILES

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS + (".pdf",)

IMAGE_FILETYPES = [("Image Files", " ".join(f"*{ext}" for ext in IMAGE_EXTENSIONS))]
PDF_FILETYPES = [("PDF Files", "*.pdf")]
# "Supported" first so the browse dialog accepts either kind without switching filter.
BROWSE_FILETYPES = [
    ("Supported Files", " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)),
] + PDF_FILETYPES + IMAGE_FILETYPES

DETECT_HEIGHT = 800        # page detection runs on a downscaled copy of this height
MIN_PAGE_AREA_RATIO = 0.15  # a candidate quad must cover this much of the frame
DROP_PROMPT = "Drag & drop files here or browse"


# --- RESOURCE HELPER FOR EXE ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


# --- Geometry & Cropping Helpers ---
def order_points(pts):
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    maxWidth = max(1, int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))))
    maxHeight = max(1, int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))))
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))


def find_page_quad(image):
    """Locate the document corners in full-resolution coordinates, or None."""
    height = image.shape[0]
    scale = min(1.0, DETECT_HEIGHT / height)
    small = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1.0 else image

    # Isolate the (bright, desaturated) sheet of paper from the background.
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 60, 255]))
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    approx = cv2.approxPolyDP(largest, 0.02 * cv2.arcLength(largest, True), True)
    if len(approx) != 4:
        return None

    small_h, small_w = small.shape[:2]
    if cv2.contourArea(approx) < MIN_PAGE_AREA_RATIO * small_w * small_h:
        return None

    return approx.reshape(4, 2).astype("float32") / scale


def process_single_page(image):
    """Deskew/crop a BGR page image and return it as a binarised grayscale array."""
    quad = find_page_quad(image)
    warped = four_point_transform(image, quad) if quad is not None else image

    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
    return cv2.medianBlur(binary, 3)


# --- Input Loading ---
def pixmap_to_bgr(pix):
    """Convert a PyMuPDF pixmap to a BGR numpy array (stride-safe)."""
    rows = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)
    img = rows[:, :pix.width * pix.n].reshape(pix.height, pix.width, pix.n)
    if pix.n == 1:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if pix.n == 4:
        # MuPDF stores premultiplied alpha; flatten onto white so a transparent
        # page background does not become black and invert after thresholding.
        alpha = img[:, :, 3:4].astype(np.uint16)
        img = np.clip(img[:, :, :3].astype(np.uint16) + (255 - alpha), 0, 255).astype(np.uint8)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def load_image_to_bgr(path):
    """Load an image file and convert to BGR format (OpenCV compatible)."""
    with Image.open(path) as opened:
        img = ImageOps.exif_transpose(opened)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            # Flatten transparency onto white so it does not threshold to black.
            rgba = img.convert("RGBA")
            flattened = Image.new("RGB", rgba.size, (255, 255, 255))
            flattened.paste(rgba, mask=rgba)
            img = flattened
        else:
            img = img.convert("RGB")
        return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)


def is_pdf(path):
    """Input kind is decided per file by extension - there is no global mode."""
    return path.lower().endswith(".pdf")


def count_source_pages(paths):
    """Total output pages: every PDF contributes its page count, every image one."""
    total = 0
    for path in paths:
        if is_pdf(path):
            with fitz.open(path) as doc:
                total += doc.page_count
        else:
            total += 1
    return total


def describe_selection(paths):
    """Human-readable summary of what was detected, e.g. '1 PDF + 2 images'."""
    pdfs = sum(1 for path in paths if is_pdf(path))
    images = len(paths) - pdfs
    parts = []
    if pdfs:
        parts.append(f"{pdfs} PDF{'s' if pdfs > 1 else ''}")
    if images:
        parts.append(f"{images} image{'s' if images > 1 else ''}")
    return " + ".join(parts)


def iter_source_images(paths, dpi):
    """Yield (index, total, bgr_image) for every page of the whole selection.

    PDFs are rasterised page by page and images are loaded whole; both are
    flattened into one continuous page stream in the order they were selected.
    """
    total = count_source_pages(paths)
    index = 0
    for path in paths:
        if is_pdf(path):
            with fitz.open(path) as doc:
                for page_number in range(doc.page_count):
                    yield index, total, pixmap_to_bgr(doc[page_number].get_pixmap(dpi=dpi))
                    index += 1
        else:
            yield index, total, load_image_to_bgr(path)
            index += 1


def open_with_default_app(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Error opening file: {e}")


# --- GUI Logic ---
# Inherit from TkinterDnD.DnDWrapper to enable drag and drop in CTk
class ScannerApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()

        # --- Initialize Drag and Drop ---
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.handle_drop)
        except Exception as e:
            print(f"Warning: Drag and Drop functionality could not be loaded: {e}")

        self.title("PDF Enhancer")
        self.geometry("600x500")
        self.resizable(False, False)
        self.set_icon(self)

        # Application State
        self.input_files = []       # any mix of PDFs and images, in selection order
        self.preview_window = None
        self.preview_img_label = None
        self.current_preview_image = None
        self.is_closing = False

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Layout Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # status row absorbs the slack

        # 1. Header
        self.lbl_title = ctk.CTkLabel(self, text="📄 PDF Clean Scanner", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 2. File Selection Frame
        self.frame_file = ctk.CTkFrame(self)
        self.frame_file.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.lbl_file_path = ctk.CTkLabel(self.frame_file, text=DROP_PROMPT, text_color="gray")
        self.lbl_file_path.pack(side="left", padx=15, pady=15)

        self.btn_browse = ctk.CTkButton(self.frame_file, text="Browse", command=self.browse_file)
        self.btn_browse.pack(side="right", padx=15, pady=15)

        # 3. Settings Frame (DPI)
        self.frame_settings = ctk.CTkFrame(self)
        self.frame_settings.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.lbl_dpi = ctk.CTkLabel(self.frame_settings, text="Scan Quality (DPI): 200")
        self.lbl_dpi.pack(side="top", pady=(15, 0))

        self.slider_dpi = ctk.CTkSlider(self.frame_settings, from_=100, to=400, number_of_steps=6, command=self.update_dpi_label)
        self.slider_dpi.set(200)
        self.slider_dpi.pack(side="top", fill="x", padx=20, pady=(5, 15))

        # 4. Buttons
        self.frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_buttons.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        self.btn_preview = ctk.CTkButton(
            self.frame_buttons, text="👁 Preview First", command=self.open_preview_window,
            height=50, fg_color="#E67E22", hover_color="#D35400",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.btn_preview.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.btn_convert = ctk.CTkButton(
            self.frame_buttons, text="💾 Convert & Save", command=self.start_conversion_thread,
            height=50, font=ctk.CTkFont(size=16, weight="bold")
        )
        self.btn_convert.pack(side="right", expand=True, fill="x", padx=(10, 0))

        # 5. Status
        self.lbl_status = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.lbl_status.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="s")

        # 6. GitHub Footer
        self.btn_github = ctk.CTkButton(
            self,
            text="Developed by @ItsSp00ky | GitHub",
            command=self.open_github,
            fg_color="transparent",
            text_color=("#3B8ED0", "#1F6AA5"),
            hover_color=("gray90", "gray20"),
            height=20,
            font=ctk.CTkFont(size=11, underline=True)
        )
        self.btn_github.grid(row=5, column=0, pady=(0, 10))

    # --- Small UI helpers ---
    def on_close(self):
        self.is_closing = True
        self.destroy()

    def run_on_ui(self, func, *args):
        """Schedule a callback on the Tk thread; a no-op once the app is closing.

        Worker threads must never touch widgets directly. Scheduling can still
        lose a race with teardown, which surfaces as TclError (widget already
        destroyed) or RuntimeError (main loop no longer running) - both mean the
        UI is gone and the update is simply dropped.
        """
        if self.is_closing:
            return
        try:
            self.after(0, lambda: func(*args))
        except (TclError, RuntimeError):
            pass

    def set_icon(self, window):
        """Apply the app icon across Windows, Linux, and macOS. CTk re-applies
        its own icon shortly after a window is created, so ours has to be
        re-asserted once that has happened."""
        icon_path_ico = resource_path("scanner.ico")
        icon_path_png = resource_path("scanner.png")

        def apply():
            try:
                if not window.winfo_exists():
                    return
                if sys.platform == "win32" and os.path.exists(icon_path_ico):
                    window.iconbitmap(icon_path_ico)
                else:
                    from PIL import ImageTk
                    png_path = icon_path_png if os.path.exists(icon_path_png) else icon_path_ico
                    if os.path.exists(png_path):
                        img = Image.open(png_path)
                        photo = ImageTk.PhotoImage(img)
                        window.iconphoto(False, photo)
                        window._icon_photo_ref = photo
            except Exception:
                pass

        window.after(200, apply)

    def set_status(self, text, color="gray"):
        self.lbl_status.configure(text=text, text_color=color)

    def set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.btn_convert.configure(state=state, text="Processing..." if busy else "💾 Convert & Save")
        self.btn_preview.configure(state=state)
        self.btn_browse.configure(state=state)

    def open_github(self):
        webbrowser.open("https://github.com/ItsSp00ky/pdf_enhancer")

    def update_dpi_label(self, value):
        self.lbl_dpi.configure(text=f"Scan Quality (DPI): {int(value)}")

    def set_input_files(self, paths, source):
        self.input_files = list(paths)
        label = (os.path.basename(self.input_files[0]) if len(self.input_files) == 1
                 else f"{len(self.input_files)} files selected")
        self.lbl_file_path.configure(text=label, text_color=("black", "white"))
        # Naming what was detected is what tells the user the guess was right,
        # now that no mode selector shows it.
        self.set_status(f"Detected {describe_selection(self.input_files)}{source}. Ready.", "green")

    # --- File Selection ---
    def handle_drop(self, event):
        """Handles files dropped into the application window."""
        # splitlist handles Tcl's brace-quoting of paths containing spaces
        raw_files = self.tk.splitlist(event.data)
        dropped_files = []
        for item in raw_files:
            item = item.strip().strip("'").strip('"')
            if item.startswith("file://"):
                parsed = urlparse(item)
                item = unquote(parsed.path)
                if sys.platform == "win32" and item.startswith("/") and len(item) > 2 and item[2] == ":":
                    item = item.lstrip("/")
            if item:
                dropped_files.append(item)

        matches = [f for f in dropped_files if f.lower().endswith(SUPPORTED_EXTENSIONS)]
        if not matches:
            messagebox.showwarning(
                "Invalid File",
                "Please drop a PDF or image files (JPG, PNG, BMP, TIFF)."
            )
            return

        self.set_input_files(matches, " via drag & drop")

    def browse_file(self):
        selection = list(filedialog.askopenfilenames(filetypes=BROWSE_FILETYPES))
        if selection:
            self.set_input_files(selection, "")

    # --- PREVIEW LOGIC (First file only) ---
    def open_preview_window(self):
        if not self.input_files:
            messagebox.showwarning("Warning", "Please select or drop a file first!")
            return

        if self.preview_window is None or not self.preview_window.winfo_exists():
            self.preview_window = ctk.CTkToplevel(self)
            self.preview_window.title("First Item Preview")
            self.preview_window.geometry("600x700")
            self.preview_window.attributes("-topmost", True)
            self.set_icon(self.preview_window)

            lbl_info = ctk.CTkLabel(self.preview_window, text="Previewing First Item Only", font=("Arial", 14, "bold"))
            lbl_info.pack(pady=10)

            self.preview_img_label = ctk.CTkLabel(
                self.preview_window, text="Processing...", width=500, height=600,
                corner_radius=10, fg_color="#2B2B2B"
            )
            self.preview_img_label.pack(padx=20, pady=(0, 20), expand=True, fill="both")
        else:
            self.preview_img_label.configure(text="Processing...", image=None)

        self.preview_window.focus()
        self.btn_preview.configure(state="disabled")

        # Snapshot the widget values here: they must not be read off the worker thread.
        args = (self.input_files[0], int(self.slider_dpi.get()))
        threading.Thread(target=self.run_preview, args=args, daemon=True).start()

    def run_preview(self, path, dpi):
        try:
            if is_pdf(path):
                with fitz.open(path) as doc:
                    if doc.page_count == 0:
                        raise ValueError("PDF is empty.")
                    image = pixmap_to_bgr(doc[0].get_pixmap(dpi=dpi))
            else:
                image = load_image_to_bgr(path)
            preview = Image.fromarray(process_single_page(image))
        except Exception as e:
            print(f"Preview Error: {e}")
            self.run_on_ui(self.preview_failed, str(e))
        else:
            self.run_on_ui(self.update_preview_ui, preview)

    def preview_failed(self, message):
        self.btn_preview.configure(state="normal")
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_img_label.configure(text=f"Could not build preview:\n{message}", image=None)

    def update_preview_ui(self, pil_img):
        self.btn_preview.configure(state="normal")
        if not self.preview_window or not self.preview_window.winfo_exists():
            return

        w, h = pil_img.size
        aspect = h / w
        display_w, display_h = 500, int(500 * aspect)
        if display_h > 600:
            display_h, display_w = 600, int(600 / aspect)

        # Held on the instance so the image is not garbage collected while shown.
        self.current_preview_image = ctk.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=(display_w, display_h)
        )
        self.preview_img_label.configure(image=self.current_preview_image, text="")

    # --- CONVERSION LOGIC ---
    def start_conversion_thread(self):
        if not self.input_files:
            messagebox.showwarning("Warning", "Please select or drop a file first!")
            return

        base = os.path.splitext(os.path.basename(self.input_files[0]))[0]

        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=PDF_FILETYPES,
            initialfile=f"{base}_scanned.pdf",
            title="Save Scanned PDF As"
        )
        if not save_path:
            return

        sources = {os.path.normcase(os.path.abspath(p)) for p in self.input_files}
        if os.path.normcase(os.path.abspath(save_path)) in sources:
            messagebox.showerror("Invalid Destination", "Please choose a different name so the source file is not overwritten.")
            return

        self.set_busy(True)
        args = (list(self.input_files), int(self.slider_dpi.get()), save_path)
        threading.Thread(target=self.run_pipeline, args=args, daemon=True).start()

    def run_pipeline(self, paths, dpi, output_path):
        try:
            processed_pages = []

            for index, total, image in iter_source_images(paths, dpi):
                self.run_on_ui(self.set_status, f"Scanning page {index + 1} of {total}...", "orange")
                enhanced = process_single_page(image)
                # Saved as 1-bit: the data is already black/white, and Pillow can
                # then use CCITT G4 compression instead of storing 8-bit pixels.
                processed_pages.append(Image.fromarray(enhanced).convert("1"))

            if not processed_pages:
                raise ValueError("No pages/images to process.")

            processed_pages[0].save(output_path, save_all=True, append_images=processed_pages[1:])
        except Exception as e:
            self.run_on_ui(self.conversion_failed, str(e))
        else:
            self.run_on_ui(self.conversion_success, output_path)

    def conversion_failed(self, message):
        self.set_busy(False)
        self.set_status("Conversion failed.", "red")
        messagebox.showerror("Error", f"An error occurred:\n{message}")

    def conversion_success(self, path):
        self.set_busy(False)
        self.set_status("Conversion Complete!", "green")
        messagebox.showinfo("Success", f"File saved successfully:\n{path}")

        try:
            open_with_default_app(path)
        except Exception as e:
            print(f"Error opening file: {e}")


def main():
    app = ScannerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
