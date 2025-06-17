# Ahmed Gali
# Copyright (c) 2025 Ahmed Gali
# Licensed under the MIT License

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import gradio as gr
import os

# --- PDF to Images ---
def pdf_to_images_in_memory(pdf_path, dpi=200):
    """Converts each page of a PDF file into a list of images."""
    try:
        doc = fitz.open(pdf_path)
        images = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:  # Handle RGBA to RGB conversion
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            images.append(img)
        return images
    except Exception as e:
        raise gr.Error(f"Failed to read PDF. Error: {e}")


# --- Image Processing Functions (Helper functions) ---
def distance(p1, p2):
    """Calculates the Euclidean distance between two points."""
    return np.linalg.norm(p1 - p2)

def order_rect(pts):
    """Orders the four points of a rectangle contour."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    rect[0] = pts[np.argmin(s)]    # Top-left
    rect[2] = pts[np.argmax(s)]    # Bottom-right
    rect[1] = pts[np.argmin(diff)] # Top-right
    rect[3] = pts[np.argmax(diff)] # Bottom-left
    return rect

def four_point_transform(image, pts):
    """Applies a perspective transform to an image based on four points."""
    rect = order_rect(pts)
    (tl, tr, br, bl) = rect

    # Calculate the width and height of the new image
    widthA = distance(br, bl)
    widthB = distance(tr, tl)
    maxWidth = int(max(widthA, widthB))

    heightA = distance(tr, br)
    heightB = distance(tl, bl)
    maxHeight = int(max(heightA, heightB))

    # Define the destination points for the transformed image
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    # Compute the perspective transform matrix and apply it
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped

# --- Core Image Processing Logic ---
def process_image_cv(image, area_threshold_ratio=0.4, upscale_factor=2):
    """
    Finds the main document in an image, straightens it, and applies a binary
    threshold to create a "scanned" look.
    """
    img_height, img_width = image.shape[:2]
    img_area = img_height * img_width

    # Pre-processing
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    edges = cv2.Canny(blurred, 10, 50)

    # Find the largest 4-sided contour
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    screenCnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > area_threshold_ratio * img_area:
            screenCnt = approx.reshape(4, 2)
            break

    # Apply perspective transform if a document is found, otherwise use the full image
    if screenCnt is not None:
        warped = four_point_transform(image, screenCnt)
    else:
        warped = image # Fallback to using the original image if no contour is found

    # Upscale and apply adaptive threshold for a clean, scanned look
    upscaled = cv2.resize(warped, (0, 0), fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)

    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=91,
        C=30
    )
    return binary

# --- Images to PDF ---
def images_to_pdf_from_arrays(images, output_pdf_path):
    """Saves a list of image arrays to a single PDF file."""
    if not images:
        raise gr.Error("No images were processed to save.")

    pil_images = [Image.fromarray(img).convert('RGB') for img in images]
    pil_images[0].save(output_pdf_path, save_all=True, append_images=pil_images[1:])


# --- Main Processing Function for Gradio ---
def enhance_pdf(pdf_file, dpi):
    """
    Main function that orchestrates the PDF processing workflow.
    This function is called by the Gradio interface.
    """
    if pdf_file is None:
        raise gr.Error("Please upload a PDF file.")

    # 1. Load PDF into images
    images = pdf_to_images_in_memory(pdf_file.name, dpi)

    # 2. Process each image
    processed_images = [process_image_cv(img) for img in images]

    # 3. Save processed images to a new PDF
    output_pdf_path = "output_enhanced.pdf"
    images_to_pdf_from_arrays(processed_images, output_pdf_path)

    return output_pdf_path

# --- Gradio Interface Definition ---
if __name__ == "__main__":
    iface = gr.Interface(
        fn=enhance_pdf,
        inputs=[
            gr.File(label="Upload your PDF", file_types=[".pdf"]),
            gr.Slider(label="Scan Quality (DPI)", minimum=72, maximum=600, value=200, step=1)
        ],
        outputs=gr.File(label="Download Enhanced PDF"),
        title="📄 PDF Print Enhancer",
        description="Upload a PDF to automatically straighten pages and improve contrast for better printing.",
        allow_flagging="never"
    )

    # Launch the web server
    iface.launch(server_name="0.0.0.0",server_port=7860)
