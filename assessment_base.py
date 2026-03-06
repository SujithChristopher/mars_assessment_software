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
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
import marsdefs as mdef
from mars_arom_data import MarsArom


class AromAssessState(Enum):
    """Assessment state machine states."""
    INIT = 0
    ASSESSROM = 1
    ADJUST = 2
    DONE = 3
    TRIAL_PAUSE = 4
    TRIAL_READY = 5


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

    def __init__(self, movement_type="MLAP", parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 800)
        self.setMaximumSize(800, 800)
        self.movement_type = movement_type  # AP, ML, or MLAP

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
        self.show_grid = False
        self.countdown_timer = None # None or int/float

        # Arm weight assessment state (imported when needed)
        self.arm_weight_targets = {}  # Dict of ArmWeightTarget -> (y, z) positions
        self.arm_weight_state = None  # ArmWeightState enum value
        self.current_arm_weight_target = None  # Currently active target
        self.completed_targets = set()  # Set of completed ArmWeightTarget values

        # Discrete reaching assessment state
        self.discrete_reach_targets = {} # Dict of DiscreteReachTarget -> (y, z) positions
        self.discrete_reach_state = None # DiscreteReachState enum value
        self.current_discrete_reach_target = None # Currently active target
        self.completed_discrete_targets = set() # Set of completed target values

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

        # Apply limb offset to unity coordinates (matches Unity C# OFFSET behavior)
        # TEST: Try inverting the offset logic
        if self.limb_type == "RIGHT":
            unity_x = -unity_x

        # Convert Unity units to screen pixels
        # Canvas is 800x800, center at 400,400
        # Unity range of ~-5 to +5 should map to screen pixels
        # Using 60 pixels per Unity unit (10 units * 60 = 600 pixels for workspace)
        pixels_per_unity_unit = 60.0

        # Apply same transformation for both limbs (flip handled above)
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
        unity_x = (x_screen - 400) / pixels_per_unity_unit
        unity_y = -(y_screen - 400) / pixels_per_unity_unit

        # Reverse the limb offset (matches forward transformation)
        if self.limb_type == "LEFT":
            unity_x = -unity_x

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
        if self.show_grid:
            self._draw_grid(painter)

        # Axes (Removed per request)
        # self._draw_axes(painter)

        # Previous AROM (Removed per request)
        # if self.previous_arom is not None:
        #     self._draw_arom_boundaries(painter, self.previous_arom, QColor(100, 150, 255, 100))

        # Trajectory (gray line) - only during AROM assessment
        if len(self.trajectory) > 1 and self.arm_weight_state is None:
            self._draw_trajectory(painter)

        # Current AROM boundaries
        if self.current_arom is not None:
            if self.state == AromAssessState.ADJUST:
                # Red with handles during adjustment
                self._draw_arom_boundaries(painter, self.current_arom, QColor(255, 50, 50, 200), True)
            elif self.state == AromAssessState.TRIAL_PAUSE:
                # Show both trial specifically and global max
                # Trial boundary in blue-ish
                self._draw_trial_boundaries(painter, self.current_arom, QColor(100, 150, 255, 150))
                # Global max in red
                self._draw_arom_boundaries(painter, self.current_arom, QColor(255, 50, 50, 100))
            elif self.arm_weight_state is not None:
                # Light gray reference for arm weight assessment
                self._draw_arom_boundaries(painter, self.current_arom, QColor(150, 150, 150, 150), False)

        # Arm weight targets (if active)
        if self.arm_weight_state is not None and len(self.arm_weight_targets) > 0:
            self._draw_arm_weight_targets(painter)

        # Current position cursor (green circle)
        if self.current_pos is not None:
            self._draw_cursor(painter)

        # Timer (if active)
        if self.countdown_timer is not None:
            self._draw_countdown_timer(painter)

        # Discrete reach targets (if active)
        if self.discrete_reach_state is not None and len(self.discrete_reach_targets) > 0:
            self._draw_discrete_reach_paths(painter)
            self._draw_discrete_reach_targets(painter)

        # Instruction text (top-left)
        self._draw_instruction_text(painter)

        # Range measurements (top-right) - only during AROM adjustment
        if self.current_arom is not None and self.state == AromAssessState.ADJUST and self.arm_weight_state is None:
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

    def _draw_arom_boundaries(self, painter, arom: MarsArom, color: QColor, with_handles: bool = False):
        """Draw AROM boundaries based on movement type.

        Args:
            painter: QPainter instance
            arom: MarsArom data
            color: Boundary color
            with_handles: Whether to draw adjustment handles
        """
        if self.movement_type == "AP":
            self._draw_ap_boundaries(painter, arom, color, with_handles)
        elif self.movement_type == "ML":
            self._draw_ml_boundaries(painter, arom, color, with_handles)
        else:  # MLAP
            self._draw_mlap_boundaries(painter, arom, color, with_handles)

    def _draw_ap_boundaries(self, painter, arom: MarsArom, color: QColor, with_handles: bool = False):
        """Draw AP boundaries as two horizontal lines.

        Args:
            painter: QPainter instance
            arom: MarsArom data
            color: Line color
            with_handles: Whether to draw adjustment handles
        """
        if arom.adjusted_top is None or arom.adjusted_bottom is None:
            return

        painter.setPen(QPen(color, 2))

        # Top line (max Y)
        top_y_screen = self.robot_to_screen(arom.adjusted_top[0], 0)[1]
        painter.drawLine(0, top_y_screen, 800, top_y_screen)

        # Bottom line (min Y)
        bottom_y_screen = self.robot_to_screen(arom.adjusted_bottom[0], 0)[1]
        painter.drawLine(0, bottom_y_screen, 800, bottom_y_screen)

        # Handles at center if requested
        if with_handles:
            handle_size = 10
            painter.setBrush(QBrush(color))
            painter.drawEllipse(395, top_y_screen - handle_size // 2, handle_size, handle_size)
            painter.drawEllipse(395, bottom_y_screen - handle_size // 2, handle_size, handle_size)

    def _draw_ml_boundaries(self, painter, arom: MarsArom, color: QColor, with_handles: bool = False):
        """Draw ML boundaries as two vertical lines.

        Args:
            painter: QPainter instance
            arom: MarsArom data
            color: Line color
            with_handles: Whether to draw adjustment handles
        """
        if arom.adjusted_left is None or arom.adjusted_right is None:
            return

        painter.setPen(QPen(color, 2))

        # Left line (min Z)
        left_x_screen = self.robot_to_screen(0, arom.adjusted_left[1])[0]
        painter.drawLine(left_x_screen, 0, left_x_screen, 800)

        # Right line (max Z)
        right_x_screen = self.robot_to_screen(0, arom.adjusted_right[1])[0]
        painter.drawLine(right_x_screen, 0, right_x_screen, 800)

        # Handles at center if requested
        if with_handles:
            handle_size = 10
            painter.setBrush(QBrush(color))
            painter.drawEllipse(left_x_screen - handle_size // 2, 395, handle_size, handle_size)
            painter.drawEllipse(right_x_screen - handle_size // 2, 395, handle_size, handle_size)

    def _draw_mlap_boundaries(self, painter, arom: MarsArom, color: QColor, with_handles: bool = False):
        """Draw MLAP boundaries as a true quadrilateral.

        Matches Unity implementation which connects the four actual extremal points:
        left → bottom → right → top → left (closing the shape)

        Args:
            painter: QPainter instance
            arom: MarsArom data
            color: Quadrilateral color
            with_handles: Whether to draw adjustment handles
        """
        if arom.adjusted_top is None or arom.adjusted_bottom is None:
            return
        if arom.adjusted_left is None or arom.adjusted_right is None:
            return

        painter.setPen(QPen(color, 2))

        # Get the four actual extremal points (as Unity does)
        # Each point is (y, z) in robot coords
        # robot_to_screen handles limb flipping automatically
        left_point = self.robot_to_screen(arom.adjusted_left[0], arom.adjusted_left[1])
        bottom_point = self.robot_to_screen(arom.adjusted_bottom[0], arom.adjusted_bottom[1])
        right_point = self.robot_to_screen(arom.adjusted_right[0], arom.adjusted_right[1])
        top_point = self.robot_to_screen(arom.adjusted_top[0], arom.adjusted_top[1])

        # Draw quadrilateral: left → bottom → right → top → left
        painter.drawLine(left_point[0], left_point[1], bottom_point[0], bottom_point[1])
        painter.drawLine(bottom_point[0], bottom_point[1], right_point[0], right_point[1])
        painter.drawLine(right_point[0], right_point[1], top_point[0], top_point[1])
        painter.drawLine(top_point[0], top_point[1], left_point[0], left_point[1])

        # Handles at the four actual extremal points if requested
        if with_handles:
            handle_size = 10
            painter.setBrush(QBrush(color))
            for point in [left_point, bottom_point, right_point, top_point]:
                painter.drawEllipse(point[0] - handle_size // 2,
                                  point[1] - handle_size // 2,
                                  handle_size, handle_size)

    def _draw_trial_boundaries(self, painter, arom: MarsArom, color: QColor):
        """Draw trial-specific boundaries (corners from the most recent trial)."""
        if arom.trial_top is None or arom.trial_bottom is None:
            return
        
        # Save global adjusted for a moment to reuse draw methods
        orig_top, orig_bottom = arom.adjusted_top, arom.adjusted_bottom
        orig_left, orig_right = arom.adjusted_left, arom.adjusted_right
        
        arom.adjusted_top, arom.adjusted_bottom = arom.trial_top, arom.trial_bottom
        arom.adjusted_left, arom.adjusted_right = arom.trial_left, arom.trial_right
        
        self._draw_arom_boundaries(painter, arom, color, False)
        
        # Restore
        arom.adjusted_top, arom.adjusted_bottom = orig_top, orig_bottom
        arom.adjusted_left, arom.adjusted_right = orig_left, orig_right

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
        """Draw range measurements based on assessment type."""
        if self.current_arom is None:
            return

        painter.setFont(QFont("Arial", 10, QFont.Bold))
        
        ml_max = self.current_arom.ml_range_cm
        ap_max = self.current_arom.ap_range_cm
        ml_avg = self.current_arom.ml_average_cm
        ap_avg = self.current_arom.ap_average_cm
        
        # Get last trial range
        ml_trial = self.current_arom.trial_ranges[-1][0] if self.current_arom.trial_ranges else 0.0
        ap_trial = self.current_arom.trial_ranges[-1][1] if self.current_arom.trial_ranges else 0.0

        y_pos = 30
        x_pos = 500

        def draw_stat_row(label, ml, ap, color, y):
            painter.setPen(QPen(color, 1))
            if self.movement_type == "AP":
                text = f"{label} AP: {ap:.2f} cm"
            elif self.movement_type == "ML":
                text = f"{label} ML: {ml:.2f} cm"
            else: # MLAP
                text = f"{label} ML: {ml:.2f}, AP: {ap:.2f} cm"
            painter.drawText(x_pos, y, text)

        # Trial (Black)
        draw_stat_row("Trial", ml_trial, ap_trial, QColor(0, 0, 0), y_pos)
        
        # Max (Red)
        draw_stat_row("Max", ml_max, ap_max, QColor(255, 0, 0), y_pos + 20)
        
        # Avg (Blue)
        draw_stat_row("Avg", ml_avg, ap_avg, QColor(0, 0, 255), y_pos + 40)

    def _draw_arm_weight_targets(self, painter):
        """Draw arm weight target boxes.

        Visual states:
        - Not started: Blue outline box
        - Current target (moving): Blue filled box
        - Current target (in target): Larger green box
        - Current target (recording): Pulsing green box
        - Completed: Small black filled box
        """
        # Import here to avoid circular dependency
        from arm_weight_data import ArmWeightTarget, ArmWeightState

        # Target size in meters
        TARGET_SIZE = 0.05  # 5 cm
        TARGET_REACH_SCALE = 2.0
        TARGET_COMPLETE_SCALE = 0.6

        # Convert to pixels
        pixels_per_unity_unit = 60.0
        target_size_pixels = TARGET_SIZE * self.SCALE_X * pixels_per_unity_unit

        for target, pos in self.arm_weight_targets.items():
            if target == ArmWeightTarget.NONE:
                continue

            y, z = pos
            screen_pos = self.robot_to_screen(y, z)

            # Determine visual style based on state
            if target in self.completed_targets:
                # Completed: small black box
                size = target_size_pixels * TARGET_COMPLETE_SCALE
                color = QColor(0, 0, 0)
                painter.setPen(QPen(color, 2))
                painter.setBrush(QBrush(color))
            elif target == self.current_arm_weight_target:
                if self.arm_weight_state == ArmWeightState.MOVING_TO_TARGET:
                    # Moving to target: blue filled box
                    size = target_size_pixels
                    color = QColor(0, 0, 255)
                    painter.setPen(QPen(color, 2))
                    painter.setBrush(QBrush(color))
                elif self.arm_weight_state == ArmWeightState.IN_TARGET:
                    # In target: larger green box
                    size = target_size_pixels * TARGET_REACH_SCALE
                    color = QColor(0, 200, 0)
                    painter.setPen(QPen(color, 3))
                    painter.setBrush(QBrush(QColor(0, 200, 0, 100)))
                elif self.arm_weight_state == ArmWeightState.RECORDING:
                    # Recording: pulsing green box (solid for now)
                    size = target_size_pixels * TARGET_REACH_SCALE
                    color = QColor(0, 255, 0)
                    painter.setPen(QPen(color, 4))
                    painter.setBrush(QBrush(color))
                else:
                    # Default
                    size = target_size_pixels
                    color = QColor(0, 0, 255)
                    painter.setPen(QPen(color, 2))
                    painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
            else:
                # Not started: blue outline only
                size = target_size_pixels
                color = QColor(0, 0, 255)
                painter.setPen(QPen(color, 2))
                painter.setBrush(QBrush(QColor(0, 0, 0, 0)))  # Transparent

            # Draw rectangle centered at target position
            half_size = size / 2
            painter.drawRect(int(screen_pos[0] - half_size),
                           int(screen_pos[1] - half_size),
                           int(size), int(size))

    def _draw_discrete_reach_targets(self, painter):
        """Draw discrete reaching target boxes.

        Visual states:
        - HOME target: Orange outline box
        - Peak targets (TOP/LEFT/RIGHT): Blue outline box
        - Current target (moving): Filled box (Orange for Home, Blue for Peak)
        - Current target (in target): Larger green box
        - Current target (hold/recording): Pulsing green box (solid green for now)
        - Completed: Small black filled box (only for Peak targets)
        """
        # Import here to avoid circular dependency
        from discrete_reach_data import DiscreteReachTarget
        from assessment_discreach import DiscreteReachState

        # Target size in meters
        TARGET_SIZE = 0.05  # 5 cm
        TARGET_REACH_SCALE = 2.0
        TARGET_COMPLETE_SCALE = 0.6

        # Convert to pixels
        pixels_per_unity_unit = 60.0
        target_size_pixels = TARGET_SIZE * self.SCALE_X * pixels_per_unity_unit

        for target, pos in self.discrete_reach_targets.items():
            if target == DiscreteReachTarget.NONE or pos is None:
                continue

            y, z = pos
            screen_pos = self.robot_to_screen(y, z)

            # Determine visual style based on state
            if target != DiscreteReachTarget.HOME and target in self.completed_discrete_targets:
                # Completed (non-home): small black box
                size = target_size_pixels * TARGET_COMPLETE_SCALE
                color = QColor(0, 0, 0)
                painter.setPen(QPen(color, 2))
                painter.setBrush(QBrush(color))
            elif target == self.current_discrete_reach_target:
                if self.discrete_reach_state in [DiscreteReachState.MOVING_TO_TARGET, 
                                               DiscreteReachState.MOVING_TO_HOME]:
                    # Moving to target: filled box (Orange for Home, Blue for Peak)
                    size = target_size_pixels
                    color = QColor(255, 140, 0) if target == DiscreteReachTarget.HOME else QColor(0, 0, 255)
                    painter.setPen(QPen(color, 2))
                    painter.setBrush(QBrush(color))
                elif self.discrete_reach_state in [DiscreteReachState.IN_TARGET, DiscreteReachState.IN_HOME]:
                    # Reached target: larger green outline
                    size = target_size_pixels * TARGET_REACH_SCALE
                    color = QColor(0, 200, 0)
                    painter.setPen(QPen(color, 3))
                    painter.setBrush(QBrush(QColor(0, 200, 0, 100)))
                elif self.discrete_reach_state in [DiscreteReachState.HOLDING, DiscreteReachState.HOLD_STABILIZING]:
                    # Holding/Recording: pulsing green box
                    size = target_size_pixels * TARGET_REACH_SCALE
                    color = QColor(0, 255, 0)
                    painter.setPen(QPen(color, 4))
                    painter.setBrush(QBrush(color))
                else:
                    # Default
                    size = target_size_pixels
                    color = QColor(0, 0, 255)
                    painter.setPen(QPen(color, 2))
                    painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
            else:
                # Not current: colored outline only
                size = target_size_pixels
                color = QColor(255, 140, 0) if target == DiscreteReachTarget.HOME else QColor(0, 0, 255)
                painter.setPen(QPen(color, 2))
                painter.setBrush(QBrush(QColor(0, 0, 0, 0)))

            # Draw rectangle centered at target position
            half_size = size / 2
            painter.drawRect(int(screen_pos[0] - half_size),
                           int(screen_pos[1] - half_size),
                           int(size), int(size))

    def _draw_discrete_reach_paths(self, painter):
        """Draw dashed lines from Home to each peak target."""
        # Import here to avoid circular dependency
        from discrete_reach_data import DiscreteReachTarget

        home_pos = self.discrete_reach_targets.get(DiscreteReachTarget.HOME)
        if home_pos is None:
            return

        home_screen = self.robot_to_screen(home_pos[0], home_pos[1])

        # Light gray dashed lines
        painter.setPen(QPen(QColor(200, 200, 200), 2, Qt.DashLine))

        for target in [DiscreteReachTarget.TOP, DiscreteReachTarget.LEFT, DiscreteReachTarget.RIGHT]:
            target_pos = self.discrete_reach_targets.get(target)
            if target_pos:
                target_screen = self.robot_to_screen(target_pos[0], target_pos[1])
                painter.drawLine(home_screen[0], home_screen[1], target_screen[0], target_screen[1])

    def _draw_countdown_timer(self, painter):
        """Draw large countdown timer at the top."""
        if self.countdown_timer is None:
            return

        # Prepare font
        font = QFont("Arial", 48, QFont.Bold)
        painter.setFont(font)
        
        # Format timer text (e.g. "3", "2", "1")
        if isinstance(self.countdown_timer, (int, float)):
            timer_val = max(0, int(self.countdown_timer + 0.9)) # Ceil-like behavior for 3, 2, 1
            if timer_val <= 0: return
            text = str(timer_val)
        else:
            text = str(self.countdown_timer)

        # Calculate position (Top Center)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        x = (self.width() - text_width) // 2
        y = 100 # Position from top

        # Draw with slight shadow for visibility
        painter.setPen(QColor(0, 0, 0, 100))
        painter.drawText(x + 2, y + 2, text)
        
        # Color based on value (Green for high, Orange/Red for low?) - Keeping it simple Green for now
        painter.setPen(QColor(0, 200, 0))
        painter.drawText(x, y, text)


class BaseAssessmentWindow(QMainWindow):
    """Base class for workspace assessment windows."""
    
    # Signal emitted when assessment is successfully saved
    # Parameter: assessment type (e.g., "AP", "ML", "MLAP")
    assessment_finished = Signal(str)

    def __init__(self, mars, patient_id=None, time_point="A0", is_demo=False, session_subdir=None, parent=None):
        super().__init__(parent)
        self.mars = mars
        self.patient_id = patient_id
        self.time_point = time_point
        self.is_demo = is_demo
        self.session_subdir = session_subdir
        self.state = AromAssessState.INIT
        self.adjust_state = AromAdjustState.NONE

        # Trial Management
        self.current_trial = 1
        self.max_trials = 3

        # Data
        self.current_arom = None
        self.previous_arom = None
        self.trajectory_points = []
        self.last_recorded_pos = None

        # Set as modal to block main window
        self.setWindowModality(Qt.ApplicationModal)

        # UI
        self.canvas = WorkspaceAssessmentCanvas(self.movement_type, self)
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
        """Load most recent assessment of this type (AROM types only)."""
        if self.movement_type in ["AP", "ML", "MLAP"]:
            self.previous_arom = MarsArom.find_latest_assessment(self.movement_type, patient_id=self.patient_id)
            self.canvas.previous_arom = self.previous_arom
        else:
            self.previous_arom = None
            self.canvas.previous_arom = None

    def on_start_assessment(self):
        """Start assessment - transition INIT -> ASSESSROM."""
        if self.state != AromAssessState.INIT:
            return

        # Initialize trial properties
        self.current_trial = 1

        # Create new AROM instance
        self.current_arom = MarsArom(self.movement_type, self.patient_id, self.time_point, self.is_demo)
        self.current_arom.start_assessment()
        self.canvas.current_arom = self.current_arom

        # Clear trajectory
        self.trajectory_points = []
        self.canvas.trajectory = []
        self.last_recorded_pos = None

        # Update state
        self.state = AromAssessState.ASSESSROM
        self.canvas.state = self.state
        self.canvas.instruction_text = f"Trial {self.current_trial} of {self.max_trials}: Move through your range. Press device button when done."

        # Update buttons
        self.start_btn.setVisible(False)

        print(f"Started {self.movement_type} assessment - Trial {self.current_trial}")

    def pause_trial_assessment(self):
        """Pause assessment between trials - transition ASSESSROM -> TRIAL_PAUSE."""
        if self.state != AromAssessState.ASSESSROM:
            return

        # Pause recording and compute corners for the *current* trial's data
        self.current_arom.pause_assessment()
        
        # Update state to TRIAL_PAUSE so user can see their bounds
        self.state = AromAssessState.TRIAL_PAUSE
        self.canvas.state = self.state
        self.canvas.instruction_text = f"Trial {self.current_trial} complete. Press button to start Trial {self.current_trial + 1}."

        print(f"Paused {self.movement_type} assessment after Trial {self.current_trial}")

    def ready_next_trial(self):
        """Prepare for next trial - transition TRIAL_PAUSE -> TRIAL_READY."""
        if self.state != AromAssessState.TRIAL_PAUSE:
            return

        self.current_trial += 1
        
        # Clear the old trajectory visually and internally before they start moving
        self.trajectory_points = []
        self.canvas.trajectory = []
        self.last_recorded_pos = None

        # Update state to TRIAL_READY
        self.state = AromAssessState.TRIAL_READY
        self.canvas.state = self.state
        self.canvas.instruction_text = f"Ready for Trial {self.current_trial}. Press device button to start."
        
        # Reclaim previous AROM context
        self.canvas.current_arom = self.current_arom
        print(f"Ready for {self.movement_type} assessment - Trial {self.current_trial}")

    def resume_trial_assessment(self):
        """Resume assessment for next trial - transition TRIAL_READY -> ASSESSROM."""
        if self.state != AromAssessState.TRIAL_READY:
            return

        # Resume recording (which will start a fresh trajectory in MarsArom)
        self.current_arom.resume_assessment()

        # Update state back to ASSESSROM
        self.state = AromAssessState.ASSESSROM
        self.canvas.state = self.state
        self.canvas.instruction_text = f"Trial {self.current_trial} of {self.max_trials}: Move through your range. Press device button when done."

        print(f"Resumed {self.movement_type} assessment - Trial {self.current_trial}")

    def stop_assessment(self):
        """Stop assessment fully - transition ASSESSROM -> ADJUST."""
        if self.state != AromAssessState.ASSESSROM:
            return

        # Stop recording completely
        self.current_arom.stop_assessment()

        # TEST: Swap left and right for LEFT limb to test behavior
        if self.canvas.limb_type == "LEFT" and self.movement_type == "MLAP":
            temp_left = self.current_arom.adjusted_left
            self.current_arom.adjusted_left = self.current_arom.adjusted_right
            self.current_arom.adjusted_right = temp_left
            print(f"[TEST] Swapped left/right corners for LEFT limb")

        # Update state
        self.state = AromAssessState.ADJUST
        self.canvas.state = self.state
        self.canvas.instruction_text = "Adjust boundaries with L/R/T/B keys + mouse. Click 'Save & Close' when done."

        # Update buttons
        self.recalibrate_btn.setVisible(True)
        self.save_btn.setVisible(True)

        print(f"Stopped {self.movement_type} assessment - computed physical corners")

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

        - INIT state: Start assessment Trial 1 (INIT → ASSESSROM)
        - ASSESSROM state (< 3 trials): Pause and calculate intermediate range (ASSESSROM → TRIAL_PAUSE)
        - ASSESSROM state (== 3 trials): Stop and adjust boundaries (ASSESSROM → ADJUST)
        - TRIAL_PAUSE state: Ready next trial by clearing bounds (TRIAL_PAUSE → TRIAL_READY)
        - TRIAL_READY state: Start next trial (TRIAL_READY → ASSESSROM)
        """
        print(f"[Button] Device button released in state: {self.state}")

        if self.state == AromAssessState.INIT:
            print("[Button] Starting assessment from button press")
            self.on_start_assessment()

        elif self.state == AromAssessState.ASSESSROM:
            if self.current_trial < self.max_trials:
                print(f"[Button] Pausing trial {self.current_trial}")
                self.pause_trial_assessment()
            else:
                print(f"[Button] Stopping assessment at trial {self.current_trial}")
                self.stop_assessment()

        elif self.state == AromAssessState.TRIAL_PAUSE:
            print(f"[Button] Readying trial {self.current_trial + 1}")
            self.ready_next_trial()
            
        elif self.state == AromAssessState.TRIAL_READY:
            print(f"[Button] Starting trial {self.current_trial}")
            self.resume_trial_assessment()

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
        filepath = self.current_arom.save_to_csv(session_subdir=self.session_subdir)
        print(f"Saved assessment to: {filepath}")

        # Emit completion signal
        self.assessment_finished.emit(self.movement_type)

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
