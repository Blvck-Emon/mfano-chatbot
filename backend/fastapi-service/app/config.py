"""
Central configuration for the FastAPI RAG service, loaded from
environment variables (see ../.env.example). Uses plain os.environ
(plus python-dotenv, already in requirements.txt, to read ../.env) to
keep the service lightweight.
"""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]  # project root (contains data/, database/, ...)

try:  # make the documented ".env" file actually take effect
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass


def _resolve_path(raw: str) -> str:
    """Relative paths in DB_PATH are resolved from the project root."""
    path = Path(raw)
    return str(path if path.is_absolute() else ROOT_DIR / path)


class Settings:
    # --- SQLite ---
    DB_PATH: str = _resolve_path(os.environ.get("DB_PATH", "data/mfano_bora_chatbot.db"))
    DB_BUSY_TIMEOUT_SECONDS: float = float(os.environ.get("DB_BUSY_TIMEOUT_SECONDS", 5))

    # --- Groq LLM ---
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"

    # --- Retrieval ---
    TOP_K_RESULTS: int = int(os.environ.get("TOP_K_RESULTS", 3))

    # --- CORS: the mfanoboraafrica.com website + the floating widget ---
    ALLOWED_ORIGINS: list = os.environ.get(
        "ALLOWED_ORIGINS", "https://www.mfanoboraafrica.com,https://mfanoboraafrica.com"
    ).split(",")

    # --- App ---
    APP_ENV: str = os.environ.get("APP_ENV", "production")
    CONTACT_EMAIL: str = os.environ.get("CONTACT_EMAIL", "info@mfanoboraafrica.com")


settings = Settings()
