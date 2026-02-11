import os
import json
import re
from config.settings import settings

class TextCleaner:
    """
    Stage 2: Advanced Text Cleaning.
    Normalizes raw extracted text by removing noise (headers, footers, links, UI artifacts),
    repairing encoding issues, and standardizing structural layout without losing data.
    """
    def __init__(self, resume_id: str):
        self.resume_id = resume_id
        self.base_path = os.path.join(settings.RESUME_DIR, resume_id)
        self.input_path = os.path.join(self.base_path, "extracted_text.json")
        self.output_json_path = os.path.join(self.base_path, "clean_text.json")
        self.output_txt_path = os.path.join(self.base_path, "clean_text.txt")

    def _repair_encoding(self, text: str) -> str:
        """Fixes common PDF encoding artifacts (Mojibake)."""
        replacements = {
            r"â€“": "-", r"Ã¢â‚¬â€œ": "-", r"Â": "", r"â€™": "'",
            r"â€œ": '"', r"â€?": '"', r"â€¢": "•", 
            r"\x0c": "" # Form feed
        }
        for pattern, replacement in replacements.items():
            text = text.replace(pattern, replacement)
        return text

    def _remove_links(self, text: str) -> str:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.sub(url_pattern, '', text)

    def _remove_ui_noise(self, text: str) -> str:
        """Removes portal buttons and repetitive system noise."""
        ui_patterns = [
            r"View\s*Uploaded\s*File", r"View\s*File", r"Download\s*File",
            r"Supporting\s*Documents?", r"View\s*Span", r"VIEW\s*CONSULTANT\s*DETAILS",
            r"\|\|", # Artifact from button separators
        ]
        for p in ui_patterns:
            text = re.sub(p, '', text, flags=re.IGNORECASE)
        return text

    def _remove_headers_footers(self, text: str) -> str:
        """Removes recurring proposal headers and page counters."""
        lines = text.splitlines()
        cleaned_lines = []
        
        noise_patterns = [
            r"Technical Proposal\s*\|\s*\d+", # Page titles with numbers
            r"INFRACON,\s*Ministry of Road Transport.*India", # System footers
            r"\d{2}/\d{2}/\d{4},\s*\d{2}:\d{2}", # System Timestamps
            r"^\d+/\d+$", # Page counters like 1/2, 2/2
        ]

        for line in lines:
            line_s = line.strip()
            if not line_s:
                continue
            # Check for systemic noise
            if any(re.search(p, line_s, re.IGNORECASE) for p in noise_patterns):
                continue
            
            # NEVER use .isdigit() on a whole line to delete it, 
            # as serial numbers (1, 2, 3) and data (40, 60) are critical.
            
            cleaned_lines.append(line_s)
            
        return "\n".join(cleaned_lines)

    def _join_fragmented_data(self, text: str) -> str:
        """
        Combines fragmented fields like:
        'Name of Staff' \n ':' \n 'John Doe' 
        into:
        'Name of Staff : John Doe'
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines: return ""
        
        joined = []
        skip_count = 0
        
        for i in range(len(lines)):
            if skip_count > 0:
                skip_count -= 1
                continue
                
            curr = lines[i]
            
            # Lookahead check for fragmented colons or values
            # Case 1: "Label" \n ":" \n "Value"
            if i + 2 < len(lines) and lines[i+1] == ":" and len(lines[i+2]) < 300:
                joined.append(f"{curr} : {lines[i+2]}")
                skip_count = 2
                continue
                
            # Case 2: "Label :" \n "Value"
            if curr.endswith(":") and i + 1 < len(lines) and len(lines[i+1]) < 300:
                # Don't join if the label is too long (likely not a label)
                if len(curr) < 50:
                    joined.append(f"{curr} {lines[i+1]}")
                    skip_count = 1
                    continue

            # Case 3: "Label" \n ": Value"
            if i + 1 < len(lines) and lines[i+1].startswith(":") and len(curr) < 50:
                joined.append(f"{curr} {lines[i+1]}")
                skip_count = 1
                continue
            
            joined.append(curr)
                
        return "\n".join(joined)

    def _normalize_structure(self, text: str) -> str:
        """Collapses excessive whitespace."""
        # Normalize Horizontal space
        text = re.sub(r'[ \t]+', ' ', text)
        # Normalize Vertical space (reduce 3+ blanks to 1)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text.strip()

    def run(self):
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Missing input: {self.input_path}")
            
        with open(self.input_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        cleaned_pages = []
        total_pages = len(raw_data["pages"])
        
        for page in raw_data["pages"]:
            page_num = page["page_number"]
            page_text = page["text"]
            
            # Step-by-step cleaning
            page_text = self._repair_encoding(page_text)
            page_text = self._remove_links(page_text)
            page_text = self._remove_ui_noise(page_text)
            page_text = self._remove_headers_footers(page_text)
            
            # Run joining twice to catch nested fragments
            page_text = self._join_fragmented_data(page_text)
            page_text = self._join_fragmented_data(page_text)
            
            if len(page_text.strip()) > 10:
                # Inject a visible page marker for the Semantic Blocker to detect page spans
                marked_text = f"[PAGE_START_{page_num}]\n{page_text}\n[PAGE_END_{page_num}]"
                cleaned_pages.append(marked_text.strip())

        # Final join and structural cleanup
        full_content = "\n\n".join(cleaned_pages)
        final_content = self._normalize_structure(full_content)

        # Artifact Generation
        output_data = {
            "content": final_content,
            "cleaning_log": [
                f"Retained {len(cleaned_pages)} pages. Filtered portal noise.",
                "REMOVED aggressive digit-only line deletion to preserve serial numbers and data.",
                "Implemented intelligent label-value joining.",
                "Repaired PDF encoding artifacts."
            ]
        }

        with open(self.output_json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)

        with open(self.output_txt_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        return self.output_json_path

if __name__ == "__main__":
    TEST_UUID = "412fb8c8-865f-4872-b247-fbac12d7babf"
    cleaner = TextCleaner(TEST_UUID)
    try:
        path = cleaner.run()
        print(f"✅ Recovery Cleaning Complete!")
        print(f"📝 Fixed Text ready at: {cleaner.output_txt_path}")
    except Exception as e:
        print(f"❌ Error during recovery: {e}")
