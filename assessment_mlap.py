"""
Combined MLAP (Medio-Lateral + Anterior-Posterior) workspace assessment window.

Assesses full 2D workspace envelope.

Author: Sivakumar Balasubramanian
Date: 09 February 2026
Email: siva82kb@gmail.com
"""

from assessment_base import BaseAssessmentWindow


class AssessmentMLAPWindow(BaseAssessmentWindow):
    """MLAP (Combined ML+AP) assessment window."""

    @property
    def movement_type(self) -> str:
        """Assessment type."""
        return "MLAP"

    def __init__(self, mars, parent=None):
        super().__init__(mars, parent)
        # Configure canvas for MLAP-specific visualization
        self.canvas.instruction_text = "MLAP Assessment: Press robot button to begin"
