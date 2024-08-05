import pigpio
import time
from pydantic import BaseModel

AZ_PIN = 5
ALT_PIN = 18

# Initialize pigpio
pi = pigpio.pi()

class ServoControlRequest(BaseModel):
    angle1: int
    angle2: int

def angle_to_pulse_width(angle):
    return int(500 + (2400 - 500) * angle / 180)

def set_angle(target_angles, current_angles, step=5):
    az_start, alt_start = current_angles
    az_end, alt_end = target_angles
    
    for i in range(step + 1):
        az_angle = az_start + (az_end - az_start) * i / step
        alt_angle = alt_start + (alt_end - alt_start) * i / step
        
        az_pw = angle_to_pulse_width(az_angle)
        alt_pw = angle_to_pulse_width(alt_angle)
        
        pi.set_servo_pulsewidth(AZ_PIN, az_pw)
        pi.set_servo_pulsewidth(ALT_PIN, alt_pw)
        
        time.sleep(0.02)
    
    return target_angles

def main():
    current_angles = (0, 0)
    
    # Move from 0 to 180 degrees
    for i in range(0, 181, 10):
        current_angles = set_angle((i, i), current_angles)
    
    # Move back to 0 degrees
    for i in range(180, -1, -10):
        current_angles = set_angle((i, i), current_angles)

if __name__ == '__main__':
    try:
        main()
    finally:
        pi.set_servo_pulsewidth(AZ_PIN, 0)
        pi.set_servo_pulsewidth(ALT_PIN, 0)
        pi.stop()
