import io
import logging
from threading import Condition
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

def initialize_camera():
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(main={"size": (1280, 720)}))
    output = StreamingOutput()
    picam2.start_recording(JpegEncoder(), FileOutput(output))
    return picam2, output

def get_frame(output):
    with output.condition:
        output.condition.wait()
        frame = output.frame
    return frame
