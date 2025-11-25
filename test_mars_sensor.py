"""
Simple test script to read and print MARS sensor data.

This script demonstrates basic usage of the QtMars class to connect
to the MARS device and display sensor readings in real-time.
"""

import sys
import signal
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from qtmars import QtMars

# Configuration
PORT = "COM4"  # Change this to your COM port
BAUDRATE = 115200

def handle_new_data(mars: QtMars):
    """Callback function when new data arrives from MARS device."""
    # Print device state
    print(f"\n--- Packet #{mars.packet_number} | Runtime: {mars.runtime:.2f}s ---")

    # Print joint angles
    print(f"Joint Angles (deg): θ1={mars.angle1:.2f}, θ2={mars.angle2:.2f}, θ3={mars.angle3:.2f}, θ4={mars.angle4:.2f}")

    # Print IMU angles
    print(f"IMU Angles (deg):   θ1={mars.imu_angle1:.2f}, θ2={mars.imu_angle2:.2f}, θ3={mars.imu_angle3:.2f}, θ4={mars.imu_angle4:.2f}")

    # Print force sensor
    print(f"Force: {mars.force:.2f} kg")

    # Print control values
    print(f"Control: Target={mars.target:.2f}, Desired={mars.desired:.2f}, Output={mars.control:.2f}")

    # Print endpoint position using forward kinematics
    x, y, z = mars.ep_pos
    print(f"Endpoint Position (m): x={x:.3f}, y={y:.3f}, z={z:.3f}")

    # Print error status if present
    if mars.error != 0:
        print(f"⚠️  ERROR: {mars.error_string}")

    # Print frame rate
    print(f"Frame Rate: {mars.framerate:.1f} Hz")

def main():
    """Main function to run the MARS sensor test."""
    app = QApplication(sys.argv)

    # Initialize MARS device with automatic heartbeat
    print(f"Connecting to MARS device on {PORT}...")
    mars = QtMars(port=PORT, baudrate=BAUDRATE, auto_heartbeat=True, log_heartbeat=False)

    if not mars.is_connected():
        print("❌ Failed to connect to MARS device!")
        print(f"   Make sure the device is connected to {PORT}")
        sys.exit(1)

    print("✓ Connected to MARS device")

    # Setup signal handler for Ctrl+C
    def signal_handler(_sig, _frame):
        print("\n\nKeyboard interrupt received. Cleaning up...")
        mars.stop_sensorstream()
        mars.close()
        app.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Timer to allow Python to process signals (makes Ctrl+C work with Qt)
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    # Get device version
    mars.get_version()

    # Wait a bit for version response
    QTimer.singleShot(200, lambda: print(f"Device: {mars.devname} | Version: {mars.version} | Compiled: {mars.compliedate}"))

    # Connect to newdata signal
    mars.newdata.connect(lambda: handle_new_data(mars))

    # Start sensor streaming
    print("\nStarting sensor stream...")
    mars.start_sensorstream()

    print("Receiving data... (Press Ctrl+C to stop)\n")
    print("=" * 80)

    # Run Qt event loop
    app.exec()

if __name__ == "__main__":
    main()
