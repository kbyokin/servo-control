import pigpio
from time import sleep

class ServoControl():
    def __init__(self):
        self.AZ_PIN = 12
        self.ALT_PIN = 23
        self.LASER_PIN = 18

        # Initialize pigpio
        self.pwm = pigpio.pi()
        self.pwm.set_mode(self.LASER_PIN, pigpio.OUTPUT)
        self.pwm.set_mode(self.AZ_PIN, pigpio.OUTPUT)
        self.pwm.set_mode(self.ALT_PIN, pigpio.OUTPUT)

        self.pwm.set_PWM_frequency(self.AZ_PIN, 50)
        self.pwm.set_PWM_frequency(self.ALT_PIN, 50)
    
    def angle_to_pulse_width(self, angle):
        return int(500 + (2500 - 500) * angle / 180)

    def set_angles(self, az_angle, alt_angle):
        az_pw = self.angle_to_pulse_width(int(az_angle))
        alt_pw = self.angle_to_pulse_width(int(alt_angle))
        
        self.pwm.set_servo_pulsewidth(self.AZ_PIN, az_pw)
        self.pwm.set_servo_pulsewidth(self.ALT_PIN, alt_pw)
        
        sleep(0.1)  # Allow time for the servos to move

    def set_laser(self, state):
        self.pwm.write(self.LASER_PIN, state)