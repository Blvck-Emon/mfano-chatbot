# Chatbot API Contract — for the Frontend Floating Widget

This is the only interface the frontend team's floating chat widget needs
to integrate against. The widget itself is **not** built in this repo —
it is being developed separately by the lead frontend designer. This
document is what they need to wire it up.

Base URL (set per environment):
```
https://api.mfanoboraafrica.com        # production FastAPI service
http://localhost:8000                  # local development
```

## 1. Send a message

```
POST /api/v1/chat/query
Content-Type: application/json
```

Request body:
```json
{
  "session_id": null,
  "message": "How do I apply for an attachment?"
}
```
- `session_id`: omit (or send `null`) on the very first message of a
  conversation. On every subsequent message, send back the `session_id`
  the API returned previously so the conversation stays linked.
- `message`: the raw text the visitor typed. Max 1000 characters.

Response body (`200 OK`):
```json
{
  "session_id": "3f1b2c9a-4d3e-4a8f-9c2e-1a2b3c4d5e6f",
  "reply": "You can apply for an industrial attachment (ICT, logistics, or administrative) through our careers/attachment portal.",
  "is_fallback": false,
  "sources": [
    { "doc_id": 7, "category": "Careers & Attachments", "source_url": "https://www.mfanoboraafrica.com/attachment#career-form" }
  ]
}
```
- `is_fallback: true` means the bot could not find a confident answer in
  the knowledge base — the widget can style this reply differently
  (e.g. show a "Contact us" button) if desired.
- `sources` can be used to render a "Learn more" link under the bot's
  reply, linking to `source_url`.

## 2. Minimal fetch() example

```js
async function sendToChatbot(message, sessionId) {
  const res = await fetch("https://api.mfanoboraafrica.com/api/v1/chat/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error(`Chatbot API error: ${res.status}`);
  return res.json(); // { session_id, reply, is_fallback, sources }
}
```

## 3. Health check (for widget "connecting..." state)

```
GET /health  -> { "status": "ok" }
```

## 4. CORS

The API only allows browser requests from the origins listed in the
backend's `ALLOWED_ORIGINS` env var (production: `www.mfanoboraafrica.com`
and `mfanoboraafrica.com`). If the widget is embedded on any other
domain (staging, a marketing microsite, etc.), ask the backend team to
add it to that list — do not try to bypass CORS client-side.

## 5. Embedding snippet

See `widget-embed-snippet.html` in this same folder for a drop-in
`<script>` example the frontend team can adapt — it just needs their
widget bundle to read `window.MFANO_BORA_CHAT_CONFIG` for the API base
URL.
