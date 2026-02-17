import os
import json
import re
from config.settings import settings
from config.logger_config import get_logger

class SemanticBlocker:
    """
    Stage 3: Semantic Block Creation.
    Groups cleaned text into logical buckets for LLM processing.
    """
    # Anchor-Based Hierarchy Configuration
    MAJOR_ANCHORS = {
        "PERSONAL_INFO": ["basic details", "before ekyc data", "aadhar", "pan validation", "profile", "passport"],
        "EDUCATION": ["qualification details", "academic", "degree", "educational qualification"],
        "EXPERIENCE": ["companies details", "detailed work details", "experience details", "work history", "employment"],
        "LEGAL_CERTIFICATION": ["certification by the candidate", "certification by the firm"]
    }

    # These are 'Child' headers. They stay inside the current Major Section.
    MINOR_ANCHORS = [
        "bridge details", "tunnel details", "highway details", "technology", 
        "designation", "nature of assignment", "description of duties", "work type",
        "detailed work certificate", "supporting documents", "client contact"
    ]

    def __init__(self, resume_id: str):
        self.resume_id = resume_id
        self.logger = get_logger("SemanticBlocker")
        self.base_path = os.path.join(settings.RESUME_DIR, resume_id)
        self.input_path = os.path.join(self.base_path, "clean_text.json")
        self.output_json_path = os.path.join(self.base_path, "semantic_blocks.json")
        self.output_txt_path = os.path.join(self.base_path, "semantic_blocks.txt")
        self.logger.info(f"SemanticBlocker initialized for {resume_id}")

    def run(self):
        self.logger.info(f"Grouping text into semantic blocks for {self.resume_id}")
        if not os.path.exists(self.input_path):
            self.logger.error(f"Missing input artifact: {self.input_path}")
            raise FileNotFoundError(f"Missing input artifact: {self.input_path}")
            
        try:
            with open(self.input_path, 'r', encoding='utf-8') as f:
                clean_text = json.load(f)["content"]

            sections = {"INTRO_HEADER": []}
            current_cat = "INTRO_HEADER"
            self.logger.debug("Starting semantic scan...")
            
            for line in clean_text.splitlines():
                line_clean = line.strip().lower().replace("#", "").strip()
                
                if not line_clean:
                    continue

                # Check for MAJOR Anchor (Category Switch)
                for cat, keywords in self.MAJOR_ANCHORS.items():
                    if any(kw in line_clean for kw in keywords):
                        is_minor = any(kw in line_clean for kw in self.MINOR_ANCHORS)
                        
                        if not is_minor:
                            if current_cat != cat:
                                self.logger.debug(f"Switching section: {current_cat} -> {cat} (Trigger: '{line_clean}')")
                            current_cat = cat
                            if current_cat not in sections: 
                                sections[current_cat] = []
                            break
                
                sections[current_cat].append(line)

            blocks = {k: "\n".join(v).strip() for k, v in sections.items() if v}
            self.logger.info(f"Semantic scan complete. Found sections: {list(blocks.keys())}")

            with open(self.output_json_path, 'w', encoding='utf-8') as f:
                json.dump(blocks, f, indent=4, ensure_ascii=False)

            with open(self.output_txt_path, 'w', encoding='utf-8') as f:
                for cat, content in blocks.items():
                    f.write(f"=== {cat} ===\n{content}\n" + "="*20 + "\n\n")
                
            self.logger.debug(f"Semantic block artifacts saved for {self.resume_id}")
            return self.output_json_path
        except Exception as e:
            self.logger.error(f"Semantic blocking error: {e}", exc_info=True)
            raise
