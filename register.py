# import face_recognition
# import cv2
# import pickle
#
# cap = cv2.VideoCapture(2)
#
# print("Press 's' to capture face")
#
# while True:
#     ret, frame = cap.read()
#     cv2.imshow("Register Face", frame)
#
#     key = cv2.waitKey(1)
#
#     if key == ord('s'):
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#
#         encodings = face_recognition.face_encodings(rgb)
#
#         if len(encodings) == 0:
#             print("❌ No face detected")
#             continue
#
#         with open("user_face.pkl", "wb") as f:
#             pickle.dump(encodings[0], f)
#
#         print("✅ Face registered successfully!")
#         break
#
#     elif key == ord('q'):
#         break
#
# cap.release()
# cv2.destroyAllWindows()





import face_recognition
import cv2
import pickle

cap = cv2.VideoCapture(2)

all_encodings = []

MAX_IMAGES = 10

print("\n📸 Multi Face Registration")
print("Press 's' to save face")
print("Press 'q' to finish\n")

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    cv2.putText(
        frame,
        f"Saved Faces: {len(all_encodings)}/{MAX_IMAGES}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Register Face", frame)

    key = cv2.waitKey(1)

    # SAVE FACE
    if key == ord('s'):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        encodings = face_recognition.face_encodings(rgb)

        if len(encodings) == 0:

            print("❌ No face detected")
            continue

        all_encodings.append(encodings[0])

        print(f"✅ Face {len(all_encodings)} saved")

        if len(all_encodings) >= MAX_IMAGES:
            break

    # QUIT
    elif key == ord('q'):
        break


# SAVE ALL ENCODINGS
if all_encodings:

    with open("user_faces.pkl", "wb") as f:

        pickle.dump(all_encodings, f)

    print(f"\n✅ {len(all_encodings)} face samples saved!")

else:

    print("❌ No faces saved")


cap.release()
cv2.destroyAllWindows()