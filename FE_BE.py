import os
import re
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Configuration
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PDF_PATH = "Bachelor of Engineering( Computer Science and Engineering)_Term_1_reval.pdf"

import mysql.connector

def save_student_to_db(ern, seat, status, gpa, semester="sem1"):
    """Saves or updates extracted student data in the MySQL database using ERN as PK."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password="root123",
            database=os.getenv("DB_NAME", "student_results")
        )
        cursor = conn.cursor()
        query = """
            INSERT INTO fe_be_results (ern, seat_no, status, gpa, semester)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            seat_no = VALUES(seat_no),
            status = VALUES(status),
            gpa = VALUES(gpa),
            semester = VALUES(semester)
        """
        cursor.execute(query, (ern, seat, status, float(gpa) if gpa else 0.0, semester))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] Could not save {ern}: {e}")

def get_student_blocks(image):
    """Detect student markers and return cropped blocks for each student."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    markers = []
    
    # 1. Identify Seat Number Markers (7 digits)
    for i, text in enumerate(data['text']):
        if re.match(r'^\d{7}$', text):
            markers.append({
                'y': data['top'][i],
                'seat': text,
                'left': data['left'][i]
            })
    
    markers.sort(key=lambda x: x['y'])
    
    blocks = []
    for i in range(len(markers)):
        curr = markers[i]
        
        # Determine crop boundaries
        # Use midpoint logic for boundaries
        top_boundary = 0
        if i == 0:
            top_boundary = max(0, curr['y'] - 100)
        else:
            top_boundary = (markers[i-1]['y'] + curr['y']) // 2
            
        bottom_boundary = image.height
        if i < len(markers) - 1:
            bottom_boundary = (curr['y'] + markers[i+1]['y']) // 2
        else:
            # If it's the last student, look up to 600px down
            bottom_boundary = min(image.height, curr['y'] + 600)
            
        crop_box = (0, top_boundary, image.width, bottom_boundary)
        student_crop = image.crop(crop_box)
        blocks.append({
            'image': student_crop,
            'seat': curr['seat']
        })
        
    return blocks

def process_student_block(student_img):
    """Extract ERN, Name, Status, and GPA from a single student crop."""
    # Use image_to_data to get coordinate-aware text
    data = pytesseract.image_to_data(student_img, output_type=pytesseract.Output.DICT)
    full_text = " ".join(data['text']).strip()
    
    # 1. Extract ERN
    ern_match = re.search(r'MU\d{10,20}', " ".join(data['text']))
    ern = ern_match.group() if ern_match else "NOT_FOUND"
    
    # 2. Extract Name (All-caps strings > 5 chars)
    name_parts = re.findall(r'[A-Z]{5,}(?:\s+[A-Z]{3,})*', full_text)
    noise = ["UNIVERSITY", "MUMBAI", "SEMESTER", "EXAMINATION", "PASSED", "FAIL", "FAILED", "SUCCESSFUL"]
    filtered_names = [n for n in name_parts if n not in noise and len(n) > 8]
    name = filtered_names[0] if filtered_names else "UNKNOWN"
    
    # 3. Status and GPA Logic
    # We look for "PASS" or "FAIL"
    status = "UNKNOWN"
    gpa = "0.0000"
    
    pass_idx = -1
    fail_idx = -1
    
    for i, text in enumerate(data['text']):
        t = text.upper().strip()
        if t == "PASS":
            pass_idx = i
            status = "PASS"
        elif "FAIL" in t:
            fail_idx = i
            status = "FAIL"
            gpa = "0.0000" # As requested: if FAILED put 0.00000

    # 4. If PASS, extract GPA from vertically below
    if "PASS" in status and pass_idx != -1:
        pass_top = data['top'][pass_idx]
        pass_left = data['left'][pass_idx]
        pass_height = data['height'][pass_idx]
        
        # Look for the first float vertically below the 'PASS' word
        # We search a wider box: 300px horizontally and 200px vertically down
        candidates = []
        for j in range(len(data['text'])):
            text_j = data['text'][j].strip()
            # Lenient float pattern: 1-2 digits, dot, 2-6 digits
            if re.match(r'^\d{1,2}\.\d{2,6}$', text_j):
                # Is it below the 'PASS' word?
                if data['top'][j] >= (pass_top + pass_height):
                    # Vertical distance should be within ~150px (immediate below)
                    v_dist = data['top'][j] - pass_top
                    if v_dist < 200:
                        # Horizontal distance: usually centered or slightly offset
                        h_dist = abs(data['left'][j] - pass_left)
                        if h_dist < 300:
                            candidates.append({
                                'gpa': text_j,
                                'dist': v_dist
                            })
        
        if candidates:
            candidates.sort(key=lambda x: x['dist'])
            gpa = candidates[0]['gpa']
        else:
            # Broader fallback for this student block
            all_floats = re.findall(r'\d{1,2}\.\d{2,6}', full_text)
            if all_floats:
                gpa = all_floats[-1]

    return {
        "ERN": ern,
        "Name": name,
        "Status": status,
        "GPA": gpa
    }

def process_pdf_to_generator(pdf_path, semester="sem1"):
    """Generator that yields results page by page and saves to DB."""
    images = convert_from_path(pdf_path, dpi=300)
    total_pages = len(images)
    
    for p_idx, page_img in enumerate(images):
        blocks = get_student_blocks(page_img)
        page_results = []
        
        for block in blocks:
            res = process_student_block(block['image'])
            # Save to Database
            save_student_to_db(res['ERN'], block['seat'], res['Status'], res['GPA'], semester)
            
            page_results.append({
                "name": res['Name'],
                "ern": res['ERN'],
                "roll": block['seat'],
                "ocr_result": {
                    "gpa": float(res['GPA']) if res['GPA'] else 0.0,
                    "status": res['Status'],
                    "ern": res['ERN']
                }
            })
            
        yield {
            "page": p_idx + 1,
            "total_pages": total_pages,
            "students": page_results
        }

def main():
    pdf_to_use = PDF_PATH
    if not os.path.exists(pdf_to_use):
        print(f"Error: {pdf_to_use} not found.")
        return

    print(f"--- Processing Marks (Row-wise Crop Engine) ---")
    try:
        gen = process_pdf_to_generator(pdf_to_use)
        total_found = 0
        
        for p_data in gen:
            print(f"Page {p_data['page']} processing...")
            for s in p_data['students']:
                print(f"Found: {s['roll']} | ERN: {s['ern']} | {s['ocr_result']['status']} | GPA: {s['ocr_result']['gpa']} | Name: {s['name']}")
                total_found += 1
                
        print(f"\nTotal extraction complete: {total_found} students processed.")
        
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    main()
