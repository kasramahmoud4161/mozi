import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh
cap = cv2.VideoCapture(0)

print("\n>>> در حال ثبت چهره مالک...")
print(">>> لطفاً مستقیم به دوربین نگاه کنید...\n")

with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7) as face_mesh:

    saved = False

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)

        if result.multi_face_landmarks:
            face = result.multi_face_landmarks[0]

            vector = []
            for lm in face.landmark:
                vector.append(lm.x)
                vector.append(lm.y)
                vector.append(lm.z)

            face_vec = np.array(vector)

            # ذخیره
            np.save("owner_face.npy", face_vec)
            print("\n>>> چهره مالک با موفقیت ذخیره شد! (owner_face.npy)\n")
            saved = True

        cv2.putText(frame, "Recording Owner Face...", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.imshow("Register Owner", frame)

        if saved or cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
