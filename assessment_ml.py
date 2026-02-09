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

    def __init__(self, mars, parent=None):
        super().__init__(mars, parent)
        # Configure canvas for ML-specific visualization
        self.canvas.instruction_text = "ML Assessment: Press 'Start Assessment' to begin"
