import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def eval_tables():
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
    tables_to_check = ["results", "known_students", "expected_students"]
    
    for t in tables_to_check:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{t}`")
            count = cursor.fetchone()[0]
            print(f"Table {t}: {count} records")
        except Exception as e:
            print(f"Table {t}: Error or Missing - {e}")
            
    cursor.close()
    conn.close()

if __name__ == "__main__":
    eval_tables()
