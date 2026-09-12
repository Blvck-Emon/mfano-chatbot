"""
llm.py
======
Wraps the Groq Chat Completions API (OpenAI-compatible schema) and
enforces the RAG guardrail: the model must answer ONLY from the
supplied knowledge-base context, and fall back to contact details
when the context doesn't cover the question.
"""

from typing import List, Dict

import requests

from app.config import settings

SYSTEM_PROMPT_TEMPLATE = """You are the Mfano Bora Africa AI Assistant.
Respond using ONLY the context provided below. Be concise and friendly.
If the answer cannot be found in the context, reply EXACTLY with:
"I cannot seem to find that exact piece of information. Feel free to contact our team via email {contact_email} or visit Mfano House from Monday to Friday 7 AM-5 PM."

Context:
{context}
"""


def build_context(kb_rows: List[Dict]) -> str:
    if not kb_rows:
        return "(no matching knowledge base entries)"
    parts = []
    for row in kb_rows:
        label = row.get("question") or row.get("category") or "Info"
        parts.append(f"- {label}: {row['content_chunk']}")
    return "\n".join(parts)


def generate_reply(user_message: str, kb_rows: List[Dict]) -> str:
    context = build_context(kb_rows)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        contact_email=settings.CONTACT_EMAIL, context=context
    )

    if not settings.GROQ_API_KEY:
        # Graceful local/dev fallback: no LLM call, just surface the top KB hit.
        if kb_rows:
            return kb_rows[0]["content_chunk"]
        return (
            "I cannot seem to find that exact piece of information. "
            f"Feel free to contact our team via email {settings.CONTACT_EMAIL} "
            "or visit Mfano House from Monday to Friday 7 AM-5 PM."
        )

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }

    try:
        resp = requests.post(settings.GROQ_API_URL, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError):
        # LLM unavailable -> degrade to raw KB answer rather than erroring out.
        if kb_rows:
            return kb_rows[0]["content_chunk"]
        return (
            "I cannot seem to find that exact piece of information. "
            f"Feel free to contact our team via email {settings.CONTACT_EMAIL} "
            "or visit Mfano House from Monday to Friday 7 AM-5 PM."
        )


def is_fallback_reply(reply: str) -> bool:
    return "cannot seem to find" in reply.lower()
