import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_conn():
    passwords = [os.getenv("DB_PASSWORD"), "root123", "Tanay@12345", "admin", ""]
    for pw in passwords:
        if pw is None: continue 
        try:
            return mysql.connector.connect(
                host=os.getenv("DB_HOST", "127.0.0.1"),
                user=os.getenv("DB_USER", "root"),
                password=pw,
                database=os.getenv("DB_NAME", "student_results")
            )
        except Exception:
            continue
    raise Exception("Could not connect to database.")

def truncate():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE student_performance")
    conn.commit()
    cursor.close()
    conn.close()
    print("Successfully truncated student_performance.")

if __name__ == "__main__":
    truncate()
