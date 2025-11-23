#!/usr/bin/env python3
"""
recognizer/app.py
- سرویس پردازش ویدئو با InsightFace
- بارگذاری embedding ها از Django endpoint (hex-encoded)
- تطبیق با cosine similarity
- anti-spoof (blink-based) ساده
- throttle هر کاربر (default 30 دقیقه)
- ارسال POST امن به Django
"""

import os
import time
import base64
import logging
import threading
import queue
from typing import List, Tuple, Dict, Optional

import cv2
import numpy as np
import requests
from sklearn.metrics.pairwise import cosine_similarity
from insightface.app import FaceAnalysis

# local module
#from anti_spoof import BlinkDetector

# ---------- CONFIG ----------
DJANGO_API_URL = os.environ.get("DJANGO_API_URL", "http://127.0.0.1:8000/attendance/record/")
DJANGO_EMBEDDINGS_URL = os.environ.get("DJANGO_EMBEDDINGS_URL", "http://127.0.0.1:8000/attendance/known-embeddings/")
RTSP_SOURCE = os.environ.get("RTSP_SOURCE", "0")  # "0" for default webcam, or actual rtsp url
CAMERA_ID = os.environ.get("CAMERA_ID", "camera_1")
LOCATION = os.environ.get("LOCATION", "محوطه")
THRESHOLD = float(os.environ.get("MATCH_THRESHOLD", "0.55"))  # cosine similarity threshold (tuneable)
THROTTLE_SECONDS = int(os.environ.get("THROTTLE_SECONDS", 1800))  # 30 minutes
FRAME_SKIP = int(os.environ.get("FRAME_SKIP", 2))  # process 1 frame every FRAME_SKIP frames
MAX_WORKER_THREADS = int(os.environ.get("MAX_WORKER_THREADS", 4))
TIMEOUT_POST = float(os.environ.get("TIMEOUT_POST", 3.0))
RELOAD_EMBED_INTERVAL = int(os.environ.get("RELOAD_EMBED_INTERVAL", 120))  # seconds
SAVE_CROP_ON_MATCH = os.environ.get("SAVE_CROP_ON_MATCH", "1") == "1"
CROP_SAVE_DIR = os.environ.get("CROP_SAVE_DIR", "/tmp/recognizer_crops")

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("recognizer")

# ---------- Prepare model ----------
logger.info("Loading InsightFace models (buffalo_l). This may download models if not present.")
face_app = FaceAnalysis(name="buffalo_l")  # change model name if you prefer
face_app.prepare(ctx_id=0, det_size=(640, 640))
logger.info("Model ready.")

# ---------- Anti-spoof (Blink) ----------
#blink_detector = BlinkDetector()  # uses landmark-based EAR

# ---------- Embeddings cache ----------
class EmbeddingDB:
    """
    Simple in-memory cache of embeddings loaded from Django endpoint.
    Stores list of tuples: (user_id:int, embedding:np.ndarray)
    """
    def __init__(self, url: str):
        self.url = url
        self._data: List[Tuple[int, np.ndarray]] = []
        self._ts = 0

    def load(self):
        try:
            r = requests.get(self.url, timeout=5)
            r.raise_for_status()
            arr = r.json()
            out = []
            for item in arr:
                uid = int(item["user_id"])
                b = bytes.fromhex(item["encoding_hex"])
                emb = np.frombuffer(b, dtype=np.float32).copy()
                out.append((uid, emb))
            self._data = out
            self._ts = time.time()
            logger.info(f"Loaded {len(out)} embeddings from {self.url}")
        except Exception as e:
            logger.exception("Failed to load embeddings: %s", e)

    def maybe_reload(self):
        if time.time() - self._ts > RELOAD_EMBED_INTERVAL:
            self.load()

    def get_all(self):
        return self._data

emb_db = EmbeddingDB(DJANGO_EMBEDDINGS_URL)
emb_db.load()

# ---------- Utility functions ----------
def best_match(embedding: np.ndarray, db: List[Tuple[int, np.ndarray]]) -> Tuple[Optional[int], float]:
    if not db:
        return None, 0.0
    matrix = np.stack([e for _, e in db])  # shape (N, D)
    sims = cosine_similarity([embedding], matrix)[0]
    idx = int(np.argmax(sims))
    return db[idx][0], float(sims[idx])

def post_attendance(payload: dict):
    try:
        r = requests.post(DJANGO_API_URL, json=payload, timeout=TIMEOUT_POST)
        if r.status_code != 200:
            logger.warning("Post returned status %s body=%s", r.status_code, r.text)
        else:
            logger.info("Posted attendance: user=%s camera=%s score=%.3f", payload.get("user_id"), payload.get("camera_id"), payload.get("confidence"))
    except Exception as e:
        logger.exception("Error posting attendance: %s", e)

# worker queue for POSTing (non-blocking)
post_queue = queue.Queue()

def post_worker():
    while True:
        payload = post_queue.get()
        if payload is None:
            break
        post_attendance(payload)
        post_queue.task_done()

# start worker threads
for _ in range(min(MAX_WORKER_THREADS, 4)):
    t = threading.Thread(target=post_worker, daemon=True)
    t.start()

# ---------- Main stream processing ----------
def ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass

if SAVE_CROP_ON_MATCH:
    ensure_dir(CROP_SAVE_DIR)

def process_camera(source: str):
    logger.info("Opening video source: %s", source)
    # source "0" -> index 0; otherwise string
    try:
        idx = int(source)
        cap = cv2.VideoCapture(idx)
    except Exception:
        cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        logger.error("Cannot open video source %s", source)
        return

    frame_count = 0
    last_seen: Dict[int, float] = {}  # user_id -> last timestamp

    while True:
        emb_db.maybe_reload()
        ret, frame = cap.read()
        if not ret:
            logger.debug("Frame read failed, sleeping briefly")
            time.sleep(0.5)
            continue

        frame_count += 1
        if frame_count % FRAME_SKIP != 0:
            continue

        # run face detection & recognition
        try:
            faces = face_app.get(frame)  # list of Face objects
        except Exception as e:
            logger.exception("Model get() failed: %s", e)
            continue

        for face in faces:
            try:
                embedding = face.embedding.astype(np.float32)
                user_id, score = best_match(embedding, emb_db.get_all())
                # Basic anti-spoof: require blink verification within a short window
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)

                # crop for blink detector (work on grayscale face region)
                face_crop = frame[y1:y2, x1:x2]
                is_live = False
                try:
                    # blink detector expects landmarks relative to full frame; we pass face.landmark if available
                    # fallback: if no blink detection, set is_live True (but not recommended)
                    is_live = blink_detector.verify_blink(face, frame)
                except Exception:
                    is_live = False

                # threshold check
                if user_id is not None and score >= THRESHOLD and is_live:
                    now = time.time()
                    last = last_seen.get(user_id, 0)
                    if now - last >= THROTTLE_SECONDS:
                        # prepare payload
                        payload = {
                            "user_id": int(user_id),
                            "camera_id": CAMERA_ID,
                            "location": LOCATION,
                            "confidence": float(score),
                        }
                        post_queue.put(payload)
                        last_seen[user_id] = now
                        # optionally save crop
                        if SAVE_CROP_ON_MATCH:
                            ts = int(now)
                            fname = f"{CROP_SAVE_DIR}/user_{user_id}_{CAMERA_ID}_{ts}.jpg"
                            cv2.imwrite(fname, face_crop)
                            logger.info("Saved crop to %s", fname)
                else:
                    logger.debug("No match / low score / spoof: uid=%s score=%.3f live=%s", user_id, score, is_live)
            except Exception as e:
                logger.exception("Error handling face: %s", e)

    cap.release()

# ---------- CLI entrypoint ----------
if __name__ == "__main__":
    # ensure crop dir
    if SAVE_CROP_ON_MATCH:
        ensure_dir(CROP_SAVE_DIR)
    src = RTSP_SOURCE
    logger.info("Starting processing for source=%s camera_id=%s", src, CAMERA_ID)
    process_camera(src)
