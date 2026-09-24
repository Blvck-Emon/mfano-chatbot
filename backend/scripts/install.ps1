<#
.SYNOPSIS
    Mfano Bora Africa Chatbot - Windows installer (PowerShell).

.DESCRIPTION
    Installs/verifies Python 3.10+ and PHP 8.x via winget (falls back to
    Chocolatey if winget is unavailable), then creates a Python virtual
    environment, installs dependencies, copies .env.example -> .env, creates
    the SQLite database (data\mfano_bora_chatbot.db) and optionally loads the
    training CSV. No database server is needed: SQLite ships with Python/PHP.
    NOTE: PHP needs the pdo_sqlite extension enabled in php.ini
    (extension=pdo_sqlite).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\install.ps1
    powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -SkipDb
#>

param(
    [switch]$SkipDb,
    [switch]$NoPackageInstall
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Install-With-Winget($id) {
    if (Test-Command "winget") {
        Write-Host "  Installing $id via winget..."
        winget install --id $id -e --accept-source-agreements --accept-package-agreements | Out-Null
    } elseif (Test-Command "choco") {
        Write-Host "  Installing $id via choco..."
        choco install $id -y | Out-Null
    } else {
        Write-Warn "Neither winget nor choco found — install $id manually."
    }
}

Write-Step "Step 1/6: Installing system dependencies (Python, PHP)"
if (-not $NoPackageInstall) {
    if (-not (Test-Command "python")) { Install-With-Winget "Python.Python.3.12" }
    if (-not (Test-Command "php"))    { Install-With-Winget "PHP.PHP" }
} else {
    Write-Warn "Skipping package install (-NoPackageInstall passed). Verifying tools only."
}

Write-Step "Step 2/6: Verifying required tools"
foreach ($tool in @("python", "php")) {
    if (Test-Command $tool) {
        $version = & $tool --version 2>&1 | Select-Object -First 1
        Write-Host "  [ok] $tool -> $version"
    } else {
        Write-Warn "$tool not found on PATH. Install it and re-run, or add it to PATH manually."
    }
}

if (Test-Command "php") {
    if ((& php -m) -match "pdo_sqlite") {
        Write-Host "  [ok] php pdo_sqlite extension"
    } else {
        Write-Warn "PHP has no pdo_sqlite extension - enable 'extension=pdo_sqlite' in php.ini or the admin panel cannot open the database."
    }
}

Write-Step "Step 3/6: Creating Python virtual environment (.\venv)"
if (-not (Test-Path "venv")) {
    python -m venv venv
}
$venvPython = ".\venv\Scripts\python.exe"
$venvPip = ".\venv\Scripts\pip.exe"
& $venvPip install --upgrade pip -q

Write-Step "Step 4/6: Installing Python dependencies"
& $venvPip install -r fastapi-service\requirements.txt -q
& $venvPip install -r scraper\requirements.txt -q
& $venvPip install -r csv-loader\requirements.txt -q
Write-Host "  Installed FastAPI service, scraper, and csv-loader dependencies."

Write-Step "Step 5/6: Setting up environment files"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  Created .env from .env.example - EDIT THIS with your real Groq key."
} else {
    Write-Host "  .env already exists, leaving it untouched."
}
if (-not (Test-Path "fastapi-service\.env")) {
    Copy-Item ".env" "fastapi-service\.env"
}
if (-not (Test-Path "admin-php\config\.env")) {
    Copy-Item ".env" "admin-php\config\.env"
}

Write-Step "Step 6/6: SQLite database"
if ($SkipDb) {
    Write-Warn "Skipping database creation / CSV load (-SkipDb passed)."
} else {
    & $venvPython database\init_db.py
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Database creation failed - run: python database\init_db.py"
    } else {
        $trainingCsv = "database\mfano_bora_chatbot_training_dataset.csv"
        if (Test-Path $trainingCsv) {
            $loadTraining = Read-Host "  Load the training dataset CSV now? [y/N]"
            if ($loadTraining -match '^[Yy]') {
                Push-Location csv-loader
                & $venvPython load_csv_to_sqlite.py --csv "..\$trainingCsv"
                Pop-Location
            }
        } else {
            Write-Warn "$trainingCsv not found - copy the CSV there, then run csv-loader\load_csv_to_sqlite.py --csv ..\$trainingCsv"
        }
        if (Test-Path "database\seed_faq.csv") {
            $loadSeed = Read-Host "  Load the seed FAQ CSV (database\seed_faq.csv) now? [y/N]"
            if ($loadSeed -match '^[Yy]') {
                Push-Location csv-loader
                & $venvPython load_csv_to_sqlite.py --csv ..\database\seed_faq.csv --source-type faq
                Pop-Location
            }
        }
    }
}

Write-Step "Done!"
Write-Host @"

Next steps:
  1. Edit .env with your real GROQ_API_KEY (DB_PATH defaults to data/mfano_bora_chatbot.db).
  2. Start the FastAPI service:
       .\venv\Scripts\Activate.ps1
       cd fastapi-service; uvicorn app.main:app --reload --port 8000
  3. Point IIS/XAMPP/your PHP server's document root at admin-php\, then
     browse to /login.php (default user: admin / ChangeMe!123 - CHANGE IMMEDIATELY).
  4. Run the scraper when ready:
       cd scraper; python scrape_site.py --base-url https://www.mfanoboraafrica.com
       cd ..\csv-loader; python load_csv_to_sqlite.py --csv ..\database\knowledge_base_scraped.csv --source-type scraped
  5. Give the frontend team integration\api-contract.md so they can wire
     up the floating widget.
"@
