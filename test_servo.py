
import RPi.GPIO as GPIO
from time import sleep
from pydantic import BaseModel

AZ_PIN = 5
ALT_PIN = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(AZ_PIN, GPIO.OUT)
GPIO.setup(ALT_PIN, GPIO.OUT)

az_pwm = GPIO.PWM(AZ_PIN, 50) # 50Hz PWM frequency
az_pwm.start(0)
alt_pwm = GPIO.PWM(ALT_PIN, 50) # 50Hz PWM frequency
alt_pwm.start(0)

class ServoControlRequest(BaseModel):
    angle1: int
    angle2: int

def set_angle(angles):
    duty_az, duty_alt = angles[0] / 18 + 2, angles[1] / 18 + 2
    GPIO.output(AZ_PIN, True)
    GPIO.output(ALT_PIN, True)
    
    az_pwm.ChangeDutyCycle(duty_az)
    alt_pwm.ChangeDutyCycle(duty_alt)
    
    sleep(0.1) # depending on angle, if too fast that cannot range large dynamic range
    GPIO.output(AZ_PIN, False)
    az_pwm.ChangeDutyCycle(0)
    GPIO.output(ALT_PIN, False)
    alt_pwm.ChangeDutyCycle(0)
    #GPIO.cleanup()

def main():
    for i in range(0, 180):
        set_angle((i, i))
        
if __name__ == '__main__':
    main()
