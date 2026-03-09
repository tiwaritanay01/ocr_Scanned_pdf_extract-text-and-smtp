import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
import re
import pandas as pd
import os
import difflib

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image(img):
    """
    Apply OpenCV preprocessing:
    1. Grayscale
    2. Optional Deskewing
    3. Crop central table area (removing black borders/triangles)
    4. Adaptive Binarization
    """
    # Convert PIL Image to OpenCV format (numpy array)
    open_cv_image = np.array(img) 
    # Convert RGB to BGR 
    open_cv_image = open_cv_image[:, :, ::-1].copy() 

    # 1. Grayscale
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

    # 2. Deskewing (Find angle of main text block and rotate)
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Rotate the image to deskew
    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # 3. Cropping 
    # Threshold to find the main white page (ignoring dark scanning borders)
    _, thresh = cv2.threshold(deskewed, 240, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # Find largest contour which should be the white page
        c = max(contours, key=cv2.contourArea)
        x, y, w_c, h_c = cv2.boundingRect(c)
        cropped = deskewed[y:y+h_c, x:x+w_c]
    else:
        cropped = deskewed

    # 4. Light Binarization (Otsu's thresholding)
    # Avoid Gaussian Blur which can destroy thin text
    _, binary = cv2.threshold(cropped, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Optional morphological operations to reconnect broken text lines slightly
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.erode(binary, kernel, iterations=1)

    return binary

def extract_tier_1(text):
    """
    Tier 1 parsing: Strict block slicing using Marks keyword.
    (This is identical to the reliable marksheet.py logic)
    """
    records = []
    # Look for names in all caps. Allow intermediate characters (like `|` or stray numbers) before Marks
    name_pattern = re.compile(r"(?:^\d+\s*\|\s*)?([A-Z]{3,}(?: [A-Z]{2,})+)[^A-Za-z0-9]*?Marks", re.MULTILINE)
    matches = list(name_pattern.finditer(text))

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        try:
            name = m.group(1).strip()

            status_match = re.search(r"(?:Obtained|Grade)[^\n]*\b([PF])\b", block)
            status = status_match.group(1) if status_match else "P"

            credit_line_match = re.search(r"Credit Pt[^\n]+", block, re.IGNORECASE)
            raw_gpa = None
            if credit_line_match:
                numbers = re.findall(r"\d+(?:\.\d+)?", credit_line_match.group(0))
                if numbers:
                    last_num = float(numbers[-1])
                    if last_num > 10 and "." not in numbers[-1]:  
                        raw_gpa = str(last_num / 100 if last_num >= 100 else last_num / 10)
                    else:
                        raw_gpa = str(last_num)
            
            if not raw_gpa:
                float_matches = re.findall(r"\d+\.\d{1,2}", block)
                raw_gpa = float_matches[-1] if float_matches else "0.0"

            if str(raw_gpa).startswith("0.") and float(raw_gpa) < 1.0:
                gpa = float("7" + str(raw_gpa)[1:])
            else:
                gpa = float(raw_gpa)

            if status == "F":
                gpa = 0.0

            records.append((name, gpa, status))

        except Exception as e:
            continue

    return records

def extract_tier_2(binary_img, text_psm6):
    """
    Tier 2 parsing: Fallback heuristic scanner for very noisy OCR.
    Runs a secondary Sparse Text OCR (PSM 11) to find names that PSM 6 failed to see.
    It then searches the primary text block for their corresponding GPA.
    """
    records = []
    
    # Run Sparse OCR explicitly to find missing names fragmented by noisy tables
    text_psm11 = pytesseract.image_to_string(binary_img, config="--psm 11")
    lines_psm11 = text_psm11.split('\n')
    lines_psm6 = text_psm6.split('\n')
    
    # Look for names in the sparse output
    potential_names = []
    for line in lines_psm11:
        name_match = re.search(r'(?:^\d+\s*\|\s*)?([A-Z]{3,}(?: [A-Z]{2,})+(?: [A-Z]{2,})*)', line)
        if name_match:
            candidate = name_match.group(1).strip()
            # Disallow generic headers
            invalid_kws = ["COLLEGE", "ENGINEERING", "UNIVERSITY", "MUMBAI", "SEMESTER", "NAME", "STUDENT", "MARKS", "TOT", "GPA", "ECG", "BEEN"]
            if not any(kw in candidate for kw in invalid_kws) and " " in candidate:
                if not re.search(r'([A-Z])\1{2,}', candidate): # no repeated garble
                    potential_names.append(candidate)
                    
    # Now that we have names, try to find their GPA in the dense PSM 6 block
    last_found_idx = 0
    final_results = []
    seen_normalized_names = set()

    for name in potential_names:
        # Standardize name for duplicate checking
        name_norm = "".join(name.split())
        is_duplicate = False
        for seen in seen_normalized_names:
            if difflib.SequenceMatcher(None, name_norm, seen).ratio() > 0.8:
                is_duplicate = True
                break
        if is_duplicate:
            continue
        seen_normalized_names.add(name_norm)

        gpa = 0.0
        status = "P"
        
        # Fuzzy find the name in the PSM 6 text to get a starting index
        start_idx = last_found_idx
        name_parts = name.split()
        search_key = " ".join(name_parts[:2]) # use first two words for better fuzzy matching
        
        matches = difflib.get_close_matches(search_key, lines_psm6[last_found_idx:last_found_idx+50], n=1, cutoff=0.5)
        if matches:
            for idx, line in enumerate(lines_psm6):
                if matches[0] in line and idx >= last_found_idx:
                    start_idx = idx
                    last_found_idx = idx
                    break
                
        # Scan next 35 lines in PSM 6 for the GPA footprint due to large tables
        scan_limit = min(start_idx + 35, len(lines_psm6))
        for j in range(start_idx, scan_limit):
            scan_line = lines_psm6[j]
            
            if "Fail" in scan_line or " F " in scan_line or "|F|" in scan_line:
                status = "F"
            
            # Sem 4 Specific: Total Credits 24 -> "24 [Score] [GPA]"
            # Could be "24 222 9.25" or "24 222 925"
            numbers = re.findall(r"\d+(?:\.\d+)?", scan_line)
            if len(numbers) >= 3 and numbers[-3] == "24":
                last_num_str = numbers[-1]
                last_num = float(last_num_str)
                if last_num > 10 and "." not in last_num_str:
                    gpa = last_num / 100 if last_num >= 100 else last_num / 10
                else:
                    gpa = last_num
                break
            
            # Generic float fallback
            fallback_match = re.findall(r'\d+\.\d{1,2}', scan_line)
            if fallback_match:
                gpa = float(fallback_match[-1])
        
        if status == "F":
            gpa = 0.0
            
        final_results.append((name, gpa, status))
        
    return final_results

def score_name(name, original_block):
    """
    Score a candidate name block. High score = likely real student name.
    """
    # Clean name
    name = re.sub(r'^[0-9\/\s|:-]+', '', name) # Strip leading seat no artifacts
    name = re.sub(r'\s+', ' ', name).strip()
    parts = name.split()
    
    # Base score: number of words (students usually have 3+)
    score = len(parts) * 20
    
    # Penalize suspicious noise words
    noise_kws = ["COLLEGE", "ENGINEERING", "UNIVERSITY", "MUMBAI", "SEMESTER", "TOT", "GPA", "ECG", "TW", "IA", "MAX", "MIN", "OBTAINED", "RESULT", "BEER", "FEE", "ECTED"]
    if any(kw in name.upper() for kw in noise_kws):
        score -= 200
        
    # Favor long words (names are usually 4+ chars)
    for p in parts:
        if len(p) <= 2:
            score -= 30
        elif len(p) >= 4:
            score += 15 # increased bonus
    
    # Penalize heavy repetition 
    if re.search(r'([A-Z])\1{2,}', name):
        score -= 100
        
    # Bonus for being near "Marks" or "Obtained" 
    if "Marks" in original_block[:100] or "Obtained" in original_block[:100]:
        score += 60
        
    return score

def extract_students_proximity(text):
    """
    Finds all names and all GPA footprints, then pairs them based on proximity.
    """
    # 1. Find all candidate Name positions
    # Allow dots and slashes initially to capture messy names
    name_pattern = re.compile(r"(?:^\d+\s*\|\s*)?([A-Z0-9.\/]{3,}(?:\s+[A-Z0-9.\/]{1,})+)", re.MULTILINE)
    candidates = []
    for m in name_pattern.finditer(text):
        name = m.group(1).strip()
        pos = m.start()
        
        # Look at the block around it for scoring context
        context = text[max(0, pos-10):pos+150]
        score = score_name(name, context)
        
        if score > 20: 
            # Clean name for final storage
            clean_name = re.sub(r'^[0-9\/\s|:-]+', '', name)
            clean_name = re.sub(r'\s+', ' ', clean_name).strip()
            # Remove noise words from the cleaned name
            noise_words = ["BEER", "FEE", "ECTED", "TOT", "ECG", "GPA"]
            clean_name = " ".join([w for w in clean_name.split() if w.upper() not in noise_words])
            
            if len(clean_name.split()) >= 2:
                candidates.append({"name": clean_name, "pos": pos, "score": score})

    # 2. Find all GPA footprint positions
    gpa_lines = []
    gpa_pattern = re.compile(r"\b24\s+\d{2,}\s+(\d+(?:\.\d+)?)\b", re.MULTILINE)
    for m in gpa_pattern.finditer(text):
        raw_val_str = m.group(1)
        raw_val = float(raw_val_str)
        if raw_val > 10 and "." not in raw_val_str:
            gpa = raw_val / 100 if raw_val >= 100 else raw_val / 10
        else:
            gpa = raw_val
        gpa_lines.append({"gpa": gpa, "pos": m.start()})

    # 3. Refine candidates
    all_gpa_pos = sorted([g["pos"] for g in gpa_lines])
    
    records = []
    seen_names = set()
    
    for k in range(len(all_gpa_pos)):
        start_search = all_gpa_pos[k-1] if k > 0 else 0
        end_search = all_gpa_pos[k]
        
        best_student = None
        for c in candidates:
            if start_search < c["pos"] < end_search:
                if not best_student or c["score"] > best_student["score"]:
                    # Stricter duplicate ratio (0.9) to allow BANE vs BANSODE
                    is_dup = any(difflib.SequenceMatcher(None, c["name"], existing).ratio() > 0.9 for existing in seen_names)
                    if not is_dup:
                        best_student = c
        
        if best_student:
            gpa_val = gpa_lines[k]["gpa"]
            status = "P" if gpa_val > 0 else "F"
            records.append((best_student["name"], gpa_val, status))
            seen_names.add(best_student["name"])

    # 4. Fallback for Failed Students
    # Sort survivors by score
    survivors = sorted([c for c in candidates if not any(difflib.SequenceMatcher(None, c["name"], x).ratio() > 0.9 for x in seen_names)], key=lambda x: x['score'], reverse=True)
    
    for c in survivors:
        block = text[c["pos"]:c["pos"]+600]
        if any(marker in block for marker in [" F ", "|F|", "04F", " Fail"]):
            records.append((c["name"], 0.0, "F"))
            seen_names.add(c["name"])
            
    return records

def process_marksheet(pdf_path):
    print("Converting PDF to images...")
    pages = convert_from_path(pdf_path, dpi=300)
    
    all_records = []
    
    for page_num, img in enumerate(pages):
        print(f"Processing Page {page_num + 1}...")
        
        # OpenCV Preprocessing
        binary_img = preprocess_image(img)
        cv2.imwrite(f"debug_page_{page_num+1}.png", binary_img)
        
        # OCR 1: PSM 6 (Dense)
        print("Running Tesseract PSM 6...")
        text_psm6 = pytesseract.image_to_string(binary_img, config="--psm 6")
        
        # OCR 2: PSM 11 (Sparse)
        print("Running Tesseract PSM 11...")
        text_psm11 = pytesseract.image_to_string(binary_img, config="--psm 11")
        
        # Combine texts for maximal discovery
        combined_text = text_psm6 + "\n" + text_psm11
        
        # Save combined OCR for debugging
        with open(f"debug_ocr_combined_page_{page_num+1}.txt", "w", encoding='utf-8') as f:
            f.write(combined_text)
        
        print("Extracting via Proximity Logic...")
        records = extract_students_proximity(combined_text)
        print(f"Found {len(records)} students.")
        all_records.extend(records)
            
    return all_records

if __name__ == "__main__":
    PDF_PATH = "New_Input._sem4.pdf"
    output_filename = "students_sem4.xlsx"
    
    print(f"Starting execution on {PDF_PATH}")
    students = process_marksheet(PDF_PATH)
    
    if students:
        df = pd.DataFrame(students, columns=["Name", "GPA", "Status"])
        df.to_excel(output_filename, index=False)
        print(f"\nSuccessfully exported {len(students)} records to {output_filename}")
        
        print("\n=========== EXTRACTED STUDENTS ===========")
        for s in students:
            print(s)
    else:
        print("\nFailed to extract any student records.")
