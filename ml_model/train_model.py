# ml_model/train_model.py
import os
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from preprocess import clean_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def train(csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(BASE_DIR, "..", "data", "dummy_data.csv")

    print(f"[1/5] Loading data from {csv_path}")
    df = pd.read_csv(csv_path)

    # Contract Section 1: Jane's file has columns 'question' and 'intent'
    if 'question' not in df.columns or 'intent' not in df.columns:
        raise ValueError("CSV must have 'question' and 'intent' columns")

    df['clean_text'] = df['question'].apply(clean_text)
    df = df.drop_duplicates(subset=['clean_text']).reset_index(drop=True)
    df = df[df['clean_text'].str.len() > 0].reset_index(drop=True)
    print(f"     Cleaned dataset shape: {df.shape}")

    print("[2/5] Encoding intent labels")
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df['intent'])
    print(f"     Classes: {list(label_encoder.classes_)}")

    print("[3/5] Fitting TF-IDF vectorizer")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    X = vectorizer.fit_transform(df['clean_text'])

    print("[4/5] Training Logistic Regression")
    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(X, y)
    print(f"     Training accuracy: {model.score(X, y):.4f}")

    print("[5/5] Saving artifacts")
    joblib.dump(model,         os.path.join(BASE_DIR, "model.pkl"))
    joblib.dump(vectorizer,    os.path.join(BASE_DIR, "vectorizer.pkl"))
    joblib.dump(label_encoder, os.path.join(BASE_DIR, "label_encoder.pkl"))
    print("     [OK] Saved: model.pkl, vectorizer.pkl, label_encoder.pkl")


if __name__ == "__main__":
    train()