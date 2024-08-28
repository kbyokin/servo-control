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

from cv2 import aruco

MARKER_SIZE = 2.5  # centimeters (measure your printed marker size)
marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
param_markers = aruco.DetectorParameters_create()

# Initialize global variables
clicked_hsv = None
hsv_image = None
target_point = None

x_err, y_err = [], []


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

def crop_image_with_padding(image, center_point, padding):
    x, y = center_point
    h, w = image.shape[:2]

    # Calculate the bounding box with padding
    x1 = max(x - padding, 0)
    y1 = max(y - padding, 0)
    x2 = min(x + padding, w)
    y2 = min(y + padding, h)

    # Crop the image using the bounding box
    cropped_image = image[y1:y2, x1:x2]
    return cropped_image

def detect_blobs(image, color_bounds):
    global hsv_image
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_bound = color_bounds[0]
    upper_bound = color_bounds[1]
    
    mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

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
    api_url = "http://172.23.161.109:8300/detect_grape_bunch"
    az, alt = 90, 80
    fov_h, fov_v = 95, 72
    # laser_offset_h = 6
    # laser_offset_v = -1
    laser_offset_h = 0
    laser_offset_v = 0
    remove_to_im = []
    remove_id = None
    remove_id_xyxy = []
    berries_depth = []
    target_index = 0
    
    
    save_data = False
    
    file = open_new_csv_file()

    with managed_resources() as (picam2, output, servo_motors):
        servo_motors.set_angles(az, alt)
        servo_motors.set_laser(1)  # turn on laser
        try:
            prev_time = time.time()
            frame_count = 0
            with concurrent.futures.ThreadPoolExecutor() as executor:
                while True:
                    start_time = time.time()
                    id = datetime.datetime.now().__str__()
                    byte_image = get_frame(output)
                    
                    image = byte_to_np_array(byte_image, save_img=False)
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    im_h, im_w = image.shape[:2]
                    im_center = (int(im_w / 2), int(im_h / 2))
                    
                    gray_frame = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                    marker_corners, marker_IDs, reject = aruco.detectMarkers(
                        gray_frame, marker_dict, parameters=param_markers
                    )
                    
                    if marker_corners:
                        total_markers = range(0, marker_IDs.size)
                        for ids, corners, i in zip(marker_IDs, marker_corners, total_markers):
                            corners = corners.reshape(4, 2)
                            corners = corners.astype(int)
                            top_right = corners[0].ravel()
                            top_left = corners[1].ravel()
                            bottom_right = corners[2].ravel()
                            bottom_left = corners[3].ravel()
                            
                            # Calculate the width and height of the marker
                            width = np.linalg.norm(top_right - top_left)
                            height = np.linalg.norm(top_right - bottom_right)

                            # You can take the average of width and height as the marker size
                            marker_size = (width + height) / 2
                            linear_ratio = MARKER_SIZE / marker_size 
                            # print(linear_ratio)
                    else:
                        az, alt = 90, 80
                        servo_motors.set_angles(az, alt)
                    
                    # blue
                    blue_lower_bound = np.array([90, 100, 100])
                    blue_upper_bound = np.array([140, 255, 255])
                    
                    # green
                    green_lower_bound = np.array([20, 100, 100])
                    green_upper_bound = np.array([60, 255, 255])
                    
                    # red
                    red_lower_bound = np.array([144, 100, 100])
                    red_upper_bound = np.array([179, 255, 255])
                    
                    laser_contour = detect_blobs(image, [red_lower_bound, red_upper_bound])
                    
                    red_blobs = []
                    min_area, max_area = 100, 2000
                    # largest_contour_image = np.zeros_like(image)
                    for contour in laser_contour:
                        area = cv2.contourArea(contour)
                        if min_area <= area <= max_area:
                            M = cv2.moments(contour)
                            if M['m00'] != 0:
                                cx = int(M['m10'] / M['m00'])
                                cy = int(M['m01'] / M['m00'])
                                
                                blob_center = (cx, cy)
                                # print(f'laser area: {area}, center: {blob_center}')
                                cv2.circle(image, blob_center, 3, (255, 0, 0), -1)
                                red_blobs.append(blob_center)
                    
                    if len(red_blobs) == 1:
                        contours = detect_blobs(image, [blue_lower_bound, blue_upper_bound])
                        # print(contours)
                        blobs_center = []
                        # min_area, max_area = 500, 3000 # 25cm
                        min_area, max_area = 1000, 10000 # 15cm
                        for idx, contour in enumerate(contours):
                            area = cv2.contourArea(contour)
                            print(area)
                            if min_area <= area <= max_area:
                                M = cv2.moments(contour)
                                if M['m00'] != 0:
                                    cx = int(M['m10'] / M['m00'])
                                    cy = int(M['m01'] / M['m00'])
                                    blob_center = (cx, cy)
                                    cv2.circle(image, blob_center, 3, (0, 255, 0), 1)
                                    blobs_center.append(blob_center)
                        
                        print(f'blobs center: {len(blobs_center)}')
                        # print(linear_ratio)
                        blobs_number = len(blobs_center)
                        if blobs_number >= 1:
                        # if blobs_number > 10 and blobs_number < 40:
                        # if True:
                            target_point = blobs_center[target_index]
                            horizontal_angle = angular_distance(red_blobs[0][0], target_point[0], fov_h, im_w)
                            vertical_angle = angular_distance(red_blobs[0][1], target_point[1], fov_v, im_h)

                            az = az - horizontal_angle - laser_offset_h
                            alt = alt + vertical_angle + laser_offset_v
                            
                            if az < 30: az = 30
                            if az > 140: az = 140
                            if alt < 30: alt = 30
                            if alt > 140: alt = 140
                        
                            servo_motors.set_angles(az, alt)
                            time.sleep(0.3)
                            # print(az, alt)
                            
                            x_err, y_err = red_blobs[0][0] - target_point[0], red_blobs[0][1] - target_point[1]
                            # x_err, y_err = im_center[0] - target_point[0], im_center[1] - target_point[1]
                            print(f'{linear_ratio * abs(x_err)}cm')
                            x_err_cm, y_err_cm = linear_ratio * abs(x_err), linear_ratio * abs(y_err)
                            print(x_err, y_err)
                            if abs(x_err) < 50 and abs(y_err) < 50:
                                # servo_motors.set_laser(1)  # turn on laser
                                crop_image = crop_image_with_padding(image, target_point, 150)
                                cv2.imwrite(f'./laser_accuracy/real15cm_{x_err_cm:.2f}_{y_err_cm:.2f}.jpg', crop_image)
                                target_index += 1
                                print(f'target: {target_index}, blobs number: {blobs_number}')
                                if target_index == blobs_number:
                                    target_index = 0
                            # else:
                            #     servo_motors.set_laser(0)
                            
                            
                    # cv2.circle(image, im_center, 3, (0, 0, 255), -1)
                    cv2.imwrite('captured_image_blob.jpg', image)

                    # Calculate FPS
                    end_time = time.time()
                    frame_time = end_time - start_time
                    frame_count += 1
                    if end_time - prev_time >= 1.0:
                        fps = frame_count / (end_time - prev_time)
                        print(f"FPS: {fps:.2f}")
                        frame_count = 0
                        prev_time = end_time

        except Exception as e:
            print(f"An error occurred in main loop: {e}")

if __name__ == "__main__":
    main_loop()
