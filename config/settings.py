import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Resume Parser POC"
    DEBUG: bool = True
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESUME_DIR: str = os.path.join(BASE_DIR, "resume")
    
    # Model Config (OpenAI)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo-0125"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Chunking
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # OCR
    TESSERACT_PATH: Optional[str] = None # Path to tesseract executable if not in PATH

    class Config:
        env_file = ".env"

settings = Settings()
