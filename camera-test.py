import cv2

print("OpenCV:", cv2.__version__)

for index in range(5):
    print(f"\nПроверяю камеру {index}...")

    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if cap.isOpened():
        print(f"КАМЕРА {index} НАЙДЕНА")

        ret, frame = cap.read()

        if ret:
            print("Кадр успешно получен")

            cv2.imshow(
                f"Camera {index}",
                frame
            )

            cv2.waitKey(3000)
            cv2.destroyAllWindows()

            cap.release()
            break

        else:
            print("Камера открылась, но кадр получить не удалось")

    else:
        print(f"Камера {index} не открылась")

    cap.release()
else:
    print("\nКамеры не найдены.")
