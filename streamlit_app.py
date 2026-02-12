import streamlit as st
import json
import os
import re
import fitz
import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

# --- CONFIG & STYLING ---
st.set_page_config(page_title="AI Resume Intelligence Hub", page_icon="🏦", layout="wide")

STORAGE_DIR = "processed_resumes"
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        color: #e0e0e0;
    }
    h1, h2, h3 {
        color: #00d4ff !important;
        font-family: 'Inter', sans-serif;
    }
    .stButton>button {
        background: linear-gradient(45deg, #00d4ff, #005f73);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
    }
    .card {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }
    .metric-card {
        text-align: center;
        padding: 15px;
        background: rgba(0, 212, 255, 0.1);
        border-radius: 10px;
        border: 1px solid #00d4ff;
    }
    .sidebar-history {
        cursor: pointer;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
        background: rgba(255,255,255,0.05);
        transition: 0.2s;
    }
    .sidebar-history:hover {
        background: rgba(0, 212, 255, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# --- PIPELINE CLASSES ---

class PDFToMarkdown:
    def __init__(self, pdf_bytes):
        self.pdf_bytes = pdf_bytes
    def run(self):
        doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
        raw_md = []
        for page in doc:
            for b in page.get_text("dict")["blocks"]:
                if "lines" in b:
                    block_text = []
                    for l in b["lines"]:
                        line = "".join([s["text"] for s in l["spans"]])
                        if l["spans"]:
                            span = l["spans"][0]
                            if span["size"] > 14: line = f"# {line}"
                            elif span["size"] > 11 or (span["flags"] & 2**4): line = f"## {line}"
                        block_text.append(line)
                    raw_md.append("\n".join(block_text))
        doc.close()
        return "\n".join(raw_md)

class TextCleaner:
    def _repair_encoding(self, text):
        reps = {r"â€“": "-", r"Â": "", r"â€¢": "•", r"â€™": "'", r"\x0c": ""}
        for p, r in reps.items(): text = text.replace(p, r)
        return text
    def _remove_noise(self, text):
        ui = [r"View\s*Uploaded\s*File", r"View\s*File", r"Download\s*File", r"Supporting\s*Documents?", r"VIEW\s*CONSULTANT"]
        for p in ui: text = re.sub(p, '', text, flags=re.I)
        noise = [r"Page \d+ of \d+", r"Technical Proposal\s*\|\s*\d+", r"Rodic Consultants", r"INFRACON"]
        lines = text.splitlines()
        return [l for l in lines if l.strip() and not any(re.search(p, l, re.I) for p in noise)]
    def _join_fragments(self, lines):
        joined = []
        skip = 0
        for i in range(len(lines)):
            if skip > 0: skip -= 1; continue
            curr = lines[i].strip()
            if i+2 < len(lines) and lines[i+1].strip() == ":" and len(lines[i+2]) < 200:
                joined.append(f"{curr} : {lines[i+2]}"); skip = 2
            elif curr.endswith(":") and i+1 < len(lines) and len(lines[i+1]) < 200 and len(curr) < 60:
                joined.append(f"{curr} {lines[i+1]}"); skip = 1
            else: joined.append(curr)
        return joined
    def run(self, text):
        text = self._repair_encoding(text)
        lines = self._remove_noise(text)
        lines = self._join_fragments(lines)
        lines = self._join_fragments(lines)
        return "\n".join(lines)

class SectionSegmenter:
    CATEGORIES = {
        "PERSONAL": ["contact", "profile", "personal", "basic details", "candidate"],
        "EDUCATION": ["education", "qualification", "academic"],
        "EXPERIENCE": ["experience", "employment", "professional", "work history", "detailed work"],
        "SKILLS": ["skills", "expertise", "competencies", "technologies"],
        "PROJECTS": ["projects", "assignments", "case studies", "project details"]
    }
    def run(self, markdown_text):
        sections = {"HEADER": []}
        current_cat = "HEADER"
        for line in markdown_text.splitlines():
            line_clean = line.strip().lower()
            if line.startswith("#"):
                for cat, keywords in self.CATEGORIES.items():
                    if any(kw in line_clean for kw in keywords):
                        current_cat = cat
                        if current_cat not in sections: sections[current_cat] = []
                        break
            sections[current_cat].append(line)
        return {k: "\n".join(v).strip() for k, v in sections.items() if v}

class LLMParser:
    def __init__(self, api_key):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0, google_api_key=api_key)
    def parse_bucket(self, bucket_name: str, text: str):
        parser = JsonOutputParser()
        prompt = PromptTemplate(
            template="You are a professional Resume Data Extractor.\n"
                     "Your goal is to extract ALL information from the {bucket_name} text into a highly structured JSON format.\n"
                     "1. Do not lose any details (dates, numbers, descriptions, labels).\n"
                     "2. Use descriptive and consistent keys.\n"
                     "3. If there are multiple items (like jobs, projects, or degrees), structure them as a JSON list of objects.\n"
                     "4. If a field has many sub-details, create a nested object.\n\n"
                     "{format_instructions}\n"
                     "TEXT:\n{text}\n",
            input_variables=["bucket_name", "text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        chain = prompt | self.llm
        try:
            response = chain.invoke({"bucket_name": bucket_name, "text": text})
            tokens_in = response.usage_metadata.get('input_tokens', 0) if hasattr(response, 'usage_metadata') else 0
            tokens_out = response.usage_metadata.get('output_tokens', 0) if hasattr(response, 'usage_metadata') else 0
            return parser.parse(response.content), (tokens_in, tokens_out)
        except Exception as e:
            return {"error": str(e)}, (0, 0)

# --- UTILS ---

def get_history():
    if not os.path.exists(STORAGE_DIR): return []
    folders = [f for f in os.listdir(STORAGE_DIR) if os.path.isdir(os.path.join(STORAGE_DIR, f))]
    return sorted(folders, reverse=True)

def load_processed_resume(folder_name):
    path = os.path.join(STORAGE_DIR, folder_name)
    files = {
        "relatable_data.md": None,
        "clean_text.txt": None,
        "semantic_blocks.json": None,
        "final_resume.json": None
    }
    for f in files:
        f_path = os.path.join(path, f)
        if os.path.exists(f_path):
            with open(f_path, "r", encoding="utf-8") as file:
                if f.endswith(".json"): files[f] = json.load(file)
                else: files[f] = file.read()
    return files

# --- UI LOGIC ---

def main():
    st.title("🏦 AI Resume Intelligence Hub")
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_key = st.text_input("Enter Gemini API Key", type="password", value="AIzaSyDwX4nZOlkjWYO-YeKzwXssDhrZQeE0AVw")
        
        st.divider()
        st.header("📂 History")
        history = get_history()
        
        if not history:
            st.info("No resumes processed yet.")
            selected_history = None
        else:
            selected_history = st.selectbox("Select a previous resume", ["None"] + history)
            if selected_history == "None": selected_history = None

        if st.button("➕ Process New Resume"):
            st.session_state['show_uploader'] = True
            st.session_state['selected_history'] = None
        
        if selected_history:
             st.session_state['selected_history'] = selected_history
             st.session_state['show_uploader'] = False

    # Main Area Logic
    if st.session_state.get('show_uploader', True) and not st.session_state.get('selected_history'):
        st.write("### 📤 Upload New Resume")
        uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
        
        if uploaded_file and api_key:
            if st.button("✨ Start Pipeline"):
                # Create Unique Folder
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                folder_name = f"{uploaded_file.name.replace(' ', '_')}_{ts}"
                folder_path = os.path.join(STORAGE_DIR, folder_name)
                os.makedirs(folder_path)
                
                with st.status("🛠️ Building Intelligence...", expanded=True) as status:
                    # 1. Raw Extracted
                    st.write("1️⃣ Extracting Structural Markdown...")
                    pdf_bytes = uploaded_file.read()
                    raw_text = PDFToMarkdown(pdf_bytes).run()
                    with open(os.path.join(folder_path, "relatable_data.md"), "w", encoding="utf-8") as f: f.write(raw_text)
                    
                    # 2. Cleaned
                    st.write("2️⃣ Running Advanced Cleaning...")
                    clean_text = TextCleaner().run(raw_text)
                    with open(os.path.join(folder_path, "clean_text.txt"), "w", encoding="utf-8") as f: f.write(clean_text)
                    
                    # 3. Blocked
                    st.write("3️⃣ Semantic Segmentation...")
                    blocks = SectionSegmenter().run(clean_text)
                    with open(os.path.join(folder_path, "semantic_blocks.json"), "w", encoding="utf-8") as f: json.dump(blocks, f, indent=4)
                    
                    # 4. LLM Final
                    st.write("4️⃣ LLM Neural Synthesis...")
                    parser = LLMParser(api_key)
                    final_data = {"sections": {}, "metadata": {"tokens_in": 0, "tokens_out": 0}}
                    
                    bar = st.progress(0)
                    for i, (cat, content) in enumerate(blocks.items()):
                        st.write(f"  • Synthesizing: {cat}")
                        res, (tin, tout) = parser.parse_bucket(cat, content)
                        final_data["sections"][cat] = res
                        final_data["metadata"]["tokens_in"] += tin
                        final_data["metadata"]["tokens_out"] += tout
                        bar.progress((i+1)/len(blocks))
                    
                    with open(os.path.join(folder_path, "final_resume.json"), "w", encoding="utf-8") as f: json.dump(final_data, f, indent=4)
                    
                    st.session_state['selected_history'] = folder_name
                    st.session_state['show_uploader'] = False
                    status.update(label="✅ Resume Knowledge Base Created!", state="complete", expanded=False)
                    st.rerun()

    # Display Logic for Selected Resume
    if st.session_state.get('selected_history'):
        folder = st.session_state['selected_history']
        st.write(f"### 📄 Resume: {folder.split('__')[0]}")
        
        data = load_processed_resume(folder)
        
        # Tabs for stages
        t1, t2, t3, t4, t5 = st.tabs(["💎 Final Result", "📝 Cleaned Text", "🧩 Semantic Blocks", "📄 Raw Markdown", "📊 Metrics"])
        
        with t1:
            if data["final_resume.json"]:
                sections = data["final_resume.json"].get("sections", {})
                for s_name, s_content in sections.items():
                    with st.expander(f"📌 {s_name}", expanded=True):
                        st.json(s_content)
                st.divider()
                st.download_button("💾 Download Full JSON", data=json.dumps(data["final_resume.json"], indent=4), file_name=f"{folder}.json")
            else: st.warning("Final JSON not found.")
            
        with t2:
            st.text_area("Cleaned Text (clean_text.txt)", data["clean_text.txt"], height=600)
            
        with t3:
            st.json(data["semantic_blocks.json"])
            
        with t4:
            st.markdown(data["relatable_data.md"])
            
        with t5:
            if data["final_resume.json"] and "metadata" in data["final_resume.json"]:
                m = data["final_resume.json"]["metadata"]
                c1, c2, c3 = st.columns(3)
                c1.metric("Tokens In", m["tokens_in"])
                c2.metric("Tokens Out", m["tokens_out"])
                cost = (m["tokens_in"]*0.000125 + m["tokens_out"]*0.000375)/1000
                c3.metric("Est. Cost", f"${round(cost, 5)}")

if __name__ == "__main__":
    main()
