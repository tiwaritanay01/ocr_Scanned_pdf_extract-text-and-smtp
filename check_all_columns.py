import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def check_all_columns():
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

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT file_id, file_name, upload_time, admin_name, college_name, status FROM result_files")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    
    cursor.close(); conn.close()

if __name__ == "__main__":
    check_all_columns()
