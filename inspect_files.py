import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def inspect_result_files():
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
    
    print("\n--- SCHEMA: result_files ---")
    cursor.execute("DESC result_files")
    for row in cursor.fetchall(): print(row)
    
    print("\n--- CONTENT: result_files ---")
    cursor.execute("SELECT * FROM result_files LIMIT 5")
    for row in cursor.fetchall(): print(row)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    inspect_result_files()
