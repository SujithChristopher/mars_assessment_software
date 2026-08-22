"""Tests for calibration failure guidance."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import marsdefs as mdef
from calibration_messages import (
    IMU_ANGLE_4_CALIBRATION_MESSAGE,
    calibration_failure_message,
    has_imu_angle_4_calibration_error,
)
from mars_assessment import MarsAssessmentLauncher


class CalibrationMessageTests(unittest.TestCase):
    def test_imu_angle_4_outside_limit_gets_orientation_guidance(self):
        for angle in (mdef.CALIB_ANGLE_LIMIT + 0.1, -mdef.CALIB_ANGLE_LIMIT - 0.1):
            with self.subTest(angle=angle):
                mars = SimpleNamespace(imu_angle4=angle)
                self.assertTrue(has_imu_angle_4_calibration_error(mars))
                self.assertEqual(
                    calibration_failure_message(mars, "generic"),
                    IMU_ANGLE_4_CALIBRATION_MESSAGE,
                )

    def test_other_calibration_failure_keeps_generic_message(self):
        mars = SimpleNamespace(imu_angle4=mdef.CALIB_ANGLE_LIMIT)
        self.assertFalse(has_imu_angle_4_calibration_error(mars))
        self.assertEqual(calibration_failure_message(mars, "generic"), "generic")

    def test_launcher_displays_special_message_for_failed_angle_4_calibration(self):
        mars = SimpleNamespace(
            calibration=0,
            imu_angle4=mdef.CALIB_ANGLE_LIMIT + 1,
            is_connected=lambda: True,
        )
        status_label = Mock()
        launcher = SimpleNamespace(mars=mars, calib_status_label=status_label)

        MarsAssessmentLauncher._check_calibration_success(launcher)

        status_label.setText.assert_called_once_with(
            IMU_ANGLE_4_CALIBRATION_MESSAGE
        )


if __name__ == "__main__":
    unittest.main()
