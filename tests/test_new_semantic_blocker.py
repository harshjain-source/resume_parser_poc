import os
import json
import re

class NewSemanticBlocker:
    """
    Test version of SemanticBlocker with enhanced anchor detection.
    """
    
    MAJOR_ANCHORS = {
        "DOCUMENT_METADATA": ["technical proposal", "extraction metadata"],
        "PERSONAL_INFORMATION": ["basic details", "profile", "before ekyc data", "nationality", "date of birth", "pan number", "aadhar number", "passport number", "mobile", "email", "current address", "permanent address", "verification status", "registration date"],
        "PROPOSED_ASSIGNMENT_DETAILS": ["proposed position", "name of firm", "profession", "years with firm", "detailed task assigned"],
        "EDUCATION": ["qualification details"],
        "PROFESSIONAL_EXPERIENCE": ["companies details", "detailed work details"],
        "LEGAL_DECLARATIONS": ["certification by the candidate", "certification by the firm"],
        "ADDITIONAL_INFORMATION": ["membership of professional", "software skills", "technical skills", "languages known", "certifications", "additional information"]
    }

    MINOR_ANCHORS = [
        "bridge details", "tunnel details", "highway details", "lane details", 
        "arbitration", "description of duties", "nature of assignment", 
        "project duration", "other assignment fields", "supporting documents",
        "experience details", "major activities", "project status", "name of work",
        "employer name", "client", "start date", "completion date", "project cost",
        "designation"
    ]

    def __init__(self, raw_text):
        self.raw_text = raw_text

    def run(self):
        sections = {"INTRO_HEADER": []}
        current_cat = "INTRO_HEADER"
        
        for line in self.raw_text.splitlines():
            line_clean = line.strip().lower()
            
            if not line_clean:
                continue

            # Check for MAJOR Anchor (Category Switch)
            # ONLY switch if it's a header line (starts with ##)
            if line_clean.startswith("##"):
                header_text = line_clean.replace("#", "").strip()
                
                found_major = False
                for cat, keywords in self.MAJOR_ANCHORS.items():
                    if any(kw == header_text or header_text.startswith(kw) for kw in keywords):
                        # Before switching, check if this is actually just a MINOR anchor 
                        is_minor = any(kw in header_text for kw in self.MINOR_ANCHORS)
                        
                        if not is_minor:
                            current_cat = cat
                            if current_cat not in sections: 
                                sections[current_cat] = []
                            found_major = True
                            break
            
            sections[current_cat].append(line)

        # Finalize blocks
        blocks = {k: "\n".join(v).strip() for k, v in sections.items() if v}
        return blocks

def test_on_existing_data():
    sample_path = r"c:\Users\Dell\Desktop\resume_parser\resume_parser1\processed_resumes\BE.pdf_20260219_123106\clean_text.json"
    
    print(f"LOADING: Loading sample: {sample_path}")
    with open(sample_path, 'r', encoding='utf-8') as f:
        clean_text = json.load(f)["content"]

    blocker = NewSemanticBlocker(clean_text)
    blocks = blocker.run()

    print("\n" + "="*50)
    print("RESULTS: NEW SEMANTIC BLOCKING RESULTS")
    print("="*50)
    
    for cat, content in blocks.items():
        line_count = len(content.splitlines())
        print(f"CATEGORY: {cat:30} | {line_count:4} lines")
        # Print first 2 lines of content for preview
        preview = "\n".join(content.splitlines()[:2])
        print(f"   Preview: {preview[:100]}...")
        print("-" * 50)

if __name__ == "__main__":
    test_on_existing_data()
