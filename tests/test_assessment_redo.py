"""Regression tests for the assessment-window Redo action."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from arm_weight_data import ArmWeightState, ArmWeightTarget
from assessment_ap import AssessmentAPWindow
from assessment_armweight import AssessmentArmWeightWindow
from assessment_base import AromAssessState
from assessment_discreach import AssessmentDiscreteReachWindow, DiscreteReachState
from assessment_ml import AssessmentMLWindow
from assessment_mlap import AssessmentMLAPWindow
from discrete_reach_data import DiscreteReachTarget
from mars_arom_data import MarsArom


class AssessmentRedoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.mlap_arom = SimpleNamespace(
            average_top=(0.0, 1.0),
            average_right=(1.0, 0.0),
            average_bottom=(0.0, -1.0),
            average_left=(-1.0, 0.0),
            adjusted_top=None,
            adjusted_right=None,
            adjusted_bottom=None,
            adjusted_left=None,
        )

    def test_workspace_redo_clears_unsaved_result(self):
        for window_class in (
            AssessmentAPWindow,
            AssessmentMLWindow,
            AssessmentMLAPWindow,
        ):
            with self.subTest(window=window_class.__name__):
                with patch.object(MarsArom, "find_latest_assessment", return_value=None):
                    window = window_class(None)

                try:
                    window.current_arom = Mock()
                    window.canvas.current_arom = window.current_arom
                    window.state = AromAssessState.ASSESSROM
                    window.current_trial = window.max_trials
                    window.stop_assessment()

                    self.assertFalse(window.redo_btn.isHidden())
                    self.assertFalse(window.save_btn.isHidden())

                    window.redo_btn.click()

                    self.assertEqual(window.state, AromAssessState.INIT)
                    self.assertIsNone(window.current_arom)
                    self.assertTrue(window.redo_btn.isHidden())
                    self.assertTrue(window.save_btn.isHidden())
                    self.assertTrue(window.start_btn.isHidden())
                finally:
                    window.close()

    def test_arm_weight_redo_replaces_collected_data(self):
        with patch.object(MarsArom, "find_latest_assessment", return_value=self.mlap_arom):
            window = AssessmentArmWeightWindow(None)

        try:
            old_data = window.arm_weight_data
            window.current_target_index = len(window.TARGET_SEQUENCE) - 1
            window.move_to_next_target()

            self.assertEqual(window.arm_weight_state, ArmWeightState.ALL_DONE)
            self.assertFalse(window.redo_btn.isHidden())

            window.redo_btn.click()

            self.assertIsNot(window.arm_weight_data, old_data)
            self.assertEqual(window.arm_weight_state, ArmWeightState.INIT)
            self.assertEqual(window.current_target, ArmWeightTarget.NONE)
            self.assertEqual(window.canvas.completed_targets, set())
            self.assertTrue(window.redo_btn.isHidden())
            self.assertTrue(window.save_btn.isHidden())
        finally:
            window.close()

    def test_discrete_reach_redo_replaces_collected_data(self):
        with patch.object(MarsArom, "find_latest_assessment", return_value=self.mlap_arom):
            window = AssessmentDiscreteReachWindow(None)

        try:
            old_data = window.dr_data
            window.dr_state = DiscreteReachState.ALL_DONE
            window.redo_btn.show()
            window.save_btn.show()

            window.redo_btn.click()

            self.assertIsNot(window.dr_data, old_data)
            self.assertEqual(window.state, AromAssessState.INIT)
            self.assertEqual(window.dr_state, DiscreteReachState.INACTIVE)
            self.assertEqual(
                window.canvas.current_discrete_reach_target,
                DiscreteReachTarget.NONE,
            )
            self.assertEqual(window.canvas.completed_discrete_targets, set())
            self.assertEqual(window.target_trial_counts[DiscreteReachTarget.TOP], 0)
            self.assertTrue(window.redo_btn.isHidden())
            self.assertTrue(window.save_btn.isHidden())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
