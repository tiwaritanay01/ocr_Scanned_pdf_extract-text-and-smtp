
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import uuid
import datetime
import json
import mysql.connector
import hashlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
import importlib

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- 1. Security & Authentication (Gap 2) ---

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# Persistent User Credentials (aligned with blueprint)
admins = {
    "dept_admin": {"password": hash_password("admin123"), "role": "staff", "name": "Department Head"},
    "super_admin": {"password": hash_password("super123"), "role": "superadmin", "name": "System Admin"}
}

class LoginRequest(BaseModel):
    username: str
    password: str

# --- 2. Database & Logging Helpers (Gap 1, 4) ---

def get_db_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password="root123",
        database=os.getenv("DB_NAME", "student_results")
    )

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

def track_file_upload(file_name, admin_name, format_type):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO result_files (file_name, admin_name, format_type, college_name, status) 
            VALUES (%s, %s, %s, 'Vasantdada Patil Pratishthan\'s College of Engineering', 'Pending')
        """, (file_name, admin_name, format_type))
        f_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return f_id
    except Exception as e:
        print(f"[Upload Tracking Error] {e}")
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

def get_db_student_names():
    names = []
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT student_name FROM student_name")
        names = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[DB] Warning: Could not fetch student names: {e}")
    return names

# --- 3. Authentication Endpoints ---

@app.post("/login")
async def login(request: LoginRequest):
    try:
        conn = get_db_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE username = %s", (request.username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user["password"] == hash_password(request.password):
            add_db_log(user["name"], "Login", "Successfully logged into dashboard")
            return {
                "success": True,
                "role": user["role"],
                "user_name": user["name"]
            }
        add_db_log(request.username or "Unknown", "Failed Login", "Invalid credentials attempted")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        print(f"[Login Error] {e}")
        raise HTTPException(status_code=500, detail="Database error during login")

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

class MailResultsRequest(BaseModel):
    students: List[StudentResult]
    user_name: str

DUMMY_EMAILS = ["tiwaritanay01@gmail.com", "anonymousthegreat750@gmail.com", "vu1f2425005@pvppcoe.ac.in"]

def send_result_email(to_email, student_name, pointer, avg):
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_email or not smtp_password: return False
    msg = MIMEMultipart()
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg["Subject"] = f"Exam Result - {student_name}"
    body = f"Hello {student_name},\n\nYour result: GPA {pointer}, Avg {avg}.\n\nRegards,\nExam Cell"
    msg.attach(MIMEText(body, "plain"))
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
    for i, student in enumerate(req.students):
        target_email = DUMMY_EMAILS[i % len(DUMMY_EMAILS)]
        success = send_result_email(target_email, student.name, student.pointer, student.avg)
        status = "sent" if success else "failed"
        log_email_sent(target_email, student.name, "Bulk Distribution", status)
        if success: success_count += 1
        else: fail_count += 1
    add_db_log(req.user_name, "Email Blast", f"Distributed: {success_count} success, {fail_count} failed")
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
            cursor.execute("SELECT ern, seat_no, status, gpa, semester FROM fe_be_results WHERE semester = %s", (semester,))
        else:
            cursor.execute("SELECT ern, seat_no, status, gpa, semester FROM fe_be_results")
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

# --- 6. Database Explorer Endpoints ---

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
        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.execute(f"DESCRIBE {table_name}")
        schema = cursor.fetchall()
        cursor.close(); conn.close()
        return {"success": True, "data": rows, "schema": schema}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

class DBUpdateRequest(BaseModel):
    table: str; pk_field: str; pk_value: str; data: dict

@app.post("/db/update-row")
async def update_db_row(req: DBUpdateRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = %s" for k in req.data.keys()])
        values = list(req.data.values()) + [req.pk_value]
        cursor.execute(f"UPDATE {req.table} SET {set_clause} WHERE {req.pk_field} = %s", tuple(values))
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

class DBAddRowRequest(BaseModel):
    table: str; data: dict

@app.post("/db/add-row")
async def add_db_row(req: DBAddRowRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        fields = ", ".join(req.data.keys()); placeholders = ", ".join(["%s"] * len(req.data))
        cursor.execute(f"INSERT INTO {req.table} ({fields}) VALUES ({placeholders})", tuple(req.data.values()))
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

class DBColumnRequest(BaseModel):
    table: str; column_name: str; column_type: str = "VARCHAR(255)"; old_name: str = None

@app.post("/db/add-column")
async def add_db_column(req: DBColumnRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        cursor.execute(f"ALTER TABLE {req.table} ADD COLUMN {req.column_name} {req.column_type}")
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/db/rename-column")
async def rename_db_column(req: DBColumnRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        cursor.execute(f"ALTER TABLE {req.table} RENAME COLUMN {req.old_name} TO {req.column_name}")
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/db/delete-row")
async def delete_db_row(req: DBUpdateRequest):
    try:
        conn = get_db_conn(); cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {req.table} WHERE {req.pk_field} = %s", (req.pk_value,))
        conn.commit(); cursor.close(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("[Main] Starting Uvicorn on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
