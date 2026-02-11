import os
import json
import fitz  # PyMuPDF
from config.settings import settings

class TextExtractor:
    """
    Stage 1: Text Extraction.
    Uses PyMuPDF (fitz) for fast, independent text extraction.
    """
    def __init__(self, resume_id: str, original_filename: str = None):
        self.resume_id = resume_id
        self.original_filename = original_filename
        # Build paths based on UUID
        base_path = os.path.join(settings.RESUME_DIR, resume_id)
        self.pdf_path = os.path.join(base_path, "original.pdf")
        self.meta_path = os.path.join(base_path, "metadata.json")
        self.output_json_path = os.path.join(base_path, "extracted_text.json")
        self.output_txt_path = os.path.join(base_path, "extracted_text.txt")

    def run(self):
        """
        Extracts text and saves to structured JSON.
        """
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"Missing PDF at {self.pdf_path}")

        # Determine original filename
        final_filename = self.original_filename
        
        # If not provided in init, try to read from metadata.json
        if not final_filename and os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    final_filename = meta.get("original_filename")
            except Exception:
                pass
        
        # Default if still nothing
        final_filename = final_filename or "unknown"

        # 1. Open Document
        with fitz.open(self.pdf_path) as doc:
            data = {
                "pages": [],
                "metadata": {
                    "total_pages": len(doc), 
                    "resume_id": self.resume_id,
                    "original_filename": final_filename
                }
            }

            # 2. Extract Text from each page with Layout Awareness (Blocks)
            for page_num, page in enumerate(doc, 1):
                # get_text("blocks") returns: (x0, y0, x1, y1, "text", block_no, block_type)
                blocks = page.get_text("blocks")
                
                # Sort blocks: vertical first (y0), then horizontal (x0)
                # This preserves reading flow for tables and multi-column sections
                blocks.sort(key=lambda b: (b[1], b[0]))
                
                # Filter empty blocks and join with clear separation
                page_content = [b[4].strip() for b in blocks if b[4].strip()]
                
                data["pages"].append({
                    "page_number": page_num,
                    "text": "\n".join(page_content),
                    "origin": "pymupdf_blocks"
                })

        # 3. Save as JSON and TXT artifacts
        os.makedirs(os.path.dirname(self.output_json_path), exist_ok=True)
        
        # Save JSON
        with open(self.output_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Save Plain Text (for easy reading)
        full_text = "\n\n".join([page["text"] for page in data["pages"]])
        with open(self.output_txt_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
            
        return self.output_json_path

if __name__ == "__main__":
    # Just for testing purposes:
    TEST_UUID = "412fb8c8-865f-4872-b247-fbac12d7babf"
    # Note: If no original_filename is passed, it will try to read from metadata.json
    extractor = TextExtractor(TEST_UUID, original_filename="BE.pdf")
    try:
        path = extractor.run()
        print(f"✅ Success! Data extracted to: {path}")
        print(f"📄 Plain text saved to: {extractor.output_txt_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
