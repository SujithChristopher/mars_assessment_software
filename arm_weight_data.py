"""
Data model for MARS Arm Weight assessment.

Collects force data at 5 target positions (4 corners + center of MLAP workspace)
to estimate arm weight characteristics.

Author: Sivakumar Balasubramanian
Date: 11 February 2026
Email: siva82kb@gmail.com
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from enum import Enum


class ArmWeightTarget(Enum):
    """Target positions for arm weight assessment."""
    NONE = 0
    TOP = 1
    RIGHT = 2
    BOTTOM = 3
    LEFT = 4
    CENTER = 5


class ArmWeightState(Enum):
    """Arm weight assessment state machine."""
    INACTIVE = 0
    INIT = 1
    MOVING_TO_TARGET = 2
    IN_TARGET = 3
    RECORDING = 4
    TARGET_COMPLETE = 5
    ALL_DONE = 6


class ArmWeightData:
    """Data model for arm weight assessment.

    Collects endpoint position and force data at 5 workspace positions
    to characterize arm weight support needs.
    """

    def __init__(self, patient_id: str = None, time_point: str = "A0", is_demo: bool = False):
        """Initialize arm weight assessment.
        
        Args:
            patient_id: Homer ID of the patient
            time_point: Time point (A0, A1, A2)
            is_demo: Whether this is a demo session
        """
        self.patient_id = patient_id
        self.time_point = time_point
        self.is_demo = is_demo
        self.timestamp = None

        # Target positions (y, z) in meters - set from MLAP assessment
        self.target_positions = {
            ArmWeightTarget.TOP: None,
            ArmWeightTarget.RIGHT: None,
            ArmWeightTarget.BOTTOM: None,
            ArmWeightTarget.LEFT: None,
            ArmWeightTarget.CENTER: None
        }

        # Data collected at each target: list of (y, z, force) tuples
        self.target_data = {
            ArmWeightTarget.TOP: [],
            ArmWeightTarget.RIGHT: [],
            ArmWeightTarget.BOTTOM: [],
            ArmWeightTarget.LEFT: [],
            ArmWeightTarget.CENTER: []
        }

        # Completion status for each target
        self.target_completed = {
            ArmWeightTarget.TOP: False,
            ArmWeightTarget.RIGHT: False,
            ArmWeightTarget.BOTTOM: False,
            ArmWeightTarget.LEFT: False,
            ArmWeightTarget.CENTER: False
        }

        self._current_target = ArmWeightTarget.NONE
        self._is_recording = False
        
        # Raw trajectory continuously collected
        self.raw_trajectory = []

    def initialize_from_mlap(self, mlap_arom, limb_type="RIGHT"):
        """Set target positions from MLAP assessment results.

        Args:
            mlap_arom: MarsArom instance with MLAP assessment data
            limb_type: "LEFT" or "RIGHT" - not used, kept for compatibility
        """
        # Use average corners from MLAP assessment for more consistent targets
        # Fallback to adjusted corners if average is not available (e.g. legacy data)
        self.target_positions[ArmWeightTarget.TOP] = mlap_arom.average_top or mlap_arom.adjusted_top
        self.target_positions[ArmWeightTarget.RIGHT] = mlap_arom.average_right or mlap_arom.adjusted_right
        self.target_positions[ArmWeightTarget.BOTTOM] = mlap_arom.average_bottom or mlap_arom.adjusted_bottom
        self.target_positions[ArmWeightTarget.LEFT] = mlap_arom.average_left or mlap_arom.adjusted_left

        # Center is average of all 4 corners
        t, r, b, l = (self.target_positions[ArmWeightTarget.TOP], 
                      self.target_positions[ArmWeightTarget.RIGHT],
                      self.target_positions[ArmWeightTarget.BOTTOM],
                      self.target_positions[ArmWeightTarget.LEFT])
        
        if all([t, r, b, l]):
            center_y = (t[0] + r[0] + b[0] + l[0]) / 4.0
            center_z = (t[1] + r[1] + b[1] + l[1]) / 4.0
            self.target_positions[ArmWeightTarget.CENTER] = (center_y, center_z)

    def start_assessment(self):
        """Begin arm weight assessment."""
        self.timestamp = datetime.now()

    def start_target_recording(self, target: ArmWeightTarget):
        """Start recording data for a specific target.

        Args:
            target: Target to record data for
        """
        self._current_target = target
        self._is_recording = True
        self.target_data[target] = []  # Clear any previous data

    def stop_target_recording(self):
        """Stop recording for current target."""
        self._is_recording = False
        if self._current_target != ArmWeightTarget.NONE:
            self.target_completed[self._current_target] = True
        self._current_target = ArmWeightTarget.NONE

    def add_raw_data_point(self, raw_row: dict):
        """Continuously collect generalized dict entries.
        
        Args:
            raw_row: Dictionary of complete MARS device/game state for raw logging
        """
        self.raw_trajectory.append(raw_row)

    def add_data_point(self, y: float, z: float, force: float, raw_row: dict):
        """Add a data point during recording.

        Args:
            y: Y coordinate in meters
            z: Z coordinate in meters
            force: Force reading in Newtons
            raw_row: The comprehensive dictionary containing the current state info
        """
        if not self._is_recording or self._current_target == ArmWeightTarget.NONE:
            return

        state = raw_row.get("MoveStates", self._current_target.name)
        time_str = raw_row.get("SystemTime", datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
        self.target_data[self._current_target].append((y, z, force, state, time_str))

    @property
    def is_complete(self) -> bool:
        """Check if all targets have been assessed."""
        return all(self.target_completed[t] for t in [
            ArmWeightTarget.TOP,
            ArmWeightTarget.RIGHT,
            ArmWeightTarget.BOTTOM,
            ArmWeightTarget.LEFT,
            ArmWeightTarget.CENTER
        ])

    def save_to_csv(self, base_dir: str = "data", session_subdir: str = None) -> str:
        """Save arm weight data to CSV file.

        Args:
            base_dir: Base directory for data storage
            session_subdir: Pre-determined session subdirectory (e.g. 'session1-2026-03-02')

        Returns:
            Full path to saved CSV file, or None if demo mode
        """
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # Target folder structure: data/<patient_id>/<time_point>/session<N>-<date>/
        date_str = self.timestamp.strftime("%Y-%m-%d")
        
        if self.patient_id:
            parent_dir = Path(base_dir) / self.patient_id / self.time_point
        else:
            parent_dir = Path(base_dir)

        if session_subdir:
            session_folder = parent_dir / session_subdir
            session_folder.mkdir(parents=True, exist_ok=True)
        else:
            # Find the most recent session folder for today
            session_num = 1
            session_folder = None
            while True:
                candidate = parent_dir / f"session{session_num}-{date_str}"
                if candidate.exists():
                    session_folder = candidate
                    session_num += 1
                else:
                    break
            
            # Use latest session or create new one
            if session_folder is None:
                session_folder = parent_dir / f"session1-{date_str}"
                session_folder.mkdir(parents=True, exist_ok=True)

        # Create filename: armweight.csv
        filename = f"armweight.csv"
        filepath = session_folder / filename

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header section
            writer.writerow(['Arm Weight Assessment Data'])
            writer.writerow(['Timestamp', self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')])
            writer.writerow([])

            # Target positions section
            writer.writerow(['Target Positions (meters)'])
            writer.writerow(['Target', 'Y', 'Z', 'Completed', 'DataPoints'])
            for target in [ArmWeightTarget.TOP, ArmWeightTarget.RIGHT,
                          ArmWeightTarget.BOTTOM, ArmWeightTarget.LEFT,
                          ArmWeightTarget.CENTER]:
                pos = self.target_positions[target]
                completed = 'Yes' if self.target_completed[target] else 'No'
                num_points = len(self.target_data[target])
                if pos:
                    writer.writerow([target.name, f"{pos[0]:.6f}", f"{pos[1]:.6f}",
                                   completed, num_points])

            writer.writerow([])

            # Collected data section
            writer.writerow(['Collected Force Data'])
            writer.writerow(['Target', 'Timestamp', 'MoveStates', 'Y', 'Z', 'Force'])

            for target in [ArmWeightTarget.TOP, ArmWeightTarget.RIGHT,
                          ArmWeightTarget.BOTTOM, ArmWeightTarget.LEFT,
                          ArmWeightTarget.CENTER]:
                for pt in self.target_data[target]:
                    y, z, force = pt[0], pt[1], pt[2]
                    state = pt[3] if len(pt) > 3 else target.name
                    t_str = pt[4] if len(pt) > 4 else ""
                    writer.writerow([target.name, t_str, state, f"{y:.6f}", f"{z:.6f}", f"{force:.4f}"])

        # Write Raw Trajectory CSV
        raw_time_str = self.timestamp.strftime("%H-%M-%S")
        raw_filename = f"raw-armweight-{date_str}-{raw_time_str}.csv"
        raw_filepath = session_folder / raw_filename
        with open(raw_filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # First 3 metadata rows
            writer.writerow([":Device: MARS"])
            writer.writerow([":Location: CMCV"])
            writer.writerow([":Movement: ArmWeight"])
            
            # Universal header
            headers = [
                "DeviceRunTime", "PacketNumber", "Status", "ControlType", "ErrorStatus",
                "Limb", "Calibration", "MarsAngle1", "MarsAngle2", "MarsAngle3", "MarsAngle4",
                "Force", "Target", "Desired", "Control", "Button", "EndPointX", "EndPointY",
                "EndPointZ", "EndPointYPlane", "EndPointZPlane", "EndPointTargetY",
                "EndPointTargetZ", "Error", "ErrorDiff", "ErrorSum", "GamePlayerX",
                "GamePlayerY", "GameTargetX", "GameTargetY", "SystemTime",
                "MoveStates"
            ]
            writer.writerow(headers)
            
            for row_dict in self.raw_trajectory:
                out_row = []
                for header in headers:
                    val = row_dict.get(header, "")
                    if isinstance(val, float):
                        out_row.append(f"{val:.6g}") 
                    else:
                        out_row.append(str(val))
                writer.writerow(out_row)

        return str(filepath)

    @classmethod
    def load_from_csv(cls, filepath: str) -> 'ArmWeightData':
        """Load arm weight data from CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            ArmWeightData instance with loaded data
        """
        # Try to extract patient info from path if possible
        # Path: data/<patient_id>/<time_point>/session.../
        path_parts = Path(filepath).parts
        patient_id = None
        time_point = "A0"
        if len(path_parts) >= 4:
            patient_id = path_parts[-4]
            time_point = path_parts[-3]

        arm_weight = cls(patient_id=patient_id, time_point=time_point)

        with open(filepath, 'r') as f:
            reader = csv.reader(f)

            # Skip header
            next(reader)  # 'Arm Weight Assessment Data'
            timestamp_row = next(reader)
            arm_weight.timestamp = datetime.fromisoformat(timestamp_row[1])

            # Skip to target positions
            next(reader)  # Empty
            next(reader)  # 'Target Positions'
            next(reader)  # Column headers

            # Read target positions
            for _ in range(5):
                row = next(reader)
                target_name = row[0]
                target = ArmWeightTarget[target_name]
                y = float(row[1])
                z = float(row[2])
                completed = row[3] == 'Yes'

                arm_weight.target_positions[target] = (y, z)
                arm_weight.target_completed[target] = completed

            # Skip to data section
            next(reader)  # Empty
            next(reader)  # 'Collected Force Data'
            next(reader)  # Column headers

            # Read data points
            for row in reader:
                if len(row) >= 4 and row[0]:
                    target = ArmWeightTarget[row[0]]
                    y = float(row[1])
                    z = float(row[2])
                    force = float(row[3])
                    arm_weight.target_data[target].append((y, z, force))

        return arm_weight
