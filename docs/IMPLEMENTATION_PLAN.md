# Implementation Plan — Mfano Bora Africa Chatbot (Refined Stack)

**Stack:** PHP (admin) + FastAPI (ML/RAG API) + MySQL (KB + logs) + a
separately-built frontend floating widget, integrated via a documented
REST contract.

This plan supersedes the earlier Node.js/MongoDB/Groq draft
(`Machine_Learning-Based_Web-Integrated_Chatbot_for_Mfano_Bora_Africa_Implementation_plan.md`)
on tech stack only — the phase structure and task coverage below still
satisfies every task in `0. INFORMATION SCIENCE ATTACHMENT ASSIGNMENT.pdf`.

## Task → Component Mapping

| # | Assignment Task | Where it's implemented |
|---|---|---|
| 1 | Information Requirements Analysis | `integration/api-contract.md` §intro + user personas already documented in `1. Machine Learning Based Chatbot...Information.pdf` (Section 2: user roles) |
| 2 | Information Source Identification | `scraper/scrape_site.py` (crawls the live site), `database/seed_faq.csv` (curated sources) |
| 3 | Information Collection | `scraper/scrape_site.py` output CSV + `csv-loader/load_csv_to_mysql.py` |
| 4 | Information Classification | `database/schema.sql` → `kb_categories` table; `scraper/scrape_site.py` → `CATEGORY_RULES` auto-tagging; `admin-php/kb_edit.php` category dropdown |
| 5 | Knowledge Base Development | `database/schema.sql` → `knowledge_base` table (the SSOT); `admin-php/kb_edit.php` + `kb_save.php` for manual curation |
| 6 | Information Organization | `knowledge_base` schema fields (category_id, status, source_type) + `admin-php/knowledge_base.php` filterable list view |
| 7 | Information Quality Assessment | `admin-php/knowledge_base.php` review workflow (status: draft/active/archived) + recommended manual QA pass before promoting scraped rows to `active` |
| 8 | Information Cleaning | `csv-loader/load_csv_to_mysql.py` — whitespace normalization, short-row filtering, de-duplication against existing rows |
| 9 | Metadata Development | `knowledge_base.keywords`, `source_url`, `source_type`, `last_updated`, `category_id` columns (Dublin-Core-inspired: subject≈category, description≈content_chunk, source≈source_url, date≈last_updated) |
| 10 | Information Retrieval Design | `fastapi-service/app/services/retrieval.py` — MySQL FULLTEXT NATURAL LANGUAGE MODE search, with a documented embedding-rerank upgrade path |
| 11 | FAQ Development | `database/seed_faq.csv` + `source_type = 'faq'` rows in `knowledge_base` |
| 12 | Information Mapping | `fastapi-service/app/routers/chat.py` — maps each query to a `doc_id`/`category` via retrieval, logged as `intent_matched` in `chat_logs` |
| 13 | Information Gap Analysis | `fastapi-service/app/services/logger.py::log_gap()` → `kb_gap_log` table; surfaced on `admin-php/index.php` dashboard |
| 14 | Information Governance | `admin-php/users.php` (RBAC roles: superadmin/editor/viewer) + recommended governance checklist below |
| 15 | Information Security and Privacy | Bcrypt-hashed admin passwords, HttpOnly/SameSite sessions (`admin-php/includes/auth.php`), SHA-256 IP hashing instead of raw IPs (`logger.py::hash_ip`), `.htaccess` config lockdown, RBAC-gated mutations |
| 16 | Information Access and Retrieval Testing | `admin-php/chat_logs.php` fallback filter; manual test script in `docs/DEPLOYMENT.md` §Testing |
| 17 | Chatbot Information Evaluation | `admin-php/index.php` + `fastapi-service/app/routers/admin.py` — fallback rate / resolution rate KPIs |
| 18 | Knowledge Base Maintenance Plan | Recurring scrape+load cron job (see `docs/DEPLOYMENT.md` §Maintenance) + gap-log-driven manual review cadence |
| 19 | Information Management Report | This document + the KPI/gap exports available from `admin-php/index.php` and `chat_logs.php` |
| 20 | Recommendations | See "Recommendations" section at the end of this document |

## Phased Delivery Plan

### Phase I — Foundation (Week 1)
- Stand up MySQL, run `database/schema.sql`.
- Install FastAPI service + PHP admin locally via `scripts/install.sh` / `install.ps1`.
- Load `database/seed_faq.csv` as the initial knowledge base (Tasks 1, 2, 3, 11).

### Phase II — Knowledge Base Build-Out (Week 2)
- Run `scraper/scrape_site.py` against the live site; review output CSV.
- Load into MySQL with `csv-loader/load_csv_to_mysql.py --source-type scraped`.
- Manually review scraped rows in `admin-php/knowledge_base.php`, correcting
  categories and promoting good rows from `draft` to `active` (Tasks 4, 6, 7, 8, 9).

### Phase III — Retrieval & LLM Integration (Week 3)
- Configure `GROQ_API_KEY` in `.env`; verify `/api/v1/chat/query` returns
  grounded answers for the core FAQ set (Task 10, 12).
- Share `integration/api-contract.md` with the frontend designer so the
  floating widget can be built/wired in parallel.

### Phase IV — Security, Governance & Testing (Week 4)
- Create named admin accounts via `users.php`; deactivate the seed `admin`
  account after verifying login works (Task 14, 15).
- Run a structured test pass: 20–30 representative questions per persona
  (student, logistics client, award nominee, Road Safety Club member),
  logging fallbacks into `kb_gap_log` (Task 16, 17).
- Close top gaps by adding entries via `admin-php/kb_edit.php`.

### Phase V — Launch, Maintenance & Reporting (Week 5+)
- Deploy per `docs/DEPLOYMENT.md`; embed the widget using
  `integration/widget-embed-snippet.html`.
- Schedule the scrape → load pipeline (weekly or on content-publish) for
  ongoing maintenance (Task 18).
- Produce the final Information Management Report from dashboard KPIs and
  this plan (Task 19); compile recommendations (Task 20).

## Recommendations (Task 20)

1. **Promote workflow discipline:** keep scraped rows in `draft` status
   until a human reviews them — never auto-publish scraped content as
   `active` without a quality pass.
2. **Upgrade retrieval if the KB grows large:** MySQL FULLTEXT is
   sufficient for a few thousand rows; if the KB grows substantially,
   populate `knowledge_base.embedding_json` and enable
   `retrieval.rerank_with_embeddings()` for semantic re-ranking.
3. **Automate the maintenance cycle:** wire `scraper/scrape_site.py` +
   `csv-loader/load_csv_to_mysql.py` into a weekly cron/scheduled task so
   new blog posts and award announcements flow into the KB automatically.
4. **Close the gap-analysis loop:** review `kb_gap_log` weekly; it is the
   single best signal for what's missing from the knowledge base.
5. **Harden before public launch:** put the FastAPI service behind HTTPS
   (reverse proxy), restrict `/api/v1/admin/*` to internal callers only,
   and rotate the seed admin password immediately.
6. **Plan for scale gradually:** if Mfano Bora expands to another
   country site or product line, the `kb_categories` table and
   `source_type` enum are already structured to support multi-tenant
   knowledge bases without a schema rewrite.
