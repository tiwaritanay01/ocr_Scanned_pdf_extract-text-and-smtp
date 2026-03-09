import sys
try:
    import pdfplumber
except ImportError:
    print("pdfplumber not installed")
    sys.exit(0)

import re
import mysql.connector

file_path = "SEM-III COMP DEC-2023 Part 1.pdf"
names = set()

# Process first page to see the structure
with pdfplumber.open(file_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    first_page_text = pdf.pages[0].extract_text()
    if first_page_text:
        lines = first_page_text.split("\n")
        print("First 20 lines of page 1:")
        for line in lines[:20]:
            print(line)
