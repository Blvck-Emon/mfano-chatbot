```markdown
# Mfano Bora Africa Chatbot System

An automated, machine learning-driven web chatbot built for Mfano Bora Africa. The system combines a fast Python FastAPI backend for AI processing with a lightweight PHP admin panel for managing the knowledge base, viewing chat logs, and tracking system analytics.

---

## How the System Works

1. **User Query:** A user submits a question through the website chat widget.
2. **Intent & Information Retrieval:** The FastAPI service evaluates the user query against the machine learning intent model (`/ml_model`) and searches the MySQL `knowledge_base` table using FULLTEXT indexing to find relevant answers.
3. **AI Guardrail Response:** The retrieved context is passed to the Groq LLM API. The AI answers strictly using the provided context. If no matching information exists, it provides standard company contact details.
4. **Logging & Information Gap Analysis:** User interactions, matching categories, and fallbacks are saved to MySQL. Unanswered queries are flagged in the `kb_gap_log` table so administrators can address missing knowledge base information.
5. **Admin Management:** Administrators log into the PHP dashboard (`admin-php`) to update information, view metrics, manage users, and address unanswered questions.

---

## Repository & Git Instructions

### 1. Clone the Repository
Open your terminal or command prompt and run:
```bash
git clone [https://github.com/Blvck-Emon/mfano-chatbot.git](https://github.com/Blvck-Emon/mfano-chatbot.git)
cd mfano-chatbot

```

### 2. Switch to the Backend Branch

```bash
git checkout Backend

```

### 3. Merge the Backend Branch into Main

To combine the verified backend code into the primary `main` branch:

```bash
git checkout main
git pull origin main
git merge Backend
git push origin main

```

---

## Running the System

### Option A: Linux / macOS (.sh)

Make the installer executable and run it:

```bash
chmod +x scripts/install.sh
./scripts/install.sh

```

To run the system components manually after installation:

```bash
# 1. Activate virtual environment & start FastAPI service
source venv/bin/activate
cd fastapi-service
uvicorn app.main:app --reload --port 8000

# 2. Run web scraper to gather live website data
cd ../scraper
python scrape_site.py --base-url [https://www.mfanoboraafrica.com](https://www.mfanoboraafrica.com)

# 3. Load scraped data into MySQL
cd ../csv-loader
python load_csv_to_mysql.py --csv ../database/knowledge_base_scraped.csv --source-type scraped

```

### Option B: Windows (.ps1)

Open PowerShell as Administrator and run:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\scripts\install.ps1

```

To run the system components manually after installation:

```powershell
# 1. Activate virtual environment & start FastAPI service
.\venv\Scripts\Activate.ps1
cd fastapi-service
uvicorn app.main:app --reload --port 8000

# 2. Run web scraper
cd ..\scraper
python scrape_site.py --base-url [https://www.mfanoboraafrica.com](https://www.mfanoboraafrica.com)

# 3. Load scraped data into MySQL
cd ..\csv-loader
python load_csv_to_mysql.py --csv ..\database\knowledge_base_scraped.csv --source-type scraped

```

---

## Team Integration & Execution Guide

To combine everyone's work seamlessly into GitHub and deploy to the Mfano Bora website, each team member must follow these instructions:

### 1. Jane (Training Dataset Lead)

* Save your dataset to `data/raw_dataset.csv` with columns `intent` and `question`.
* Push your changes to your feature branch and submit a Pull Request to `main`.

### 2. Anna (Data Preprocessing Lead)

* Pull `data/raw_dataset.csv`, clean the data, and split it using `random_state=42`.
* Save `X_train.pkl`, `X_test.pkl`, `y_train.pkl`, and `y_test.pkl` into the `/data` directory.

### 3. Vinicent (Machine Learning Developer)

* Train the model using Anna's preprocessed data files.
* Save `model.pkl`, `vectorizer.pkl`, and `label_encoder.pkl` into the `/ml_model` directory.
* Create `/ml_model/predict.py` containing the `predict_intent(user_text: str)` function as defined in `CONTRACTS.md`.

### 4. Lewis (Backend & Database Lead)

* Ensure `fastapi-service/app/routers/chat.py` imports and calls `predict_intent` from `/ml_model/predict.py`.
* Verify MySQL connection settings in `.env` and run `database/schema.sql`.

### 5. Nyota (Frontend Lead)

* Copy `integration/widget-embed-snippet.html` into the Mfano Bora website theme/footer.
* Connect your chat widget UI to `POST http://localhost:8000/api/v1/chat/query` (or the live API domain).

### 6. Hannah (QA & Testing Lead)

* Execute cross-device and mobile browser tests.
* Log test cases, fallback responses, and bug reports based on responses logged in `admin-php/chat_logs.php`.

### 7. Peter (Project Lead)

* Review and merge all feature branches into `main`.
* Perform the final system end-to-end integration test before website deployment.

```

```
