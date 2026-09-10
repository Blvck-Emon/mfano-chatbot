# Mfano Bora Africa Chatbot — Refined System (PHP + FastAPI + MySQL)

This is the refined implementation of the Machine Learning-Based
Web-Integrated Chatbot for Mfano Bora Africa, rebuilt on a lightweight,
easily-hostable stack so it can sit directly alongside the existing
Mfano Bora Africa PHP website:

| Layer | Technology | Why |
|---|---|---|
| Knowledge base + logs | **MySQL 8** | Widely available on shared/VPS PHP hosting; FULLTEXT search gives relevance-ranked retrieval without a separate vector DB |
| RAG / ML API | **FastAPI (Python)** | Fast, small, async-ready; the only piece that talks to the Groq LLM |
| Admin dashboard | **PHP (no framework, no Composer required)** | Drops straight into the same server/hosting as the main website (`/admin`) |
| Frontend chat widget | **Built separately by the frontend design lead** | This repo only ships the API contract + an embed snippet (`integration/`) — no widget code lives here |
| Knowledge base seeding | **Python scraper → CSV → MySQL loader** | Crawls the whole live site once (or on a schedule) and refreshes the KB |

This intentionally departs from the earlier Node.js/MongoDB/Postgres+pgvector
draft (see `docs/Machine_Learning-Based_Web-Integrated_Chatbot_for_Mfano_Bora_Africa_Implementation_plan.md`
for that original plan) in favor of a lighter footprint that a small
attachment team can install, run, and hand over without managing a
container orchestrator.

## Folder structure

```
mfano-bora-chatbot-system/
├── database/
│   ├── schema.sql                 # MySQL DDL (run first)
│   └── seed_faq.csv               # Hand-verified FAQ seed data
├── scraper/
│   ├── scrape_site.py             # Crawls mfanoboraafrica.com -> CSV
│   └── requirements.txt
├── csv-loader/
│   ├── load_csv_to_mysql.py       # Loads any KB CSV into MySQL (dedup + clean)
│   └── requirements.txt
├── fastapi-service/               # ML/RAG backend (Python)
│   ├── app/
│   │   ├── main.py                # FastAPI app + CORS
│   │   ├── config.py               # env-driven settings
│   │   ├── db.py                   # MySQL connection pool
│   │   ├── models.py               # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── chat.py            # POST /api/v1/chat/query
│   │   │   ├── admin.py           # GET  /api/v1/admin/dashboard-stats
│   │   │   └── health.py          # GET  /health
│   │   └── services/
│   │       ├── retrieval.py       # MySQL FULLTEXT search (Task 10)
│   │       ├── llm.py             # Groq API call + guardrail prompt
│   │       └── logger.py          # chat logging + gap tracking
│   └── requirements.txt
├── admin-php/                     # Admin dashboard (drop into the website)
│   ├── config/                    # env.php, db.php (PDO), .env (you create)
│   ├── includes/                  # auth.php (RBAC), functions.php
│   ├── api/stats.php              # session-authed JSON stats
│   ├── assets/css/style.css
│   ├── login.php / logout.php
│   ├── index.php                  # KPI dashboard + gap analysis
│   ├── knowledge_base.php         # KB list/search
│   ├── kb_edit.php / kb_save.php  # KB create/update/delete
│   ├── chat_logs.php              # Task 16/17 access & evaluation view
│   └── users.php                  # superadmin-only user management
├── integration/
│   ├── api-contract.md            # What the frontend widget team needs
│   └── widget-embed-snippet.html  # Drop-in <script> for the website
├── docs/
│   ├── IMPLEMENTATION_PLAN.md     # 20-task -> component mapping + phased plan
│   └── DEPLOYMENT.md              # Production hosting notes
├── scripts/
│   ├── install.sh                 # Linux/macOS setup
│   └── install.ps1                # Windows PowerShell setup
└── .env.example
```

## Quick start

**Linux/macOS:**
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

Both scripts verify/install Python, PHP, and MySQL client tools, create
a Python virtualenv, install all Python dependencies, copy `.env.example`
to `.env`, and optionally apply `database/schema.sql` + load the seed FAQ.

After install:

1. **Edit `.env`** with real `DB_PASSWORD` and `GROQ_API_KEY`.
2. **Start the FastAPI service:**
   ```bash
   source venv/bin/activate          # venv\Scripts\Activate.ps1 on Windows
   cd fastapi-service
   uvicorn app.main:app --reload --port 8000
   ```
3. **Serve `admin-php/`** with any PHP 8.x + `pdo_mysql` webserver (Apache,
   Nginx+PHP-FPM, or just `php -S 0.0.0.0:8080 -t admin-php` for local
   testing). Log in at `/login.php` with `admin` / `ChangeMe!123` and
   change the password immediately (add a real user via `users.php` and
   deactivate/replace the seed account).
4. **Scrape the live site into the knowledge base:**
   ```bash
   cd scraper
   python scrape_site.py --base-url https://www.mfanoboraafrica.com --max-pages 200
   cd ../csv-loader
   python load_csv_to_mysql.py --csv ../database/knowledge_base_scraped.csv --source-type scraped
   ```
5. **Hand `integration/api-contract.md`** to the frontend designer building
   the floating widget — it's the entire interface they need.

See `docs/IMPLEMENTATION_PLAN.md` for how each of the assignment's 20 tasks
maps onto this codebase, and `docs/DEPLOYMENT.md` for production notes
(reverse proxy, systemd unit, cron refresh, security checklist).
