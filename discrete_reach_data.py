"""
Data model for MARS Discrete Reaching assessment.

Collects endpoint position data at 4 workspace positions 
(Home + 3 targets at 75% of MLAP workspace) to evaluate reaching precision.

Author: Sivakumar Balasubramanian
Date: 23 February 2026
Email: siva82kb@gmail.com
"""

import csv
from datetime import datetime
from pathlib import Path
from enum import Enum


class DiscreteReachTarget(Enum):
    """Target positions for discrete reaching assessment."""
    NONE = 0
    HOME = 1
    TOP = 2
    LEFT = 3
    RIGHT = 4


class DiscreteReachData:
    """Data model for discrete reaching assessment.

    Tracks targets derived from MLAP assessment and records reaching results.
    """

    def __init__(self):
        """Initialize discrete reaching assessment."""
        self.timestamp = None

        # Target positions (y, z) in meters - calculated from MLAP
        self.target_positions = {
            DiscreteReachTarget.HOME: None,
            DiscreteReachTarget.TOP: None,
            DiscreteReachTarget.LEFT: None,
            DiscreteReachTarget.RIGHT: None
        }

        # Actual positions reached (averaged over hold duration)
        self.actual_positions = {
            DiscreteReachTarget.HOME: [], # Store trajectory during hold
            DiscreteReachTarget.TOP: [],
            DiscreteReachTarget.LEFT: [],
            DiscreteReachTarget.RIGHT: []
        }

        self.target_completed = {
            DiscreteReachTarget.HOME: False,
            DiscreteReachTarget.TOP: False,
            DiscreteReachTarget.LEFT: False,
            DiscreteReachTarget.RIGHT: False
        }

        self._current_target = DiscreteReachTarget.NONE
        self._is_recording = False

    def initialize_from_mlap(self, mlap_arom):
        """Calculate targets at 75% distance from bottom vertex.

        Args:
            mlap_arom: MarsArom instance with MLAP assessment data
        """
        bottom = mlap_arom.adjusted_bottom  # (y, z)
        top = mlap_arom.adjusted_top
        left = mlap_arom.adjusted_left
        right = mlap_arom.adjusted_right

        if not all([bottom, top, left, right]):
            print("Warning: Missing MLAP corner points for discrete reaching.")
            return

        # HOME is the bottom vertex
        self.target_positions[DiscreteReachTarget.HOME] = bottom

        # TOP target = Bottom + 0.75 * (Top - Bottom)
        self.target_positions[DiscreteReachTarget.TOP] = (
            bottom[0] + 0.75 * (top[0] - bottom[0]),
            bottom[1] + 0.75 * (top[1] - bottom[1])
        )

        # LEFT target = Bottom + 0.75 * (Left - Bottom)
        self.target_positions[DiscreteReachTarget.LEFT] = (
            bottom[0] + 0.75 * (left[0] - bottom[0]),
            bottom[1] + 0.75 * (left[1] - bottom[1])
        )

        # RIGHT target = Bottom + 0.75 * (Right - Bottom)
        self.target_positions[DiscreteReachTarget.RIGHT] = (
            bottom[0] + 0.75 * (right[0] - bottom[0]),
            bottom[1] + 0.75 * (right[1] - bottom[1])
        )

    def start_assessment(self):
        """Begin discrete reaching assessment."""
        self.timestamp = datetime.now()

    def start_target_recording(self, target: DiscreteReachTarget):
        """Start recording data for a specific target.

        Args:
            target: Target to record data for
        """
        self._current_target = target
        self._is_recording = True
        self.actual_positions[target] = []  # Clear any previous data

    def stop_target_recording(self):
        """Stop recording for current target."""
        self._is_recording = False
        if self._current_target != DiscreteReachTarget.NONE:
            self.target_completed[self._current_target] = True
        self._current_target = DiscreteReachTarget.NONE

    def add_data_point(self, y: float, z: float):
        """Add a data point during recording.

        Args:
            y: Y coordinate in meters
            z: Z coordinate in meters
        """
        if not self._is_recording or self._current_target == DiscreteReachTarget.NONE:
            return

        self.actual_positions[self._current_target].append((y, z))

    @property
    def is_complete(self) -> bool:
        """Check if all targets (Top, Left, Right) have been assessed."""
        return all(self.target_completed[t] for t in [
            DiscreteReachTarget.TOP,
            DiscreteReachTarget.LEFT,
            DiscreteReachTarget.RIGHT
        ])

    def save_to_csv(self, base_dir: str = "data") -> str:
        """Save discrete reaching data to CSV file.

        Args:
            base_dir: Base directory for data storage

        Returns:
            Full path to saved CSV file
        """
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # Follow session folder convention
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

        # Create filename: discreach-{date}-{time}.csv
        time_str = self.timestamp.strftime("%H-%M-%S")
        filename = f"discreach-{date_str}-{time_str}.csv"
        filepath = latest_session / filename

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header section
            writer.writerow(['Discrete Reaching Assessment Data'])
            writer.writerow(['Timestamp', self.timestamp.isoformat()])
            writer.writerow([])

            # Target positions section
            writer.writerow(['Target Summary (meters)'])
            writer.writerow(['Target', 'Target Y', 'Target Z', 'Actual Y (avg)', 'Actual Z (avg)', 'Completed'])
            
            for target in [DiscreteReachTarget.HOME, DiscreteReachTarget.TOP, 
                          DiscreteReachTarget.LEFT, DiscreteReachTarget.RIGHT]:
                t_pos = self.target_positions[target]
                a_data = self.actual_positions[target]
                
                if a_data:
                    avg_y = sum(p[0] for p in a_data) / len(a_data)
                    avg_z = sum(p[1] for p in a_data) / len(a_data)
                else:
                    avg_y, avg_z = None, None
                
                completed = 'Yes' if self.target_completed[target] else 'No'
                
                if t_pos:
                    writer.writerow([
                        target.name, 
                        f"{t_pos[0]:.6f}", 
                        f"{t_pos[1]:.6f}", 
                        f"{avg_y:.6f}" if avg_y is not None else '', 
                        f"{avg_z:.6f}" if avg_z is not None else '', 
                        completed
                    ])

            writer.writerow([])

            # Collected trajectory section
            writer.writerow(['Detailed Trajectory Data during Hold'])
            writer.writerow(['Target', 'Y (m)', 'Z (m)'])

            for target in [DiscreteReachTarget.HOME, DiscreteReachTarget.TOP, 
                          DiscreteReachTarget.LEFT, DiscreteReachTarget.RIGHT]:
                for y, z in self.actual_positions[target]:
                    writer.writerow([target.name, f"{y:.6f}", f"{z:.6f}"])

        return str(filepath)
