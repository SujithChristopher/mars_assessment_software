import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QGridLayout, QPushButton,
                               QLineEdit, QGroupBox, QComboBox, QSlider, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from qtmars import QtMars
import time


class MarsDisplayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mars = None

        # Heartbeat timer - send heartbeat every 3 seconds
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("MARS Sensor Data Display")
        self.setGeometry(100, 100, 600, 400)

        # Set green terminal style
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #001a00;
            }
            QLabel {
                color: #00ff00;
                font-family: 'Courier New', monospace;
                font-size: 11pt;
            }
            QLineEdit {
                background-color: #003300;
                color: #00ff00;
                border: 1px solid #00aa00;
                padding: 3px;
                font-family: 'Courier New', monospace;
            }
            QPushButton {
                background-color: #004400;
                color: #00ff00;
                border: 2px solid #00aa00;
                padding: 5px 15px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #006600;
                border-color: #00ff00;
            }
            QPushButton:pressed {
                background-color: #00aa00;
            }
            QGroupBox {
                color: #00ff00;
                border: 2px solid #00aa00;
                margin-top: 10px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #00ff00;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QSlider::groove:vertical {
                background-color: #00aa00;
                border-radius: 3px;
                width: 4px;
                margin: 0px;
            }
            QSlider::handle:vertical {
                background-color: #00ff00;
                border: 2px solid #00aa00;
                height: 18px;
                margin: -8px -10px;
                border-radius: 3px;
            }
            QSlider::handle:vertical:hover {
                background-color: #00ff00;
                border: 2px solid #00ff00;
            }
            QSlider::handle:vertical:pressed {
                background-color: #00aa00;
            }
            QSlider::sub-page:vertical {
                background-color: #00ff00;
                border-radius: 3px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Connection controls (Top)
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("COM Port:"))
        self.port_input = QLineEdit("COM4")
        self.port_input.setMaximumWidth(100)
        conn_layout.addWidget(self.port_input)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn)

        conn_layout.addStretch()
        main_layout.addLayout(conn_layout)

        # Data display with control panel on the right
        data_container = QWidget()
        data_container_layout = QHBoxLayout(data_container)

        # Left side: Data display grid
        data_widget = QWidget()
        data_layout = QGridLayout(data_widget)

        self.value_labels = {}

        # Joint Angles
        angles_group = QGroupBox("Joint Angles (degrees)")
        angles_layout = QGridLayout(angles_group)
        for i in range(1, 5):
            angles_layout.addWidget(QLabel(f"angle{i}:"), i-1, 0)
            label = QLabel("--")
            self.value_labels[f"angle{i}"] = label
            angles_layout.addWidget(label, i-1, 1)
        data_layout.addWidget(angles_group, 0, 0)

        # IMU Angles
        imu_group = QGroupBox("IMU Angles (degrees)")
        imu_layout = QGridLayout(imu_group)
        for i in range(1, 5):
            imu_layout.addWidget(QLabel(f"imu_angle{i}:"), i-1, 0)
            label = QLabel("--")
            self.value_labels[f"imu_angle{i}"] = label
            imu_layout.addWidget(label, i-1, 1)
        data_layout.addWidget(imu_group, 0, 1)

        # Control Parameters
        control_group = QGroupBox("Control Parameters")
        control_layout = QGridLayout(control_group)
        control_params = ["force", "target", "desired", "control"]
        for i, param in enumerate(control_params):
            control_layout.addWidget(QLabel(f"{param}:"), i, 0)
            label = QLabel("--")
            self.value_labels[param] = label
            control_layout.addWidget(label, i, 1)
        data_layout.addWidget(control_group, 1, 0)

        # Error Terms
        error_group = QGroupBox("Error Terms")
        error_layout = QGridLayout(error_group)
        error_params = ["err_p", "err_d", "err_i"]
        for i, param in enumerate(error_params):
            error_layout.addWidget(QLabel(f"{param}:"), i, 0)
            label = QLabel("--")
            self.value_labels[param] = label
            error_layout.addWidget(label, i, 1)
        data_layout.addWidget(error_group, 1, 1)

        # Device Status
        status_group = QGroupBox("Device Status")
        status_layout = QGridLayout(status_group)
        status_params = ["status", "datatype", "controltype", "limb",
                        "error", "packet_number", "runtime", "framerate"]
        for i, param in enumerate(status_params):
            status_layout.addWidget(QLabel(f"{param}:"), i, 0)
            label = QLabel("--")
            self.value_labels[param] = label
            status_layout.addWidget(label, i, 1)
        data_layout.addWidget(status_group, 2, 0)

        # Endpoint Position
        ep_group = QGroupBox("Endpoint Position (meters)")
        ep_layout = QGridLayout(ep_group)
        ep_params = ["ep_x", "ep_y", "ep_z"]
        for i, param in enumerate(ep_params):
            ep_layout.addWidget(QLabel(f"{param}:"), i, 0)
            label = QLabel("--")
            self.value_labels[param] = label
            ep_layout.addWidget(label, i, 1)
        data_layout.addWidget(ep_group, 2, 1)

        # Error Status (Compact)
        error_status_group = QGroupBox("Error Status")
        error_status_layout = QGridLayout(error_status_group)
        error_status_layout.addWidget(QLabel("Code:"), 0, 0)
        self.error_code_label = QLabel("--")
        error_status_layout.addWidget(self.error_code_label, 0, 1)
        error_status_layout.addWidget(QLabel("Desc:"), 0, 2)
        self.error_desc_label = QLabel("None")
        self.error_desc_label.setWordWrap(True)
        error_status_layout.addWidget(self.error_desc_label, 0, 3)
        data_layout.addWidget(error_status_group, 3, 0, 1, 2)

        # Add data grid to left side of container
        data_container_layout.addWidget(data_widget, 1)

        # Right side: Control Panel
        control_panel_widget = QWidget()
        control_panel_layout = QVBoxLayout(control_panel_widget)

        # Limb Selection
        limb_layout = QHBoxLayout()
        limb_layout.addWidget(QLabel("Limb:"))
        self.limb_combo = QComboBox()
        self.limb_combo.addItems(["LEFT", "RIGHT"])
        self.limb_combo.setCurrentIndex(0)
        self.limb_combo.currentTextChanged.connect(self.on_limb_changed)
        limb_layout.addWidget(self.limb_combo)
        control_panel_layout.addLayout(limb_layout)

        # Calibrate Button
        self.calibrate_btn = QPushButton("Calibrate")
        self.calibrate_btn.clicked.connect(self.on_calibrate)
        control_panel_layout.addWidget(self.calibrate_btn)

        control_panel_layout.addSpacing(20)

        # Position Target
        pos_label = QLabel("Position Target:")
        control_panel_layout.addWidget(pos_label)

        # Slider
        self.pos_target_slider = QSlider(Qt.Orientation.Vertical)
        self.pos_target_slider.setMinimum(0)
        self.pos_target_slider.setMaximum(100)
        self.pos_target_slider.setSingleStep(5)
        self.pos_target_slider.setPageStep(5)
        self.pos_target_slider.setValue(0)
        self.pos_target_slider.setMinimumHeight(200)
        self.pos_target_slider.setMaximumWidth(80)
        self.pos_target_slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self.pos_target_slider.setTickInterval(10)
        control_panel_layout.addWidget(self.pos_target_slider)

        # Value display
        self.pos_target_label = QLabel("0")
        self.pos_target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pos_target_slider.valueChanged.connect(self.on_slider_value_changed)
        control_panel_layout.addWidget(self.pos_target_label)

        # Set Target Button
        self.set_target_btn = QPushButton("Set Target")
        self.set_target_btn.clicked.connect(self.on_set_target)
        control_panel_layout.addWidget(self.set_target_btn)

        control_panel_layout.addStretch()
        data_container_layout.addWidget(control_panel_widget, 0)

        main_layout.addWidget(data_container)

    def send_heartbeat(self):
        """Send heartbeat to MARS device."""
        if self.mars and self.mars.is_connected():
            self.mars.send_heartbeat()

    def toggle_connection(self):
        if self.mars is None:
            port = self.port_input.text()
            try:
                # Create connection with auto_heartbeat disabled
                self.mars = QtMars(port=port, baudrate=115200, auto_heartbeat=False)

                # Check if connected
                if not self.mars.is_connected():
                    print(f"Failed to connect to {port}")
                    self.mars = None
                    return

                print(f"✓ Connected successfully to {port}\n")

                # Connect signal for data updates
                self.mars.newdata.connect(self.update_display)

                # Execute connection sequence
                self.mars.get_version()
                time.sleep(0.05)
                self.mars.start_sensorstream()
                time.sleep(0.05)
                self.mars.set_diagnostic_mode()
                time.sleep(0.05)
                self.mars.send_heartbeat()
                time.sleep(0.05)
                
                # Send initial limb choice
                self.mars.set_limb(self.limb_combo.currentText())

                # Start heartbeat timer (3 seconds = 3000 ms)
                self.heartbeat_timer.start(3000)
                print("Heartbeat timer started (3 second interval)")

                # Update UI
                self.connect_btn.setText("Disconnect")
                self.port_input.setEnabled(False)

            except Exception as e:
                print(f"Connection failed: {e}")
                self.mars = None
        else:
            self.disconnect_device()

    def disconnect_device(self):
        if self.mars:
            try:
                # Stop heartbeat timer
                if self.heartbeat_timer.isActive():
                    self.heartbeat_timer.stop()
                    print("Heartbeat timer stopped")

                # Stop streaming
                self.mars.stop_sensorstream()
                # Close serial connection
                if hasattr(self.mars, 'dev') and self.mars.dev:
                    self.mars.dev.abort()
                    self.mars.dev.quit()
                    self.mars.dev.wait()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                self.mars = None
                self.connect_btn.setText("Connect")
                self.port_input.setEnabled(True)
                for label in self.value_labels.values():
                    label.setText("--")
                print("Disconnected")

    def on_limb_changed(self, limb):
        """Handle limb selection change."""
        if self.mars and self.mars.is_connected():
            try:
                self.mars.set_limb(limb)
                print(f"Limb set to: {limb}")
            except Exception as e:
                print(f"Error setting limb: {e}")

    def on_calibrate(self):
        """Handle calibrate button click."""
        if self.mars and self.mars.is_connected():
            try:
                QMessageBox.information(self, "Calibration Steps",
                                      "To calibrate the device:\n"
                                      "1. Move the device to the fully extended (horizontal) position.\n"
                                      "2. Ensure all joint angles are roughly 0.\n"
                                      "3. Press the physical button on the MARS device to confirm.\n\n"
                                      "Click OK to begin.")
                # Disconnect if previously connected
                try:
                    self.mars.btnreleased.disconnect(self._do_calibrate)
                except Exception:
                    pass
                self.mars.btnreleased.connect(self._do_calibrate)
                print("Waiting for physical button press to calibrate...")
            except Exception as e:
                print(f"Error preparing calibration: {e}")

    def _do_calibrate(self):
        """Helper to send calibration command when physical button is pressed."""
        if self.mars and self.mars.is_connected():
            try:
                self.mars.calibrate()
                print("Calibration command sent via physical button press.")
                try:
                    self.mars.btnreleased.disconnect(self._do_calibrate)
                except Exception:
                    pass
                QTimer.singleShot(500, self._check_calibration_success)
            except Exception as e:
                print(f"Error sending calibration command: {e}")

    def _check_calibration_success(self):
        """Check if calibration was successful."""
        if self.mars and self.mars.is_connected():
            if getattr(self.mars, 'calibration', 0) == 1:
                QMessageBox.information(self, "Calibration Complete", "Device successfully calibrated.")
            else:
                QMessageBox.warning(self, "Calibration Pending", 
                                  "Device not calibrated yet. Please ensure device is still and angles are close to 0.")

    def on_slider_value_changed(self, value):
        """Update position target display when slider changes."""
        # Slider goes from 0 to 100, but we display 0 to -100
        display_value = -value
        self.pos_target_label.setText(str(display_value))

    def on_set_target(self):
        """Handle set target button click."""
        if self.mars and self.mars.is_connected():
            try:
                # Ensure device is calibrated before setting position mode
                if getattr(self.mars, 'calibration', 0) == 0:
                    print("Warning: Please calibrate the device first.")
                    return
                    
                slider_value = self.pos_target_slider.value()
                target_value = -slider_value  # Convert to negative range
                
                self._plane_setup_attempts = 0
                self._plane_target_value = target_value
                self._plane_timer = QTimer()
                self._plane_timer.timeout.connect(self._plane_setup_step)
                self._plane_timer.start(100) # Check every 100ms
            except Exception as e:
                print(f"Error setting target: {e}")

    def _plane_setup_step(self):
        """Helper method to set target value after confirming control type."""
        if not self.mars or not self.mars.is_connected():
            self._plane_timer.stop()
            return
            
        try:
            if self.mars.controltype != 1: # 1 is POSITION mode
                self.mars.set_control_type("POSITION")
                self._plane_setup_attempts += 1
                if self._plane_setup_attempts > 20: # 2 seconds timeout
                    self._plane_timer.stop()
                    print("Failed to set POSITION mode. Ensure device is properly calibrated.")
                return
                
            self.mars.set_control_target(self._plane_target_value)
            print(f"Position control enabled, target set to: {self._plane_target_value}")
            self._plane_timer.stop()
        except Exception as e:
            print(f"Error setting control target: {e}")
            self._plane_timer.stop()

    def update_display(self):
        if not self.mars:
            return

        try:
            # Update angles
            for i in range(1, 5):
                angle = getattr(self.mars, f"angle{i}", 0.0)
                self.value_labels[f"angle{i}"].setText(f"{angle:.2f}")

                imu_angle = getattr(self.mars, f"imu_angle{i}", 0.0)
                self.value_labels[f"imu_angle{i}"].setText(f"{imu_angle:.2f}")

            # Update control parameters
            for param in ["force", "target", "desired", "control"]:
                value = getattr(self.mars, param, 0.0)
                self.value_labels[param].setText(f"{value:.2f}")

            # Update error terms
            for param in ["err_p", "err_d", "err_i"]:
                value = getattr(self.mars, param, 0.0)
                self.value_labels[param].setText(f"{value:.2f}")

            # Update status
            self.value_labels["status"].setText(str(self.mars.status))
            self.value_labels["datatype"].setText(str(self.mars.datatype))
            self.value_labels["controltype"].setText(str(self.mars.controltype))
            self.value_labels["limb"].setText(str(self.mars.limb))
            self.value_labels["error"].setText(str(self.mars.error))
            self.value_labels["packet_number"].setText(str(self.mars.packet_number))
            self.value_labels["runtime"].setText(f"{self.mars.runtime:.2f}")
            self.value_labels["framerate"].setText(f"{self.mars.framerate:.1f}")

            # Update endpoint position
            ep_x, ep_y, ep_z = self.mars.ep_pos
            self.value_labels["ep_x"].setText(f"{ep_x:.4f}")
            self.value_labels["ep_y"].setText(f"{ep_y:.4f}")
            self.value_labels["ep_z"].setText(f"{ep_z:.4f}")

            # Update error status
            error_code = self.mars.error
            error_string = getattr(self.mars, 'error_string', 'Unknown')
            self.error_code_label.setText(str(error_code))
            if error_code == 0:
                self.error_desc_label.setText("No Error")
                self.error_desc_label.setStyleSheet("color: #00ff00;")
            else:
                self.error_desc_label.setText(str(error_string))
                self.error_desc_label.setStyleSheet("color: #ff0000;")

        except Exception as e:
            print(f"Error updating display: {e}")

    def closeEvent(self, event):
        self.disconnect_device()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MarsDisplayWindow()
    window.show()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nExiting...")
        window.disconnect_device()
        sys.exit(0)


if __name__ == "__main__":
    main()
