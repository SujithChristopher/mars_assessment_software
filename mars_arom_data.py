"""
Data model for MARS Active Range of Motion (AROM) assessments.

Author: Sivakumar Balasubramanian
Date: 09 February 2026
Email: siva82kb@gmail.com
"""

import csv
import os
from datetime import datetime
from pathlib import Path


class MarsArom:
    """Data model for MARS AROM assessment.

    Stores trajectory data, computed corner points, and metadata for
    Active Range of Motion assessments (AP, ML, or MLAP).
    """

    def __init__(self, movement_type: str, patient_id: str = None, 
                 time_point: str = "A0", is_demo: bool = False):
        """Initialize MarsArom instance.
        
        Args:
            movement_type: Assessment type - "AP", "ML", or "MLAP"
            patient_id: Homer ID of the patient
            time_point: Time point (A0, A1, A2)
            is_demo: Whether this is a demo session
        """
        if movement_type not in ["AP", "ML", "MLAP"]:
            raise ValueError(f"Invalid movement type: {movement_type}")

        self.movement_type = movement_type
        self.patient_id = patient_id
        self.time_point = time_point
        self.is_demo = is_demo
        self.timestamp = None
        self.plane_angle = 90.0  # Default training plane angle

        # Raw trajectory data: list of [y, z] points in meters
        self.raw_trajectory = []

        # Corner points: (y, z) tuples in meters
        self.raw_top = None
        self.raw_bottom = None
        self.raw_left = None
        self.raw_right = None

        self.adjusted_top = None
        self.adjusted_bottom = None
        self.adjusted_left = None
        self.adjusted_right = None

        self._is_recording = False

    def start_assessment(self):
        """Begin data collection for assessment."""
        self.timestamp = datetime.now()
        self.raw_trajectory = []
        self._is_recording = True

    def add_data_point(self, y: float, z: float):
        """Add a trajectory point during assessment.

        Args:
            y: Y coordinate (anterior-posterior) in meters
            z: Z coordinate (medio-lateral) in meters
        """
        if not self._is_recording:
            return
        self.raw_trajectory.append([y, z])

    def stop_assessment(self):
        """Stop data collection and compute corner points using 5% extremes."""
        self._is_recording = False
        self._compute_corners()

    def _compute_corners(self):
        """Compute corner points using 5% statistical extreme averaging.

        For each boundary:
        - Sort points by relevant axis
        - Take extreme 5% of points
        - Average to get corner position
        """
        if len(self.raw_trajectory) < 20:
            # Need at least 20 points for 5% calculation
            return

        # Calculate 5% count (minimum 1 point)
        n_extreme = max(1, int(len(self.raw_trajectory) * 0.05))

        # Extract y and z coordinates
        y_coords = [p[0] for p in self.raw_trajectory]
        z_coords = [p[1] for p in self.raw_trajectory]

        # Sort by Y axis for top/bottom (AP direction)
        sorted_by_y = sorted(self.raw_trajectory, key=lambda p: p[0])
        top_points = sorted_by_y[-n_extreme:]  # Highest Y values
        bottom_points = sorted_by_y[:n_extreme]  # Lowest Y values

        # Average the extreme points
        self.raw_top = (
            sum(p[0] for p in top_points) / len(top_points),
            sum(p[1] for p in top_points) / len(top_points)
        )
        self.raw_bottom = (
            sum(p[0] for p in bottom_points) / len(bottom_points),
            sum(p[1] for p in bottom_points) / len(bottom_points)
        )

        # Sort by Z axis for left/right (ML direction)
        sorted_by_z = sorted(self.raw_trajectory, key=lambda p: p[1])
        left_points = sorted_by_z[:n_extreme]  # Lowest Z values (left)
        right_points = sorted_by_z[-n_extreme:]  # Highest Z values (right)

        self.raw_left = (
            sum(p[0] for p in left_points) / len(left_points),
            sum(p[1] for p in left_points) / len(left_points)
        )
        self.raw_right = (
            sum(p[0] for p in right_points) / len(right_points),
            sum(p[1] for p in right_points) / len(right_points)
        )

        # Initialize adjusted corners same as raw
        self.adjusted_top = self.raw_top
        self.adjusted_bottom = self.raw_bottom
        self.adjusted_left = self.raw_left
        self.adjusted_right = self.raw_right

    @property
    def ml_range_cm(self) -> float:
        """Calculate medio-lateral range in centimeters."""
        if self.adjusted_left is None or self.adjusted_right is None:
            return 0.0
        return abs(self.adjusted_right[1] - self.adjusted_left[1]) * 100.0

    @property
    def ap_range_cm(self) -> float:
        """Calculate anterior-posterior range in centimeters."""
        if self.adjusted_top is None or self.adjusted_bottom is None:
            return 0.0
        return abs(self.adjusted_top[0] - self.adjusted_bottom[0]) * 100.0

    def save_to_csv(self, base_dir: str = "data", session_subdir: str = None) -> str:
        """Save AROM data to CSV file in session folder.

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
        
        # Build path based on patient_id and time_point
        if self.patient_id:
            parent_dir = Path(base_dir) / self.patient_id / self.time_point
        else:
            parent_dir = Path(base_dir)

        if session_subdir:
            session_folder = parent_dir / session_subdir
            session_folder.mkdir(parents=True, exist_ok=True)
        else:
            # Original auto-increment logic if no subdir provided
            session_num = 1
            while True:
                session_folder = parent_dir / f"session{session_num}-{date_str}"
                if not session_folder.exists():
                    session_folder.mkdir(parents=True, exist_ok=True)
                    break
                # Check if this session has files - if yes, increment
                if list(session_folder.glob("*.csv")):
                    session_num += 1
                else:
                    break

        # Create filename: {movement}-{date}-{time}.csv
        time_str = self.timestamp.strftime("%H-%M-%S")
        filename = f"{self.movement_type.lower()}-{date_str}-{time_str}.csv"
        filepath = session_folder / filename

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'datetime', 'plane_angle', 'movement_type',
                'patient_id', 'time_point',
                'raw_top_y', 'raw_top_z',
                'raw_bottom_y', 'raw_bottom_z',
                'raw_left_y', 'raw_left_z',
                'raw_right_y', 'raw_right_z',
                'adjusted_top_y', 'adjusted_top_z',
                'adjusted_bottom_y', 'adjusted_bottom_z',
                'adjusted_left_y', 'adjusted_left_z',
                'adjusted_right_y', 'adjusted_right_z',
                'ml_range_cm', 'ap_range_cm'
            ])

            # Data row
            writer.writerow([
                self.timestamp.isoformat(),
                self.plane_angle,
                self.movement_type,
                self.patient_id if self.patient_id else '',
                self.time_point if self.time_point else '',
                self.raw_top[0] if self.raw_top else '',
                self.raw_top[1] if self.raw_top else '',
                self.raw_bottom[0] if self.raw_bottom else '',
                self.raw_bottom[1] if self.raw_bottom else '',
                self.raw_left[0] if self.raw_left else '',
                self.raw_left[1] if self.raw_left else '',
                self.raw_right[0] if self.raw_right else '',
                self.raw_right[1] if self.raw_right else '',
                self.adjusted_top[0] if self.adjusted_top else '',
                self.adjusted_top[1] if self.adjusted_top else '',
                self.adjusted_bottom[0] if self.adjusted_bottom else '',
                self.adjusted_bottom[1] if self.adjusted_bottom else '',
                self.adjusted_left[0] if self.adjusted_left else '',
                self.adjusted_left[1] if self.adjusted_left else '',
                self.adjusted_right[0] if self.adjusted_right else '',
                self.adjusted_right[1] if self.adjusted_right else '',
                f"{self.ml_range_cm:.2f}",
                f"{self.ap_range_cm:.2f}"
            ])

            # Trajectory data section
            writer.writerow([])
            writer.writerow(['Trajectory Data'])
            writer.writerow(['y (m)', 'z (m)'])
            for point in self.raw_trajectory:
                writer.writerow([f"{point[0]:.6f}", f"{point[1]:.6f}"])

        return str(filepath)

    @classmethod
    def load_from_csv(cls, filepath: str) -> 'MarsArom':
        """Load AROM data from CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            MarsArom instance with loaded data
        """
        with open(filepath, 'r') as f:
            reader = csv.reader(f)

            # Read header
            header = next(reader)

            # Read data row
            data_row = next(reader)
            data_dict = dict(zip(header, data_row))

            # Create instance
            movement_type = data_dict['movement_type']
            patient_id = data_dict.get('patient_id')
            time_point = data_dict.get('time_point', 'A0')
            
            # Backward compatibility for polluted movement_type strings (e.g. "123/A0/MLAP")
            if '/' in movement_type:
                parts = movement_type.split('/')
                if len(parts) >= 3:
                    movement_type = parts[-1]
                    if not patient_id: patient_id = parts[0]
                    if time_point == 'A0': time_point = parts[1]

            arom = cls(movement_type, patient_id=patient_id, time_point=time_point)
            arom.timestamp = datetime.fromisoformat(data_dict['datetime'])
            arom.plane_angle = float(data_dict['plane_angle'])

            # Load corners
            if data_dict.get('raw_top_y'):
                arom.raw_top = (float(data_dict['raw_top_y']), float(data_dict['raw_top_z']))
            if data_dict.get('raw_bottom_y'):
                arom.raw_bottom = (float(data_dict['raw_bottom_y']), float(data_dict['raw_bottom_z']))
            if data_dict.get('raw_left_y'):
                arom.raw_left = (float(data_dict['raw_left_y']), float(data_dict['raw_left_z']))
            if data_dict.get('raw_right_y'):
                arom.raw_right = (float(data_dict['raw_right_y']), float(data_dict['raw_right_z']))

            if data_dict.get('adjusted_top_y'):
                arom.adjusted_top = (float(data_dict['adjusted_top_y']), float(data_dict['adjusted_top_z']))
            if data_dict.get('adjusted_bottom_y'):
                arom.adjusted_bottom = (float(data_dict['adjusted_bottom_y']), float(data_dict['adjusted_bottom_z']))
            if data_dict.get('adjusted_left_y'):
                arom.adjusted_left = (float(data_dict['adjusted_left_y']), float(data_dict['adjusted_left_z']))
            if data_dict.get('adjusted_right_y'):
                arom.adjusted_right = (float(data_dict['adjusted_right_y']), float(data_dict['adjusted_right_z']))

            # Skip empty row and trajectory header
            next(reader)  # Empty row
            next(reader)  # "Trajectory Data"
            next(reader)  # Column headers

            # Load trajectory points
            arom.raw_trajectory = []
            for row in reader:
                if len(row) >= 2 and row[0] and row[1]:
                    arom.raw_trajectory.append([float(row[0]), float(row[1])])

        return arom

    @staticmethod
    def find_latest_assessment(movement_type: str, base_dir: str = "data", patient_id: str = None) -> 'MarsArom':
        """Find and load the most recent assessment of given type.

        Args:
            movement_type: Assessment type - "AP", "ML", or "MLAP"
            base_dir: Base directory for data storage
            patient_id: Optional patient ID to filter by

        Returns:
            MarsArom instance or None if not found
        """
        base_path = Path(base_dir)
        if not base_path.exists():
            return None

        # Determine search pattern
        if patient_id:
            # Look in any time point folder for this patient
            pattern = f"{patient_id}/*/*/ {movement_type.lower()}-*.csv"
            # Adjusting pattern to handle the session folders
            # path: data/<patient_id>/<time_point>/session.../movement-*.csv
            pattern = f"{patient_id}/*/*/{movement_type.lower()}-*.csv"
        else:
            # Original behavior (recursive search)
            pattern = f"**/{movement_type.lower()}-*.csv"
            
        matching_files = list(base_path.glob(pattern))

        if not matching_files:
            return None

        # Sort by modification time, newest first
        latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)

        return MarsArom.load_from_csv(str(latest_file))
