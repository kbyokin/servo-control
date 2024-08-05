from fastapi import FastAPI
import pigpio
from time import sleep
from pydantic import BaseModel

app = FastAPI()

AZ_PIN = 12
ALT_PIN = 23
LASER_PIN = 18

# Initialize pigpio
pi = pigpio.pi()
pi.set_mode(LASER_PIN, pigpio.OUTPUT)

class ServoControlRequest(BaseModel):
    angle1: int
    angle2: int

def angle_to_pulse_width(angle):
    return int(500 + (2400 - 500) * angle / 180)

def set_angle(angles):
    az_angle, alt_angle = angles
    az_pw = angle_to_pulse_width(az_angle)
    alt_pw = angle_to_pulse_width(alt_angle)
    
    pi.set_servo_pulsewidth(AZ_PIN, az_pw)
    pi.set_servo_pulsewidth(ALT_PIN, alt_pw)
    
    sleep(0.1)  # Allow time for the servos to move

def set_laser(state):
    pi.write(LASER_PIN, state)

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
