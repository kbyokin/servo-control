from control_motors import ServoControl
import time

def test_motor():
    # Initialize the ServoControl instance
    servo = ServoControl()

    # Test range for azimuth and altitude (30 to 160 degrees)
    min_angle = 30
    max_angle = 120

    print("Testing motor movement from 30 to 160 degrees")

    try:
        # Move from 30 to 160 degrees
        for angle in range(80, 120 + 1, 10):
            print(f"Setting angle to {angle}")
            servo.set_angles(angle, angle)  # Setting both azimuth and altitude to the same value
            servo.set_laser(1)
            time.sleep(0.5)  # Pause for half a second to observe the movement

        # Move back from 160 to 30 degrees
        for angle in range(30, 100 - 1, -10):
            print(f"Setting angle to {angle}")
            servo.set_angles(angle, angle)  # Setting both azimuth and altitude to the same value
            time.sleep(0.5)  # Pause for half a second to observe the movement

    except Exception as e:
        print(f"An error occurred during the motor test: {e}")

    print("Motor test completed.")

if __name__ == "__main__":
    test_motor()
