import streamlit as st
import pdfplumber
import re
import pandas as pd
import io
st.set_page_config(
    page_title="AI/DS Result Converter",
    page_icon="🎓",
    layout="wide"
)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #00875A; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- STRICT GRADE POINTS ---
grade_points = {
    "O": 10, "S": 10, "0": 10,
    "A+": 9, "A": 8, "B+": 7,
    "B": 6, "C": 5, 
    "U": 0, "RA": 0, "UA": 0, "AB": 0, "SA": 0,
    "W": 0, "WH": 0, "WD": 0, "NE": 0
}
syllabus_info = {
    # Semester 1 (R2021)
    "BS3171": (2, 1), "CY3151": (3, 1), "GE3151": (3, 1), "GE3152": (1, 1), 
    "GE3171": (2, 1), "GE3172": (1, 1), "HS3151": (3, 1), "MA3151": (4, 1), "PH3151": (3, 1),
    # Semester 2
    "AD3251": (3, 2), "AD3271": (2, 2), "BE3251": (3, 2), "GE3251": (4, 2), "GE3252": (1, 2), 
    "GE3271": (2, 2), "GE3272": (2, 2), "HS3251": (2, 2), "MA3251": (4, 2), "PH3256": (3, 2),
    # Semester 3
    "AD3301": (4, 3), "AD3311": (1.5, 3), "AD3351": (4, 3), "AD3381": (1.5, 3), "AD3391": (3, 3), 
    "AL3391": (3, 3), "CS3351": (4, 3), "GE3361": (1, 3), "MA3354": (4, 3),
    # Semester 4
    "AD3411": (2, 4), "AD3491": (3, 4), "AL3451": (3, 4), "AL3452": (4, 4), "AL3461": (2, 4), 
    "CS3591": (4, 4), "GE3451": (2, 4), "MA3391": (4, 4),
    # Semester 5
    "AD3501": (3, 5), "AD3511": (2, 5), "AD3512": (2, 5), "CCS334": (3, 5), "CCS335": (3, 5), 
    "CCW331": (3, 5), "CS3551": (3, 5), "CW3551": (3, 5),
    # Semester 6
    "CCS332": (3, 6), "CCS341": (3, 6), "CCS345": (3, 6), "CCS371": (3, 6), "CS3661": (2, 6), 
    "CS3691": (4, 6), "SB8051": (2, 6),
    # Semester 7
    "AI3021": (3, 7), "GE3751": (3, 7), "GE3791": (2, 7), "NM1117": (2, 7), "OGI352": (3, 7),
    # Semester 8
    "AD3811": (10, 8),
    # 2025 Regulation
    "CS25C01": (3, 1), "CS25C03": (2, 1), "CY25C01": (3, 1), "EN25C01": (3, 1), "MA25C01": (4, 1), 
    "ME25C04": (3, 1), "PH25C01": (3, 1), "UC25A01": (1, 1), "UC25A02": (1, 1), "UC25H01": (2, 1)
}
def process_pdf(pdf_file):
    student_records = {}
    global_col_map = {} 
    
    SUBJECT_REGEX = re.compile(r"^[A-Z]{2,4}\d{2,4}[A-Z]?\d{0,2}$")

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            if not words: continue
            
            words_sorted = sorted(words, key=lambda w: w['top'])
            lines = []
            current_line = []
            current_top = None
            
            for w in words_sorted:
                if current_top is None:
                    current_top = w['top']
                    current_line.append(w)
                elif abs(w['top'] - current_top) <= 5: 
                    current_line.append(w)
                else:
                    lines.append(sorted(current_line, key=lambda x: x['x0']))
                    current_line = [w]
                    current_top = w['top']
            if current_line:
                lines.append(sorted(current_line, key=lambda x: x['x0']))
                
            skip_until = -1
            for i in range(len(lines)):
                if i < skip_until: continue
                    
                line = lines[i]
                text = " ".join([w['text'] for w in line]).upper()
                if "SUBJECT" in text and "CODE" in text:
                    header_words = []
                    header_words.extend(lines[i])
                    j = i + 1
                    
                    while j < len(lines):
                        j_text = " ".join([w['text'] for w in lines[j]]).upper()
                        if "REG" in j_text and "NUMBER" in j_text:
                            header_words.extend(lines[j]) 
                            j += 1
                            break
                        elif any(re.match(r"^\d{10,12}$", w['text']) for w in lines[j]):
                            break  
                        else:
                            header_words.extend(lines[j])
                            j += 1
                            
                    skip_until = j
                    
                    ignore_texts = {"SUBJECT", "CODE", "->", "REG.", "NUMBER", "STUD.", "NAME", "GRADE", "MARKS", "REG", "REGNUMBER"}
                    valid_header_words = [w for w in header_words if w['text'].upper().strip() not in ignore_texts]
                    
                    cols = []
                    for w in valid_header_words:
                        center_x = (w['x0'] + w['x1']) / 2
                        placed = False
                        for col in cols:
                            if abs(col['x'] - center_x) < 20: 
                                col['words'].append(w)
                                col['x'] = (col['x'] + center_x) / 2 
                                placed = True
                                break
                        if not placed:
                            cols.append({'x': center_x, 'words': [w]})
                            
                    temp_col_map = {}
                    for col in cols:
                        col['words'].sort(key=lambda w: w['top'])
                        raw_text = "".join([w['text'].strip() for w in col['words']]).upper()
                        clean_text = raw_text.replace("GRADE", "").replace("MARKS", "")
                        
                        match = re.search(SUBJECT_REGEX, clean_text)
                        if match:
                            temp_col_map[col['x']] = match.group()
                        else:
                            for code in syllabus_info.keys():
                                if code in clean_text:
                                    temp_col_map[col['x']] = code
                                    break
                                    
                    if len(temp_col_map) > 0:
                        global_col_map = temp_col_map
                first_word = line[0]['text'].strip()
                if re.match(r"^\d{10,12}$", first_word) and global_col_map:
                    reg_no = first_word
                    min_subj_x = min(global_col_map.keys()) - 25
                    
                    name_words = []
                    grade_words = []
                    
                    for w in line[1:]:
                        if w['x0'] < min_subj_x:
                            name_words.append(w['text'])
                        else:
                            grade_words.append(w)
                            
                    name = " ".join(name_words) if name_words else "Unknown"
                    
                    if reg_no not in student_records:
                        student_records[reg_no] = {"name": name, "grades": {}}
                        
                    for gw in grade_words:
                        g_center = (gw['x0'] + gw['x1']) / 2
                        closest_col_x = None
                        min_dist = float('inf')
                        
                        for cx in global_col_map.keys():
                            dist = abs(cx - g_center)
                            if dist < min_dist:
                                min_dist = dist
                                closest_col_x = cx
                                
                        if min_dist < 30: 
                            subj = global_col_map[closest_col_x]
                            grade_val = gw['text'].replace(' ', '').upper().strip()
                            if grade_val == "0": grade_val = "O"
                            
                            if grade_val in grade_points:
                                student_records[reg_no]["grades"][subj] = grade_val
    cohort_max_sem = {}
    for reg_no, data in student_records.items():
        joining_year = "20" + str(reg_no)[4:6] if len(str(reg_no)) >= 6 else "Unknown"
        valid_sems = [syllabus_info[code][1] for code in data["grades"] if code in syllabus_info]
        if valid_sems:
            max_s = max(valid_sems)
            if joining_year not in cohort_max_sem:
                cohort_max_sem[joining_year] = max_s
            else:
                cohort_max_sem[joining_year] = max(cohort_max_sem[joining_year], max_s)

    final_rows = []
    for reg_no, data in student_records.items():
        joining_year = "20" + str(reg_no)[4:6] if len(str(reg_no)) >= 6 else "Unknown"
        valid_sems = [syllabus_info[code][1] for code in data["grades"] if code in syllabus_info]
        if not valid_sems: continue 
            
        target_sem = max(valid_sems)
        expected_current_sem = cohort_max_sem.get(joining_year, target_sem)
        if target_sem < expected_current_sem: continue
        
        total_credits = 0
        total_points = 0
        
        for code, grade in data['grades'].items():
            if code in syllabus_info:
                credits, subject_sem = syllabus_info[code]
                if subject_sem == target_sem:
                    if grade not in ["W", "WH", "NE", "WD", "-", "NA", ""]:
                        total_credits += credits
                        total_points += grade_points.get(grade, 0) * credits
                
        gpa = round((total_points / total_credits) + 1e-9, 2) if total_credits > 0 else 0.00

        final_rows.append({
            "Joining Year": int(joining_year) if joining_year.isdigit() else joining_year,
            "Semester": target_sem,
            "Reg No": reg_no,
            "Name": data["name"],
            "GPA": gpa 
        })

    df = pd.DataFrame(final_rows)
    if not df.empty:
        df = df.sort_values(by=["Joining Year", "Semester", "Reg No"])
    return df
st.sidebar.title("📌 Instructions")
st.sidebar.info("""
1. Upload the official Semester Result PDF.
2. The app will extract Registration No, Names, and dynamically calculate GPA.
3. Lower-semester Arrears are safely filtered out.
4. Download as a formatted Excel file.
""")

st.title("🎓 Academic Performance Parser")
st.subheader("Transform PDF Results into Data Insights")

uploaded_file = st.file_uploader("Drop your Anna University PDF file here", type="pdf")

if uploaded_file:
    with st.spinner('⚙️ Analyzing PDF physical layout and calculating GPAs...'):
        try:
            df = process_pdf(uploaded_file)
            
            if df.empty:
                st.warning("No valid student results found. Ensure the PDF matches the defined syllabus.")
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("Students Found", len(df))
                col2.metric("Highest GPA", f"{df['GPA'].max():.2f}")
                col3.metric("Average GPA", f"{df['GPA'].mean():.2f}")
                st.write("### 🔍 Data Preview")
                st.dataframe(df.style.format({"GPA": "{:.2f}"}), use_container_width=True)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='GPA_Results')
                
                st.write("---")
                st.download_button(
                    label="📥 Download Excel Report",
                    data=output.getvalue(),
                    file_name="Results_Summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.balloons()

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.info("Ensure the PDF is a standard Anna University result document.")
else:
    st.info("👋 Welcome! Please upload a PDF to get started.")
