-- =====================================================================
-- Mfano Bora Africa Chatbot - SQLite Schema
-- Migrated from MySQL 8.x to SQLite 3 (needs SQLite >= 3.24 with FTS5).
--
--   * MySQL FULLTEXT / MATCH..AGAINST  ->  FTS5 virtual tables kept in
--     sync by triggers (BM25 ranking, Porter stemming).
--   * ENUM columns                      ->  TEXT + CHECK constraints.
--   * AUTO_INCREMENT                    ->  INTEGER PRIMARY KEY AUTOINCREMENT.
--   * ON UPDATE CURRENT_TIMESTAMP       ->  AFTER UPDATE trigger.
--   * All timestamps are stored in UTC (CURRENT_TIMESTAMP).
--
-- Training-dataset mapping (mfano_bora_chatbot_training_dataset*.csv):
--   intent   -> kb_categories.name          (21 intents)
--   response -> knowledge_base.content_chunk (one row per UNIQUE response)
--   question -> kb_questions.question_text   (many questions -> one response)
--
-- Apply with:   python database/init_db.py
-- =====================================================================

PRAGMA journal_mode = WAL;      -- lets FastAPI and the PHP admin share the file
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. Admin users (RBAC) - consumed by admin-php
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'viewer'
                    CHECK (role IN ('superadmin','editor','viewer')),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at   TEXT NULL
);

-- ---------------------------------------------------------------------
-- 2. Knowledge base categories (Task 4: Information Classification)
--    One row per distinct `intent` value in the training CSV.
--    `name` is case-insensitive-unique ('Greetings' == 'greetings').
--    `is_fallback` marks the catch-all intent: when it is the top match
--    the chat router answers with its stored reply and logs a KB gap.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kb_categories (
    category_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    description     TEXT NULL,
    is_fallback     INTEGER NOT NULL DEFAULT 0 CHECK (is_fallback IN (0,1))
);

INSERT OR IGNORE INTO kb_categories (name, description, is_fallback) VALUES
 ('Greetings',            'Opening greetings and "is anyone there?" style messages', 0),
 ('about_company',        'General information about MFANO BORA AFRICA LIMITED and the website', 0),
 ('services',             'What the website provides and the areas it covers', 0),
 ('contact',              'How to reach the company (Contact section)', 0),
 ('location',             'Office location and physical address', 0),
 ('careers',              'General career information and job guidance', 0),
 ('internship',           'Internship and industrial attachment application guidance', 0),
 ('ict_resources',        'ICT, computer, technology and digital-skills resources', 0),
 ('transport_resources',  'Transport, logistics, fleet and supply-chain resources', 0),
 ('attachment_resources', 'Industrial attachment and student training resources', 0),
 ('career_resources',     'CV guides, interview preparation and job-search materials', 0),
 ('road_safety',          'Road Safety Guides under the Transport category', 0),
 ('award_brochures',      'Award brochures and how to find them', 0),
 ('download_resource',    'How to download a resource file', 0),
 ('search_resource',      'How to search for resources and use category filters', 0),
 ('resource_categories',  'Overview of the main resource categories', 0),
 ('faq',                  'Pointer to the FAQ section of the website', 0),
 ('help',                 'What the assistant can help with', 0),
 ('thanks',               'Replies to expressions of thanks', 0),
 ('goodbye',              'Replies to farewells', 0),
 ('fallback',             'Unclear or out-of-scope questions (logged as KB gaps)', 1);

-- ---------------------------------------------------------------------
-- 3. Knowledge base = the ANSWERS (Task 5/6/9: KB development,
--    organization, metadata). Single Source of Truth the FastAPI service
--    searches, populated by the CSV loader / scraper / admin panel.
--    `content_chunk` holds the CSV `response` (or a scraped text chunk).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_base (
    doc_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id     INTEGER NULL REFERENCES kb_categories(category_id) ON DELETE SET NULL,
    content_chunk   TEXT NOT NULL,          -- the answer / scraped text chunk
    keywords        TEXT NULL,              -- comma separated metadata keywords (Dublin Core style)
    source_url      TEXT NULL,              -- origin page on mfanoboraafrica.com
    source_type     TEXT NOT NULL DEFAULT 'manual'
                    CHECK (source_type IN ('scraped','manual','faq')),
    embedding_json  TEXT NULL,              -- optional pre-computed embedding vector (JSON array)
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','draft','archived')),
    last_updated    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_kb_category ON knowledge_base(category_id);
CREATE INDEX IF NOT EXISTS ix_kb_status   ON knowledge_base(status);

-- Replacement for MySQL's "ON UPDATE CURRENT_TIMESTAMP".
CREATE TRIGGER IF NOT EXISTS trg_kb_touch
AFTER UPDATE ON knowledge_base
WHEN NEW.last_updated = OLD.last_updated
BEGIN
    UPDATE knowledge_base SET last_updated = CURRENT_TIMESTAMP WHERE doc_id = NEW.doc_id;
END;

-- ---------------------------------------------------------------------
-- 3b. Training questions (CSV `question` column).
--     Many questions can point at ONE knowledge_base answer, so the 25
--     phrasings of "Where are you located?" share a single stored reply.
--     Question text is case-insensitive-unique: one question, one answer.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kb_questions (
    question_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id          INTEGER NOT NULL REFERENCES knowledge_base(doc_id) ON DELETE CASCADE,
    question_text   TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_kbq_doc ON kb_questions(doc_id);

-- ---------------------------------------------------------------------
-- 3c. Full-text search (replaces MySQL FULLTEXT ft_kb_search).
--     External-content FTS5 tables + triggers keep the indexes in sync.
-- ---------------------------------------------------------------------
CREATE VIRTUAL TABLE IF NOT EXISTS kb_questions_fts USING fts5(
    question_text,
    content='kb_questions', content_rowid='question_id',
    tokenize='porter unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS trg_kbq_ai AFTER INSERT ON kb_questions BEGIN
    INSERT INTO kb_questions_fts(rowid, question_text)
    VALUES (new.question_id, new.question_text);
END;
CREATE TRIGGER IF NOT EXISTS trg_kbq_ad AFTER DELETE ON kb_questions BEGIN
    INSERT INTO kb_questions_fts(kb_questions_fts, rowid, question_text)
    VALUES ('delete', old.question_id, old.question_text);
END;
CREATE TRIGGER IF NOT EXISTS trg_kbq_au AFTER UPDATE OF question_text ON kb_questions BEGIN
    INSERT INTO kb_questions_fts(kb_questions_fts, rowid, question_text)
    VALUES ('delete', old.question_id, old.question_text);
    INSERT INTO kb_questions_fts(rowid, question_text)
    VALUES (new.question_id, new.question_text);
END;

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_base_fts USING fts5(
    content_chunk, keywords,
    content='knowledge_base', content_rowid='doc_id',
    tokenize='porter unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS trg_kb_ai AFTER INSERT ON knowledge_base BEGIN
    INSERT INTO knowledge_base_fts(rowid, content_chunk, keywords)
    VALUES (new.doc_id, new.content_chunk, new.keywords);
END;
CREATE TRIGGER IF NOT EXISTS trg_kb_ad AFTER DELETE ON knowledge_base BEGIN
    INSERT INTO knowledge_base_fts(knowledge_base_fts, rowid, content_chunk, keywords)
    VALUES ('delete', old.doc_id, old.content_chunk, old.keywords);
END;
CREATE TRIGGER IF NOT EXISTS trg_kb_au AFTER UPDATE OF content_chunk, keywords ON knowledge_base BEGIN
    INSERT INTO knowledge_base_fts(knowledge_base_fts, rowid, content_chunk, keywords)
    VALUES ('delete', old.doc_id, old.content_chunk, old.keywords);
    INSERT INTO knowledge_base_fts(rowid, content_chunk, keywords)
    VALUES (new.doc_id, new.content_chunk, new.keywords);
END;

-- ---------------------------------------------------------------------
-- 4. Chat sessions & logs (Task 10/16/17: retrieval design + testing)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id      TEXT PRIMARY KEY,               -- UUID generated by FastAPI
    ip_hash         TEXT NULL,                      -- hashed IP for privacy (Task 15)
    start_time      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time        TEXT NULL,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed'))
);

CREATE TABLE IF NOT EXISTS chat_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    sender_type     TEXT NOT NULL CHECK (sender_type IN ('user','bot')),
    message_text    TEXT NOT NULL,
    intent_matched  TEXT NULL,                      -- kb_categories.name of the top hit
    doc_id_matched  INTEGER NULL REFERENCES knowledge_base(doc_id) ON DELETE SET NULL,
    was_fallback    INTEGER NOT NULL DEFAULT 0 CHECK (was_fallback IN (0,1)),
    timestamp       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_chat_logs_session ON chat_logs(session_id);
CREATE INDEX IF NOT EXISTS ix_chat_logs_time    ON chat_logs(timestamp);

-- ---------------------------------------------------------------------
-- 5. Pre-aggregated admin KPIs (Task 17/19: evaluation + reporting)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_metrics (
    metric_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date_recorded       TEXT NOT NULL UNIQUE,       -- YYYY-MM-DD
    total_conversations INTEGER NOT NULL DEFAULT 0,
    total_messages      INTEGER NOT NULL DEFAULT 0,
    fallback_rate       REAL NOT NULL DEFAULT 0.00,
    resolution_rate     REAL NOT NULL DEFAULT 0.00
);

-- ---------------------------------------------------------------------
-- 6. Information gap / governance log (Task 13/14: gap analysis, governance)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kb_gap_log (
    gap_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    unanswered_query TEXT NOT NULL,
    frequency        INTEGER NOT NULL DEFAULT 1,
    status           TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','sourcing','resolved')),
    flagged_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_by      INTEGER NULL REFERENCES admin_users(user_id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------------
-- Seed a default superadmin (username: admin / password: ChangeMe!123)
-- CHANGE THIS IMMEDIATELY AFTER FIRST LOGIN.
-- ---------------------------------------------------------------------
INSERT OR IGNORE INTO admin_users (username, email, password_hash, role)
VALUES ('admin', 'admin@mfanoboraafrica.com',
        '$2b$10$jPQNa93EQc/1MBcaYlcbcOWWywANJQ3dqX0McN0.X1lNhKeDfmoYK',
        'superadmin');
