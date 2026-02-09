"""
MARS Workspace Assessment System - Main Launcher Window.

Professional application for clinical workspace assessments with three
assessment types: AP, ML, and MLAP.

Author: Sivakumar Balasubramanian
Date: 09 February 2026
Email: siva82kb@gmail.com
"""

import sys
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QLabel, QComboBox,
                               QGroupBox, QMessageBox, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from qtmars import QtMars
from assessment_ap import AssessmentAPWindow
from assessment_ml import AssessmentMLWindow
from assessment_mlap import AssessmentMLAPWindow


class MarsAssessmentLauncher(QMainWindow):
    """Main launcher window for MARS workspace assessments."""

    def __init__(self):
        super().__init__()
        self.mars = None
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)

        # Assessment windows
        self.ap_window = None
        self.ml_window = None
        self.mlap_window = None

        self.init_ui()
        self.populate_com_ports()

    def init_ui(self):
        """Create main window UI."""
        self.setWindowTitle("MARS Workspace Assessment System")
        self.setFixedSize(650, 700)  # Increased height to fit all content

        # Apply modern styling with better contrast and visibility
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                background-color: transparent;
            }
            QGroupBox {
                border: 2px solid #2196F3;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 20px;
                padding-left: 10px;
                padding-right: 10px;
                padding-bottom: 10px;
                background-color: white;
                font-weight: bold;
                font-size: 11pt;
                color: #2196F3;
            }
            QGroupBox::title {
                color: #2196F3;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 10pt;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #FFFFFF;
            }
            QComboBox {
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: white;
                font-size: 10pt;
                min-height: 25px;
            }
            QLabel {
                font-size: 10pt;
                color: #333333;
                background-color: transparent;
            }
        """)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Connection Group
        conn_group = QGroupBox("Device Connection")
        conn_layout = QVBoxLayout(conn_group)

        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        port_layout.addWidget(self.port_combo, 1)
        self.refresh_ports_btn = QPushButton("⟳")
        self.refresh_ports_btn.setFixedWidth(40)
        self.refresh_ports_btn.clicked.connect(self.populate_com_ports)
        port_layout.addWidget(self.refresh_ports_btn)
        conn_layout.addLayout(port_layout)

        # Connect button and status
        connect_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        connect_layout.addWidget(self.connect_btn)

        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        connect_layout.addWidget(self.status_label)
        connect_layout.addStretch()
        conn_layout.addLayout(connect_layout)

        main_layout.addWidget(conn_group)

        # Configuration Group
        config_group = QGroupBox("Device Configuration")
        config_layout = QVBoxLayout(config_group)

        # Limb selection
        limb_layout = QHBoxLayout()
        limb_layout.addWidget(QLabel("Limb:"))
        self.limb_combo = QComboBox()
        self.limb_combo.addItems(["RIGHT", "LEFT"])
        self.limb_combo.currentTextChanged.connect(self.on_limb_changed)
        limb_layout.addWidget(self.limb_combo)
        limb_layout.addStretch()
        config_layout.addLayout(limb_layout)

        # Calibrate button
        self.calibrate_btn = QPushButton("Calibrate Device")
        self.calibrate_btn.clicked.connect(self.on_calibrate)
        self.calibrate_btn.setEnabled(False)
        config_layout.addWidget(self.calibrate_btn)

        # Set plane button
        self.set_plane_btn = QPushButton("Set Plane (90°)")
        self.set_plane_btn.clicked.connect(self.on_set_plane)
        self.set_plane_btn.setEnabled(False)
        config_layout.addWidget(self.set_plane_btn)

        main_layout.addWidget(config_group)

        # Workspace Assessments Group
        assess_group = QGroupBox("Workspace Assessments")
        assess_layout = QVBoxLayout(assess_group)

        # AP Assessment Button
        self.ap_btn = self.create_assessment_button(
            "↕  Assess Anterior-Posterior",
            "(Forward/Backward Movement)",
            self.launch_ap_assessment
        )
        assess_layout.addWidget(self.ap_btn)

        # ML Assessment Button
        self.ml_btn = self.create_assessment_button(
            "↔  Assess Medio-Lateral",
            "(Side-to-Side Movement)",
            self.launch_ml_assessment
        )
        assess_layout.addWidget(self.ml_btn)

        # MLAP Assessment Button
        self.mlap_btn = self.create_assessment_button(
            "⊕  Assess Combined (MLAP)",
            "(Full Workspace Envelope)",
            self.launch_mlap_assessment
        )
        assess_layout.addWidget(self.mlap_btn)

        main_layout.addWidget(assess_group)

        main_layout.addStretch()

    def create_assessment_button(self, title: str, subtitle: str, callback) -> QPushButton:
        """Create a styled assessment button with title and subtitle.

        Args:
            title: Main button text
            subtitle: Descriptive subtitle
            callback: Click handler function

        Returns:
            QPushButton configured with layout
        """
        btn = QPushButton(f"{title}\n{subtitle}")
        btn.setMinimumHeight(70)
        btn.clicked.connect(callback)
        btn.setEnabled(False)
        btn.setStyleSheet("""
            QPushButton {
                text-align: center;
                padding: 15px;
                font-size: 11pt;
            }
            QPushButton:hover {
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
        """)
        return btn

    def populate_com_ports(self):
        """Populate COM port dropdown with available ports."""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)

        if self.port_combo.count() == 0:
            self.port_combo.addItem("No ports found")

    def toggle_connection(self):
        """Toggle device connection."""
        if self.mars is None:
            self.connect_device()
        else:
            self.disconnect_device()

    def connect_device(self):
        """Connect to MARS device."""
        port = self.port_combo.currentText()

        if port == "No ports found":
            QMessageBox.warning(self, "Connection Error",
                              "No COM ports available. Please check device connection.")
            return

        try:
            self.mars = QtMars(port=port, baudrate=115200, auto_heartbeat=False)

            if not self.mars.is_connected():
                QMessageBox.critical(self, "Connection Error",
                                   f"Failed to connect to {port}.\n"
                                   "Please check:\n"
                                   "- Device is powered on\n"
                                   "- Correct COM port selected\n"
                                   "- No other application using the port")
                self.mars = None
                return

            # Connection sequence
            self.mars.get_version()
            self.mars.start_sensorstream()
            self.mars.set_diagnostic_mode()
            self.mars.send_heartbeat()

            # Start heartbeat timer (every 3 seconds)
            self.heartbeat_timer.start(3000)

            # Update UI
            self.connect_btn.setText("Disconnect")
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.port_combo.setEnabled(False)
            self.refresh_ports_btn.setEnabled(False)

            # Enable configuration controls
            self.calibrate_btn.setEnabled(True)
            self.set_plane_btn.setEnabled(True)

            # Enable assessment buttons
            self.ap_btn.setEnabled(True)
            self.ml_btn.setEnabled(True)
            self.mlap_btn.setEnabled(True)

            print(f"Connected to MARS device on {port}")

        except Exception as e:
            QMessageBox.critical(self, "Connection Error",
                               f"Connection failed: {str(e)}")
            self.mars = None

    def disconnect_device(self):
        """Disconnect from MARS device."""
        if self.mars:
            self.heartbeat_timer.stop()
            self.mars.stop_sensorstream()
            self.mars.close()
            self.mars = None

            # Update UI
            self.connect_btn.setText("Connect")
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            self.port_combo.setEnabled(True)
            self.refresh_ports_btn.setEnabled(True)

            # Disable configuration controls
            self.calibrate_btn.setEnabled(False)
            self.set_plane_btn.setEnabled(False)

            # Disable assessment buttons
            self.ap_btn.setEnabled(False)
            self.ml_btn.setEnabled(False)
            self.mlap_btn.setEnabled(False)

            print("Disconnected from MARS device")

    def send_heartbeat(self):
        """Send periodic heartbeat to device."""
        if self.mars and self.mars.is_connected():
            self.mars.send_heartbeat()

    def on_limb_changed(self, limb: str):
        """Handle limb selection change.

        Args:
            limb: Selected limb ("LEFT" or "RIGHT")
        """
        if self.mars and self.mars.is_connected():
            try:
                self.mars.set_limb(limb)
                print(f"Limb set to: {limb}")
            except Exception as e:
                QMessageBox.warning(self, "Command Error",
                                  f"Failed to set limb: {str(e)}")

    def on_calibrate(self):
        """Handle calibrate button click."""
        if self.mars and self.mars.is_connected():
            try:
                self.mars.calibrate()
                QMessageBox.information(self, "Calibration",
                                      "Calibration command sent.\n"
                                      "Please follow device calibration procedure.")
                print("Calibration command sent")
            except Exception as e:
                QMessageBox.warning(self, "Command Error",
                                  f"Calibration failed: {str(e)}")

    def on_set_plane(self):
        """Handle set plane button click - sets robot to 90 degrees."""
        if self.mars and self.mars.is_connected():
            try:
                # Set control type to POSITION
                self.mars.set_control_type("POSITION")

                # Delay before setting target to allow device to process
                QTimer.singleShot(200, self._set_plane_target)

                print("Position control enabled, setting plane to 90 degrees")
            except Exception as e:
                QMessageBox.warning(self, "Command Error",
                                  f"Failed to set plane: {str(e)}")

    def _set_plane_target(self):
        """Helper to set plane target value after delay."""
        if self.mars and self.mars.is_connected():
            try:
                self.mars.set_control_target(90.0)
                print("Plane target set to 90 degrees")
            except Exception as e:
                QMessageBox.warning(self, "Command Error",
                                  f"Failed to set plane target: {str(e)}")

    def launch_ap_assessment(self):
        """Launch AP (Anterior-Posterior) assessment window."""
        if not self.mars or not self.mars.is_connected():
            QMessageBox.warning(self, "Connection Required",
                              "Please connect to device before starting assessment.")
            return

        if self.ap_window is None or not self.ap_window.isVisible():
            self.ap_window = AssessmentAPWindow(self.mars, self)
            # Update canvas limb type
            self.ap_window.canvas.limb_type = self.limb_combo.currentText()
            self.ap_window.show()
            print("Launched AP assessment window")

    def launch_ml_assessment(self):
        """Launch ML (Medio-Lateral) assessment window."""
        if not self.mars or not self.mars.is_connected():
            QMessageBox.warning(self, "Connection Required",
                              "Please connect to device before starting assessment.")
            return

        if self.ml_window is None or not self.ml_window.isVisible():
            self.ml_window = AssessmentMLWindow(self.mars, self)
            # Update canvas limb type
            self.ml_window.canvas.limb_type = self.limb_combo.currentText()
            self.ml_window.show()
            print("Launched ML assessment window")

    def launch_mlap_assessment(self):
        """Launch MLAP (Combined) assessment window."""
        if not self.mars or not self.mars.is_connected():
            QMessageBox.warning(self, "Connection Required",
                              "Please connect to device before starting assessment.")
            return

        if self.mlap_window is None or not self.mlap_window.isVisible():
            self.mlap_window = AssessmentMLAPWindow(self.mars, self)
            # Update canvas limb type
            self.mlap_window.canvas.limb_type = self.limb_combo.currentText()
            self.mlap_window.show()
            print("Launched MLAP assessment window")

    def closeEvent(self, event):
        """Handle window close event."""
        self.disconnect_device()
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MarsAssessmentLauncher()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
