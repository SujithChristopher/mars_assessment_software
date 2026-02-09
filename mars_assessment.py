import sys
import math
from typing import List, Tuple
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QGroupBox, QFrame, QSizePolicy, QComboBox)
from PySide6.QtCore import Qt, QTimer, QPointF, Signal, Slot
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush

from qtmars import QtMars
import marsdefs as mdef

class WorkspaceCanvas(QWidget):
    """
    A custom widget to draw the robot's movement path in 2D.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.path: List[QPointF] = []
        self.current_pos: QPointF = QPointF(0, 0)
        self.scale = 500.0  # Pixels per meter
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.setMinimumSize(600, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Appearance constants
        self.bg_color = QColor("#001a00")
        self.grid_color = QColor("#003300")
        self.path_color = QColor("#00ff00")
        self.cursor_color = QColor("#ffffff")
        self.text_color = QColor("#00ff00")

    def clear_path(self):
        self.path = []
        self.update()

    def update_position(self, y: float, z: float, tracking: bool):
        # Robot y, z in meters
        # We want to map this to widget coordinates
        self.current_pos = QPointF(y, z)
        if tracking:
            self.path.append(self.current_pos)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Center of the widget
        cx = self.width() / 2
        cy = self.height() / 2
        
        # Apply transformation: center is (0,0) in meters
        # Robot coordinates: Y is right, Z is up (positive Z is up, but screen Y is down)
        # So Screen X = cx + y * scale
        # Screen Y = cy - z * scale
        
        self.draw_grid(painter, cx, cy)
        self.draw_path(painter, cx, cy)
        self.draw_cursor(painter, cx, cy)
        self.draw_status(painter)

    def draw_grid(self, painter, cx, cy):
        painter.setPen(QPen(self.grid_color, 1, Qt.DotLine))
        
        # 10cm grid lines
        step = 0.1 * self.scale
        
        # Vertical lines
        x = cx % step
        while x < self.width():
            painter.drawLine(x, 0, x, self.height())
            x += step
            
        # Horizontal lines
        y = cy % step
        while y < self.height():
            painter.drawLine(0, y, self.width(), y)
            y += step
            
        # Main Axes
        painter.setPen(QPen(QColor("#005500"), 2))
        painter.drawLine(cx, 0, cx, self.height())
        painter.drawLine(0, cy, self.width(), cy)

    def draw_path(self, painter, cx, cy):
        if len(self.path) < 2:
            return
            
        painter.setPen(QPen(self.path_color, 2))
        
        for i in range(len(self.path) - 1):
            p1 = self.path[i]
            p2 = self.path[i+1]
            
            x1 = cx + p1.x() * self.scale
            y1 = cy - p1.y() * self.scale
            x2 = cx + p2.x() * self.scale
            y2 = cy - p2.y() * self.scale
            
            painter.drawLine(x1, y1, x2, y2)

    def draw_cursor(self, painter, cx, cy):
        painter.setPen(QPen(self.cursor_color, 2))
        painter.setBrush(QBrush(self.cursor_color))
        
        px = cx + self.current_pos.x() * self.scale
        py = cy - self.current_pos.y() * self.scale
        
        painter.drawEllipse(QPointF(px, py), 5, 5)
        
        # Draw crosshair
        painter.drawLine(px - 10, py, px + 10, py)
        painter.drawLine(px, py - 10, px, py + 10)

    def draw_status(self, painter):
        painter.setPen(self.text_color)
        painter.setFont(QFont("Courier New", 10, QFont.Bold))
        status_text = f"Y: {self.current_pos.x():.4f}m, Z: {self.current_pos.y():.4f}m"
        painter.drawText(10, 20, status_text)
        painter.drawText(10, 40, f"Scale: {self.scale} px/m")

class MarsAssessmentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mars = None
        self.is_tracking = False
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("MARS Workspace Assessment")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #001a00;
                color: #00ff00;
                font-family: 'Courier New', monospace;
            }
            QPushButton {
                background-color: #004400;
                border: 2px solid #00aa00;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #006600;
            }
            QPushButton:checked {
                background-color: #00aa00;
                color: #000000;
            }
            QLineEdit {
                background-color: #003300;
                border: 1px solid #00aa00;
                padding: 2px;
            }
            QGroupBox {
                border: 2px solid #00aa00;
                margin-top: 10px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Side: Canvas
        self.canvas = WorkspaceCanvas()
        main_layout.addWidget(self.canvas, 1)

        # Right Side: Controls
        control_panel = QWidget()
        control_panel.setFixedWidth(250)
        control_layout = QVBoxLayout(control_panel)
        main_layout.addWidget(control_panel)

        # Connection Group
        conn_group = QGroupBox("Connection")
        conn_vbox = QVBoxLayout(conn_group)
        
        port_hbox = QHBoxLayout()
        port_hbox.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("COM4")
        port_hbox.addWidget(self.port_input)
        conn_vbox.addLayout(port_hbox)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_vbox.addWidget(self.connect_btn)
        
        control_layout.addWidget(conn_group)

        # Device Configuration Group
        config_group = QGroupBox("Configuration")
        config_vbox = QVBoxLayout(config_group)

        limb_hbox = QHBoxLayout()
        limb_hbox.addWidget(QLabel("Limb:"))
        self.limb_combo = QComboBox()
        self.limb_combo.addItems(["LEFT", "RIGHT"])
        self.limb_combo.currentTextChanged.connect(self.on_limb_changed)
        limb_hbox.addWidget(self.limb_combo)
        config_vbox.addLayout(limb_hbox)

        self.calibrate_btn = QPushButton("Calibrate")
        self.calibrate_btn.clicked.connect(self.on_calibrate)
        config_vbox.addWidget(self.calibrate_btn)

        self.set_plane_btn = QPushButton("Set Plane (90°)")
        self.set_plane_btn.clicked.connect(self.on_set_plane)
        config_vbox.addWidget(self.set_plane_btn)

        control_layout.addWidget(config_group)

        # Movement Tracking Group
        track_group = QGroupBox("Workspace Assessment")
        track_vbox = QVBoxLayout(track_group)
        
        self.track_btn = QPushButton("Start Tracking")
        self.track_btn.setCheckable(True)
        self.track_btn.toggled.connect(self.toggle_tracking)
        track_vbox.addWidget(self.track_btn)
        
        self.clear_btn = QPushButton("Clear Path")
        self.clear_btn.clicked.connect(self.canvas.clear_path)
        track_vbox.addWidget(self.clear_btn)
        
        control_layout.addWidget(track_group)

        # View Settings
        view_group = QGroupBox("View Settings")
        view_vbox = QVBoxLayout(view_group)
        
        scale_hbox = QHBoxLayout()
        scale_hbox.addWidget(QLabel("Scale:"))
        self.scale_input = QLineEdit("500")
        self.scale_input.returnPressed.connect(self.update_scale)
        scale_hbox.addWidget(self.scale_input)
        view_vbox.addLayout(scale_hbox)
        
        control_layout.addWidget(view_group)
        
        # Simulation Group
        sim_group = QGroupBox("Simulation")
        sim_vbox = QVBoxLayout(sim_group)
        
        self.sim_btn = QPushButton("Start Simulation")
        self.sim_btn.setCheckable(True)
        self.sim_btn.toggled.connect(self.toggle_simulation)
        sim_vbox.addWidget(self.sim_btn)
        
        control_layout.addWidget(sim_group)
        
        control_layout.addStretch()

        # Simulation Timer
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.simulate_movement)
        self.sim_angle = 0.0

    def toggle_simulation(self, checked):
        if checked:
            if self.mars:
                self.disconnect_device()
            self.sim_timer.start(50)
            self.sim_btn.setText("Stop Simulation")
            self.connect_btn.setEnabled(False)
        else:
            self.sim_timer.stop()
            self.sim_btn.setText("Start Simulation")
            self.connect_btn.setEnabled(True)

    def simulate_movement(self):
        # Generate some circular movement for testing
        self.sim_angle += 0.05
        ry = 0.3 + 0.1 * math.cos(self.sim_angle)
        rz = -0.3 + 0.1 * math.sin(self.sim_angle)
        self.canvas.update_position(ry, rz, self.is_tracking)

    def toggle_connection(self):
        if self.mars is None:
            port = self.port_input.text()
            try:
                self.mars = QtMars(port=port, baudrate=115200, auto_heartbeat=False)
                if not self.mars.is_connected():
                    self.mars = None
                    return
                
                self.mars.newdata.connect(self.update_robot_data)
                
                # Connection sequence
                self.mars.get_version()
                self.mars.start_sensorstream()
                self.mars.set_diagnostic_mode()
                self.mars.send_heartbeat()
                
                self.heartbeat_timer.start(3000)
                
                self.connect_btn.setText("Disconnect")
                self.port_input.setEnabled(False)
            except Exception as e:
                print(f"Connection failed: {e}")
                self.mars = None
        else:
            self.disconnect_device()

    def disconnect_device(self):
        if self.mars:
            self.heartbeat_timer.stop()
            self.mars.stop_sensorstream()
            self.mars.close()
            self.mars = None
            self.connect_btn.setText("Connect")
            self.port_input.setEnabled(True)

    def send_heartbeat(self):
        if self.mars and self.mars.is_connected():
            self.mars.send_heartbeat()

    def toggle_tracking(self, checked):
        self.is_tracking = checked
        if checked:
            self.track_btn.setText("Stop Tracking")
        else:
            self.track_btn.setText("Start Tracking")

    def update_scale(self):
        try:
            val = float(self.scale_input.text())
            if val > 0:
                self.canvas.scale = val
                self.canvas.update()
        except ValueError:
            pass

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
                self.mars.calibrate()
                print("Calibration command sent")
            except Exception as e:
                print(f"Error during calibration: {e}")

    def on_set_plane(self):
        """Handle set plane button click - sets robot to 90 degrees."""
        if self.mars and self.mars.is_connected():
            try:
                # Set control type to POSITION
                self.mars.set_control_type("POSITION")
                # Delay before setting target to allow device to process control type change
                QTimer.singleShot(200, lambda: self._set_plane_target())
                print("Position control enabled, setting plane to 90 degrees")
            except Exception as e:
                print(f"Error setting plane: {e}")

    def _set_plane_target(self):
        """Helper method to set plane target value after delay."""
        if self.mars and self.mars.is_connected():
            try:
                self.mars.set_control_target(90.0)
            except Exception as e:
                print(f"Error setting plane target: {e}")

    @Slot()
    def update_robot_data(self):
        if not self.mars:
            return
            
        # Get position in plane (x=0, y, z)
        # Note: qtmars.ep_pos_in_plane returns (x, y, z)
        # Based on forward_kinematics_in_plane: x=0, y=temp, z=computed
        _, ry, rz = self.mars.ep_pos_in_plane
        
        # In our canvas, we map ry to horizontal and rz to vertical
        self.canvas.update_position(ry, rz, self.is_tracking)

    def closeEvent(self, event):
        self.disconnect_device()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MarsAssessmentWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
