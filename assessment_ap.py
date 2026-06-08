"""
Anterior-Posterior (AP) workspace assessment window.

Assesses forward/backward movement capability.

Author: Sivakumar Balasubramanian
Date: 09 February 2026
Email: siva82kb@gmail.com
"""

from assessment_base import BaseAssessmentWindow


class AssessmentAPWindow(BaseAssessmentWindow):
    """AP (Anterior-Posterior) assessment window."""

    @property
    def movement_type(self) -> str:
        """Assessment type."""
        return "AP"

    def __init__(self, mars, patient_id=None, time_point="A0", is_demo=False, session_subdir=None, parent=None, limb="RIGHT"):
        super().__init__(mars, patient_id, time_point, is_demo, session_subdir, parent, limb)
        # Configure canvas for AP-specific visualization
        self.canvas.instruction_text = "AP Assessment: Press robot button to begin"
