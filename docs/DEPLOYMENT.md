# Deployment Notes

## Architecture in production

```
Browser (mfanoboraafrica.com)
   │  loads widget.js (frontend team's bundle)
   ▼
Floating widget  ──POST /api/v1/chat/query──▶  FastAPI (uvicorn, behind Nginx/Apache reverse proxy, HTTPS)
                                                     │
                                                     ▼
                                                 MySQL 8 (knowledge_base, chat_logs, ...)
                                                     ▲
                                                     │  PDO
                                admin-php/  ◀────────┘  (served from the same site, e.g. /admin, HTTPS + auth)
```

## FastAPI service (systemd example)

```ini
# /etc/systemd/system/mfano-chatbot-api.service
[Unit]
Description=Mfano Bora Chatbot FastAPI service
After=network.target mysql.service

[Service]
User=www-data
WorkingDirectory=/opt/mfano-bora-chatbot-system/fastapi-service
EnvironmentFile=/opt/mfano-bora-chatbot-system/.env
ExecStart=/opt/mfano-bora-chatbot-system/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then reverse-proxy `api.mfanoboraafrica.com` → `127.0.0.1:8000` with Nginx
and a Let's Encrypt certificate. Never expose uvicorn directly to the
internet.

## admin-php

Point a vhost/subdirectory at `admin-php/` with PHP 8.x + `pdo_mysql`
enabled, e.g. `https://www.mfanoboraafrica.com/admin/`. Ensure:
- `admin-php/config/.env` exists and is **not** web-readable (the
  included `.htaccess` denies `.env`/`.sql`/`.log`; on Nginx add an
  equivalent `location ~ \.(env|sql|log)$ { deny all; }` block).
- HTTPS is enforced site-wide so session cookies (`secure` flag) work.
- PHP's `session.cookie_httponly` and `session.use_strict_mode` are on
  at the php.ini level as defense in depth (the app already sets these
  per-session).

## Maintenance cron (Task 18)

```cron
# Re-scrape the site and refresh the knowledge base every Monday at 02:00
0 2 * * 1 cd /opt/mfano-bora-chatbot-system/scraper && /opt/mfano-bora-chatbot-system/venv/bin/python scrape_site.py --base-url https://www.mfanoboraafrica.com --out ../database/knowledge_base_scraped.csv && cd ../csv-loader && /opt/mfano-bora-chatbot-system/venv/bin/python load_csv_to_mysql.py --csv ../database/knowledge_base_scraped.csv --source-type scraped
```
New scraped rows land as `status='active'` by default via the loader —
if you want the "review before publish" workflow from the recommendations,
change the loader's INSERT to default `status='draft'` for `source_type='scraped'`.

## Testing (Task 16)

Minimal smoke test once the API is running:
```bash
curl -s -X POST http://localhost:8000/api/v1/chat/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What are your business hours?"}' | python3 -m json.tool
```
Expect a grounded reply referencing Monday-Friday 7 AM-5 PM / Saturday
8 AM-1 PM, with `is_fallback: false`.

## Security checklist before go-live (Task 15)

- [ ] Change the seed `admin` / `ChangeMe!123` password (or delete that
      account after creating named accounts).
- [ ] Set a strong, unique `DB_PASSWORD` and `GROQ_API_KEY` in `.env`
      (never commit `.env` to version control — it's already excluded
      via `.gitignore`, add one if missing).
- [ ] Restrict MySQL user `mfano_app` to only the privileges it needs
      (SELECT/INSERT/UPDATE/DELETE on `mfano_bora_chatbot.*`, no GRANT).
- [ ] Confirm `ALLOWED_ORIGINS` in `.env` lists only real production
      domains before launch.
- [ ] Confirm chat_sessions only stores hashed IPs, never raw IPs/PII.
