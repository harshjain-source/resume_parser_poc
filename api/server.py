import os
import shutil
import json
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from main_pipeline import ResumePipeline

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_resume_task(pdf_path: str, resume_id: str, filename: str):
    """Background task to run the full pipeline."""
    try:
        pipeline = ResumePipeline(resume_id=resume_id, original_filename=filename)
        pipeline.run(pdf_path)
        # Clean up the temporary upload
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    except Exception as e:
        print(f"FAILED BACKGROUND PROCESS {resume_id}: {e}")

@app.post("/upload", status_code=201)
async def upload_resume(file: UploadFile, background_tasks: BackgroundTasks):
    """
    Upload and trigger processing.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    resume_id = str(os.urandom(8).hex()) # Simple hex ID for API
    temp_dir = os.path.join(settings.RESUME_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_path = os.path.join(temp_dir, f"{resume_id}_{file.filename}")
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Trigger the pipeline in the background
    background_tasks.add_task(process_resume_task, temp_path, resume_id, file.filename)
    
    return {
        "resume_id": resume_id,
        "status": "processing",
        "message": "Resume uploaded and processing started."
    }

@app.get("/result/{resume_id}")
async def get_result(resume_id: str):
    """Fetch the final parsed JSON for a resume."""
    result_path = os.path.join(settings.RESUME_DIR, resume_id, "final_resume.json")
    
    if not os.path.exists(result_path):
        # Check if folder exists at least
        if os.path.exists(os.path.join(settings.RESUME_DIR, resume_id)):
            return {"status": "processing", "message": "Resume is still being analyzed."}
        raise HTTPException(status_code=404, detail="Resume ID not found.")
        
    with open(result_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/health")
def health_check():
    return {"status": "ok"}


