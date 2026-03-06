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

        # Trial-specific information
        self.trial_top = None
        self.trial_bottom = None
        self.trial_left = None
        self.trial_right = None
        self.trial_ranges = []  # List of (ml_range_cm, ap_range_cm) tuples

        self.raw_trajectory = [] # Stores all points across trials
        self.trial_trajectory = [] # Only the points for the current trial
        self._is_recording = False

    def start_assessment(self):
        """Begin data collection for assessment (Trial 1)."""
        self.timestamp = datetime.now()
        self.raw_trajectory = []
        self.trial_trajectory = []
        self._is_recording = True

    def pause_assessment(self):
        """Pause data recording between trials and compute *cumulative* corners."""
        self._is_recording = False
        
        # Compute corners for the *current trial* only
        trial_corners = self._compute_corners_for_points(self.trial_trajectory)
        if trial_corners:
            self.trial_top, self.trial_bottom, self.trial_left, self.trial_right = trial_corners
            
            # Update global boundaries (expansion-only)
            self._update_global_boundaries(trial_corners)
            
            # Store trial ranges for averaging
            ml = abs(self.trial_right[1] - self.trial_left[1]) * 100.0
            ap = abs(self.trial_top[0] - self.trial_bottom[0]) * 100.0
            self.trial_ranges.append((ml, ap))

        # Save the trial trajectory to the main trajectory list
        if self.trial_trajectory:
            self.raw_trajectory.extend(self.trial_trajectory)
            self.trial_trajectory = []

    def resume_assessment(self):
        """Resume recording for the next trial, starting with a fresh visual trajectory."""
        self.trial_trajectory = []
        self._is_recording = True

    def add_data_point(self, y: float, z: float):
        """Add a trajectory point during assessment.

        Args:
            y: Y coordinate (anterior-posterior) in meters
            z: Z coordinate (medio-lateral) in meters
        """
        if not self._is_recording:
            return
            
        self.trial_trajectory.append([y, z])

    def stop_assessment(self):
        """Stop data collection entirely and compute final corner points."""
        self._is_recording = False
        
        # Compute corners for the *current trial* only
        trial_corners = self._compute_corners_for_points(self.trial_trajectory)
        if trial_corners:
            self.trial_top, self.trial_bottom, self.trial_left, self.trial_right = trial_corners
            
            # Update global boundaries (expansion-only)
            self._update_global_boundaries(trial_corners)
            
            # Store trial ranges for averaging
            ml = abs(self.trial_right[1] - self.trial_left[1]) * 100.0
            ap = abs(self.trial_top[0] - self.trial_bottom[0]) * 100.0
            self.trial_ranges.append((ml, ap))

        # Combine final trial points
        if self.trial_trajectory:
            self.raw_trajectory.extend(self.trial_trajectory)
            self.trial_trajectory = []

    def _compute_corners_for_points(self, points):
        """Compute corner points for a specific list of points."""
        if len(points) < 5:  # Reduced threshold for trial-specific corners
            return None

        # Calculate 5% count (minimum 1 point)
        n_extreme = max(1, int(len(points) * 0.05))

        # Sort by Y axis for top/bottom (AP direction)
        sorted_by_y = sorted(points, key=lambda p: p[0])
        top_pts = sorted_by_y[-n_extreme:]
        bottom_pts = sorted_by_y[:n_extreme]

        top = (sum(p[0] for p in top_pts) / len(top_pts), sum(p[1] for p in top_pts) / len(top_pts))
        bottom = (sum(p[0] for p in bottom_pts) / len(bottom_pts), sum(p[1] for p in bottom_pts) / len(bottom_pts))

        # Sort by Z axis for left/right (ML direction)
        sorted_by_z = sorted(points, key=lambda p: p[1])
        left_pts = sorted_by_z[:n_extreme]
        right_pts = sorted_by_z[-n_extreme:]

        left = (sum(p[0] for p in left_pts) / len(left_pts), sum(p[1] for p in left_pts) / len(left_pts))
        right = (sum(p[0] for p in right_pts) / len(right_pts), sum(p[1] for p in right_pts) / len(right_pts))

        return top, bottom, left, right

    def _update_global_boundaries(self, trial_corners):
        """Update global adjusted boundaries based on new trial corners (expansion only)."""
        t_top, t_bottom, t_left, t_right = trial_corners

        # Initialize global corners if they don't exist
        if self.adjusted_top is None:
            self.adjusted_top, self.adjusted_bottom = t_top, t_bottom
            self.adjusted_left, self.adjusted_right = t_left, t_right
            self.raw_top, self.raw_bottom = t_top, t_bottom
            self.raw_left, self.raw_right = t_left, t_right
            return

        # Expansion logic: update only if further from center/origin
        # Using Y for Top (Max Y) and Bottom (Min Y)
        if t_top[0] > self.adjusted_top[0]:
            self.adjusted_top = t_top
        if t_bottom[0] < self.adjusted_bottom[0]:
            self.adjusted_bottom = t_bottom
            
        # Using Z for Left (Min Z) and Right (Max Z)
        if t_left[1] < self.adjusted_left[1]:
            self.adjusted_left = t_left
        if t_right[1] > self.adjusted_right[1]:
            self.adjusted_right = t_right

        # Keep raw corners synced with adjusted for now
        self.raw_top, self.raw_bottom = self.adjusted_top, self.adjusted_bottom
        self.raw_left, self.raw_right = self.adjusted_left, self.adjusted_right

    def _compute_corners(self):
        """Deprecated: Compute corner points using all points. 
        Now we use expansion-only logic in _update_global_boundaries.
        """
        pass

    @property
    def ml_range_cm(self) -> float:
        """Calculate medio-lateral range in centimeters (Global Maximum)."""
        if self.adjusted_left is None or self.adjusted_right is None:
            return 0.0
        return abs(self.adjusted_right[1] - self.adjusted_left[1]) * 100.0

    @property
    def ap_range_cm(self) -> float:
        """Calculate anterior-posterior range in centimeters (Global Maximum)."""
        if self.adjusted_top is None or self.adjusted_bottom is None:
            return 0.0
        return abs(self.adjusted_top[0] - self.adjusted_bottom[0]) * 100.0

    @property
    def ml_average_cm(self) -> float:
        """Calculate average medio-lateral range across trials."""
        if not self.trial_ranges:
            return 0.0
        return sum(r[0] for r in self.trial_ranges) / len(self.trial_ranges)

    @property
    def ap_average_cm(self) -> float:
        """Calculate average anterior-posterior range across trials."""
        if not self.trial_ranges:
            return 0.0
        return sum(r[1] for r in self.trial_ranges) / len(self.trial_ranges)

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
                'ml_range_cm', 'ap_range_cm',
                'ml_average_cm', 'ap_average_cm',
                'trial_ranges'
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
                f"{self.ap_range_cm:.2f}",
                f"{self.ml_average_cm:.2f}",
                f"{self.ap_average_cm:.2f}",
                ";".join([f"{ml:.2f},{ap:.2f}" for ml, ap in self.trial_ranges])
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

            # Load trial ranges
            if data_dict.get('trial_ranges'):
                try:
                    range_str = data_dict['trial_ranges']
                    for r_pair in range_str.split(';'):
                        if r_pair:
                            ml, ap = r_pair.split(',')
                            arom.trial_ranges.append((float(ml), float(ap)))
                except Exception as e:
                    print(f"Error loading trial ranges: {e}")

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
