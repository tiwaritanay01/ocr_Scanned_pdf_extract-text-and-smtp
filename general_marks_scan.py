"""
general_marks_scan.py — Generalized, Robust Marksheet OCR Pipeline
===================================================================
Built from the best-performing pipelines across SEM-III COMP DEC-2023
Part 1 (15 pages) and Sem3_part2 (22 pages).

Pipelines:
  1. Image Preprocessing: Grayscale → Deskew → Adaptive Binarization
  2. Grid Detection: Morphological line detection + Canny fallback
  3. Adaptive Column Detection: Handles variable left-margin layouts
  4. Fuzzy Name Matching: DB-backed entity matching with containment
  5. Multi-mode GPA Extraction: Composite block + row-by-row + multi-PSM
  6. Status Detection: Fail-first with strict word boundaries
"""

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
import re
import pandas as pd
import difflib
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Ensure Poppler is in PATH (Cross-platform)
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

# Configure Tesseract path (Windows fallback / Linux native)
tesseract_bin = os.getenv("TESSERACT_CMD")
if tesseract_bin and os.path.exists(tesseract_bin):
    pytesseract.pytesseract.tesseract_cmd = tesseract_bin
elif os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────────────────────
# DB: Load ground-truth student names (Primary Truth Source)
# ─────────────────────────────────────────────────────────────

def get_scan_db_conn():
    try:
        from main import get_db_conn
        return get_db_conn()
    except Exception:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "root123"),
            database=os.getenv("DB_NAME", "student_results"),
            port=int(os.getenv("DB_PORT", "3306"))
        )

def load_known_names():
    known = set()

    # 1. Local Excel fallbacks
    for fname in ["temp_students.xlsx", "Student_ERN_List.xlsx", "students_sem4.xlsx"]:
        if os.path.exists(fname):
            try:
                df = pd.read_excel(fname)
                if "Name" in df.columns:
                    for n in df["Name"].dropna().astype(str):
                        known.add(n.strip().upper())
            except Exception:
                pass

    # 2. MySQL student_name table (Primary Source)
    try:
        conn = get_scan_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT student_name FROM student_name")
        for (name,) in cur.fetchall():
            known.add(str(name).strip().upper())
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB] Warning: {e}")

    return list(known)

KNOWN_NAMES = load_known_names()
print(f"[Init] Loaded {len(KNOWN_NAMES)} known student names.")

# ─────────────────────────────────────────────────────────────
# Step 1: Vision-based Grid Detection
# ─────────────────────────────────────────────────────────────

def detect_lines(binary_img):
    """
    Detect horizontal and vertical lines in the table using morphology.
    """
    h, w = binary_img.shape

    # Horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 60, 1))
    h_lines = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, h_kernel)
    h_lines = cv2.dilate(h_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)), iterations=2)

    # Vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 60))
    v_lines = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, v_kernel)
    v_lines = cv2.dilate(v_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1)), iterations=2)

    return h_lines, v_lines


def get_boundaries(line_img, axis, min_dist=40):
    """Detect peak positions of lines with clustering."""
    projection = np.sum(line_img, axis=axis)
    peak_thresh = np.max(projection) * 0.2

    raw_pos = np.where(projection > peak_thresh)[0]
    if len(raw_pos) == 0:
        return []

    # Cluster consecutive positions
    boundaries = []
    cluster = [raw_pos[0]]
    for i in range(1, len(raw_pos)):
        if raw_pos[i] - raw_pos[i-1] < min_dist:
            cluster.append(raw_pos[i])
        else:
            boundaries.append(int(np.mean(cluster)))
            cluster = [raw_pos[i]]
    boundaries.append(int(np.mean(cluster)))

    return sorted(list(set(boundaries)))


# ─────────────────────────────────────────────────────────────
# Step 2: Extraction Logic
# ─────────────────────────────────────────────────────────────

def fuzzy_match_entity(candidate, known_names, cutoff=0.55):
    """
    Match OCR text against the database as a complete entity.
    Returns (matched_name, score) or (None, 0).
    """
    if not candidate or len(candidate) < 3:
        return None, 0

    # 1. Cleaning
    candidate = candidate.upper().strip()
    # Remove noise prefixes
    candidate = re.sub(r'^(SR|NAME|SEAT|STUDENT|NO|RESULT|EXAM|TOTAL|CREDIT)', '', candidate)
    candidate = re.sub(r'[^A-Z\s]', ' ', candidate)
    candidate = re.sub(r'\s+', ' ', candidate).strip()

    if len(candidate) < 4:
        return None, 0

    # Reject obvious header/noise words
    noise_kws = ["COLLEGE", "ENGINEERING", "UNIVERSITY", "MUMBAI", "SEMESTER",
                  "MARKS", "OBTAINED", "GRADE", "TOTAL", "CREDIT", "RESULT",
                  "POINTER", "PAPER", "SUBJECT", "THEORY", "PRACTICAL",
                  "INTERNAL", "EXTERNAL", "STATUS", "EXAMINATION"]
    for kw in noise_kws:
        if kw in candidate:
            return None, 0

    # Strategy 1: Close match via difflib
    matches = difflib.get_close_matches(candidate, known_names, n=1, cutoff=cutoff)
    if matches:
        score = difflib.SequenceMatcher(None, candidate, matches[0]).ratio()
        return matches[0], score

    # Strategy 2: Containment check for long names
    for kn in known_names:
        if len(candidate) > 10 and candidate in kn:
            return kn, 0.9
        if len(kn) > 10 and kn in candidate:
            return kn, 0.9

    return None, 0


def ocr_upscaled(roi, psm=6):
    """Upscale small ROI for better OCR accuracy with fast linear interpolation."""
    if roi is None or roi.size == 0:
        return ""
    h, w = roi.shape[:2]

    # Moderate upscale if too small (avoid massive 8x blowups that stall Tesseract)
    if h < 55:
        scale = min(2.5, 75.0 / max(h, 1))
        roi = cv2.resize(roi, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)

    if len(roi.shape) == 3:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Truly empty region check
    mean_val = np.mean(roi)
    if mean_val > 252:
        return ""

    text = pytesseract.image_to_string(roi, config=f"--psm {psm}").strip()
    return text


def parse_marks_box(text):
    """
    Robust marks extraction: Find the last valid float or triplet in the GPA range.
    Handles standard floats, gazette (EC ECG GPA) triplets, and integer GPAs.
    """
    text_clean = text.upper().replace(',', '.')

    # 1. Fail Status Detection (strict word boundaries)
    if re.search(r'\bFAIL\b|\bATKT\b|NULL|^F$|[(]F[)]|\sF\s', text_clean):
        return 0.0, "F"

    # 2. Extract Floats: look for patterns like 8.50, 9.1, 10.00
    matches = re.findall(r"(\d{1,2}\.\d{1,2})", text_clean)
    if matches:
        for num in reversed(matches):
            try:
                val = float(num)
                if 4.0 <= val <= 10.0:
                    return val, "P"
            except:
                continue

    # 3. Look for Gazette EC ECG GPA triplet: e.g. "24 168 7" or "24 204 8.5"
    triplet = re.findall(r"\b(2[0-8])\s+(\d{2,3})\b(?:\s+(\d{1,2}(?:\.\d{1,2})?))?", text_clean)
    if triplet:
        for ec, ecg, gpa_str in reversed(triplet):
            try:
                if gpa_str:
                    g_val = float(gpa_str)
                    if 4.0 <= g_val <= 10.0:
                        return round(g_val, 2), "P"
                calc = float(ecg) / float(ec)
                if 4.0 <= calc <= 10.0:
                    return round(calc, 2), "P"
            except:
                continue

    return 0.0, "P"


def find_name_and_result_columns(x_bounds, img_width):
    """
    Adaptively find the name column and result area boundaries.
    Handles variable left-margin layouts where some pages have an extra
    leading column (e.g., page border detected as a vertical line).

    Returns: (name_x0, name_x1, result_x0)
    """
    if len(x_bounds) < 3:
        # Fallback to percentage-based
        return int(img_width * 0.05), int(img_width * 0.20), int(img_width * 0.65)

    # The Student Name column is ALWAYS in the left portion of the page (starts before 0.18*w and ends before 0.35*w)
    max_name_end = int(img_width * 0.35)
    min_col_width = max(80, int(img_width * 0.045))
    valid_candidates = []

    for idx in range(len(x_bounds) - 1):
        x0 = x_bounds[idx]
        x1 = x_bounds[idx + 1]
        gap = x1 - x0
        if x0 < int(img_width * 0.18) and x1 <= max_name_end and gap >= min_col_width:
            valid_candidates.append((gap, x0, x1, idx))

    if valid_candidates:
        valid_candidates.sort(reverse=True, key=lambda c: c[0])
        best_gap, name_x0, name_x1, best_idx = valid_candidates[0]
        sr_x0 = x_bounds[best_idx - 1] if best_idx > 0 else 0
    else:
        name_x0 = int(img_width * 0.045)
        name_x1 = int(img_width * 0.22)
        sr_x0 = 0

    # Result area: rightmost ~35% of the table
    result_x0 = int(img_width * 0.65)

    return name_x0, name_x1, result_x0, sr_x0


# ─────────────────────────────────────────────────────────────
# Step 3: Main Pipeline
# ─────────────────────────────────────────────────────────────

def process_marksheet_iter(pdf_path):
    """
    Iterator version of marksheet processing. Yields results per page.
    """
    print(f"[Pipeline] Starting on {pdf_path}")
    try:
        pages = convert_from_path(pdf_path, dpi=200)
    except Exception as e:
        print(f"[Error] PDF conversion failed: {e}")
        return

    seen_names = set()

    for page_num, pil_img in enumerate(pages):
        print(f"\n[Page {page_num+1}/{len(pages)}]")
        page_results = []

        # ── 1. Image Preprocessing ──
        img = np.array(pil_img)[:, :, ::-1].copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Adaptive binary for line detection (inverted)
        binary_inv = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 10
        )

        # Deskew
        coords = np.column_stack(np.where(binary_inv > 0))
        if len(coords) > 100:
            angle = cv2.minAreaRect(coords)[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if abs(angle) > 0.1:
                h_orig, w_orig = gray.shape
                M = cv2.getRotationMatrix2D((w_orig // 2, h_orig // 2), angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w_orig, h_orig),
                                      flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                img = cv2.warpAffine(img, M, (w_orig, h_orig),
                                     flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                binary_inv = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV, 21, 10
                )

        # ── 2. Grid Detection ──
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        h_lines, v_lines = detect_lines(edges)

        y_bounds = get_boundaries(h_lines, axis=1, min_dist=25)
        x_bounds = get_boundaries(v_lines, axis=0, min_dist=40)

        # Fallback
        if len(x_bounds) < 3 or len(y_bounds) < 10:
            h_lines_fb, v_lines_fb = detect_lines(binary_inv)
            y_bounds_fb = get_boundaries(h_lines_fb, axis=1, min_dist=25)
            x_bounds_fb = get_boundaries(v_lines_fb, axis=0, min_dist=40)
            if len(y_bounds_fb) > len(y_bounds):
                y_bounds = y_bounds_fb
            if len(x_bounds_fb) > len(x_bounds):
                x_bounds = x_bounds_fb

        if len(x_bounds) < 2 or len(y_bounds) < 5:
            yield {"page": page_num + 1, "students": []}
            continue

        # ── 3. Adaptive Column Detection ──
        name_x0, name_x1, result_x0, sr_x0 = find_name_and_result_columns(x_bounds, img.shape[1])

        # ── 4. Row-by-Row Student + Result Extraction ──
        row_ocr_cache = {}
        for r_idx in range(len(y_bounds) - 1):
            cell = gray[y_bounds[r_idx]:y_bounds[r_idx+1], name_x0:name_x1]
            txt = ocr_upscaled(cell, psm=6)
            row_ocr_cache[r_idx] = txt

        i = 0
        while i < len(y_bounds) - 1:
            matched_name = None

            for off in range(0, 5):
                idx = i + off
                if idx + 1 >= len(y_bounds):
                    break
                t1 = row_ocr_cache.get(idx, "")
                m, s = fuzzy_match_entity(t1, KNOWN_NAMES)

                # Check merged 2-row window for split names (e.g. Student 1)
                if not m and idx + 2 < len(y_bounds):
                    cell2 = gray[y_bounds[idx]:y_bounds[idx+2], name_x0:name_x1]
                    t2 = ocr_upscaled(cell2, psm=6)
                    m2, s2 = fuzzy_match_entity(t2, KNOWN_NAMES)
                    if m2:
                        m = m2
                        # If row idx+1 alone matches, then idx was just noise; start at idx+1
                        m_next_single, _ = fuzzy_match_entity(row_ocr_cache.get(idx+1, ""), KNOWN_NAMES)
                        if m_next_single == m:
                            idx = idx + 1

                if m and m not in seen_names:
                    matched_name = m
                    i = idx
                    break

            if not matched_name:
                i += 1
                continue

            # Find next student boundary starting from i + 1
            block_end_i = min(i + 15, len(y_bounds) - 1)
            for k in range(i + 1, block_end_i):
                if k + 1 >= len(y_bounds):
                    break
                t_chk = row_ocr_cache.get(k, "")
                m_next, _ = fuzzy_match_entity(t_chk, KNOWN_NAMES)
                if m_next and m_next != matched_name:
                    block_end_i = k
                    break

                # Check 2-row merged window for next student
                if k + 2 < len(y_bounds):
                    cell2 = gray[y_bounds[k]:y_bounds[k+2], name_x0:name_x1]
                    t2 = ocr_upscaled(cell2, psm=6)
                    m_next2, _ = fuzzy_match_entity(t2, KNOWN_NAMES)
                    if m_next2 and m_next2 != matched_name:
                        # If row k+1 alone matches m_next2, boundary is k+1
                        m_k1, _ = fuzzy_match_entity(row_ocr_cache.get(k+1, ""), KNOWN_NAMES)
                        if m_k1 == m_next2:
                            block_end_i = k + 1
                        else:
                            block_end_i = k
                        break

            # Result extraction for this student's block [i : block_end_i]
            best_gpa = 0.0
            best_status = "P"
            block_roi = gray[y_bounds[i]:y_bounds[block_end_i], result_x0:img.shape[1]-10]

            for pval in [11, 6]:
                txt = ocr_upscaled(block_roi, psm=pval)
                g, s = parse_marks_box(txt)
                if s == "F":
                    best_gpa, best_status = 0.0, "F"
                    break
                if g > 0:
                    best_gpa, best_status = g, s
                    break

            # Fallback to last 2 rows in block if needed (GPA/result is strictly at the bottom)
            if best_gpa == 0.0 and best_status == "P":
                check_start = max(i, block_end_i - 2)
                for k_sub in range(check_start, block_end_i):
                    if k_sub + 1 >= len(y_bounds):
                        break
                    row_roi = gray[y_bounds[k_sub]:y_bounds[k_sub+1], result_x0:img.shape[1]-10]
                    row_text = ocr_upscaled(row_roi, psm=6)
                    g, s = parse_marks_box(row_text)
                    if s == "F":
                        best_gpa, best_status = 0.0, "F"
                        break
                    if g > 0:
                        best_gpa, best_status = g, s
                        break

            # If no passing GPA was found, student is Fail / ATKT
            if best_gpa == 0.0:
                best_status = "F"

            page_results.append({"name": matched_name, "gpa": best_gpa, "status": best_status})
            seen_names.add(matched_name)
            i = block_end_i

        yield {"page": page_num + 1, "total_pages": len(pages), "students": page_results}

def process_marksheet(pdf_path):
    all_results = []
    for chunk in process_marksheet_iter(pdf_path):
        for s in chunk["students"]:
            all_results.append((s["name"], s["gpa"], s["status"]))
    return all_results


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "SEM-III COMP DEC-2023 Part 1.pdf"
    output_filename = "students_general.xlsx"

    students = process_marksheet(pdf_path)

    if students:
        df = pd.DataFrame(students, columns=["Name", "GPA", "Status"])
        df.to_excel(output_filename, index=False)

        passed = sum(1 for _, g, s in students if s == "P" and g > 0)
        failed = sum(1 for _, _, s in students if s == "F")
        no_gpa = sum(1 for _, g, s in students if s == "P" and g == 0)

        print(f"\n{'='*60}")
        print(f"  Exported {len(students)} students to {output_filename}")
        print(f"  Pass (with GPA): {passed} | Fail: {failed} | Pass (no GPA): {no_gpa}")
        print(f"{'='*60}")
        for s in students:
            print(s)
    else:
        print("\nNo students were matched.")
