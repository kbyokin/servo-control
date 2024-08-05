import pigpio
import time

LASER_PIN = 18  # Choose the appropriate GPIO pin for your laser

# Initialize pigpio
pi = pigpio.pi()

# Set up the laser pin as output
pi.set_mode(LASER_PIN, pigpio.OUTPUT)

def set_laser(state):
    pi.write(LASER_PIN, state)

def laser_test_routine(duration=60, interval=1):
    end_time = time.time() + duration
    while time.time() < end_time:
        print("Laser ON")
        set_laser(1)  # Turn laser on
        time.sleep(interval)
        print("Laser OFF")
        set_laser(0)  # Turn laser off
        time.sleep(interval)

if __name__ == "__main__":
    try:
        print("Starting laser test. Press Ctrl+C to stop.")
        laser_test_routine()
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        set_laser(0)  # Ensure laser is off
        pi.stop()  # Clean up pigpio resources
        print("Test finished. Laser turned off.")
