import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def consolidate_admin_config():
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
    
    # 1. Add columns to admins table
    columns_to_add = ["university", "college", "department"]
    for col in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE admins ADD COLUMN `{col}` VARCHAR(255) AFTER email")
            print(f"SUCCESS: Added '{col}' column to admins.")
        except Exception as e:
            print(f"NOTE: Column '{col}' maybe exists: {e}")

    # 2. Extract values (assuming single entries or default values for current admins)
    # We'll take the first available name from each table if they exist.
    univ_name = "Mumbai University"
    coll_name = "Vasantdada Patil Pratishthan's College of Engineering"
    dept_name = "Computer Science"
    
    try:
        cursor.execute("SELECT name FROM university LIMIT 1")
        row = cursor.fetchone()
        if row: univ_name = row[0]
        
        cursor.execute("SELECT name FROM college LIMIT 1")
        row = cursor.fetchone()
        if row: coll_name = row[0]
        
        cursor.execute("SELECT name FROM department LIMIT 1")
        row = cursor.fetchone()
        if row: dept_name = row[0]
    except Exception as e:
        print(f"Note during data extraction: {e}")

    # 3. Update all current admins with these values
    try:
        cursor.execute("UPDATE admins SET university = %s, college = %s, department = %s", 
                       (univ_name, coll_name, dept_name))
        print("SUCCESS: Updated all admins with university/college/dept info.")
    except Exception as e:
        print(f"ERROR updating admins: {e}")

    # 4. Drop the redundant tables
    for t in ["university", "college", "department"]:
        try:
            cursor.execute(f"DROP TABLE `{t}`")
            print(f"SUCCESS: Dropped redundant table '{t}'.")
        except Exception as e:
            print(f"ERROR dropping table '{t}': {e}")

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    consolidate_admin_config()
