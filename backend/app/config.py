from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Cyber Investigation Assistant"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # MongoDB Atlas
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "cyber_investigation"

    # AI / LLM (Groq API)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str = ""  # Deprecated - replaced by GROQ_API_KEY

    # Authentication & Security
    JWT_SECRET_KEY: str = "dev-insecure-secret-key-replace-in-production-must-be-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours forensic session
    BOOTSTRAP_SECRET_KEY: str = ""  # Secret token required to invoke /api/auth/bootstrap API

    def validate_production_security(self):
        if self.ENVIRONMENT.lower() == "production":
            if (
                not self.JWT_SECRET_KEY
                or "dev-insecure" in self.JWT_SECRET_KEY
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: JWT_SECRET_KEY must be a cryptographically "
                    "secure secret with at least 32 characters in production environment."
                )

    @property
    def effective_db_name(self) -> str:
        name = (self.MONGODB_DB_NAME or "").strip()
        return name if name else "cyber_investigation"

    # OCR
    TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    # Storage
    EVIDENCE_VAULT_DIR: str = "./data/evidence_vault"
    MAX_FILE_SIZE_MB: int = 50

    # CORS
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,"
        "https://ai-cyber-investigation-assistant.vercel.app"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
