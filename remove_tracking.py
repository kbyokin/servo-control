import io
import sys
import cv2
import requests
import json
from PIL import Image
import numpy as np
sys.path.append('./')
from camera_stream import initialize_camera, get_frame
from control_motors import ServoControl

picam2, output = initialize_camera()
servo_motors = ServoControl()

az, alt = 20, 30
fov_h, fov_v = 95, 72

api_url = "http://172.23.161.109:8300/detect_grape_bunch"

def byte_to_np_array(byte_image, save_img=True):
    image = Image.open(io.BytesIO(byte_image))
    if save_img:
        image.save('captured_image.png')
    return np.array(image)

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
        raise Exception

try:
    while True:
        byte_image = get_frame(output)
        servo_motors.set_angles(az, alt)
        pred = detect_via_api(api_url, byte_image, predict_remove=True)
        image = byte_to_np_array(byte_image, save_img=False)
        print(f'image shape: {image.shape}')
        print(pred)

except Exception as e:
    print("An error occurred:", e)