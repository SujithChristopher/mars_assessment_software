"""
Test continuous heartbeat sending to clear NOHEARTBEAT error.

This script sends heartbeats automatically and monitors if the error clears.
"""

import sys
import signal
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from qtmars import QtMars

# Configuration
PORT = "COM4"  # Change this to your COM port
BAUDRATE = 115200

def main():
    """Send continuous heartbeats and monitor error status."""
    app = QApplication(sys.argv)

    print("=" * 80)
    print("CONTINUOUS HEARTBEAT TEST - Monitor Error Clearing")
    print("=" * 80)

    # Initialize MARS with auto heartbeat enabled
    print(f"\nConnecting to {PORT} with auto-heartbeat enabled...")
    mars = QtMars(port=PORT, baudrate=BAUDRATE, auto_heartbeat=True, log_heartbeat=True)

    if not mars.is_connected():
        print(f"❌ Failed to connect!")
        sys.exit(1)

    print("✓ Connected")
    print(f"✓ Auto-heartbeat active: {mars.is_heartbeat_active}")
    print(f"✓ Heartbeat interval: 2000ms (firmware expects within 5000ms)")

    # Setup signal handler for Ctrl+C
    def signal_handler(_sig, _frame):
        print("\n\nStopping...")
        mars.stop_sensorstream()
        mars.close()
        app.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Timer to allow Python to process signals
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)

    # Monitor error status
    error_count = [0]
    def monitor_errors():
        if mars.is_data_available():
            print(mars.imu_angle1)
            # if mars.error != 0:
            #     error_count[0] += 1
            #     if error_count[0] % 20 == 1:  # Print every 20th error to reduce spam
            #         print(f"⚠️  Still has error: {mars.error_string} | Time: {mars.runtime:.2f}s")
            # else:
            #     if error_count[0] > 0:
            #         print(f"✓ ERROR CLEARED! | Time: {mars.runtime:.2f}s")
            #         error_count[0] = 0

    # Connect to newdata signal to monitor
    mars.newdata.connect(monitor_errors)

    # Start streaming
    print("\nStarting sensor stream...")
    mars.start_sensorstream()

    print("\n" + "=" * 80)
    print("Monitoring... Heartbeats are being sent every 2 seconds")
    print("Watch for 'ERROR CLEARED!' message")
    print("Press Ctrl+C to stop")
    print("=" * 80 + "\n")

    # Run
    app.exec()

if __name__ == "__main__":
    main()
