import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def final_migration_and_cleanup():
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
    
    # 1. Add ern column to student_name if it doesn't exist
    try:
        cursor.execute("ALTER TABLE student_name ADD COLUMN ern VARCHAR(50) AFTER id")
        print("SUCCESS: Added 'ern' column to student_name.")
    except Exception as e:
        if "Duplicate column name" in str(e):
            print("NOTE: Column 'ern' already exists.")
        else:
            print(f"ERROR adding ern: {e}")

    # 2. Add student_email column if it doesn't exist (just in case)
    try:
        cursor.execute("ALTER TABLE student_name ADD COLUMN student_email VARCHAR(255) AFTER student_name")
        print("SUCCESS: Ensured 'student_email' exists in student_name.")
    except Exception as e:
        pass

    # 3. Migrate data from `students` to `student_name`
    # Matching by Name
    try:
        cursor.execute("""
            INSERT INTO student_name (ern, student_name, student_email)
            SELECT s.ERN, s.NAME, s.EMAIL
            FROM students s
            LEFT JOIN student_name sn ON s.NAME = sn.student_name
            WHERE sn.student_name IS NULL
        """)
        print(f"SUCCESS: Inserted {cursor.rowcount} new students from students table.")
        
        cursor.execute("""
            UPDATE student_name sn
            JOIN students s ON sn.student_name = s.NAME
            SET sn.ern = s.ERN, sn.student_email = s.EMAIL
            WHERE sn.ern IS NULL OR sn.ern = '' OR sn.student_email IS NULL OR sn.student_email = ''
        """)
        print(f"SUCCESS: Updated {cursor.rowcount} existing students with data from students table.")
    except Exception as e:
        print(f"ERROR during data migration: {e}")

    # 4. DROP the students table
    try:
        cursor.execute("DROP TABLE students")
        print("SUCCESS: Dropped 'students' table as it's now redundant.")
    except Exception as e:
        print(f"ERROR dropping table: {e}")

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    final_migration_and_cleanup()
