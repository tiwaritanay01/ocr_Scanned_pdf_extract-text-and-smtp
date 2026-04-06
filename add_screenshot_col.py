import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def add_col():
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
        print("FAIL")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE fe_be_results ADD COLUMN screenshot LONGTEXT AFTER gpa")
        conn.commit()
        print("SUCCESS: Added screenshot column.")
    except Exception as e:
        print(f"NOTE: {e}")
    
    cursor.close(); conn.close()

if __name__ == "__main__":
    add_col()
