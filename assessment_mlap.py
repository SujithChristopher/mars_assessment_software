"""
Combined MLAP (Medio-Lateral + Anterior-Posterior) workspace assessment window.

Assesses full 2D workspace envelope.
Standalone Arm Weight assessment is now a separate task.

Author: Sivakumar Balasubramanian
Date: 11 February 2026 (Refactored 03 March 2026)
Email: siva82kb@gmail.com
"""

from assessment_base import BaseAssessmentWindow, AromAssessState


class AssessmentMLAPWindow(BaseAssessmentWindow):
    """MLAP (Combined ML+AP) assessment window."""

    @property
    def movement_type(self) -> str:
        """Assessment type."""
        return "MLAP"

    def __init__(self, mars, patient_id=None, time_point="A0", is_demo=False, session_subdir=None, parent=None):
        super().__init__(mars, patient_id, time_point, is_demo, session_subdir, parent)
        # Configure canvas for MLAP-specific visualization
        self.canvas.instruction_text = "MLAP Assessment: Press robot button to begin"

    def save_assessment(self):
        """Save AROM assessment and close."""
        if self.current_arom is None:
            return

        # Save AROM data to CSV
        filepath = self.current_arom.save_to_csv(session_subdir=self.session_subdir)
        print(f"Saved MLAP assessment to: {filepath}")

        # Update state to DONE
        self.state = AromAssessState.DONE

        # Emit completion signal
        self.assessment_finished.emit(self.movement_type)

        # Close window
        self.close()

    def handle_button_release(self):
        """Handle device button release - inherited behavior for AROM."""
        super().handle_button_release()

    def handle_new_data(self):
        """Handle new data from MARS device - inherited behavior for AROM."""
        super().handle_new_data()
