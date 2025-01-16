from control_motors import ServoControl
import numpy as np
import json
import requests
import cv2

# Open a connection to the camera (0 is usually the built-in camera, 1 or higher for USB cameras)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()
    
    
while True:
    ret, frame = cap.read()
    if ret:
        # Save the captured frame to an image file
        rgb_frame = cv2.resize(frame, (640, 480))
        _, buffer = cv2.imencode('.jpg', rgb_frame)
        frame_bytes = buffer.tobytes()
        im_h, im_w, = rgb_frame.shape[:2]
        im_center = (int(im_w / 2), int(im_h / 2))
        
        cv2.circle(rgb_frame, im_center, 10, (0, 0, 255), 2)
        cv2.imwrite('captured_image.jpg', rgb_frame)
        
    else:
        print("Error: Could not read frame.")

# Release the camera
cap.release()