import cv2
from control_motors import ServoControl
import numpy as np
import json
import requests
import time
from picamera2 import Picamera2
import pyttsx3

import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Open a connection to the camera (0 is usually the built-in camera, 1 or higher for USB cameras)
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

class GlobalState:
    def __init__(self):
        self.az = 90
        self.alt = 70
        self.fov_h = 90
        self.fov_v = 72
        self.servo_motors = ServoControl()
        self.servo_motors.set_laser(0)          # Turn off the laser when first initialized

state = GlobalState()

def concatenate_images_horizontally(left_img, right_img):
    import cv2
    # Ensure same height if needed
    height = min(left_img.shape[0], right_img.shape[0])
    left_resized = cv2.resize(left_img, (int(left_img.shape[1] * (height/left_img.shape[0])), height))
    right_resized = cv2.resize(right_img, (int(right_img.shape[1] * (height/right_img.shape[0])), height))
    # Concatenate
    return cv2.hconcat([left_resized, right_resized])

def crop_image_by_box(image, bounding_box):
    left, top, right, bottom = bounding_box
    # Clamp to image size
    left = max(0, min(left, image.shape[1]))
    top = max(0, min(top, image.shape[0]))
    right = max(0, min(right, image.shape[1]))
    bottom = max(0, min(bottom, image.shape[0]))
    # Crop
    return image[top:bottom, left:right]

def calculate_center(bounding_box):
    """
    Calculate center coordinates of a bounding box
    Args:
        bounding_box: BoundingBox object with origin_x, origin_y, width, height
    Returns:
        tuple: (center_x, center_y)
    """
    center_x = bounding_box.origin_x + (bounding_box.width / 2)
    center_y = bounding_box.origin_y + (bounding_box.height / 2)
    return (center_x, center_y)

def angular_distance(x_c, x_t, fov, im_dim):
    degree_per_pixel = fov / im_dim
    angle_target = (x_c - x_t) * degree_per_pixel
    return angle_target

state.servo_motors.set_angles(state.az, state.alt)

base_options = python.BaseOptions(model_asset_path="/home/pi5/servo-control/models/mobilenet_grape_0120.tflite")

options = vision.ObjectDetectorOptions(base_options=base_options,
                                        #    running_mode=vision.RunningMode.LIVE_STREAM,
                                           max_results=100, score_threshold=0.5)
detector = vision.ObjectDetector.create_from_options(options)

while True:
    frame = picam2.capture_array()
    # Save the captured frame to an image file
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    im_h, im_w, = rgb_frame.shape[:2]
    im_center = (int(im_w / 2), int(im_h / 2))
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    detection_result = detector.detect(mp_image)
    # print(detection_result)
    detected_objects = detection_result.detections
    if len(detected_objects) == 0:
        # cv2.circle(rgb_frame, im_center, 10, (0, 0, 255), 2)
        cv2.imwrite('captured_image.jpg', rgb_frame)
        continue
    
    classes = [detected_objects[i].categories[0].category_name for i in range(len(detected_objects))]
    classes = np.array(classes)
    print(classes)
    bunch_idx = np.where(classes == 'bunch')[0]
    print(bunch_idx)
    if len(bunch_idx) == 0:
        print(f"{time.time()}: Bunch not found")
        # cv2.circle(rgb_frame, im_center, 10, (0, 0, 255), 2)
        cv2.imwrite('captured_image.jpg', rgb_frame)
        continue
    bunch_bounding_box = detected_objects[int(bunch_idx[0])].bounding_box
    bunch_center = calculate_center(bunch_bounding_box)
    print(f'bunch_center: {bunch_center}')
    print(f'im_center: {im_center}')
    
    # distancee = (im_center[0] - bunch_xyxy[0], im_center[1] - bunch_xyxy[1])
    
    horizontal_angle = angular_distance(im_center[0], bunch_center[0], state.fov_h, im_w)
    vertical_angle = angular_distance(im_center[1], bunch_center[1], state.fov_v, im_h)
    print(f'horizontal_angle: {horizontal_angle}, vertical_angle: {vertical_angle}')
    calculate_az = state.az - horizontal_angle
    calculate_alt = state.alt + vertical_angle
    state.az = np.clip(calculate_az, 30, 120)
    state.alt = np.clip(calculate_alt, 30, 120) - 7
    print(f'calculate angle az:{int(calculate_az)}, alt:{int(calculate_alt)}')
    
    state.servo_motors.set_angles(state.az, state.alt)
    print('---------------------------')
    cv2.circle(rgb_frame, (int(bunch_center[0]), int(bunch_center[1])), 10, (0, 0, 255), 2)
    
    if abs(im_center[0] - bunch_center[0]) < 70 and abs(im_center[1] - bunch_center[1]) < 70:
        print('Bunch is in the center')
        state.servo_motors.set_laser(1)
        cv2.circle(rgb_frame, (int(bunch_center[0]), int(bunch_center[1])), 10, (0, 255, 0), 2)
    else:
        state.servo_motors.set_laser(0)
        
    # print("Image saved successfully.")
    # cv2.circle(rgb_frame, im_center, 10, (0, 0, 255), 2)
    cv2.imwrite('captured_image.jpg', rgb_frame)