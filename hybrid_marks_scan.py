"""
hybrid_marks_scan.py — Experimental Hybrid OCR Pipeline (Tesseract 5 + TrOCR Sniper)
=====================================================================================
Stand-alone testing script completely isolated from production.

Features:
  1. Content-Aware Whitelisting:
     - CONFIG_NUMERIC: Strict digits for marks/points
     - CONFIG_GRADE: Strict grade characters (O, A, B, C, D, E, P, F)
     - CONFIG_MIXED_CODE: Alphanumeric for subject codes & remarks
     - CONFIG_TEXT: Alphabetical whitelist for student names
     - CONFIG_GPA: Float & status whitelist for pointer cells
  2. Hybrid Tiered Execution:
     - Tier 1: Fast Tesseract 5 with targeted profile (~5-10ms per cell)
     - Validation Gate: Format and vocabulary check
     - Tier 2 (Sniper Fallback): TrOCR triggers ONLY when Tesseract fails validation
  3. Shared Pre- & Post-Processing:
     - Bilateral filtering, adaptive Gaussian binarization, affine deskewing
     - Morphological grid detection & projection clustering
     - OCR character disambiguation (O<->0, B<->8, I<->1, S<->5)
     - Ground-truth fuzzy matching against registered student roster
     - Fail-First status logic

Usage:
  py hybrid_marks_scan.py "New_Input.pdf"
"""

import os
import sys
import time
import re
import difflib
import numpy as np
import cv2
import pandas as pd
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
from dotenv import load_dotenv
import warnings
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# Ensure safe UTF-8 printing in Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

# ─────────────────────────────────────────────────────────────
# 1. Environment & Binary Configurations
# ─────────────────────────────────────────────────────────────

POPPLER_DIRS = [
    os.getenv("POPPLER_PATH"),
    r"C:\Program Files\poppler-25.12.0\Library\bin",
    r"C:\Program Files\poppler\Library\bin",
    r"C:\poppler\Library\bin",
    r"C:\poppler\bin",
]
for p in POPPLER_DIRS:
    if p and os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

tesseract_bin = os.getenv("TESSERACT_CMD")
if tesseract_bin and os.path.exists(tesseract_bin):
    pytesseract.pytesseract.tesseract_cmd = tesseract_bin
elif os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────────────────────
# 2. Dynamic Tesseract Whitelist Configuration Profiles
# ─────────────────────────────────────────────────────────────

CONFIG_NUMERIC    = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
CONFIG_GRADE      = '--oem 3 --psm 10 -c tessedit_char_whitelist=OABCDEFPRV()'
CONFIG_MIXED_CODE = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789OABCDEF'
CONFIG_TEXT       = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz '
CONFIG_GPA        = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.PF'

# ─────────────────────────────────────────────────────────────
# 3. TrOCR Lazy-Loaded Sniper Engine
# ─────────────────────────────────────────────────────────────

_trocr_processor = None
_trocr_model = None
_trocr_device = None
_trocr_available = None

def get_trocr():
    """Lazy loader for TrOCR so script boots instantly without waiting on torch unless needed."""
    global _trocr_processor, _trocr_model, _trocr_device, _trocr_available
    if _trocr_available is False:
        return None, None, None

    if _trocr_model is None:
        try:
            print("  [TrOCR] Initializing TrOCR sniper model (microsoft/trocr-base-printed)...")
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            _trocr_device = "cuda" if torch.cuda.is_available() else "cpu"
            _trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
            _trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed").to(_trocr_device)
            _trocr_model.eval()
            _trocr_available = True
            print(f"  [TrOCR] Loaded successfully on {_trocr_device.upper()}.")
        except Exception as e:
            print(f"  [TrOCR Warning] Could not load TrOCR ({e}). Operating in pure Tesseract mode.")
            _trocr_available = False
            return None, None, None

    return _trocr_processor, _trocr_model, _trocr_device

def trocr_sniper_infer(cell_crop):
    """Executes TrOCR inference on a single cell ROI."""
    processor, model, device = get_trocr()
    if model is None:
        return ""
    try:
        import torch
        if len(cell_crop.shape) == 2:
            pil_img = Image.fromarray(cell_crop).convert("RGB")
        else:
            pil_img = Image.fromarray(cv2.cvtColor(cell_crop, cv2.COLOR_BGR2RGB))

        pixel_values = processor(pil_img, return_tensors="pt").pixel_values.to(device)
        with torch.no_grad():
            generated_ids = model.generate(pixel_values, max_new_tokens=10, num_beams=1)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return text.strip()
    except Exception as e:
        print(f"  [TrOCR Inference Error] {e}")
        return ""

# ─────────────────────────────────────────────────────────────
# 4. Ground-Truth Student Name Loader
# ─────────────────────────────────────────────────────────────

def is_valid_student_name(name):
    """Sanitizes candidate ground-truth names to prevent OCR error leakage."""
    if not name or len(name) < 6:
        return False
    # Strictly require alphabetic characters, spaces, and periods
    if not re.match(r'^[A-Za-z\s.]+$', name):
        return False
    parts = name.strip().split()
    if len(parts) < 2:
        return False
    noise_kws = ["COLLEGE", "ENGINEERING", "UNIVERSITY", "MUMBAI", "SEMESTER",
                 "MARKS", "OBTAINED", "GRADE", "TOTAL", "CREDIT", "RESULT",
                 "POINTER", "PAPER", "SUBJECT", "THEORY", "PRACTICAL", "EXAM", "SEAT"]
    if any(kw in name.upper() for kw in noise_kws):
        return False
    return True

def load_known_names():
    known = set()
    # Note: Only load genuine rosters (exclude legacy/scratch test outputs like students_sem4.xlsx)
    for fname in ["temp_students.xlsx", "Student_ERN_List.xlsx"]:
        if os.path.exists(fname):
            try:
                df = pd.read_excel(fname)
                if "Name" in df.columns:
                    for n in df["Name"].dropna().astype(str):
                        cln = n.strip().upper()
                        if is_valid_student_name(cln):
                            known.add(cln)
            except Exception:
                pass
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "root123"),
            database=os.getenv("DB_NAME", "student_results"),
            port=int(os.getenv("DB_PORT", "3306"))
        )
        cur = conn.cursor()
        cur.execute("SELECT student_name FROM student_name")
        for (name,) in cur.fetchall():
            cln = str(name).strip().upper()
            if is_valid_student_name(cln):
                known.add(cln)
        cur.close()
        conn.close()
    except Exception:
        pass
    return list(known)

KNOWN_NAMES = load_known_names()
print(f"[Init] Ground-truth database loaded: {len(KNOWN_NAMES)} known student identities.")

# ─────────────────────────────────────────────────────────────
# 5. Vision Pre-Processing & Grid Segmentation
# ─────────────────────────────────────────────────────────────

def preprocess_image(cv_img):
    """Denoise, adaptive binarize, and deskew."""
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # 1. Bilateral filter (edge preserving)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 2. Adaptive Gaussian Binarization (inverted)
    binary_inv = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 21, 10
    )
    
    # 3. Deskew
    coords = np.column_stack(np.where(binary_inv > 0))
    if len(coords) > 100:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.1:
            h, w = gray.shape
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            cv_img = cv2.warpAffine(cv_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            binary_inv = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 21, 10
            )

    return gray, cv_img, binary_inv

def detect_grid_boundaries(gray_img, binary_inv):
    """Isolate horizontal & vertical lines and cluster projection peaks."""
    h, w = gray_img.shape
    edges = cv2.Canny(gray_img, 50, 150, apertureSize=3)

    # Horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 60, 1))
    h_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, h_kernel)
    h_lines = cv2.dilate(h_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)), iterations=2)

    # Vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 60))
    v_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, v_kernel)
    v_lines = cv2.dilate(v_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1)), iterations=2)

    def get_boundaries(line_img, axis, min_dist):
        proj = np.sum(line_img, axis=axis)
        peak_thresh = np.max(proj) * 0.2 if np.max(proj) > 0 else 1
        pos = np.where(proj > peak_thresh)[0]
        if len(pos) == 0:
            return []
        clusters = []
        c = [pos[0]]
        for i in range(1, len(pos)):
            if pos[i] - pos[i-1] < min_dist:
                c.append(pos[i])
            else:
                clusters.append(int(np.mean(c)))
                c = [pos[i]]
        clusters.append(int(np.mean(c)))
        return sorted(list(set(clusters)))

    y_bounds = get_boundaries(h_lines, axis=1, min_dist=25)
    x_bounds = get_boundaries(v_lines, axis=0, min_dist=40)

    # Fallback if edges were too sparse
    if len(x_bounds) < 3 or len(y_bounds) < 10:
        h_lines_fb = cv2.morphologyEx(binary_inv, cv2.MORPH_OPEN, h_kernel)
        v_lines_fb = cv2.morphologyEx(binary_inv, cv2.MORPH_OPEN, v_kernel)
        y_bounds_fb = get_boundaries(h_lines_fb, axis=1, min_dist=25)
        x_bounds_fb = get_boundaries(v_lines_fb, axis=0, min_dist=40)
        if len(y_bounds_fb) > len(y_bounds):
            y_bounds = y_bounds_fb
        if len(x_bounds_fb) > len(x_bounds):
            x_bounds = x_bounds_fb

    return y_bounds, x_bounds

def find_columns_geometry(x_bounds, img_width):
    """
    Identifies Name column (widest gap in first columns) and isolates
    the precise Result column [x_bounds[-2]..x_bounds[-1]] to avoid capturing
    intermediate subject marks/failures.
    """
    if len(x_bounds) < 3:
        return int(img_width * 0.05), int(img_width * 0.20), int(img_width * 0.85), img_width - 10, 0

    best_gap = 0
    best_idx = 1
    for idx in range(min(len(x_bounds) - 1, 5)):
        gap = x_bounds[idx + 1] - x_bounds[idx]
        if gap > best_gap:
            best_gap = gap
            best_idx = idx

    name_x0 = x_bounds[best_idx]
    name_x1 = x_bounds[best_idx + 1] if best_idx + 1 < len(x_bounds) else int(img_width * 0.40)
    sr_x0 = x_bounds[best_idx - 1] if best_idx > 0 else 0

    if len(x_bounds) >= 4:
        result_x0 = x_bounds[-2]
        result_x1 = x_bounds[-1]
    else:
        result_x0 = int(img_width * 0.85)
        result_x1 = img_width - 10

    return name_x0, name_x1, result_x0, result_x1, sr_x0

# ─────────────────────────────────────────────────────────────
# 6. Hybrid Cell OCR Engine (Tesseract Fast-Path + TrOCR Sniper)
# ─────────────────────────────────────────────────────────────

# Global benchmark counters
BENCHMARK_STATS = {
    "tesseract_fast_hits": 0,
    "trocr_sniper_hits": 0,
}

def read_cell_hybrid(cell_crop, cell_type="text", enable_trocr_fallback=False):
    """
    Tier 1: Tesseract 5 with specific whitelist profile (~5ms).
    Validation: Check format compliance.
    Tier 2: TrOCR Sniper fallback (Only triggered on locked/critical cells if enable_trocr_fallback is True).
    Post-Processing: Enforce domain character disambiguation.
    """
    if cell_crop is None or cell_crop.size == 0 or np.mean(cell_crop) > 252:
        return ""

    # Reconnect strokes damaged by morphological line subtraction
    if cell_type in ["numeric", "grade"]:
        kernel = np.ones((2, 2), np.uint8)
        cell_crop = cv2.dilate(cell_crop, kernel, iterations=1)

    # Upscale small cells for Tesseract
    h, w = cell_crop.shape[:2]
    if h < 60:
        scale = 60 / h
        cell_crop = cv2.resize(cell_crop, (int(w * scale), 60), interpolation=cv2.INTER_CUBIC)

    # 1. Select Configuration Profile
    if cell_type == "numeric":
        config = CONFIG_NUMERIC
    elif cell_type == "grade":
        config = CONFIG_GRADE
    elif cell_type == "mixed":
        config = CONFIG_MIXED_CODE
    elif cell_type == "gpa":
        config = CONFIG_GPA
    else:
        config = CONFIG_TEXT

    # 2. Tier 1: Fast Tesseract Pass
    text = pytesseract.image_to_string(cell_crop, config=config).strip()
    if cell_type == "text" and len(text) < 4:
        txt11 = pytesseract.image_to_string(cell_crop, config="--psm 11").strip()
        if len(txt11) >= 4:
            text = txt11

    # 3. Validation Gate
    is_valid = False
    if cell_type == "numeric":
        is_valid = bool(re.match(r"^\d+$", text))
    elif cell_type == "grade":
        is_valid = text in ["O", "A", "B", "C", "D", "E", "P", "F"]
    elif cell_type == "gpa":
        is_valid = bool(re.match(r"^\d{1,2}\.\d{1,2}$", text)) or text in ["P", "F", "PASS", "FAIL"]
    elif cell_type == "text":
        is_valid = len(text) >= 4 and not re.search(r"^\d+$", text)
    else:
        is_valid = len(text) > 0

    if is_valid:
        BENCHMARK_STATS["tesseract_fast_hits"] += 1
    elif enable_trocr_fallback:
        # 4. Tier 2: TrOCR Sniper Fallback (Only if cell actually has ink pixels)
        dark_pixels = np.sum(cell_crop < 190)
        if dark_pixels > 60:
            trocr_res = trocr_sniper_infer(cell_crop)
            if trocr_res:
                BENCHMARK_STATS["trocr_sniper_hits"] += 1
                text = trocr_res

    # 5. Domain-Specific Disambiguation (Post-Processing)
    if cell_type == "numeric":
        text = text.replace("O", "0").replace("I", "1").replace("l", "1").replace("S", "5").replace("B", "8")
        text = re.sub(r"[^\d]", "", text)
    elif cell_type == "grade":
        text = text.upper().replace("0", "O").replace("8", "B")
        text = re.sub(r"[^OABCDEFPRV]", "", text)
        if len(text) > 1:
            text = text[0]  # Single letter grade

    return text

# ─────────────────────────────────────────────────────────────
# 7. Fuzzy Entity Matching & Parsing Heuristics
# ─────────────────────────────────────────────────────────────

def fuzzy_match_entity(candidate, known_names, cutoff=0.55):
    if not candidate or len(candidate) < 3:
        return None, 0
    candidate = candidate.upper().strip()
    candidate = re.sub(r'^(SR|NAME|SEAT|STUDENT|NO|RESULT|EXAM|TOTAL|CREDIT)', '', candidate)
    candidate = re.sub(r'[^A-Z\s]', ' ', candidate)
    candidate = re.sub(r'\s+', ' ', candidate).strip()
    if len(candidate) < 4:
        return None, 0

    noise_kws = ["COLLEGE", "ENGINEERING", "UNIVERSITY", "MUMBAI", "SEMESTER",
                 "MARKS", "OBTAINED", "GRADE", "TOTAL", "CREDIT", "RESULT",
                 "POINTER", "PAPER", "SUBJECT", "THEORY", "PRACTICAL"]
    if any(kw in candidate for kw in noise_kws):
        return None, 0

    # Strategy 1: difflib close matches
    matches = difflib.get_close_matches(candidate, known_names, n=1, cutoff=cutoff)
    if matches:
        score = difflib.SequenceMatcher(None, candidate, matches[0]).ratio()
        return matches[0], score

    # Strategy 2: Substring containment for compound names
    for kn in known_names:
        if (len(candidate) > 10 and candidate in kn) or (len(kn) > 10 and kn in candidate):
            return kn, 0.9

    return None, 0

def parse_marks_box_hybrid(block_crop):
    """
    Robust multi-tier marks & GPA parser for the isolated Result column.
    
    Tiers:
    1. Direct Float Detection:
       Run Tesseract PSM 6 & PSM 11. Search for GPA float (4.0 <= val <= 10.0).
       Also handle perfect 10 CGPA (e.g., '230 10' or ' 10 ').
    2. Mathematical Validation & Recovery:
       In Mumbai University engineering mark sheets:
         EC = Total Credits (23 for full semester)
         ECG = Total Grade Points
         GPA = ECG / 23.0
       If student passed (EC=23) but decimal was dropped or missing:
         - Missing-dot recovery: 3-digit int in 400..1000 -> int / 100.0 (e.g. 843 -> 8.43)
         - Or computed as round(ECG / 23.0, 2)
    3. Tier 2 TrOCR Sniper Fallback:
       If no valid float found yet, crop bottom GPA sub-cell and infer with TrOCR sniper.
    4. Fail-First Decision:
       - If explicit 'F', or credits < 23 (e.g. 20, 14, 0), or GPA has '--' / '—',
         and no confirmed passing GPA >= 4.0 was established: Status = 'F', GPA = 0.0.
       - If confirmed valid GPA >= 4.0 exists and no explicit FAIL/ATKT keyword: Status = 'P', GPA = val.
       - Defaults to Status = 'F', GPA = 0.0.
    """
    # 1. OCR Block with PSM 6 and PSM 11
    text_psm6 = pytesseract.image_to_string(block_crop, config="--psm 6").upper().replace(",", ".")
    text_psm11 = pytesseract.image_to_string(block_crop, config="--psm 11").upper().replace(",", ".")
    combined_text = text_psm6 + "\n" + text_psm11

    # Search for direct GPA float
    all_floats = re.findall(r"(\d{1,2}\.\d{1,2})", combined_text)
    valid_gpa = None
    if all_floats:
        for num in reversed(all_floats):
            try:
                val = float(num)
                if 4.0 <= val <= 10.0:
                    valid_gpa = val
                    break
            except Exception:
                continue

    # Also check for perfect 10 CGPA (e.g., '230 10' or ' 10 ')
    if not valid_gpa and re.search(r'\b230\s+10\b|\b10\.00\b|\b 10\b', combined_text):
        if re.search(r'\b23\b', combined_text):
            valid_gpa = 10.0

    # 2. Check Credits & ECG (Mumbai University standard EC=23)
    credits_match = re.search(r'\b(23|20|18|14|12|10)\s+(\d{2,3})\b', combined_text)
    ec = int(credits_match.group(1)) if credits_match else None
    ecg = int(credits_match.group(2)) if credits_match else None

    # Missing Decimal & Formula Recovery if EC=23
    if not valid_gpa and ec == 23 and ecg and 92 <= ecg <= 230:
        computed_gpa = round(ecg / 23.0, 2)
        dotless = re.search(r'\b(\d{3})\b', combined_text)
        if dotless and 400 <= int(dotless.group(1)) <= 1000:
            rec = round(int(dotless.group(1)) / 100.0, 2)
            if abs(rec - computed_gpa) < 0.05:
                valid_gpa = rec
        if not valid_gpa:
            valid_gpa = computed_gpa

    # 3. Tier 2: TrOCR Sniper on Bottom Cell if GPA is still missing
    if not valid_gpa:
        h, w = block_crop.shape[:2]
        bottom_cell = block_crop[int(h * 0.45):h, :]
        dark_pixels = np.sum(bottom_cell < 190)
        if dark_pixels > 60:
            trocr_txt = trocr_sniper_infer(bottom_cell).upper().replace(",", ".")
            trocr_matches = re.findall(r"(\d{1,2}\.\d{1,2})", trocr_txt)
            if trocr_matches:
                for num in reversed(trocr_matches):
                    try:
                        val = float(num)
                        if 4.0 <= val <= 10.0:
                            BENCHMARK_STATS["trocr_sniper_hits"] += 1
                            valid_gpa = val
                            break
                    except Exception:
                        continue

    # 4. Final Status Evaluation (Fail-First)
    is_explicit_fail = bool(re.search(r'\bFAIL\b|\bATKT\b|\bNULL\b|^F$|\sF\s|\bF\b', combined_text))
    has_dashes = bool(re.search(r'--|—', combined_text))
    is_fail = is_explicit_fail or (ec is not None and ec < 23) or (has_dashes and not valid_gpa)

    if valid_gpa:
        if re.search(r'\bFAIL\b|\bATKT\b', combined_text):
            return 0.0, "F"
        BENCHMARK_STATS["tesseract_fast_hits"] += 1
        return valid_gpa, "P"
    elif is_fail or not valid_gpa:
        return 0.0, "F"
    else:
        return 0.0, "F"

# ─────────────────────────────────────────────────────────────
# 8. Main Multi-Page Processing Loop
# ─────────────────────────────────────────────────────────────

def process_hybrid_pipeline(pdf_path):
    print(f"\n{'='*70}")
    print(f"[START] Hybrid OCR Pipeline on: {pdf_path}")
    print(f"{'='*70}")
    
    # Pre-warm TrOCR so loading output does not disrupt per-page status
    get_trocr()

    t0 = time.time()
    try:
        pages = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"[Error] Failed to convert PDF: {e}")
        return []

    print(f"Loaded {len(pages)} page(s) at 300 DPI.\n")
    all_results = []
    seen_names = set()

    for page_idx, page_pil in enumerate(pages):
        page_start = time.time()
        print(f"--- Processing Page {page_idx + 1}/{len(pages)} ---")
        
        cv_img = np.array(page_pil)[:, :, ::-1].copy()
        gray, cv_img, binary_inv = preprocess_image(cv_img)
        y_bounds, x_bounds = detect_grid_boundaries(gray, binary_inv)

        if len(x_bounds) < 2 or len(y_bounds) < 5:
            print(f"  [!] Sparse grid detected. Skipping page {page_idx + 1}.")
            continue

        name_x0, name_x1, result_x0, result_x1, sr_x0 = find_columns_geometry(x_bounds, gray.shape[1])
        print(f"  Grid detected: {len(y_bounds)} rows, {len(x_bounds)} columns.")
        print(f"  Name Column: [{name_x0}..{name_x1}] | Result Column: [{result_x0}..{result_x1}]")

        i = 0
        page_students = 0

        while i < len(y_bounds) - 1:
            # Stop if approaching bottom footer stamp (>86% page height)
            if y_bounds[i] > gray.shape[0] * 0.86:
                break

            matched_name = None

            # Look ahead up to 5 sub-rows to anchor the student name
            for off in range(0, 5):
                idx = i + off
                if idx + 1 >= len(y_bounds):
                    break
                name_cell = gray[y_bounds[idx]:y_bounds[idx+1], name_x0:name_x1]
                raw_name = read_cell_hybrid(name_cell, cell_type="text")
                m_n, score = fuzzy_match_entity(raw_name, KNOWN_NAMES)
                if m_n and m_n not in seen_names:
                    matched_name = m_n
                    i = idx
                    break

            if not matched_name:
                i += 1
                continue

            # Determine student block boundary (typically 3 to 5 sub-rows)
            block_end_i = min(i + 6, len(y_bounds) - 1)
            for k in range(i + 3, block_end_i):
                if k + 1 >= len(y_bounds) or y_bounds[k] > gray.shape[0] * 0.86:
                    block_end_i = k
                    break
                # Check for next student name
                chk_cell = gray[y_bounds[k]:y_bounds[k+1], name_x0:name_x1]
                chk_text = read_cell_hybrid(chk_cell, cell_type="text")
                m_next, _ = fuzzy_match_entity(chk_text, KNOWN_NAMES)
                if m_next and m_next != matched_name:
                    block_end_i = k
                    break
                # Check for next sequential serial number
                sr_cell = gray[y_bounds[k]:y_bounds[k+1], sr_x0:name_x0]
                sr_text = read_cell_hybrid(sr_cell, cell_type="numeric")
                if re.match(r"^\d{1,3}$", sr_text):
                    block_end_i = k
                    break

            # Process marks & GPA block for this student within isolated Result column
            block_roi = gray[y_bounds[i]:y_bounds[block_end_i], result_x0:result_x1]
            gpa, status = parse_marks_box_hybrid(block_roi)

            # Sample sub-row inspection using Dynamic Whitelist Profiles:
            # Check if any sub-row in this block contains letter grades vs numeric marks
            grade_samples = []
            for sub_k in range(i + 1, min(i + 4, block_end_i)):
                # Inspect first subject column right after name
                if len(x_bounds) > 3:
                    sub_col_x0 = x_bounds[2]
                    sub_col_x1 = x_bounds[3] if len(x_bounds) > 4 else x_bounds[-1]
                    sub_crop = gray[y_bounds[sub_k]:y_bounds[sub_k+1], sub_col_x0:sub_col_x1]
                    
                    # Test Grade Profile
                    g_char = read_cell_hybrid(sub_crop, cell_type="grade")
                    if g_char in ["O", "A", "B", "C", "D", "E", "P", "F"]:
                        grade_samples.append(g_char)

            grade_summary = f"Sample Grade: {grade_samples[0]}" if grade_samples else "Grades: Dynamic"

            print(f"  [STUDENT] {matched_name:<30} | GPA: {gpa:<4} | Status: {status} | {grade_summary}")
            all_results.append({
                "Page": page_idx + 1,
                "Name": matched_name,
                "GPA": gpa,
                "Status": status
            })
            seen_names.add(matched_name)
            page_students += 1
            i = block_end_i

        page_duration = time.time() - page_start
        print(f"  Completed Page {page_idx + 1} in {page_duration:.2f}s ({page_students} students extracted).\n")

    total_duration = time.time() - t0
    return all_results, total_duration

# ─────────────────────────────────────────────────────────────
# 9. Execution Entrypoint & Performance Report
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "New_Input.pdf"
    
    if not os.path.exists(target_file):
        print(f"[Error] Target file '{target_file}' not found.")
        sys.exit(1)

    results, elapsed = process_hybrid_pipeline(target_file)
    output_xlsx = "hybrid_test_results.xlsx"

    if results:
        df = pd.DataFrame(results)
        df.to_excel(output_xlsx, index=False)

        pass_count = sum(1 for r in results if r["Status"] == "P" and r["GPA"] > 0)
        fail_count = sum(1 for r in results if r["Status"] == "F")
        zero_gpa_count = sum(1 for r in results if r["Status"] == "P" and r["GPA"] == 0)

        print(f"{'='*70}")
        print(f"[REPORT] HYBRID PIPELINE TEST BENCHMARK REPORT")
        print(f"{'='*70}")
        print(f"Target File:               {target_file}")
        print(f"Total Execution Time:      {elapsed:.2f} seconds")
        print(f"Total Students Extracted:  {len(results)}")
        print(f"  - Passed (with GPA):     {pass_count}")
        print(f"  - Failed (Status F):     {fail_count}")
        print(f"  - Pass (Needs Review):   {zero_gpa_count}")
        print(f"----------------------------------------------------------------------")
        print(f"[METRICS] Speed & Efficiency Breakdown:")
        print(f"  - Tesseract Fast-Path:   {BENCHMARK_STATS['tesseract_fast_hits']} cells (~5-10ms each)")
        print(f"  - TrOCR Sniper Hits:     {BENCHMARK_STATS['trocr_sniper_hits']} cells (triggered on failure)")
        print(f"----------------------------------------------------------------------")
        print(f"[OUTPUT] Results saved to Excel:  {output_xlsx}")
        print(f"{'='*70}\n")
    else:
        print("[!] No results could be extracted.")
