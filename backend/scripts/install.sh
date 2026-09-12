#!/usr/bin/env bash
# =====================================================================
# Mfano Bora Africa Chatbot — Linux/macOS installer
#
# Installs/verifies: Python 3.10+, pip, venv, MySQL client, PHP 8.x + PDO,
# then creates a Python virtualenv, installs FastAPI/scraper/csv-loader
# dependencies, copies .env.example -> .env, and (optionally) loads the
# MySQL schema + seed FAQ.
#
# Usage:
#   chmod +x scripts/install.sh
#   ./scripts/install.sh                 # full setup
#   ./scripts/install.sh --skip-db       # skip schema/seed load
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
        php php-cli php-mysql php-mbstring \
        mysql-client default-mysql-client 2>/dev/null || \
      $SUDO apt-get install -y mysql-client || true
      ;;
    dnf)
      $SUDO dnf install -y python3 python3-pip php php-cli php-pdo php-mysqlnd mysql
      ;;
    brew)
      brew install python@3.11 php mysql-client || true
      ;;
    none)
      warn "No supported package manager detected (apt/dnf/brew)."
      warn "Please install manually: Python 3.10+, pip, php 8.x with pdo_mysql, mysql-client."
      ;;
  esac
}

log "Step 1/6: Installing system dependencies (Python, PHP, MySQL client)"
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
check_tool mysql

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
  echo "  Created .env from .env.example — EDIT THIS with real DB/Groq credentials."
else
  echo "  .env already exists, leaving it untouched."
fi
if [ ! -f "fastapi-service/.env" ]; then
  ln -sf ../.env fastapi-service/.env 2>/dev/null || cp .env fastapi-service/.env
fi
if [ ! -f "admin-php/config/.env" ]; then
  cp .env admin-php/config/.env 2>/dev/null || true
fi

log "Step 6/6: MySQL schema"
if $SKIP_DB; then
  warn "Skipping schema/seed load (--skip-db passed)."
else
  if command -v mysql >/dev/null 2>&1; then
    echo "  You will be prompted for the MySQL root/admin password."
    read -rp "  MySQL host [127.0.0.1]: " MYSQL_HOST; MYSQL_HOST=${MYSQL_HOST:-127.0.0.1}
    read -rp "  MySQL admin user [root]: " MYSQL_USER; MYSQL_USER=${MYSQL_USER:-root}
    mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p < database/schema.sql && \
      echo "  Schema applied." || warn "Schema load failed — run database/schema.sql manually."

    read -rp "  Load the seed FAQ CSV now? [y/N]: " LOAD_SEED
    if [[ "$LOAD_SEED" =~ ^[Yy]$ ]]; then
      (cd csv-loader && python3 load_csv_to_mysql.py --csv ../database/seed_faq.csv --source-type faq)
    fi
  else
    warn "mysql CLI not found — apply database/schema.sql manually once MySQL is installed."
  fi
fi

log "Done!"
cat <<'EOM'

Next steps:
  1. Edit .env with your real DB_PASSWORD and GROQ_API_KEY.
  2. Start the FastAPI service:
       source venv/bin/activate
       cd fastapi-service && uvicorn app.main:app --reload --port 8000
  3. Point your PHP webserver's document root at admin-php/ (or drop the
     folder into /var/www/mfanoboraafrica.com/admin/), then browse to
     /login.php  (default user: admin / ChangeMe!123 — CHANGE IMMEDIATELY).
  4. Run the scraper when ready:
       cd scraper && python3 scrape_site.py --base-url https://www.mfanoboraafrica.com
       cd ../csv-loader && python3 load_csv_to_mysql.py --csv ../database/knowledge_base_scraped.csv --source-type scraped
  5. Give the frontend team integration/api-contract.md so they can wire
     up the floating widget.
EOM
