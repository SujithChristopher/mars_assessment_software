"""
Medio-Lateral (ML) workspace assessment window.

Assesses side-to-side movement capability.

Author: Sivakumar Balasubramanian
Date: 09 February 2026
Email: siva82kb@gmail.com
"""

from assessment_base import BaseAssessmentWindow


class AssessmentMLWindow(BaseAssessmentWindow):
    """ML (Medio-Lateral) assessment window."""

    @property
    def movement_type(self) -> str:
        """Assessment type."""
        return "ML"

    def __init__(self, mars, patient_id=None, time_point="A0", is_demo=False, session_subdir=None, parent=None, limb="RIGHT"):
        super().__init__(mars, patient_id, time_point, is_demo, session_subdir, parent, limb)
        # Configure canvas for ML-specific visualization
        self.canvas.instruction_text = "ML Assessment: Press robot button to begin"
