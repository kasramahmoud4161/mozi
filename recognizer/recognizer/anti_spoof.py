"""
anti_spoof.py
- پیاده‌سازی ساده بر پایه EAR (Eye Aspect Ratio) برای تشخیص blink
- تابع verify_blink(face, frame) که true/false باز می‌گرداند.
- این نسخه ساده است و برای افزایش اطمینان بهتر است CNN-based PAD هم اضافه شود.
"""

import numpy as np
import time
import collections
import logging

logger = logging.getLogger("blink")

# پارامترها
EAR_THRESHOLD = 0.20   # زیر این مقدار چشم بسته فرض می‌شود
CONSEC_FRAMES = 2     # چند فریم بسته بودن برای ثبت blink
BLINK_WINDOW = 2.5    # ثانیه برای جستجوی blink قبل/بعد از Detection

# برای نگهداری تاریخچه‌ی EAR
class BlinkDetector:
    def __init__(self):
        # هر شخص در pipeline می‌تواند شناسه موقت داشته باشد اما چون ما id نداریم، از یک صف ساده استفاده می‌کنیم
        self.history = collections.deque(maxlen=30)  # نگه داشتن تا 30 EAR اخیر

    @staticmethod
    def eye_aspect_ratio(eye):
        # eye: numpy array shape (6,2) of landmarks
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        ear = (A + B) / (2.0 * C) if C != 0 else 0.0
        return ear

    def verify_blink(self, face, frame) -> bool:
        """
        face: insightface face object with .landmark (numpy array)
        frame: full frame (BGR)
        returns True if a blink detected recently (simple heuristic)
        """
        try:
            lm = face.landmark  # shape (106,2) or (68,2) depending on model
            # choose approximate eye landmark indices for buffalo_l (use 33-42 / 43-52 depending)
            # We'll try both common subsets:
            # fallback indices (68-point)
            left_eye_idx = [36,37,38,39,40,41]
            right_eye_idx = [42,43,44,45,46,47]

            if lm.shape[0] >= 68:
                left = np.array([lm[i] for i in left_eye_idx])
                right = np.array([lm[i] for i in right_eye_idx])
            else:
                # for 106 landmarks, approximate eye indices
                left = lm[33:39]
                right = lm[39:45]

            left_ear = self.eye_aspect_ratio(left)
            right_ear = self.eye_aspect_ratio(right)
            ear = (left_ear + right_ear) / 2.0
            self.history.append((time.time(), float(ear)))
            # analyze history for blink: find a drop below EAR_THRESHOLD then rise
            times, ears = zip(*self.history)
            # simple: if any ear < threshold in history window, say it's a blink
            if any(e < EAR_THRESHOLD for e in ears):
                logger.debug("Blink detected via EAR history (min EAR=%.3f)", min(ears))
                return True
            return False
        except Exception as e:
            logger.exception("Blink verification failed: %s", e)
            return False
