from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
load_dotenv()
import shutil
import uuid
from general_marks_scan import process_marksheet
from pydantic import BaseModel
from typing import List, Optional
import datetime
import mysql.connector

def get_db_student_names():
    """Fetch the ground truth student name list from MySQL for fuzzy matching."""
    names = []
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password="root123",
            database=os.getenv("DB_NAME", "student_results")
        )
        cursor = conn.cursor()
        cursor.execute("SELECT student_name FROM student_name")
        names = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        print(f"[DB] Loaded {len(names)} expected student names for fuzzy matching.")
    except Exception as e:
        print(f"[DB] Warning: Could not fetch student names from DB: {e}")
    return names
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = FastAPI()

# Activity Logging System
activity_log = []

def add_log(user, action, details="", status="Success"):
    activity_log.append({
        "id": len(activity_log) + 1,
        "user": user,
        "action": action,
        "details": details,
        "status": status,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# In-memory User Credentials (in sync with SuperAdmin view)
USERS = {
    "superadmin@college.edu": {"password": "admin123", "role": "super-admin", "name": "System SuperAdmin", "dept": "Management"},
    "cs_admin@college.edu": {"password": "cs123", "role": "dept-admin", "name": "Dr. Sarah Wilson", "dept": "Computer Science"},
    "mech_admin@college.edu": {"password": "me123", "role": "dept-admin", "name": "Prof. James Miller", "dept": "Mechanical Eng."},
    "ee_admin@college.edu": {"password": "ee123", "role": "dept-admin", "name": "Dr. Emily Chen", "dept": "Electrical Eng."},
}

class LoginRequest(BaseModel):
    email: str
    password: str

class StudentResult(BaseModel):
    name: str
    email: str
    pointer: float
    avg: float

class MailResultsRequest(BaseModel):
    students: List[StudentResult]
    user_name: str

# Dummy Emails to cycle through
DUMMY_EMAILS = [
    "tiwaritanay01@gmail.com",
    "anonymousthegreat750@gmail.com",
    "vu1f2425005@pvppcoe.ac.in"
]

def send_result_email(to_email, student_name, pointer, avg):
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not smtp_email or not smtp_password:
        print("SMTP credentials missing!")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg["Subject"] = f"Exam Result - {student_name}"

    body = f"""Hello {student_name},

Your exam result has been processed.

Details:
- Name: {student_name}
- Current Pointer: {pointer}
- Average Pointer: {avg}

Regards,
Exam Cell Portal
"""
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

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/login")
async def login(req: LoginRequest):
    user = USERS.get(req.email)
    if user and user["password"] == req.password:
        add_log(user["name"], "Login", f"Logged into system via unified gateway")
        return {
            "success": True, 
            "user": {
                "name": user["name"],
                "email": req.email,
                "role": user["role"],
                "dept": user["dept"]
            }
        }
    
    add_log(req.email, "Failed Login", f"Failed attempt on unified gateway", "Failed")
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.get("/logs")
async def get_logs():
    return {"logs": list(reversed(activity_log))} # Return newest first

@app.post("/send-results")
async def send_results(req: MailResultsRequest):
    success_count = 0
    fail_count = 0
    
    for i, student in enumerate(req.students):
        # Cycle through dummy emails as requested
        target_email = DUMMY_EMAILS[i % len(DUMMY_EMAILS)]
        
        success = send_result_email(
            target_email, 
            student.name, 
            student.pointer, 
            student.avg
        )
        
        if success:
            success_count += 1
        else:
            fail_count += 1
            
    add_log(
        req.user_name, 
        "Bulk Mailing", 
        f"Mails sent: {success_count} Success, {fail_count} Failed"
    )
    
    return {"success": True, "sent": success_count, "failed": fail_count}

@app.post("/upload-marksheet-stream")
async def upload_marksheet_stream(file: UploadFile = File(...), user_name: str = "Anonymous", semester: str = "sem3", expected_names: str = Form(None)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_id = str(uuid.uuid4())
    temp_file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 1. Always load from DB first
    name_list = get_db_student_names()
    
    # 2. Optionally merge with any names passed by frontend
    if expected_names:
        import json
        extra_names = json.loads(expected_names)
        existing_set = set(name_list)
        for n in extra_names:
            if n not in existing_set:
                name_list.append(n)
    
    # 3. Write to temp_students.xlsx for fuzzy matching
    if name_list:
        import pandas as pd
        df = pd.DataFrame({"Name": name_list})
        df.to_excel("temp_students.xlsx", index=False)
        import importlib
        import general_marks_scan
        importlib.reload(general_marks_scan)

    from general_marks_scan import process_marksheet_iter
    from fastapi.responses import StreamingResponse
    import json

    def generate_results():
        try:
            for page_data in process_marksheet_iter(temp_file_path):
                # Format results for this page
                formatted_students = []
                for s in page_data["students"]:
                    formatted_students.append({
                        "name": s["name"],
                        "ocr_result": {
                            "gpa": s["gpa"],
                            "status": s["status"]
                        }
                    })
                
                chunk = {
                    "page": page_data["page"],
                    "total_pages": page_data["total_pages"],
                    "students": formatted_students,
                    "target_semester": semester
                }
                yield json.dumps(chunk) + "\n"
        finally:
            # Clean up temp files after streaming is done
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists("temp_students.xlsx"):
                os.remove("temp_students.xlsx")

    return StreamingResponse(generate_results(), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
