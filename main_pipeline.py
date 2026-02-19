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

from utils.code_integrity import verify_code_integrity

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

    def run(self, pdf_path: str, progress_callback=None):
        """Runs the full pipeline transition for a PDF file with time tracking."""
        import time
        start_total = time.time()
        
        def log(msg, detail=None):
            print(f"⏳ {msg}")
            if progress_callback:
                progress_callback(msg, detail)

        # --- PHASE 0: CODE INTEGRITY CHECK ---
        log("Phase 0: Verifying code integrity...")
        success, message = verify_code_integrity()
        if not success:
            log("❌ PIPELINE ABORTED: Code Integrity Failure!")
            raise SyntaxError(message)

        log(f"🚀 Starting Pipeline for: {self.original_filename}")
        
        # 0. Preparation
        t0 = time.time()
        target_pdf = os.path.join(self.output_dir, "original.pdf")
        import shutil
        shutil.copy(pdf_path, target_pdf)
        
        meta = {
            "resume_id": self.resume_id,
            "original_filename": self.original_filename,
            "processed_at": datetime.datetime.now().isoformat(),
            "timelines": []
        }
        
        def add_timeline(stage, duration):
            elapsed = time.time() - start_total
            start = elapsed - duration
            meta["timelines"].append(f"{stage}: ({start:.2f}s - {elapsed:.2f}s)")
            log(f"{stage}", f"Interval: {start:.2f}s - {elapsed:.2f}s")

        add_timeline("Stage 0: Preparation", time.time() - t0)

        try:
            # 1. Extraction
            t1 = time.time()
            log("Stage 1: Structural text extraction...")
            self.extractor.run()
            add_timeline("Stage 1: Extraction", time.time() - t1)
            
            # 1.5 Image Extraction
            t15 = time.time()
            log("Stage 1.5: Photo extraction...")
            photo_path = self.image_extractor.run(target_pdf)
            add_timeline("Stage 1.5: Photo Extraction", time.time() - t15)
            
            # 2. Cleaning
            t2 = time.time()
            log("Stage 2: Text cleaning & noise removal...")
            self.cleaner.run()
            add_timeline("Stage 2: Cleaning", time.time() - t2)
            
            # 3. Blocking
            t3 = time.time()
            log("Stage 3: Semantic blocking...")
            self.blocker.run()
            add_timeline("Stage 3: Blocking", time.time() - t3)

            # 6.5 Validation
            tv = time.time()
            log("Stage 4: Pre-flight validation...")
            blocks_path = os.path.join(self.output_dir, "semantic_blocks.json")
            if not os.path.exists(blocks_path):
                raise RuntimeError("Validation Error: Missing blocks file.")

            with open(blocks_path, "r", encoding="utf-8") as f:
                blocks = json.load(f)
                total_text = "".join(blocks.values())
                
            if len(total_text.strip()) < 100:
                raise ValueError("Validation Error: Insufficient text content.")
            add_timeline("Stage 4: Validation", time.time() - tv)

            # 7. LLM Parsing
            t7 = time.time()
            log("Stage 5: LLM Synthesis (Structured JSON)...")
            result_path = self.parser.run(self.resume_id)
            add_timeline("Stage 5: LLM Synthesis", time.time() - t7)
            
            # Inject Photo & Timelines
            with open(result_path, "r", encoding="utf-8") as f:
                final_data = json.load(f)
            
            if photo_path:
                final_data["metadata"] = final_data.get("metadata", {})
                final_data["metadata"]["candidate_photo"] = photo_path
            
            final_data["timelines"] = meta["timelines"]
            
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=4, ensure_ascii=False)
            
            # Update metadata.json one last time
            meta["usage"] = final_data.get("usage", {})
            with open(os.path.join(self.output_dir, "metadata.json"), "w") as f:
                json.dump(meta, f, indent=4)

            total_time = time.time() - start_total
            log("✅ Pipeline Complete!", f"Total Time: {total_time:.2f}s")
            return result_path
            
        except Exception as e:
            log(f"❌ Pipeline Failed: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage:
    # pdf = "path/to/resume.pdf"
    # pipeline = ResumePipeline(original_filename=os.path.basename(pdf))
    # pipeline.run(pdf)
    pass
