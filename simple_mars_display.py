import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QGridLayout, QPushButton,
                               QLineEdit, QGroupBox)
from PySide6.QtCore import Qt
from qtmars import QtMars


class MarsDisplayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mars = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("MARS Sensor Data Display")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Connection controls
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("COM Port:"))
        self.port_input = QLineEdit("COM4")
        self.port_input.setMaximumWidth(100)
        conn_layout.addWidget(self.port_input)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn)

        self.start_stream_btn = QPushButton("Start Stream")
        self.start_stream_btn.clicked.connect(self.start_stream)
        self.start_stream_btn.setEnabled(False)
        conn_layout.addWidget(self.start_stream_btn)

        self.stop_stream_btn = QPushButton("Stop Stream")
        self.stop_stream_btn.clicked.connect(self.stop_stream)
        self.stop_stream_btn.setEnabled(False)
        conn_layout.addWidget(self.stop_stream_btn)

        conn_layout.addStretch()
        main_layout.addLayout(conn_layout)

        # Data display
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

        main_layout.addWidget(data_widget)

    def toggle_connection(self):
        if self.mars is None:
            port = self.port_input.text()
            try:
                self.mars = QtMars(port=port, baudrate=115200)
                self.mars.newdata.connect(self.update_display)

                self.connect_btn.setText("Disconnect")
                self.start_stream_btn.setEnabled(True)
                self.port_input.setEnabled(False)

                print(f"Connected to {port}")
            except Exception as e:
                print(f"Connection failed: {e}")
                self.mars = None
        else:
            self.disconnect_device()

    def disconnect_device(self):
        if self.mars:
            try:
                self.stop_stream()
                if hasattr(self.mars, 'dev') and self.mars.dev:
                    self.mars.dev.abort()
                    self.mars.dev.quit()
                    self.mars.dev.wait()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                self.mars = None
                self.connect_btn.setText("Connect")
                self.start_stream_btn.setEnabled(False)
                self.stop_stream_btn.setEnabled(False)
                self.port_input.setEnabled(True)
                for label in self.value_labels.values():
                    label.setText("--")
                print("Disconnected")

    def start_stream(self):
        if self.mars:
            try:
                self.mars.start_sensorstream()
                self.start_stream_btn.setEnabled(False)
                self.stop_stream_btn.setEnabled(True)
                print("Stream started")
            except Exception as e:
                print(f"Failed to start stream: {e}")

    def stop_stream(self):
        if self.mars:
            try:
                self.mars.stop_sensorstream()
                self.start_stream_btn.setEnabled(True)
                self.stop_stream_btn.setEnabled(False)
                print("Stream stopped")
            except Exception as e:
                print(f"Failed to stop stream: {e}")

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
