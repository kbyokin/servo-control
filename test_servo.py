import RPi.GPIO as GPIO
import pigpio
from time import sleep
from pydantic import BaseModel

AZ_PIN = 12
ALT_PIN = 23

def angle_to_pulse_width(angle):
    return int(500 + (2400 - 500) * angle / 180)

pwm = pigpio.pi()
pwm.set_mode(AZ_PIN, pigpio.OUTPUT)
pwm.set_mode(ALT_PIN, pigpio.OUTPUT)

pwm.set_PWM_frequency(AZ_PIN, 50)
pwm.set_PWM_frequency(ALT_PIN, 50)



# GPIO.setmode(GPIO.BCM)
# GPIO.setup(AZ_PIN, GPIO.OUT)
# GPIO.setup(ALT_PIN, GPIO.OUT)

# az_pwm = GPIO.PWM(AZ_PIN, 50) # 50Hz PWM frequency
# az_pwm.start(0)
# alt_pwm = GPIO.PWM(ALT_PIN, 50) # 50Hz PWM frequency
# alt_pwm.start(0)

class ServoControlRequest(BaseModel):
    angle1: int
    angle2: int

def set_angle(angles):
    print(angles)
    az_duty, alt_duty = angle_to_pulse_width(angles[0]), angle_to_pulse_width(angles[1])
    pwm.set_servo_pulsewidth(AZ_PIN, az_duty)
    pwm.set_servo_pulsewidth(ALT_PIN, alt_duty)
    sleep(0.1)
    
    # duty_az, duty_alt = angles[0] / 18 + 2, angles[1] / 18 + 2
    # GPIO.output(AZ_PIN, True)
    # GPIO.output(ALT_PIN, True)
    
    # az_pwm.ChangeDutyCycle(duty_az)
    # alt_pwm.ChangeDutyCycle(duty_alt)
    
    # sleep(0.1) # depending on angle, if too fast that cannot range large dynamic range
    # GPIO.output(AZ_PIN, False)
    # az_pwm.ChangeDutyCycle(0)
    # GPIO.output(ALT_PIN, False)
    # alt_pwm.ChangeDutyCycle(0)
    # #GPIO.cleanup()

def main():
    for i in range(0, 180):
        set_angle((i, i))
        
if __name__ == '__main__':
    main()
