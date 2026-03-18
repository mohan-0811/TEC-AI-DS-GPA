import streamlit as st
import pdfplumber
import re
import pandas as pd
import io
from collections import defaultdict

# --- CONFIGURATION ---
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
    "W": 0, "SA": 0, "WH": 0, "AB": 0
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
    """Get subjects for a specific semester - ordered by typical PDF appearance"""
    mapping = {
        1: ["HS3151", "MA3151", "PH3151", "CY3151", "GE3151", "GE3152", "BS3171", "GE3171", "GE3172"],
        2: ["MA3251", "PH3256", "BE3251", "AD3251", "GE3251", "GE3252", "HS3251", "GE3271", "AD3271", "GE3272"],
        3: ["MA3354", "AD3391", "AD3351", "CS3351", "AL3391", "AD3301", "GE3361", "AD3381", "AD3311"],
        4: ["MA3391", "CS3591", "AL3452", "AL3451", "AD3491", "GE3451"],
        5: ["AD3501", "CCS334", "CCS335", "CCW331", "CS3551", "CW3551", "AD3511", "AD3512"],
        6: ["CCS332", "CCS341", "CCS345", "CCS371", "CS3691", "CS3661", "SB8051"],
        7: ["AI3021", "OGI352", "GE3751", "GE3791", "NM1117"],
        8: ["AD3811"]
    }
    return mapping.get(sem, [])

def extract_grades_from_line(line, expected_subjects):
    """Extract grades from student line more robustly"""
    parts = line.strip().split()
    if len(parts) < 2 or not re.match(r"^\d{10,12}", parts[0]):
        return None, None
    
    reg_no = parts[0]
    
    # Extract all potential grades from the end of the line
    grades = []
    name_parts = []
    
    for part in reversed(parts[1:]):
        if part in grade_points:
            grades.insert(0, part)
        else:
            name_parts.insert(0, part)
    
    # Clean name (remove any stray codes)
    name = " ".join([p for p in name_parts if not re.match(r"^[A-Z]{2,3}\d{3,4}$", p)])
    
    return reg_no, {"name": name, "grades": grades[:len(expected_subjects)]}

def calculate_gpa(reg_no, sem, grades, subjects):
    """Calculate GPA for given semester"""
    total_credits = 0
    total_points = 0
    
    for i, (code, grade) in enumerate(zip(subjects, grades)):
        if code in syllabus and grade in grade_points:
            _, credits = syllabus[code]
            points = grade_points[grade]
            
            # Skip failed/withdrawn subjects for GPA calculation
            if grade not in ["U", "UA", "W", "WH", "SA", "AB"]:
                total_credits += credits
                total_points += points * credits
    
    gpa = round(total_points / total_credits, 2) if total_credits > 0 else 0.00
    return gpa

def process_pdf(pdf_file):
    student_records = defaultdict(dict)
    CODE_REGEX = re.compile(r"^[A-Z]{2,3}\d{3,4}$")
    
    with pdfplumber.open(pdf_file) as pdf:
        full_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]
    
    current_sem = 0
    debug_info = []  # For troubleshooting
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detect semester
        if "Semester No." in line or "SEMESTER" in line.upper():
            sem_match = re.search(r"(?:Semester|SEM)\s*(?:No\.?|NO)\s*[:\-]?\s*(\d+)", line, re.IGNORECASE)
            if sem_match:
                current_sem = int(sem_match.group(1))
                debug_info.append(f"Found semester {current_sem}")
        
        # Skip if not a student record line
        if not re.match(r"^\d{10,12}", line):
            i += 1
            continue
        
        # Get expected subjects for this semester
        expected_subjects = get_sem_subjects(current_sem)
        if not expected_subjects:
            debug_info.append(f"No subjects found for semester {current_sem}")
            i += 1
            continue
        
        # Extract student data
        reg_no, student_data = extract_grades_from_line(line, expected_subjects)
        if reg_no and student_data:
            grades = student_data["grades"]
            gpa = calculate_gpa(reg_no, current_sem, grades, expected_subjects)
            
            student_records[reg_no][current_sem] = {
                "name": student_data["name"],
                "gpa": gpa,
                "subjects_used": expected_subjects[:len(grades)],
                "grades_found": grades
            }
            debug_info.append(f"Processed {reg_no}: GPA {gpa} for sem {current_sem}")
        
        i += 1
    
    # Create final dataframe
    final_rows = []
    for reg_no, sem_data in student_records.items():
        # Use highest semester available
        max_sem = max(sem_data.keys())
        data = sem_data[max_sem]
        batch_year = "20" + str(reg_no)[4:6] if len(str(reg_no)) >= 6 else "Unknown"
        
        final_rows.append({
            "Batch": batch_year,
            "Semester": max_sem,
            "Reg No": reg_no,
            "Name": data["name"],
            "GPA": data["gpa"],
            "Subjects Used": ", ".join(data["subjects_used"][:3]) + "..." if len(data["subjects_used"]) > 3 else ", ".join(data["subjects_used"])
        })
    
    df = pd.DataFrame(final_rows).sort_values(by=["Batch", "Semester", "Reg No"])
    
    # Show debug info in expander
    with st.expander("🔧 Debug Info (Click to expand)"):
        st.write("Processing log:")
        for info in debug_info[-20:]:  # Last 20 entries
            st.write(info)
        st.info(f"Total students processed: {len(df)}")
    
    return df

# --- UI LAYOUT ---
st.sidebar.title("📌 Instructions")
st.sidebar.info("""
1. Upload the official Semester Result PDF.
2. Works for **ALL semesters (1-8)** with improved parsing.
3. Fixed grade-subject alignment issues.
4. Preview results and download Excel.
""")

st.title("🎓 Academic Performance Parser")
st.subheader("✅ Fixed for ALL Semesters (1-8)")

uploaded_file = st.file_uploader("Drop your PDF file here", type="pdf")

if uploaded_file:
    with st.spinner('⚙️ Processing PDF with improved semester detection...'):
        try:
            df = process_pdf(uploaded_file)
            
            if df.empty:
                st.warning("No student data found. Please check if PDF format matches expected structure.")
            else:
                # SUCCESS METRICS
                col1, col2, col3 = st.columns(3)
                col1.metric("Students Found", len(df))
                col2.metric("Highest GPA", f"{df['GPA'].max():.2f}")
                col3.metric("Average GPA", f"{df['GPA'].mean():.2f}")

                # DATA PREVIEW
                st.write("### 🔍 Results Preview")
                st.dataframe(df[["Batch", "Semester", "Reg No", "Name", "GPA"]], use_container_width=True)

                # EXCEL GENERATION
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='GPA_Results')
                
                st.write("---")
                st.success("✅ Processing complete!")
                st.download_button(
                    label="📥 Download Excel Report",
                    data=output.getvalue(),
                    file_name=f"Results_S{int(df['Semester'].max())}-{len(df)}students.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.balloons()

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("💡 Tips:\n• Ensure PDF is official result sheet\n• Try different PDF if issue persists")
else:
    st.info("👋 Upload a PDF to analyze semester results!")
