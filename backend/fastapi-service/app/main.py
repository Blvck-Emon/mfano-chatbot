"""
Mfano Bora Africa Chatbot - FastAPI RAG service.

Run locally:
    uvicorn app.main:app --reload --port 8000

Run in production (see scripts/install.sh for a systemd unit example):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, admin, health

app = FastAPI(
    title="Mfano Bora Africa Chatbot API",
    description="Lightweight RAG backend: MySQL knowledge base + Groq LLM",
    version="1.0.0",
)

# Allow only the Mfano Bora website (and the floating widget's origin) to
# call this API from a browser. Add localhost while developing.
origins = settings.ALLOWED_ORIGINS + (
    ["http://localhost:3000", "http://127.0.0.1:3000"] if settings.APP_ENV != "production" else []
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(admin.router)
