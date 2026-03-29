"""
Wrapper emotion detector that will use the included `music_app.ai` model when available.
If the AI model is not present, falls back to a lightweight Haar-cascade + neutral fallback.

Exposed API:
- detect_emotion_from_frame(frame) -> (emotion_label_or_None, mood, confidence)

Supported emotion labels (from the training data):
['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
"""

import os
import cv2
import numpy as np

# Try to import user-provided ai predictor
_ai_detector = None
try:
    from .ai import emotion_detector as ai_detector
    _ai_detector = ai_detector
except Exception:
    _ai_detector = None

# Lightweight fallback face cascade
_face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Label list (must match model)
EMO_LABELS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']


def detect_emotion_from_frame(frame):
    """Return (emotion_label_or_None, mood, confidence).

    - If face not detected -> (None, 'null', 0.0)
    - If AI model available -> use it and map label->mood (identity)
    - Else -> try lightweight cascade + return 'neutral' fallback
    """
    try:
        # If ai detector module available, use it (it expects BGR image)
        if _ai_detector is not None:
            try:
                label, conf = _ai_detector.predict_emotion_from_image(frame)
                # _ai_detector returns (label, confidence)
                if label is None:
                    return None, 'null', 0.0
                # Map label to available moods in the Song model
                mood = label if label in ['happy', 'sad', 'fear', 'surprise', 'neutral', 'angry'] else 'neutral'
                if label == 'disgust':
                    mood = 'angry'
                return label, mood, float(conf)
            except FileNotFoundError:
                # model file missing inside ai; fall back
                pass
            except Exception as e:
                print('Error using ai detector:', e)

        # Fallback: detect face with Haar cascade
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        if len(faces) == 0:
            return None, 'null', 0.0

        # Pick largest face
        x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
        roi = gray[y:y+h, x:x+w]
        try:
            roi_resized = cv2.resize(roi, (48, 48))
            roi_norm = roi_resized.astype('float32') / 255.0
            # No model available: fallback to neutral
            return 'neutral', 'neutral', 0.5
        except Exception:
            return 'neutral', 'neutral', 0.5

    except Exception as e:
        print('Emotion detector error:', e)
        return None, 'null', 0.0
