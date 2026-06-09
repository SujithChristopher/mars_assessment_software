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
                 time_point: str = "A0", is_demo: bool = False, limb: str = "RIGHT"):
        """Initialize MarsArom instance.

        Args:
            movement_type: Assessment type - "AP", "ML", or "MLAP"
            patient_id: Homer ID of the patient
            time_point: Time point (Screening, A0, A1, A2)
            is_demo: Whether this is a demo session
            limb: Assessed limb ("LEFT" or "RIGHT") - part of the save path
        """
        if movement_type not in ["AP", "ML", "MLAP"]:
            raise ValueError(f"Invalid movement type: {movement_type}")

        self.movement_type = movement_type
        self.patient_id = patient_id
        self.time_point = time_point
        self.is_demo = is_demo
        self.limb = limb
        self.timestamp = None
        self.plane_angle = 90.0  # Default training plane angle

        # Raw trajectory data: list of [y, z, trial_num] points in meters
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
        self.trial_corners_history = [] # List of (top, bottom, left, right) tuples
        self.trial_timestamps = [] # List of datetime objects for each trial start

        self.trial_trajectory = [] # Only the points for the current trial as [y, z]
        self._is_recording = False
        self.current_trial_num = 1

    def start_assessment(self):
        """Begin data collection for assessment (Trial 1)."""
        self.timestamp = datetime.now()
        self.raw_trajectory = []
        self.trial_trajectory = []
        self.trial_timestamps = [self.timestamp]
        self.current_trial_num = 1
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
            
            # Store trial corners in history
            self.trial_corners_history.append(trial_corners)
            
            # Store trial ranges for averaging
            ml = abs(self.trial_right[1] - self.trial_left[1])
            ap = abs(self.trial_top[0] - self.trial_bottom[0])
            self.trial_ranges.append((ml, ap))

        # Save the trial trajectory to the main trajectory list with trial number
        if self.trial_trajectory:
            for pt in self.trial_trajectory:
                # pt is either [y, z] or [y, z, {raw_row}]
                # standard format in raw_trajectory will be [y, z, trial_num, {raw_row}]
                row_dict = pt[2] if len(pt) > 2 else {}
                self.raw_trajectory.append([pt[0], pt[1], self.current_trial_num, row_dict])
            self.trial_trajectory = []
            self.current_trial_num += 1

    def resume_assessment(self):
        """Resume recording for the next trial, starting with a fresh visual trajectory."""
        self.trial_trajectory = []
        self.trial_timestamps.append(datetime.now())
        self._is_recording = True

    def add_data_point(self, y: float, z: float, raw_row: dict = None):
        """Add a trajectory point during assessment.

        Args:
            y: Y coordinate (anterior-posterior) in meters
            z: Z coordinate (medio-lateral) in meters
            raw_row: Dictionary of complete MARS device/game state for raw logging
        """
        if not self._is_recording:
            return
            
        # trial_trajectory only needs y,z for boundary calculation
        # but we also keep the raw_row for the final raw_csv formulation
        pt_data = [y, z]
        if raw_row is not None:
            pt_data.append(raw_row)
            
        self.trial_trajectory.append(pt_data)

    def stop_assessment(self):
        """Stop data collection entirely and compute final corner points."""
        self._is_recording = False
        
        # Compute corners for the *current trial* only
        trial_corners = self._compute_corners_for_points(self.trial_trajectory)
        if trial_corners:
            self.trial_top, self.trial_bottom, self.trial_left, self.trial_right = trial_corners
            
            # Update global boundaries (expansion-only)
            self._update_global_boundaries(trial_corners)
            
            # Store trial corners in history
            self.trial_corners_history.append(trial_corners)
            
            # Store trial ranges for averaging
            ml = abs(self.trial_right[1] - self.trial_left[1])
            ap = abs(self.trial_top[0] - self.trial_bottom[0])
            self.trial_ranges.append((ml, ap))

        # Combine final trial points
        if self.trial_trajectory:
            for pt in self.trial_trajectory:
                row_dict = pt[2] if len(pt) > 2 else {}
                self.raw_trajectory.append([pt[0], pt[1], self.current_trial_num, row_dict])
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
    def ml_range(self) -> float:
        """Calculate medio-lateral range in meters (Global Maximum)."""
        if self.adjusted_left is None or self.adjusted_right is None:
            return 0.0
        return abs(self.adjusted_right[1] - self.adjusted_left[1])

    @property
    def ap_range(self) -> float:
        """Calculate anterior-posterior range in meters (Global Maximum)."""
        if self.adjusted_top is None or self.adjusted_bottom is None:
            return 0.0
        return abs(self.adjusted_top[0] - self.adjusted_bottom[0])

    @property
    def ml_average(self) -> float:
        """Calculate average medio-lateral range across trials in meters."""
        if not self.trial_ranges:
            return 0.0
        return sum(r[0] for r in self.trial_ranges) / len(self.trial_ranges)

    @property
    def ap_average(self) -> float:
        """Calculate average anterior-posterior range across trials in meters."""
        if not self.trial_ranges:
            return 0.0
        return sum(r[1] for r in self.trial_ranges) / len(self.trial_ranges)

    @property
    def average_ml_range(self):
        if not self.trial_ranges: return self.ml_range
        return sum(r[0] for r in self.trial_ranges) / len(self.trial_ranges)

    @property
    def average_ap_range(self):
        if not self.trial_ranges: return self.ap_range
        return sum(r[1] for r in self.trial_ranges) / len(self.trial_ranges)

    @property
    def average_top(self):
        if not self.trial_corners_history: return None
        return (sum(c[0][0] for c in self.trial_corners_history) / len(self.trial_corners_history),
                sum(c[0][1] for c in self.trial_corners_history) / len(self.trial_corners_history))

    @property
    def average_bottom(self):
        if not self.trial_corners_history: return None
        return (sum(c[1][0] for c in self.trial_corners_history) / len(self.trial_corners_history),
                sum(c[1][1] for c in self.trial_corners_history) / len(self.trial_corners_history))

    @property
    def average_left(self):
        if not self.trial_corners_history: return None
        return (sum(c[2][0] for c in self.trial_corners_history) / len(self.trial_corners_history),
                sum(c[2][1] for c in self.trial_corners_history) / len(self.trial_corners_history))

    @property
    def average_right(self):
        if not self.trial_corners_history: return None
        return (sum(c[3][0] for c in self.trial_corners_history) / len(self.trial_corners_history),
                sum(c[3][1] for c in self.trial_corners_history) / len(self.trial_corners_history))

    def save_to_csv(self, base_dir: str = None, session_subdir: str = None) -> str:
        """Save AROM data to CSV file in session folder.

        Args:
            base_dir: Base directory for data storage (defaults to app data dir)
            session_subdir: Pre-determined session subdirectory (e.g. 'session1-2026-03-02')

        Returns:
            Full path to saved CSV file, or None if demo mode
        """
        if base_dir is None:
            from app_paths import get_data_dir
            base_dir = str(get_data_dir())
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # Target folder structure (see app_paths.get_assessment_dir):
        #   Screening: <root>/Screening/<patient>/<limb>/session<N>-<date>/
        #   A0/A1/A2:  <root>/Assessment/<patient>/<limb>/<time_point>/session<N>-<date>/
        date_str = self.timestamp.strftime("%Y-%m-%d")

        # Build path based on patient_id, limb and time_point
        if self.patient_id:
            from app_paths import get_assessment_dir
            parent_dir = get_assessment_dir(self.patient_id, self.limb, self.time_point)
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

        # Create filenames
        time_str = self.timestamp.strftime("%H-%M-%S")
        filename = f"{self.movement_type.lower()}-rom.csv"
        raw_filename = f"raw-{self.movement_type.lower()}-{date_str}-{time_str}.csv"
        
        filepath = session_folder / filename
        raw_filepath = session_folder / raw_filename

        # Write Summary CSV (One row per trial + Average + Final Max)
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'DateTime', 'PlaneAngle', 'MovementType',
                'PatientId', 'TimePoint', 'TrialNumber',
                'MLRange', 'APRange',
                'TopY', 'TopZ', 'BottomY', 'BottomZ',
                'LeftY', 'LeftZ', 'RightY', 'RightZ'
            ])

            base_common_info = [
                self.plane_angle,
                self.movement_type,
                self.patient_id if self.patient_id else '',
                self.time_point if self.time_point else ''
            ]

            # 1. Individual Trials
            for i, (ml, ap) in enumerate(self.trial_ranges):
                trial_idx = i + 1
                corners = self.trial_corners_history[i] if i < len(self.trial_corners_history) else (None, None, None, None)
                trial_time = self.trial_timestamps[i].strftime('%Y-%m-%d %H:%M:%S.%f') if i < len(self.trial_timestamps) else self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
                
                row = [trial_time] + base_common_info + [
                    f"Trial {trial_idx}", f"{ml:.6f}", f"{ap:.6f}",
                    corners[0][0] if corners[0] else '', corners[0][1] if corners[0] else '',
                    corners[1][0] if corners[1] else '', corners[1][1] if corners[1] else '',
                    corners[2][0] if corners[2] else '', corners[2][1] if corners[2] else '',
                    corners[3][0] if corners[3] else '', corners[3][1] if corners[3] else ''
                ]
                writer.writerow(row)

            # 2. Average row
            avg_row = [self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')] + base_common_info + [
                "AVERAGE", f"{self.ml_average:.6f}", f"{self.ap_average:.6f}",
                self.average_top[0] if self.average_top else '', self.average_top[1] if self.average_top else '',
                self.average_bottom[0] if self.average_bottom else '', self.average_bottom[1] if self.average_bottom else '',
                self.average_left[0] if self.average_left else '', self.average_left[1] if self.average_left else '',
                self.average_right[0] if self.average_right else '', self.average_right[1] if self.average_right else ''
            ]
            writer.writerow(avg_row)

            # 3. Maximum (Cumulative) row
            max_row = [self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')] + base_common_info + [
                "MAXIMUM", f"{self.ml_range:.6f}", f"{self.ap_range:.6f}",
                self.adjusted_top[0] if self.adjusted_top else '', self.adjusted_top[1] if self.adjusted_top else '',
                self.adjusted_bottom[0] if self.adjusted_bottom else '', self.adjusted_bottom[1] if self.adjusted_bottom else '',
                self.adjusted_left[0] if self.adjusted_left else '', self.adjusted_left[1] if self.adjusted_left else '',
                self.adjusted_right[0] if self.adjusted_right else '', self.adjusted_right[1] if self.adjusted_right else ''
            ]
            writer.writerow(max_row)

        # Write Raw Trajectory CSV
        with open(raw_filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # First 3 metadata rows
            writer.writerow([":Device: MARS"])
            writer.writerow([":Location: CMCV"])
            writer.writerow([f":Movement: {self.movement_type}"])
            
            # Universal header
            headers = [
                "DeviceRunTime", "PacketNumber", "Status", "ControlType", "ErrorStatus",
                "Limb", "Calibration", "MarsAngle1", "MarsAngle2", "MarsAngle3", "MarsAngle4",
                "Force", "Target", "Desired", "Control", "Button", "EndPointX", "EndPointY",
                "EndPointZ", "EndPointYPlane", "EndPointZPlane", "EndPointTargetY",
                "EndPointTargetZ", "Error", "ErrorDiff", "ErrorSum", "GamePlayerX",
                "GamePlayerY", "GameTargetX", "GameTargetY", "SystemTime",
                "MoveStates", "TrialNumber"
            ]
            writer.writerow(headers)

            for point in self.raw_trajectory:
                # point is [y, z, trial_num, raw_row_dict]
                trial_num = point[2] if len(point) > 2 else ""
                row_dict = point[3] if len(point) > 3 else {}

                # Build the row to match the headers
                out_row = []
                for header in headers:
                    if header == "TrialNumber":
                        out_row.append(str(trial_num))
                        continue
                    val = row_dict.get(header, "")
                    if isinstance(val, float):
                        # Format floats to reasonable precision, could do .6f or similar
                        out_row.append(f"{val:.6g}")
                    else:
                        out_row.append(str(val))
                writer.writerow(out_row)

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
            
            # Read all data rows
            rows = []
            for row in reader:
                if row and row[0]: # Check if row is not empty
                    rows.append(dict(zip(header, row)))
            
            if not rows:
                return None

            # Create instance from first row
            data_dict = rows[0]
            movement_type = data_dict.get('MovementType', data_dict.get('movement_type'))
            patient_id = data_dict.get('PatientId', data_dict.get('patient_id'))
            time_point = data_dict.get('TimePoint', data_dict.get('time_point', 'A0'))
            
            # Backward compatibility for polluted movement_type strings
            if movement_type and '/' in movement_type:
                parts = movement_type.split('/')
                if len(parts) >= 3:
                    movement_type = parts[-1]
                    if not patient_id: patient_id = parts[0]
                    if time_point == 'A0': time_point = parts[1]

            arom = cls(movement_type, patient_id=patient_id, time_point=time_point)
            arom.timestamp = datetime.fromisoformat(data_dict.get('DateTime', data_dict.get('datetime')))
            arom.plane_angle = float(data_dict.get('PlaneAngle', data_dict.get('plane_angle')))

            # Populate trial data from rows
            for d in rows:
                trial_label = d.get('TrialNumber', d.get('trial_number', ''))
                
                # Extract corner positions if they exist
                # Try CamelCase then snake_case
                ty = d.get('TopY', d.get('top_y'))
                tz = d.get('TopZ', d.get('top_z'))
                by = d.get('BottomY', d.get('bottom_y'))
                bz = d.get('BottomZ', d.get('bottom_z'))
                ly = d.get('LeftY', d.get('left_y'))
                lz = d.get('LeftZ', d.get('left_z'))
                ry = d.get('RightY', d.get('right_y'))
                rz = d.get('RightZ', d.get('right_z'))

                corners = None
                if ty:
                    corners = (
                        (float(ty), float(tz)),
                        (float(by), float(bz)),
                        (float(ly), float(lz)),
                        (float(ry), float(rz))
                    )

                if "Trial" in trial_label:
                    # Individual trial row
                    if corners:
                        arom.trial_corners_history.append(corners)
                    
                    # Convert cm to meters if loading old data
                    ml_val = d.get('MLRange', d.get('ml_range_cm'))
                    ap_val = d.get('APRange', d.get('ap_range_cm'))
                    if ml_val is not None and ap_val is not None:
                        is_old = 'ml_range_cm' in d
                        ml_float = float(ml_val)
                        ap_float = float(ap_val)
                        if is_old:
                            ml_float /= 100.0
                            ap_float /= 100.0
                        arom.trial_ranges.append((ml_float, ap_float))
                
                elif trial_label == "AVERAGE":
                    # Skip populating properties directly, they are calculated via trial_corners_history
                    pass
                
                elif trial_label == "MAXIMUM" or (not trial_label and not arom.adjusted_top):
                    # Maximum/Summary row or legacy single-row format
                    if corners:
                        arom.adjusted_top, arom.adjusted_bottom, arom.adjusted_left, arom.adjusted_right = corners
                        arom.raw_top, arom.raw_bottom, arom.raw_left, arom.raw_right = corners

            # Try to load raw trajectory from separate file if it exists
            try:
                filename = Path(filepath).name
                raw_filename = f"raw-{filename}"
                raw_filepath = Path(filepath).parent / raw_filename
                
                if raw_filepath.exists():
                    with open(raw_filepath, 'r') as rf:
                        raw_reader = csv.reader(rf)
                        next(raw_reader) # Skip header
                        arom.raw_trajectory = []
                        for row in raw_reader:
                            if len(row) >= 3:
                                arom.raw_trajectory.append([float(row[1]), float(row[2]), int(row[0])])
            except Exception as e:
                print(f"Error loading trajectory: {e}")

        return arom

    @staticmethod
    def find_latest_assessment(movement_type: str, base_dir: str = None,
                               patient_id: str = None, limb: str = None) -> 'MarsArom':
        """Find and load the most recent assessment of given type.

        Args:
            movement_type: Assessment type - "AP", "ML", or "MLAP"
            base_dir: Base directory for data storage (defaults to app data dir)
            patient_id: Optional patient ID to filter by
            limb: Optional limb ("LEFT"/"RIGHT") to filter by. When given with
                patient_id, the search spans both Screening and Assessment trees
                for that patient+limb, across all phases.

        Returns:
            MarsArom instance or None if not found
        """
        if base_dir is None:
            from app_paths import get_data_dir
            base_dir = str(get_data_dir())
        base_path = Path(base_dir)
        if not base_path.exists():
            return None

        name = movement_type.lower()
        # Determine search patterns
        if patient_id and limb:
            # patient+limb across any phase, both Screening and Assessment trees
            patterns = [
                f"Screening/{patient_id}/{limb}/*/{name}-*.csv",
                f"Assessment/{patient_id}/{limb}/*/*/{name}-*.csv",
            ]
        elif patient_id:
            # patient across any limb/phase in both trees
            patterns = [
                f"Screening/{patient_id}/*/*/{name}-*.csv",
                f"Assessment/{patient_id}/*/*/*/{name}-*.csv",
            ]
        else:
            # Recursive fallback
            patterns = [f"**/{name}-*.csv"]

        matching_files = []
        for pattern in patterns:
            matching_files.extend(base_path.glob(pattern))

        # Filter out "raw-" files
        matching_files = [p for p in matching_files if not p.name.startswith("raw-")]

        if not matching_files:
            return None

        # Sort by modification time, newest first
        latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)

        return MarsArom.load_from_csv(str(latest_file))
