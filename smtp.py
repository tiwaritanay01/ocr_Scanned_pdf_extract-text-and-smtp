import os
import smtplib
import mysql.connector
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        auth_plugin="mysql_native_password"
    )


SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_mail(to_email, attachment_path, ern):
    msg = MIMEMultipart()
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "Your Exam Result"

    body = f"""Hello,

Your exam result is attached.

Seat Number: {ern}

Regards,
Exam Cell
"""
    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{os.path.basename(attachment_path)}"'
    )
    msg.attach(part)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SMTP_EMAIL, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()

def main():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.email, r.result_path, r.ern
        FROM results r
        JOIN students s ON r.ern = s.ern
        WHERE s.email IS NOT NULL
    """)

    rows = cur.fetchall()

    for email, path, ern in rows:
        if os.path.exists(path):
            try:
                send_mail(email, path, ern)
                print(f"Mail sent to {email}")
            except Exception as e:
                print(f"Failed for {email}: {e}")
        else:
            print(f"File not found for {ern}: {path}")

    conn.close()

if __name__ == "__main__":
    main()
