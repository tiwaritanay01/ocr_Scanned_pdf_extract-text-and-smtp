import cv2
import numpy as np
import pytesseract
import re
from pdf2image import convert_from_path
import csv

# ----------------------------
# TESSERACT PATH
# ----------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PDF_PATH = "New_Input.pdf"
DPI = 400


# ----------------------------
# PREPROCESS
# ----------------------------
def preprocess_image(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    _, thresh = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    return thresh


# ----------------------------
# REMOVE TABLE LINES
# ----------------------------
def remove_table_lines(thresh):

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)

    lines = cv2.add(vertical, horizontal)

    cleaned = cv2.subtract(thresh, lines)

    return cleaned


# ----------------------------
# DYNAMIC COLUMN DETECTION
# ----------------------------
def crop_columns_dynamic(image, thresh):

    projection = np.sum(thresh, axis=0)
    threshold = np.max(projection) * 0.2

    columns = []
    start = None

    for i, val in enumerate(projection):
        if val > threshold and start is None:
            start = i
        elif val <= threshold and start is not None:
            if i - start > 200:
                columns.append((start, i))
            start = None

    columns = sorted(columns, key=lambda x: x[0])

    if len(columns) >= 2:
        left = image[:, columns[0][0]:columns[0][1]]
        right = image[:, columns[-1][0]:columns[-1][1]]
        print("Dynamic columns detected.")
    else:
        print("Fallback column cropping used.")
        h, w = image.shape[:2]
        left = image[:, int(0.05*w):int(0.35*w)]
        right = image[:, int(0.75*w):int(0.95*w)]

    return left, right


# ----------------------------
# STABLE ROW SEGMENTATION
# ----------------------------
def segment_rows(column_img):

    gray = cv2.cvtColor(column_img, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    projection = np.sum(thresh, axis=1)

    threshold = np.mean(projection) * 0.4

    rows = []
    start = None

    for i, val in enumerate(projection):
        if val > threshold and start is None:
            start = i
        elif val <= threshold and start is not None:
            if i - start > 30:
                rows.append((start, i))
            start = None

    print("Rows detected:", len(rows))

    return rows


# ----------------------------
# OCR
# ----------------------------
def ocr_row(row_img, mode):

    if mode == "left":
        config = "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "
    else:
        config = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.PF"

    return pytesseract.image_to_string(row_img, config=config).strip()


# ----------------------------
# CLEAN NUMERIC
# ----------------------------
def clean_numeric(text):

    replacements = {
        'O': '0',
        'I': '1',
        'l': '1',
        'S': '5',
        'B': '8'
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text


# ----------------------------
# MAIN
# ----------------------------
def process_pdf():

    pages = convert_from_path(PDF_PATH, dpi=DPI)
    all_results = []

    for page_index, page in enumerate(pages):

        print(f"\nProcessing Page {page_index+1}")

        image = np.array(page)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        thresh = preprocess_image(image)
        cleaned = remove_table_lines(thresh)

        left_col, right_col = crop_columns_dynamic(image, cleaned)

        rows = segment_rows(left_col)

        if not rows:
            print("No rows found — check thresholds.")
            continue

        for (start, end) in rows:

            start_adj = max(0, start + 5)
            end_adj = end - 5

            left_row = left_col[start_adj:end_adj, :]
            right_row = right_col[start_adj:end_adj, :]

            left_text = ocr_row(left_row, "left")
            right_text = ocr_row(right_row, "right")

            if not left_text and not right_text:
                continue

            right_text = clean_numeric(right_text)

            seat_match = re.search(r"\d{6,8}", left_text)
            seat_number = seat_match.group() if seat_match else ""

            if seat_number:
                left_text = left_text.replace(seat_number, "")

            name = re.sub(r"[^A-Za-z\s]", "", left_text)
            name = re.sub(r"\s+", " ", name).strip()

            if len(name) < 5:
                continue

            pointer_match = re.search(r"\d\.\d{2}", right_text)
            pointer = pointer_match.group() if pointer_match else ""

            status = ""
            if "F" in right_text.upper():
                status = "F"
            elif "P" in right_text.upper():
                status = "P"

            print("NAME:", name)
            print("SEAT:", seat_number)
            print("POINTER:", pointer)
            print("STATUS:", status)
            print("-" * 50)

            all_results.append({
                "page": page_index + 1,
                "name": name,
                "seat_number": seat_number,
                "pointer": pointer,
                "status": status
            })

    return all_results


if __name__ == "__main__":

    results = process_pdf()

    if results:
        with open("extracted_results.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["page", "name", "seat_number", "pointer", "status"]
            )
            writer.writeheader()
            writer.writerows(results)

        print("\nExtraction Completed.")
        print("Saved as extracted_results.csv")
    else:
        print("\nNo data extracted.")