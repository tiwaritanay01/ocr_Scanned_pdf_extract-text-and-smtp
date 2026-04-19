import mysql.connector

conn = mysql.connector.connect(host='127.0.0.1', user='root', password='root123', database='student_results')
c = conn.cursor()

# Delete the wrong sem3 backfill data
c.execute("DELETE FROM student_performance WHERE semester = 'sem3'")
print(f"Deleted {c.rowcount} old sem3 records")

# Correct sem3 data from Dept Admin OCR extraction (all 11 students)
sem3_data = [
    ("ALLU SANTOSH CHINTAMANI KAMALINI", 7.36),
    ("AMBRE SANKET VILAS KALPANA", 9.13),
    ("ARALI SINDHU SURESH BHUVANESHWAR", 7.22),
    ("ARDEKAR OMKAR PRAKASH POOJA", 9.61),
    ("ARMORIKAR ISHAN DINESH JYOTI", 0),
    ("BAMANE SAIRAJ CHANDRAKANT SHOBHA", 7.09),
    ("BANE JANHAVI CHANDRASHEKHAR", 8.39),
    ("BANSODE SHREYAS ARUN SWATI", 8.52),
    ("BELNEKAR PRACHI PRABHAKAR POOJA", 9.09),
    ("BHALEKAR ATHARVA DHANAJ", 0),
    ("BHALEKAR ATHARVA DHANAJI SNEHA", 0),
]

for name, gpa in sem3_data:
    c.execute("""
        INSERT INTO student_performance (ern, student_name, pointer, semester, department)
        VALUES (%s, %s, %s, 'sem3', 'Computer Engineering')
    """, (name, name, gpa))
    print(f"  Inserted: {name} -> GPA {gpa} (sem3)")

conn.commit()

# Verify
c.execute("SELECT semester, COUNT(*) FROM student_performance GROUP BY semester ORDER BY semester")
print(f"\nFinal counts:")
for sem, cnt in c.fetchall():
    print(f"  {sem}: {cnt} students")

c.close()
conn.close()
print("\nDone!")
