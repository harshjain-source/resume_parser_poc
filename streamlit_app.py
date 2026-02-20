import streamlit as st
import json
import os
import re
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
    personal_section = sections.get("PERSONAL_INFORMATION") or sections.get("PERSONAL_INFO", {})
    # Handle different nesting versions
    personal = personal_section.get("personal_details") or personal_section
    
    if isinstance(personal, list) and personal:
        personal = personal[0]
    elif not isinstance(personal, dict):
        personal = {}
    
    # Extract email and contact with new nested paths
    contact = personal.get("contact_details") or personal.get("contact", {})
    email = personal.get("email") or contact.get("email") or personal.get("Email") or "N/A"
    mobile = contact.get("primary_mobile") or contact.get("mobile") or contact.get("Mobile") or "N/A"
    # 2. Extract and Sanitize Lists
    # Support both new and old Experience schemas
    employments = ensure_list(sections.get("PROFESSIONAL_EXPERIENCE", []))
    if not employments:
        exp_data = sections.get("EXPERIENCE", {})
        if isinstance(exp_data, dict) and "employments" in exp_data:
            employments = ensure_list(exp_data["employments"])
        else:
            employments = ensure_list(exp_data)
    
    # Support both new and old Education schemas
    edu_list = ensure_list(sections.get("EDUCATION", []))
    if len(edu_list) == 1 and isinstance(edu_list[0], dict) and "qualifications" in edu_list[0]:
        edu_list = ensure_list(edu_list[0]["qualifications"])
    
    # 3. Dynamic Stats Calculation
    computed = final.get("computed", {})
    total_years = computed.get("total_experience_years") or "N/A"
    
    raw_employers = []
    raw_clients = []
    raw_projects = []

    def fuzzy_normalize(name):
        if not name: return ""
        n = str(name).lower().strip()
        n = re.sub(r'[^a-z0-9\s]', '', n) # Remove punct
        # Remove common suffixes and noisy words
        n = re.sub(r'\b(ltd|limited|pvt|pvt ltd|company|inc|corp|co|and|&|solutions|services|consultants)\b', '', n)
        return " ".join(n.split())

    # Collect from Experience
    for emp_obj in employments:
        if not isinstance(emp_obj, dict): continue
        
        # Employer
        e_name = emp_obj.get("company_name") or emp_obj.get("firm") or emp_obj.get("organization")
        if e_name: raw_employers.append(str(e_name).strip())
        
        # Projects & Clients
        plist = ensure_list(emp_obj.get("projects", []))
        # Handle old key fallback if needed
        if not plist: plist = ensure_list(emp_obj.get("individual_project_details", []))
            
        for p in plist:
            if not isinstance(p, dict): continue
            
            # Project Name
            p_name = p.get("project_name") or p.get("name")
            if p_name: raw_projects.append(str(p_name).strip())
            
            # Project Client
            c_name = p.get("client_name") or p.get("client")
            if c_name: raw_clients.append(str(c_name).strip())

        # Hybrid case: Check for single project name at employment level if list is empty
        if not plist:
            top_p = emp_obj.get("project_name")
            if top_p: raw_projects.append(str(top_p).strip())

    # Fuzzy Deduplicate
    def dedupe(items):
        seen_norm = set()
        unique = []
        for item in items:
            norm = fuzzy_normalize(item)
            if norm and norm not in seen_norm:
                unique.append(item)
                seen_norm.add(norm)
        return unique

    employers = dedupe(raw_employers)
    projects = dedupe(raw_projects)
    clients = dedupe(raw_clients)

    total_companies = len(employers)
    total_projects = len(projects)
    total_clients = len(clients)
    
    # Image Handling
    metadata = final.get("metadata", {})
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
                    <h2 style="margin:0;">{personal.get('name') or 'Candidate Profile'}</h2>
                    <p style="color: #636E72; font-size: 1.1rem; margin-top: 0.5rem;">
                         📧 {email} | 📞 {mobile}
                    </p>
                    <div style="margin-top: 1rem;">
                        <span class="badge">Total Exp: {total_years} Yrs</span>
                        <span class="badge">Employers: {total_companies}</span>
                        <span class="badge">Clients: {total_clients}</span>
                        <span class="badge">Projects: {total_projects}</span>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Detailed Content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🛠️ Professional Summary")
        summary = personal.get("professional_summary") or personal.get("summary")
        if not summary:
            designation = personal.get("proposed_position") or personal.get("firm")
            if designation:
                summary = f"Professional profile with background in {designation}."
            else:
                summary = "Detailed project and experience information available in sections."
        st.write(summary)

        st.subheader("🏢 Previous Employers")
        if employers:
            for e in employers:
                st.markdown(f"- **{e}**")
        else:
            st.write("No employer information found.")

        st.subheader("🤝 Associated Clients")
        if clients:
            for c in clients:
                st.markdown(f"- **{c}**")
        else:
            st.write("No client information found.")

        st.subheader("🚀 Projects Handled")
        if projects:
            for p in projects[:15]: # Top 15 projects
                st.markdown(f"- {p}")
            if len(projects) > 15:
                st.write(f"*... and {len(projects)-15} more projects*")
        else:
            st.write("No project details found.")
    
    with col2:
        st.subheader("👤 Personal Details")
        reg = personal.get("professional_registration_details") or {}
        ident = personal.get("identity_details") or {}
        addr = personal.get("addresses") or {}
        
        st.markdown(f"""
        - **DOB**: {personal.get('date_of_birth') or personal.get('dob') or 'N/A'}
        - **Nationality**: {personal.get('nationality') or 'N/A'}
        - **Address**: {addr.get('current_address') or personal.get('address', {}).get('current') or 'N/A'}
        - **Reg No**: {reg.get('registration_number') or 'N/A'}
        - **Verification**: {reg.get('verification_status') or 'N/A'} ({reg.get('verification_remarks') or 'None'})
        """)

        st.subheader("🎓 Education")
        if edu_list:
            for edu in edu_list:
                level = edu.get('degree_title') or edu.get('degree') or edu.get('level') or 'Degree'
                inst = edu.get('university_name') or edu.get('institution_name') or edu.get('university') or edu.get('institution') or 'N/A'
                year = edu.get('passing_year') or edu.get('dates', {}).get('end', '')
                st.markdown(f"**{level}**  \n{inst} ({year})")
        else:
            st.write("Educational background not found.")

        st.subheader("⚡ Skills & Tools")
        skills = personal.get("skills") or sections.get("SKILLS") or []
        if isinstance(skills, str): skills = [s.strip() for s in skills.split(",")]
        
        if skills:
            skills_html = "".join([f'<span class="badge">{s}</span>' for s in skills])
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.write("No specific skills listed.")

# --- UI LOGIC ---

def main():
    st.title("💼 Resume Intelligence Hub")
    
    # Initialize session state
    if 'current_id' not in st.session_state:
        st.session_state['current_id'] = "None"
    
    with st.sidebar:
        st.header("📂 Data History")
        history = get_history()
        
        # We drive the selection from session state
        selected_history = st.selectbox(
            "Select Resume", 
            ["None"] + history,
            index=["None", *history].index(st.session_state['current_id']) if st.session_state['current_id'] in ["None", *history] else 0
        )

        if selected_history != st.session_state['current_id']:
            st.session_state['current_id'] = selected_history
            st.rerun()
        
        if st.button("➕ Process New", use_container_width=True):
            st.session_state['current_id'] = "None"
            st.rerun()

        st.divider()
        st.header("⚙️ Model Config")
        provider = st.selectbox("Provider", ["google", "groq", "sarvam"], index=0 if settings.DEFAULT_PROVIDER == "google" else 1 if settings.DEFAULT_PROVIDER == "groq" else 2)
        
        if provider == "google":
            model_options = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash-lite"]
            default_model = settings.GEMINI_MODEL
        elif provider == "groq":
            model_options = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
            default_model = settings.GROQ_MODEL
        else:
            model_options = ["sarvam-m"]
            default_model = settings.SARVAM_MODEL
            
        model = st.selectbox("Model", model_options, index=model_options.index(default_model) if default_model in model_options else 0)

    if st.session_state['current_id'] == "None":
        st.write("### 📄 Upload New Resume")
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file and st.button("✨ Run Pipeline"):
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            resume_id = f"{uploaded_file.name.replace(' ', '_')}_{ts}"
            temp_path = os.path.join(STORAGE_DIR, "temp_upload.pdf")
            with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
            
            with st.status("🛠️ Analyzing using " + model + "...", expanded=True) as status:
                pipeline = ResumePipeline(
                    resume_id=resume_id, 
                    original_filename=uploaded_file.name,
                    provider=provider,
                    model=model
                )
                
                def progress_update(msg, detail=None):
                    if detail:
                        status.write(f"**{msg}** ({detail})")
                    else:
                        status.write(f"⏳ {msg}")
                
                pipeline.run(temp_path, progress_callback=progress_update)
                status.update(label="✅ Extraction Complete!", state="complete", expanded=False)
            st.session_state['current_id'] = resume_id
            st.rerun()
    else:
        folder = selected_history
        data = load_processed_resume(folder)
        
        # COLUMN / TABBED ARTIFACTS
        tabs = st.tabs([
            "📊 Dashboard", 
            "📄 Final JSON", 
            "📄 Original PDF", 
            "🧩 Semantic Blocks", 
            "📝 Clean Text", 
            "📄 Structure (MD)"
        ])

        # Sidebar Metadata
        with st.sidebar:
            st.divider()
            st.markdown("### 🔍 Extraction Metadata")
            
            # Correct retrieval from deep nested 'final' JSON
            final_json = data.get("final") or {}
            usage = final_json.get("usage", {})
            st.write(f"**Input Tokens**: {usage.get('input_tokens', 0)}")
            st.write(f"**Output Tokens**: {usage.get('output_tokens', 0)}")
            st.write(f"**Total Tokens**: {usage.get('total_tokens', 0)}")
            st.info(f"Last Extracted: {final_json.get('extracted_at', 'N/A')}")
            
            # Timelines
            st.divider()
            st.markdown("### ⏲️ Pipeline Timelines")
            timelines = final_json.get("timelines", [])
            if timelines:
                for tl in timelines:
                    st.caption(tl)
            else:
                st.write("No timeline data found.")

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

if __name__ == "__main__":
    main()

