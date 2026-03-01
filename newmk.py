from pdf2image import convert_from_path
import pytesseract
import re

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

# ---------------- DYNAMIC PARSER (first 1-2 students) ----------------
def parse_first_students(text, max_students=2):
    text = re.sub(r'\n+', ' ', text)
    tokens = text.split()
    records = []
    i = 0
    last_index = 0

    while i < len(tokens) and len(records) < max_students:
        token = tokens[i]
        if re.fullmatch(r'[A-Z]{3,}', token):
            name_tokens = [token]
            j = i + 1
            while j < len(tokens) and re.fullmatch(r'[A-Z]{2,}', tokens[j]) and len(name_tokens) < 5:
                name_tokens.append(tokens[j])
                j += 1

            if len(name_tokens) < 3:  # still keep them to avoid missing
                i += 1
                continue

            name = " ".join(name_tokens)
            i = j

            # F first, then P
            status = None
            while i < len(tokens):
                if tokens[i] == "F":
                    status = "F"
                    gpa = 0.0
                    i += 1
                    break
                elif tokens[i] == "P":
                    status = "P"
                    i += 1
                    gpa = 0.0
                    while i < len(tokens):
                        float_match = re.match(r'\d+\.\d{1,2}', tokens[i])
                        if float_match:
                            gpa = float(float_match.group())
                            break
                        i += 1
                    break
                i += 1

            if status is None:
                status = "P"
                gpa = 0.0

            records.append((name, gpa, status))
            last_index = i
        else:
            i += 1

    return records, last_index

# ---------------- ORIGINAL BULK PARSER ----------------
def parse_students_bulk(text):
    records = []
    name_pattern = re.compile(r"([A-Z]{3,}(?: [A-Z]{2,}){2,4})\s*Marks[\)\s]*")
    matches = list(name_pattern.finditer(text))

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        try:
            name = m.group(1).strip()
            # F first, then P
            status_match_f = re.search(r"(?:Obtained|Grade)[^\n]*\b(F)\b", block)
            status_match_p = re.search(r"(?:Obtained|Grade)[^\n]*\b(P)\b", block)
            if status_match_f:
                status = "F"
                gpa = 0.0
            elif status_match_p:
                status = "P"
                credit_match = re.findall(r"Credit Pt.*?(\d+\.\d{1,2})", block, re.S)
                if credit_match:
                    raw_gpa = credit_match[-1]
                else:
                    float_matches = re.findall(r'\d+\.\d{1,2}', block)
                    raw_gpa = float_matches[-1] if float_matches else "0.0"
                if str(raw_gpa).startswith("0."):
                    gpa = float("7" + str(raw_gpa)[1:])
                else:
                    gpa = float(raw_gpa)
            else:
                status = "P"
                gpa = 0.0

            records.append((name, gpa, status))
        except:
            continue
    return records

# ---------------- HYBRID MERGE (no cleanup) ----------------
first_students, last_index = parse_first_students(full_text, max_students=2)
remaining_text = " ".join(full_text.split()[last_index:])
bulk_students = parse_students_bulk(remaining_text)
students_fixed = first_students + bulk_students

# ---------------- OUTPUT ----------------
print("========== PARSED STUDENTS ==========")
for s in students_fixed:
    print(s)
