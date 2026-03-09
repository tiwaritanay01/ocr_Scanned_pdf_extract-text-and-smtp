import pandas as pd
import os
import smtplib
from marksheet import process_marksheet, KNOWN_NAMES

# 1. Create a temporary Excel sheet with expected names present in New_Input2.pdf
temp_db_names = [
    "CHAUBEY RISHABH KUMAR",
    "CHAUDHARI PIYUSH ARVIND",
    "CHANDORKAR NIKHIL VINAYAK",
    "BHAMBID SATYAM JANARDAN",
    "BODKE OMKAR SOMNATH",
    "CHITAPUR SUNIL MANOHAR",
    "DALVI PARTH AJAY",
    "DAMRE NIKHIL RAJESH",
    "DANDGE MANAS RAJENDRA"
]

temp_db_path = "temp_students.xlsx"

df = pd.DataFrame({"Name": temp_db_names})
df.to_excel(temp_db_path, index=False)

print(f"Created temporary database: {temp_db_path} with {len(temp_db_names)} expected students.")

# 2. Re-import or force-reload marksheet to pick up the new temp_students.xlsx
import importlib
import marksheet
importlib.reload(marksheet)

# 3. Run the OCR logic with fuzzy matching
print(f"\nRunning OCR on New_Input2.pdf...")
pdf_path = "New_Input2.pdf"
results = marksheet.process_marksheet(pdf_path)

extracted_names = [record[0] for record in results]

print("\n--- OCR Results ---")
for record in results:
    print(record)

# 4. Compare extracted names against the temporary excel database
print("\n--- Validation ---")
undetected_students = []

for expected in temp_db_names:
    if expected not in extracted_names:
        undetected_students.append(expected)

if undetected_students:
    print(f"FLAG FOR ADMIN: The following {len(undetected_students)} students were NOT detected successfully by OCR and need manual entry:")
    for student in undetected_students:
        print(f" - {student}")
else:
    print("SUCCESS: All students from the temporary database were successfully extracted by OCR.")

# 5. Output successful matches for website DB
print("\n--- Database Ready Extraction (for React App) ---")
for record in results:
    if record[0] in temp_db_names:
        print(f"Insert into DB -> Name: {record[0]}, GPA: {record[1]}, Status: {record[2]}")

# 6. Delete temporary database
if os.path.exists(temp_db_path):
    os.remove(temp_db_path)
    print(f"\nDeleted temporary database: {temp_db_path}")

