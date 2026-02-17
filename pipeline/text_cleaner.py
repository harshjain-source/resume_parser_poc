import os
import json
import re
from config.settings import settings
from config.logger_config import get_logger

class TextCleaner:
    """
    Stage 2: Advanced Text Cleaning.
    Normalizes raw extracted text by removing noise (headers, footers, links, UI artifacts),
    repairing encoding issues, and standardizing structural layout without losing data.
    """
    def __init__(self, resume_id: str):
        self.resume_id = resume_id
        self.logger = get_logger("TextCleaner")
        self.base_path = os.path.join(settings.RESUME_DIR, resume_id)
        self.input_path = os.path.join(self.base_path, "extracted_text.json")
        self.output_json_path = os.path.join(self.base_path, "clean_text.json")
        self.output_txt_path = os.path.join(self.base_path, "clean_text.txt")
        self.logger.info(f"TextCleaner initialized for {resume_id}")

    def _repair_encoding(self, text: str) -> str:
        """Fixes common PDF encoding artifacts."""
        replacements = {
            r"â€“": "-", r"Ã¢â‚¬â€œ": "-", r"Â": "", r"â€™": "'",
            r"â€œ": '"', r"â€?": '"', r"â€¢": "•", 
            r"\x0c": "" # Form feed
        }
        for pattern, replacement in replacements.items():
            text = text.replace(pattern, replacement)
        return text

    def _remove_noise(self, text: str) -> list[str]:
        """Removes portal buttons, system headers, footers, unusual UI links, and placeholders."""
        ui_patterns = [
            r"View\s*Uploaded\s*File", r"View\s*File", r"Download\s*File",
            r"Supporting\s*Documents?", r"VIEW\s*CONSULTANT\s*DETAILS",
            r"Click\s*here\s*to\s*view", r"ATTACHMENT\s*DETAILS",
            r"\|\|", r"---+"  # Separators
        ]
        for p in ui_patterns:
            text = re.sub(p, '', text, flags=re.IGNORECASE)
        
        noise_patterns = [
            r"Page \d+ of \d+", 
            r"Technical Proposal\s*\|\s*\d+",  
            r"INFRACON",
            r"Ministry of Road Transport.*India",
            r"Curriculum\s*Vitae.*Page\s*\d+",
            r"\d{2}/\d{2}/\d{4},\s*\d{2}:\d{2}",
            r"Document\s*Generated\s*on.*"
        ]
        
        unusual_link_pattern = r"https?://[^\s]+\.doc[^\s]*|https?://[^\s]+\.pdf[^\s]*"
        text = re.sub(unusual_link_pattern, '', text, flags=re.IGNORECASE)

        lines = text.splitlines()
        cleaned = []
        seen_headers = set()
        header_dedup_list = ["TECHNICAL PROPOSAL", "Proposed Position", "Bridge Structural Engineer"]

        for line in lines:
            line_s = line.strip()
            if not line_s or line_s == "\x0c":
                continue

            placeholders = [r":\s*Nil$", r":\s*NA$", r":\s*N/A$", r":\s*--$", r":\s*Not\s*Uploaded$"]
            if any(re.search(p, line_s, re.IGNORECASE) for p in placeholders):
                continue
            
            if any(re.search(p, line_s, re.IGNORECASE) for p in noise_patterns):
                continue

            is_static_header = any(h in line_s for h in header_dedup_list)
            if is_static_header:
                if line_s in seen_headers:
                    continue
                seen_headers.add(line_s)

            if re.match(r"^[#\s|:-]+$", line_s):
                continue

            if line_s.lower() == "view":
                continue

            cleaned.append(line_s)
        return cleaned

    def _compact_bio(self, lines: list[str]) -> list[str]:
        """Consolidates Basic Details into a single Bio line."""
        bio_fields = {}
        target_keys = ["Name", "DOB", "Father Name", "Email", "Mobile"]
        new_lines = []
        in_details = False
        
        for line in lines:
            if "BASIC DETAILS" in line or "Before EKYC Data" in line:
                in_details = True
                new_lines.append(line)
                continue
            
            if in_details:
                if " : " in line:
                    key, val = line.split(" : ", 1)
                    key_clean = key.strip().replace("##", "").strip()
                    if key_clean in target_keys:
                        bio_fields[key_clean] = val.strip()
                        continue
                
                if "QUALIFICATION" in line or "COMPANY" in line:
                    if bio_fields:
                        bio_str = " | ".join([f"{k}: {v}" for k, v in bio_fields.items()])
                        new_lines.append(f"BIO_SUMMARY : {bio_str}")
                        bio_fields = {}
                    in_details = False
                    new_lines.append(line)
                    continue
            
            new_lines.append(line)
        return new_lines

    def _join_fragments(self, lines: list[str]) -> list[str]:
        """Combines fragmented fields like Label : Value."""
        joined = []
        skip = 0
        for i in range(len(lines)):
            if skip > 0:
                skip -= 1
                continue
            curr = lines[i].strip()
            
            if i + 2 < len(lines):
                next_line = lines[i+1].strip()
                after_next = lines[i+2].strip()
                if next_line == ":" or next_line == "## : ##":
                    joined.append(f"{curr} : {after_next}")
                    skip = 2
                    continue
                
            if curr.endswith(":") and i + 1 < len(lines) and len(lines[i+1]) < 200 and len(curr) < 60:
                joined.append(f"{curr} {lines[i+1]}")
                skip = 1
                continue

            joined.append(curr)
        return joined

    def run(self):
        self.logger.info(f"Cleaning text for {self.resume_id}")
        if not os.path.exists(self.input_path):
            self.logger.error(f"Missing input artifact: {self.input_path}")
            raise FileNotFoundError(f"Missing input artifact: {self.input_path}")
            
        try:
            with open(self.input_path, 'r', encoding='utf-8') as f:
                raw_text = json.load(f)["content"]

            text = self._repair_encoding(raw_text)
            lines = self._remove_noise(text)
            lines = self._join_fragments(lines)
            lines = self._join_fragments(lines)
            lines = self._compact_bio(lines)
            
            final_content = "\n".join(lines)
            self.logger.info(f"Cleaned text reduced to {len(lines)} lines.")

            output_data = {
                "content": final_content,
                "cleaning_log": [
                    "Repaired PDF encoding artifacts.",
                    "Removed Rodic/INFRACON system noise.",
                    "Joined fragmented label-value pairs."
                ]
            }

            with open(self.output_json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)

            with open(self.output_txt_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
                
            self.logger.debug(f"Clean text artifacts saved for {self.resume_id}")
            return self.output_json_path
        except Exception as e:
            self.logger.error(f"Cleaning error: {e}", exc_info=True)
            raise
