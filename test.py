import fitz  # PyMuPDF
import os
import re
import json
import datetime

# ==========================================
# STEP 1: CONVERT PDF TO STRUCTURAL MARKDOWN
# ==========================================
class PDFToMarkdown:
    """Stage 1: Extracts text and preserves headers/bolding using font data."""
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def run(self):
        doc = fitz.open(self.pdf_path)
        raw_md = []
        for page in doc:
            for b in page.get_text("dict")["blocks"]:
                if "lines" in b:
                    block_text = []
                    for l in b["lines"]:
                        line = "".join([s["text"] for s in l["spans"]])
                        if l["spans"]:
                            span = l["spans"][0]
                            # Use font size and flags (bit 4 is bold) for MD structure
                            if span["size"] > 14: line = f"# {line}"
                            elif span["size"] > 11 or (span["flags"] & 2**4): line = f"## {line}"
                        block_text.append(line)
                    raw_md.append("\n".join(block_text))
        doc.close()
        return "\n".join(raw_md)

# ==========================================
# STEP 2: ADVANCED CLEANING (NO DATA LOSS)
# ==========================================
class TextCleaner:
    """Stage 2: Fixes encoding, removes UI noise, and joins fragmented data."""
    
    def _repair_encoding(self, text):
        reps = {r"â€“": "-", r"Â": "", r"â€¢": "•", r"â€™": "'", r"\x0c": ""}
        for p, r in reps.items(): text = text.replace(p, r)
        return text

    def _remove_noise(self, text):
        # 1. UI Buttons & Portal artifacts
        ui = [r"View\s*Uploaded\s*File", r"View\s*File", r"Download\s*File", r"Supporting\s*Documents?", r"VIEW\s*CONSULTANT"]
        for p in ui: text = re.sub(p, '', text, flags=re.I)
        
        # 2. System Headers/Footers
        noise = [r"Page \d+ of \d+", r"Technical Proposal\s*\|\s*\d+", r"Rodic Consultants", r"INFRACON"]
        lines = text.splitlines()
        return [l for l in lines if l.strip() and not any(re.search(p, l, re.I) for p in noise)]

    def _join_fragments(self, lines):
        joined = []
        skip = 0
        for i in range(len(lines)):
            if skip > 0: skip -= 1; continue
            curr = lines[i].strip()
            # Lookahead: Join "Label" + ":" + "Value"
            if i+2 < len(lines) and lines[i+1].strip() == ":" and len(lines[i+2]) < 200:
                joined.append(f"{curr} : {lines[i+2]}@"); skip = 2 # Added @ to preserve join intent then clean it
            # Lookahead: Join "Label:" + "Value"
            elif curr.endswith(":") and i+1 < len(lines) and len(lines[i+1]) < 200 and len(curr) < 60:
                joined.append(f"{curr} {lines[i+1]}"); skip = 1
            else: joined.append(curr)
        
        # Simple cleanup of the marker
        return [l.replace("@", "") for l in joined]

    def run(self, text):
        text = self._repair_encoding(text)
        lines = self._remove_noise(text)
        # Process joining twice to catch nested fragments
        lines = self._join_fragments(lines)
        lines = self._join_fragments(lines)
        return "\n".join(lines)

# ==========================================
# STEP 3: SEMANTIC BLOCKING (SEGMENTATION)
# ==========================================
class SectionSegmenter:
    """Stage 3: Groups cleaned text into logical buckets for LLM processing."""
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
            # Detect section by header keywords
            if line.startswith("#"):
                found_new = False
                for cat, keywords in self.CATEGORIES.items():
                    if any(kw in line_clean for kw in keywords):
                        current_cat = cat
                        if current_cat not in sections: sections[current_cat] = []
                        found_new = True
                        break
            
            sections[current_cat].append(line)

        return {k: "\n".join(v).strip() for k, v in sections.items() if v}

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    PDF_FILE = r"C:\Users\Dell\Downloads\rodic resumes\rodic resumes\TL.pdf"
    STORAGE_BASE = "processed_resumes"
    
    if os.path.exists(PDF_FILE):
        # Create Unique Folder
        filename = os.path.basename(PDF_FILE).replace(" ", "_")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{filename}_{ts}"
        output_dir = os.path.join(STORAGE_BASE, folder_name)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        print(f"🚀 Running Structured Pipeline for: {PDF_FILE}")
        print(f"📁 Output Directory: {output_dir}")

        # 1. EXTRACT
        raw_text = PDFToMarkdown(PDF_FILE).run()
        with open(os.path.join(output_dir, "relatable_data.md"), "w", encoding="utf-8") as f: 
            f.write(raw_text)
        
        # 2. CLEAN
        clean_text = TextCleaner().run(raw_text)
        with open(os.path.join(output_dir, "clean_text.txt"), "w", encoding="utf-8") as f: 
            f.write(clean_text)
        print("✅ Step 1 & 2 Complete (Raw and Clean text saved).")

        # 3. BLOCK
        blocks = SectionSegmenter().run(clean_text)
        
        # Save JSON
        with open(os.path.join(output_dir, "semantic_blocks.json"), "w", encoding="utf-8") as f: 
            json.dump(blocks, f, indent=4)
            
        # Optional: Save Human-Readable Text for debugging
        with open(os.path.join(output_dir, "semantic_blocks.txt"), "w", encoding="utf-8") as f:
            for cat, content in blocks.items():
                f.write(f"=== {cat} ===\n")
                f.write(content)
                f.write("\n" + "="*len(f"=== {cat} ===") + "\n\n")
                
        print("✅ Step 3: Semantic Segmentation Complete.")
        print(f"📂 Intermediate files saved in: {output_dir}")
    else:
        print(f"❌ Error: {PDF_FILE} not found.")
