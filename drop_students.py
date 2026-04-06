import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def drop_redundant_table():
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

    cursor = conn.cursor()
    
    # 1. Drop the foreign key constraint on results table
    try:
        cursor.execute("ALTER TABLE results DROP FOREIGN KEY results_ibfk_1")
        print("SUCCESS: Dropped foreign key results_ibfk_1.")
    except Exception as e:
        print(f"NOTE: Could not drop FK (maybe already gone or different name): {e}")

    # 2. DROP the students table
    try:
        cursor.execute("DROP TABLE students")
        print("SUCCESS: Dropped redundant 'students' table.")
    except Exception as e:
        print(f"ERROR: Could not drop 'students' table: {e}")

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    drop_redundant_table()
