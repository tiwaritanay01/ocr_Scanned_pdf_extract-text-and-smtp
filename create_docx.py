import sys
import subprocess
import urllib.request
import urllib.parse
import os

def install_and_import(package):
    try:
        import docx
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    finally:
        globals()["docx"] = __import__("docx")

install_and_import("python-docx")
from docx import Document
from docx.shared import Inches

def download_graphviz(dot_code, filename):
    url = 'https://quickchart.io/graphviz?format=png&graph=' + urllib.parse.quote(dot_code)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
            out_file.write(response.read())
        return filename
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return None

# Generate images
dot0 = """
digraph G {
  rankdir=LR;
  node [shape=box, style=filled, fillcolor=lightgrey]; Admin; Student;
  node [shape=circle, style=filled, fillcolor=white]; System [label="Online Result\\nProcessing &\\nDistribution System"];
  Admin -> System [label="Uploads Marksheets\\n(PDF/Excel)"];
  System -> Student [label="Personalized Result\\nEmail"];
}
"""
download_graphviz(dot0, "level0.png")

dot1 = """
digraph G {
  rankdir=TB;
  node [shape=box, style=filled, fillcolor=lightgrey]; Admin; Student; 
  node [shape=none, margin=0]; Database [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="4"><tr><td>MySQL Database</td></tr></table>>];
  node [shape=circle, style=filled, fillcolor=white, width=1.5];
  P1 [label="1.0\\nData\\nIngestion"];
  P2 [label="2.0\\nOCR &\\nPre-processing"];
  P3 [label="3.0\\nData\\nVerification"];
  P4 [label="4.0\\nResult\\nAggregation"];
  P5 [label="5.0\\nEmail\\nDispatch"];

  Admin -> P1 [label="PDF/Excel"];
  P1 -> P2 [label="Images/Spreadsheets"];
  P2 -> P3 [label="Extracted Marks"];
  P3 -> Database [label="Verified Data"];
  Database -> P4 [label="Student Records"];
  P4 -> P5 [label="Email Content"];
  P5 -> Student [label="Emails"];
}
"""
download_graphviz(dot1, "level1.png")

dot2 = """
digraph G {
  rankdir=TB;
  node [shape=circle, style=filled, fillcolor=white, width=1.5];
  P21 [label="2.1\\nPDF to Image\\nConversion"];
  P22 [label="2.2\\nImage\\nEnhancement"];
  P23 [label="2.3\\nGrid\\nDetection"];
  P24 [label="2.4\\nText\\nRecognition"];
  
  node [shape=none, style=empty];
  start [label="Image Blobs"];
  end [label="Raw Extracted Text"];

  start -> P21;
  P21 -> P22 [label="High-res Images"];
  P22 -> P23 [label="Enhanced Images"];
  P23 -> P24 [label="Cropped Cells"];
  P24 -> end;
}
"""
download_graphviz(dot2, "level2.png")

doc = Document()
doc.add_heading('Experiment No.06', 0)
doc.add_heading('A.1 Aim:', level=2)
doc.add_paragraph('Draw the Data Flow Diagram (DFD) for the selected Case Study using any open source tool.')
doc.add_heading('A.2 Prerequisite:', level=2)
doc.add_paragraph('Knowledge about requirement engineering processes of SDLC and requirement modelling.')
doc.add_heading('A.3 Outcome:', level=2)
doc.add_paragraph('After successful completion of this experiment, students will be able to: Model requirements of the project (software) using Data Flow Diagram (DFD).')
doc.add_heading('A.4 Theory:', level=2)
doc.add_heading('DATA FLOW DIAGRAM (DFD):', level=3)
doc.add_paragraph('- The data flow diagram is a graphical model of a system, which shows what are the various functions (activities) performed by the system and how data flows among various functions.')
doc.add_paragraph('- Each function is considered as a separate process.')
doc.add_paragraph('- A data flow diagram (DFD) is a graphical representation of the "flow" of data through an information system. DFDs can also be used for the visualization of data processing (structured design).')
doc.add_paragraph('- On a DFD, data items flow from an external data source or an internal data store to an internal data store or an external data sink, via an internal process.')
doc.add_paragraph('- A DFD provides no information about the timing of processes, or about whether processes will operate in sequence or parallel.')
doc.add_paragraph('- It is therefore quite different from a flowchart, which shows the flow of control through an algorithm, allowing a reader to determine what operations will be performed, in what order, and under what circumstances, but not what kinds of data will be input to and output from the system, nor where the data will come from and go to, nor where the data will be stored (all of which are shown on a DFD).')
doc.add_paragraph('- Data Flow diagrams (DFD) that help you model data flows and functional requirements for a designed system.')

doc.add_heading('Elements of Data Flow Diagram', level=3)
doc.add_paragraph('1. DATA STORE:-A data store is a holding place for information within the system')
doc.add_paragraph('2. PROCESS:-A process performs transformation or manipulation on input data and produces output data.')
doc.add_paragraph('3. ENTITY:-An entity is anything that interacts with the system and is a source or destination of a data.')
doc.add_paragraph('4. DATA FLOW:-A data flow shows the flow of information from its source to its destination.')
doc.add_paragraph('\n---\n')

doc.add_heading('PART B', level=1)
doc.add_paragraph('(PART B: TO BE COMPLETED BY STUDENTS)', style='Intense Quote')
doc.add_heading('B.1 Draw DFD of the selected mini-project up to level 2', level=2)
doc.add_paragraph('Selected Mini-Project: Online Result Generator & Distribution System')
doc.add_heading('Data Flow Diagram:', level=3)
doc.add_paragraph('The data flow diagram is a graphical representation of the flow of data in an information system. It is capable of depicting incoming data flow, outgoing data flow and stored data. The DFD does not mention anything about how data flows through the system.')

doc.add_heading('Zero Level Data flow Diagram(0 Level DFD) of Online Result Generator:', level=3)
doc.add_paragraph('High-Level Entities and process flow of the Online Result Generator:')
doc.add_paragraph('• Managing all the PDF/Excel Uploads')
doc.add_paragraph('• Managing all the Data Extractions (OCR)')
doc.add_paragraph('• Managing all the Data Verification')
doc.add_paragraph('• Managing all the Student Records')
doc.add_paragraph('• Managing all the Result Emails')

if os.path.exists("level0.png"):
    doc.add_picture("level0.png", width=Inches(5))
    doc.add_paragraph('Level 0 DFD or Context level DFD', style='Caption')

doc.add_heading('First Level Data flow Diagram(1st Level DFD) of Online Result Generator:', level=3)
doc.add_paragraph('Main entities and output of First Level DFD (1st Level DFD):')
doc.add_paragraph('• Processing Admin Upload records and generate data ingestion')
doc.add_paragraph('• Processing Document records and generates extracted marks')
doc.add_paragraph('• Processing Extraction records and generates verified data')
doc.add_paragraph('• Processing Student records and generates aggregated results')
doc.add_paragraph('• Processing Results records and generate dispatched emails')

if os.path.exists("level1.png"):
    doc.add_picture("level1.png", width=Inches(4))
    doc.add_paragraph('Level 1 DFD', style='Caption')

doc.add_heading('Second Level Data flow Diagram(2nd Level DFD) of Online Result Generator:', level=3)
doc.add_paragraph('Low-level functionalities of Online Result Generator (OCR Process):')
doc.add_paragraph('• Admin manages PDF to Image Conversion')
doc.add_paragraph('• System enhances image records via deskewing')
doc.add_paragraph('• System detects grid details of tables')
doc.add_paragraph('• System extracts text details via text recognition')

if os.path.exists("level2.png"):
    doc.add_picture("level2.png", width=Inches(3))
    doc.add_paragraph('Level 2 DFD for OCR Process of level 1 DFD', style='Caption')

doc.add_heading('B.2 Conclusion:', level=2)
doc.add_paragraph('Data-flow diagrams can be a powerful tool for not only making business decisions but to be used by accounting in many different areas. The simple symbols used make it easy to follow the flow of the charts to understand how decisions are reached or processed.')
doc.add_paragraph('Data flow analysis has proved itself to be an essential technique in the grand scheme of developing custom software solutions. For our Online Result Generator System, DFDs greatly improve conceptual clarity for understanding the complex automated pipeline. It visually breaks down the dual-mode ingestion, the computer vision extraction process, the admin verification ledger, and the final SMTP distribution logic. It helps show the true scope of the project, ensuring all data streams between the Admin, the OCR pipeline, the database, and the Student are securely mapped, which is almost always bigger than originally anticipated.')

doc.add_heading('B.3 Question of Curiosity', level=2)
doc.add_paragraph('1. What do you mean by requirement modelling? Why is it required?')
doc.add_paragraph('Answer: Requirement modelling is the process of translating and representing raw, often unstructured requirements into standardized graphical and textual formats (such as Data Flow Diagrams, Use Case Diagrams, and ER Diagrams).')
doc.add_paragraph('It is required because it:\n- Simplifies complex system information and acts as a clear blueprint for system design.\n- Bridges the communication gap between technical developers and non-technical stakeholders.\n- Helps identify missing, overlapping, or conflicting requirements early in the Software Development Life Cycle (SDLC) before coding begins.')

doc.add_paragraph('2. List of various requirement gathering techniques.')
doc.add_paragraph('Answer:\n- Interviews: Direct one-on-one or group discussions with stakeholders.\n- Surveys and Questionnaires: Gathering standardized feedback from a large group.\n- Document Analysis: Studying existing documents.\n- Observation / Job Shadowing: Watching users perform their tasks to understand workflows.\n- Brainstorming: Idea generation sessions with the team.\n- Prototyping: Creating early models of the UI to get feedback.\n- JAD (Joint Application Development) Sessions: Collaborative workshops with stakeholders and developers.')

doc.save('Experiment No 6_Completed_With_Diagrams.docx')
print('Successfully saved Experiment No 6_Completed_With_Diagrams.docx')
