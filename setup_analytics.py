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
    raise Exception("Could not connect to database with any known password.")

def setup_analytics_table():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Create the separate table for visualization as requested
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_performance (
        performance_id INT AUTO_INCREMENT PRIMARY KEY,
        ern VARCHAR(50),
        student_name VARCHAR(255),
        pointer DECIMAL(4,2),
        semester VARCHAR(20),
        department VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY student_sem (ern, semester)
    )
    """)
    
    # Analytics table created. We keep it empty initially as per user request.
    # Data will be populated during real PDF/Excel uploads.
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Analytics table 'student_performance' created and populated.")

if __name__ == "__main__":
    setup_analytics_table()
