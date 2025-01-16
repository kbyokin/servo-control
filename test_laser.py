from time import sleep
from control_motors import ServoControl

# Initialize the ServoControl instance
servo = ServoControl()

# Turn the laser ON
print("Turning laser ON")
servo.set_laser(1)
sleep(2)  # Keep the laser ON for 2 seconds

# Turn the laser OFF
print("Turning laser OFF")
servo.set_laser(0)
sleep(2)  # Wait for 2 seconds

# Repeat ON/OFF for testing
for _ in range(3):
    print("Laser ON")
    servo.set_laser(1)
    sleep(1)
    print("Laser OFF")
    servo.set_laser(0)
    sleep(1)

print("Laser control test completed.")
