import cv2
import numpy as np
import os
from tensorflow.keras.models import load_model

# Labels must match the model's training labels/order
EMO_LABELS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

# Load model path
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'emotion_model.h5')

# Lazy-load global model
_model = None

# Face detection model
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def _load_model():
    """Load the model only once for better performance."""
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found at: {MODEL_PATH}")
        _model = load_model(MODEL_PATH)
    return _model


def predict_emotion_from_image(img_bgr):
    """
    Input: img_bgr (OpenCV image in BGR format)
    Output: (emotion_label, confidence)
    """
    model = _load_model()

    # Convert to grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Detect faces
    # faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    faces = _face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )


    if len(faces) == 0:
        # Fallback when face is not detected
        return None, 0.0


    # Pick the largest detected face
    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
    face = gray[y:y+h, x:x+w]

    # Preprocess for model (48x48 grayscale)
    face = cv2.resize(face, (48, 48))
    face = face.astype("float32") / 255.0
    face = np.expand_dims(face, axis=0)      # shape: (1, 48, 48)
    face = np.expand_dims(face, axis=-1)     # shape: (1, 48, 48, 1)

    # Predict
    preds = model.predict(face)[0]           # softmax output
    idx = int(np.argmax(preds))

    label = EMO_LABELS[idx]
    confidence = float(preds[idx])

    return label, round(confidence, 3)
