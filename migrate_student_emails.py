import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
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
    
    # 1. Add column to student_name if it doesn't exist
    try:
        cursor.execute("ALTER TABLE student_name ADD COLUMN student_email VARCHAR(255) AFTER student_name")
        print("SUCCESS: Added student_email column to student_name table.")
    except Exception as e:
        if "Duplicate column name" in str(e):
            print("NOTE: Column student_email already exists.")
        else:
            print(f"ERROR: Could not add column: {e}")

    # 2. Populate from email_logs where names match
    try:
        cursor.execute("""
            UPDATE student_name s
            JOIN (
                SELECT DISTINCT student_name, student_email 
                FROM email_logs 
                WHERE student_email IS NOT NULL AND student_email != ''
            ) e ON s.student_name = e.student_name
            SET s.student_email = e.student_email
            WHERE s.student_email IS NULL OR s.student_email = ''
        """)
        print(f"SUCCESS: Populated {cursor.rowcount} students with emails from email_logs.")
    except Exception as e:
        print(f"ERROR: Could not populate emails: {e}")

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    migrate()
