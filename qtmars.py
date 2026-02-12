"""
Module implementing a QObject for abstracting MARS which uses the qtjedi
to connect to the device, unpack data, and send/receive signals.

Author: Sivakumar Balasubramanian
Date: 17 October 2025
Email: siva82kb@gmail.com
"""

from PySide6.QtCore import QObject, Signal, QTimer
from qtjedi import JediComm
from datetime import datetime
import sys
import struct
import math
import logging
from pathlib import Path
from typing import Optional, Tuple
import random

import marsdefs as mdef

# Frame rate estimation window
FR_WINDOW_N = 100

# Arm geometry constants (in meters)
L1 = 0.475  # Upper arm length
L2 = 0.291  # Forearm length
L3 = 0.075  # Hand length
L4 = 0.0438  # Wrist length

# Arm weight constants
ARM_WEIGHT_THRESHOLD = 10.0  # Minimum valid arm weight in kg
LOW_HIGH_ARM_WEIGHT_ERROR_THRESHOLD = 0.5  # Threshold for arm weight range checking

# Frame rate thresholds
MIN_FRAMERATE_WARNING = 60  # Warn if below this
MIN_FRAMERATE_SAFETY = 20  # Disable control if below this

# Heartbeat interval (in milliseconds)
HEARTBEAT_INTERVAL_MS = 5000  # Send heartbeat every 2 seconds (firmware expects within 5 seconds)

class QtMars(QObject):
    """
    Class to handle MARS IO operations.
    """
    newdata = Signal()
    btnpressed = Signal()
    btnreleased = Signal()
    controlmodechanged = Signal()
    armweightinoutofrange = Signal()

    def __init__(self, port: str | None = None, baudrate: int = 115200, limb: str = "Right", auto_heartbeat: bool = True, log_heartbeat: bool = False) -> None:
        super().__init__()
        self.dev = JediComm(port, baudrate)
        # Upacked data from MARS with time stamp.
        self.currstatedata = []
        self.prevstatedata = []
        self._packetnumber = 0
        self._runtime = 0.0
        self._prevruntime = 0.0 
        self.currsensordata = []
        # Other variables.
        self._preverrstatus = 0
        self._currerrstatus = 0
        # framerate related stuff
        self._currt = None
        self._prevt = None
        self._deltimes = []
        self._framerate = 0.0
        # Version and device name
        self._version = ""
        self._devname = ""
        self._compliedate = ""
        # Object simulator params
        self._objparams = {}
        # Limb being used with Mars
        self._limb = limb
        # Arm weight management
        self._arm_weight_low = 0.0
        self._arm_weight_high = 0.0
        self._is_arm_weight_out_of_range = False
        # Logging
        self._logger = self._setup_logger()
        self._has_error_logged_once = False
        # Heartbeat timer
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._send_heartbeat_internal)
        self._auto_heartbeat_enabled = auto_heartbeat
        self._log_heartbeat = log_heartbeat
        # Packet decoding functions.
        self._packet_type_handlers = {
            mdef.OutDataType["SENSORSTREAM"]: self._handle_stream,
            mdef.OutDataType["DIAGNOSTICS"]: self._handle_stream,
            mdef.OutDataType["VERSION"]: self._handle_version,
        }

        # Call back for newdata_signal
        self.dev.newdata_signal.connect(self._callback_newdata)

        # start the communication
        self.dev.start()

        # Send initial heartbeat immediately to clear any existing NOHEARTBEAT errors
        if self._auto_heartbeat_enabled:
            self._logger.info("Sending initial heartbeat")
            self.send_heartbeat()
            # Start automatic heartbeat timer
            self.start_heartbeat_timer()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger for MARS communication."""
        logger = logging.getLogger('QtMars')
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    @property
    def devname(self):
        return self._devname
    
    @property
    def compliedate(self):
        return self._compliedate
    
    @property
    def version(self):
        return self._version

    @property
    def systime(self):
        return self.currstatedata[0] if len(self.currstatedata) > 0 else None
    
    @property
    def status(self) -> int | None:
        return int(self.currstatedata[1]) if len(self.currstatedata) > 0 else None
    
    @property
    def datatype(self) -> int | None:
        return (self.status >> 4) if len(self.currstatedata) > 0 and self.status is not None else None

    @property
    def controltype(self) -> int | None:
        return (self.status & 0x0E) >> 1 if len(self.currstatedata) > 0 and self.status is not None else None

    @property
    def calibration(self) -> int | None:
        return self.status & 0x01 if len(self.currstatedata) > 0 and self.status is not None else None

    @property
    def error(self) -> int:
        return int(self.currstatedata[2]) if len(self.currstatedata) > 2 else 0

    @property
    def error_string(self) -> str:
        """Get human-readable error string."""
        if self.error == 0:
            return "NOERROR"
        err_str = ""
        for i in range(16):
            if (self.error & (1 << i)) != 0:
                if i < len(mdef.ErrorTypes):
                    err_name = mdef.get_name(mdef.ErrorTypes, 1 << i)
                    if err_name:
                        err_str += (" | " if err_str else "") + err_name
        return err_str if err_str else "UNKNOWN"

    @property
    def limb(self) -> int:
        """Get limb type from state data."""
        return (self.currstatedata[3] & 0x03) if len(self.currstatedata) > 3 else 0

    @property
    def button_state(self) -> int:
        """Get button state from state data."""
        return ((self.currstatedata[3] >> 4) & 0x01) if len(self.currstatedata) > 3 else 0

    @property
    def recent_command_status(self) -> int:
        """Get recent command status."""
        return (self.currstatedata[3] >> 6) if len(self.currstatedata) > 3 else 0

    @property
    def packet_number(self) -> int:
        """Get packet number."""
        return int(self.currstatedata[4]) if len(self.currstatedata) > 4 else 0

    @property
    def runtime(self) -> float:
        """Get device runtime in seconds."""
        return float(self.currstatedata[5]) if len(self.currstatedata) > 5 else 0.0

    # Sensor data properties - MARS specific
    @property
    def angle1(self) -> float:
        """Joint angle 1 in degrees."""
        return self.currsensordata[0] if len(self.currsensordata) > 0 else 0.0

    @property
    def angle2(self) -> float:
        """Joint angle 2 in degrees."""
        return self.currsensordata[1] if len(self.currsensordata) > 1 else 0.0

    @property
    def angle3(self) -> float:
        """Joint angle 3 in degrees."""
        return self.currsensordata[2] if len(self.currsensordata) > 2 else 0.0

    @property
    def angle4(self) -> float:
        """Joint angle 4 in degrees."""
        return self.currsensordata[3] if len(self.currsensordata) > 3 else 0.0

    @property
    def imu_angle1(self) -> float:
        """IMU angle 1 in degrees."""
        return self.currsensordata[4] if len(self.currsensordata) > 4 else 0.0

    @property
    def imu_angle2(self) -> float:
        """IMU angle 2 in degrees."""
        return self.currsensordata[5] if len(self.currsensordata) > 5 else 0.0

    @property
    def imu_angle3(self) -> float:
        """IMU angle 3 in degrees."""
        return self.currsensordata[6] if len(self.currsensordata) > 6 else 0.0

    @property
    def imu_angle4(self) -> float:
        """IMU angle 4 in degrees."""
        return self.currsensordata[7] if len(self.currsensordata) > 7 else 0.0

    @property
    def force(self) -> float:
        """Force sensor reading in kg."""
        return self.currsensordata[8] if len(self.currsensordata) > 8 else 0.0

    @property
    def target(self) -> float:
        """Control target value."""
        return self.currsensordata[9] if len(self.currsensordata) > 9 else 0.0

    @property
    def desired(self) -> float:
        """Desired control value."""
        return self.currsensordata[10] if len(self.currsensordata) > 10 else 0.0

    @property
    def control(self) -> float:
        """Control output value."""
        return self.currsensordata[11] if len(self.currsensordata) > 11 else 0.0

    @property
    def err_p(self) -> float:
        """Proportional error term."""
        return self.currsensordata[12] if len(self.currsensordata) > 12 else 0.0

    @property
    def err_d(self) -> float:
        """Derivative error term."""
        return self.currsensordata[13] if len(self.currsensordata) > 13 else 0.0

    @property
    def err_i(self) -> float:
        """Integral error term."""
        return self.currsensordata[14] if len(self.currsensordata) > 14 else 0.0

    @property
    def gravity_compensation_torque(self) -> float:
        """Gravity compensation torque."""
        return self.currsensordata[15] if len(self.currsensordata) > 15 else 0.0

    @property
    def angular_velocity1(self) -> float:
        """Angular velocity of joint 1."""
        return self.currsensordata[16] if len(self.currsensordata) > 16 else 0.0

    # Arm weight properties
    @property
    def arm_weight_low(self) -> float:
        """Lower bound of arm weight range in kg."""
        return self._arm_weight_low

    @property
    def arm_weight_high(self) -> float:
        """Upper bound of arm weight range in kg."""
        return self._arm_weight_high

    @property
    def is_arm_weight_set(self) -> bool:
        """Check if arm weight range is properly set."""
        return (self._arm_weight_low > ARM_WEIGHT_THRESHOLD and
                self._arm_weight_high > ARM_WEIGHT_THRESHOLD and
                (self._arm_weight_high - self._arm_weight_low) > 0)

    @property
    def is_arm_weight_out_of_range(self) -> bool:
        """Check if current force is outside arm weight range."""
        return self._is_arm_weight_out_of_range

    @property
    def framerate(self) -> float:
        """Get current frame rate in Hz."""
        return self._framerate

    @property
    def ep_pos(self) -> Tuple[float, float, float]:
        """Get endpoint position in 3D space using forward kinematics."""
        return self.forward_kinematics(self.angle1, self.angle2, self.angle3)

    @property
    def ep_pos_in_plane(self) -> Tuple[float, float, float]:
        """Get endpoint position in the movement plane using forward kinematics."""
        return self.forward_kinematics_in_plane(self.angle2, self.angle3)

    @property
    def is_heartbeat_active(self) -> bool:
        """Check if automatic heartbeat timer is active."""
        return self._heartbeat_timer.isActive()

    def is_connected(self):
        return self.dev.is_open()

    def is_data_available(self):
        return len(self.currstatedata) != 0

    def forward_kinematics(self, theta1: float, theta2: float, theta3: float) -> Tuple[float, float, float]:
        """
        Compute 3D endpoint position from joint angles using forward kinematics.

        Args:
            theta1: Joint angle 1 in degrees
            theta2: Joint angle 2 in degrees
            theta3: Joint angle 3 in degrees

        Returns:
            Tuple of (x, y, z) position in meters
        """
        # Convert to radians
        theta1_rad = math.radians(theta1)
        theta2_rad = math.radians(theta2)
        theta3_rad = math.radians(theta3)

        # Calculate intermediate term
        temp = L1 * math.cos(theta2_rad) + L2 * math.cos(theta2_rad + theta3_rad)

        # Calculate x, y, z
        x = math.cos(theta1_rad) * temp
        y = math.sin(theta1_rad) * temp
        z = -L1 * math.sin(theta2_rad) - L2 * math.sin(theta2_rad + theta3_rad)

        return (x, y, z)

    def forward_kinematics_in_plane(self, theta2: float, theta3: float) -> Tuple[float, float, float]:
        """
        Compute endpoint position in the movement plane using forward kinematics.

        Args:
            theta2: Joint angle 2 in degrees
            theta3: Joint angle 3 in degrees

        Returns:
            Tuple of (x, y, z) position in meters (x=0 for planar movement)
        """
        # Convert to radians
        theta2_rad = math.radians(theta2)
        theta3_rad = math.radians(theta3)

        # Calculate intermediate term
        temp = L1 * math.cos(theta2_rad) + L2 * math.cos(theta2_rad + theta3_rad)

        # Calculate x, y, z (x is always 0 for planar)
        x = 0.0
        y = temp
        z = -L1 * math.sin(theta2_rad) - L2 * math.sin(theta2_rad + theta3_rad)

        return (x, y, z)

    def forward_kinematics_extended(self, theta1: float, theta2: float,
                                   theta3: float, theta4: float) -> Tuple[float, float, float]:
        """
        Compute 3D endpoint position including wrist joint using forward kinematics.

        Args:
            theta1: Joint angle 1 in degrees
            theta2: Joint angle 2 in degrees
            theta3: Joint angle 3 in degrees
            theta4: Joint angle 4 (wrist) in degrees

        Returns:
            Tuple of (x, y, z) position in meters
        """
        # Convert to radians
        theta1_rad = math.radians(theta1)
        theta2_rad = math.radians(theta2)
        theta3_rad = math.radians(theta3)
        theta4_rad = math.radians(theta4)

        # Calculate intermediate term
        temp = (L1 * math.cos(theta2_rad) +
                L2 * math.cos(theta2_rad + theta3_rad) +
                L3 * math.cos(theta2_rad + theta3_rad + theta4_rad) -
                L4 * math.sin(theta2_rad + theta3_rad + theta4_rad))

        # Calculate x, y, z
        x = math.cos(theta1_rad) * temp
        y = math.sin(theta1_rad) * temp
        z = (-L1 * math.sin(theta2_rad) -
             L2 * math.sin(theta2_rad + theta3_rad) -
             L3 * math.sin(theta2_rad + theta3_rad + theta4_rad) -
             L4 * math.cos(theta2_rad + theta3_rad + theta4_rad))

        return (x, y, z)

    def set_arm_weight_range(self, low: float, high: float) -> bool:
        """
        Set the arm weight range for monitoring.

        Args:
            low: Lower bound of arm weight in kg
            high: Upper bound of arm weight in kg

        Returns:
            True if range was set successfully, False otherwise
        """
        if (low > ARM_WEIGHT_THRESHOLD and
            high > ARM_WEIGHT_THRESHOLD and
            (high - low) > 0):
            self._arm_weight_low = low
            self._arm_weight_high = high
            self._logger.info(f"Arm weight range set to [{low:.2f}, {high:.2f}] kg")
            return True
        else:
            self._logger.warning(f"Invalid arm weight range [{low:.2f}, {high:.2f}] kg")
            return False

    def _callback_newdata(self, newdata: list[int]):
        """
        Handles newdata packect recevied through the COM port.
        """
        # print(newdata[:20])
        # Store previous data
        self.prevstatedata = self.currstatedata
        
        # Unpack and update current data
        # System time - 0
        self.currstatedata: list[str | int | float] = [datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')]
        # status - 1
        self.currstatedata.append(newdata[0])
        # error - 2
        self.currstatedata.append(255 * newdata[2] + newdata[1])
        # actuated - 3
        self.currstatedata.append(newdata[3])
        
        # Decode according to the datatype.
        if self.datatype in self._packet_type_handlers:
            self._packet_type_handlers[self.datatype](newdata)
    
    def _handle_stream(self, newdata: list[int]):
        """
        Function to handle SENSORSTREAM and DIAGNOSTICS data.
        """
        # Packet number - 4
        self.currstatedata.append(255 * newdata[5] + newdata[4])

        # Run time - 5
        self._prevruntime = self._runtime
        self._runtime = 1e-3 * struct.unpack('L', bytes(newdata[6:10]))[0]
        self.currstatedata.append(self._runtime)

        # Robot sensor data. This depends on the datatype.
        _outDataTypeName = mdef.get_name(mdef.OutDataType, self.datatype) if self.datatype is not None else None
        N = mdef.MarsSensorDataNumber[_outDataTypeName] if _outDataTypeName is not None else 0

        # Mars sensor data
        self.currsensordata : list[float] = [
            struct.unpack('f', bytes(newdata[i:i+4]))[0]
            for i in range(10, 10 + N * 4, 4)
        ]

        # Update frame rate calculation
        if self._prevruntime > 0:
            time_diff = self._runtime - self._prevruntime
            if time_diff > 0:
                self._framerate = 1.0 / time_diff

        # Error handling
        if self.error != 0:
            # Log error with probabilistic reduction to avoid flooding
            if self._preverrstatus != self.error or random.randint(1, 100) <= 5:
                self._logger.error(f"Error: {self.error_string} ({self.error}) | Time: {self._runtime:.2f}")
        else:
            # Log when error is resolved
            if self._preverrstatus != 0:
                self._logger.info(f"Error Resolved | Previous Error: {self.error_string} | Time: {self._runtime:.2f}")

        self._preverrstatus = self.error
        self._logger.info(f"Frame Rate: {self._framerate:.1f}Hz | Time: {self._runtime:.2f}")
        # Frame rate warning
        if self._framerate < MIN_FRAMERATE_WARNING and self._framerate > 0:
            self._logger.warning(f"Frame Rate Low | Frame Rate: {self._framerate:.1f}Hz | Time: {self._runtime:.2f}")

            # Safety: disable control if frame rate too low
            if self._framerate < MIN_FRAMERATE_SAFETY:
                if self.controltype != mdef.ControlTypes.get("NONE", 0):
                    self._logger.info("Frame rate too low. Setting control to NONE.")
                    self.set_control_type("NONE")

        # Check button state changes
        if len(self.prevstatedata) > 3:
            prev_button = ((self.prevstatedata[3] >> 4) & 0x01) if isinstance(self.prevstatedata[3], int) else 0
            curr_button = self.button_state

            if prev_button == 0 and curr_button == 1:
                self._logger.info(f"MARS Button Released | Time: {self._runtime:.2f}")
                self.btnreleased.emit()
            elif prev_button == 1 and curr_button == 0:
                self.btnpressed.emit()

        # Check control mode changes
        if len(self.prevstatedata) > 1:
            prev_ctrl = ((self.prevstatedata[1] & 0x0E) >> 1) if isinstance(self.prevstatedata[1], int) else 0
            if prev_ctrl != self.controltype:
                self._logger.info(f"Control Mode Changed | ControlType: {self.controltype} | Time: {self._runtime:.2f}")
                self.controlmodechanged.emit()

        # Check arm weight range
        if self.is_arm_weight_set:
            band = LOW_HIGH_ARM_WEIGHT_ERROR_THRESHOLD * (self._arm_weight_high - self._arm_weight_low)
            if self.force < self._arm_weight_low - band or self.force > self._arm_weight_high + band:
                if not self._is_arm_weight_out_of_range:
                    self._logger.warning(
                        f"Arm Weight Out of Range | Force: {self.force:.2f} kg | "
                        f"Arm Weight Range: [{self._arm_weight_low:.2f}, {self._arm_weight_high:.2f}] kg | "
                        f"Time: {self._runtime:.2f}"
                    )
                    self.armweightinoutofrange.emit()
                self._is_arm_weight_out_of_range = True
            else:
                if self._is_arm_weight_out_of_range:
                    self._logger.info(
                        f"Arm Weight Back in Range | Force: {self.force:.2f} kg | "
                        f"Arm Weight Range: [{self._arm_weight_low:.2f}, {self._arm_weight_high:.2f}] kg | "
                        f"Time: {self._runtime:.2f}"
                    )
                    self.armweightinoutofrange.emit()
                self._is_arm_weight_out_of_range = False

        # Emit newdata signal for other listeners
        self.newdata.emit()
    
    def _handle_version(self, newdata: list[int]):
        """
        Function to handle VERSION data.
        """
        # Parse version string from payload
        version_str = bytes(newdata[4:]).decode('ascii', errors='ignore').rstrip('\x00')
        parts = version_str.split(",")
        if len(parts) >= 3:
            self._devname = parts[0]
            self._version = parts[1]
            self._compliedate = parts[2]
            self._logger.info(f"Received Version | Version: {self._version} | Compile Date: {self._compliedate} | Device ID: {self._devname}")
    
    def start_heartbeat_timer(self):
        """Start the automatic heartbeat timer."""
        if not self._heartbeat_timer.isActive():
            self._heartbeat_timer.start(HEARTBEAT_INTERVAL_MS)
            self._logger.info(f"Heartbeat timer started (interval: {HEARTBEAT_INTERVAL_MS}ms)")

    def stop_heartbeat_timer(self):
        """Stop the automatic heartbeat timer."""
        if self._heartbeat_timer.isActive():
            self._heartbeat_timer.stop()
            self._logger.info("Heartbeat timer stopped")

    def _send_heartbeat_internal(self):
        """Internal method called by timer to send heartbeat."""
        if self.is_connected():
            self.send_heartbeat()
        else:
            self._logger.warning("Heartbeat timer fired but device not connected")

    def close(self):
        """Close the connection to the device."""
        # Stop heartbeat timer first
        self.stop_heartbeat_timer()

        if self.dev is not None and self.dev.isRunning():
            self.dev.abort()
            self.dev.quit()
            self.dev.wait()
            self._logger.info("Connection closed")

    def calibrate(self):
        """Calibrate the MARS device encoders."""
        if not self.is_connected():
            self._logger.warning("Cannot calibrate: not connected")
            return
        self._logger.info("Calibrating")
        _payload = [mdef.InDataType["CALIBRATE"]]
        self.dev.send_message(_payload)

    def set_control_type(self, control: str):
        """
        Set the control type for the device.

        Args:
            control: Control type name ("NONE", "POSITION", etc.)
        """
        if not self.is_connected():
            self._logger.warning(f"Cannot set control type: not connected")
            return

        if control not in mdef.ControlTypes:
            self._logger.warning(f"Invalid control type: {control}")
            return

        self._logger.info(f"Setting Control Type: {control}")
        _payload = [mdef.InDataType["SET_CONTROL_TYPE"], mdef.ControlTypes[control]]
        self.dev.send_message(_payload)

    def set_control_target(self, target: float, dur: float = 6.0):
        """
        Set the control target position.

        Args:
            target: Target value
            dur: Duration for movement in seconds (default: 6.0)
        """
        if not self.is_connected():
            self._logger.warning("Cannot set control target: not connected")
            return

        if self.controltype == mdef.ControlTypes.get("NONE", 0):
            self._logger.warning("Cannot set target: control type is NONE")
            return

        self._logger.info(f"Setting Control Target: {target}")

        # Determine start position based on control type
        if self.controltype == mdef.ControlTypes.get("POSITION", 0):
            target0 = self.angle1 if self.target == mdef.INVALID_TARGET else self.target
        else:
            target0 = 1.0 if self.target == mdef.INVALID_TARGET else self.target

        t0 = 0.0

        # Build payload with floats
        _payload = [mdef.InDataType["SET_CONTROL_TARGET"]]
        _payload += list(struct.pack('<f', target0))  # Little-endian float
        _payload += list(struct.pack('<f', t0))
        _payload += list(struct.pack('<f', target))
        _payload += list(struct.pack('<f', dur))
        self.dev.send_message(_payload)

    def set_limb(self, limb: str):
        """
        Set the limb type for the device.

        Args:
            limb: Limb name ("RIGHT", "LEFT", "NOLIMB")
        """
        if not self.is_connected():
            self._logger.warning("Cannot set limb: not connected")
            return

        if limb not in mdef.LimbType:
            self._logger.warning(f"Invalid limb type: {limb}")
            return

        self._logger.info(f"Setting Limb: {limb}")
        _payload = [mdef.InDataType["SET_LIMB"], mdef.LimbType[limb]]
        self.dev.send_message(_payload)

    def set_diagnostic_mode(self):
        """Set the device to diagnostics mode."""
        if not self.is_connected():
            self._logger.warning("Cannot set diagnostic mode: not connected")
            return
        self._logger.info("Setting Diagnostic Mode")
        _payload = [mdef.InDataType["SET_DIAGNOSTICS"]]
        self.dev.send_message(_payload)

    def reset_packet_number(self):
        """Reset the packet number counter."""
        if not self.is_connected():
            self._logger.warning("Cannot reset packet number: not connected")
            return
        self._logger.info("Resetting Packet Number")
        _payload = [mdef.InDataType["RESET_PACKETNO"]]
        self.dev.send_message(_payload)

    def start_sensorstream(self):
        """Start sensor stream from the device."""
        if not self.is_connected():
            self._logger.warning("Cannot start sensor stream: not connected")
            return
        self._logger.info("Starting Sensor Stream")
        _payload = [mdef.InDataType["START_STREAM"]]
        self.dev.send_message(_payload)

    def stop_sensorstream(self):
        """Stop sensor stream from the device."""
        if not self.is_connected():
            self._logger.warning("Cannot stop sensor stream: not connected")
            return
        self._logger.info("Stopping Sensor Stream")
        _payload = [mdef.InDataType["STOP_STREAM"]]
        self.dev.send_message(_payload)

    def get_version(self):
        """Request version information from the device."""
        if not self.is_connected():
            self._logger.warning("Cannot get version: not connected")
            return
        self._logger.info("Getting Version")
        _payload = [mdef.InDataType["GET_VERSION"]]
        self.dev.send_message(_payload)

    def send_heartbeat(self):
        """Send a heartbeat signal to the device to maintain connection."""
        if not self.is_connected():
            self._logger.warning("Cannot send heartbeat: not connected")
            return
        _payload = [mdef.InDataType["HEARTBEAT"]]
        self.dev.send_message(_payload)
        if self._log_heartbeat:
            self._logger.info(f"Heartbeat sent | Time: {self._runtime:.2f}s")


class RecursiveLeastSquares:
    """
    Recursive Least Squares parameter estimator.

    This class implements online parameter estimation using the RLS algorithm,
    useful for adaptive control and system identification.
    """

    def __init__(self, n: int):
        """
        Initialize RLS estimator.

        Args:
            n: Number of parameters to estimate
        """
        self.n = n
        self.theta = [0.0] * n  # Parameter estimates
        self.P = [[0.0] * n for _ in range(n)]  # Covariance matrix
        self.K = [0.0] * n  # Kalman gain
        self.lambda_factor = 1.0  # Forgetting factor
        self.i = 0  # Update counter
        self.reset_estimator()

    def reset_estimator(self):
        """Reset the estimator to initial conditions."""
        self.i = 0
        # Initialize P to identity matrix
        for row in range(self.n):
            for col in range(self.n):
                self.P[row][col] = 1.0 if row == col else 0.0
            self.theta[row] = 0.0

    def update(self, x: list[float], y: float):
        """
        Update parameter estimates with new measurement.

        Args:
            x: Feature vector (regressor)
            y: Measurement (output)
        """
        # Compute the Kalman gain
        self._update_kalman_gain(x)

        # Compute the prediction error
        error = y - self._inner_product(self.theta, x)

        # Update the parameter estimates
        for row in range(self.n):
            self.theta[row] += self.K[row] * error

        # Update the covariance matrix P
        P_adjust = self._matrix_multiply(
            self._outer_product(self.K, x),
            self.P
        )
        for row in range(self.n):
            for col in range(self.n):
                self.P[row][col] -= P_adjust[row][col] / self.lambda_factor

        # Increment counter
        self.i += 1

    def _update_kalman_gain(self, x: list[float]):
        """Update Kalman gain vector."""
        self.K = self._matrix_vector_multiply(self.P, x)
        denom = 1.0 + self._inner_product(x, self.K)
        # Update the Kalman gain
        for row in range(self.n):
            self.K[row] /= denom

    @staticmethod
    def _inner_product(a: list[float], b: list[float]) -> float:
        """Compute inner product of two vectors."""
        return sum(a[i] * b[i] for i in range(len(a)))

    @staticmethod
    def _outer_product(a: list[float], b: list[float]) -> list[list[float]]:
        """Compute outer product of two vectors."""
        return [[a[i] * b[j] for j in range(len(b))] for i in range(len(a))]

    @staticmethod
    def _matrix_multiply(A: list[list[float]], B: list[list[float]]) -> list[list[float]]:
        """Multiply two matrices."""
        rows_A = len(A)
        cols_A = len(A[0])
        rows_B = len(B)
        cols_B = len(B[0])

        if cols_A != rows_B:
            raise ValueError("Matrix dimensions do not match for multiplication")

        result = [[0.0] * cols_B for _ in range(rows_A)]
        for i in range(rows_A):
            for j in range(cols_B):
                for k in range(cols_A):
                    result[i][j] += A[i][k] * B[k][j]
        return result

    @staticmethod
    def _matrix_vector_multiply(A: list[list[float]], b: list[float]) -> list[float]:
        """Post-multiply a matrix with a vector."""
        rows_A = len(A)
        cols_A = len(A[0])

        if cols_A != len(b):
            raise ValueError("Incompatible matrix and vector dimensions")

        result = [0.0] * rows_A
        for i in range(rows_A):
            for j in range(cols_A):
                result[i] += A[i][j] * b[j]
        return result


if __name__ == "__main__":
    import sys
    import signal
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from qtjedi import JediComm

    app = QApplication(sys.argv)
    # Initialize with automatic heartbeat enabled and logging enabled for testing
    mars = QtMars(port="COM4", auto_heartbeat=True, log_heartbeat=True)

    # Setup signal handler for Ctrl+C
    def signal_handler(_sig, _frame):
        print("\nKeyboard interrupt received. Cleaning up...")
        mars.stop_sensorstream()
        mars.close()
        app.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Create a timer to allow Python to process signals
    # This makes Ctrl+C work properly with Qt event loop
    timer = QTimer()
    timer.timeout.connect(lambda: None)  # Wake up Python interpreter
    timer.start(500)  # Check every 500ms

    mars.stop_sensorstream()
    mars.get_version()
    print(mars.angle1)

    # Note: No need to manually call send_heartbeat() anymore!
    # The automatic heartbeat timer is already running

    mars.start_sensorstream()

    print("MARS device running with automatic heartbeat...")
    print(f"Heartbeat active: {mars.is_heartbeat_active}")
    print("Press Ctrl+C to stop...")
    app.exec()
