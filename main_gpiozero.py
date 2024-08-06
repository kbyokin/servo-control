from fastapi import FastAPI
from gpiozero import AngularServo, LED
from time import sleep
from pydantic import BaseModel

app = FastAPI()

AZ_PIN = 12
ALT_PIN = 23
LASER_PIN = 18

az_servo = AngularServo(AZ_PIN, min_angle=0, max_angle=180)
alt_servo = AngularServo(ALT_PIN, min_angle=0, max_angle=180)
laser = LED(LASER_PIN)

class ServoControlRequest(BaseModel):
    angle1: int
    angle2: int

def angle_to_pulse_width(angle):
    return int(500 + (2400 - 500) * angle / 180)

def set_angle(angles):
    az_angle, alt_angle = angles
    
    az_servo.angle = az_angle
    alt_servo.angle = alt_angle
    
    sleep(0.1)  # Allow time for the servos to move

def set_laser(state):
    if state == 0:
        laser.off()
    else:
        laser.on()

@app.get("/")
async def main():
    return "Usage: POST to /servo/az/{az}/alt/{alt}"

@app.post("/servo/az/{az}/alt/{alt}/laser/{laser_state}")
async def control_servo(az: int, alt: int, laser_state: int):
    set_angle((az, alt))
    set_laser(laser_state)
    return {"az": az, "alt": alt, "laser_state": laser_state}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
