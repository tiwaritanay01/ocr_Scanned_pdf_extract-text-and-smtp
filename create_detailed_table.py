import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def create_detailed_results_table():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password="root123",
            database=os.getenv("DB_NAME", "student_results")
        )
        cursor = conn.cursor()
        
        # Create table for detailed subject-wise marks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detailed_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ern VARCHAR(255),
                student_name VARCHAR(255),
                semester VARCHAR(50),
                subject_marks JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY `unique_student_sem` (`ern`, `student_name`, `semester`)
            )
        """)
        
        conn.commit()
        print("SUCCESS: detailed_results table created or already exists.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    create_detailed_results_table()
