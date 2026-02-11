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


class ArmWeightData:
    """Data model for arm weight assessment.

    Collects endpoint position and force data at 5 workspace positions
    to characterize arm weight support needs.
    """

    def __init__(self):
        """Initialize arm weight assessment."""
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

    def initialize_from_mlap(self, mlap_arom):
        """Set target positions from MLAP assessment results.

        Args:
            mlap_arom: MarsArom instance with MLAP assessment data
        """
        # Use adjusted corners from MLAP assessment
        self.target_positions[ArmWeightTarget.TOP] = mlap_arom.adjusted_top
        self.target_positions[ArmWeightTarget.RIGHT] = mlap_arom.adjusted_right
        self.target_positions[ArmWeightTarget.BOTTOM] = mlap_arom.adjusted_bottom
        self.target_positions[ArmWeightTarget.LEFT] = mlap_arom.adjusted_left

        # Center is average of all 4 corners
        center_y = (mlap_arom.adjusted_top[0] + mlap_arom.adjusted_right[0] +
                   mlap_arom.adjusted_bottom[0] + mlap_arom.adjusted_left[0]) / 4.0
        center_z = (mlap_arom.adjusted_top[1] + mlap_arom.adjusted_right[1] +
                   mlap_arom.adjusted_bottom[1] + mlap_arom.adjusted_left[1]) / 4.0
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

    def add_data_point(self, y: float, z: float, force: float):
        """Add a data point during recording.

        Args:
            y: Y coordinate in meters
            z: Z coordinate in meters
            force: Force reading in Newtons
        """
        if not self._is_recording or self._current_target == ArmWeightTarget.NONE:
            return

        self.target_data[self._current_target].append((y, z, force))

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

    def save_to_csv(self, base_dir: str = "data") -> str:
        """Save arm weight data to CSV file.

        Args:
            base_dir: Base directory for data storage

        Returns:
            Full path to saved CSV file
        """
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # Use same session folder as MLAP assessment
        date_str = self.timestamp.strftime("%Y-%m-%d")
        session_dir = Path(base_dir)

        # Find the most recent session folder for today
        session_num = 1
        latest_session = None
        while True:
            session_folder = session_dir / f"session{session_num}-{date_str}"
            if session_folder.exists():
                latest_session = session_folder
                session_num += 1
            else:
                break

        # Use latest session or create new one
        if latest_session is None:
            latest_session = session_dir / f"session1-{date_str}"
            latest_session.mkdir(parents=True, exist_ok=True)

        # Create filename: armweight-{date}-{time}.csv
        time_str = self.timestamp.strftime("%H-%M-%S")
        filename = f"armweight-{date_str}-{time_str}.csv"
        filepath = latest_session / filename

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header section
            writer.writerow(['Arm Weight Assessment Data'])
            writer.writerow(['Timestamp', self.timestamp.isoformat()])
            writer.writerow([])

            # Target positions section
            writer.writerow(['Target Positions (meters)'])
            writer.writerow(['Target', 'Y', 'Z', 'Completed', 'Data Points'])
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
            writer.writerow(['Target', 'Y (m)', 'Z (m)', 'Force (N)'])

            for target in [ArmWeightTarget.TOP, ArmWeightTarget.RIGHT,
                          ArmWeightTarget.BOTTOM, ArmWeightTarget.LEFT,
                          ArmWeightTarget.CENTER]:
                for y, z, force in self.target_data[target]:
                    writer.writerow([target.name, f"{y:.6f}", f"{z:.6f}", f"{force:.4f}"])

        return str(filepath)

    @classmethod
    def load_from_csv(cls, filepath: str) -> 'ArmWeightData':
        """Load arm weight data from CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            ArmWeightData instance with loaded data
        """
        arm_weight = cls()

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
