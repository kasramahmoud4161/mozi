import cv2
import mediapipe as mp
import numpy as np
import argparse
import time
import os
import sys

# ==========================================
# تنظیمات سیستم (System Config)
# ==========================================
FILE_FACE_VEC = "owner_face_vec.npy"
FILE_HAND_VEC = "owner_hand_vec.npy"

# حساسیت تشخیص (هرچه کمتر، سخت‌گیرتر)
FACE_MATCH_THRESHOLD = 0.55  
HAND_MATCH_THRESHOLD = 0.35

# آستانه باز بودن چشم (EAR) - اگر کمتر از این باشد یعنی چشم بسته است
EYE_OPEN_THRESHOLD = 0.22  

# تعداد فریم لازم برای ثبت دقیق
SAMPLES_NEEDED = 40

# ایندکس‌های نقاط چشم و عنبیه در MediaPipe FaceMesh
# چشم چپ و راست (برای محاسبه باز/بسته بودن)
LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]
# عنبیه (برای ترسیم دایره دور چشم)
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]

# راه‌اندازی MediaPipe
mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# ==========================================
# توابع کمکی ریاضی و پردازش (Core Logic)
# ==========================================

def euclidean_distance(point1, point2):
    """محاسبه فاصله بین دو نقطه"""
    x1, y1 = point1.ravel()
    x2, y2 = point2.ravel()
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def calculate_ear(landmarks, indices, w, h):
    """
    محاسبه نسبت ابعاد چشم (Eye Aspect Ratio)
    فرمول علمی برای تشخیص باز یا بسته بودن چشم
    """
    # تبدیل مختصات نرمال شده به پیکسل
    coords = []
    for idx in indices:
        coords.append(np.array([landmarks[idx].x * w, landmarks[idx].y * h]))

    # محاسبه فواصل عمودی پلک
    A = euclidean_distance(coords[1], coords[5])
    B = euclidean_distance(coords[2], coords[4])
    # محاسبه فاصله افقی چشم
    C = euclidean_distance(coords[0], coords[3])

    # محاسبه EAR
    ear = (A + B) / (2.0 * C)
    return ear

def get_iris_center(landmarks, indices, w, h):
    """پیدا کردن مرکز و شعاع عنبیه برای رسم گرافیکی"""
    coords = []
    for idx in indices:
        coords.append((int(landmarks[idx].x * w), int(landmarks[idx].y * h)))
    coords = np.array(coords)
    (cx, cy), radius = cv2.minEnclosingCircle(coords)
    return (int(cx), int(cy)), int(radius)

def normalize_vector(arr):
    """نرمال‌سازی بردار برای مقایسه دقیق"""
    arr = np.array(arr, dtype=np.float32).flatten()
    arr = arr - np.mean(arr) # حذف بایاس نوری
    norm = np.linalg.norm(arr) + 1e-8
    return arr / norm

def get_face_embedding(landmarks):
    """تبدیل لندمارک‌های صورت به یک بردار ویژگی یکتا"""
    # فقط از مختصات هندسی استفاده می‌کنیم
    data = [[lm.x, lm.y, lm.z] for lm in landmarks]
    return normalize_vector(data)

def get_hand_embedding(landmarks):
    """تبدیل لندمارک‌های دست به بردار"""
    data = [[lm.x, lm.y, lm.z] for lm in landmarks]
    return normalize_vector(data)

def is_palm_open(landmarks):
    """بررسی باز بودن کف دست (برای جلوگیری از مشت کردن)"""
    # فاصله نوک انگشتان از مچ باید زیاد باشد
    tips = [4, 8, 12, 16, 20]
    wrist = np.array([landmarks[0].x, landmarks[0].y])
    avg_dist = 0
    for t in tips:
        tip = np.array([landmarks[t].x, landmarks[t].y])
        avg_dist += np.linalg.norm(tip - wrist)
    # عدد تجربی: اگر میانگین فاصله نوک انگشت‌ها تا مچ > 0.25 باشد، دست باز است
    return (avg_dist / 5) > 0.2

# ==========================================
# 1. فاز ثبت نام (Registration Phase)
# ==========================================

def register_mode(target="face"):
    cap = cv2.VideoCapture(0)
    collected_vectors = []
    
    print(f"\n>>> شروع ثبت {target.upper()} مالک...")
    print(">>> لطفاً ثابت بمانید و تغییرات جزئی داشته باشید تا مدل دقیق شود.")

    # تنظیمات بر اساس هدف (دست یا صورت)
    if target == "face":
        detector = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.7)
    else:
        detector = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

    while len(collected_vectors) < SAMPLES_NEEDED:
        ret, frame = cap.read()
        if not ret: continue
        
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if target == "face":
            res = detector.process(rgb)
            if res.multi_face_landmarks:
                lm = res.multi_face_landmarks[0].landmark
                collected_vectors.append(get_face_embedding(lm))
                
                # نمایش پیشرفت
                cv2.putText(frame, f"Face Samples: {len(collected_vectors)}/{SAMPLES_NEEDED}", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                # رسم عنبیه برای زیبایی
                try:
                    center, rad = get_iris_center(lm, LEFT_IRIS, w, h)
                    cv2.circle(frame, center, rad, (0, 255, 0), 1)
                except: pass
        else:
            res = detector.process(rgb)
            if res.multi_hand_landmarks:
                lm = res.multi_hand_landmarks[0].landmark
                if is_palm_open(lm):
                    collected_vectors.append(get_hand_embedding(lm))
                    cv2.putText(frame, f"Hand Samples: {len(collected_vectors)}/{SAMPLES_NEEDED}", (20, 50), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    mp_drawing.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)
                else:
                    cv2.putText(frame, "Open your hand!", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow(f"Register {target}", frame)
        if cv2.waitKey(1) == 27: # ESC
            break
            
    detector.close()
    cap.release()
    cv2.destroyAllWindows()

    if len(collected_vectors) >= SAMPLES_NEEDED:
        final_vec = np.mean(collected_vectors, axis=0)
        filename = FILE_FACE_VEC if target == "face" else FILE_HAND_VEC
        np.save(filename, final_vec)
        print(f">>> ثبت {target} با موفقیت انجام شد! فایل ذخیره شد: {filename}")
    else:
        print(">>> عملیات لغو شد.")

# ==========================================
# 2. فاز شناسایی فوق پیشرفته (Ultimate Recognition)
# ==========================================

def security_system():
    if not os.path.exists(FILE_FACE_VEC):
        print("خطا: فایل چهره یافت نشد. ابتدا اجرا کنید: python ultimate_owner.py --register-face")
        return

    print(">>> سیستم امنیتی فعال شد.")
    owner_face_vec = np.load(FILE_FACE_VEC)
    owner_hand_vec = np.load(FILE_HAND_VEC) if os.path.exists(FILE_HAND_VEC) else None

    cap = cv2.VideoCapture(0)

    # اجرای همزمان FaceMesh و Hands
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.6, min_tracking_confidence=0.6)
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6)

    while True:
        ret, frame = cap.read()
        if not ret: break
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_res = face_mesh.process(rgb)
        hand_res = hands.process(rgb)

        # وضعیت‌های امنیتی
        is_face_match = False
        is_eyes_open = False
        is_hand_match = False # اگر دست ثبت نشده باشد، پیش‌فرض True می‌شود
        if owner_hand_vec is None: is_hand_match = True

        # --- پردازش چهره ---
        if face_res.multi_face_landmarks:
            landmarks = face_res.multi_face_landmarks[0].landmark
            
            # 1. بررسی شباهت چهره
            current_vec = get_face_embedding(landmarks)
            if len(current_vec) == len(owner_face_vec):
                face_dist = np.linalg.norm(current_vec - owner_face_vec)
                if face_dist < FACE_MATCH_THRESHOLD:
                    is_face_match = True
                    face_color = (0, 255, 0) # سبز
                else:
                    face_color = (0, 0, 255) # قرمز
                
                # نمایش گرافیکی شباهت
                similarity_pct = max(0, int((1 - (face_dist / (FACE_MATCH_THRESHOLD * 2))) * 100))
                cv2.putText(frame, f"ID Match: {similarity_pct}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, face_color, 2)

            # 2. بررسی باز بودن چشم (Liveness)
            l_ear = calculate_ear(landmarks, LEFT_EYE_IDX, w, h)
            r_ear = calculate_ear(landmarks, RIGHT_EYE_IDX, w, h)
            avg_ear = (l_ear + r_ear) / 2.0

            if avg_ear > EYE_OPEN_THRESHOLD:
                is_eyes_open = True
                eye_status = "OPEN (Live)"
                eye_color = (0, 255, 0)
            else:
                eye_status = "CLOSED"
                eye_color = (0, 0, 255)
            
            cv2.putText(frame, f"Eyes: {eye_status}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, eye_color, 2)

            # 3. رسم سایبرنتیک عنبیه (Iris HUD)
            l_center, l_rad = get_iris_center(landmarks, LEFT_IRIS, w, h)
            r_center, r_rad = get_iris_center(landmarks, RIGHT_IRIS, w, h)
            # دایره دور عنبیه
            cv2.circle(frame, l_center, l_rad, (0, 255, 255), 1)
            cv2.circle(frame, r_center, r_rad, (0, 255, 255), 1)
            # نقطه مرکز عنبیه
            cv2.circle(frame, l_center, 2, (0, 0, 255), -1)
            cv2.circle(frame, r_center, 2, (0, 0, 255), -1)

        # --- پردازش دست ---
        if owner_hand_vec is not None and hand_res.multi_hand_landmarks:
            h_lm = hand_res.multi_hand_landmarks[0].landmark
            if is_palm_open(h_lm):
                current_h_vec = get_hand_embedding(h_lm)
                if len(current_h_vec) == len(owner_hand_vec):
                    hand_dist = np.linalg.norm(current_h_vec - owner_hand_vec)
                    if hand_dist < HAND_MATCH_THRESHOLD:
                        is_hand_match = True
                        cv2.putText(frame, "Hand: MATCH", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    else:
                        cv2.putText(frame, "Hand: WRONG", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                mp_drawing.draw_landmarks(frame, hand_res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)
        
        # --- تصمیم نهایی (Access Control) ---
        if is_face_match and is_eyes_open and is_hand_match:
            # کادر سبز دور کل تصویر
            cv2.rectangle(frame, (0, 0), (w, h), (0, 255, 0), 8)
            cv2.putText(frame, "ACCESS GRANTED", (w//2 - 180, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            cv2.putText(frame, "Welcome Owner", (w//2 - 130, h//2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        elif is_face_match and not is_eyes_open:
             cv2.putText(frame, "OPEN EYES TO VERIFY", (w//2 - 180, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.imshow("Ultimate Security System", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--register-face", action="store_true", help="Register Owner Face")
    parser.add_argument("--register-hand", action="store_true", help="Register Owner Hand")
    args = parser.parse_args()

    if args.register_face:
        register_mode("face")
    elif args.register_hand:
        register_mode("hand")
    else:
        security_system()