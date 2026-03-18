import streamlit as st
import pdfplumber
import re
import pandas as pd
import io


st.set_page_config(
    page_title="AI/DS Result Converter",
    page_icon="📊",
    layout="wide"
)

# --- STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #00875A; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA DICTIONARIES ---
grade_points = {
    "O": 10, "S": 10, "A+": 9, "A": 8, "B+": 7,
    "B": 6, "C": 5, "U": 0, "UA": 0,
    "W": 0, "SA": 0, "WH": 0
}

syllabus = {
    "BS3171": ("Physics & Chemistry Lab", 2), "CY3151": ("Engineering Chemistry", 3),
    "GE3151": ("Python Programming", 3), "GE3152": ("Heritage of Tamils", 1),
    "GE3171": ("Python Lab", 2), "GE3172": ("English Lab", 1),
    "HS3151": ("Professional English I", 3), "MA3151": ("Matrices & Calculus", 4),
    "PH3151": ("Engineering Physics", 3), "AD3251": ("Data Structures", 3),
    "AD3271": ("DS Lab", 2), "BE3251": ("BEEE", 3),
    "GE3251": ("Engineering Graphics", 4), "GE3252": ("Tamils & Technology", 1),
    "GE3271": ("Engg Practices Lab", 2), "GE3272": ("Communication Lab", 2),
    "HS3251": ("Professional English II", 2), "MA3251": ("Statistics", 4),
    "PH3256": ("Physics for IS", 3), "AD3301": ("Data Exploration", 4),
    "AD3311": ("AI Lab", 1.5), "AD3351": ("Algorithms", 4),
    "AD3381": ("DB Lab", 1.5), "AD3391": ("DBMS", 3),
    "AL3391": ("Artificial Intelligence", 3), "CS3351": ("DPCO", 4),
    "GE3361": ("Professional Dev", 1), "MA3354": ("Discrete Maths", 4),
    "AD3491": ("Data Science", 3), "AL3451": ("Machine Learning", 3),
    "AL3452": ("Operating Systems", 4), "CS3591": ("Computer Networks", 4),
    "GE3451": ("Environmental Science", 2), "MA3391": ("Probability", 4),
    "AD3501": ("Deep Learning", 3), "AD3511": ("DL Lab", 2),
    "AD3512": ("Internship", 2), "CCS334": ("Big Data", 3),
    "CCS335": ("Cloud Computing", 3), "CCW331": ("Business Analytics", 3),
    "CS3551": ("Distributed Computing", 3), "CW3551": ("Data Security", 3),
    "CCS332": ("App Dev", 3), "CCS341": ("Data Warehousing", 3),
    "CCS345": ("Ethics AI", 3), "CCS371": ("Video Editing", 3),
    "CS3661": ("IoT Lab", 2), "CS3691": ("IoT", 4),
    "SB8051": ("Naan Mudhalvan", 2), "AI3021": ("IT Agriculture", 3),
    "GE3751": ("Management", 3), "GE3791": ("Human Values", 2),
    "NM1117": ("Naan Mudhalvan", 2), "OGI352": ("GIS", 3),
    "AD3811": ("Project", 10)
}

def get_sem_subjects(sem):
    mapping = {
        1: ["BS3171","CY3151","GE3151","GE3152","GE3171","GE3172","HS3151","MA3151","PH3151"],
        2: ["AD3251","AD3271","BE3251","GE3251","GE3252","GE3271","GE3272","HS3251","MA3251","PH3256"],
        3: ["AD3301","AD3311","AD3351","AD3381","AD3391","AL3391","CS3351","GE3361","MA3354"],
        4: ["AD3491","AL3451","AL3452","CS3591","GE3451","MA3391"],
        5: ["AD3501","AD3511","AD3512","CCS334","CCS335","CCW331","CS3551","CW3551"],
        6: ["CCS332","CCS341","CCS345","CCS371","CS3661","CS3691","SB8051"],
        7: ["AI3021","GE3751","GE3791","NM1117","OGI352"],
        8: ["AD3811"]
    }
    return mapping.get(sem, [])

# --- LOGIC ---
def process_pdf(pdf_file):
    student_records = {}
    current_sem = 0
    current_header_subjects = []
    CODE_REGEX = re.compile(r"^[A-Z]{2,3}\d{3,4}$")

    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    
    lines = text.split("\n")
    for line in lines:
        if "Semester No." in line:
            match = re.search(r"Semester No.\s*:\s*(\d+)", line)
            if match:
                current_sem = int(match.group(1))
                current_header_subjects = []
            continue
        
        strip_line = line.strip()
        if not re.match(r"^\d{10,12}", strip_line):
            tokens = strip_line.split()
            codes = [w for w in tokens if CODE_REGEX.match(w) or w in syllabus]
            if len(codes) >= 2:
                current_header_subjects = codes
            continue

        parts = strip_line.split()
        reg_no = parts[0]
        subjects_to_use = current_header_subjects if current_header_subjects else get_sem_subjects(current_sem)
        
        grades = []
        name_parts = []
        for p in reversed(parts[1:]):
            if len(grades) < len(subjects_to_use) and p in grade_points:
                grades.insert(0, p)
            else:
                name_parts.insert(0, p)
        
        name = " ".join([w for w in name_parts if not CODE_REGEX.match(w)])
        total_credits, total_points = 0, 0
        limit = min(len(subjects_to_use), len(grades))
        
        for i in range(limit):
            code = subjects_to_use[i]
            grade = grades[i]
            _, credits = syllabus.get(code, ("Unknown", 3))
            if grade not in ["UA", "W", "WH", "SA"]:
                total_credits += credits
                total_points += grade_points.get(grade, 0) * credits
        
        gpa = round((total_points / total_credits) + 1e-9, 2) if total_credits > 0 else 0.00
        if reg_no not in student_records: student_records[reg_no] = {}        
        student_records[reg_no][current_sem] = {"name": name, "gpa": gpa}

    final_rows = []
    for reg_no, sem_data in student_records.items():
        max_sem = max(sem_data.keys())
        data = sem_data[max_sem]
        batch_year = "20" + str(reg_no)[4:6] if len(str(reg_no)) >= 6 else "Unknown"
        final_rows.append({
            "Batch": batch_year, "Semester": max_sem, 
            "Reg No": reg_no, "Name": data["name"], "GPA": data["gpa"]
        })
    return pd.DataFrame(final_rows).sort_values(by=["Batch", "Semester", "Reg No"])

# --- UI LAYOUT ---
st.sidebar.title("📌 Instructions")
st.sidebar.info("""
1. Upload the official Semester Result PDF.
2. The app will extract Registration No, Names, and calculate GPA.
3. Preview the results in the table.
4. Download as a formatted Excel file.
""")

st.title("🎓 Academic Performance Parser")
st.subheader("Transform PDF Results into Data Insights")

uploaded_file = st.file_uploader("Drop your PDF file here", type="pdf")

if uploaded_file:
    with st.spinner('⚙️ Analyzing PDF structure and calculating GPAs...'):
        try:
            df = process_pdf(uploaded_file)
            
            # SUCCESS METRICS
            col1, col2, col3 = st.columns(3)
            col1.metric("Students Found", len(df))
            col2.metric("Highest GPA", f"{df['GPA'].max():.2f}")
            col3.metric("Average GPA", f"{df['GPA'].astype(float).mean():.2f}")

            # DATA PREVIEW
            st.write("### 🔍 Data Preview")
            st.dataframe(df, use_container_width=True)

            # EXCEL GENERATION
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='GPA_Results')
            
            st.write("---")
            st.download_button(
                label="📥 Download Excel Report",
                data=output.getvalue(),
                file_name=f"Results_Summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.balloons()

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.info("Ensure the PDF matches the expected format.")
else:
    st.info("👋 Welcome! Please upload a PDF to get started.")
