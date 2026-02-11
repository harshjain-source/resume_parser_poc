import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings

app = FastAPI(title=settings.APP_NAME)

# CORS (Optional, good for frontend dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload", status_code=201)
async def upload_resume(file: UploadFile, background_tasks: BackgroundTasks):
    """
    Upload a resume PDF.
    
    Process:
    1. Validate file type (PDF only).
    2. Generate unique UUID.
    3. Save to `resume/{uuid}/original.pdf`.
    4. Return UUID for tracking.
    """
    # 1. Validation
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # 2. Setup
    resume_id = str(uuid.uuid4())
    resume_dir = os.path.join(settings.RESUME_DIR, resume_id)
    os.makedirs(resume_dir, exist_ok=True)
    
    # 3. Save File
    file_path = os.path.join(resume_dir, "original.pdf")
    meta_path = os.path.join(resume_dir, "metadata.json")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Save original filename metadata
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"original_filename": file.filename}, f)
            
    except Exception as e:
        # Cleanup on failure
        shutil.rmtree(resume_dir)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # TODO: Trigger background pipeline here
    # background_tasks.add_task(run_pipeline, resume_id)
    
    return {
        "uuid": resume_id,
        "message": "Resume uploaded successfully",
        "original_filename": file.filename
    }
    
@app.get("/health")
def health_check():
    return {"status": "ok"}


