import cv2

def capture_frames():
    # Open the default camera (use 0 for the first camera, 1 for the second, etc.)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Press 'q' to quit.")

    frame_count = 0

    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()

        if not ret:
            print("Error: Failed to capture frame.")
            break

        # Display the resulting frame
        # cv2.imshow('Camera Feed', frame)

        # Save each frame continuously
        filename = f'./capture_frame/frame_{frame_count:04d}.png'
        cv2.imwrite(filename, frame)
        print(f"Frame saved as {filename}")
        frame_count += 1

        # Wait for a key press
        key = cv2.waitKey(1) & 0xFF

        # If 'q' is pressed, exit the loop
        if key == ord('q'):
            print("Exiting...")
            break

    # Release the capture and close all OpenCV windows
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_frames()
