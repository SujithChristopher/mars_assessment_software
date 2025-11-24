"""
Module containing definitions of different MARS related variables.

Author: Sivakumar Balasubramanian
Date: 17 October 2025
Email: siva82kb@gmail.com
"""

from enum import Enum


class PlutoEvents(Enum):
    PRESSED = 0
    RELEASED = 1
    NEWDATA = 2

LimbType = {
    "NOLIMB":   0x00,
    "RIGHT":    0x01,
    "LEFT":     0x02,
}

ControlTypes = {
    "NONE":             0x00,
    "POSITION":         0x01,
}

OutDataType = {
    "VERSION":      0x00,
    "SENSORSTREAM": 0x01,
    "CONTROLPARAM": 0x02,
    "DIAGNOSTICS":  0x03
}

InDataType = {
    "GET_VERSION":          0x00,
    "RESET_PACKETNO":       0x01,
    "SET_LIMB":             0x02,
    "CALIBRATE":            0x03,
    "START_STREAM":         0x04,
    "STOP_STREAM":          0x05,
    "SET_CONTROL_TYPE":     0x06,
    "SET_CONTROL_TARGET":   0x07,
    "SET_DIAGNOSTICS":      0x08,
    "HEARTBEAT":            0x80,
}

ErrorTypes = {
    "NOHEARTBEAT":          0x0001,
    "ANG1MISMATCHERR":      0x0002,
    "ANG234MISMATCHERR":    0x0004,
    "ANG1JUMPERR":          0x0008,
    "ANG234JUMPERR":        0x0010,
    "ANG1LIMITERR":         0x0020,
    "ANG234LIMITERR":       0x0040
}

MovementTypes = [
    "MEDICAL-LATERAL",
    "ANTERIOR-POSTERIOR",
    "COMBINED"
]

OperationStatus = {
    "NOERR":  0x00,
    "YESERR": 0x01,
}

CommandStatus = {
    "NONE":     0x00,
    "SUCCESS":  0x01,
    "FAIL":     0x02,
}

CalibrationStatus = {
    "NOCALIB":  0x00,
    "YESCALIB": 0x01,
}

MarsSensorDataNumber = {
    "DUMMY":        0,
    "SENSORSTREAM": 12,
    "CONTROLPARAM": 8,
    "DIAGNOSTICS":  17
}

INVALID_TARGET = 999.0
CALIB_ANGLE_LIMIT = 50.0


def get_name(def_dict: dict[str, int], code: int) -> str | None:
    """Gets the name corresponding to the given code from the definition  dictionary.
    """
    for name, value in def_dict.items():
        if value == code:
            return name
    return None
