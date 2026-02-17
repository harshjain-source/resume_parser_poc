import re
from typing import List, Dict, Any
from config.logger_config import get_logger

class ChunkManager:
    """
    Utility to handle 'Mega-Sections' by splitting them into logical sub-chunks.
    Uses anchor-based splitting for data integrity, with a hard-limit fallback.
    """
    
    # Anchors that usually signify the start of a new entry in a resume
    ANCHORS = [
        r"\d{1,2}/\d{1,2}/\d{2,4}",                  # 01/12/1995 or 12/2020
        r"\d{1,2}/\d{4}",                            # 12/2020
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}", # January 2022
        r"\d{4}\s*-\s*(?:\d{4}|Present|Now|current)", # 2018 - 2022 or 2018 - Present
        r"(?:Employer|Company|Client|Institution|Project Name|Sno)\s*[:.]", # Common labels
        r"^\s*•\s*",                                 # Bullet points
        r"^\s*-\s*",                                 # Hyphen bullets
        r"^\d+\s*[\.\)]\s+"                          # Numbered lists: 1. or 1)
    ]

    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
        # Hard limit is 1.5x max_tokens. If we reach this without an anchor, split anyway.
        self.hard_limit = int(max_tokens * 1.5)
        self.logger = get_logger("ChunkManager")
        self.anchor_pattern = re.compile("|".join(self.ANCHORS), re.IGNORECASE | re.MULTILINE)

    def _estimate_tokens(self, text: str) -> int:
        """Improved token estimation: char count / 4 is a standard safe fallback."""
        if not text:
            return 0
        # Words * 1.3 is good for English, but characters / 3 is safer for structural text
        return max(int(len(text.split()) * 1.3), int(len(text) / 3))

    def prepare_chunks(self, text: str, section_name: str, candidate_name: str = "Unknown") -> List[Dict[str, Any]]:
        """
        Splits a large text block into a list of structured sub-chunks.
        """
        estimated_total = self._estimate_tokens(text)
        
        if estimated_total <= self.max_tokens:
            self.logger.debug(f"Section {section_name} fits in one chunk ({estimated_total} tokens)")
            return [{
                "metadata": {
                    "section": section_name,
                    "candidate_name": candidate_name,
                    "part": 1,
                    "total_parts": 1,
                    "is_continuation": False
                },
                "content": text
            }]

        self.logger.info(f"Section {section_name} exceeds limit ({estimated_total} > {self.max_tokens}). Splitting...")
        
        raw_chunks = []
        lines = text.splitlines()
        current_buffer = []
        current_buffer_tokens = 0

        for line in lines:
            line_tokens = self._estimate_tokens(line)
            is_anchor = self.anchor_pattern.search(line)
            
            # TRIGGER SPLIT IF:
            # 1. We are over the soft limit AND see an anchor (Logical Split)
            # 2. OR we are over the hard limit (Safety Split)
            should_split = False
            if current_buffer_tokens + line_tokens > self.max_tokens:
                if is_anchor:
                    should_split = True
                elif current_buffer_tokens + line_tokens > self.hard_limit:
                    should_split = True
                    self.logger.debug(f"Hard-split triggered for {section_name} at {current_buffer_tokens} tokens.")

            if should_split and current_buffer:
                raw_chunks.append("\n".join(current_buffer))
                current_buffer = []
                current_buffer_tokens = 0
            
            current_buffer.append(line)
            current_buffer_tokens += line_tokens

        if current_buffer:
            raw_chunks.append("\n".join(current_buffer))

        self.logger.info(f"{section_name} partitioned into {len(raw_chunks)} chunks.")

        # Wrap in metadata
        total_parts = len(raw_chunks)
        structured_chunks = []
        for i, content in enumerate(raw_chunks):
            structured_chunks.append({
                "metadata": {
                    "section": section_name,
                    "candidate_name": candidate_name,
                    "part": i + 1,
                    "total_parts": total_parts,
                    "is_continuation": i > 0
                },
                "content": content
            })
            
        return structured_chunks
