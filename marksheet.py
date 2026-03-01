from pdf2image import convert_from_path
import pytesseract
import re
import pandas as pd

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PDF_PATH = "New_Input.pdf"

def ocr_with_bottom_boost(img):
    w, h = img.size
    main_text = pytesseract.image_to_string(img, config="--psm 6")
    bottom_text = pytesseract.image_to_string(img.crop((0, int(h*0.75), w, h)), config="--psm 6")
    return main_text + "\n" + bottom_text

# OCR all pages
pages = convert_from_path(PDF_PATH, dpi=300)
full_text = ""
for img in pages:
    full_text += ocr_with_bottom_boost(img)

def parse_students_smart(text):
    records = []

    # Look for names in all caps followed by Marks
    name_pattern = re.compile(r"([A-Z]{3,}(?: [A-Z]{2,})+)\s*Marks")
    matches = list(name_pattern.finditer(text))

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        try:
            name = m.group(1).strip()

            # Status: look for the word "Obtained" or "Grade" line and pick P/F nearby
            status_match = re.search(r"(?:Obtained|Grade)[^\n]*\b([PF])\b", block)
            status = status_match.group(1) if status_match else "P"

            # GPA: last float in block (after "Credit Pt" if possible)
            credit_match = re.findall(r"Credit Pt.*?(\d+\.\d{1,2})", block, re.S)
            if credit_match:
                raw_gpa = credit_match[-1]
            else:
                # fallback: any float
                float_matches = re.findall(r"\d+\.\d{1,2}", block)
                raw_gpa = float_matches[-1] if float_matches else "0.0"

            # Fix OCR error: 0.xx → 7.xx
            if str(raw_gpa).startswith("0."):
                gpa = float("7" + str(raw_gpa)[1:])
            else:
                gpa = float(raw_gpa)

            # F → GPA = 0
            if status == "F":
                gpa = 0.0

            records.append((name, gpa, status))

        except:
            continue

    return records


students_fixed = parse_students_smart(full_text)

def export_to_excel(records, filename="students.xlsx"):
    # Convert list of tuples to DataFrame
    df = pd.DataFrame(records, columns=["Name", "GPA", "Status"])
    # Export to Excel
    df.to_excel(filename, index=False)
    print(f"Data exported to {filename}")
export_to_excel(students_fixed)
# --- Main ---
print("========== RAW OCR OUTPUT ==========")
print(full_text[:3000])
print("\n=========== END PREVIEW ===========\n")

print("========== PARSED STUDENTS FIXED ==========")
for s in students_fixed:
    print(s)
