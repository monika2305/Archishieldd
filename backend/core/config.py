import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

class Settings(BaseSettings):
    APP_NAME: str = "ArchiShield API"
    ENVIRONMENT: str = "development"
    GROQ_API_KEY: str = ""
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
        "http://localhost:3000", "http://127.0.0.1:3000"
    ]
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    N8N_ENABLED: bool = True
    N8N_WEBHOOK_URL: str = ""
    N8N_WEBHOOK_SECRET: str = "archishield-n8n-secret-2026"
    BACKEND_INTERNAL_URL: str = "https://welcome-obtained-guarantee-hollow.trycloudflare.com"
    NBC_COMPLIANCE_THRESHOLD: float = 80.0
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8001"
    AUDIT_LOG_PATH: str = "data/autoops_audit.jsonl"
    SUPABASE_URL: str = "https://ufttkgyvhmwvskklaxne.supabase.co"
    SUPABASE_KEY: str = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVmdHRrZ3l2aG13dnNra"
        "2xheG5lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwODA4MjksImV"
        "4cCI6MjA5NjY1MjgyOX0"
        ".CXRJJdQn21ouipdmBgoTE37L-d5KKfML1YKlWxZGN1E"
    )
    SUPABASE_BUCKET: str = "innovescence-ifc-files"

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
