# Ahmed Gali
# Copyright (c) 2025 Ahmed Gali
# Licensed under the MIT License

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import gradio as gr
import os

# --- Geometry & Cropping Helpers ---
def order_points(pts):
    """Orders coordinates: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    """Applies perspective transform to flatten the document."""
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
    """
    1. Detects white paper on dark background.
    2. Crops and flattens.
    3. Converts to high-contrast flat black & white.
    """
    # --- Step 1: Smart Crop (Detect White Paper) ---
    orig_h, orig_w = image.shape[:2]
    ratio = 800.0 / orig_h
    small_img = cv2.resize(image, (int(orig_w * ratio), 800))
    
    # Convert to HSV to find "White" paper easily
    hsv = cv2.cvtColor(small_img, cv2.COLOR_BGR2HSV)
    # Define range for "paper-like" colors (low saturation, high brightness)
    lower_white = np.array([0, 0, 100]) # adjust if paper is darker
    upper_white = np.array([180, 60, 255])
    
    mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # Clean up the mask (remove noise)
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Find the largest contour in the mask (The Paper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

    screenCnt = None
    if contours:
        c = contours[0]
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        # Check if it looks like a page (4 corners & big enough)
        if len(approx) == 4 and cv2.contourArea(approx) > (0.15 * (800 * int(orig_w * ratio))):
            screenCnt = approx

    # Apply Crop if found
    if screenCnt is not None:
        screenCnt = screenCnt.reshape(4, 2) * (1.0 / ratio)
        warped = four_point_transform(image, screenCnt)
    else:
        # Fallback: Use the whole image if no paper edge detected
        warped = image

    # --- Step 2: Make it Flat Black & White ---
    # Convert to grayscale
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    # Adaptive Thresholding: This is the "Scanner" magic.
    # It looks at local neighborhoods to decide black vs white.
    # blockSize=21 (looks at local area), C=10 (constant subtracted from mean)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=21,
        C=10
    )
    
    # Optional: Denoise slightly to remove "pepper" noise
    denoised = cv2.medianBlur(binary, 3) # Removes small black dots

    return denoised

# --- PDF Pipeline ---
def enhance_pdf_pipeline(pdf_file, dpi_val):
    if pdf_file is None:
        raise gr.Error("Please upload a PDF file.")

    output_pdf_path = "output_scanned.pdf"
    
    try:
        doc = fitz.open(pdf_file.name)
        processed_pages = []

        for i, page in enumerate(doc):
            # Render page to image
            pix = page.get_pixmap(dpi=dpi_val)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # Process
            enhanced_img = process_single_page(img)
            
            # Convert to PIL
            pil_img = Image.fromarray(enhanced_img)
            processed_pages.append(pil_img)

        if processed_pages:
            processed_pages[0].save(output_pdf_path, save_all=True, append_images=processed_pages[1:])
            return output_pdf_path
        else:
            raise gr.Error("No pages processed.")

    except Exception as e:
        raise gr.Error(f"Error: {e}")

# ---- Gradio UI ----
if __name__ == "__main__":
    with gr.Blocks(title="📄 Clean Scanner") as iface:
        gr.Markdown("# 📄 Clean Scan Converter")
        gr.Markdown("Upload a PDF. Converts it to a **flat, cropped, black & white** scan.")
        
        with gr.Row():
            in_file = gr.File(label="Upload PDF", file_types=[".pdf"])
            dpi_slider = gr.Slider(minimum=100, maximum=400, value=200, step=50, label="Quality (DPI)")
        
        btn = gr.Button("Convert to Clean Scan", variant="primary")
        out_file = gr.File(label="Download Result")

        btn.click(fn=enhance_pdf_pipeline, inputs=[in_file, dpi_slider], outputs=out_file)

    iface.launch()