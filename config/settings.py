import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Resume Parser POC"
    DEBUG: bool = True
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESUME_DIR: str = os.path.join(BASE_DIR, "processed_resumes")
    
    # Model Config (Gemini)
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    
    # Model Config (Groq)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    
    # Model Config (Sarvam)
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_MODEL: str = "sarvam-m"
    SARVAM_BASE_URL: str = "https://api.sarvam.ai"
    
    # Selection
    DEFAULT_PROVIDER: str = "google" # "google", "groq", or "sarvam"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_timestamp(self) -> str:
        import datetime
        return datetime.datetime.now().isoformat()

settings = Settings()
