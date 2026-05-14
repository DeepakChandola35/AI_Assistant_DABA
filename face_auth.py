# import face_recognition
# import cv2
# import pickle
# import os
#
#
# def verify_face(max_attempts=3, threshold=0.5):
#     try:
#         # ✅ FIX: Always load file from correct directory
#         BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#         file_path = os.path.join(BASE_DIR, "user_face.pkl")
#
#         if not os.path.exists(file_path):
#             print("❌ user_face.pkl not found. Please run register.py first.")
#             return False
#
#         with open(file_path, "rb") as f:
#             known_encoding = pickle.load(f)
#
#         cap = cv2.VideoCapture(2)
#
#         print("🔐 Face Authentication Started...")
#         print("Press 'q' to exit")
#
#         attempts = 0
#
#         while attempts < max_attempts:
#             ret, frame = cap.read()
#
#             if not ret:
#                 print("❌ Camera error")
#                 break
#
#             rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#
#             # Detect faces
#             face_locations = face_recognition.face_locations(rgb)
#             encodings = face_recognition.face_encodings(rgb)
#
#             result_text = "Scanning..."
#
#             if len(encodings) > 0:
#                 for (top, right, bottom, left), face_encoding in zip(face_locations, encodings):
#
#                     distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
#
#                     if distance < threshold:
#                         result_text = "✅ Access Granted"
#
#                         # Draw green box
#                         cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
#
#                         cv2.putText(frame, result_text, (left, top - 10),
#                                     cv2.FONT_HERSHEY_SIMPLEX, 0.8,
#                                     (0, 255, 0), 2)
#
#                         cv2.imshow("Face Authentication", frame)
#                         cv2.waitKey(1500)
#
#                         cap.release()
#                         cv2.destroyAllWindows()
#                         print("✅ Face Verified")
#                         return True
#
#                     else:
#                         result_text = "❌ Access Denied"
#                         attempts += 1
#
#                         # Draw red box
#                         cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
#
#                         cv2.putText(frame, result_text, (left, top - 10),
#                                     cv2.FONT_HERSHEY_SIMPLEX, 0.8,
#                                     (0, 0, 255), 2)
#
#             # Show status text
#             cv2.putText(frame, result_text, (20, 40),
#                         cv2.FONT_HERSHEY_SIMPLEX, 1,
#                         (255, 255, 255), 2)
#
#             cv2.imshow("Face Authentication", frame)
#
#             # Exit manually
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break
#
#         cap.release()
#         cv2.destroyAllWindows()
#
#         print("❌ Face authentication failed")
#         return False
#
#     except Exception as e:
#         print("Error in face auth:", e)
#         return False


import face_recognition
import cv2
import pickle
import numpy as np


def verify_face():

    # Load saved faces
    with open("user_faces.pkl", "rb") as f:
        known_encodings = pickle.load(f)

    cap = cv2.VideoCapture(2)

    print("🔐 Face Authentication Started")

    while True:

        ret, frame = cap.read()

        if not ret:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces
        face_locations = face_recognition.face_locations(rgb)

        face_encodings = face_recognition.face_encodings(
            rgb,
            face_locations
        )

        access_granted = False

        for (top, right, bottom, left), face_encoding in zip(
                face_locations,
                face_encodings
        ):

            # Compare with all saved faces
            matches = face_recognition.compare_faces(
                known_encodings,
                face_encoding,
                tolerance=0.5
            )

            face_distances = face_recognition.face_distance(
                known_encodings,
                face_encoding
            )

            best_match_index = np.argmin(face_distances)

            # ACCESS GRANTED
            if matches[best_match_index]:

                access_granted = True

                # GREEN BOX
                cv2.rectangle(
                    frame,
                    (left, top),
                    (right, bottom),
                    (0, 255, 0),
                    3
                )

                cv2.putText(
                    frame,
                    "ACCESS GRANTED",
                    (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2
                )

            # ACCESS DENIED
            else:

                cv2.rectangle(
                    frame,
                    (left, top),
                    (right, bottom),
                    (0, 0, 255),
                    3
                )

                cv2.putText(
                    frame,
                    "ACCESS DENIED",
                    (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 0, 255),
                    2
                )

        cv2.imshow("Neo Face Authentication", frame)

        # SUCCESS
        if access_granted:

            print("✅ Authorized User Detected")

            cv2.waitKey(1500)

            cap.release()
            cv2.destroyAllWindows()

            return True

        # EXIT
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    print("❌ Authentication Failed")

    return False