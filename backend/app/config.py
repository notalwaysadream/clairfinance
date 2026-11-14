import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# App directory
APP_DIR = Path(__file__).resolve().parent
# Backend directory
BACKEND_DIR = APP_DIR.parent
# Base project directory
PROJECT_ROOT = BACKEND_DIR.parent

# Load .env file from backend or root
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

DB_FILE_PATH = BACKEND_DIR / "finops.db"
DB_URI_PATH = DB_FILE_PATH.as_posix()

class Settings:
    PROJECT_NAME: str = "ClaireFinance API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Consistent absolute path database URL with forward slashes (cross-platform compatible)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_URI_PATH}")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", f"sqlite:///{DB_URI_PATH}")
    
    # Auth & JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "hackathon-secret-jwt-key-2026-super-secure")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    
    # AI / LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "*",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

settings = Settings()
# If DATABASE_URL was set to a relative path like sqlite+aiosqlite:///./finops.db, normalize it
if "///./" in settings.DATABASE_URL:
    settings.DATABASE_URL = f"sqlite+aiosqlite:///{DB_URI_PATH}"
if "///./" in settings.SYNC_DATABASE_URL:
    settings.SYNC_DATABASE_URL = f"sqlite:///{DB_URI_PATH}"
