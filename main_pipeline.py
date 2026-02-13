import os
import uuid
import datetime
import json
from pipeline.text_extractor import TextExtractor
from pipeline.image_extractor import ImageExtractor
from pipeline.text_cleaner import TextCleaner
from pipeline.semantic_blocker import SemanticBlocker
from pipeline.llm_parser import LLMParser
from config.settings import settings

class ResumePipeline:
    """
    Orchestrator for the entire Resume Parser pipeline.
    Stages 1, 1.5, 2, 3, and 7.
    """
    def __init__(self, resume_id: str = None, original_filename: str = "unknown"):
        self.resume_id = resume_id or str(uuid.uuid4())
        self.original_filename = original_filename
        self.output_dir = os.path.join(settings.RESUME_DIR, self.resume_id)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize stages
        self.extractor = TextExtractor(self.resume_id, original_filename)
        self.image_extractor = ImageExtractor(self.resume_id, self.output_dir)
        self.cleaner = TextCleaner(self.resume_id)
        self.blocker = SemanticBlocker(self.resume_id)
        self.parser = LLMParser()

    def run(self, pdf_path: str):
        """Runs the full pipeline transition for a PDF file."""
        print(f"🚀 Starting Pipeline for: {self.original_filename} (ID: {self.resume_id})")
        
        # 0. Preparation: Sync PDF to internal storage
        target_pdf = os.path.join(self.output_dir, "original.pdf")
        import shutil
        shutil.copy(pdf_path, target_pdf)
        
        # Save Metadata
        meta = {
            "resume_id": self.resume_id,
            "original_filename": self.original_filename,
            "processed_at": datetime.datetime.now().isoformat()
        }
        with open(os.path.join(self.output_dir, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=4)

        try:
            # 1. Extraction
            print("⏳ Stage 1: Extracting structural text...")
            self.extractor.run()
            
            # 1.5 Image Extraction
            print("⏳ Stage 1.5: Extracting candidate photo...")
            photo_path = self.image_extractor.run(target_pdf)
            
            # 2. Cleaning
            print("⏳ Stage 2: Cleaning text and removing noise...")
            self.cleaner.run()
            
            # 3. Blocking
            print("⏳ Stage 3: Creating semantic blocks...")
            self.blocker.run()
            
            # 7. LLM Parsing
            print("⏳ Stage 7: LLM-based structured extraction...")
            result_path = self.parser.run(self.resume_id)
            
            # Inject Photo Path into final JSON
            if photo_path:
                print(f"📸 Injecting photo path: {photo_path}")
                with open(result_path, "r", encoding="utf-8") as f:
                    final_data = json.load(f)
                
                final_data["metadata"] = final_data.get("metadata", {})
                final_data["metadata"]["candidate_photo"] = photo_path
                
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump(final_data, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Pipeline Complete! Result saved to: {result_path}")
            return result_path
            
        except Exception as e:
            print(f"❌ Pipeline Failed: {e}")
            raise

if __name__ == "__main__":
    # Example usage:
    # pdf = "path/to/resume.pdf"
    # pipeline = ResumePipeline(original_filename=os.path.basename(pdf))
    # pipeline.run(pdf)
    pass
