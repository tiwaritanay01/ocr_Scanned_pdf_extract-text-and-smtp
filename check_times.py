import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def check_times():
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
    cursor.execute("SELECT upload_time, file_name FROM result_files")
    rows = cursor.fetchall()
    for row in rows:
        print(f"TIME: {row[0]} | NAME: {row[1]}")
    
    cursor.close(); conn.close()

if __name__ == "__main__":
    check_times()
