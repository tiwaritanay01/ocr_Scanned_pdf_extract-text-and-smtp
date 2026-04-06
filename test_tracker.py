import mysql.connector
import os
from dotenv import load_dotenv

# Replicate the track_file_upload logic for direct testing
def get_db_conn():
    load_dotenv()
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
    return None

def test_track_file_upload(file_name, admin_name, format_type, college_name=None):
    try:
        conn = get_db_conn()
        if not conn:
            print("ERROR: Connection failed")
            return
        cursor = conn.cursor()
        
        # If college_name wasn't provided, try to find it for this admin
        if not college_name:
            try:
                cursor.execute("SELECT college FROM admins WHERE name = %s", (admin_name,))
                row = cursor.fetchone()
                if row: college_name = row[0]
            except Exception as ex:
                print(f"Warn admin select: {ex}")
                pass
        
        if not college_name:
            college_name = "Vasantdada Patil Pratishthan's College of Engineering"

        print(f"Attempting to insert: {file_name}, {admin_name}, {format_type}, {college_name}")
        cursor.execute("""
            INSERT INTO result_files (file_name, admin_name, format_type, college_name, status) 
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (file_name, admin_name, format_type, college_name))
        
        f_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"SUCCESS: Logged upload ID: {f_id}")
        return f_id
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    test_track_file_upload("test_script_run.pdf", "System Admin", "PDF")
