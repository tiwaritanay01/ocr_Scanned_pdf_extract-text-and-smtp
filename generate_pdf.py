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


def detect_students(image):
    """
    Detect ERN lines and return student crop regions.
    """
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    students = []

    for i, text in enumerate(ocr_data["text"]):
        # Detect ERN pattern
        if re.search(r'\(MU.*?\)', text):
            y = ocr_data["top"][i]

            # Larger crop region to include full subject block
            top = max(0, y - 120)
            bottom = min(image.height, y + 420)

            crop_box = (0, top, image.width, bottom)
            crop = image.crop(crop_box)

            # Extract nearby words to find seat no and name
            words = []
            for j in range(max(0, i - 8), min(len(ocr_data["text"]), i + 8)):
                words.append(ocr_data["text"][j])

            joined = " ".join(words)

            seat_no = "UNKNOWN"
            name = "STUDENT"

            seat_match = re.search(r'\b\d{7}\b', joined)
            if seat_match:
                seat_no = seat_match.group()

            name_match = re.search(r'\d{7}\s+([A-Z\s]+)', joined)
            if name_match:
                name = name_match.group(1).strip()

            students.append((seat_no, name, crop))

    return students


def main():
    images = convert_from_path(PDF_PATH, dpi=300)

    for img in images:
        students = detect_students(img)

        for seat_no, name, crop in students:
            safe_name = sanitize_filename(name)
            filename = f"{seat_no}_{safe_name}.png"
            file_path = os.path.join(OUTPUT_DIR, filename)

            crop.save(file_path)
            print(f"Saved: {file_path}")


if __name__ == "__main__":
    main()