
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
from typing import List, Optional, Any
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

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    print(f"[Main] Starting Uvicorn on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
