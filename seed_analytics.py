import mysql.connector
import os
import random
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

def seed():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Names to use
    names = [
        "Tanay Tiwari", "Rahul Sharma", "Sneha Patil", "Amit Verma", 
        "Priya Singh", "Aniket Deshmukh", "Siddharth Kulkarni", "Neha Gupta",
        "Vikram Rathore", "Pooja Hegde", "Rohan Joshi", "Aditi Rao",
        "Yash Vardhan", "Kriti Sanon", "Varun Dhawan", "Shraddha Kapoor"
    ]
    
    semesters = ["sem3", "sem4"]
    
    print("Seeding student_performance table...")
    
    for name in names:
        for sem in semesters:
            ern = f"MU{random.randint(1000000, 9999999)}"
            pointer = round(random.uniform(6.0, 9.8), 2)
            
            cursor.execute("""
            INSERT INTO student_performance (ern, student_name, pointer, semester, department)
            VALUES (%s, %s, %s, %s, 'Computer Engineering')
            ON DUPLICATE KEY UPDATE pointer = VALUES(pointer)
            """, (ern, name, pointer, sem))
            
    conn.commit()
    cursor.close()
    conn.close()
    print("Successfully seeded student_performance with sample data.")

if __name__ == "__main__":
    seed()
