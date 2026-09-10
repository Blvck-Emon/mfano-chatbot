# ml_model/predict.py
import os
import joblib
from preprocess import clean_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH      = os.path.join(BASE_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "vectorizer.pkl")
ENCODER_PATH    = os.path.join(BASE_DIR, "label_encoder.pkl")

_model = _vectorizer = _encoder = None


def load_artifacts():
    global _model, _vectorizer, _encoder
    if _model is None:
        for p in (MODEL_PATH, VECTORIZER_PATH, ENCODER_PATH):
            if not os.path.exists(p):
                raise FileNotFoundError(
                    f"Missing {p}. Run `python train_model.py` first."
                )
        _model      = joblib.load(MODEL_PATH)
        _vectorizer = joblib.load(VECTORIZER_PATH)
        _encoder    = joblib.load(ENCODER_PATH)
    return _model, _vectorizer, _encoder


def predict_intent(user_text: str, confidence_threshold: float = 0.60) -> tuple[str, float]:
    """Contract interface: returns (intent_string, confidence_score)."""
    model, vectorizer, encoder = load_artifacts()
    cleaned = clean_text(user_text)
    if not cleaned:
        return "fallback", 0.0

    X = vectorizer.transform([cleaned])
    probs = model.predict_proba(X)[0]
    idx = probs.argmax()
    confidence = float(probs[idx])
    intent = encoder.inverse_transform([idx])[0]

    if confidence < confidence_threshold:
        return "fallback", confidence
    return intent, confidence


if __name__ == "__main__":
    tests = ["hi", "How can I apply?", "Where are you located?", "asdfghjkl nonsense"]
    for q in tests:
        print(f"Q: {q!r:40} -> {predict_intent(q)}")