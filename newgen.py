from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import re
import os

# Set tesseract path (Windows only)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PDF_PATH = "result.pdf"
OUTPUT_DIR = "student_png"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def sanitize_filename(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def detect_student_rows(image):
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    rows = []

    for i, text in enumerate(data["text"]):
        if re.search(r'\(MU.*?\)', text):
            y = data["top"][i]

            words = []
            for j in range(max(0, i - 8), min(len(data["text"]), i + 8)):
                words.append(data["text"][j])

            joined = " ".join(words)

            seat_no = "UNKNOWN"
            name = "STUDENT"

            seat_match = re.search(r'\b\d{7}\b', joined)
            if seat_match:
                seat_no = seat_match.group()

            name_match = re.search(r'\d{7}\s+([A-Z\s]+)', joined)
            if name_match:
                name = name_match.group(1).strip()

            rows.append((y, seat_no, name))

    rows.sort(key=lambda x: x[0])
    return rows


def crop_students(image, rows):
    for i in range(len(rows)):
        y, seat_no, name = rows[i]

        # Determine top boundary
        if i == 0:
            top = max(0, y - 250)  # include subject header
        else:
            prev_y = rows[i - 1][0]
            top = int((prev_y + y) / 2)

        # Determine bottom boundary
        if i < len(rows) - 1:
            next_y = rows[i + 1][0]
            bottom = int((y + next_y) / 2)
        else:
            bottom = image.height

        crop_box = (0, top, image.width, bottom)
        crop = image.crop(crop_box)

        safe_name = sanitize_filename(name)
        filename = f"{seat_no}_{safe_name}.png"
        file_path = os.path.join(OUTPUT_DIR, filename)

        crop.save(file_path)
        print(f"Saved: {file_path}")


def main():
    images = convert_from_path(PDF_PATH, dpi=300)

    for img in images:
        rows = detect_student_rows(img)
        crop_students(img, rows)


if __name__ == "__main__":
    main()