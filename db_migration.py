
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password="root123",
            database=os.getenv("DB_NAME", "student_results")
        )
        cursor = conn.cursor()

        print("[Migration] Creating organizational tables...")
        
        # 1. ADMINS (Section 1.1)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                admin_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                role VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'active'
            )
        """)

        # 2. UNIVERSITY
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS university (
                university_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL UNIQUE,
                location VARCHAR(150) NOT NULL
            )
        """)

        # 2. COLLEGE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS college (
                college_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                university_id INT,
                address VARCHAR(255),
                FOREIGN KEY (university_id) REFERENCES university(university_id)
            )
        """)

        # 3. DEPARTMENT
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS department (
                department_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                college_id INT,
                FOREIGN KEY (college_id) REFERENCES college(college_id)
            )
        """)

        # 4. Update STUDENT (already exists, but let's align schema if needed)
        # We might need to add FKs to department/college later if we want strict mode.
        # For now let's focus on the audit tables.

        # 5. RESULT_FILE (Metadata tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS result_files (
                file_id INT AUTO_INCREMENT PRIMARY KEY,
                file_name VARCHAR(255) NOT NULL,
                upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                format_type VARCHAR(50) DEFAULT 'PDF',
                status VARCHAR(20) DEFAULT 'pending',
                admin_name VARCHAR(100),
                college_name VARCHAR(150)
            )
        """)

        # 6. EMAIL_LOG
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_logs (
                mail_id INT AUTO_INCREMENT PRIMARY KEY,
                student_email VARCHAR(150) NOT NULL,
                student_name VARCHAR(150),
                sent_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'sent',
                subject_semester VARCHAR(50)
            )
        """)

        # 7. ACTIVITY_LOG (Audit Trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                user_name VARCHAR(100),
                action_type VARCHAR(50),
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("[Migration] All missing tables created successfully.")
        
        # Seed initial Admins if empty
        cursor.execute("SELECT COUNT(*) FROM admins")
        if cursor.fetchone()[0] == 0:
            import hashlib
            def hash_p(p): return hashlib.sha256(p.encode()).hexdigest()
            cursor.execute("""
                INSERT INTO admins (username, password, name, email, role) 
                VALUES (%s, %s, %s, %s, %s)
            """, ("dept_admin", hash_p("admin123"), "Department Head", "dept@college.edu", "staff"))
            cursor.execute("""
                INSERT INTO admins (username, password, name, email, role) 
                VALUES (%s, %s, %s, %s, %s)
            """, ("super_admin", hash_p("super123"), "System Admin", "admin@system.com", "superadmin"))
            print("[Migration] Seeded default Admins.")

        # Seed initial University/College if empty
        cursor.execute("SELECT COUNT(*) FROM university")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO university (name, location) VALUES ('University of Mumbai', 'Mumbai')")
            u_id = cursor.lastrowid
            cursor.execute("INSERT INTO college (name, university_id, address) VALUES ('Vasantdada Patil Pratishthan\'s College of Engineering', %s, 'Sion, Mumbai')", (u_id,))
            print("[Migration] Seeded default University and College.")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[Migration] Error: {e}")

if __name__ == "__main__":
    migrate()
