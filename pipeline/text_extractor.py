import os
import json
import fitz  # PyMuPDF
from config.settings import settings
from config.logger_config import get_logger

class TextExtractor:
    """
    Stage 1: Text Extraction.
    Extracts text and preserves headers/bolding using font data.
    """
    def __init__(self, resume_id: str, original_filename: str = None):
        self.resume_id = resume_id
        self.original_filename = original_filename
        self.logger = get_logger("TextExtractor")
        self.logger.info(f"TextExtractor initialized for {resume_id}")
        
        # Build paths based on UUID
        base_path = os.path.join(settings.RESUME_DIR, resume_id)
        self.pdf_path = os.path.join(base_path, "original.pdf")
        self.meta_path = os.path.join(base_path, "metadata.json")
        self.output_json_path = os.path.join(base_path, "extracted_text.json")
        self.output_txt_path = os.path.join(base_path, "extracted_text.txt")
        self.output_md_path = os.path.join(base_path, "extracted_text.md")

    def run(self):
        """
        Extracts structural text and saves to artifacts.
        """
        self.logger.info(f"Starting text extraction for PDF: {self.pdf_path}")
        if not os.path.exists(self.pdf_path):
            self.logger.error(f"Missing PDF at {self.pdf_path}")
            raise FileNotFoundError(f"Missing PDF at {self.pdf_path}")

        try:
            doc = fitz.open(self.pdf_path)
            raw_md = []
            
            for page in doc:
                page_blocks = []
                for b in page.get_text("dict")["blocks"]:
                    if "lines" in b:
                        block_text = []
                        for l in b["lines"]:
                            line = "".join([s["text"] for s in l["spans"]])
                            if l["spans"]:
                                span = l["spans"][0]
                                # Use font size and flags (bit 4 is bold) for MD structure
                                if span["size"] > 14: 
                                    line = f"# {line}"
                                elif span["size"] > 11 or (span["flags"] & 2**4): 
                                    line = f"## {line}"
                            block_text.append(line)
                        page_blocks.append("\n".join(block_text))
                
                raw_md.append("\n".join(page_blocks))
                
            total_pages = len(doc)
            doc.close()
            full_text = "\n\n".join(raw_md)
            self.logger.info(f"Successfully extracted {total_pages} pages.")

            # Artifact Generation
            data = {
                "content": full_text,
                "metadata": {
                    "total_pages": total_pages,
                    "resume_id": self.resume_id,
                    "original_filename": self.original_filename or "unknown"
                }
            }

            os.makedirs(os.path.dirname(self.output_json_path), exist_ok=True)
            
            with open(self.output_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            with open(self.output_txt_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
                
            with open(self.output_md_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
                
            self.logger.debug(f"Extraction artifacts saved for {self.resume_id}")
            return self.output_json_path
        except Exception as e:
            self.logger.error(f"Extraction error: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    import shutil
    TEST_UUID = "test_extraction_debug"
    SOURCE_PDF = r"C:\Users\Dell\Downloads\rodic resumes\rodic resumes\BE.pdf"
    test_dir = os.path.join(settings.RESUME_DIR, TEST_UUID)
    os.makedirs(test_dir, exist_ok=True)
    if os.path.exists(SOURCE_PDF):
        shutil.copy(SOURCE_PDF, os.path.join(test_dir, "original.pdf"))
        extractor = TextExtractor(TEST_UUID, "BE.pdf")
        result = extractor.run()
        print(f"✅ Extraction Successful!")
    else:
        print(f"❌ Error: Could not find the PDF at {SOURCE_PDF}")
