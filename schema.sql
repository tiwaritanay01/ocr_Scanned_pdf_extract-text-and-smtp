-- ========================================================
-- Online Result Processing & Distribution System
-- Full Database Schema & Seed Data
-- ========================================================

CREATE DATABASE IF NOT EXISTS student_results;
USE student_results;

-- 1. Admins Table
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
);

-- 2. Audit Activity Logs
CREATE TABLE IF NOT EXISTS activity_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(100),
    action_type VARCHAR(50),
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Uploaded Result Files Tracking
CREATE TABLE IF NOT EXISTS result_files (
    file_id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    format_type VARCHAR(50) DEFAULT 'PDF',
    status VARCHAR(20) DEFAULT 'pending',
    admin_name VARCHAR(100),
    college_name VARCHAR(150)
);

-- 4. Email Distribution Logs
CREATE TABLE IF NOT EXISTS email_logs (
    mail_id INT AUTO_INCREMENT PRIMARY KEY,
    student_email VARCHAR(150) NOT NULL,
    student_name VARCHAR(150),
    sent_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent',
    subject_semester VARCHAR(50)
);

-- 5. Student Master Directory
CREATE TABLE IF NOT EXISTS student_name (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ern VARCHAR(50),
    student_name VARCHAR(255) UNIQUE,
    student_email VARCHAR(255)
);

-- 6. Detailed Subject-wise Marks
CREATE TABLE IF NOT EXISTS detailed_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ern VARCHAR(255),
    student_name VARCHAR(255),
    semester VARCHAR(50),
    subject_marks JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_student_sem (ern, student_name, semester)
);

-- 7. FE/BE Summary Results
CREATE TABLE IF NOT EXISTS fe_be_results (
    ern VARCHAR(255) NOT NULL PRIMARY KEY,
    seat_no VARCHAR(50),
    status VARCHAR(10),
    gpa FLOAT,
    screenshot LONGTEXT,
    semester VARCHAR(20)
);

-- 8. Student Performance Analytics
CREATE TABLE IF NOT EXISTS student_performance (
    performance_id INT AUTO_INCREMENT PRIMARY KEY,
    ern VARCHAR(50),
    student_name VARCHAR(255),
    pointer DECIMAL(4,2),
    semester VARCHAR(20),
    department VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY student_sem (ern, semester)
);

-- ========================================================
-- Seed Default Admins
-- dept_admin   / admin123  (SHA-256: 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9)
-- super_admin  / super123  (SHA-256: 4fca4b4cb7df473d09a0f02377a0302fa9ee24db8969b76e27606e921d7b309f)
-- ========================================================
INSERT IGNORE INTO admins (admin_id, username, password, name, email, department, college, university, role, status)
VALUES 
(1, 'dept_admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Department Head', 'dept@college.edu', 'Computer Engineering', 'Vasantdada Patil Pratishthan\'s College of Engineering', 'University of Mumbai', 'staff', 'active'),
(2, 'super_admin', '4fca4b4cb7df473d09a0f02377a0302fa9ee24db8969b76e27606e921d7b309f', 'System Admin', 'admin@system.com', 'Central Admin', 'Vasantdada Patil Pratishthan\'s College of Engineering', 'University of Mumbai', 'superadmin', 'active');


-- ========================================================
-- Student Master Names Seed
-- ========================================================
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('ALLU SANTOSH CHINTAMANI KAMALINI', 'tiwaritanay01@gmail.com');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('AMBRE SANKET VILAS KALPANA', 'anonymousthegreat750@gmail.com');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('ARALI SINDHU SURESH BHUVANESHWAR', 'vu1f2425005@pvppcoe.ac.in');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('ARDEKAR OMKAR PRAKASH POOJA', 'tiwaritanay01@gmail.com');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('ARMORIKAR ISHAN DINESH JYOTI', 'anonymousthegreat750@gmail.com');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BADGUJAR SUBODH SURESH SEEMA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BALBALE AMAAN IMTIYAZ VASMIN', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BAMANE SAIRAJ CHANDRAKANT SHOBHA', 'vu1f2425005@pvppcoe.ac.in');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BANE JANHAVI CHANDRASHEKHAR', 'tiwaritanay01@gmail.com');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BANSODE SHREYAS ARUN SWATI', 'anonymousthegreat750@gmail.com');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BAVALEKAR AADESH VIJAY', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BELNEKAR PRACHI PRABHAKAR POOJA', 'vu1f2425005@pvppcoe.ac.in');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BHALEKAR ATHARVA DHANAJI SNEHA', 'anonymousthegreat750@gmail.com');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BHAMID SATYAM JANARDAN', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BODKE OMKAR SOMNATH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('BORKAR SMIT SURESH KUMAR', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHAKRANARAYAN TEJAS PRADIP', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHANDORKAR NIKHIL VINAYAK TRUPTI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHAUBEY RISHABH KUMAR', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHAUDHARI PIYUSH ARVIND', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHAUDHARI VAISHANAVI AJAY', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHAVAN DIVYA RAVINDRA SNEHAL', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHITAPUR SUNIL MANOHAR NAGMA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHOWDHURY HIYA SUBASH ROOPA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('DALVI PARTH AJAY AASTHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('DAMRE NIKHIL RAJESH RIYA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('DAREKAR MAHALAKSHMI SHASHIKANT NIRMALA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('DEVKATE SWAPNIL MADHUKAR', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('DHUMAL ABHISHEK', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('DIXIT ASHISH HEMENDRA SHARMA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('DUBEY NISHANT RAMCHANDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAIKWAD PRATHMESH ASHOK', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAIKWAD SHREYAS SANDIP RASIKA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAJBE PRAJWAL PRAVIN BHAWNA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GANGAR JANVI VIPUL', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAOKAR SARVEDNYA NIRANJAN', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GARJE SUYASH RAJENDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAUD VIJAY NANDLAL SANDHYA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAVIT ATUL SURESH VIJAYA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAWADE PRANAY AMRUT RUPALI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAWADE VEDANT ROHIDAS', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GAWDE VINAYAK ANIL', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GHADGE AMEY RAJENDRA KUMAR', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GHARAT PRANIT PRABHAKAR', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GHAWALE TEJASWINI GUNAJI SNEHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GHOLAP SUSHANT DILIP MANISHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GHORPADE YASHANKUSH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GHUGARE SWAPNIL RAMESH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GOSAVI BHAVIK PRAKASH PRIYA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GUPTA ARYAN SANTOSH ASHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GUPTA AZAD AMLESH USHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GUPTA SAMAY SANTOSH SUSHMA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('GUPTA SHIVAM SURESHKUMAR', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('HOWALE SIDDHESH RAJENDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('HULE SAKSHI SUVARNA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('JADHAV ADVAITYA SHARDUL', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('JADHAV BHOOMI SANJAY SUVIDHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('JADHAV PRATHAMESH VINOD', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('JAISWAL OM PRAMOD GEETA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('JAMDADE PRERANA JOTIRAM RUPALI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('JHA HARSH RAVINDRA KIRAN', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('JUWATKAR SEJALANAND', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KADAM APOORVA PRAVIN PREETI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KADAM PRASAD PREMANAND', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KAIRAMKONDA ROHIT SURESH VANI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KAIRAMKONDA SHREYA PRAVIN', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KAMBLE ATHRAV NITIN NEHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KAMBLE DARSHAN SUNIL ARCHANA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KAMBLE MITALI GANESH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KANOJIYA AJAYMOHAN JILEDAR USHADEVI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KAPSE ARCHIT KAUR HARVINDER', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KAPSE HARSHAD BALIRAM USHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KARBELKAR SAHEEM HASANMIYA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KARVANDE PRIYAL PRASHANT PUSHPA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KASBE ANTARA BALU ARCHANA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KHAN HAMDAN ABDUL WAHID SHAFGUFTA BANO', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KITKE NITUSHKA VILAS', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KOKULLA KARTIK LAXMINARAYANA KAVITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('KOLPE ATHARV SUKHADE VAISHALI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('LAD PAYAL NANDKUMAR NAMRATA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('LAD SANIKA VIVEKANAND VIDYA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('LOKHANDE DARSHAN PRAVIN JAYASHRI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MACHHI KAUSTUBH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MAHAJAN AMIT VIJAY JYOTI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MAHAJAN DIVYA PRAMOD NISHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MANDPE PRAGYA SATYENDRA PRATIBHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MANE PRATIKSHA SUBHASH SAVITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MANE SUJAL SAMBHAJI SUREKHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MANEGOPALE VARAD PARMESHWAR ARCHANA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MAPARI MAHI SHARAFAT', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MAURYA SAHIL HARISHCHANDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MAYATRA DEVANSH JITENDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MEJARI VISHAL GANESH GAYATRI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MHATRE NISHANT SURENDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MHATRE SHRIYASH SANTOSH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MISAL SIDDHARTH SANJAY', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MITRA NILARGHA PRADIP TUHINA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MOHITE HARSHAD SURESH SANGITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MOLAWADE PRANAV SUNIL VARSHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MORAJKAR AYUSH SANJAY REKHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MORE ABHISHEK JIVAN ANITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MOREPATIL ARYAN YASHWANT', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('MOURYA RITESH SANTOSH VANDANA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('NAGPURE ASHWAYU RAVINDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('NAIK SHRIRAJ NILESH JANHAVI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('NALAWADE AARYAN SUNIL JAYSHREE', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('NANDANWAR SOHAM KRISHNA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('NICHAL DHANASHREE NANASAAHEB DIPALI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('OHOL PRATIK MAHENDRA MAYAVATI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PACHARKAR AMEY MAHENDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PANCHAL MEET KAMLESH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PARAB DURVESH SANDIP SHRUTI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PARAB SUMAANT', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PATADE PRATHAMESH SANDIP SAKSHI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PATIL RIDDHI NILESH MANISHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PATIL TUSHAR SUBHASH MANISHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PATIL VAISHNAV SHYAM SHUBHADA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PATIL VIKRANT VINOD VAISHALI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PATIL VINAYAK KAKASAHEB', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PATIVE EKATA RAJKUMAR SUSHILA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PAWAR HRUTUJA VILAS SANGEETA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PAWAR SRUSHTI SANDIP MANISHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('PINGALE ADITYA MAHADEV KAVITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('RAJAM SOHAM RAJENDRA RASIKA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('RANA AKANSHA VIJAY', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('RANGREZ HASSAN RAZA AKHTAR HUSSAIN SHAHER BANO', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('RANJANE SMITA SUBHASH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('RATHOD ARYAN ASHOK RANJANA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('RIZVI AHMED ABBAS NASIR HUSSAIN', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SAINI KRITIKA MANOJKUMAR', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SANGALE PRACHI RAVINDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SAVANE SHEETAL SAKHARAM', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SAWANT RUSHI RAJESH MANISHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SAWANT SUMEDH SAMIR SMITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SAYYED SUBIYA KALIM AYESHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHAH MOHAMMED ARSHADAZAM', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHAIKH HAMZA ZUBAIR KAUSAR', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHELAR DISHA SANJAY APARNA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHINDE ABHIJIT AMOL SAROJ', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHINDE SAMAR MANOJ RACHANA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHINDE SARANG RAJENDRA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHINDE SARVESH SHASHIKANT', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHINDE VISHAL BALABHAU', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHINGARE PARITOSH BALKRISHNA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SHRIVASTAVA DAMINI SHYAM', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SIDAM ROHINI DHARMAJI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SINGH KARTIKEY PRADEEP SARITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SIRVI HARISHKUMAR KERARA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SONAWANE PIYUSH ASHOK SARIKA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SONAWANE SAGAR SOMANATH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SONAWANE SAIRAJ BHIKAJI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SONI YASH DINESH BHAGAWATI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('SUTAR OM LAXMAN POURNIMA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('TADUKA RAKESH YELLAIAH', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('TAMSE PRATHA PRAVIN POOJA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('TARADE PRANIT PRADEEP SUSHMA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('TASHI MEGHAN SUHAS', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('TAVAREJ PRANAV SANJAY VEENA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('THAKRE ANANYA NILESH ARTI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('THOMBARE SIDDHANT DHANAJI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('TIWARI ABHAY BRIJENDRA SANJU', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('TUPE ANISH DEEPESH PRESHITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('UPADHYAY DEEP ASHISH SONAL', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('UPADHYAY HARSHIT AJAY SANJU', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('URANKAR NIRAV VIKRANT SUVERNA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('VICHARE KARTIK SURYAKANT', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('WAGH ANIKET MANGESH SARALA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('WAKSHE PRATHMESH TANAJI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('WARANG KUNAL YASHWANT', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('WARUDE YASH PUNAMCHAND JYOTI', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('YADAV HARSH JAYSHANKAR ANITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('YADAV RANJANKUMAR VIJAY NISHA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('YADAV SHUBHAM DILIPKUMAR VANITA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('YEOLE OM SHYAMKANT KALPANA', 'None');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHAVAN VIGHNESH NITIN R', 'tiwaritanay01@gmail.com');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('ANUSHKA AVINASH PANDIT R', 'vu1f2425005@pvppcoe.ac.in');
INSERT IGNORE INTO student_name (student_name, student_email) VALUES ('CHAITANYA BHANUDAS TALAVNEKAR', 'anonymousthegreat750@gmail.com');