"""
Accuracy test runner for the full OCR + fuzzy matching pipeline.
Uploads SEM-III COMP DEC-2023 Part 1.pdf to the backend and compares
results against the GT names in the student_name MySQL table.
"""
import requests
import mysql.connector
import difflib

PDF_PATH = "SEM-III COMP DEC-2023 Part 1.pdf"
API_URL = "http://127.0.0.1:8000/upload-marksheet"

# --- Step 1: Load ground truth names ---
conn = mysql.connector.connect(host='127.0.0.1', user='root', password='root123', database='student_results')
cursor = conn.cursor()
cursor.execute('SELECT student_name FROM student_name')
gt_names = [row[0] for row in cursor.fetchall()]
cursor.close()
conn.close()
print(f"Ground Truth: {len(gt_names)} students in DB")

# --- Step 2: Upload PDF to backend API ---
print(f"\nUploading {PDF_PATH} to backend...")
with open(PDF_PATH, "rb") as f:
    resp = requests.post(
        API_URL,
        files={"file": (PDF_PATH, f, "application/pdf")},
        data={"user_name": "accuracy_test", "semester": "sem3"}
    )

if resp.status_code != 200:
    print(f"ERROR: API returned {resp.status_code}: {resp.text}")
    exit(1)

data = resp.json()
students = data.get("students", [])
undetected = data.get("undetected", [])

print(f"OCR Detected : {len(students)} students")

# --- Step 3: Fuzzy Match extracted names against GT ---
extracted_names = [s["name"] for s in students]

matched = []
unmatched_gt = []

for gt in sorted(gt_names):
    # Check exact or fuzzy match
    close = difflib.get_close_matches(gt, extracted_names, n=1, cutoff=0.75)
    if close:
        matched.append((gt, close[0]))
    else:
        unmatched_gt.append(gt)

total_gt = len(gt_names)
accuracy = len(matched) / total_gt * 100

print(f"\n{'='*60}")
print(f"  ACCURACY REPORT")
print(f"{'='*60}")
print(f"  Ground Truth Students : {total_gt}")
print(f"  OCR Detected          : {len(students)}")
print(f"  Fuzzy Matched         : {len(matched)}")
print(f"  Unmatched (missed)    : {len(unmatched_gt)}")
print(f"  Accuracy              : {accuracy:.1f}%")
print(f"{'='*60}")

print(f"\n✅ MATCHED ({len(matched)}):")
for gt, found in matched:
    flag = "  " if gt == found else "~"  # ~ means fuzzy corrected
    print(f"  {flag} {gt}  →  {found}")

print(f"\n❌ MISSED ({len(unmatched_gt)}) - Need Manual Entry:")
for name in unmatched_gt:
    print(f"  - {name}")

print(f"\n📋 OCR Extracted but Not in GT ({len([n for n in extracted_names if not difflib.get_close_matches(n, gt_names, n=1, cutoff=0.75)])}):")
for name in extracted_names:
    if not difflib.get_close_matches(name, gt_names, n=1, cutoff=0.75):
        print(f"  + {name}")
