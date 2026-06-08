"""
Simple test to send a heartbeat and observe the outgoing packet.

This script demonstrates sending a heartbeat command and shows
the debug output of what's actually transmitted over the serial port.
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from qtmars import QtMars

# Configuration
PORT = "COM4"  # Change this to your COM port
BAUDRATE = 115200

def main():
    """Send a single heartbeat and show debug output."""
    app = QApplication(sys.argv)
    # Initialize MARS device (auto_heartbeat disabled for manual testing)
    mars = QtMars(port=PORT, baudrate=BAUDRATE, auto_heartbeat=False)

    if not mars.is_connected():
        sys.exit(1)

    print("✓ Connected successfully\n")
    mars.get_version()
    mars.start_sensorstream()
    mars.send_heartbeat()
    mars.set_diagnostic_mode()
    
    # QTimer.singleShot(5000, app.quit)
    
    while True:
        mars.send_heartbeat()
        print("Heartbeat sent.")

        print(mars._framerate)
        # print(mars.imu_angle2)
        # print(mars.imu_angle3)
        # print(mars.imu_angle4)
        # print(mars.angle4)
    
    print(mars.imu_angle1)

    # time.sleep(2)


    # Create a timer to keep the event loop alive briefly
    # while QTimer.singleShot(200, app.quit):
        
    #     print(mars.angle1)
    #     print(mars.angle2)
    #     print(mars.angle3)
    #     print(mars.angle4)
        
    #     print(mars.imu_angle1)
    #     print(mars.imu_angle2)
    #     print(mars.imu_angle3)
    #     print(mars.imu_angle4)
    
    app.exec()

    # Cleanup
    print("\nClosing connection...")
    mars.stop_sensorstream()
    mars.close()
    print("✓ Test complete")

if __name__ == "__main__":
    main()
