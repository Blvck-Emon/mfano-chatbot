#!/usr/bin/env bash
# =====================================================================
# Mfano Bora Africa Chatbot — Linux/macOS installer
#
# Installs/verifies: Python 3.10+, pip, venv, PHP 8.x + pdo_sqlite,
# then creates a Python virtualenv, installs FastAPI/scraper/csv-loader
# dependencies, copies .env.example -> .env, creates the SQLite database
# (data/mfano_bora_chatbot.db) and (optionally) loads the training CSV.
# No database server is needed: SQLite is built into Python and PHP.
#
# Usage:
#   chmod +x scripts/install.sh
#   ./scripts/install.sh                 # full setup
#   ./scripts/install.sh --skip-db       # skip database creation / CSV load
#   ./scripts/install.sh --no-sudo       # don't attempt package installs
# =====================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SKIP_DB=false
USE_SUDO=true
for arg in "$@"; do
  case "$arg" in
    --skip-db) SKIP_DB=true ;;
    --no-sudo) USE_SUDO=false ;;
  esac
done

log()  { printf "\n\033[1;34m==> %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m[warn] %s\033[0m\n" "$1"; }

SUDO=""
if $USE_SUDO && command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
fi

detect_pkg_manager() {
  if command -v apt-get >/dev/null 2>&1; then echo "apt"; return; fi
  if command -v dnf >/dev/null 2>&1; then echo "dnf"; return; fi
  if command -v brew >/dev/null 2>&1; then echo "brew"; return; fi
  echo "none"
}

PKG_MGR=$(detect_pkg_manager)
log "Detected package manager: $PKG_MGR"

install_system_deps() {
  case "$PKG_MGR" in
    apt)
      $SUDO apt-get update -y
      $SUDO apt-get install -y python3 python3-pip python3-venv \
        php php-cli php-sqlite3 php-mbstring sqlite3 || true
      ;;
    dnf)
      $SUDO dnf install -y python3 python3-pip php php-cli php-pdo php-mbstring sqlite
      ;;
    brew)
      brew install python@3.11 php sqlite || true
      ;;
    none)
      warn "No supported package manager detected (apt/dnf/brew)."
      warn "Please install manually: Python 3.10+, pip, php 8.x with pdo_sqlite + mbstring."
      ;;
  esac
}

log "Step 1/6: Installing system dependencies (Python, PHP + pdo_sqlite)"
if $USE_SUDO; then
  install_system_deps
else
  warn "Skipping system package install (--no-sudo passed). Verifying tools only."
fi

check_tool() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "  [ok] $1 -> $($1 --version 2>&1 | head -n1)"
  else
    warn "$1 not found on PATH — install it before running the app."
  fi
}

log "Step 2/6: Verifying required tools"
check_tool python3
check_tool php
if command -v php >/dev/null 2>&1; then
  # (no `grep -q` here: it closes the pipe early and `set -o pipefail` would flag SIGPIPE as failure)
  if php -m | grep -i '^pdo_sqlite$' >/dev/null; then
    echo "  [ok] php pdo_sqlite extension"
  else
    warn "PHP has no pdo_sqlite extension - the admin panel cannot open the database (apt: php-sqlite3)."
  fi
fi

log "Step 3/6: Creating Python virtual environment (./venv)"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip -q

log "Step 4/6: Installing Python dependencies"
pip install -r fastapi-service/requirements.txt -q
pip install -r scraper/requirements.txt -q
pip install -r csv-loader/requirements.txt -q
echo "  Installed FastAPI service, scraper, and csv-loader dependencies."

log "Step 5/6: Setting up environment files"
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "  Created .env from .env.example — EDIT THIS with your real Groq key."
else
  echo "  .env already exists, leaving it untouched."
fi
if [ ! -f "fastapi-service/.env" ]; then
  ln -sf ../.env fastapi-service/.env 2>/dev/null || cp .env fastapi-service/.env
fi
if [ ! -f "admin-php/config/.env" ]; then
  cp .env admin-php/config/.env 2>/dev/null || true
fi

log "Step 6/6: SQLite database"
if $SKIP_DB; then
  warn "Skipping database creation / CSV load (--skip-db passed)."
else
  if python3 database/init_db.py; then
    TRAINING_CSV="database/mfano_bora_chatbot_training_dataset.csv"
    if [ -f "$TRAINING_CSV" ]; then
      read -rp "  Load the training dataset CSV now? [y/N]: " LOAD_TRAINING
      if [[ "$LOAD_TRAINING" =~ ^[Yy]$ ]]; then
        (cd csv-loader && python3 load_csv_to_sqlite.py --csv "../$TRAINING_CSV")
      fi
    else
      warn "$TRAINING_CSV not found - copy the CSV there, then run: (cd csv-loader && python3 load_csv_to_sqlite.py --csv ../$TRAINING_CSV)"
    fi
    read -rp "  Load the seed FAQ CSV (database/seed_faq.csv) now? [y/N]: " LOAD_SEED
    if [[ "$LOAD_SEED" =~ ^[Yy]$ ]] && [ -f database/seed_faq.csv ]; then
      (cd csv-loader && python3 load_csv_to_sqlite.py --csv ../database/seed_faq.csv --source-type faq)
    fi
  else
    warn "Database creation failed - run: python3 database/init_db.py"
  fi
fi

log "Done!"
cat <<'EOM'

Next steps:
  1. Edit .env with your real GROQ_API_KEY (DB_PATH defaults to data/mfano_bora_chatbot.db).
  2. Start the FastAPI service:
       source venv/bin/activate
       cd fastapi-service && uvicorn app.main:app --reload --port 8000
  3. Point your PHP webserver's document root at admin-php/ (or drop the
     folder into /var/www/mfanoboraafrica.com/admin/), then browse to
     /login.php  (default user: admin / ChangeMe!123 — CHANGE IMMEDIATELY).
  4. Run the scraper when ready:
       cd scraper && python3 scrape_site.py --base-url https://www.mfanoboraafrica.com
       cd ../csv-loader && python3 load_csv_to_sqlite.py --csv ../database/knowledge_base_scraped.csv --source-type scraped
  5. Give the frontend team integration/api-contract.md so they can wire
     up the floating widget.
  6. PERMISSIONS: the PHP web-server user AND the user running uvicorn must both
     be able to write to data/ (the .db file and its -wal/-shm companions), e.g.
       sudo chgrp -R www-data data && sudo chmod -R g+rwX data
EOM
