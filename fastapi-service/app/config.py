"""
Central configuration for the FastAPI RAG service, loaded from
environment variables (see ../.env.example). Uses plain os.environ
(no extra dependency) to keep the service lightweight.
"""

import os


class Settings:
    # --- MySQL ---
    DB_HOST: str = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.environ.get("DB_PORT", 3306))
    DB_NAME: str = os.environ.get("DB_NAME", "mfano_bora_chatbot")
    DB_USER: str = os.environ.get("DB_USER", "mfano_app")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")

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
