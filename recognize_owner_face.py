import cv2
import numpy as np
import mediapipe as mp

mp_face = mp.solutions.face_mesh

# Load the saved owner face vector
owner_vector = np.load("owner_face.npy")

cap = cv2.VideoCapture(0)

# --- NEW THRESHOLD for large values ---
THRESHOLD = 3500   # <<—— مناسب برای فاصله‌های 2700–3000

def compare(v1, v2):
    return np.linalg.norm(v1 - v2)

with mp_face.FaceMesh(static_image_mode=False, max_num_faces=1) as face_mesh:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)

        if result.multi_face_landmarks:
            face = result.multi_face_landmarks[0]
            points = []

            for lm in face.landmark:
                points.append([lm.x, lm.y, lm.z])

            face_vector = np.array(points).flatten()

            dist = compare(owner_vector, face_vector)

            # Display the distance value
            cv2.putText(frame, f"dist: {dist:.1f}", (20, 450),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

            if dist < THRESHOLD:
                text = "OWNER DETECTED ✓"
                color = (0,255,0)
            else:
                text = "NOT OWNER ✗"
                color = (0,0,255)

            cv2.putText(frame, text, (20,50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.imshow("Face Recognition", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
