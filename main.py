# Ahmed Gali
# Copyright (c) 2025 Ahmed Gali
# Licensed under the MIT License

import pypdfium2 as pdfium
import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageChops
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


def four_point_transform(img_pil, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    maxWidth = max(1, int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))))
    maxHeight = max(1, int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))))
    # Pillow QUAD data format: (tl_x, tl_y, bl_x, bl_y, br_x, br_y, tr_x, tr_y)
    quad_data = (tl[0], tl[1], bl[0], bl[1], br[0], br[1], tr[0], tr[1])
    return img_pil.transform(
        (maxWidth, maxHeight),
        Image.Transform.QUAD,
        quad_data,
        resample=Image.Resampling.BILINEAR
    )


def find_page_quad(img_pil):
    """Locate the document corners in full-resolution coordinates, or None."""
    orig_w, orig_h = img_pil.size
    scale = min(1.0, DETECT_HEIGHT / orig_h)
    if scale < 1.0:
        small_w = max(1, int(orig_w * scale))
        small_h = max(1, int(orig_h * scale))
        small = img_pil.resize((small_w, small_h), Image.Resampling.BILINEAR)
    else:
        small = img_pil
        small_w, small_h = orig_w, orig_h

    rgb = np.asarray(small.convert("RGB"), dtype=np.float32)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)

    # Paper mask: V >= 100 and S <= 60 (OpenCV HSV equivalent: [0,0,100] to [180,60,255])
    mask = (max_c >= 100.0) & ((max_c - min_c) <= (60.0 / 255.0) * max_c)

    mask_img = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    # Open / Close morphology with 5x5 kernel
    opened = mask_img.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
    closed = opened.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))

    # Extract boundary pixels for fast convex hull
    eroded = closed.filter(ImageFilter.MinFilter(3))
    boundary = ImageChops.difference(closed, eroded)

    ys, xs = np.where(np.asarray(boundary) > 0)
    if len(xs) < 4:
        return None

    pts = np.column_stack([xs, ys]).astype(np.float32)

    # Graham scan convex hull
    start_idx = np.lexsort((pts[:, 0], pts[:, 1]))[0]
    start = pts[start_idx]
    diff = pts - start
    angles = np.arctan2(diff[:, 1], diff[:, 0])
    dists = np.hypot(diff[:, 0], diff[:, 1])
    order = np.lexsort((-dists, angles))
    sorted_pts = pts[order]

    hull = [start, sorted_pts[0]]
    for p in sorted_pts[1:]:
        while len(hull) >= 2:
            v1 = hull[-1] - hull[-2]
            v2 = p - hull[-1]
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            if cross <= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    hull = np.array(hull, dtype=np.float32)

    # Perimeter
    diffs = np.diff(np.vstack([hull, hull[0]]), axis=0)
    perim = np.sum(np.hypot(diffs[:, 0], diffs[:, 1]))

    # Douglas-Peucker polygon simplification (at 2% perimeter)
    def point_line_distance(pts_arr, p1, p2):
        diff_l = p2 - p1
        norm_l = np.hypot(diff_l[0], diff_l[1])
        if norm_l < 1e-6:
            return np.hypot(pts_arr[:, 0] - p1[0], pts_arr[:, 1] - p1[1])
        return np.abs(diff_l[0] * (p1[1] - pts_arr[:, 1]) - (p1[0] - pts_arr[:, 0]) * diff_l[1]) / norm_l

    def dp(pts_arr, eps):
        if len(pts_arr) <= 2:
            return pts_arr
        dists_arr = point_line_distance(pts_arr[1:-1], pts_arr[0], pts_arr[-1])
        if len(dists_arr) == 0:
            return pts_arr
        dmax_i = np.argmax(dists_arr) + 1
        if dists_arr[dmax_i - 1] > eps:
            r1 = dp(pts_arr[:dmax_i + 1], eps)
            r2 = dp(pts_arr[dmax_i:], eps)
            return np.vstack((r1[:-1], r2))
        return np.array([pts_arr[0], pts_arr[-1]])

    closed_hull = np.vstack([hull, hull[0]])
    approx = dp(closed_hull, 0.02 * perim)
    if np.allclose(approx[0], approx[-1]):
        approx = approx[:-1]

    if len(approx) != 4:
        return None

    # Shoelace formula for polygon area
    x_coords, y_coords = approx[:, 0], approx[:, 1]
    area = 0.5 * np.abs(np.dot(x_coords, np.roll(y_coords, 1)) - np.dot(y_coords, np.roll(x_coords, 1)))
    if area < MIN_PAGE_AREA_RATIO * small_w * small_h:
        return None

    return approx / scale


def process_single_page(img_pil, dpi=200):
    """Deskew/crop a PIL page image and return it as a binarised 1-bit PIL Image."""
    quad = find_page_quad(img_pil)
    warped = four_point_transform(img_pil, quad) if quad is not None else img_pil

    gray = warped.convert("L")
    # Adaptive Gaussian threshold (radius scaled proportionally with DPI for consistent stroke width)
    radius = max(1.0, (dpi / 200.0) * 3.5)
    blurred = gray.filter(ImageFilter.GaussianBlur(radius=radius))
    arr_g = np.asarray(gray, dtype=np.int16)
    arr_b = np.asarray(blurred, dtype=np.int16)
    binary = np.where(arr_g > (arr_b - 10), 255, 0).astype(np.uint8)

    median_size = 3 if dpi < 300 else 5
    clean = Image.fromarray(binary, mode="L").filter(ImageFilter.MedianFilter(size=median_size))
    return clean.convert("1")


# --- Input Loading ---
def pdf_page_to_image(page, dpi):
    """Render a PDFium page to a PIL RGB image at requested DPI."""
    return page.render(scale=dpi / 72.0).to_pil().convert("RGB")


def load_image(path):
    """Load an image file and convert to RGB format with transparency flattened onto white."""
    with Image.open(path) as opened:
        img = ImageOps.exif_transpose(opened)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            flattened = Image.new("RGB", rgba.size, (255, 255, 255))
            flattened.paste(rgba, mask=rgba)
            return flattened
        return img.convert("RGB")


def is_pdf(path):
    """Input kind is decided per file by extension - there is no global mode."""
    return path.lower().endswith(".pdf")


def count_source_pages(paths):
    """Total output pages: every PDF contributes its page count, every image one."""
    total = 0
    for path in paths:
        if is_pdf(path):
            with pdfium.PdfDocument(path) as doc:
                total += len(doc)
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
    """Yield (index, total, pil_image) for every page of the whole selection.

    PDFs are rasterised page by page and images are loaded whole; both are
    flattened into one continuous page stream in the order they were selected.
    """
    total = count_source_pages(paths)
    index = 0
    for path in paths:
        if is_pdf(path):
            with pdfium.PdfDocument(path) as doc:
                for page_number in range(len(doc)):
                    yield index, total, pdf_page_to_image(doc[page_number], dpi)
                    index += 1
        else:
            yield index, total, load_image(path)
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
        dpi_int = int(round(value))
        self.lbl_dpi.configure(text=f"Scan Quality (DPI): {dpi_int}")
        # If preview window is open, dynamically refresh preview at new DPI
        if hasattr(self, "preview_window") and self.preview_window and self.preview_window.winfo_exists() and self.input_files:
            if hasattr(self, "_dpi_timer") and self._dpi_timer:
                try:
                    self.after_cancel(self._dpi_timer)
                except Exception:
                    pass
            self._dpi_timer = self.after(250, lambda: self.refresh_preview_dpi(dpi_int))

    def refresh_preview_dpi(self, dpi):
        if self.preview_window and self.preview_window.winfo_exists() and self.input_files:
            if hasattr(self, "lbl_preview_info") and self.lbl_preview_info.winfo_exists():
                self.lbl_preview_info.configure(text=f"Rendering at {dpi} DPI...")
            threading.Thread(target=self.run_preview, args=(self.input_files[0], dpi), daemon=True).start()

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

        dpi = int(round(self.slider_dpi.get()))

        if self.preview_window is None or not self.preview_window.winfo_exists():
            self.preview_window = ctk.CTkToplevel(self)
            self.preview_window.title("Preview")
            self.preview_window.geometry("620x720")
            self.preview_window.attributes("-topmost", True)
            self.set_icon(self.preview_window)

            self.lbl_preview_info = ctk.CTkLabel(
                self.preview_window, text=f"Previewing First Item @ {dpi} DPI", font=("Arial", 14, "bold")
            )
            self.lbl_preview_info.pack(pady=10)

            self.preview_img_label = ctk.CTkLabel(
                self.preview_window, text="Processing...", width=500, height=600,
                corner_radius=10, fg_color="#2B2B2B"
            )
            self.preview_img_label.pack(padx=20, pady=(0, 20), expand=True, fill="both")
        else:
            if hasattr(self, "lbl_preview_info") and self.lbl_preview_info.winfo_exists():
                self.lbl_preview_info.configure(text=f"Previewing First Item @ {dpi} DPI")
            self.preview_img_label.configure(text="Processing...", image=None)

        self.preview_window.focus()
        self.btn_preview.configure(state="disabled")

        # Snapshot the widget values here: they must not be read off the worker thread.
        args = (self.input_files[0], dpi)
        threading.Thread(target=self.run_preview, args=args, daemon=True).start()

    def run_preview(self, path, dpi):
        try:
            if is_pdf(path):
                with pdfium.PdfDocument(path) as doc:
                    if len(doc) == 0:
                        raise ValueError("PDF is empty.")
                    image = pdf_page_to_image(doc[0], dpi)
            else:
                image = load_image(path)
            preview = process_single_page(image, dpi=dpi)
        except Exception as e:
            print(f"Preview Error: {e}")
            self.run_on_ui(self.preview_failed, str(e))
        else:
            self.run_on_ui(self.update_preview_ui, preview, dpi)

    def preview_failed(self, message):
        self.btn_preview.configure(state="normal")
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_img_label.configure(text=f"Could not build preview:\n{message}", image=None)

    def update_preview_ui(self, pil_img, dpi):
        self.btn_preview.configure(state="normal")
        if not self.preview_window or not self.preview_window.winfo_exists():
            return

        w, h = pil_img.size
        if hasattr(self, "lbl_preview_info") and self.lbl_preview_info.winfo_exists():
            self.lbl_preview_info.configure(
                text=f"Previewing First Page • {w}×{h} px ({dpi} DPI)"
            )
            self.preview_window.title(f"Preview - {w}×{h} px @ {dpi} DPI")

        aspect = h / w
        display_w, display_h = 500, int(500 * aspect)
        if display_h > 580:
            display_h, display_w = 580, int(580 / aspect)

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
        args = (list(self.input_files), int(round(self.slider_dpi.get())), save_path)
        threading.Thread(target=self.run_pipeline, args=args, daemon=True).start()

    def run_pipeline(self, paths, dpi, output_path):
        try:
            processed_pages = []

            for index, total, image in iter_source_images(paths, dpi):
                self.run_on_ui(self.set_status, f"Scanning page {index + 1} of {total}...", "orange")
                # Saved as 1-bit: the data is already black/white, and Pillow can
                # then use CCITT G4 compression instead of storing 8-bit pixels.
                processed_pages.append(process_single_page(image, dpi=dpi))

            if not processed_pages:
                raise ValueError("No pages/images to process.")

            processed_pages[0].save(
                output_path,
                "PDF",
                resolution=float(dpi),
                save_all=True,
                append_images=processed_pages[1:]
            )
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
