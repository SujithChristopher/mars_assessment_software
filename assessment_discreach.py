"""
Discrete Reaching assessment window.

Guides the user from a bottom 'Home' position to 75% workspace targets.
Requires a 3-second hold at each target.

Author: Sivakumar Balasubramanian
Date: 23 February 2026
Email: siva82kb@gmail.com
"""

from enum import Enum
import time
from PySide6.QtCore import QTimer
from assessment_base import BaseAssessmentWindow, AromAssessState
from mars_arom_data import MarsArom
from discrete_reach_data import DiscreteReachData, DiscreteReachTarget


class DiscreteReachState(Enum):
    """Discrete reaching assessment state machine."""
    INACTIVE = 0
    INIT = 1
    MOVING_TO_HOME = 2
    IN_HOME = 3
    MOVING_TO_TARGET = 4
    IN_TARGET = 5
    HOLD_STABILIZING = 6
    HOLDING = 7
    TARGET_COMPLETE = 8
    ALL_DONE = 9


class AssessmentDiscreteReachWindow(BaseAssessmentWindow):
    """Discrete Reaching assessment window."""

    # Constants
    TARGET_SIZE = 0.05  # meters
    TARGET_TOLERANCE = TARGET_SIZE * 0.5
    HOLD_TIME = 3.0  # seconds

    # Peak target sequence
    PEAK_SEQUENCE = [
        DiscreteReachTarget.TOP,
        DiscreteReachTarget.LEFT,
        DiscreteReachTarget.RIGHT
    ]

    @property
    def movement_type(self) -> str:
        """Assessment type name."""
        return "DiscreteReaching"

    def __init__(self, mars, patient_id=None, time_point="A0", is_demo=False, session_subdir=None, parent=None):
        self.dr_state = DiscreteReachState.INACTIVE
        self.dr_data = None
        self.current_peak_index = 0
        self.holding_start_time = 0.0
        
        super().__init__(mars, patient_id, time_point, is_demo, session_subdir, parent)
        self.canvas.instruction_text = "Discrete Reaching: Press robot button to begin"
        
        # Load latest MLAP to initialize targets
        mlap_arom = MarsArom.find_latest_assessment("MLAP", patient_id=self.patient_id)
        if mlap_arom:
            self.dr_data = DiscreteReachData(self.patient_id, self.time_point, self.is_demo)
            self.dr_data.initialize_from_mlap(mlap_arom)
            self.canvas.discrete_reach_targets = self.dr_data.target_positions
            # Also keep the MLAP quadrilateral visible
            self.canvas.current_arom = mlap_arom
            print(f"Initialized targets from latest MLAP assessment for patient {self.patient_id}")
        else:
            print("No MLAP assessment found. Calibration required.")
            self.canvas.instruction_text = "ERROR: No MLAP data found. Please complete MLAP assessment first."

    def on_start_assessment(self):
        """Initialize discrete reaching assessment."""
        if self.dr_data is None:
            # Try reloading MLAP if it was missing initially
            mlap_arom = MarsArom.find_latest_assessment("MLAP", patient_id=self.patient_id)
            if mlap_arom:
                self.dr_data = DiscreteReachData(self.patient_id, self.time_point, self.is_demo)
                self.dr_data.initialize_from_mlap(mlap_arom)
                self.canvas.discrete_reach_targets = self.dr_data.target_positions
                self.canvas.current_arom = mlap_arom
            else:
                return
            
        self.dr_data.start_assessment()
        self.dr_state = DiscreteReachState.INIT
        self.current_peak_index = 0
        self.canvas.discrete_reach_state = self.dr_state
        self.canvas.completed_discrete_targets = set()
        
        # UI configuration
        self.recalibrate_btn.setVisible(False)
        self.save_btn.setText("Complete Assessment")
        # Reuse save_btn for "Complete"
        try:
            self.save_btn.clicked.disconnect()
        except:
            pass
        self.save_btn.clicked.connect(self.save_and_close)
        self.save_btn.setVisible(False)

        print("Discrete reaching assessment started")

    def run_dr_state_machine(self):
        """Run discrete reaching assessment state machine logic."""
        if self.dr_state == DiscreteReachState.INACTIVE or self.mars is None:
            return

        _, y, z = self.mars.ep_pos_in_plane
        
        if self.dr_state == DiscreteReachState.MOVING_TO_HOME:
            home_pos = self.dr_data.target_positions[DiscreteReachTarget.HOME]
            if self._is_at_pos(y, z, home_pos):
                self.dr_state = DiscreteReachState.IN_HOME
                self.canvas.discrete_reach_state = self.dr_state
                self.canvas.current_discrete_reach_target = DiscreteReachTarget.HOME
                self.canvas.instruction_text = "Reached Home. Release button to start hold."

        elif self.dr_state == DiscreteReachState.MOVING_TO_TARGET:
            target = self.PEAK_SEQUENCE[self.current_peak_index]
            target_pos = self.dr_data.target_positions[target]
            if self._is_at_pos(y, z, target_pos):
                self.dr_state = DiscreteReachState.IN_TARGET
                self.canvas.discrete_reach_state = self.dr_state
                self.canvas.instruction_text = f"Reached {target.name} target. Release button to start hold."

        elif self.dr_state == DiscreteReachState.HOLD_STABILIZING:
            # Short delay or check if within target before starting timer
            target = self.canvas.current_discrete_reach_target
            target_pos = self.dr_data.target_positions[target]
            
            if self._is_at_pos(y, z, target_pos):
                self.dr_state = DiscreteReachState.HOLDING
                self.holding_start_time = time.time()
                self.dr_data.start_target_recording(target)
                self.canvas.discrete_reach_state = self.dr_state
            else:
                self.canvas.instruction_text = f"Keep within {target.name} to hold."

        elif self.dr_state == DiscreteReachState.HOLDING:
            # Holding at either Home or Peak target
            target = self.canvas.current_discrete_reach_target
            target_pos = self.dr_data.target_positions[target]
            
            if not self._is_at_pos(y, z, target_pos):
                # Moved out of target - recording stopped, go back to moving
                self.dr_data.stop_target_recording()
                self.canvas.countdown_timer = None
                if target == DiscreteReachTarget.HOME:
                    self.dr_state = DiscreteReachState.MOVING_TO_HOME
                else:
                    self.dr_state = DiscreteReachState.MOVING_TO_TARGET
                
                self.canvas.discrete_reach_state = self.dr_state
                self.canvas.instruction_text = f"Moved out! Return to {target.name}."
                return

            # Record data point
            self.dr_data.add_data_point(y, z)

            # Check hold duration
            elapsed = time.time() - self.holding_start_time
            remaining = self.HOLD_TIME - elapsed
            
            if remaining > 0:
                self.canvas.countdown_timer = remaining
                self.canvas.instruction_text = f"Holding {target.name}... ({int(remaining + 0.9)}s)"
            else:
                # Hold complete
                self.canvas.countdown_timer = None
                self.dr_data.stop_target_recording()
                
                if target == DiscreteReachTarget.HOME:
                    # Home hold complete -> move to current peak or finish
                    if self.current_peak_index >= len(self.PEAK_SEQUENCE):
                        # Final home hold complete
                        self.dr_state = DiscreteReachState.ALL_DONE
                        self.canvas.discrete_reach_state = self.dr_state
                        self.canvas.instruction_text = "Assessment finished! Click 'Complete Assessment' to save."
                        self.save_btn.setVisible(True)
                        print("Discrete Reaching assessment finished.")
                    else:
                        peak_target = self.PEAK_SEQUENCE[self.current_peak_index]
                        self.dr_state = DiscreteReachState.MOVING_TO_TARGET
                        self.canvas.current_discrete_reach_target = peak_target
                        self.canvas.discrete_reach_state = self.dr_state
                        self.canvas.instruction_text = f"Home hold complete! Reach to {peak_target.name}."
                else:
                    # Peak target hold complete
                    self.canvas.completed_discrete_targets.add(target)
                    print(f"Completed {target.name}")
                    
                    if self.current_peak_index + 1 >= len(self.PEAK_SEQUENCE):
                        # This was the last peak target. 
                        # We must return to Home one last time to finish the loop.
                        self.dr_state = DiscreteReachState.TARGET_COMPLETE
                        self.canvas.discrete_reach_state = self.dr_state
                        self.canvas.instruction_text = f"{target.name} complete! Return to Home to finish."
                        # Use a state that indicates we are finished with peaks and just need to reach home
                        QTimer.singleShot(1000, self.transition_to_final_home)
                    else:
                        # Transition back to Home for the next peak
                        self.dr_state = DiscreteReachState.TARGET_COMPLETE
                        self.canvas.discrete_reach_state = self.dr_state
                        self.canvas.instruction_text = f"{target.name} complete! Return to Home."
                        QTimer.singleShot(1000, self.auto_transition_after_hold)

    def _is_at_pos(self, y: float, z: float, target_pos: tuple) -> bool:
        """Check if current position is within tolerance of target."""
        if target_pos is None: return False
        dy = abs(y - target_pos[0])
        dz = abs(z - target_pos[1])
        return dy < self.TARGET_TOLERANCE and dz < self.TARGET_TOLERANCE

    def transition_to_final_home(self):
        """Transition back to Home after the last peak target."""
        self.current_peak_index = len(self.PEAK_SEQUENCE) # Signal we are done with peaks
        self.dr_state = DiscreteReachState.MOVING_TO_HOME
        self.canvas.discrete_reach_state = self.dr_state
        self.canvas.current_discrete_reach_target = DiscreteReachTarget.HOME
        self.canvas.instruction_text = "Return to Home for final hold."

    def auto_transition_after_hold(self):
        """Advance to next target in sequence."""
        self.current_peak_index += 1
        self.dr_state = DiscreteReachState.MOVING_TO_HOME
        self.canvas.discrete_reach_state = self.dr_state
        self.canvas.current_discrete_reach_target = DiscreteReachTarget.HOME
        self.canvas.instruction_text = "Return to Home position."

    def handle_button_release(self):
        """Handle device button release for state machine transitions."""
        print(f"[DR] Button released in state: {self.dr_state}")
        
        if self.dr_state == DiscreteReachState.INACTIVE:
            # Start assessment
            super().handle_button_release()
            return

        if self.dr_state == DiscreteReachState.INIT:
            # Move to Home vertex to start sequence
            self.dr_state = DiscreteReachState.MOVING_TO_HOME
            self.canvas.current_discrete_reach_target = DiscreteReachTarget.HOME
            self.canvas.discrete_reach_state = self.dr_state
            self.canvas.instruction_text = "Move to Home position (bottom vertex)."

        elif self.dr_state == DiscreteReachState.IN_HOME:
            # Button released at Home -> Start 3s hold at Home
            self.holding_start_time = time.time()
            self.dr_state = DiscreteReachState.HOLD_STABILIZING
            self.canvas.discrete_reach_state = self.dr_state
            self.canvas.instruction_text = "Holding Home... (3s)"

        elif self.dr_state == DiscreteReachState.IN_TARGET:
            # Button released at Target -> Start 3s hold at Target
            self.holding_start_time = time.time()
            self.dr_state = DiscreteReachState.HOLD_STABILIZING
            self.canvas.discrete_reach_state = self.dr_state
            self.canvas.instruction_text = f"Holding {self.PEAK_SEQUENCE[self.current_peak_index].name}... (3s)"

    def handle_new_data(self):
        """Process new data from robot."""
        # Update canvas position
        super().handle_new_data()
        # Process state machine
        self.run_dr_state_machine()

    def save_and_close(self):
        """Save results and exit window."""
        if self.dr_data:
            filepath = self.dr_data.save_to_csv(session_subdir=self.session_subdir)
            print(f"Discrete Reaching assessment saved: {filepath}")
            # Emit completion signal
            self.assessment_finished.emit(self.movement_type)
        self.close()
