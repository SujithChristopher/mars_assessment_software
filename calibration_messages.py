"""User-facing guidance for MARS calibration failures."""

import marsdefs as mdef


IMU_ANGLE_4_CALIBRATION_MESSAGE = (
    "Calibration error: Check the end-effector orientation. Ensure the laser is pointing toward "
    "the ground. If the issue persists, contact an engineer."
)


def has_imu_angle_4_calibration_error(mars) -> bool:
    """Return whether IMU Angle 4 is outside the calibration limit."""
    try:
        return abs(float(mars.imu_angle4)) > mdef.CALIB_ANGLE_LIMIT
    except (AttributeError, TypeError, ValueError):
        return False


def calibration_failure_message(mars, default: str) -> str:
    """Return special IMU Angle 4 guidance or the caller's default text."""
    if has_imu_angle_4_calibration_error(mars):
        return IMU_ANGLE_4_CALIBRATION_MESSAGE
    return default
