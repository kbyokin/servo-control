import cv2
from control_motors import ServoControl
import numpy as np
import json
import requests

# Open a connection to the camera (0 is usually the built-in camera, 1 or higher for USB cameras)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Capture a single frame

class GlobalState:
    def __init__(self):
        self.az = 90
        self.alt = 50
        self.fov_h = 95
        self.fov_v = 72
        self.servo_motors = ServoControl()

state = GlobalState()

def angular_distance(x_c, x_t, fov, im_dim):
    degree_per_pixel = fov / im_dim
    angle_target = (x_c - x_t) * degree_per_pixel
    return angle_target
        
def detect_via_api(api_url, image_bytes, predict_remove=False):
    try:
        files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}
        data = {'predict_remove': str(predict_remove)}

        response = requests.post(api_url, files=files, data=data)

        if response.status_code == 200:
            response_dict = json.loads(response.content.decode())
            return response_dict
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception in detect_via_api: {e}")
        return None

api_url = "https://grape-headset-api.ai-8lab.com/detect_grape_bunch"
state.servo_motors.set_angles(state.az, state.alt)

while True:
    ret, frame = cap.read()
    if ret:
        # Save the captured frame to an image file
        rgb_frame = cv2.resize(frame, (640, 480))
        _, buffer = cv2.imencode('.jpg', rgb_frame)
        frame_bytes = buffer.tobytes()
        pred = detect_via_api(api_url, frame_bytes, predict_remove=True)
        # print(pred)
        
        bunch_xyxy = pred.get('bunch', None)
        im_h, im_w, = rgb_frame.shape[:2]
        im_center = (int(im_w / 2), int(im_h / 2))
        if len(bunch_xyxy) != 0:
            bunch_center = ((bunch_xyxy[0] + bunch_xyxy[2]) / 2, (bunch_xyxy[1] + bunch_xyxy[3]) / 2)
            print(f'bunch_xyxy: {bunch_center}')
            print(f'im_center: {im_center}')
            # distancee = (im_center[0] - bunch_xyxy[0], im_center[1] - bunch_xyxy[1])
            
            horizontal_angle = angular_distance(im_center[0], bunch_center[0], state.fov_h, im_w)
            vertical_angle = angular_distance(im_center[1], bunch_center[1], state.fov_v, im_h)
            print(f'horizontal_angle: {horizontal_angle}, vertical_angle: {vertical_angle}')
            calculate_az = state.az - horizontal_angle
            calculate_alt = state.alt + vertical_angle
            state.az = np.clip(calculate_az, 30, 120)
            state.alt = np.clip(calculate_alt, 30, 120)
            print(f'calculate angle az:{int(calculate_az)}, alt:{int(calculate_alt)}')
            
            state.servo_motors.set_angles(state.az, state.alt)
            print('---------------------------')
            cv2.circle(rgb_frame, (int(bunch_center[0]), int(bunch_center[1])), 2, (0, 255, 0), -1)
            
        # print("Image saved successfully.")
        cv2.circle(rgb_frame, im_center, 10, (0, 0, 255), 2)
        cv2.imwrite('captured_image.jpg', rgb_frame)
        
    else:
        print("Error: Could not read frame.")

# Release the camera
cap.release()