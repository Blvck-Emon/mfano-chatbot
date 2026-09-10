# ml_model/preprocess.py
import pandas as pd
import re
import string

def clean_text(text):
    """Lowercase, remove punctuation, and strip extra spaces."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'\d+', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = text.strip()
    return text

def load_and_clean_data(filepath):
    print(f"Loading data from {filepath}...")
    df = pd.read_csv(filepath)
    if 'text' not in df.columns or 'intent' not in df.columns:
        raise ValueError("Dataset must have 'text' and 'intent' columns")
    df['clean_text'] = df['text'].apply(clean_text)
    df = df.drop_duplicates(subset=['clean_text'])
    print(f"Data cleaned. Final shape: {df.shape}")
    return df

if __name__ == "__main__":
    print("Preprocessing script ready.")