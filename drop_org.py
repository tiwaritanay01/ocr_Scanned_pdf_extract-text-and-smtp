import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def drop_org_tables():
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
    
    # Correct order for foreign key constraints
    tables = ["department", "college", "university"]
    for t in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS `{t}`")
            print(f"SUCCESS: Dropped table '{t}'.")
        except Exception as e:
            print(f"ERROR dropping '{t}': {e}")

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    drop_org_tables()
