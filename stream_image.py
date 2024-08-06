import io
import logging
from threading import Condition
import requests
import json

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

def detect_via_api(api_url, image_bytes, predict_remove=False):
    try:
        files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}
        data = {'predict_remove': str(predict_remove)}

        # Make the POST request with the image file
        response = requests.post(api_url, files=files, data=data)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # print("Image successfully posted to the API.")
            response_dict = json.loads(response.content.decode())
            return response_dict
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        raise Exception
    

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

api_url = "http://172.23.161.109:8300/detect_grape_bunch"

while True:
    with output.condition:
        output.condition.wait()
        frame = output.frame
        res = detect_via_api(api_url, frame, predict_remove=True)