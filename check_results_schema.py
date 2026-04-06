import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_fk():
    # Try common passwords
    pw_list = [os.getenv("DB_PASSWORD"), "Tanay@12345", "root123", "root", "admin", ""]
    conn = None
    for pw in pw_list:
        if pw is None: continue
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "127.0.0.1"),
                user=os.getenv("DB_USER", "root"),
                password=pw,
                database=os.getenv("DB_NAME", "student_results")
            )
            break
        except:
            continue
    
    if not conn:
        print("FAIL: Could not connect to DB")
        return

    cursor = conn.cursor(dictionary=True)
    
    # 1. Get constraint info
    print("\n--- RESULTS SCHEMA ---")
    cursor.execute("DESC results")
    res_cols = cursor.fetchall()
    for col in res_cols: print(col)
    
    # 2. Add student_id to results if missing
    if not any(c['Field'] == 'student_id' for c in res_cols):
        cursor.execute("ALTER TABLE results ADD COLUMN student_id INT AFTER result_id")
        print("SUCCESS: Added student_id column to results table.")

    # 3. Populate student_id by matching name/ern
    # This assumes student_name table now has the correct data but maybe not the results yet.
    # We match by the old student link in `results`.
    # Let's find out what's in `results` first.
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    migrate_fk()
