# Chatbot Project: Technical Contracts

**Project Lead:** Peter
**Status:** Frozen (Do not change without approval from Peter)

This document defines the exact technical interfaces for the Chatbot project. All team members must adhere to these formats to prevent integration errors.

---

## 1. The Data Contract (Jane ➔ Anna ➔ Vincent)

### Step 1: Jane's Raw Dataset
*   **Format:** CSV file
*   **Filename:** `raw_dataset.csv`
*   **Columns:** 
    *   `intent` (The category, e.g., `apply_attachment`)
    *   `question` (The user's question, e.g., `How do I apply for attachment?`)
*   **Rules:** No empty rows. No duplicate questions.

### Step 2: Anna's Preprocessed Dataset
*   **Format:** Python Pickle files (`.pkl`)
*   **Filenames:** `X_train.pkl`, `X_test.pkl`, `y_train.pkl`, `y_test.pkl`
*   **Location:** `/data` folder in the GitHub repository.
*   **Split Rule:** 70% Train, 15% Validation, 15% Test.
*   **Random Seed:** Anna must use `random_state=42` so the split is reproducible.

---

## 2. The ML Contract (Vincent ➔ Lewis)

### Step 1: Model Artifacts
*   **What Vinicent saves:** 
    *   `model.pkl` (The trained Logistic Regression or SVM model)
    *   `vectorizer.pkl` (The TF-IDF vectorizer)
    *   `label_encoder.pkl` (If intents need to be mapped from strings to numbers)
*   **Location:** `/ml_model` folder in the GitHub repository.

### Step 2: Python Interface
Vinicent must write a Python file called `predict.py` inside `/ml_model`. It must contain this exact function signature:

```python
def predict_intent(user_text: str) -> tuple[str, float]:
    # Returns: (intent_string, confidence_score)
    # Example: ("apply_attachment", 0.95)
