from pdf2image import convert_from_path
import pytesseract
import pandas as pd
import re

# Set Tesseract path (Windows only)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PDF_PATH = "result.pdf"

def extract_students(pdf_path):
    images = convert_from_path(pdf_path, dpi=300)
    students = []

    for img in images:
        text = pytesseract.image_to_string(img)
        lines = text.split("\n")

        for line in lines:
            # Match pattern: SeatNo Name ... (ERN)
            # Example: 1402458 ANUSHKA AVINASH PANDIT ... (MU03411205202846)
            match = re.search(r'(\d{7})\s+([A-Z\s]+).*?\((MU.*?)\)', line)

            if match:
                seat_no = match.group(1)
                name = match.group(2).strip()
                ern = match.group(3)

                students.append({
                    "Seat No": seat_no,
                    "Name": name,
                    "ERN": ern
                })

    return students


# Extract data
students = extract_students(PDF_PATH)

# Convert to table
df = pd.DataFrame(students)

# Save to Excel
output_file = "Student_ERN_List.xlsx"
df.to_excel(output_file, index=False)

print(f"Extracted {len(df)} students")
print(f"Saved to {output_file}")