from gpiozero import AngularServo, LED
from time import sleep

servo1 = AngularServo(12, min_angle=-90, max_angle=90)
servo2 = AngularServo(23, min_angle=-90, max_angle=90)

while True:
    servo1.angle = -90
    servo2.angle = -90
    sleep(2)
    servo1.angle = -45
    servo2.angle = -45
    sleep(2)
    servo1.angle = 0
    servo2.angle = 0
    sleep(2)
    servo1.angle = 45
    servo2.angle = 45
    sleep(2)
    servo1.angle = 90
    servo2.angle = 90
    sleep(2)