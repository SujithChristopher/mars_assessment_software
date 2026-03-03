"""
Arm Weight Assessment window.

Standalone assessment for force recording at 5 targets (TOP, RIGHT, BOTTOM, LEFT, CENTER).
Requires prior MLAP data for workspace context.

Author: Sivakumar Balasubramanian
Date: 11 February 2026 (Refactored 03 March 2026)
Email: siva82kb@gmail.com
"""

import time
from enum import Enum
from PySide6.QtCore import QTimer, Signal
from assessment_base import BaseAssessmentWindow, AromAssessState
from arm_weight_data import ArmWeightData, ArmWeightTarget, ArmWeightState
from mars_arom_data import MarsArom


class AssessmentArmWeightWindow(BaseAssessmentWindow):
    """Standalone Arm Weight assessment window."""

    # Arm weight constants (matching original implementation)
    TARGET_SIZE = 0.05  # meters (5 cm)
    TARGET_TOLERANCE = TARGET_SIZE * 0.5  # 2.5 cm
    RECORDING_TIME = 2.0  # seconds
    TARGET_REACH_SCALE = 2.0
    TARGET_COMPLETE_SCALE = 0.6

    # Target sequence (matching original: TOP → RIGHT → BOTTOM → LEFT → CENTER)
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
        return "ArmWeight"

    def __init__(self, mars, patient_id=None, time_point="A0", is_demo=False, session_subdir=None, parent=None):
        # Arm weight state management
        self.arm_weight_state = ArmWeightState.INACTIVE
        self.arm_weight_data = None
        self.current_target = ArmWeightTarget.NONE
        self.current_target_index = 0
        self.recording_start_time = 0.0

        super().__init__(mars, patient_id, time_point, is_demo, session_subdir, parent)
        
        # Override BaseAssessmentWindow initialization for Arm Weight
        self.state = AromAssessState.DONE # Skip AROM part
        
        # Load latest MLAP to initialize targets
        mlap_arom = MarsArom.find_latest_assessment("MLAP", patient_id=self.patient_id)
        if mlap_arom:
            self.arm_weight_data = ArmWeightData(self.patient_id, self.time_point, self.is_demo)
            self.arm_weight_data.initialize_from_mlap(mlap_arom)
            self.canvas.arm_weight_targets = self.arm_weight_data.target_positions
            # Keep the MLAP quadrilateral visible for context
            self.canvas.current_arom = mlap_arom
            
            # Start arm weight assessment
            self.arm_weight_data.start_assessment()
            self.arm_weight_state = ArmWeightState.INIT
            self.canvas.arm_weight_state = self.arm_weight_state
            self.canvas.instruction_text = "Arm Weight Assessment: Press robot button to begin"
            print(f"Initialized Arm Weight targets from latest MLAP for patient {self.patient_id}")
        else:
            self.canvas.instruction_text = "ERROR: No MLAP data found. Please complete MLAP assessment first."
            print("No MLAP assessment found for Arm Weight targets.")

        # Hide AROM specific buttons
        self.recalibrate_btn.setVisible(False)
        self.save_btn.setText("Complete Arm Weight")
        self.save_btn.clicked.disconnect()
        self.save_btn.clicked.connect(self.save_arm_weight_and_close)
        self.save_btn.setVisible(False) # Only show when all done

    def run_arm_weight_state_machine(self):
        """Run arm weight assessment state machine."""
        if self.arm_weight_state == ArmWeightState.INACTIVE or self.arm_weight_data is None:
            return

        if self.arm_weight_state == ArmWeightState.MOVING_TO_TARGET:
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
            if self.mars is None:
                return

            _, y, z = self.mars.ep_pos_in_plane
            target_pos = self.arm_weight_data.target_positions[self.current_target]

            dy = abs(y - target_pos[0])
            dz = abs(z - target_pos[1])

            if dy >= self.TARGET_TOLERANCE or dz >= self.TARGET_TOLERANCE:
                # Moved out of target
                self.canvas.countdown_timer = None
                self.arm_weight_state = ArmWeightState.MOVING_TO_TARGET
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"Moving to {self.current_target.name} target..."
                print(f"Left {self.current_target.name} target")

        elif self.arm_weight_state == ArmWeightState.RECORDING:
            # Recording data for target
            if self.mars is None:
                return

            _, y, z = self.mars.ep_pos_in_plane
            target_pos = self.arm_weight_data.target_positions[self.current_target]

            dy = abs(y - target_pos[0])
            dz = abs(z - target_pos[1])

            # Check if button pressed (interrupts recording)
            if self.mars.button_state == 0:
                self.arm_weight_data.stop_target_recording()
                self.canvas.countdown_timer = None
                self.arm_weight_state = ArmWeightState.IN_TARGET
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"Recording stopped. Release button to record again."
                print(f"Recording interrupted for {self.current_target.name}")
                return

            if dy >= self.TARGET_TOLERANCE or dz >= self.TARGET_TOLERANCE:
                # Moved out of target - stop recording
                self.arm_weight_data.stop_target_recording()
                self.canvas.countdown_timer = None
                self.arm_weight_state = ArmWeightState.MOVING_TO_TARGET
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"Left target. Moving to {self.current_target.name} target..."
                print(f"Left {self.current_target.name} target during recording")
                return

            # Collect data point
            force = self.mars.force
            self.arm_weight_data.add_data_point(y, z, force)

            # Check if recording time complete
            elapsed = time.time() - self.recording_start_time
            remaining = self.RECORDING_TIME - elapsed
            
            if remaining > 0:
                self.canvas.countdown_timer = remaining
                self.canvas.instruction_text = f"Recording {self.current_target.name}... ({int(remaining + 0.9)}s)"
            else:
                # Recording complete
                self.arm_weight_data.stop_target_recording()
                self.canvas.countdown_timer = None
                self.arm_weight_state = ArmWeightState.TARGET_COMPLETE
                self.canvas.completed_targets.add(self.current_target)
                self.canvas.arm_weight_state = self.arm_weight_state
                self.canvas.instruction_text = f"{self.current_target.name} target complete!"
                print(f"Completed {self.current_target.name} target")

                # Move to next target after short delay
                QTimer.singleShot(1000, self.move_to_next_target)

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
        """Handle device button release."""
        if self.arm_weight_data is None:
            return

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
            self.recording_start_time = time.time()
            self.arm_weight_data.start_target_recording(self.current_target)
            self.arm_weight_state = ArmWeightState.RECORDING
            self.canvas.arm_weight_state = self.arm_weight_state
            self.canvas.instruction_text = f"Recording {self.current_target.name} target... Hold still!"
            print(f"Started recording {self.current_target.name} target")

    def handle_new_data(self):
        """Handle new data from MARS device."""
        # Call base implementation to update robot position etc.
        super().handle_new_data()

        # Run arm weight state machine
        self.run_arm_weight_state_machine()

    def save_arm_weight_and_close(self):
        """Save arm weight data and close window."""
        if self.arm_weight_data is None or self.arm_weight_state != ArmWeightState.ALL_DONE:
            return

        # Save arm weight data
        filepath = self.arm_weight_data.save_to_csv(session_subdir=self.session_subdir)
        print(f"Saved arm weight assessment to: {filepath}")

        # Emit completion signal (inherited from BaseAssessmentWindow)
        self.assessment_finished.emit(self.movement_type)

        # Close window
        self.close()
