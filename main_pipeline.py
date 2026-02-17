import os
import uuid
import datetime
import json
import time
from pipeline.text_extractor import TextExtractor
from pipeline.image_extractor import ImageExtractor
from pipeline.text_cleaner import TextCleaner
from pipeline.semantic_blocker import SemanticBlocker
from pipeline.llm_parser import LLMParser
from config.settings import settings
from config.logger_config import get_logger

class ResumePipeline:
    """
    Orchestrator for the entire Resume Parser pipeline.
    Stages 1, 1.5, 2, 3, and 7.
    """
    def __init__(self, resume_id: str = None, original_filename: str = "unknown", llm_provider: str = "Google", llm_model: str = "gemini-2.5-flash-lite"):
        self.resume_id = resume_id or str(uuid.uuid4())
        self.original_filename = original_filename
        self.output_dir = os.path.join(settings.RESUME_DIR, self.resume_id)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize session logger
        log_file = os.path.join(self.output_dir, "pipeline.log")
        self.logger = get_logger(f"Pipeline_{self.resume_id[:8]}", log_file=log_file)
        self.logger.info(f"Initializing pipeline for {original_filename} (ID: {self.resume_id})")

        # Initialize stages
        self.extractor = TextExtractor(self.resume_id, original_filename)
        self.image_extractor = ImageExtractor(self.resume_id, self.output_dir)
        self.cleaner = TextCleaner(self.resume_id)
        self.blocker = SemanticBlocker(self.resume_id)
        self.parser = LLMParser(provider=llm_provider, model_name=llm_model)

    def _report_progress(self, stage_name, stage_start, total_start, callback):
        now = time.time()
        duration = now - stage_start
        relative_start = stage_start - total_start
        relative_end = now - total_start
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Format: [13:30:05] Stage 1: Extraction | Time: 0.10s - 0.55s (0.45s)
        full_msg = f"[{timestamp}] {stage_name} | Range: {relative_start:.2f}s - {relative_end:.2f}s | Duration: {duration:.2f}s"
        
        self.logger.info(full_msg)
        if callback:
            callback(full_msg)

    def run(self, pdf_path: str, progress_callback=None):
        """Runs the full pipeline transition for a PDF file."""
        total_start = time.time()
        print(f"🚀 Starting Pipeline for: {self.original_filename} (ID: {self.resume_id})")
        
        # 0. Preparation
        prep_start = time.time()
        target_pdf = os.path.join(self.output_dir, "original.pdf")
        import shutil
        shutil.copy(pdf_path, target_pdf)
        
        meta = {
            "resume_id": self.resume_id,
            "original_filename": self.original_filename,
            "processed_at": datetime.datetime.now().isoformat()
        }
        with open(os.path.join(self.output_dir, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=4)
        self._report_progress("📁 Step 0: Prep & Sync", prep_start, total_start, progress_callback)

        try:
            # 1. Extraction
            s1_start = time.time()
            self.extractor.run()
            self._report_progress("📝 Stage 1: Text Extraction", s1_start, total_start, progress_callback)
            
            # 2. Image Extraction
            s2_start = time.time()
            photo_path = self.image_extractor.run(target_pdf)
            self._report_progress("📸 Stage 2: Photo Extraction", s2_start, total_start, progress_callback)
            
            # 3. Cleaning
            s3_start = time.time()
            self.cleaner.run()
            self._report_progress("🧹 Stage 3: Text Cleaning", s3_start, total_start, progress_callback)
            
            # 4. Blocking
            s4_start = time.time()
            self.blocker.run()
            self._report_progress("🧩 Stage 4: Semantic Blocking", s4_start, total_start, progress_callback)
            
            # 5. LLM Parsing
            s5_start = time.time()
            result_path = self.parser.run(self.resume_id, progress_callback=progress_callback)
            self._report_progress("🤖 Stage 5: LLM AI Parsing", s5_start, total_start, progress_callback)
            
            # 6. Injection
            s6_start = time.time()
            if photo_path:
                with open(result_path, "r", encoding="utf-8") as f:
                    final_data = json.load(f)
                final_data["metadata"] = final_data.get("metadata", {})
                final_data["metadata"]["candidate_photo"] = photo_path
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump(final_data, f, indent=4, ensure_ascii=False)
            self._report_progress("💉 Stage 6: Data Injection", s6_start, total_start, progress_callback)
            
            total_duration = time.time() - total_start
            final_msg = f"✅ Pipeline Complete! (Total Time: {total_duration:.2f}s)"
            print(final_msg)
            if progress_callback: progress_callback(final_msg)
            
            # --- NEW: Rename folder to include candidate name ---
            try:
                # Re-read to get the most accurate name after injection/post-processing
                with open(result_path, "r", encoding="utf-8") as f:
                    final_data = json.load(f)
                
                personal = final_data.get("sections", {}).get("PERSONAL_INFO", {})
                if isinstance(personal, list) and personal:
                    personal = personal[0]
                
                raw_name = personal.get("full_name") or personal.get("name") or "unknown"
                # Clean name: lowercase, no dots, underscores for spaces
                clean_name = "".join(c if c.isalnum() else "_" for c in raw_name.lower()).strip("_")
                
                # Create the final ID
                new_id = f"{self.resume_id}_{clean_name}"
                new_output_dir = os.path.join(settings.RESUME_DIR, new_id)
                
                # Check for collision and then move
                if not os.path.exists(new_output_dir):
                    os.rename(self.output_dir, new_output_dir)
                    # Update local state so return path is correct
                    self.output_dir = new_output_dir
                    self.resume_id = new_id
                    result_path = os.path.join(self.output_dir, "final_resume.json")
                    if progress_callback:
                        progress_callback(f"🏷️ Profile Labelled: {clean_name}")
                else:
                    if progress_callback:
                        progress_callback("ℹ️ Note: Profile with this name already exists, using existing folder.")
            except Exception as rename_err:
                print(f"⚠️ Rename skipped: {rename_err}")

            return result_path
            
        except Exception as e:
            err_msg = f"❌ Pipeline Failed: {e}"
            self.logger.error(err_msg, exc_info=True)
            if progress_callback: progress_callback(err_msg)
            raise

if __name__ == "__main__":
    # Example usage:
    # pdf = "path/to/resume.pdf"
    # pipeline = ResumePipeline(original_filename=os.path.basename(pdf))
    # pipeline.run(pdf)
    pass
