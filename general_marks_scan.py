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

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────────────────────
# DB: Load ground-truth student names (Primary Truth Source)
# ─────────────────────────────────────────────────────────────

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
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password="root123",
            database=os.getenv("DB_NAME", "student_results"),
        )
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
    """Upscale small ROI for better OCR accuracy."""
    if roi is None or roi.size == 0:
        return ""
    h, w = roi.shape[:2]

    # Upscale if too small
    if h < 200:
        scale = 200 / h
        roi = cv2.resize(roi, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    if len(roi.shape) == 3:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Truly empty region check
    mean_val = np.mean(roi)
    if mean_val > 250:
        return ""

    text = pytesseract.image_to_string(roi, config=f"--psm {psm}").strip()
    return text


def parse_marks_box(text):
    """
    Robust marks extraction: Find the last valid float in the GPA range.
    User tip: GPA is at right-bottom of P status.
    """
    # Clean text: normalize commas, dots
    text = text.upper().replace(',', '.')

    # 1. Fail Status Detection (strict word boundaries)
    if re.search(r'\bFAIL\b|\bATKT\b|NULL|^F$|[(]F[)]|\sF\s', text):
        return 0.0, "F"

    # 2. Extract Floats: look for patterns like 8.50, 9.1, 10.00
    matches = re.findall(r"(\d{1,2}\.\d{1,2})", text)
    if matches:
        # Take the last valid float in range (user tip: bottom-right)
        for num in reversed(matches):
            try:
                val = float(num)
                if 4.0 <= val <= 10.0:
                    return val, "P"
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

    # Heuristic: The name column is the WIDEST column in the left half.
    # In most marksheets: Col0=SrNo(narrow), Col1=Name(wide), Col2+=Subjects
    # But some pages have an extra thin left border column.

    # Find the widest gap in the first 5 columns
    best_gap = 0
    best_start_idx = 1  # Default: column 1

    for idx in range(min(len(x_bounds) - 1, 5)):
        gap = x_bounds[idx + 1] - x_bounds[idx]
        if gap > best_gap:
            best_gap = gap
            best_start_idx = idx

    name_x0 = x_bounds[best_start_idx]
    name_x1 = x_bounds[best_start_idx + 1] if best_start_idx + 1 < len(x_bounds) else int(img_width * 0.40)

    # Sr No column is just before the name column
    sr_x0 = x_bounds[best_start_idx - 1] if best_start_idx > 0 else 0

    # Result area: rightmost ~35% of the table
    result_x0 = int(img_width * 0.65)

    return name_x0, name_x1, result_x0, sr_x0


# ─────────────────────────────────────────────────────────────
# Step 3: Main Pipeline
# ─────────────────────────────────────────────────────────────

def process_marksheet(pdf_path):
    """
    Generalized marksheet processing pipeline.
    Works across different page layouts and PDF chunks.
    """
    print(f"[Pipeline] Starting on {pdf_path}")
    try:
        pages = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"[Error] PDF conversion failed: {e}")
        return []

    results = []
    seen_names = set()

    for page_num, pil_img in enumerate(pages):
        print(f"\n[Page {page_num+1}/{len(pages)}]")

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
        # Primary: Canny edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        h_lines, v_lines = detect_lines(edges)

        y_bounds = get_boundaries(h_lines, axis=1, min_dist=25)
        x_bounds = get_boundaries(v_lines, axis=0, min_dist=40)

        # Fallback: Adaptive threshold if Canny yields too few lines
        if len(x_bounds) < 3 or len(y_bounds) < 10:
            print(f"  WARN: Sparse grid (x:{len(x_bounds)}, y:{len(y_bounds)}), trying threshold fallback")
            h_lines_fb, v_lines_fb = detect_lines(binary_inv)
            y_bounds_fb = get_boundaries(h_lines_fb, axis=1, min_dist=25)
            x_bounds_fb = get_boundaries(v_lines_fb, axis=0, min_dist=40)
            if len(y_bounds_fb) > len(y_bounds):
                y_bounds = y_bounds_fb
            if len(x_bounds_fb) > len(x_bounds):
                x_bounds = x_bounds_fb

        if len(x_bounds) < 2 or len(y_bounds) < 5:
            print(f"  [X] Skipping page: insufficient grid structure")
            continue

        # ── 3. Adaptive Column Detection ──
        name_x0, name_x1, result_x0, sr_x0 = find_name_and_result_columns(x_bounds, img.shape[1])
        print(f"  Grid: {len(x_bounds)} cols × {len(y_bounds)} rows | Name: [{name_x0}:{name_x1}] | Result: [{result_x0}:]")

        # Debug visualization
        debug_vis = img.copy()
        for y in y_bounds:
            cv2.line(debug_vis, (0, y), (img.shape[1], y), (0, 0, 255), 1)
        for x in x_bounds:
            cv2.line(debug_vis, (x, 0), (x, img.shape[0]), (255, 0, 0), 1)
        # Mark name column in green, result area in blue
        cv2.line(debug_vis, (name_x0, 0), (name_x0, img.shape[0]), (0, 255, 0), 2)
        cv2.line(debug_vis, (name_x1, 0), (name_x1, img.shape[0]), (0, 255, 0), 2)
        cv2.line(debug_vis, (result_x0, 0), (result_x0, img.shape[0]), (255, 255, 0), 2)
        cv2.imwrite(f"debug_general_grid_p{page_num+1}.jpg", debug_vis)

        # ── 4. Row-by-Row Student + Result Extraction ──
        i = 0
        page_student_count = 0
        while i < len(y_bounds) - 1:
            # ── 4a. Name Detection: Scan ahead up to 5 sub-rows ──
            matched_name = None
            match_row_idx = i

            for off in range(0, 5):
                idx = i + off
                if idx + 1 >= len(y_bounds):
                    break
                sub_roi = gray[y_bounds[idx]:y_bounds[idx+1], name_x0:name_x1]
                ocr_text = ocr_upscaled(sub_roi, psm=6)
                m_n, score = fuzzy_match_entity(ocr_text, KNOWN_NAMES)
                if m_n and m_n not in seen_names:
                    matched_name = m_n
                    match_row_idx = idx
                    i = idx
                    break

            if not matched_name:
                i += 1
                continue

            # ── 4b. Block End Detection ──
            # Find where the next student starts (next name or next Sr No)
            block_end_i = min(i + 15, len(y_bounds) - 1)
            for k in range(i + 3, block_end_i):
                if k + 1 >= len(y_bounds):
                    break
                # Check for next student name
                chk_n_roi = gray[y_bounds[k]:y_bounds[k+1], name_x0:name_x1]
                chk_n_text = ocr_upscaled(chk_n_roi, psm=6)
                m_n, _ = fuzzy_match_entity(chk_n_text, KNOWN_NAMES)
                if m_n and m_n != matched_name:
                    block_end_i = k
                    break
                # Check for sequential number (Sr No)
                chk_sr_roi = gray[y_bounds[k]:y_bounds[k+1], sr_x0:name_x0]
                chk_sr_text = ocr_upscaled(chk_sr_roi, psm=6).strip()
                if re.search(r'^\d{1,3}$', chk_sr_text):
                    block_end_i = k
                    break

            # ── 4c. Result Extraction: Multi-mode scan ──
            best_gpa = 0.0
            best_status = "P"

            # Mode A: Composite Block OCR
            # Scan the entire right portion of the student block at once
            block_roi = gray[y_bounds[i]:y_bounds[block_end_i], result_x0:img.shape[1]-10]
            for pval in [3, 6]:
                txt = ocr_upscaled(block_roi, psm=pval).upper()
                g, s = parse_marks_box(txt)
                if s == "F":
                    best_gpa, best_status = 0.0, "F"
                    break
                if g > 0:
                    best_gpa, best_status = g, s

            # Mode B: Row-by-row fallback (if block OCR missed the GPA)
            if best_gpa == 0.0 and best_status == "P":
                for k_sub in range(i, block_end_i):
                    if k_sub + 1 >= len(y_bounds):
                        break
                    row_roi = gray[y_bounds[k_sub]:y_bounds[k_sub+1], result_x0:img.shape[1]-10]
                    for pval in [6, 11]:
                        row_text = ocr_upscaled(row_roi, psm=pval).upper()
                        g, s = parse_marks_box(row_text)
                        if s == "F":
                            best_gpa, best_status = 0.0, "F"
                            break
                        if g > 0:
                            best_gpa, best_status = g, s
                    if best_status == "F" or best_gpa > 0:
                        break

            # Mode C: Targeted last-column scan (rightmost 2 columns)
            if best_gpa == 0.0 and best_status == "P" and len(x_bounds) > 2:
                last_col_x0 = x_bounds[-2]
                for k_sub in range(block_end_i - 1, i, -1):
                    if k_sub + 1 >= len(y_bounds):
                        continue
                    cell_roi = gray[y_bounds[k_sub]:y_bounds[k_sub+1], last_col_x0:img.shape[1]-10]
                    for pval in [6, 7, 11]:
                        cell_text = ocr_upscaled(cell_roi, psm=pval).upper()
                        g, s = parse_marks_box(cell_text)
                        if s == "F":
                            best_gpa, best_status = 0.0, "F"
                            break
                        if g > 0:
                            best_gpa, best_status = g, s
                            break
                    if best_status == "F" or best_gpa > 0:
                        break

            results.append((matched_name, best_gpa, best_status))
            seen_names.add(matched_name)
            page_student_count += 1
            print(f"  [+] {matched_name} | GPA: {best_gpa} | {best_status}")
            i = block_end_i

        if page_student_count == 0:
            print(f"  [X] No students detected on this page")

    return results


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
