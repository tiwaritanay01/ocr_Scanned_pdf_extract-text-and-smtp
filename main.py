
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import uuid
import datetime
import json
import mysql.connector
import hashlib
import base64
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
import importlib

from urllib.parse import urlparse
import pytesseract

# Load environment variables
load_dotenv()

# Ensure Poppler is in PATH (Cross-platform)
POPPLER_DIRS = [
    os.getenv("POPPLER_PATH"),
    r"C:\Program Files\poppler-25.12.0\Library\bin",
    r"C:\Program Files\poppler\Library\bin",
    r"C:\poppler\Library\bin",
    r"C:\poppler\bin",
]
for p in POPPLER_DIRS:
    if p and os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

# Configure Tesseract path (Windows fallback / Linux native)
tesseract_bin = os.getenv("TESSERACT_CMD")
if tesseract_bin and os.path.exists(tesseract_bin):
    pytesseract.pytesseract.tesseract_cmd = tesseract_bin
elif os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = FastAPI(title="Online Result Processing & Distribution System")

# Enable CORS for frontend
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Health check endpoints for cloud monitoring ---
@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"status": "ok", "service": "Automated Result Processing API"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}

# --- 1. Security & Authentication ---

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# Persistent User Credentials (fallback)
admins_dict = {
    "dept_admin": {"password": hash_password("admin123"), "role": "staff", "name": "Department Head"},
    "super_admin": {"password": hash_password("super123"), "role": "superadmin", "name": "System Admin"}
}

# --- 2. Database & Logging Helpers ---

def get_db_conn():
    """Robust DB connection supporting cloud URLs, custom ports, and SSL."""
    db_url = os.getenv("DATABASE_URL")
    if db_url and (db_url.startswith("mysql://") or db_url.startswith("mysql+mysqlconnector://")):
        # Strip scheme for urlparse if needed
        clean_url = db_url.replace("mysql+mysqlconnector://", "mysql://")
        parsed = urlparse(clean_url)
        return mysql.connector.connect(
            host=parsed.hostname,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/"),
            port=parsed.port or 3306
        )

    host = os.getenv("DB_HOST", "127.0.0.1")
    user = os.getenv("DB_USER", "root")
    dbname = os.getenv("DB_NAME", "student_results")
    port = int(os.getenv("DB_PORT", "3306"))
    primary_pw = os.getenv("DB_PASSWORD")

    # Try configured password first, then common local fallbacks
    passwords = [primary_pw, "root123", "Tanay@12345", "admin", ""]
    last_err = None
    for pw in passwords:
        if pw is None:
            continue
        try:
            conn_args = {
                "host": host,
                "user": user,
                "password": pw,
                "database": dbname,
                "port": port
            }
            ssl_ca = os.getenv("DB_SSL_CA")
            if ssl_ca and os.path.exists(ssl_ca):
                conn_args["ssl_ca"] = ssl_ca
            return mysql.connector.connect(**conn_args)
        except Exception as e:
            last_err = e
            continue

    if last_err:
        raise last_err
    raise Exception("Could not connect to MySQL database")

def init_db_tables():
    """Ensure all required tables and default users exist on startup."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                admin_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                department VARCHAR(255) NULL,
                college VARCHAR(255) NULL,
                university VARCHAR(255) NULL,
                role VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'active'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                user_name VARCHAR(100),
                action_type VARCHAR(50),
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_name (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ern VARCHAR(50),
                student_name VARCHAR(255) UNIQUE,
                student_email VARCHAR(255)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detailed_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ern VARCHAR(255),
                student_name VARCHAR(255),
                semester VARCHAR(50),
                subject_marks JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_student_sem (ern, student_name, semester)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fe_be_results (
                ern VARCHAR(255) NOT NULL PRIMARY KEY,
                seat_no VARCHAR(50),
                status VARCHAR(10),
                gpa FLOAT,
                screenshot LONGTEXT,
                semester VARCHAR(20)
            )
        """)

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

        # Seed initial admins if empty
        cursor.execute("SELECT COUNT(*) FROM admins")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO admins (username, password, name, email, department, college, university, role)
                VALUES 
                ('dept_admin', %s, 'Department Head', 'dept@college.edu', 'Computer Engineering', 'Vasantdada Patil Pratishthan College of Engineering', 'University of Mumbai', 'staff'),
                ('super_admin', %s, 'System Admin', 'admin@system.com', 'Administration', 'Vasantdada Patil Pratishthan College of Engineering', 'University of Mumbai', 'superadmin')
            """, (hash_password("admin123"), hash_password("super123")))
            print("[Init DB] Seeded default admin credentials.")

        conn.commit()
        cursor.close()
        conn.close()
        print("[Init DB] Database schema verified.")
    except Exception as e:
        print(f"[Init DB Warning] Auto-init skipped or failed: {e}")

@app.on_event("startup")
def on_app_startup():
    init_db_tables()

def add_db_log(user_name, action, details):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO activity_logs (user_name, action_type, details) VALUES (%s, %s, %s)", 
                       (user_name, action, details))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[Logging Error] {e}")

def track_file_upload(file_name, admin_name, format_type, college_name=None):
    print(f"\n[!] FILE TRACKER STARTING: {file_name} by {admin_name}")
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # Resolve organizational context
        if not college_name:
            try:
                cursor.execute("SELECT college FROM admins WHERE name = %s", (admin_name,))
                row = cursor.fetchone()
                if row: college_name = row[0]
            except Exception as e:
                print(f"    [Tracker Warning] Org lookup error: {e}")
        
        if not college_name:
            college_name = "Vasantdada Patil Pratishthan's College of Engineering"

        # 1. Log into result_files
        cursor.execute("""
            INSERT INTO result_files (file_name, admin_name, format_type, college_name, status) 
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (file_name, admin_name, format_type, college_name))
        
        f_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        # 2. Log into activity_logs
        add_db_log(admin_name, "Upload", f"Uploaded file: {file_name} ({format_type})")
        
        print(f"[*] FILE TRACKER SUCCESS: Recorded upload ID {f_id} for {admin_name}\n")
        return f_id
    except Exception as e:
        print(f"[!] FILE TRACKER CRITICAL ERROR: {e}\n")
        return None

class ApprovalRequest(BaseModel):
    file_id: int
    admin_name: str

@app.post("/approve-file")
async def approve_file(req: ApprovalRequest):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE result_files SET status = 'Approved' WHERE file_id = %s", (req.file_id,))
        conn.commit()
        cursor.close()
        conn.close()
        add_db_log(req.admin_name, "Finalization", f"Approved Result File ID: {req.file_id}")
        return {"success": True, "message": "File status updated to Approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def log_email_sent(email, name, semester, status="sent"):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO email_logs (student_email, student_name, subject_semester, status) 
            VALUES (%s, %s, %s, %s)
        """, (email, name, semester, status))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[Email Logging Error] {e}")

def get_db_student_members():
    students = []
    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, student_name, student_email FROM student_name")
        students = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception as e:
        print(f"[DB] Error fetching full student details: {e}")
    return students

def get_db_student_names():
    names = []
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT student_name FROM student_name")
        names = [row[0] for row in cursor.fetchall()]
        cursor.close(); conn.close()
    except Exception as e:
        print(f"[DB] Warning: Could not fetch student names: {e}")
    return names

# --- 3. Authentication Endpoints ---

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
async def login(request: LoginRequest):
    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        # Simple Query by email OR username
        cursor.execute("SELECT * FROM admins WHERE email = %s OR username = %s", (request.email, request.email))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user["password"] == hash_password(request.password):
            # Normalize role for frontend expectation
            frontend_role = user["role"]
            if frontend_role == "superadmin":
                frontend_role = "super-admin"
            elif frontend_role == "staff":
                frontend_role = "dept-admin"

            add_db_log(user["name"], "Login", f"Successfully logged into {frontend_role} dashboard")
            return {
                "success": True,
                "user": {
                    "role": frontend_role,
                    "name": user["name"],
                    "email": user["email"],
                    "university": user.get("university", ""),
                    "college": user.get("college", ""),
                    "department": user.get("department", "")
                }
            }
        
        # Log failed attempt
        add_db_log(request.email or "Unknown", "Failed Login", "Invalid credentials attempted")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        print(f"[Login Error] {e}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Database error during login: {str(e)}")

@app.get("/logs")
async def get_activity_logs():
    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                log_id as id,
                timestamp as time, 
                user_name as user, 
                action_type as action, 
                details,
                'Success' as status 
            FROM activity_logs 
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
        logs = cursor.fetchall()
        for log in logs:
            if isinstance(log['time'], datetime.datetime):
                log['time'] = log['time'].strftime("%Y-%m-%d %H:%M:%S")
        cursor.close()
        conn.close()
        return {"logs": logs}
    except Exception as e:
        return {"logs": [], "error": str(e)}

# --- 4. Email Distribution System (Gap 3) ---

class StudentResult(BaseModel):
    name: str
    email: str
    pointer: float
    avg: float
    screenshot: Optional[str] = None
    subject_marks: Optional[dict] = None

class MailResultsRequest(BaseModel):
    students: List[StudentResult]
    user_name: str
    file_id: Optional[int] = None
    semester: str = "sem1"

DUMMY_EMAILS = ["tiwaritanay01@gmail.com", "anonymousthegreat750@gmail.com", "vu1f2425005@pvppcoe.ac.in"]

def send_result_email(to_email, student_name, pointer, avg, screenshot=None, subject_marks=None):
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_email or not smtp_password: return False
    
    msg = MIMEMultipart("related")
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg["Subject"] = f"Exam Result - {student_name}"
    
    html_body = f"""
    <html>
      <body style="font-family: sans-serif; color: #333;">
        <h2 style="color: #2563eb;">Hello {student_name},</h2>
        <p>Your results have been processed with the following details:</p>
        <div style="background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; display: inline-block; margin-bottom: 20px;">
          <strong>GPA:</strong> {pointer}<br/>
          <strong>Average:</strong> {avg}
        </div>
    """

    if subject_marks:
        html_body += """
        <div style="margin-top: 10px; margin-bottom: 20px;">
            <p style="font-weight: bold;">Subject-wise Breakdown:</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 400px; border: 1px solid #e2e8f0;">
                <thead style="background: #f1f5f9;">
                    <tr>
                        <th style="padding: 10px; text-align: left; border: 1px solid #e2e8f0;">Subject Code</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #e2e8f0;">Marks</th>
                    </tr>
                </thead>
                <tbody>
        """
        for code, mark in subject_marks.items():
            html_body += f"""
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e2e8f0;">{code}</td>
                        <td style="padding: 10px; border: 1px solid #e2e8f0;">{mark}</td>
                    </tr>
            """
        html_body += """
                </tbody>
            </table>
        </div>
        """

    if screenshot:
        html_body += f"""
        <div style="margin-top: 20px;">
            <p style="font-weight: bold;">Result Snippet Verification:</p>
            <img src="cid:marks_section" style="max-width: 100%; border: 1px solid #cbd5e1; border-radius: 8px;" alt="Result Screenshot"/>
        </div>
        """

    html_body += f"""
        <p style="margin-top: 30px; font-size: 0.8em; color: #64748b;">Regards,<br/>Exam Cell</p>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, "html"))

    if screenshot:
        try:
            if "," in screenshot: screenshot = screenshot.split(",")[1]
            img_data = base64.b64decode(screenshot)
            img = MIMEImage(img_data)
            img.add_header('Content-ID', '<marks_section>')
            msg.attach(img)
        except Exception as e:
            print(f"Attachment Error: {e}")

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

@app.post("/send-results")
async def send_results(req: MailResultsRequest):
    success_count = 0
    fail_count = 0
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    for i, student in enumerate(req.students):
        # Use real email if available, else fallback to dummy for testing
        target_email = student.email if "@" in student.email and "pending" not in student.email else DUMMY_EMAILS[i % len(DUMMY_EMAILS)]
        
        success = send_result_email(
            target_email, 
            student.name, 
            student.pointer, 
            student.avg, 
            student.screenshot,
            student.subject_marks
        )
        
        status = "sent" if success else "failed"
        log_email_sent(target_email, student.name, req.semester, status)
        
        if success: 
            success_count += 1
            # AUTO-SYNC TO ANALYTICS ON SUCCESSFUL MAIL
            # We assume ERN might be roll or we can use name if ERN is missing
            ern_to_use = student.name # Defaulting to name for matching if ERN is not in StudentResult
            # Actually, let's look for ERN if we can. 
            # (In a real system, StudentResult should have ERN. Let's assume student.name is unique for now or update StudentResult)
            
            try:
                cursor.execute("""
                    INSERT INTO student_performance (ern, student_name, pointer, semester, department)
                    VALUES (%s, %s, %s, %s, 'Computer Engineering')
                    ON DUPLICATE KEY UPDATE 
                        student_name = VALUES(student_name),
                        pointer = VALUES(pointer)
                """, (student.name, student.name, student.pointer, req.semester))
            except Exception as e:
                print(f"[Analytics Sync Error] {e}")
        else: 
            fail_count += 1
            
    # Update File Status to 'Distributed'
    if req.file_id:
        cursor.execute("UPDATE result_files SET status = 'Distributed' WHERE file_id = %s", (req.file_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    add_db_log(req.user_name, "Email Blast", f"Distributed: {success_count} success, {fail_count} failed. File ID: {req.file_id}")
    return {"message": "Email processing complete", "success_count": success_count, "fail_count": fail_count}

# --- 5. OCR & Result Processing ---

@app.post("/upload-fe-be")
async def upload_fe_be(file: UploadFile = File(...), user_name: str = "Anonymous", semester: str = "sem1"):
    if not file.filename.endswith(".pdf"): raise HTTPException(status_code=400, detail="Only PDF allowed")
    f_id = track_file_upload(file.filename, user_name, "PDF")
    add_db_log(user_name, f"{semester.upper()} Upload", f"Processing {file.filename}")
    file_id = str(uuid.uuid4())
    temp_file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(temp_file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    from FE_BE import process_pdf_to_generator
    all_students = []
    try:
        for result_page in process_pdf_to_generator(temp_file_path, semester=semester):
            for s in result_page["students"]: all_students.append(s)
    finally:
        if os.path.exists(temp_file_path): os.remove(temp_file_path)
    return {"success": True, "count": len(all_students), "students": all_students, "semester": semester, "file_id": f_id}

@app.get("/fe-be-results")
def get_fe_be_results(semester: str = None):
    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        if semester:
            cursor.execute("SELECT ern, seat_no, status, gpa, screenshot, semester FROM fe_be_results WHERE semester = %s", (semester,))
        else:
            cursor.execute("SELECT ern, seat_no, status, gpa, screenshot, semester FROM fe_be_results")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"success": True, "results": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}

@app.post("/upload-marksheet-stream")
async def upload_marksheet_stream(file: UploadFile = File(...), user_name: str = "Anonymous", semester: str = "sem3", expected_names: str = Form(None)):
    if not file.filename.endswith(".pdf"): raise HTTPException(status_code=400, detail="Only PDF allowed")
    f_id = track_file_upload(file.filename, user_name, "PDF")
    add_db_log(user_name, "PDF Upload", f"Processing {file.filename} for {semester}")
    file_id = str(uuid.uuid4())
    temp_file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(temp_file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    
    name_list = get_db_student_names()
    if expected_names:
        extra = json.loads(expected_names)
        name_list = list(set(name_list + extra))
    
    if name_list:
        import pandas as pd
        pd.DataFrame({"Name": name_list}).to_excel("temp_students.xlsx", index=False)
        import general_marks_scan
        importlib.reload(general_marks_scan)

    from general_marks_scan import process_marksheet_iter
    def generate_results():
        try:
            for page_data in process_marksheet_iter(temp_file_path):
                formatted = [{"name": s["name"], "ocr_result": {"gpa": s["gpa"], "status": s["status"]}} for s in page_data["students"]]
                yield json.dumps({"page": page_data["page"], "total_pages": page_data["total_pages"], "students": formatted, "target_semester": semester, "file_id": f_id}) + "\n"
        finally:
            if os.path.exists(temp_file_path): os.remove(temp_file_path)
            if os.path.exists("temp_students.xlsx"): os.remove("temp_students.xlsx")

    return StreamingResponse(generate_results(), media_type="application/x-ndjson")

@app.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...), user_name: str = "Anonymous", semester: str = "sem1"):
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files allowed")
    
    f_id = track_file_upload(file.filename, user_name, "Excel")
    add_db_log(user_name, "Excel Upload", f"Processing {file.filename} for {semester}")
    
    try:
        import pandas as pd
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Standardize column names for matching
        original_cols = list(df.columns)
        upper_cols = [str(c).strip().upper() for c in original_cols]
        df.columns = upper_cols
        
        # REQUIRED Keywords: Name, GPA, Status
        name_col = next((c for i, c in enumerate(upper_cols) if "NAME" in c), None)
        gpa_col = next((c for i, c in enumerate(upper_cols) if any(x in c for x in ["GPA", "POINTER", "SGPI", "RESULT", "TOTAL", "AVERAGE"])), None)
        status_col = next((c for i, c in enumerate(upper_cols) if any(x in c for x in ["STATUS", "RESULT_STATUS", "OUTCOME"])), None)
        # If no status col found, but we find GPA, we can infer it
        ern_col = next((c for i, c in enumerate(upper_cols) if any(x in c for x in ["ERN", "SEAT", "ROLL", "ID", "PRN", "SR_NO"])), None)
        
        if not name_col:
            raise HTTPException(status_code=400, detail="Could not find NAME column. Available columns: " + ", ".join(original_cols))
        
        results = []
        conn = get_db_conn()
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            s_name = str(row[name_col])
            s_gpa = float(row[gpa_col]) if gpa_col and not pd.isna(row[gpa_col]) else 0.0
            
            # Infer status if not explicit
            if status_col and not pd.isna(row[status_col]):
                s_status = str(row[status_col]).upper()
            else:
                s_status = "PASS" if s_gpa >= 4.0 else "FAIL" # Default fallback logic
                
            s_ern = str(row[ern_col]) if ern_col and not pd.isna(row[ern_col]) else "N/A"
            
            # Sub-marks: All other columns that aren't the primary ones
            subject_marks = {}
            reserved = [name_col, gpa_col, status_col, ern_col]
            for col in upper_cols:
                if col not in reserved:
                    val = row[col]
                    if not pd.isna(val):
                        # Use the original column name for subject display
                        orig_idx = upper_cols.index(col)
                        orig_name = original_cols[orig_idx]
                        subject_marks[orig_name] = str(val)
            
            # Save detailed results to DB
            cursor.execute("""
                INSERT INTO detailed_results (ern, student_name, semester, subject_marks)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                subject_marks = VALUES(subject_marks)
            """, (s_ern, s_name, semester, json.dumps(subject_marks)))
            
            # Sync to main summary table
            # fe_be_results is for dashboard summary
            cursor.execute("""
                INSERT INTO fe_be_results (ern, seat_no, status, gpa, semester)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                status = VALUES(status),
                gpa = VALUES(gpa)
            """, (s_ern, s_ern, s_status, s_gpa, semester))
            
            results.append({
                "name": s_name,
                "ern": s_ern,
                "roll": s_ern,
                "ocr_result": {
                    "gpa": s_gpa,
                    "status": s_status,
                    "subjectMarks": subject_marks
                }
            })
            
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"success": True, "count": len(results), "students": results, "semester": semester, "file_id": f_id}
        
    except Exception as e:
        print(f"Excel Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/db/tables")
async def list_db_tables():
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        cursor.close(); conn.close()
        return {"success": True, "tables": tables}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/db/table/{table_name}")
async def get_table_data(table_name: str):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{table_name}`")
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        # Get detailed schema for primary key detection
        cursor.execute(f"DESCRIBE `{table_name}`")
        schema = cursor.fetchall()
        cursor.close(); conn.close()
        return {"success": True, "data": rows, "schema": schema}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

class DBUpdateRequest(BaseModel):
    table: str; pk_field: str; pk_value: Any; data: dict

@app.post("/db/update-row")
async def update_db_row(req: DBUpdateRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        # Filter out the PK from the update data to avoid constraint issues
        update_items = {k: v for k, v in req.data.items() if k != req.pk_field}
        if not update_items: return {"success": True, "message": "No changes needed"}
        
        set_clause = ", ".join([f"`{k}` = %s" for k in update_items.keys()])
        values = list(update_items.values()) + [req.pk_value]
        
        query = f"UPDATE `{req.table}` SET {set_clause} WHERE `{req.pk_field}` = %s"
        cursor.execute(query, tuple(values))
        conn.commit(); cursor.close(); conn.close()
        add_db_log("System Admin", "DB Update", f"Updated row in {req.table} (PK: {req.pk_value})")
        return {"success": True}
    except Exception as e: 
        print(f"[DB Update Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

class DBAddRowRequest(BaseModel):
    table: str; data: dict

@app.post("/db/add-row")
async def add_db_row(req: DBAddRowRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        # Filter out nulls (especially for auto-increment PKs)
        clean_data = {k: v for k, v in req.data.items() if v is not None}
        fields = ", ".join([f"`{k}`" for k in clean_data.keys()]); 
        placeholders = ", ".join(["%s"] * len(clean_data))
        
        cursor.execute(f"INSERT INTO `{req.table}` ({fields}) VALUES ({placeholders})", tuple(clean_data.values()))
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

class DBColumnRequest(BaseModel):
    table: str; column_name: str; column_type: str = "VARCHAR(255)"; old_name: str = None

@app.post("/db/add-column")
async def add_db_column(req: DBColumnRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        cursor.execute(f"ALTER TABLE `{req.table}` ADD COLUMN `{req.column_name}` {req.column_type}")
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/db/rename-column")
async def rename_db_column(req: DBColumnRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        cursor.execute(f"ALTER TABLE `{req.table}` RENAME COLUMN `{req.old_name}` TO `{req.column_name}`")
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/db/delete-row")
async def delete_db_row(req: DBUpdateRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        cursor.execute(f"DELETE FROM `{req.table}` WHERE `{req.pk_field}` = %s", (req.pk_value,))
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/semesters")
async def get_available_semesters():
    """Return list of semesters that have data in student_performance."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT semester FROM student_performance ORDER BY semester")
        semesters = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"success": True, "semesters": semesters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/stats")
async def get_analytics_stats(semester: str = None):
    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Build WHERE clause for semester filtering
        where = ""
        params = ()
        if semester and semester != "all":
            where = " WHERE semester = %s"
            params = (semester,)
        
        # 1. Average & Count
        cursor.execute(f"SELECT AVG(pointer) as avg_gpa, COUNT(*) as total_students FROM student_performance{where}", params)
        summary = cursor.fetchone()
        
        # 2. Topper
        cursor.execute(f"SELECT student_name, pointer, semester FROM student_performance{where} ORDER BY pointer DESC LIMIT 1", params)
        topper = cursor.fetchone()
        
        # 3. Distribution (for bar/pie chart)
        cursor.execute(f"""
            SELECT 
                CASE 
                    WHEN pointer >= 9.0 THEN '9.0 - 10.0'
                    WHEN pointer >= 8.0 THEN '8.0 - 8.9'
                    WHEN pointer >= 7.0 THEN '7.0 - 7.9'
                    WHEN pointer >= 6.0 THEN '6.0 - 6.9'
                    ELSE 'Below 6.0'
                END as grade_range,
                COUNT(*) as count
            FROM student_performance{where}
            GROUP BY grade_range
            ORDER BY grade_range DESC
        """, params)
        distribution = cursor.fetchall()
        
        # 4. Year/Semester wise averages (always show all semesters for comparison)
        cursor.execute("SELECT semester, AVG(pointer) as avg_gpa, COUNT(*) as student_count FROM student_performance GROUP BY semester ORDER BY semester")
        sem_averages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "summary": summary,
            "topper": topper,
            "distribution": distribution,
            "semester_averages": sem_averages,
            "filtered_semester": semester or "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 6. KT Processing, Reconciliation & Final Output ---

def ensure_examination_attempts_table():
    """Create the examination_attempts table if it doesn't exist."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS examination_attempts (
                attempt_id INT AUTO_INCREMENT PRIMARY KEY,
                student_identifier VARCHAR(255) NOT NULL,
                student_name VARCHAR(255) DEFAULT '',
                student_level VARCHAR(10) DEFAULT 'SE',
                exam_session VARCHAR(50) NOT NULL,
                semester VARCHAR(20) DEFAULT '',
                attempt_status VARCHAR(10) DEFAULT 'UNKNOWN',
                gpa FLOAT DEFAULT 0.0,
                clearance_pointer TEXT,
                source_pdf VARCHAR(255) DEFAULT '',
                file_id INT DEFAULT NULL,
                screenshot LONGTEXT,
                exam_type VARCHAR(20) DEFAULT 'REGULAR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_attempt (student_identifier, exam_session, semester, exam_type)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("[Init DB] examination_attempts table verified.")
    except Exception as e:
        print(f"[Init DB Warning] examination_attempts migration: {e}")

# Run migration on import
try:
    ensure_examination_attempts_table()
except Exception:
    pass

@app.on_event("startup")
def on_kt_startup():
    ensure_examination_attempts_table()


class KTUploadParams(BaseModel):
    exam_session: str = "SH 2026"
    semester: str = "sem3"
    student_level: str = "SE"


@app.post("/upload-kt")
async def upload_kt(
    file: UploadFile = File(...),
    user_name: str = "Anonymous",
    exam_session: str = "SH 2026",
    semester: str = "sem3",
    student_level: str = "SE",
):
    """Upload a KT/re-examination result PDF and store as KT examination attempts."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF allowed")

    f_id = track_file_upload(file.filename, user_name, "PDF")
    print(f"\n[KT Upload] Received {file.filename} (Level: {student_level}, Semester: {semester}, Session: {exam_session}) from {user_name}")
    add_db_log(user_name, "KT Upload", f"Processing KT file {file.filename} for {exam_session} {semester}")

    file_id = str(uuid.uuid4())
    temp_file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    all_students = []
    duplicates = 0
    errors = []
    raw_students = []

    level_norm = (student_level or "SE").strip().upper()
    is_fe_be = level_norm in ("FE", "BE") or semester in ("sem1", "sem2", "sem7", "sem8")

    if is_fe_be:
        # FE and BE Format: Specifically trigger 7-digit detection engine
        try:
            from FE_BE import process_pdf_to_generator
            for result_page in process_pdf_to_generator(temp_file_path, semester=semester):
                for s in result_page.get("students", []):
                    raw_students.append({
                        "sid": s.get("ern", "") or s.get("roll", "") or s.get("name", ""),
                        "name": s.get("name", ""),
                        "roll": s.get("roll", ""),
                        "status": s.get("ocr_result", {}).get("status", "UNKNOWN"),
                        "gpa": float(s.get("ocr_result", {}).get("gpa", 0.0)),
                        "screenshot": s.get("ocr_result", {}).get("screenshot", ""),
                    })
        except Exception as e:
            errors.append(f"FE/BE 7-digit scan error: {e}")
    else:
        # SE and TE Format: Strictly trigger general marksheet scan (7-digit logic does not trigger)
        try:
            from general_marks_scan import process_marksheet_iter
            for page_data in process_marksheet_iter(temp_file_path):
                for s in page_data.get("students", []):
                    raw_students.append({
                        "sid": s.get("ern", "") or s.get("roll", "") or s.get("name", ""),
                        "name": s.get("name", ""),
                        "roll": s.get("roll", ""),
                        "status": s.get("status", "UNKNOWN"),
                        "gpa": float(s.get("gpa", 0.0)),
                        "screenshot": "",
                    })
        except Exception as e:
            errors.append(f"SE/TE marksheet scan error: {e}")

    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch existing attempts for this level and semester to identify failed candidates
        cursor.execute("""
            SELECT student_identifier, student_name, gpa, exam_session, attempt_status
            FROM examination_attempts
            WHERE student_level = %s AND semester = %s
        """, (student_level, semester))
        existing_sem_records = cursor.fetchall()

        failed_candidates = [
            r for r in existing_sem_records 
            if (r.get("attempt_status") or "").upper() in ("FAIL", "F", "FAILED", "UNSUCCESSFUL")
        ]
        passed_identifiers = {
            str(r.get("student_identifier", "")).strip().upper() 
            for r in existing_sem_records 
            if (r.get("attempt_status") or "").upper() in ("PASS", "P", "SUCCESS", "SUCCESSFUL", "PASSED")
        }
        passed_names = {
            " ".join(str(r.get("student_name", "")).upper().split()) 
            for r in existing_sem_records 
            if (r.get("attempt_status") or "").upper() in ("PASS", "P", "SUCCESS", "SUCCESSFUL", "PASSED")
        }

        import difflib
        def match_failed_candidate(c_name, c_sid, failed_list):
            name_clean = " ".join(str(c_name or "").upper().split())
            sid_clean = str(c_sid or "").strip().upper()
            for f in failed_list:
                f_sid = str(f.get("student_identifier", "")).strip().upper()
                f_name = " ".join(str(f.get("student_name", "")).upper().split())
                if f_sid and (f_sid == sid_clean or f_sid in name_clean or sid_clean in f_sid):
                    return f
                if f_name and (f_name == name_clean or f_name in name_clean or name_clean in f_name):
                    return f
                if f_name and difflib.SequenceMatcher(None, f_name, name_clean).ratio() > 0.82:
                    return f
            return None

        for s in raw_students:
            sid = s["sid"] or s["name"]
            name = s["name"]
            raw_st = (s["status"] or "UNKNOWN").upper()
            if raw_st in ("P", "PASS", "SUCCESS", "SUCCESSFUL", "PASSED"):
                norm_status = "PASS"
            elif raw_st in ("F", "FAIL", "FAILED", "UNSUCCESSFUL"):
                norm_status = "FAIL"
            else:
                norm_status = raw_st
            gpa = s["gpa"]
            screenshot = s["screenshot"]
            pointer = f"{gpa:.2f}" if (norm_status == "PASS" and gpa > 0) else ""

            # Check if there are known failed candidates in DB for this semester
            if failed_candidates:
                matched_fc = match_failed_candidate(name, sid, failed_candidates)
                if matched_fc:
                    # Matched an authentic failed candidate sitting for KT!
                    sid = matched_fc.get("student_identifier") or sid
                    name = matched_fc.get("student_name") or name
                    print(f"[KT Upload] Matched failed candidate: {name} ({sid}) -> {norm_status} ({gpa})")
                else:
                    # Student wasn't in the failed list.
                    # If they already passed this semester regularly, skip adding a redundant KT attempt
                    name_norm = " ".join(str(name).upper().split())
                    sid_norm = str(sid).strip().upper()
                    if sid_norm in passed_identifiers or name_norm in passed_names:
                        print(f"[KT Upload] Skipping {name}: already passed regular examination for {semester}")
                        continue
                    else:
                        print(f"[KT Upload] Unmatched KT candidate: {name} ({sid})")

            # Idempotent insert: ON DUPLICATE KEY UPDATE
            try:
                cursor.execute("""
                    INSERT INTO examination_attempts
                    (student_identifier, student_name, student_level, exam_session,
                     semester, attempt_status, gpa, clearance_pointer, source_pdf, file_id, screenshot, exam_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'KT')
                    ON DUPLICATE KEY UPDATE
                        student_name = VALUES(student_name),
                        attempt_status = VALUES(attempt_status),
                        gpa = VALUES(gpa),
                        clearance_pointer = VALUES(clearance_pointer),
                        source_pdf = VALUES(source_pdf),
                        file_id = VALUES(file_id),
                        screenshot = VALUES(screenshot)
                """, (sid, name, student_level, exam_session, semester,
                      norm_status, gpa, pointer, file.filename, f_id, screenshot))
            except Exception as e:
                if "Duplicate" in str(e):
                    duplicates += 1
                else:
                    errors.append(f"{sid}: {str(e)}")

            all_students.append({
                "name": name,
                "ern": sid,
                "roll": s.get("roll", ""),
                "exam_session": exam_session,
                "exam_type": "KT",
                "ocr_result": {
                    "gpa": gpa,
                    "status": norm_status,
                    "clearance_pointer": pointer,
                    "screenshot": screenshot
                }
            })

        conn.commit()
        cursor.close()
        conn.close()
        print(f"[KT Upload] Successfully saved {len(all_students)} KT attempt(s) into database.")
    except Exception as e:
        print(f"[KT Upload Error] {e}")
        errors.append(str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return {
        "success": True,
        "count": len(all_students),
        "duplicates": duplicates,
        "errors": errors,
        "students": all_students,
        "exam_session": exam_session,
        "semester": semester,
        "student_level": student_level,
        "file_id": f_id,
    }


@app.get("/kt-results")
def get_kt_results(exam_session: str = None, student_level: str = None, semester: str = None):
    """Retrieve stored KT examination attempts with optional filters."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM examination_attempts WHERE exam_type = 'KT'"
        params = []
        if exam_session:
            query += " AND exam_session = %s"
            params.append(exam_session)
        if student_level:
            query += " AND student_level = %s"
            params.append(student_level)
        if semester:
            query += " AND semester = %s"
            params.append(semester)
        query += " ORDER BY created_at DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        # Convert datetime objects to strings
        for row in rows:
            for k, v in row.items():
                if isinstance(v, datetime.datetime):
                    row[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        cursor.close()
        conn.close()
        return {"success": True, "results": rows, "count": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


@app.get("/examination-attempts")
def get_examination_attempts(student_identifier: str = None, exam_session: str = None,
                             student_level: str = None, exam_type: str = None):
    """Retrieve all examination attempts with optional filters."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM examination_attempts WHERE 1=1"
        params = []
        if student_identifier:
            query += " AND student_identifier = %s"
            params.append(student_identifier)
        if exam_session:
            query += " AND exam_session = %s"
            params.append(exam_session)
        if student_level:
            query += " AND student_level = %s"
            params.append(student_level)
        if exam_type:
            query += " AND exam_type = %s"
            params.append(exam_type)
        query += " ORDER BY student_identifier, exam_session"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        for row in rows:
            for k, v in row.items():
                if isinstance(v, datetime.datetime):
                    row[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        cursor.close()
        conn.close()
        return {"success": True, "results": rows, "count": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


class SyncRegularAttemptsRequest(BaseModel):
    student_level: str = "SE"
    exam_session: str = "FH 2026"
    semester: str = "sem3"
    students: Optional[List[Dict[str, Any]]] = None


@app.post("/store-regular-attempts")
async def store_regular_attempts(
    req: Optional[SyncRegularAttemptsRequest] = None,
    student_level: Optional[str] = None,
    exam_session: Optional[str] = None,
    semester: Optional[str] = None,
):
    """
    Sync regular examination attempts into examination_attempts as REGULAR type.
    Supports either JSON body with students or synchronizing from existing DB tables.
    """
    try:
        level = (req.student_level if req else None) or student_level or "SE"
        session_val = (req.exam_session if req else None) or exam_session or "FH 2026"
        sem_val = (req.semester if req else None) or semester or "sem3"
        students_list = req.students if req else None

        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        imported = 0

        if students_list and len(students_list) > 0:
            for s in students_list:
                name = (s.get("name") or "").strip()
                raw_ern = str(s.get("ern") or "").strip()
                raw_roll = str(s.get("roll") or "").strip()

                if raw_ern and raw_ern.upper() not in ("N/A", "NONE", "NULL"):
                    sid = raw_ern
                elif raw_roll and raw_roll.upper() not in ("N/A", "NONE", "NULL"):
                    sid = raw_roll
                else:
                    sid = name or ""

                sem_marks = s.get("marks", {}).get(sem_val, {})
                status = sem_marks.get("status", "UNKNOWN")
                raw_st = str(status or "").upper().strip()
                if raw_st in ("P", "PASS", "SUCCESS", "SUCCESSFUL", "PASSED"):
                    norm_status = "PASS"
                elif raw_st in ("F", "FAIL", "FAILED", "UNSUCCESSFUL"):
                    norm_status = "FAIL"
                else:
                    norm_status = raw_st or "UNKNOWN"

                gpa = float(sem_marks.get("gpa", 0.0))
                screenshot = sem_marks.get("screenshot", "")
                if not sid:
                    continue
                try:
                    cursor.execute("""
                        INSERT INTO examination_attempts
                        (student_identifier, student_name, student_level, exam_session,
                         semester, attempt_status, gpa, screenshot, exam_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'REGULAR')
                        ON DUPLICATE KEY UPDATE
                            student_name = IF(VALUES(student_name) != '', VALUES(student_name), student_name),
                            attempt_status = VALUES(attempt_status),
                            gpa = VALUES(gpa),
                            screenshot = IF(VALUES(screenshot) != '', VALUES(screenshot), screenshot)
                    """, (sid, name, level, session_val, sem_val, norm_status, gpa, screenshot))
                    imported += 1
                except Exception as ex:
                    print(f"[store_regular_attempts Insert Error] {ex}")
        else:
            # Pull from existing fe_be_results joined with student_name if possible
            sql = """
                SELECT f.*, COALESCE(sn.student_name, '') AS resolved_name
                FROM fe_be_results f
                LEFT JOIN student_name sn ON f.ern = sn.ern
            """
            params = []
            if sem_val:
                sql += " WHERE f.semester = %s"
                params.append(sem_val)
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

            for row in rows:
                sid = row.get("ern", "")
                name = row.get("resolved_name", "")
                status = row.get("status", "UNKNOWN")
                gpa = float(row.get("gpa", 0.0))
                screenshot = row.get("screenshot", "")
                try:
                    cursor.execute("""
                        INSERT INTO examination_attempts
                        (student_identifier, student_name, student_level, exam_session,
                         semester, attempt_status, gpa, screenshot, exam_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'REGULAR')
                        ON DUPLICATE KEY UPDATE
                            student_name = IF(VALUES(student_name) != '', VALUES(student_name), student_name),
                            attempt_status = VALUES(attempt_status),
                            gpa = VALUES(gpa),
                            screenshot = IF(VALUES(screenshot) != '', VALUES(screenshot), screenshot)
                    """, (sid, name, level, session_val, sem_val, status.upper(), gpa, screenshot))
                    imported += 1
                except Exception:
                    pass

        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "imported": imported}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/seed-demo-kt")
async def seed_demo_kt_endpoint():
    """Demo seeding permanently disabled to preserve real student database."""
    return {"success": False, "message": "Demo seeding has been permanently disabled."}


class ReconcileRequest(BaseModel):
    student_level: str = "SE"
    exam_session: Optional[str] = None
    semester: Optional[str] = None



@app.post("/reconcile")
async def run_reconciliation(req: ReconcileRequest):
    """
    Run the reconciliation engine on stored examination attempts.
    Returns summary with counts and per-student reconciliation results.
    """
    from reconciliation import (
        ExaminationAttempt as RecAttempt,
        normalize_status as rec_normalize,
        normalize_identifier as rec_norm_id,
        reconcile_batch as rec_batch,
    )

    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)

        # Fetch all relevant attempts (exclude any seeded dummy records)
        query = """
            SELECT * FROM examination_attempts 
            WHERE student_level = %s
              AND student_identifier NOT LIKE 'MU%%'
              AND student_identifier NOT LIKE 'TE-%%'
              AND student_name NOT IN ('Tanay Tiwari', 'Aditi Rao', 'Vihaan Kumar', 'Ananya Mishra', 'Arjun Reddy', 'MHATRE NISHANT SURENDRA', 'Sanya Mehta', 'Rohan Deshmukh', 'Kabir Verma')
        """
        params = [req.student_level]
        if req.semester:
            query += " AND semester = %s"
            params.append(req.semester)
        query += " ORDER BY student_identifier, exam_session"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert DB rows to reconciliation objects
        all_attempts = []
        kt_attempts = []
        regular_ids = set()

        for row in rows:
            att = RecAttempt(
                attempt_id=row.get("attempt_id"),
                student_identifier=row.get("student_identifier", ""),
                student_name=row.get("student_name", ""),
                student_level=row.get("student_level", ""),
                exam_session=row.get("exam_session", ""),
                semester=row.get("semester", ""),
                attempt_status=rec_normalize(row.get("attempt_status", "")),
                gpa=float(row.get("gpa", 0.0)),
                clearance_pointer=row.get("clearance_pointer", "") or "",
                source_pdf=row.get("source_pdf", ""),
                file_id=row.get("file_id"),
                exam_type=row.get("exam_type", "REGULAR"),
            )
            all_attempts.append(att)
            if att.exam_type == "KT":
                kt_attempts.append(att)
            else:
                regular_ids.add(rec_norm_id(att.student_identifier))

        summary = rec_batch(all_attempts, kt_attempts=kt_attempts, regular_identifiers=regular_ids)

        # Serialize results
        results_data = []
        for r in summary.results:
            results_data.append({
                "student_identifier": r.student_identifier,
                "student_name": r.student_name,
                "student_level": r.student_level,
                "clearance_status": r.clearance_status.value,
                "clearance_session": r.clearance_session,
                "clearance_pointer": r.clearance_pointer,
                "final_status": r.final_status,
                "total_attempts": r.total_attempts,
                "review_flags": r.review_flags,
                "attempts": [
                    {
                        "exam_session": a.exam_session,
                        "semester": a.semester,
                        "attempt_status": a.attempt_status.value,
                        "gpa": a.gpa,
                        "exam_type": a.exam_type,
                        "source_pdf": a.source_pdf,
                        "clearance_pointer": a.clearance_pointer,
                    }
                    for a in r.attempts
                ]
            })

        exceptions_data = []
        for e in summary.exceptions:
            exceptions_data.append({
                "student_identifier": e.student_identifier,
                "student_name": e.student_name,
                "exception_type": e.exception_type.value,
                "description": e.description,
                "action_required": e.action_required,
            })

        return {
            "success": True,
            "summary": {
                "total_students": summary.total_students,
                "pass_count": summary.pass_count,
                "fail_count": summary.fail_count,
                "cleared_count": summary.cleared_count,
                "uncleared_count": summary.uncleared_count,
                "pending_count": summary.pending_count,
                "duplicate_count": summary.duplicate_count,
                "conflict_count": summary.conflict_count,
                "unmatched_kt_count": summary.unmatched_kt_count,
                "needs_review_count": summary.needs_review_count,
                "session_counts": summary.session_counts,
            },
            "results": results_data,
            "exceptions": exceptions_data,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-final-output")
async def generate_final_output(req: ReconcileRequest):
    """
    Run reconciliation and generate a downloadable Excel workbook with three sheets:
      1. Consolidated Results
      2. Examination Attempt History
      3. Exceptions and Validation
    """
    from reconciliation import (
        ExaminationAttempt as RecAttempt,
        normalize_status as rec_normalize,
        normalize_identifier as rec_norm_id,
        reconcile_batch as rec_batch,
    )
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT * FROM examination_attempts 
            WHERE student_level = %s
              AND student_identifier NOT LIKE 'MU%%'
              AND student_identifier NOT LIKE 'TE-%%'
              AND student_name NOT IN ('Tanay Tiwari', 'Aditi Rao', 'Vihaan Kumar', 'Ananya Mishra', 'Arjun Reddy', 'MHATRE NISHANT SURENDRA', 'Sanya Mehta', 'Rohan Deshmukh', 'Kabir Verma')
        """
        params = [req.student_level]
        if req.semester:
            query += " AND semester = %s"
            params.append(req.semester)
        query += " ORDER BY student_identifier, exam_session"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Build attempt objects
        all_attempts = []
        kt_attempts = []
        regular_ids = set()

        for row in rows:
            att = RecAttempt(
                attempt_id=row.get("attempt_id"),
                student_identifier=row.get("student_identifier", ""),
                student_name=row.get("student_name", ""),
                student_level=row.get("student_level", ""),
                exam_session=row.get("exam_session", ""),
                semester=row.get("semester", ""),
                attempt_status=rec_normalize(row.get("attempt_status", "")),
                gpa=float(row.get("gpa", 0.0)),
                clearance_pointer=row.get("clearance_pointer", "") or "",
                source_pdf=row.get("source_pdf", ""),
                file_id=row.get("file_id"),
                exam_type=row.get("exam_type", "REGULAR"),
            )
            all_attempts.append(att)
            if att.exam_type == "KT":
                kt_attempts.append(att)
            else:
                regular_ids.add(rec_norm_id(att.student_identifier))

        summary = rec_batch(all_attempts, kt_attempts=kt_attempts, regular_identifiers=regular_ids)

        # --- Build Excel workbook ---
        wb = openpyxl.Workbook()

        # Styles
        header_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        title_font = Font(name="Calibri", bold=True, size=14, color="1F4E79")
        subtitle_font = Font(name="Calibri", bold=True, size=10, color="555555")
        pass_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        fail_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        review_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin"),
        )

        # --- Sheet 1: Consolidated Results ---
        ws1 = wb.active
        ws1.title = "Consolidated Results"
        ws1.append([f"{req.student_level} CONSOLIDATED RESULTS"])
        ws1.merge_cells("A1:L1")
        ws1["A1"].font = title_font
        ws1.append([f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        ws1["A2"].font = subtitle_font
        ws1.append([])

        consol_headers = [
            "Student ID", "Student Name", "Level",
            "Original Exam Session", "Original Status", "Original GPA",
            "Subsequent Exam Session", "Subsequent Status", "Subsequent GPA",
            "Clearance Status", "Clearance Session", "Clearance Pointer",
            "Final Consolidated Status", "Total Attempts", "Review Flags"
        ]
        ws1.append(consol_headers)
        for col_num, hdr in enumerate(consol_headers, 1):
            cell = ws1.cell(row=4, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
            cell.border = thin_border

        for r_idx, rec in enumerate(summary.results, 5):
            sorted_atts = rec.attempts
            orig = sorted_atts[0] if sorted_atts else None
            subseq = sorted_atts[1] if len(sorted_atts) > 1 else None

            row_data = [
                rec.student_identifier,
                rec.student_name,
                rec.student_level,
                orig.exam_session if orig else "",
                orig.attempt_status.value if orig else "",
                orig.gpa if orig else "",
                subseq.exam_session if subseq else "",
                subseq.attempt_status.value if subseq else "",
                subseq.gpa if subseq else "",
                rec.clearance_status.value,
                rec.clearance_session,
                rec.clearance_pointer,
                rec.final_status,
                rec.total_attempts,
                "; ".join(rec.review_flags) if rec.review_flags else "",
            ]
            ws1.append(row_data)

            # Color-code clearance status
            status_cell = ws1.cell(row=r_idx, column=10)
            status_cell.border = thin_border
            cs = rec.clearance_status.value
            if cs in ("PASSED_ORIGINAL", "CLEARED_SUBSEQUENTLY"):
                status_cell.fill = pass_fill
            elif cs in ("UNCLEARED", "PENDING"):
                status_cell.fill = fail_fill
            else:
                status_cell.fill = review_fill

            for col_num in range(1, len(row_data) + 1):
                ws1.cell(row=r_idx, column=col_num).border = thin_border

        # Auto-width
        for col in ws1.columns:
            max_length = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            ws1.column_dimensions[col_letter].width = min(max_length + 4, 40)
        ws1.auto_filter.ref = f"A4:{get_column_letter(len(consol_headers))}{ws1.max_row}"
        ws1.freeze_panes = "A5"

        # --- Sheet 2: Examination Attempt History ---
        ws2 = wb.create_sheet("Attempt History")
        hist_headers = [
            "Student ID", "Student Name", "Level",
            "Exam Session", "Semester", "Status", "GPA",
            "Exam Type", "Source PDF", "Clearance Pointer",
            "File ID", "Record Timestamp"
        ]
        ws2.append(hist_headers)
        for col_num, hdr in enumerate(hist_headers, 1):
            cell = ws2.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
            cell.border = thin_border

        for row in rows:
            created = row.get("created_at", "")
            if isinstance(created, datetime.datetime):
                created = created.strftime("%Y-%m-%d %H:%M:%S")
            ws2.append([
                row.get("student_identifier", ""),
                row.get("student_name", ""),
                row.get("student_level", ""),
                row.get("exam_session", ""),
                row.get("semester", ""),
                row.get("attempt_status", ""),
                row.get("gpa", 0),
                row.get("exam_type", ""),
                row.get("source_pdf", ""),
                row.get("clearance_pointer", ""),
                row.get("file_id", ""),
                created,
            ])

        for col in ws2.columns:
            max_length = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            ws2.column_dimensions[col_letter].width = min(max_length + 4, 40)
        ws2.auto_filter.ref = f"A1:{get_column_letter(len(hist_headers))}{ws2.max_row}"
        ws2.freeze_panes = "A2"

        # --- Sheet 3: Exceptions and Validation ---
        ws3 = wb.create_sheet("Exceptions")
        exc_headers = [
            "Student ID", "Student Name", "Exception Type",
            "Description", "Action Required"
        ]
        ws3.append(exc_headers)
        for col_num, hdr in enumerate(exc_headers, 1):
            cell = ws3.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
            cell.border = thin_border

        if summary.exceptions:
            for exc in summary.exceptions:
                ws3.append([
                    exc.student_identifier,
                    exc.student_name,
                    exc.exception_type.value,
                    exc.description,
                    exc.action_required,
                ])
        else:
            ws3.append(["", "", "", "No exceptions detected", ""])

        for col in ws3.columns:
            max_length = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            ws3.column_dimensions[col_letter].width = min(max_length + 4, 50)
        ws3.auto_filter.ref = f"A1:{get_column_letter(len(exc_headers))}{ws3.max_row}"
        ws3.freeze_panes = "A2"

        # --- Sheet 4: Sem 1 to Sem 8 Progression & Clearance Analysis ---
        ws4 = wb.create_sheet("Sem 1-8 Analysis")
        ws4.append(["SEMESTER 1 TO 8 CLEARANCE & PROGRESSION ANALYSIS"])
        ws4.merge_cells("A1:L1")
        ws4["A1"].font = title_font
        ws4.append(["University Examination History & KT Clearance Matrix Across Semesters 1 - 8"])
        ws4["A2"].font = subtitle_font
        ws4.append([])

        matrix_headers = [
            "Student ID", "Student Name", "Level",
            "sem 1", "sem 2", "sem 3", "sem 4", "sem 5", "sem 6", "sem 7", "sem 8",
            "Current Backlogs"
        ]
        ws4.append(matrix_headers)
        for col_num, hdr in enumerate(matrix_headers, 1):
            cell = ws4.cell(row=4, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
        ws4.row_dimensions[4].height = 26

        # Fetch multi-semester attempts for all relevant students
        sids = list({r.student_identifier for r in summary.results if r.student_identifier})
        conn_multi = get_db_conn()
        cur_multi = conn_multi.cursor(dictionary=True)

        if sids:
            format_strings = ','.join(['%s'] * len(sids))
            cur_multi.execute(
                f"SELECT * FROM examination_attempts WHERE student_identifier IN ({format_strings}) ORDER BY student_identifier, semester, created_at",
                tuple(sids)
            )
            multi_rows = cur_multi.fetchall()
        else:
            multi_rows = []
        cur_multi.close()
        conn_multi.close()

        def format_sess_short(s):
            if not s:
                return ""
            import re
            m = re.search(r'(FH|SH)\s*(\d{2,4})', str(s), re.IGNORECASE)
            if m:
                term = m.group(1).upper()
                yr = m.group(2)
                if len(yr) == 4:
                    yr = yr[-2:]
                return f"{term}{yr}"
            return str(s).strip()

        students_dict = {}
        for rec in summary.results:
            students_dict[rec.student_identifier] = {
                "name": rec.student_name,
                "level": rec.student_level,
                "attempts": []
            }

        for row_m in multi_rows:
            sid = row_m.get("student_identifier", "")
            if sid not in students_dict:
                students_dict[sid] = {
                    "name": row_m.get("student_name", ""),
                    "level": row_m.get("student_level", ""),
                    "attempts": []
                }
            students_dict[sid]["attempts"].append(row_m)

        pass_matrix_fill = PatternFill(start_color="E2F0D9", end_color="E2F0D9", fill_type="solid")
        pass_matrix_font = Font(name="Calibri", size=10, color="276A3C", bold=False)
        cleared_matrix_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
        cleared_matrix_font = Font(name="Calibri", size=10, color="1F4E79", bold=True)
        fail_matrix_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        fail_matrix_font = Font(name="Calibri", size=10, color="C00000", bold=True)

        row_m_idx = 5
        for sid, sinfo in students_dict.items():
            name = sinfo.get("name", "")
            lvl = sinfo.get("level", "")
            atts = sinfo.get("attempts", [])

            sem_map = {f"sem{i}": [] for i in range(1, 9)}
            for a in atts:
                raw_sem = str(a.get("semester", "")).lower().replace(" ", "").replace("_", "")
                for i in range(1, 9):
                    if raw_sem in (f"sem{i}", f"semester{i}", str(i)):
                        sem_map[f"sem{i}"].append(a)
                        break

            # Check KT clearances to detect "passed FH26 and sem3 in FH26"
            cleared_in_session = {}
            for s_key, att_list in sem_map.items():
                for a in att_list:
                    if a.get("exam_type", "").upper() == "KT" and a.get("attempt_status", "").upper() == "PASS":
                        sess_short = format_sess_short(a.get("exam_session", ""))
                        if sess_short:
                            cleared_in_session.setdefault(sess_short, []).append(s_key)

            sem_cells = []
            pending_backlogs = []

            for i in range(1, 9):
                s_key = f"sem{i}"
                att_list = sem_map[s_key]
                if not att_list:
                    sem_cells.append({"text": "", "type": "empty"})
                    continue

                regs = [a for a in att_list if a.get("exam_type", "").upper() != "KT"]
                kts = [a for a in att_list if a.get("exam_type", "").upper() == "KT"]

                reg_att = regs[0] if regs else None
                last_kt = kts[-1] if kts else None

                reg_status = (reg_att.get("attempt_status", "") if reg_att else "").upper()
                reg_session = format_sess_short(reg_att.get("exam_session", "")) if reg_att else ""

                cleared_earlier = cleared_in_session.get(reg_session, [])
                cleared_earlier_other = [s for s in cleared_earlier if s != s_key]

                cell_text = ""
                cell_type = "empty"

                if reg_status == "PASS":
                    cell_text = f"passed {reg_session}"
                    cell_type = "pass"
                    if cleared_earlier_other:
                        cleared_str = ", ".join(cleared_earlier_other)
                        cell_text += f" and {cleared_str} in {reg_session}"
                        cell_type = "cleared"
                elif reg_status == "FAIL":
                    if last_kt and last_kt.get("attempt_status", "").upper() == "PASS":
                        kt_sess = format_sess_short(last_kt.get("exam_session", ""))
                        cell_text = f"failed {reg_session}; cleared in {kt_sess}"
                        cell_type = "cleared"
                    elif last_kt and last_kt.get("attempt_status", "").upper() == "FAIL":
                        kt_sess = format_sess_short(last_kt.get("exam_session", ""))
                        cell_text = f"failed {reg_session}; failed KT in {kt_sess}"
                        cell_type = "fail"
                        pending_backlogs.append(s_key)
                    else:
                        cell_text = f"failed {reg_session}"
                        cell_type = "fail"
                        pending_backlogs.append(s_key)
                elif last_kt:
                    kt_sess = format_sess_short(last_kt.get("exam_session", ""))
                    if last_kt.get("attempt_status", "").upper() == "PASS":
                        cell_text = f"cleared in {kt_sess}"
                        cell_type = "cleared"
                    else:
                        cell_text = f"failed KT in {kt_sess}"
                        cell_type = "fail"
                        pending_backlogs.append(s_key)
                else:
                    cell_text = ""
                    cell_type = "empty"

                sem_cells.append({"text": cell_text, "type": cell_type})

            backlog_text = "Clear" if not pending_backlogs else f"KT in {', '.join(pending_backlogs).upper()}"

            row_data = [sid, name, lvl] + [c["text"] for c in sem_cells] + [backlog_text]
            ws4.append(row_data)
            ws4.row_dimensions[row_m_idx].height = 24

            for col_idx, c_info in enumerate(sem_cells, 4):
                cell = ws4.cell(row=row_m_idx, column=col_idx)
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border
                if c_info["type"] == "pass":
                    cell.fill = pass_matrix_fill
                    cell.font = pass_matrix_font
                elif c_info["type"] == "cleared":
                    cell.fill = cleared_matrix_fill
                    cell.font = cleared_matrix_font
                elif c_info["type"] == "fail":
                    cell.fill = fail_matrix_fill
                    cell.font = fail_matrix_font

            # Style ID, Name, Level, and Backlog
            for c_pos in (1, 2, 3):
                c_cell = ws4.cell(row=row_m_idx, column=c_pos)
                c_cell.border = thin_border
                c_cell.alignment = Alignment(horizontal="left" if c_pos == 2 else "center", vertical="center")
                c_cell.font = Font(name="Calibri", bold=(c_pos != 3), size=10)

            bk_cell = ws4.cell(row=row_m_idx, column=len(matrix_headers))
            bk_cell.border = thin_border
            bk_cell.alignment = Alignment(horizontal="center", vertical="center")
            if pending_backlogs:
                bk_cell.fill = fail_matrix_fill
                bk_cell.font = fail_matrix_font
            else:
                bk_cell.fill = pass_matrix_fill
                bk_cell.font = pass_matrix_font

            row_m_idx += 1

        for col in ws4.columns:
            max_len = 0
            col_let = get_column_letter(col[0].column)
            for cell in col:
                try:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                except Exception:
                    pass
            ws4.column_dimensions[col_let].width = max(min(max_len + 4, 38), 12)

        ws4.auto_filter.ref = f"A4:{get_column_letter(len(matrix_headers))}{ws4.max_row}"
        ws4.freeze_panes = "D5"

        # Save to buffer
        output_buffer = io.BytesIO()
        wb.save(output_buffer)
        output_buffer.seek(0)

        filename = f"{req.student_level}_Consolidated_Results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        add_db_log("System", "Final Output", f"Generated {filename} with {summary.total_students} students")

        return StreamingResponse(
            output_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    print(f"[Main] Starting Uvicorn on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
