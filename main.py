# Ahmed Gali
# Copyright (c) 2025 Ahmed Gali
# Licensed under the MIT License

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import os
import sys
import threading
import webbrowser  # <--- Added for GitHub link
import subprocess  # <--- Added for opening files on non-Windows systems
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- RESOURCE HELPER FOR EXE ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Geometry & Cropping Helpers ---
def order_points(pts):
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
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))

def process_single_page(image):
    # Resize for processing speed
    orig_h, orig_w = image.shape[:2]
    ratio = 800.0 / orig_h
    small_img = cv2.resize(image, (int(orig_w * ratio), 800))
    
    # Edge Detection
    hsv = cv2.cvtColor(small_img, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 100])
    upper_white = np.array([180, 60, 255])
    mask = cv2.inRange(hsv, lower_white, upper_white)
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]
    screenCnt = None
    
    if contours:
        c = contours[0]
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > (0.15 * (800 * int(orig_w * ratio))):
            screenCnt = approx
            
    # Transform
    if screenCnt is not None:
        screenCnt = screenCnt.reshape(4, 2) * (1.0 / ratio)
        warped = four_point_transform(image, screenCnt)
    else:
        warped = image
        
    # Thresholding
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
    denoised = cv2.medianBlur(binary, 3)
    return denoised

# --- GUI Logic ---
class ScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("PDF Enhancer")
        self.geometry("600x450") # Increased height slightly for the footer
        self.resizable(False, False)

        # SET ICON
        try:
            icon_path = resource_path("scanner.ico")
            self.iconbitmap(icon_path)
        except Exception:
            pass  # Icon not found, use default

        # Layout Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Title
        self.grid_rowconfigure(1, weight=0) # Input
        self.grid_rowconfigure(2, weight=0) # Settings
        self.grid_rowconfigure(3, weight=0) # Buttons
        self.grid_rowconfigure(4, weight=1) # Status
        self.grid_rowconfigure(5, weight=0) # GitHub Footer (NEW)

        # 1. Header
        self.lbl_title = ctk.CTkLabel(self, text="📄 PDF Clean Scanner", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 2. File Selection
        self.frame_file = ctk.CTkFrame(self)
        self.frame_file.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.lbl_file_path = ctk.CTkLabel(self.frame_file, text="No PDF selected", text_color="gray")
        self.lbl_file_path.pack(side="left", padx=15, pady=15)
        
        self.btn_browse = ctk.CTkButton(self.frame_file, text="Browse PDF", command=self.browse_file)
        self.btn_browse.pack(side="right", padx=15, pady=15)

        # 3. Settings
        self.frame_settings = ctk.CTkFrame(self)
        self.frame_settings.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.lbl_dpi = ctk.CTkLabel(self.frame_settings, text="Scan Quality (DPI): 200")
        self.lbl_dpi.pack(side="top", pady=(10, 0))
        
        self.slider_dpi = ctk.CTkSlider(self.frame_settings, from_=100, to=400, number_of_steps=6, command=self.update_dpi_label)
        self.slider_dpi.set(200)
        self.slider_dpi.pack(side="top", fill="x", padx=20, pady=(5, 15))

        # 4. Buttons
        self.frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_buttons.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        
        self.btn_preview = ctk.CTkButton(self.frame_buttons, text="👁 Preview First Page", command=self.open_preview_window, height=50, fg_color="#E67E22", hover_color="#D35400", font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_preview.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.btn_convert = ctk.CTkButton(self.frame_buttons, text="💾 Convert & Save", command=self.start_conversion_thread, height=50, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_convert.pack(side="right", expand=True, fill="x", padx=(10, 0))

        # 5. Status
        self.lbl_status = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.lbl_status.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="s")

        # 6. GitHub Footer (NEW)
        self.btn_github = ctk.CTkButton(
            self, 
            text="Developed by @ItsSp00ky | GitHub", 
            command=self.open_github,
            fg_color="transparent",
            text_color=("#3B8ED0", "#1F6AA5"), # Link blue
            hover_color=("gray90", "gray20"),
            height=20,
            font=ctk.CTkFont(size=11, underline=True)
        )
        self.btn_github.grid(row=5, column=0, pady=(0, 10))

        # Application State
        self.selected_file = None
        
        # Preview State
        self.preview_window = None
        self.preview_doc = None
        self.preview_img_label = None
        self.current_preview_image = None 

    def open_github(self):
        webbrowser.open("https://github.com/ItsSp00ky/pdf_enhancer")

    def update_dpi_label(self, value):
        self.lbl_dpi.configure(text=f"Scan Quality (DPI): {int(value)}")

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filename:
            self.selected_file = filename
            self.lbl_file_path.configure(text=os.path.basename(filename), text_color=("black", "white"))
            self.lbl_status.configure(text="File loaded. Ready.", text_color="green")

    # --- PREVIEW LOGIC (SINGLE PAGE ONLY) ---
    def open_preview_window(self):
        if not self.selected_file:
            messagebox.showwarning("Warning", "Please select a PDF file first!")
            return
            
        try:
            self.preview_doc = fitz.open(self.selected_file)
            if len(self.preview_doc) < 1:
                messagebox.showerror("Error", "PDF is empty.")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Could not open PDF: {e}")
            return

        if self.preview_window is None or not self.preview_window.winfo_exists():
            self.preview_window = ctk.CTkToplevel(self)
            self.preview_window.title("First Page Preview")
            self.preview_window.geometry("600x700")
            
            # --- MAKE WINDOW APPEAR ON TOP ---
            self.preview_window.attributes("-topmost", True)
            
            # --- SET ICON FOR PREVIEW ---
            try:
                icon_path = resource_path("scanner.ico")
                self.preview_window.iconbitmap(icon_path)
            except:
                pass

            self.preview_window.protocol("WM_DELETE_WINDOW", self.close_preview_window)
            
            # Title
            lbl_info = ctk.CTkLabel(self.preview_window, text="Previewing First Page Only", font=("Arial", 14, "bold"))
            lbl_info.pack(pady=10)

            # Image Area
            self.preview_img_label = ctk.CTkLabel(self.preview_window, text="Processing...", width=500, height=600, corner_radius=10, fg_color="#2B2B2B")
            self.preview_img_label.pack(padx=20, pady=(0, 20), expand=True, fill="both")
        
        self.preview_window.focus()
        
        # Start processing thread for Page 0
        threading.Thread(target=self.process_preview_thread, daemon=True).start()

    def close_preview_window(self):
        if self.preview_doc:
            self.preview_doc.close()
            self.preview_doc = None
        self.preview_window.destroy()

    def process_preview_thread(self):
        try:
            # Always load page 0
            page = self.preview_doc[0]
            dpi_val = int(self.slider_dpi.get())
            pix = page.get_pixmap(dpi=dpi_val)
            
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            enhanced = process_single_page(img)
            pil_img = Image.fromarray(enhanced)
            
            # Pass result to UI thread
            self.after(0, lambda: self.update_preview_ui(pil_img))
            
        except Exception as e:
            print(f"Preview Error: {e}")
            self.after(0, lambda: self.preview_img_label.configure(text="Error loading page.", image=None))

    def update_preview_ui(self, pil_img):
        # Check if window was closed during processing
        if not self.preview_window or not self.preview_window.winfo_exists():
            return

        # 1. Calculate Dimensions
        w, h = pil_img.size
        aspect = h / w
        display_w = 500
        display_h = int(display_w * aspect)
        
        if display_h > 600:
            display_h = 600
            display_w = int(display_h / aspect)

        # 2. Create CTkImage
        # Creating CTkImage on the main thread (here) prevents the TclError
        self.current_preview_image = ctk.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=(display_w, display_h)
        )

        # 3. Update Label
        self.preview_img_label.configure(image=self.current_preview_image, text="")

    # --- CONVERSION LOGIC ---
    def start_conversion_thread(self):
        if not self.selected_file:
            messagebox.showwarning("Warning", "Please select a PDF file first!")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=os.path.splitext(os.path.basename(self.selected_file))[0] + "_scanned.pdf",
            title="Save Scanned PDF As"
        )

        if not save_path:
            return 

        self.btn_convert.configure(state="disabled", text="Processing...")
        self.btn_preview.configure(state="disabled")
        self.btn_browse.configure(state="disabled")
        
        threading.Thread(target=self.run_pipeline, args=(save_path,), daemon=True).start()

    def run_pipeline(self, output_path):
        try:
            doc = fitz.open(self.selected_file)
            processed_pages = []
            dpi_val = int(self.slider_dpi.get())
            total_pages = len(doc)

            for i, page in enumerate(doc):
                self.after(0, lambda p=i+1, t=total_pages: self.lbl_status.configure(text=f"Scanning Page {p} of {t}...", text_color="orange"))
                
                pix = page.get_pixmap(dpi=dpi_val)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                
                if pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                elif pix.n == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                enhanced = process_single_page(img)
                pil_img = Image.fromarray(enhanced)
                processed_pages.append(pil_img)

            if processed_pages:
                processed_pages[0].save(output_path, save_all=True, append_images=processed_pages[1:])
                self.after(0, lambda: self.conversion_success(output_path))
            else:
                self.after(0, lambda: messagebox.showerror("Error", "No pages found in PDF."))

        except Exception as e:
            self.after(0, lambda err=str(e): messagebox.showerror("Error", f"An error occurred:\n{err}"))
            self.after(0, self.reset_ui)

    def conversion_success(self, path):
        messagebox.showinfo("Success", f"File saved successfully:\n{path}")
        self.lbl_status.configure(text="Conversion Complete!", text_color="green")
        
        # --- OPEN FILE LOGIC ---
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", path])
            else:  # Linux
                subprocess.call(["xdg-open", path])
        except Exception as e:
            print(f"Error opening file: {e}")
        # -----------------------

        self.reset_ui()

    def reset_ui(self):
        self.btn_convert.configure(state="normal", text="Convert & Save As...")
        self.btn_preview.configure(state="normal")
        self.btn_browse.configure(state="normal")

if __name__ == "__main__":
    app = ScannerApp()
    app.mainloop()