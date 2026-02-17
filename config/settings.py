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
    
    # Model Configs
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    SARVAM_API_KEY: Optional[str] = None
    
    # Provider Registry
    LLM_MODELS: dict = {
        "Google": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.5-flash-lite"],
        "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "Anthropic": ["claude-3-5-sonnet-latest", "claude-3-haiku-20240307"],
        "Sarvam": ["sarvam-m"],
        "Ollama (Local)": ["llama3", "mistral", "phi3"]
    }
    
    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        extra = "ignore"

    def get_timestamp(self) -> str:
        import datetime
        return datetime.datetime.now().isoformat()

settings = Settings()
