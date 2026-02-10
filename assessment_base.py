"""
Base class for MARS workspace assessments (AP, ML, MLAP).

Provides shared functionality for trajectory visualization, state management,
and boundary adjustment.

Author: Sivakumar Balasubramanian
Date: 09 February 2026
Email: siva82kb@gmail.com
"""

from enum import Enum
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QPushButton, QLabel)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
import marsdefs as mdef
from mars_arom_data import MarsArom


class AromAssessState(Enum):
    """Assessment state machine states."""
    INIT = 0
    ASSESSROM = 1
    ADJUST = 2
    DONE = 3


class AromAdjustState(Enum):
    """Boundary adjustment states."""
    NONE = 0
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4


class WorkspaceAssessmentCanvas(QWidget):
    """Canvas widget for visualizing AROM trajectory and boundaries."""

    # Scale factors (meters to pixels)
    SCALE_X = 10.0  # Matches Unity implementation
    SCALE_Y = 10.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 800)
        self.setMaximumSize(800, 800)

        # Data to visualize
        self.current_pos = None  # (y, z) in meters
        self.trajectory = []  # List of (y, z) points in meters
        self.current_arom = None  # MarsArom instance
        self.previous_arom = None  # MarsArom instance
        self.limb_type = "RIGHT"  # Affects coordinate transformation

        # UI state
        self.state = AromAssessState.INIT
        self.adjust_state = AromAdjustState.NONE
        self.instruction_text = "Press robot button to begin"

    def robot_to_screen(self, y: float, z: float) -> tuple:
        """Convert robot coordinates (meters) to screen coordinates (pixels).

        Args:
            y: Y coordinate (anterior-posterior) in meters
            z: Z coordinate (medio-lateral) in meters

        Returns:
            (x_screen, y_screen) tuple in pixels
        """
        # Workspace ranges (matching Unity's MarsDefs)
        z_min = mdef.WORKSPACE_Z_MIN
        z_max = mdef.WORKSPACE_Z_MAX
        y_min = mdef.WORKSPACE_Y_MIN
        y_max = mdef.WORKSPACE_Y_MAX
        z_center = mdef.WORKSPACE_Z_CENTER
        y_center = mdef.WORKSPACE_Y_CENTER

        # Normalize coordinates (Unity approach) - ranges from -0.5 to 0.5 approximately
        z_normalized = (z - z_center) / (z_max - z_min)
        y_normalized = (y - y_center) / (y_max - y_min)

        # Apply Unity scale factor (10.0)
        unity_x = z_normalized * self.SCALE_X
        unity_y = y_normalized * self.SCALE_Y

        # Convert Unity units to screen pixels
        # Canvas is 800x800, center at 400,400
        # Unity range of ~-5 to +5 should map to screen pixels
        # Using 60 pixels per Unity unit (10 units * 60 = 600 pixels for workspace)
        pixels_per_unity_unit = 60.0

        # Apply scale and flip for left limb
        if self.limb_type == "LEFT":
            x_screen = 400 - unity_x * pixels_per_unity_unit
        else:
            x_screen = 400 + unity_x * pixels_per_unity_unit

        y_screen = 400 - unity_y * pixels_per_unity_unit  # Flip Y (screen coords go down)

        return (int(x_screen), int(y_screen))

    def screen_to_robot(self, x_screen: int, y_screen: int) -> tuple:
        """Convert screen coordinates (pixels) to robot coordinates (meters).

        Args:
            x_screen: X coordinate in pixels
            y_screen: Y coordinate in pixels

        Returns:
            (y, z) tuple in meters
        """
        # Workspace ranges
        z_min = mdef.WORKSPACE_Z_MIN
        z_max = mdef.WORKSPACE_Z_MAX
        y_min = mdef.WORKSPACE_Y_MIN
        y_max = mdef.WORKSPACE_Y_MAX
        z_center = mdef.WORKSPACE_Z_CENTER
        y_center = mdef.WORKSPACE_Y_CENTER

        pixels_per_unity_unit = 60.0

        # Convert screen pixels to Unity units
        unity_y = -(y_screen - 400) / pixels_per_unity_unit

        if self.limb_type == "LEFT":
            unity_x = -(x_screen - 400) / pixels_per_unity_unit
        else:
            unity_x = (x_screen - 400) / pixels_per_unity_unit

        # Convert Unity units to normalized coordinates
        z_normalized = unity_x / self.SCALE_X
        y_normalized = unity_y / self.SCALE_Y

        # Denormalize to robot coordinates
        z = z_center + z_normalized * (z_max - z_min)
        y = y_center + y_normalized * (y_max - y_min)

        return (y, z)

    def paintEvent(self, event):
        """Paint canvas layers."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        # Grid (5cm intervals)
        self._draw_grid(painter)

        # Axes
        self._draw_axes(painter)

        # Previous AROM (light blue, semi-transparent)
        if self.previous_arom is not None:
            self._draw_arom_box(painter, self.previous_arom, QColor(100, 150, 255, 100))

        # Trajectory (gray line)
        if len(self.trajectory) > 1:
            self._draw_trajectory(painter)

        # Current AROM (red with handles)
        if self.current_arom is not None and self.state == AromAssessState.ADJUST:
            self._draw_arom_box(painter, self.current_arom, QColor(255, 50, 50, 200), True)

        # Current position cursor (green circle)
        if self.current_pos is not None:
            self._draw_cursor(painter)

        # Instruction text (top-left)
        self._draw_instruction_text(painter)

        # Range measurements (top-right)
        if self.current_arom is not None and self.state == AromAssessState.ADJUST:
            self._draw_range_text(painter)

    def _draw_grid(self, painter):
        """Draw background grid with 5cm intervals."""
        painter.setPen(QPen(QColor(220, 220, 220), 1))

        # Vertical lines every 50 pixels (5cm)
        for x in range(0, 801, 50):
            painter.drawLine(x, 0, x, 800)

        # Horizontal lines every 50 pixels (5cm)
        for y in range(0, 801, 50):
            painter.drawLine(0, y, 800, y)

    def _draw_axes(self, painter):
        """Draw centered axes."""
        painter.setPen(QPen(QColor(150, 150, 150), 2))

        # Vertical center line
        painter.drawLine(400, 0, 400, 800)

        # Horizontal center line
        painter.drawLine(0, 400, 800, 400)

    def _draw_trajectory(self, painter):
        """Draw trajectory line."""
        painter.setPen(QPen(QColor(100, 100, 100), 3))

        for i in range(len(self.trajectory) - 1):
            p1 = self.robot_to_screen(self.trajectory[i][0], self.trajectory[i][1])
            p2 = self.robot_to_screen(self.trajectory[i + 1][0], self.trajectory[i + 1][1])
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

    def _draw_arom_box(self, painter, arom: MarsArom, color: QColor, with_handles: bool = False):
        """Draw AROM boundary box.

        Args:
            painter: QPainter instance
            arom: MarsArom data
            color: Box color
            with_handles: Whether to draw adjustment handles
        """
        if arom.adjusted_top is None or arom.adjusted_bottom is None:
            return
        if arom.adjusted_left is None or arom.adjusted_right is None:
            return

        painter.setPen(QPen(color, 2))

        # Get screen coordinates for corners
        top_left = self.robot_to_screen(arom.adjusted_top[0], arom.adjusted_left[1])
        top_right = self.robot_to_screen(arom.adjusted_top[0], arom.adjusted_right[1])
        bottom_left = self.robot_to_screen(arom.adjusted_bottom[0], arom.adjusted_left[1])
        bottom_right = self.robot_to_screen(arom.adjusted_bottom[0], arom.adjusted_right[1])

        # Draw box
        painter.drawLine(top_left[0], top_left[1], top_right[0], top_right[1])  # Top
        painter.drawLine(bottom_left[0], bottom_left[1], bottom_right[0], bottom_right[1])  # Bottom
        painter.drawLine(top_left[0], top_left[1], bottom_left[0], bottom_left[1])  # Left
        painter.drawLine(top_right[0], top_right[1], bottom_right[0], bottom_right[1])  # Right

        # Draw handles if requested
        if with_handles:
            handle_size = 10
            painter.setBrush(QBrush(color))

            # Top handle
            top_center = ((top_left[0] + top_right[0]) // 2, top_left[1])
            painter.drawEllipse(top_center[0] - handle_size // 2,
                              top_center[1] - handle_size // 2,
                              handle_size, handle_size)

            # Bottom handle
            bottom_center = ((bottom_left[0] + bottom_right[0]) // 2, bottom_left[1])
            painter.drawEllipse(bottom_center[0] - handle_size // 2,
                              bottom_center[1] - handle_size // 2,
                              handle_size, handle_size)

            # Left handle
            left_center = (top_left[0], (top_left[1] + bottom_left[1]) // 2)
            painter.drawEllipse(left_center[0] - handle_size // 2,
                              left_center[1] - handle_size // 2,
                              handle_size, handle_size)

            # Right handle
            right_center = (top_right[0], (top_right[1] + bottom_right[1]) // 2)
            painter.drawEllipse(right_center[0] - handle_size // 2,
                              right_center[1] - handle_size // 2,
                              handle_size, handle_size)

    def _draw_cursor(self, painter):
        """Draw current position cursor."""
        if self.current_pos is None:
            return

        screen_pos = self.robot_to_screen(self.current_pos[0], self.current_pos[1])

        painter.setPen(QPen(QColor(0, 200, 0), 2))
        painter.setBrush(QBrush(QColor(0, 200, 0, 100)))
        painter.drawEllipse(screen_pos[0] - 8, screen_pos[1] - 8, 16, 16)

    def _draw_instruction_text(self, painter):
        """Draw instruction text overlay."""
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(10, 30, self.instruction_text)

    def _draw_range_text(self, painter):
        """Draw range measurements."""
        if self.current_arom is None:
            return

        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setFont(QFont("Arial", 11, QFont.Bold))

        ml_range = self.current_arom.ml_range_cm
        ap_range = self.current_arom.ap_range_cm

        text = f"ML: {ml_range:.2f} cm, AP: {ap_range:.2f} cm"
        painter.drawText(550, 30, text)


class BaseAssessmentWindow(QMainWindow):
    """Base class for workspace assessment windows."""

    def __init__(self, mars, parent=None):
        super().__init__(parent)
        self.mars = mars
        self.state = AromAssessState.INIT
        self.adjust_state = AromAdjustState.NONE

        # Data
        self.current_arom = None
        self.previous_arom = None
        self.trajectory_points = []
        self.last_recorded_pos = None

        # Set as modal to block main window
        self.setWindowModality(Qt.ApplicationModal)

        # UI
        self.canvas = WorkspaceAssessmentCanvas(self)
        self.init_ui()

        # Connect signals
        self.connect_signals()

        # Load previous assessment if exists
        self.load_previous_assessment()

        # Update timer for canvas refresh
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_canvas)
        self.update_timer.start(33)  # ~30 FPS

    @property
    def movement_type(self) -> str:
        """Override in subclasses to specify assessment type."""
        raise NotImplementedError("Subclasses must define movement_type")

    def init_ui(self):
        """Create window layout."""
        self.setWindowTitle(f"MARS Workspace Assessment - {self.movement_type}")
        self.setFixedSize(850, 900)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Canvas
        layout.addWidget(self.canvas, alignment=Qt.AlignCenter)

        # Button panel
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Assessment")
        self.start_btn.clicked.connect(self.on_start_assessment)
        self.start_btn.setVisible(False)  # Hidden - use robot button instead
        button_layout.addWidget(self.start_btn)

        self.recalibrate_btn = QPushButton("Recalibrate")
        self.recalibrate_btn.clicked.connect(self.on_recalibrate)
        self.recalibrate_btn.setVisible(False)
        button_layout.addWidget(self.recalibrate_btn)

        self.save_btn = QPushButton("Save & Close")
        self.save_btn.clicked.connect(self.save_assessment)
        self.save_btn.setVisible(False)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        # Apply modern styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)

    def connect_signals(self):
        """Connect to MARS device signals."""
        if self.mars is not None:
            print(f"[Signal] Connecting signals for {self.movement_type} assessment")
            self.mars.newdata.connect(self.handle_new_data)
            self.mars.btnreleased.connect(self.handle_button_release)
            print(f"[Signal] Connected: newdata and btnreleased")

    def disconnect_signals(self):
        """Disconnect from MARS device signals."""
        if self.mars is not None:
            try:
                self.mars.newdata.disconnect(self.handle_new_data)
                self.mars.btnreleased.disconnect(self.handle_button_release)
            except:
                pass

    def load_previous_assessment(self):
        """Load most recent assessment of this type."""
        self.previous_arom = MarsArom.find_latest_assessment(self.movement_type)
        self.canvas.previous_arom = self.previous_arom

    def on_start_assessment(self):
        """Start assessment - transition INIT -> ASSESSROM."""
        if self.state != AromAssessState.INIT:
            return

        # Create new AROM instance
        self.current_arom = MarsArom(self.movement_type)
        self.current_arom.start_assessment()
        self.canvas.current_arom = self.current_arom

        # Clear trajectory
        self.trajectory_points = []
        self.canvas.trajectory = []
        self.last_recorded_pos = None

        # Update state
        self.state = AromAssessState.ASSESSROM
        self.canvas.state = self.state
        self.canvas.instruction_text = "Move through your range. Press device button when done."

        # Update buttons
        self.start_btn.setVisible(False)

        print(f"Started {self.movement_type} assessment")

    def stop_assessment(self):
        """Stop assessment - transition ASSESSROM -> ADJUST."""
        if self.state != AromAssessState.ASSESSROM:
            return

        # Stop recording
        self.current_arom.stop_assessment()

        # Update state
        self.state = AromAssessState.ADJUST
        self.canvas.state = self.state
        self.canvas.instruction_text = "Adjust boundaries with L/R/T/B keys + mouse. Click 'Save & Close' when done."

        # Update buttons
        self.recalibrate_btn.setVisible(True)
        self.save_btn.setVisible(True)

        print(f"Stopped {self.movement_type} assessment - computed corners")

    def handle_new_data(self):
        """Handle new data from MARS device."""
        if self.mars is None:
            return

        # Get current endpoint position (ep_pos_in_plane returns (x, y, z))
        _, y, z = self.mars.ep_pos_in_plane

        # Update canvas current position
        self.canvas.current_pos = (y, z)

        # Debug: Print position periodically (every 30 frames = ~1 second)
        if not hasattr(self, '_debug_counter'):
            self._debug_counter = 0
        self._debug_counter += 1
        if self._debug_counter % 30 == 0:
            screen_pos = self.canvas.robot_to_screen(y, z)
            print(f"Robot pos: ({y:.3f}, {z:.3f}) → Screen pos: {screen_pos}")

        # If in ASSESSROM state, add to trajectory
        if self.state == AromAssessState.ASSESSROM:
            # Check distance threshold
            if self.last_recorded_pos is None:
                should_add = True
            else:
                dy = y - self.last_recorded_pos[0]
                dz = z - self.last_recorded_pos[1]
                dist = (dy**2 + dz**2)**0.5
                should_add = dist >= mdef.AROM_DIST_THRESHOLD

            if should_add:
                self.current_arom.add_data_point(y, z)
                self.trajectory_points.append([y, z])
                self.canvas.trajectory = self.trajectory_points
                self.last_recorded_pos = (y, z)

    def handle_button_release(self):
        """Handle device button release - triggers state transitions.

        Based on Unity MarsAssessAROM.cs OnMarsButtonReleased():
        - INIT state: Start assessment (INIT → ASSESSROM)
        - ASSESSROM state: Stop assessment (ASSESSROM → ADJUST)
        """
        print(f"[Button] Device button released in state: {self.state}")

        if self.state == AromAssessState.INIT:
            # Start assessment automatically (like Unity allows)
            print("[Button] Starting assessment from button press")
            self.on_start_assessment()

        elif self.state == AromAssessState.ASSESSROM:
            # Stop assessment and move to adjust mode
            print("[Button] Stopping assessment from button press")
            self.stop_assessment()

        else:
            print(f"[Button] No action for state: {self.state}")

    def update_canvas(self):
        """Periodic canvas update."""
        self.canvas.update()

    def on_recalibrate(self):
        """Reset to INIT state for new assessment."""
        self.state = AromAssessState.INIT
        self.canvas.state = self.state
        self.canvas.instruction_text = "Press robot button to begin"

        # Clear current data
        self.current_arom = None
        self.canvas.current_arom = None
        self.trajectory_points = []
        self.canvas.trajectory = []

        # Update buttons
        self.start_btn.setVisible(True)
        self.recalibrate_btn.setVisible(False)
        self.save_btn.setVisible(False)

    def save_assessment(self):
        """Save assessment and close window."""
        if self.current_arom is None:
            return

        # Save to CSV
        filepath = self.current_arom.save_to_csv()
        print(f"Saved assessment to: {filepath}")

        # Update state
        self.state = AromAssessState.DONE

        # Close window
        self.close()

    def keyPressEvent(self, event):
        """Handle keyboard input for boundary adjustment."""
        if self.state != AromAssessState.ADJUST:
            return

        key = event.key()

        if key == Qt.Key_L:
            self.adjust_state = AromAdjustState.LEFT
            self.canvas.adjust_state = self.adjust_state
            self.canvas.instruction_text = "Adjusting LEFT boundary - drag with mouse"
        elif key == Qt.Key_R:
            self.adjust_state = AromAdjustState.RIGHT
            self.canvas.adjust_state = self.adjust_state
            self.canvas.instruction_text = "Adjusting RIGHT boundary - drag with mouse"
        elif key == Qt.Key_T:
            self.adjust_state = AromAdjustState.TOP
            self.canvas.adjust_state = self.adjust_state
            self.canvas.instruction_text = "Adjusting TOP boundary - drag with mouse"
        elif key == Qt.Key_B:
            self.adjust_state = AromAdjustState.BOTTOM
            self.canvas.adjust_state = self.adjust_state
            self.canvas.instruction_text = "Adjusting BOTTOM boundary - drag with mouse"
        elif key == Qt.Key_Escape:
            self.adjust_state = AromAdjustState.NONE
            self.canvas.adjust_state = self.adjust_state
            self.canvas.instruction_text = "Adjust boundaries with L/R/T/B keys + mouse. Click 'Save & Close' when done."

    def mousePressEvent(self, event):
        """Handle mouse press for boundary adjustment."""
        if self.state != AromAssessState.ADJUST or self.adjust_state == AromAdjustState.NONE:
            return

        # Get mouse position relative to canvas
        canvas_pos = self.canvas.mapFromGlobal(event.globalPos())
        robot_coords = self.canvas.screen_to_robot(canvas_pos.x(), canvas_pos.y())

        # Update appropriate boundary
        self._update_boundary(robot_coords)

    def mouseMoveEvent(self, event):
        """Handle mouse move for boundary adjustment."""
        if self.state != AromAssessState.ADJUST or self.adjust_state == AromAdjustState.NONE:
            return

        if event.buttons() & Qt.LeftButton:
            canvas_pos = self.canvas.mapFromGlobal(event.globalPos())
            robot_coords = self.canvas.screen_to_robot(canvas_pos.x(), canvas_pos.y())
            self._update_boundary(robot_coords)

    def _update_boundary(self, robot_coords):
        """Update boundary based on adjust state."""
        y, z = robot_coords

        if self.adjust_state == AromAdjustState.TOP:
            self.current_arom.adjusted_top = (y, self.current_arom.adjusted_top[1])
        elif self.adjust_state == AromAdjustState.BOTTOM:
            self.current_arom.adjusted_bottom = (y, self.current_arom.adjusted_bottom[1])
        elif self.adjust_state == AromAdjustState.LEFT:
            self.current_arom.adjusted_left = (self.current_arom.adjusted_left[0], z)
        elif self.adjust_state == AromAdjustState.RIGHT:
            self.current_arom.adjusted_right = (self.current_arom.adjusted_right[0], z)

    def closeEvent(self, event):
        """Clean disconnect from signals when closing."""
        self.disconnect_signals()
        self.update_timer.stop()
        event.accept()
