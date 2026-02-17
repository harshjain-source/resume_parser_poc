import streamlit as st
import json
import os
import base64
import datetime
from main_pipeline import ResumePipeline
from config.settings import settings
from dotenv import load_dotenv

# Load .env from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

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
    .project-item {
        margin-left: 1.5rem;
        border-left: 2px solid #0984E3;
        padding-left: 1rem;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .kyc-badge {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 4px 8px;
        border-radius: 4px;
        background: #E8F8F5;
        color: #27AE60;
        border: 1px solid #27AE60;
        font-weight: 700;
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
        "original": ["original.pdf"],
        "log": ["pipeline.log"]
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
    metadata = final.get("metadata", {})
    
    # 1. Extract Personal Info
    personal = sections.get("PERSONAL_INFO", {})
    if isinstance(personal, list) and personal:
        personal = personal[0]
    elif not isinstance(personal, dict):
        personal = {}
    
    # 2. Key Data Extraction
    dob = personal.get("date_of_birth") or "N/A"
    nation = personal.get("nationality") or "N/A"
    profession = personal.get("inferred_profession") or "Professional Candidate"
    kyc = personal.get("kyc_status")
    
    total_years = metadata.get("total_experience_years") or "N/A"
    edu_tier = metadata.get("highest_education_tier") or "N/A"
    
    # AI Token Usage
    usage = final.get("token_usage", {"input": 0, "output": 0, "total": 0})
    
    exp_list = ensure_list(sections.get("EXPERIENCE", []))
    edu_list = ensure_list(sections.get("EDUCATION", []))
    cert_list = ensure_list(sections.get("LEGAL_CERTIFICATION", []))
    
    # Photo Handling
    photo_rel_path = metadata.get("candidate_photo")
    image_col = None
    if photo_rel_path:
        photo_abs_path = os.path.join(STORAGE_DIR, folder, photo_rel_path)
        if os.path.exists(photo_abs_path):
            image_col = photo_abs_path

    # --- TOP HEADER CARD ---
    img_html = ""
    if image_col:
        with open(image_col, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        img_html = f'<img src="data:image/png;base64,{b64}" style="width:140px; height:160px; object-fit:cover; border-radius:12px; border: 2px solid #0984E3;">'
    else:
        img_html = '<div style="width:140px; height:160px; background:#f0f2f6; border-radius:12px; display:flex; align-items:center; justify-content:center; color:#adb5bd; border: 2px dashed #ddd;">No Photo</div>'

    kyc_html = f'<span class="kyc-badge">🛡️ {kyc}</span>' if kyc else ''
    
    header_html = f"""
    <div class="candidate-card">
        <div style="display: flex; flex-direction: row; align-items: flex-start; gap: 2rem;">
            <div style="flex-shrink: 0;">{img_html}</div>
            <div style="flex-grow: 1; min-width: 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <h1 style="margin:0; font-size: 2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{personal.get('full_name') or personal.get('name') or 'Candidate Profile'}</h1>
                    {kyc_html}
                </div>
                <h3 style="margin: 0.2rem 0; color: #636E72 !important; font-weight: 400;">{profession}</h3>
                <p style="color: #636E72; font-size: 0.95rem; margin-top: 0.5rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                    <span>📍 {personal.get('location') or 'Global'}</span>
                    <span>📧 {personal.get('email') or 'N/A'}</span>
                    <span>📞 {personal.get('phone') or 'N/A'}</span>
                </p>
                <hr style="margin: 0.8rem 0; border: 0; border-top: 1px solid #eee;">
                <div style="display: flex; flex-wrap: wrap; gap: 1.5rem;">
                    <div><small style="color:#adb5bd; font-size:0.75rem;">DOB</small><br><span style="font-weight:600;">{dob}</span></div>
                    <div><small style="color:#adb5bd; font-size:0.75rem;">NATIONALITY</small><br><span style="font-weight:600;">{nation}</span></div>
                    <div><small style="color:#adb5bd; font-size:0.75rem;">HIGHEST EDU</small><br><span style="font-weight:600;">{edu_tier}</span></div>
                    <div><small style="color:#adb5bd; font-size:0.75rem;">EXPERIENCE</small><br><span style="font-weight:600;">{total_years} Yrs</span></div>
                </div>
                <div style="margin-top: 1rem; padding: 0.5rem; background: #f1f2f6; border-radius: 8px; display: flex; gap: 1.5rem; border: 1px solid #dfe4ea;">
                    <div style="font-size: 0.8rem;"><span style="color:#636e72;">In:</span> <b style="color:#0984e3;">{usage['input']}</b></div>
                    <div style="font-size: 0.8rem;"><span style="color:#636e72;">Out:</span> <b style="color:#0984e3;">{usage['output']}</b></div>
                    <div style="font-size: 0.8rem;"><span style="color:#636e72;">Total Tokens:</span> <b style="color:#0984e3;">{usage['total']}</b></div>
                    <div style="font-size: 0.8rem; margin-left: auto; color: #b2bec3;">AI Insights ✨</div>
                </div>
            </div>
        </div>
    </div>
    """.replace('\n', ' ')

    st.markdown(header_html, unsafe_allow_html=True)

    # --- MAIN CONTENT GRID ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("� Professional Career & Projects")
        if not exp_list:
            st.info("No work history found.")
        else:
            for exp in exp_list:
                with st.container():
                    st.markdown(f"#### {exp.get('position', 'Role')} @ {exp.get('company', 'Organization')}")
                    d = exp.get('dates') or {}
                    st.caption(f"🗓️ {d.get('start', 'N/A')} — {d.get('end', 'Present')} | 📍 {exp.get('location', 'Remote')}")
                    
                    # Nested Projects
                    projects = exp.get("projects", [])
                    if projects:
                        for p in projects:
                            p_dates = p.get('dates') or {}
                            st.markdown(f"""
                                <div class="project-item">
                                    <strong>🔹 Project: {p.get('title', 'System Development')}</strong> ({p_dates.get('start', '')} - {p_dates.get('end', '')})<br>
                                    <span style="font-size: 0.9rem; color: #444;">{p.get('description') or p.get('role') or 'Contributed to core development and delivery.'}</span>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        # Fallback to description bullet points if no projects nested
                        desc = exp.get("description", [])
                        if isinstance(desc, list):
                            for bullet in desc[:3]:
                                st.markdown(f"- {bullet}")
                    st.divider()

    with col2:
        st.subheader("🎓 Academic Qualification")
        for edu in edu_list:
            st.markdown(f"**{edu.get('degree', 'Degree')}**")
            st.markdown(f"{edu.get('institution', 'University')}")
            edu_dates = edu.get('dates') or {}
            st.caption(f"({edu_dates.get('end', 'N/A')}) | GPA: {edu.get('gpa', 'N/A')}")
            st.write("")
        
        st.subheader("📜 Declarations & Certs")
        certs = cert_list + sections.get("LEGAL_CERTIFICATION", []) if not isinstance(sections.get("LEGAL_CERTIFICATION"), list) else cert_list
        if cert_list:
            for cert in cert_list:
                st.markdown(f"✅ **{cert.get('name')}**")
                st.caption(f"Issued by {cert.get('issuer') or 'Authority'} ({cert.get('date_issued', 'N/A')})")
        else:
            st.write("No certifications found.")
            
        st.subheader("⚡ Core Skills")
        skills = final.get("skills", []) or sections.get("skills", [])
        if skills:
            skills_html = "".join([f'<span class="badge">{s}</span>' for s in skills[:15]])
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.write("No skill data available.")

# --- UI LOGIC ---

def main():
    st.title("💼 Resume Intelligence Hub")
    
    # Initialize session state for current selection and AI settings
    if 'current_selection' not in st.session_state:
        st.session_state['current_selection'] = "None"
    if 'llm_provider' not in st.session_state:
        st.session_state['llm_provider'] = "Google"
    if 'llm_model' not in st.session_state:
        st.session_state['llm_model'] = "gemini-2.5-flash-lite"
    
    with st.sidebar:
        st.header("🧠 AI Settings")
        provider = st.selectbox("LLM Provider", list(settings.LLM_MODELS.keys()), key="llm_provider")
        model_name = st.selectbox("Model", settings.LLM_MODELS[st.session_state['llm_provider']], key="llm_model")
        
        st.divider()
        st.header("📂 Data History")
        history = get_history()
        options = ["None"] + history
        
        # Find index of current selection to keep UI in sync
        try:
            current_index = options.index(st.session_state['current_selection'])
        except ValueError:
            current_index = 0
            
        selected_history = st.selectbox("Select Resume", options, index=current_index)
        
        # Update session state if dropdown changed manually
        if selected_history != st.session_state['current_selection']:
            st.session_state['current_selection'] = selected_history
            st.rerun()
        
        if st.button("➕ Process New"):
            st.session_state['current_selection'] = "None"
            st.rerun()

    if st.session_state['current_selection'] == "None":
        st.write("### 📄 Upload New Resume")
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file and st.button("✨ Run Pipeline"):
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            resume_id = f"{uploaded_file.name.replace(' ', '_')}_{ts}"
            temp_path = os.path.join(STORAGE_DIR, "temp_upload.pdf")
            with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
            
            with st.status(f"🛠️ Analyzing with {st.session_state['llm_model']}...", expanded=True):
                pipeline = ResumePipeline(
                    resume_id=resume_id, 
                    original_filename=uploaded_file.name,
                    llm_provider=st.session_state['llm_provider'],
                    llm_model=st.session_state['llm_model']
                )
                # Pass st.write as callback for real-time progress
                final_path = pipeline.run(temp_path, progress_callback=st.write)
            
            # Successfully update selection with the NEW renamed folder ID
            new_id = os.path.basename(os.path.dirname(final_path))
            st.session_state['current_selection'] = new_id
            st.rerun()
    else:
        folder = st.session_state['current_selection']
        data = load_processed_resume(folder)
        
        # # 1. TOP DASHBOARD
        # render_dashboard(data, folder)
        
        # st.divider()
        
        # 2. COLUMN / TABBED ARTIFACTS
        tabs = st.tabs(["Dashboard","💎 Final JSON", "📄 Original PDF", "🧩 Semantic Blocks", "📝 Clean Text", "📄 Structure (MD)", "📜 Pipeline Logs"])
        
        with tabs[0]:
            render_dashboard(data, folder)                  
        with tabs[1]:
            st.json(data["final"] or {"error": "No final JSON found"})
            
        with tabs[2]:
            if data["original"]:
                display_pdf(data["original"])
            else:
                st.error("Original PDF not found for this entry.")
                
        with tabs[3]:
            st.json(data["blocks"] or {"error": "No blocks found"})
            
        with tabs[4]:
            st.text_area("Content", data["txt"] or "N/A", height=600)
            
        with tabs[5]:
            if data["md"]:
                st.markdown(data["md"])
            else:
                st.warning("No markdown structure found.")

        with tabs[6]:
            if data["log"]:
                st.text_area("Logs", data["log"], height=600)
            else:
                st.info("No logs found for this session.")

if __name__ == "__main__":
    main()

