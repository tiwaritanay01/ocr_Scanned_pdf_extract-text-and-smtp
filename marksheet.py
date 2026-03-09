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

# ─────────────────────────────────────────────────────────────
# Step 1: Vision-based Grid Detection
# ─────────────────────────────────────────────────────────────

def detect_lines(binary_img):
    """
    Detect horizontal and vertical lines in the table.
    """
    h, w = binary_img.shape
    
    # Horizontal lines - hyper-sensitive to catch faint boundaries
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 60, 1))
    h_lines = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, h_kernel)
    h_lines = cv2.dilate(h_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)), iterations=2)
    
    # Vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 60))
    v_lines = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, v_kernel)
    v_lines = cv2.dilate(v_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1)), iterations=2)
    
    return h_lines, v_lines

def get_boundaries(line_img, axis, min_dist=40):
    """Detect peak positions of lines with better clustering."""
    projection = np.sum(line_img, axis=axis)
    # Use a dynamic threshold based on local peaks
    peak_thresh = np.max(projection) * 0.2
    
    raw_pos = np.where(projection > peak_thresh)[0]
    if len(raw_pos) == 0:
        return []
    
    # Cluster consecutive positions
    boundaries = []
    if len(raw_pos) > 0:
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
    Match against the database as a complete entity.
    """
    if not candidate or len(candidate) < 3:
        return None, 0
    
    # 1. Cleaning
    candidate = candidate.upper().strip()
    # Remove noise
    candidate = re.sub(r'^(SR|NAME|SEAT|STUDENT|NO)', '', candidate)
    candidate = re.sub(r'[^A-Z\s]', ' ', candidate)
    candidate = re.sub(r'\s+', ' ', candidate).strip()
    
    if len(candidate) < 4: return None, 0

    # Strategy 1: Close match
    matches = difflib.get_close_matches(candidate, known_names, n=1, cutoff=cutoff)
    if matches:
        score = difflib.SequenceMatcher(None, candidate, matches[0]).ratio()
        return matches[0], score
    
    # Strategy 2: Containment (EATHAKOTTI etc) - Require high similarity
    for kn in known_names:
        if len(candidate) > 10 and candidate in kn: 
            return kn, 0.9
        if len(kn) > 10 and kn in candidate:
            return kn, 0.9
            
    return None, 0

def ocr_upscaled(roi, psm=6):
    """Upscale ROI for better OCR results."""
    if roi is None or roi.size == 0: return ""
    h, w = roi.shape[:2]
    
    # Save for extreme debug
    # cv2.imwrite(f"debug_roi_{h}_{w}.png", roi)
    
    if h < 200:
        scale = 200 / h
        roi = cv2.resize(roi, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    
    if len(roi.shape) == 3:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Check if image is mostly white (could be the issue)
    mean_val = np.mean(roi)
    if mean_val > 250:
         return "" # Truly empty
    
    # Return OCR
    text = pytesseract.image_to_string(roi, config=f"--psm {psm}").strip()
    return text

def parse_marks_box(text):
    """
    Restore old logic: find the last float in range.
    """
    # Clean text: dots, commas, noise
    text = text.upper().replace(',', '.')
    
    # 1. Fail Status
    if re.search(r'\bFAIL\b|\bATKT\b|NULL|^F$|[(]F[)]|\sF\s', text):
        return 0.0, "F"
    
    # 2. Extract Floats
    # We look for numbers like 8.50, 9.1, 10.00
    matches = re.findall(r"(\d{1,2}\.\d{1,2})", text)
    if matches:
        # User Tip: Bottom right. Take the last valid one.
        for num in reversed(matches):
            try:
                val = float(num)
                if 4.0 <= val <= 10.0:
                    return val, "P"
            except: continue
            
    return 0.0, "P"

# ─────────────────────────────────────────────────────────────
# Step 3: Pipeline
# ─────────────────────────────────────────────────────────────

def process_marksheet(pdf_path):
    print(f"Starting refinement on {pdf_path}")
    try:
        pages = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"PDF Error: {e}")
        return []

    results = []
    seen_names = set()

    for page_num, pil_img in enumerate(pages):
        print(f"Processing Page {page_num+1}...")
        
        # 1. Image Preprocessing
        img = np.array(pil_img)[:, :, ::-1].copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Binary for line detection (inverted: white lines on black)
        binary_inv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY_INV, 21, 10)
        
        # Deskew logic
        coords = np.column_stack(np.where(binary_inv > 0))
        if len(coords):
            angle = cv2.minAreaRect(coords)[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if abs(angle) > 0.1:
                (h_orig, w_orig) = gray.shape
                M = cv2.getRotationMatrix2D((w_orig // 2, h_orig // 2), angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w_orig, h_orig), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                img = cv2.warpAffine(img, M, (w_orig, h_orig), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                # Re-threshold after deskew
                binary_inv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                  cv2.THRESH_BINARY_INV, 21, 10)

        # 2. Grid Detection
        print(f"  Image Shape: {img.shape}")
        # Use Canny to find edges for better line detection in noisy areas
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        h_lines, v_lines = detect_lines(edges)
        
        y_bounds = get_boundaries(h_lines, axis=1, min_dist=25) 
        x_bounds = get_boundaries(v_lines, axis=0, min_dist=40) 
        
        if len(x_bounds) < 3 or len(y_bounds) < 10:
            print(f"  Warning: Minimal layout detected (x:{len(x_bounds)}, y:{len(y_bounds)}) - Trying fallback")
            # Try once more with adaptive threshold if Canny failed
            h_lines, v_lines = detect_lines(binary_inv)
            y_bounds = get_boundaries(h_lines, axis=1, min_dist=25)
            x_bounds = get_boundaries(v_lines, axis=0, min_dist=40)

        print(f"  x_bounds: {x_bounds}")
        if len(x_bounds) < 2: continue
            
        # Refine ROI Columns
        # Column 0: Sr No | Column 1: Name | ... | Last Column: Result
        # We need Column 1 for Name and Last Column for Marks
        name_x0 = x_bounds[1] if len(x_bounds) > 1 else int(img.shape[1] * 0.05)
        # Find the next bound for Name
        name_x1 = x_bounds[2] if len(x_bounds) > 2 else int(img.shape[1] * 0.40)
        
        # Marks is the very last column
        marks_x0 = x_bounds[-2] if len(x_bounds) > 1 else int(img.shape[1] * 0.85)
        marks_x1 = x_bounds[-1] if len(x_bounds) > 0 else int(img.shape[1] * 0.99)
        
        # Debug
        debug_vis = img.copy()
        for y in y_bounds: cv2.line(debug_vis, (0, y), (img.shape[1], y), (0, 0, 255), 1)
        for x in x_bounds: cv2.line(debug_vis, (x, 0), (x, img.shape[0]), (255, 0, 0), 1)
        cv2.imwrite(f"debug_grid_page_{page_num+1}.jpg", debug_vis)

        # 3. Iterate Sub-Rows
        i = 0
        while i < len(y_bounds) - 1:
            # 1. Match name
            matched_name = None
            for off in range(0, 5):
                idx = i + off
                if idx + 1 >= len(y_bounds): break
                sub_roi = gray[y_bounds[idx]:y_bounds[idx+1], name_x0:name_x1]
                m_n, _ = fuzzy_match_entity(ocr_upscaled(sub_roi, psm=6), KNOWN_NAMES)
                if m_n and m_n not in seen_names:
                    matched_name = m_n
                    i = idx
                    break
            
            if matched_name:
                # 2. Determine block end: next Sr No or next Student Name
                block_end_i = min(i + 15, len(y_bounds) - 1)
                for k in range(i + 3, block_end_i):
                    # Check for student name
                    chk_n_roi = gray[y_bounds[k]:y_bounds[k+1], name_x0:name_x1]
                    chk_n_text = ocr_upscaled(chk_n_roi, psm=6)
                    m_n, _ = fuzzy_match_entity(chk_n_text, KNOWN_NAMES)
                    if m_n and m_n != matched_name:
                        block_end_i = k
                        break
                    # Check for SR No
                    chk_sr_roi = gray[y_bounds[k]:y_bounds[k+1], 0:name_x0]
                    chk_sr_text = ocr_upscaled(chk_sr_roi, psm=6).strip()
                    if re.search(r'^\d+$', chk_sr_text):
                        block_end_i = k
                        break
                
                # 3. Result Scan: Multi-mode resilient search
                best_gpa = 0.0
                best_status = "P"
                
                # Scan area: 65% to edge
                res_x0 = int(img.shape[1] * 0.65)
                
                # Mode A: Composite Block OCR (Resilient to small row misalignments)
                block_roi = gray[y_bounds[i]:y_bounds[block_end_i], res_x0:img.shape[1]-10]
                for pval in [3, 6]:
                    txt = ocr_upscaled(block_roi, psm=pval).upper()
                    g, s = parse_marks_box(txt)
                    if s == "F":
                        best_gpa, best_status = 0.0, "F"
                        break
                    if g > 0:
                        best_gpa, best_status = g, s
                        # Keep looking in block in case there's another float below
                
                # Mode B: Fallback to Row-by-Row top-down (Precision Mode)
                if best_gpa == 0.0 and best_status == "P":
                    for k_sub in range(i, block_end_i):
                        row_roi = gray[y_bounds[k_sub]:y_bounds[k_sub+1], res_x0:img.shape[1]-10]
                        # Try PSM 6 and 11
                        for pval in [6, 11]:
                            row_text = ocr_upscaled(row_roi, psm=pval).upper()
                            g, s = parse_marks_box(row_text)
                            if s == "F":
                                best_gpa, best_status = 0.0, "F"
                                break
                            if g > 0:
                                best_gpa, best_status = g, s
                        if best_status == "F" or best_gpa > 0: break
                
                results.append((matched_name, best_gpa, best_status))
                seen_names.add(matched_name)
                print(f"  Detected: {matched_name} | GPA: {best_gpa} | Status: {best_status}")
                i = block_end_i
            else:
                i += 1

    return results

if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "New_Input._sem4.pdf"
    output_filename = "students_refined.xlsx"
    
    students = process_marksheet(pdf_path)
    
    if students:
        df = pd.DataFrame(students, columns=["Name", "GPA", "Status"])
        df.to_excel(output_filename, index=False)
        print(f"\nDone! Exported {len(students)} students to {output_filename}")
        for s in students:
            print(s)
    else:
        print("No students were matched with the DB.")
