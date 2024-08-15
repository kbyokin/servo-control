import io
import sys
import cv2
import requests
import json
from PIL import Image
import numpy as np
import datetime
import csv
from contextlib import contextmanager

sys.path.append('./')
from camera_stream import initialize_camera, get_frame
from control_motors import ServoControl

@contextmanager
def managed_resources():
    picam2, output = initialize_camera()
    servo_motors = ServoControl()
    try:
        yield picam2, output, servo_motors
    finally:
        # Properly close or release resources if needed
        if picam2:
            picam2.stop()
        if servo_motors:
            servo_motors.cleanup()

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
        print(f"Exception in detect_via_api: {e}")
        return None

def angular_distance(x_c, x_t, fov, im_dim):
    degree_per_pixel = fov / im_dim
    angle_target = (x_c - x_t) * degree_per_pixel
    return angle_target

def open_new_csv_file():
    global file_name, writer
    file_name = './tracking_data/' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_data.csv"
    file = open(file_name, 'a', newline='')
    fieldnames = ["id", "im_w", "im_h", "im_x", "im_y", "obj_x", "obj_y", 'obj_w', 'obj_h', "berry_size", "az", "alt", "dx", "dy"]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    return file

def main_loop():
    api_url = "http://172.23.161.109:8300/detect_grape_bunch"
    az, alt = 90, 80
    fov_h, fov_v = 95, 72
    laser_offset_h = 5
    laser_offset_v = 2
    remove_to_im = []
    remove_id = None
    remove_id_xyxy = []
    berries_depth = []
    
    file = open_new_csv_file()

    with managed_resources() as (picam2, output, servo_motors):
        servo_motors.set_angles(az, alt)
        try:
            while True:
                id = datetime.datetime.now().__str__()
                byte_image = get_frame(output)
                pred = detect_via_api(api_url, byte_image, predict_remove=True)
                image = byte_to_np_array(byte_image, save_img=False)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                im_h, im_w = image.shape[:2]
                im_center = (int(im_w / 2), int(im_h / 2))

                update_threshold = 50
                if pred is not None:
                    bunch_boxes = np.array(pred['bunch'])
                    berry_boxes = np.array(pred['berry'])
                    remove_box = np.array(pred['remove'])

                    if remove_id is None and len(remove_box) > 0:
                        remove_id = int(remove_box[4])
                    elif remove_to_im and (abs(remove_to_im[0]) < update_threshold) and (abs(remove_to_im[1]) < update_threshold):
                        pass

                    if len(bunch_boxes) > 0:
                        bunch_center = (int((bunch_boxes[0] + bunch_boxes[2]) / 2), int((bunch_boxes[1] + bunch_boxes[3]) / 2))

                        if len(remove_box) > 0 and len(berry_boxes) > 0:
                            berry_id = berry_boxes[:, 4]
                            remove_indice = berry_id == remove_id
                            if not remove_indice.any():
                                remove_id = remove_box[4]
                            else:
                                remove_id_xyxy = berry_boxes[remove_indice][0]
                                remove_center = (int((remove_id_xyxy[0] + remove_id_xyxy[2]) / 2), int((remove_id_xyxy[1] + remove_id_xyxy[3]) / 2))
                                cv2.rectangle(image, (int(remove_id_xyxy[0]), int(remove_id_xyxy[1])), (int(remove_id_xyxy[2]), int(remove_id_xyxy[3])), (255, 0, 0) if remove_to_im and (abs(remove_to_im[0]) < update_threshold) and (abs(remove_to_im[1]) < update_threshold) else (0, 0, 255), 2)
                                
                                remove_to_im = (im_center[0] - remove_center[0], im_center[1] - remove_center[1])
                                
                                horizontal_angle = angular_distance(im_center[0], remove_center[0], fov_h, im_w)
                                vertical_angle = angular_distance(im_center[1], remove_center[1], fov_v, im_h)
                                print(f'horizontal_angle: {horizontal_angle}, vertical_angle: {vertical_angle}')
                                print(az, alt)
                                az = az - horizontal_angle - laser_offset_h
                                alt = alt + vertical_angle + laser_offset_v
                                if az < 30:
                                    az = 30
                                elif az > 140:
                                    az = 140

                                if alt < 30:
                                    alt = 30
                                elif alt > 140:
                                    alt = 140

                                servo_motors.set_angles(az, alt)
                                if remove_to_im and (abs(remove_to_im[0]) < update_threshold) and (abs(remove_to_im[1]) < update_threshold):
                                    servo_motors.set_laser(1)
                                else:
                                    servo_motors.set_laser(0)
                                print(remove_to_im)
                                # cv2.circle(image, bunch_center, 3, (0, 0, 255), -1)
                                
                                new_row = {
                                    "id": id,
                                    "im_w": im_w,
                                    "im_h": im_h,
                                    "im_x": im_center[0],
                                    "im_y": im_center[1],
                                    "obj_x": remove_center[0],
                                    "obj_y": remove_center[1],
                                    'obj_w': remove_id_xyxy[2] - remove_id_xyxy[0],
                                    'obj_h': remove_id_xyxy[3] - remove_id_xyxy[1],
                                    "berry_size": (remove_id_xyxy[2] - remove_id_xyxy[0]) * (remove_id_xyxy[3] - remove_id_xyxy[1]),
                                    "az": az,
                                    "alt": alt,
                                    "dx": remove_to_im[0],
                                    "dy": remove_to_im[1]
                                }
                                writer.writerow(new_row)
                # cv2.circle(image, (int(im_w / 2), int(im_h / 2)), 3, (0, 0, 255), -1)
                cv2.imwrite('captured_image.jpg', image)
                
                

        except Exception as e:
            print(f"An error occurred in main loop: {e}")

if __name__ == "__main__":
    main_loop()
