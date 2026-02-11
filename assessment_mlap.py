"""
Combined MLAP (Medio-Lateral + Anterior-Posterior) workspace assessment window.

Assesses full 2D workspace envelope, followed by arm weight assessment at 5 targets.

Author: Sivakumar Balasubramanian
Date: 11 February 2026
Email: siva82kb@gmail.com
"""

from enum import Enum
from PySide6.QtCore import QTimer
from assessment_base import BaseAssessmentWindow, AromAssessState
from arm_weight_data import ArmWeightData, ArmWeightTarget


class ArmWeightState(Enum):
    """Arm weight assessment state machine."""
    INACTIVE = 0
    INIT = 1
    MOVING_TO_TARGET = 2
    IN_TARGET = 3
    RECORDING = 4
    TARGET_COMPLETE = 5
    ALL_DONE = 6


class AssessmentMLAPWindow(BaseAssessmentWindow):
    """MLAP (Combined ML+AP) assessment window with arm weight assessment."""

    # Arm weight constants (matching Unity implementation)
    TARGET_SIZE = 0.05  # meters (5 cm)
    TARGET_TOLERANCE = TARGET_SIZE * 0.5  # 2.5 cm
    RECORDING_TIME = 2.0  # seconds
    TARGET_REACH_SCALE = 2.0
    TARGET_COMPLETE_SCALE = 0.6

    # Target sequence (matching Unity: TOP → RIGHT → BOTTOM → LEFT → CENTER)
    TARGET_SEQUENCE = [
        ArmWeightTarget.TOP,
        ArmWeightTarget.RIGHT,
        ArmWeightTarget.BOTTOM,
        ArmWeightTarget.LEFT,
        ArmWeightTarget.CENTER
    ]

    @property
    def movement_type(self) -> str:
        """Assessment type."""
        return "MLAP"

    def __init__(self, mars, parent=None):
        # Arm weight state management
        self.arm_weight_state = ArmWeightState.INACTIVE
        self.arm_weight_data = None
        self.current_target = ArmWeightTarget.NONE
        self.current_target_index = 0
        self.recording_start_time = 0.0

        super().__init__(mars, parent)
        # Configure canvas for MLAP-specific visualization
        self.canvas.instruction_text = "MLAP Assessment: Press robot button to begin"

    def save_assessment(self):
        """Save AROM assessment and transition to arm weight assessment."""
        if self.current_arom is None:
            return

        # Save AROM data to CSV
        filepath = self.current_arom.save_to_csv()
        print(f"Saved MLAP assessment to: {filepath}")

        # Update state to DONE
        self.state = AromAssessState.DONE

        # Initialize arm weight assessment
        self.start_arm_weight_assessment()

    def start_arm_weight_assessment(self):
        """Initialize arm weight assessment after MLAP is complete."""
        print("Starting arm weight assessment...")

        # Create arm weight data instance
        self.arm_weight_data = ArmWeightData()
        self.arm_weight_data.initialize_from_mlap(self.current_arom, self.canvas.limb_type)
        self.arm_weight_data.start_assessment()

        # Clear trajectory but keep quadrilateral
        self.trajectory_points = []
        self.canvas.trajectory = []

        # Update state
        self.arm_weight_state = ArmWeightState.INIT
        self.current_target = ArmWeightTarget.NONE
        self.current_target_index = 0

        # Update UI
        self.canvas.instruction_text = "Arm Weight Assessment: Press robot button to begin"
        self.canvas.arm_weight_targets = self.arm_weight_data.target_positions
        self.canvas.arm_weight_state = self.arm_weight_state
        self.canvas.current_arm_weight_target = self.current_target
        self.canvas.completed_targets = set()

        # Hide adjust buttons, show arm weight complete button
        self.recalibrate_btn.setVisible(False)
        self.save_btn.setText("Complete Arm Weight")
        self.save_btn.clicked.disconnect()
        self.save_btn.clicked.connect(self.save_arm_weight_and_close)
        self.save_btn.setVisible(False)  # Only show when all done

        print("Arm weight assessment initialized")

    def run_arm_weight_state_machine(self):
        """Run arm weight assessment state machine."""
        if self.arm_weight_state == ArmWeightState.INACTIVE:
            return

        if self.arm_weight_state == ArmWeightState.INIT:
            # Waiting for button press to start
            pass

        elif self.arm_weight_state == ArmWeightState.MOVING_TO_TARGET:
            # Check if user reached target
            if self.mars is None:
                return

            _, y, z = self.mars.ep_pos_in_plane
            target_pos = self.arm_weight_data.target_positions[self.current_target]

            dy = abs(y - target_pos[0])
            dz = abs(z - target_pos[1])

            if dy < self.TARGET_TOLERANCE and dz < self.TARGET_TOLERANCE:
                # Reached target
                self.arm_weight_state = ArmWeightState.IN_TARGET
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"In {self.current_target.name} target. Release button to record."
                print(f"Reached {self.current_target.name} target")

        elif self.arm_weight_state == ArmWeightState.IN_TARGET:
            # Waiting for button release to start recording
            # Check if still in target
            if self.mars is None:
                return

            _, y, z = self.mars.ep_pos_in_plane
            target_pos = self.arm_weight_data.target_positions[self.current_target]

            dy = abs(y - target_pos[0])
            dz = abs(z - target_pos[1])

            if dy >= self.TARGET_TOLERANCE or dz >= self.TARGET_TOLERANCE:
                # Moved out of target
                self.arm_weight_state = ArmWeightState.MOVING_TO_TARGET
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"Moving to {self.current_target.name} target..."
                print(f"Left {self.current_target.name} target")

        elif self.arm_weight_state == ArmWeightState.RECORDING:
            # Recording data for target
            if self.mars is None:
                return

            # Check if still in target
            _, y, z = self.mars.ep_pos_in_plane
            target_pos = self.arm_weight_data.target_positions[self.current_target]

            dy = abs(y - target_pos[0])
            dz = abs(z - target_pos[1])

            # Check if button pressed (interrupts recording)
            # button_state: 0 = pressed, 1 = released
            if self.mars.button_state == 0:
                # Button pressed - stop recording and go back to IN_TARGET
                self.arm_weight_data.stop_target_recording()
                self.arm_weight_state = ArmWeightState.IN_TARGET
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"Recording stopped. Release button to record again."
                print(f"Recording interrupted for {self.current_target.name}")
                return

            if dy >= self.TARGET_TOLERANCE or dz >= self.TARGET_TOLERANCE:
                # Moved out of target - stop recording
                self.arm_weight_data.stop_target_recording()
                self.arm_weight_state = ArmWeightState.MOVING_TO_TARGET
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"Left target. Moving to {self.current_target.name} target..."
                print(f"Left {self.current_target.name} target during recording")
                return

            # Collect data point
            force = self.mars.force
            self.arm_weight_data.add_data_point(y, z, force)

            # Check if recording time complete
            import time
            elapsed = time.time() - self.recording_start_time
            if elapsed >= self.RECORDING_TIME:
                # Recording complete
                self.arm_weight_data.stop_target_recording()
                self.arm_weight_state = ArmWeightState.TARGET_COMPLETE
                self.canvas.completed_targets.add(self.current_target)
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"{self.current_target.name} target complete!"
                print(f"Completed {self.current_target.name} target")

                # Move to next target after short delay
                QTimer.singleShot(1000, self.move_to_next_target)

        elif self.arm_weight_state == ArmWeightState.TARGET_COMPLETE:
            # Waiting for timer to move to next target
            pass

        elif self.arm_weight_state == ArmWeightState.ALL_DONE:
            # All targets complete
            pass

    def move_to_next_target(self):
        """Move to next target in sequence."""
        self.current_target_index += 1

        if self.current_target_index >= len(self.TARGET_SEQUENCE):
            # All targets complete
            self.arm_weight_state = ArmWeightState.ALL_DONE
            self.canvas.arm_weight_state = self.arm_weight_state
            self.canvas.instruction_text = "Arm weight assessment complete! Click 'Complete Arm Weight' to save."
            self.save_btn.setVisible(True)
            print("All arm weight targets complete!")
        else:
            # Move to next target
            self.current_target = self.TARGET_SEQUENCE[self.current_target_index]
            self.arm_weight_state = ArmWeightState.MOVING_TO_TARGET
            self.canvas.current_arm_weight_target = self.current_target
            self.canvas.arm_weight_state = self.arm_weight_state
            self.canvas.instruction_text = f"Moving to {self.current_target.name} target..."
            print(f"Moving to {self.current_target.name} target")

    def handle_button_release(self):
        """Handle device button release - triggers state transitions for both AROM and arm weight."""
        print(f"[Button] Device button released in AROM state: {self.state}, Arm weight state: {self.arm_weight_state}")

        # Handle AROM states (inherited behavior)
        if self.arm_weight_state == ArmWeightState.INACTIVE:
            super().handle_button_release()
            return

        # Handle arm weight states
        if self.arm_weight_state == ArmWeightState.INIT:
            # Start first target
            self.current_target = self.TARGET_SEQUENCE[0]
            self.current_target_index = 0
            self.arm_weight_state = ArmWeightState.MOVING_TO_TARGET
            self.canvas.current_arm_weight_target = self.current_target
            self.canvas.arm_weight_state = self.arm_weight_state
            self.canvas.instruction_text = f"Moving to {self.current_target.name} target..."
            print(f"Started arm weight assessment - moving to {self.current_target.name}")

        elif self.arm_weight_state == ArmWeightState.IN_TARGET:
            # Start recording
            import time
            self.recording_start_time = time.time()
            self.arm_weight_data.start_target_recording(self.current_target)
            self.arm_weight_state = ArmWeightState.RECORDING
            self.canvas.arm_weight_state = self.arm_weight_state
            self.canvas.instruction_text = f"Recording {self.current_target.name} target... Hold still!"
            print(f"Started recording {self.current_target.name} target")

    def handle_new_data(self):
        """Handle new data from MARS device - update for both AROM and arm weight."""
        # Call parent implementation for AROM
        super().handle_new_data()

        # Run arm weight state machine
        self.run_arm_weight_state_machine()

    def save_arm_weight_and_close(self):
        """Save arm weight data and close window."""
        if self.arm_weight_data is None or self.arm_weight_state != ArmWeightState.ALL_DONE:
            return

        # Save arm weight data
        filepath = self.arm_weight_data.save_to_csv()
        print(f"Saved arm weight assessment to: {filepath}")

        # Close window
        self.close()
