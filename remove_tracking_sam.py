import io
import sys
import cv2
import requests
import json
from PIL import Image
import numpy as np
import datetime
import csv
import time
from contextlib import contextmanager
import concurrent.futures

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
    fieldnames = ["id", "im_w", "im_h", "im_x", "im_y", 'obj_id', "obj_x", "obj_y", 'obj_w', 'obj_h', "berry_size", "az", "alt", "dx", "dy"]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    return file

def main_loop():
    # api_url = "http://172.23.161.109:8300/detect_grape_bunch"
    # MBP
    # api_url = "http://192.168.182.179:8300/detect_grape_bunch"    # Maolab Wifi MBP
    # api_url = "http://192.168.1.106:8300/detect_grape_bunch"      # TP-link
    
    # Jetson
    # api_url = "http://192.168.1.178:8300/detect_grape_bunch"        # GTX
    # api_url = "http://192.168.9.170:8300/detect_grape_bunch"        # TP-link
    api_url = "http://192.168.9.170:8300/sam_tracking"        # TP-link
    az, alt = 90, 70
    # fov_h, fov_v = 95, 72 # arducam
    fov_h, fov_v = 66, 41   # picam m3
    laser_offset_h = 1
    laser_offset_v = -3
    remove_to_im = []
    remove_id = None
    remove_id_xyxy = []
    berries_depth = []
    
    save_data = False
    
    # file = open_new_csv_file()

    with managed_resources() as (picam2, output, servo_motors):
        initial_az, initial_alt = az, alt
        last_bunch_time = time.time()
        servo_motors.set_angles(az, alt)
        try:
            prev_time = time.time()
            frame_count = 0
            with concurrent.futures.ThreadPoolExecutor() as executor:
                while True:
                    start_time = time.time()
                    id = datetime.datetime.now().__str__()
                    byte_image = get_frame(output)
                    
                    # future_pred = executor.submit(detect_via_api, api_url, byte_image, True)
                    pred = detect_via_api(api_url, byte_image, predict_remove=True)
                    print(pred)
                    image = byte_to_np_array(byte_image, save_img=False)
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    im_h, im_w = image.shape[:2]
                    im_center = (int(im_w / 2), int(im_h / 2))
                    
                    # pred = future_pred.result()

                    update_threshold = 100
                    if pred is not None:
                        bunch_boxes = np.array(pred['bunch'])
                        berry_boxes = np.array(pred['berry'])
                        remove_box = np.array(pred['remove_xyxy'])
                        
                        if len(bunch_boxes) > 0:
                            last_bunch_time = time.time()
                        
                        # if remove_id is None and len(remove_box) > 0:
                        #     remove_id = int(remove_box[4])
                        # elif remove_to_im and (abs(remove_to_im[0]) < update_threshold) and (abs(remove_to_im[1]) < update_threshold):
                        #     # remove_id = int(remove_box[4])
                        #     pass

                        if len(bunch_boxes) > 0:
                            bunch_center = (int((bunch_boxes[0] + bunch_boxes[2]) / 2), int((bunch_boxes[1] + bunch_boxes[3]) / 2))
                            if len(remove_box) > 0 and len(berry_boxes) > 0:
                                remove_center = (int((remove_box[0] + remove_box[2]) / 2), int((remove_box[1] + remove_box[3]) / 2))
                                remove_to_im = (im_center[0] - remove_center[0], im_center[1] - remove_center[1])
                                cv2.rectangle(image, (int(remove_box[0]), int(remove_box[1])), (int(remove_box[2]), int(remove_box[3])), (255, 0, 0) if remove_to_im and (abs(remove_to_im[0]) < update_threshold) and (abs(remove_to_im[1]) < update_threshold) else (0, 0, 255), 2)
                                horizontal_angle = angular_distance(im_center[0], remove_center[0], fov_h, im_w)
                                vertical_angle = angular_distance(im_center[1], remove_center[1], fov_v, im_h)
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
                    # Move back to initial angles if no bunch found for 5 seconds
                    if time.time() - last_bunch_time > 3:
                        az = initial_az
                        alt = initial_alt
                        servo_motors.set_angles(az, alt)
                    
                    # Get current time as string
                    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Put timestamp on image
                    cv2.putText(image, timestamp_str, (10, image.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                1, (0, 255, 0), 2, cv2.LINE_AA)

                    # Save image with timestamp overlay
                    # cv2.imwrite('captured_image.jpg', image)

                    # Calculate FPS
                    end_time = time.time()
                    frame_time = end_time - start_time
                    frame_count += 1
                    if end_time - prev_time >= 1.0:
                        fps = frame_count / (end_time - prev_time)
                        print(f"FPS: {fps:.2f}")
                        frame_count = 0
                        prev_time = end_time
                        
                    # if time.time() - last_bunch_time > 3:
                    #     az = initial_az
                    #     alt = initial_alt
                    #     servo_motors.set_angles(az, alt)

        except Exception as e:
            print(f"An error occurred in main loop: {e}")

if __name__ == "__main__":
    main_loop()
