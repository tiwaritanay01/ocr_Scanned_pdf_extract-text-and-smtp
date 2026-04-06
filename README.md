# 🎓 Online Result Generator & Distribution System

A robust, enterprise-grade automated pipeline designed to extract student results from institutional PDF/Excel documents and distribute them via personalized emails with verified visual proof.

---

## 🏗 System Architecture & Workflow

The system is built on a **High-Fidelity Automated Pipeline** designed to bridge the gap between static institutional records and student-facing digital notifications.

### 1. Unified Data Ingestion
The system supports dual-mode ingestion:
- **PDF Mode (Tesseract 5 Deep Learning OCR)**: Processes official university result sheets using a custom **Tesseract 5 (LSTM)** pipeline. It involves grayscale preprocessing, deskewing, and adaptive binarization to handle varying scan qualities.
- **Excel Mode (Data-Driven)**: Direct ingestion of internal departmental spreadsheets. It dynamically identifies subject-wise marks, GPAs, and student metadata using `pandas` heuristics.

### 2. The Verification Ledger (Admin Dashboard)
Extracted data is staged in a "Batch Management" interface for human audit:
- **Floating Academic Breakdown**: An interactive popover triggered by hovering over an `Info` icon in the Actions column, displaying granular subject-wise marks.
- **Visual Verification**: A "Side-Peek" preview that shows the original PDF screenshot captured during the OCR phase.
- **Edit & Lock Logic**: Admin can toggle **Edit Mode** to correct OCR anomalies. Once verified, the admin **Approves** the batch, which persistent-locks the data and generates an audit trace in the `activity_logs`.

### 3. Personalized Distribution
The email engine uses `smtplib` to dispatch results. Each email contains:
- **Dynamic Greeting**: Personalized with the student's name.
- **Live GPA**: The extracted pointer for the specific semester.
- **Visual Proof**: An embedded high-resolution screenshot of their entry from the official result sheet.

---

## 🛠 Tech Stack & Library Deep-Dive

### **Backend (FastAPI & Python)**
| Library | Use Case | Implementation Trigger |
| :--- | :--- | :--- |
| **FastAPI** | Orchestration | Handles all REST endpoints (`/upload-marksheet`, `/send-results`). |
| **pytesseract** | Vision Engine | Interfaces with **Tesseract 5** for high-accuracy text extraction. |
| **PyMuPDF (fitz)** | PDF Handling | Used to convert PDF pages to high-res images for OCR and cropping. |
| **pdf2image** | Conversion | Converts PDF blobs into PIL images for pre-processing. |
| **OpenCV (cv2)** | Pre-processing | Grayscale conversion, deskewing, and grid detection. |
| **Pandas** | Data Management | Core engine for parsing uploaded Excel files and CSV exports. |
| **MySQL Connector** | Persistence | Manages 7 tables (`fe_be_results`, `detailed_results`, etc.). |
| **SMTPLib** | Communication | Securely connects to SMTP servers for batch mailing. |

### **Frontend (React & Tailwind)**
| Library | Use Case | Logic Details |
| :--- | :--- | :--- |
| **Vite** | Build Tool | Optimized frontend development and bundling. |
| **Lucide React** | UI Visuals | Dynamic icons for status tracking (`Shield` for verified, `Activity` for loading). |
| **Context API** | State Management | `DataContext.jsx` syncs student lists across views. |
| **TailwindCSS** | Aesthetics | Custom glassmorphism, floating popovers, and high-density dark mode. |

---

## 🚀 Local Environment Setup

Follow these steps to set up the project on your local machine:

### **1. Prerequisites**
- **Python 3.10+**: [Download here](https://www.python.org/downloads/)
- **Node.js & NPM**: [Download here](https://nodejs.org/)
- **MySQL Server**: [Download here](https://dev.mysql.com/downloads/installer/)

### **2. External Binaries (Critical)**
The pipeline relies on two external binaries that must be installed and added to your system environment:
1.  **Tesseract OCR 5**: 
    - Install from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
    - Ensure the path in `general_marks_scan.py` matches your installation (Default: `C:\Program Files\Tesseract-OCR\tesseract.exe`).
2.  **Poppler**:
    - Required for `pdf2image`. Download the Windows binaries from [here](https://github.com/oschwartz10612/poppler-windows/releases/).
    - Add the `bin` folder to your system's **Path** environment variable.

### **3. Backend Setup**
1.  Navigate to the root directory.
2.  Create a `.env` file based on the environment variables needed:
    ```env
    DB_HOST=localhost
    DB_USER=root
    DB_PASSWORD=your_password
    DB_NAME=result_generator
    SMTP_EMAIL=your_email@gmail.com
    SMTP_PASSWORD=your_app_password
    ```
3.  Install dependencies:
    ```bash
    pip install fastapi uvicorn mysql-connector-python pandas pytesseract pdf2image opencv-python pillow python-dotenv
    ```
4.  Run the server: `python main.py`

### **4. Frontend Setup**
1.  Navigate to `mail_frontend/frontend_mini_pro`.
2.  Install dependencies: `npm install`
3.  Run development server: `npm run dev`

---

## 📂 Database Schema Overview
The system maintains strict relational integrity across 7 tables:
- `fe_be_results`: Summary results (GPA, Status) for FE/BE batches.
- `detailed_results`: JSON-capable storage for subject-wise marks across semesters.
- `result_files`: Metadata for every document processed.
- `activity_logs`: Trace of admin interactions (Uploads, Approvals).
- `student_name`: Master reference for mapping student identities during scans.

---
*Created with ❤️ for Academic Excellence.*
