import os
import json
import re
from config.settings import settings

class SemanticBlocker:
    """
    Stage 3: Semantic Block Creation.
    Dynamically groups clean text into logical buckets (Education, Experience, etc.)
    using scoring heuristics and a state machine. Designed for 20-200 page resumes.
    """
    
    # Broad patterns to identify section starts across different formats
    CATEGORIES = {
        "PERSONAL": [r"profile", r"personal", r"contact", r"basic details", r"candidate"],
        "EDUCATION": [r"qualification", r"academic", r"education", r"degree"],
        "EXPERIENCE": [r"work", r"experience", r"employment", r"professional", r"detailed work"],
        "SKILLS": [r"skills", r"expertise", r"competencies", r"technologies"],
        "PROJECTS": [r"projects", r"assignments", r"case studies", r"detailed.*work"]
    }

    def __init__(self, resume_id: str):
        self.resume_id = resume_id
        self.base_path = os.path.join(settings.RESUME_DIR, resume_id)
        self.input_path = os.path.join(self.base_path, "clean_text.json")
        self.output_path = os.path.join(self.base_path, "semantic_blocks.json")

    def _score_heading(self, line: str) -> tuple[int, str]:
        """Heuristic scoring to determine if a line is a section heading."""
        line = line.strip()
        if not line or len(line.split()) > 8:
            return 0, "UNCERTAIN"
        
        score = 0
        detected_cat = "UNCERTAIN"
        
        # 1. Pattern Match Score (High weights)
        for cat, patterns in self.CATEGORIES.items():
            if any(re.search(p, line, re.IGNORECASE) for p in patterns):
                score += 6
                detected_cat = cat
                break
        
        # 2. Visual Style Score
        if line.isupper(): score += 3
        if len(line.split()) <= 3: score += 2
        
        return score, detected_cat

    def run(self):
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Missing input artifact: {self.input_path}")
            
        with open(self.input_path, 'r', encoding='utf-8') as f:
            content = json.load(f)["content"]

        lines = content.splitlines()
        blocks = []
        
        # State tracking
        current_cat = "HEADER"
        current_text = []
        current_page = 1
        start_page = 1
        block_count = 1

        for line in lines:
            # Detect Page Transitions
            if "[PAGE_START_" in line:
                page_match = re.search(r"PAGE_START_(\d+)", line)
                if page_match:
                    current_page = int(page_match.group(1))
                continue
            if "[PAGE_END_" in line: continue

            # Score the current line
            score, category = self._score_heading(line)
            
            # If line is a strong heading (score >= 6), trigger a transition
            if score >= 6 and category != current_cat:
                # Save previous block if it has content
                if current_text:
                    blocks.append({
                        "id": f"block_{block_count:03d}",
                        "category": current_cat,
                        "raw_text": "\n".join(current_text).strip(),
                        "page_span": [start_page, current_page]
                    })
                    block_count += 1
                
                # Start new block
                current_cat = category
                current_text = [line]
                start_page = current_page
            else:
                current_text.append(line)

        # Final flush
        if current_text:
            blocks.append({
                "id": f"block_{block_count:03d}",
                "category": current_cat,
                "raw_text": "\n".join(current_text).strip(),
                "page_span": [start_page, current_page]
            })

        # Save JSON Artifact
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(blocks, f, indent=4, ensure_ascii=False)

        # Save human-readable Text Artifact
        output_txt_path = os.path.join(self.base_path, "semantic_blocks.txt")
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            for b in blocks:
                header = f"=== {b['category']} (Pages: {b['page_span'][0]}-{b['page_span'][1]}) ==="
                f.write(f"{header}\n")
                f.write(b['raw_text'])
                f.write("\n" + "="*len(header) + "\n\n")
            
        return self.output_path

if __name__ == "__main__":
    TEST_UUID = "412fb8c8-865f-4872-b247-fbac12d7babf"
    blocker = SemanticBlocker(TEST_UUID)
    try:
        path = blocker.run()
        print(f"✅ Stage 3 Complete! Blocks saved to: {path}")
    except Exception as e:
        print(f"❌ Error in Stage 3: {e}")
