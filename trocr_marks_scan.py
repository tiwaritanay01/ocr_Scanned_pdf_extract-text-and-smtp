"""
trocr_marks_scan.py — Standalone TrOCR Pipeline
================================================
Instructions:
1. pip install -U transformers torch pillow opencv-python numpy pdf2image
2. Ensure poppler is installed and in your PATH for pdf2image.
3. Run: py trocr_marks_scan.py "Your_Marksheet.pdf"
"""

import cv2
import numpy as np
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
from pdf2image import convert_from_path
import re
import pandas as pd
import os

# ─────────────────────────────────────────────────────────────
# 1. TrOCR INITIALIZATION
# ─────────────────────────────────────────────────────────────
print("[Init] Loading TrOCR Model (microsoft/trocr-base-printed)...")
device = "cuda" if torch.cuda.is_available() else "cpu"
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed").to(device)
print(f"[Init] Model loaded on {device.upper()}")

# ─────────────────────────────────────────────────────────────
# 2. IMAGE PRE-PROCESSING (Hybrid Technique)
# ─────────────────────────────────────────────────────────────

def preprocess_for_trocr(cv_img):
    """
    Combines Bilateral filtering and Deskewing for clean OCR.
    """
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # 1. Bilateral filter (Preserves edges, removes noise)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 2. Deskewing
    coords = np.column_stack(np.where(gray < 200))
    if len(coords) > 100:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.1:
            h, w = gray.shape
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            cv_img = cv2.warpAffine(cv_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return gray, cv_img

# ─────────────────────────────────────────────────────────────
# 3. TrOCR ENGINE WRAPPER
# ─────────────────────────────────────────────────────────────

def ocr_with_trocr(cv_roi):
    """
    Submits a CV2 image segment to the TrOCR engine.
    """
    if cv_roi is None or cv_roi.size == 0:
        return ""
        
    # Convert CV2 (BGR/Gray) to PIL (RGB)
    if len(cv_roi.shape) == 2:
        pil_img = Image.fromarray(cv_roi).convert("RGB")
    else:
        pil_img = Image.fromarray(cv2.cvtColor(cv_roi, cv2.COLOR_BGR2RGB))

    # Inference
    pixel_values = processor(pil_img, return_tensors="pt").pixel_values.to(device)
    generated_ids = model.generate(pixel_values)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    return text.strip()

# ─────────────────────────────────────────────────────────────
# 4. GRID & SEGMENTATION LOGIC
# ─────────────────────────────────────────────────────────────

def detect_grid_boundaries(gray_img):
    """
    Detects table lines using morphological operators.
    """
    binary = cv2.adaptiveThreshold(gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10)
    h, w = binary.shape
    
    # Horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 50, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    
    # Vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 50))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    
    # Peak detection for rows and columns
    y_proj = np.sum(h_lines, axis=1)
    x_proj = np.sum(v_lines, axis=0)
    
    y_bounds = [i for i, v in enumerate(y_proj) if v > np.max(y_proj) * 0.3]
    x_bounds = [i for i, v in enumerate(x_proj) if v > np.max(x_proj) * 0.3]
    
    # Cluster points into single lines
    def cluster(points, min_dist=30):
        if not points: return []
        res = [points[0]]
        for p in points[1:]:
            if p - res[-1] > min_dist: res.append(p)
        return res

    return cluster(y_bounds), cluster(x_bounds)

# ─────────────────────────────────────────────────────────────
# 5. MAIN EXTRACTION PIPELINE
# ─────────────────────────────────────────────────────────────

def process_with_trocr(pdf_path):
    print(f"[Pipeline] Processing {pdf_path} with TrOCR...")
    pages = convert_from_path(pdf_path, dpi=300)
    all_data = []

    for page_num, page_pil in enumerate(pages):
        print(f" > Processing Page {page_num+1}/{len(pages)}")
        cv_img = np.array(page_pil)[:, :, ::-1].copy()
        gray, cv_img = preprocess_for_trocr(cv_img)
        
        y_bounds, x_bounds = detect_grid_boundaries(gray)
        
        if len(y_bounds) < 5 or len(x_bounds) < 3:
            print(f" [!] Page {page_num+1}: Table grid not clearly detected. Skipping.")
            continue

        # Find Name column (usually the widest in the first 3 columns)
        name_col_idx = 1
        max_w = 0
        for j in range(min(len(x_bounds)-1, 3)):
            col_w = x_bounds[j+1] - x_bounds[j]
            if col_w > max_w:
                max_w = col_w
                name_col_idx = j
        
        # Result zones (Rightmost portion of the page)
        result_x0 = int(cv_img.shape[1] * 0.70)

        for i in range(len(y_bounds) - 1):
            y0, y1 = y_bounds[i], y_bounds[i+1]
            if (y1 - y0) < 25: continue

            # OCR Name
            name_roi = gray[y0:y1, x_bounds[name_col_idx]:x_bounds[name_col_idx+1]]
            student_name = ocr_with_trocr(name_roi)
            
            if len(student_name) < 5 or any(kw in student_name.upper() for kw in ["COLLEGE", "NAME", "SR.", "TOTAL"]):
                continue

            # OCR Results
            result_roi = gray[y0:y1, result_x0:cv_img.shape[1]-10]
            result_text = ocr_with_trocr(result_roi).upper()
            
            # Post-Processing logic (As requested: kept the same)
            gpa = 0.0
            status = "P"
            if "FAIL" in result_text or "F" == result_text:
                status = "F"
            else:
                gpa_match = re.search(r"(\d{1}\.\d{2})", result_text)
                if gpa_match:
                    gpa = float(gpa_match.group(1))

            print(f"   [FOUND] {student_name} | GPA: {gpa} | Status: {status}")
            all_data.append({"Name": student_name, "GPA": gpa, "Status": status})

    return all_data

if __name__ == "__main__":
    # Test on your provided file or update variable path
    INPUT_FILE = "New_Input.pdf"
    if os.path.exists(INPUT_FILE):
        results = process_with_trocr(INPUT_FILE)
        if results:
            df = pd.DataFrame(results)
            df.to_excel("trocr_extracted_results.xlsx", index=False)
            print(f"\n[Success] Extraction complete. Saved to 'trocr_extracted_results.xlsx'")
        else:
            print("\n[Fail] No student data found.")
    else:
        print(f"\n[Error] File {INPUT_FILE} not found. Please provide a valid PDF.")
