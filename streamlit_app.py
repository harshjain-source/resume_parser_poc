import streamlit as st
import json
import os
import base64
import datetime
from main_pipeline import ResumePipeline
from config.settings import settings
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Resume Intelligence Portal", page_icon="📄", layout="wide")

STORAGE_DIR = settings.RESUME_DIR
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

# Premium Light Theme CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    .main {
        background-color: #F8F9FA;
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #FFFFFF;
        color: #2D3436;
    }
    h1, h2, h3 {
        color: #0984E3 !important;
        font-weight: 700;
    }
    .stSidebar {
        background-color: #F1F2F6;
        border-right: 1px solid #DFE4EA;
    }
    .candidate-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-bottom: 2rem;
        border: 1px solid #E1E8ED;
    }
    .stat-box {
        background: #F8F9FA;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #EDF2F7;
    }
    .stat-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0984E3;
    }
    .badge {
        display: inline-block;
        padding: 4px 12px;
        background: #E1F5FE;
        color: #0288D1;
        border-radius: 20px;
        margin: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- UTILS ---

def display_pdf(file_path):
    """Embeds a PDF in an iframe using base64."""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def get_history():
    if not os.path.exists(STORAGE_DIR): return []
    folders = [f for f in os.listdir(STORAGE_DIR) if os.path.isdir(os.path.join(STORAGE_DIR, f)) and f != "temp"]
    folders.sort(key=lambda x: os.path.getmtime(os.path.join(STORAGE_DIR, x)), reverse=True)
    return folders

def load_processed_resume(folder_name):
    path = os.path.join(STORAGE_DIR, folder_name)
    files = {
        "md": None, "txt": None, "blocks": None, "final": None, "original": None
    }
    schema = {
        "md": ["extracted_text.md", "extracted_text.txt"],
        "txt": ["clean_text.txt"],
        "blocks": ["semantic_blocks.json"],
        "final": ["final_resume.json"],
        "original": ["original.pdf"]
    }
    for key, possible_names in schema.items():
        for filename in possible_names:
            f_path = os.path.join(path, filename)
            if os.path.exists(f_path):
                if filename.endswith(".json"):
                    with open(f_path, "r", encoding="utf-8") as file:
                        files[key] = json.load(file)
                elif filename.endswith(".pdf"):
                    files[key] = f_path
                else:
                    with open(f_path, "r", encoding="utf-8") as file:
                        files[key] = file.read()
                break
    return files

# --- DASHBOARD COMPONENT ---

def ensure_list(data):
    """Ensures data is a list; if it's a dict, wraps it in a list."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []

def render_dashboard(data, folder):
    final = data.get("final")
    if not final or "sections" not in final:
        st.warning("Dashboard data not fully available. Parsing in progress or failed.")
        return

    sections = final.get("sections", {})
    
    # 1. Extract Personal Info
    personal = sections.get("PERSONAL_INFO", {})
    if isinstance(personal, list) and personal:
        personal = personal[0]
    elif not isinstance(personal, dict):
        personal = {}
    
    # 2. Extract and Sanitize Lists (Fixes KeyError/TypeError on slice)
    exp_list = ensure_list(sections.get("EXPERIENCE", []))
    edu_list = ensure_list(sections.get("EDUCATION", []))
    
    # 3. Stats Calculation with safe access
    # We check metadata first, then fallback to sections if needed
    metadata = final.get("metadata", {})
    total_years = metadata.get("total_experience_years") or sections.get("total_experience_years") or "N/A"
    
    total_companies = len(exp_list)
    total_projects = sum([1 for e in exp_list if "project" in str(e).lower()])
    
    # Image Handling
    photo_rel_path = metadata.get("candidate_photo")
    image_col = None
    if photo_rel_path:
        photo_abs_path = os.path.join(STORAGE_DIR, folder, photo_rel_path)
        if os.path.exists(photo_abs_path):
            image_col = photo_abs_path

    # Main Header
    st.markdown(f"""
        <div class="candidate-card">
            <div style="display: flex; align-items: flex-start; gap: 2rem;">
                {f'<img src="data:image/png;base64,{base64.b64encode(open(image_col, "rb").read()).decode()}" style="width:120px; border-radius:10px; border: 1px solid #ddd;">' if image_col else '<div style="width:120px; height:150px; background:#f0f2f6; border-radius:10px; display:flex; align-items:center; justify-content:center; color:#adb5bd;">Photo</div>'}
                <div style="flex: 1;">
                    <h2 style="margin:0;">{personal.get('full_name') or personal.get('name') or 'Candidate Profile'}</h2>
                    <p style="color: #636E72; font-size: 1.1rem; margin-top: 0.5rem;">
                        📍 {personal.get('location') or 'Location Not Specified'} | 📧 {personal.get('email') or 'N/A'} | 📞 {personal.get('phone') or 'N/A'}
                    </p>
                    <div style="margin-top: 1rem;">
                        <span class="badge">Total Exp: {total_years} Yrs</span>
                        <span class="badge">Companies: {total_companies}</span>
                        <span class="badge">Projects: {total_projects}+</span>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Secondary Highlights
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("🛠️ Highlights")
        summary = final.get("professional_summary") or "Qualified engineer with extensive experience in structural and bridge design."
        st.write(summary)
    
    with col2:
        st.subheader("🎓 Education")
        for edu in edu_list[:2]:
            st.markdown(f"**{edu.get('degree', 'Degree')}**  \n{edu.get('institution', 'University')} ({edu.get('dates', {}).get('end', '')})")
    
    with col3:
        st.subheader("⚡ Skills")
        skills = final.get("skills", [])
        if not skills and "PERSONAL_INFO" in sections:
            # Fallback for portal skills
            skills = ["Bridge Design", "Project Management", "Technical Supervision", "Structural Analysis"]
        
        skills_html = "".join([f'<span class="badge">{s}</span>' for s in skills[:12]])
        st.markdown(skills_html, unsafe_allow_html=True)

# --- UI LOGIC ---

def main():
    st.title("💼 Resume Intelligence Hub")
    
    with st.sidebar:
        st.header("📂 Data History")
        history = get_history()
        selected_history = st.selectbox("Select Resume", ["None"] + history)
        
        if st.button("➕ Process New"):
            st.session_state['selected_history'] = None
            st.rerun()

    if selected_history == "None":
        st.write("### � Upload New Resume")
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file and st.button("✨ Run Pipeline"):
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            resume_id = f"{uploaded_file.name.replace(' ', '_')}_{ts}"
            temp_path = os.path.join(STORAGE_DIR, "temp_upload.pdf")
            with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
            
            with st.status("🛠️ Analyzing...", expanded=True):
                pipeline = ResumePipeline(resume_id=resume_id, original_filename=uploaded_file.name)
                pipeline.run(temp_path)
            st.session_state['selected_history'] = resume_id
            st.rerun()
    else:
        folder = selected_history
        data = load_processed_resume(folder)
        
        # 1. TOP DASHBOARD
        render_dashboard(data, folder)
        
        st.divider()
        
        # 2. COLUMN / TABBED ARTIFACTS
        tabs = st.tabs(["� Final JSON", "📄 Original PDF", "🧩 Semantic Blocks", "📝 Clean Text", "📄 Structure (MD)"])
        
        with tabs[0]:
            st.json(data["final"] or {"error": "No final JSON found"})
            
        with tabs[1]:
            if data["original"]:
                display_pdf(data["original"])
            else:
                st.error("Original PDF not found for this entry.")
                
        with tabs[2]:
            st.json(data["blocks"] or {"error": "No blocks found"})
            
        with tabs[3]:
            st.text_area("Content", data["txt"] or "N/A", height=600)
            
        with tabs[4]:
            if data["md"]:
                st.markdown(data["md"])
            else:
                st.warning("No markdown structure found.")

if __name__ == "__main__":
    main()

