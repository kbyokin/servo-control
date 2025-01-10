import numpy as np
import requests
import json
from picamera2 import Picamera2
from flask import Flask, Response
import cv2
from control_motors import ServoControl

# Initialize Flask app
app = Flask(__name__)

# Initialize Picamera2
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

class GlobalState:
    def __init__(self):
        self.az = 90
        self.alt = 80
        self.fov_h = 95
        self.fov_v = 72
        self.servo_motors = ServoControl()

state = GlobalState()

def generate_frames():
    """Generator function to yield frames."""
    while True:
        frame = picam2.capture_array()
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        # Yield frame as MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
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
    
@app.route('/snapshot')
def snapshot():
    api_url = "https://grape-headset-api.ai-8lab.com/detect_grape_bunch"
    state.servo_motors.set_angles(state.az, state.alt)
    
    """Capture a single snapshot and return it as a JPEG."""
    # Capture a frame from Picamera2
    frame = picam2.capture_array()
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Encode the frame to JPEG
    _, buffer = cv2.imencode('.jpg', rgb_frame)
    frame_bytes = buffer.tobytes()
    
    # Return the JPEG image as a response
    return Response(frame_bytes, mimetype='image/jpeg')

@app.route('/usb_stream')
def usb_stream():
    def generate_frames():
        """Stream frames from the USB camera."""
        cap = cv2.VideoCapture(0)
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        try:
            if not cap.isOpened():
                print("Error: Could not open camera.")
                return

            while True:
                ret, frame = cap.read()
                if ret:
                    print(f"Frame captured successfully. Shape: {frame.shape}")
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    print("Error: Could not read frame.")
                    break
                    
        except Exception as e:
            print(f"Camera error: {str(e)}")
        finally:
            cap.release()
            
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/test_camera')
def test_camera():
    """Test endpoint to verify camera access"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        return "Error: Could not open camera", 500
        
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        cv2.imwrite('test_frame.jpg', frame)
        return "Camera test successful - frame saved", 200
    else:
        return "Error: Could not read frame", 500

@app.route('/stream')
def stream():
    api_url = "https://grape-headset-api.ai-8lab.com/detect_grape_bunch"
    state.servo_motors.set_angles(state.az, state.alt)
    
    def generate_stream():
        while True:
            # Capture a frame from Picamera2
            frame = picam2.capture_array()
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', rgb_frame)
            frame_bytes = buffer.tobytes()
            
            # Call the API with the current frame
            pred = detect_via_api(api_url, frame_bytes, predict_remove=True)
            print(pred)  # Debugging: print API prediction
            
            bunch_xyxy = pred.get('bunch', None)
            im_h, im_w, = frame.shape[:2]
            im_center = (int(im_w / 2), int(im_h / 2))
            if len(bunch_xyxy) != 0:
                bunch_center = ((bunch_xyxy[0] + bunch_xyxy[2]) / 2, (bunch_xyxy[1] + bunch_xyxy[3]) / 2)
                
                
                horizontal_angle = angular_distance(im_center[0], bunch_xyxy[0], state.fov_h, im_w)
                vertical_angle = angular_distance(im_center[1], bunch_xyxy[1], state.fov_v, im_h)
                calculate_az = state.az - horizontal_angle
                calculate_alt = state.alt + vertical_angle
                state.az = np.clip(calculate_az, 30, 140)
                state.alt = np.clip(calculate_alt, 30, 120)
                
                
                state.servo_motors.set_angles(state.az, state.alt)
            
            # Yield frame for the MJPEG stream
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    # Return the MJPEG stream response
    return Response(generate_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    state.servo_motors.set_angles(state.az, state.alt)
    app.run(host='0.0.0.0', port=8080)