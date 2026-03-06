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

    print("=" * 80)
    print("HEARTBEAT DEBUG TEST")
    print("=" * 80)
    print(f"\nConnecting to MARS device on {PORT}...")

    # Initialize MARS device (auto_heartbeat disabled for manual testing)
    mars = QtMars(port=PORT, baudrate=BAUDRATE, auto_heartbeat=False)

    if not mars.is_connected():
        print(f"❌ Failed to connect to MARS device on {PORT}")
        print("   Make sure the device is connected and the port is correct")
        sys.exit(1)

    print("✓ Connected successfully\n")

    # Send a few commands to see the output format
    print("\n1. Sending GET_VERSION command...")
    print("   Expected output: [0xAA, 0xAA, length, 0x00, checksum]")
    mars.get_version()
    time.sleep(0.1)

    print("\n2. Sending HEARTBEAT command...")
    print("   Expected output: [0xAA, 0xAA, 0x02, 0x80, 0xD6]")
    print("   Breakdown:")
    print("     - 0xAA, 0xAA = Headers")
    print("     - 0x02 = Length (1 byte payload + 1 byte checksum)")
    print("     - 0x80 = HEARTBEAT command")
    print("     - 0xD6 = Checksum (170+170+2+128) % 256 = 214 (0xD6)")
    mars.send_heartbeat()
    time.sleep(0.1)

    print("\n3. Sending STOP_STREAM command...")
    print("   Expected output: [0xAA, 0xAA, 0x02, 0x05, checksum]")
    mars.stop_sensorstream()
    time.sleep(0.1)

    print("\n4. Sending START_STREAM command...")
    print("   Expected output: [0xAA, 0xAA, 0x02, 0x04, checksum]")
    mars.start_sensorstream()
    mars.set_diagnostic_mode()

    time.sleep(0.1)

    # Wait a bit to see any response
    print("\n" + "=" * 80)
    print("Waiting 2 seconds to see device response...")
    print("=" * 80)

    # Create a timer to keep the event loop alive briefly
    while QTimer.singleShot(200, app.quit):
        
        print(mars.angle1)
        print(mars.angle2)
        print(mars.angle3)
        print(mars.angle4)
        
        print(mars.imu_angle1)
        print(mars.imu_angle2)
        print(mars.imu_angle3)
        print(mars.imu_angle4)
    
    app.exec()

    # Cleanup
    print("\nClosing connection...")
    mars.stop_sensorstream()
    mars.close()
    print("✓ Test complete")

if __name__ == "__main__":
    main()
