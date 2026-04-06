import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def inspect_admins_detailed():
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
    cursor.execute("SELECT * FROM admins")
    admins = cursor.fetchall()
    for row in admins:
        print(f"ADMIN_ID: {row['admin_id']} | NAME: '{row['name']}' | USERNAME: '{row['username']}' | ROLE: {row['role']}")
        print(f"   ORG: Univ={row.get('university')}, Coll={row.get('college')}, Dept={row.get('department')}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    inspect_admins_detailed()
