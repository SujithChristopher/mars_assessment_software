"""
MARS Workspace Assessment System - Main Launcher Window.

Professional application for clinical workspace assessments with three
assessment types: AP, ML, and MLAP.

Authors: Sivakumar Balasubramanian and Sujith Christopher
Date: 09 February 2026
Email: siva82kb@gmail.com, sujiht.christopher52@gmail.com
"""

import sys
import time
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QLabel, QComboBox,
                               QGroupBox, QMessageBox, QFrame, QLineEdit,
                               QStackedWidget, QScrollArea, QRadioButton,
                               QButtonGroup)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from qtmars import QtMars
from assessment_ap import AssessmentAPWindow
from assessment_ml import AssessmentMLWindow
from assessment_mlap import AssessmentMLAPWindow
from assessment_armweight import AssessmentArmWeightWindow
from assessment_discreach import AssessmentDiscreteReachWindow


class PatientEntryWidget(QWidget):
    """Initial scene for capturing patient ID and session info."""
    
    # Custom signal to notify when entry is complete
    # Emits (patient_id, time_point, is_demo)
    entry_complete = Signal(str, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Create patient entry UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        # Title
        title_label = QLabel("Patient Management")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Session Type (radio buttons)
        session_group = QGroupBox("Session Type")
        session_layout = QVBoxLayout(session_group)

        radio_row = QHBoxLayout()
        self.screening_radio = QRadioButton("Screening")
        self.assessment_radio = QRadioButton("Assessment")

        self._session_btn_group = QButtonGroup(self)
        self._session_btn_group.setExclusive(True)
        self._session_btn_group.addButton(self.screening_radio)
        self._session_btn_group.addButton(self.assessment_radio)

        radio_row.addWidget(self.screening_radio)
        radio_row.addWidget(self.assessment_radio)
        radio_row.addStretch()
        session_layout.addLayout(radio_row)

        # Assessment phase dropdown (only visible when Assessment selected)
        phase_row = QHBoxLayout()
        self._phase_label = QLabel("Phase:")
        self.phase_combo = QComboBox()
        self.phase_combo.addItems(["A0", "A1", "A2"])
        self.phase_combo.setMinimumHeight(35)
        phase_row.addWidget(self._phase_label)
        phase_row.addWidget(self.phase_combo, 1)
        session_layout.addLayout(phase_row)

        self._phase_label.setVisible(False)
        self.phase_combo.setVisible(False)

        layout.addWidget(session_group)

        # Connect radio clicks
        self._session_btn_group.buttonClicked.connect(self._on_session_type_clicked)
        self.phase_combo.currentIndexChanged.connect(self.update_lock_status)

        # Homer ID Field
        id_group = QGroupBox("Patient Registration")
        id_layout = QVBoxLayout(id_group)

        id_input_layout = QHBoxLayout()
        id_input_layout.addWidget(QLabel("HOMER ID / Patient ID:"))
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Enter Homer / Patient ID (e.g. HOMER_001)")
        self.id_input.setMinimumHeight(35)
        self.id_input.textChanged.connect(self.update_lock_status)
        id_input_layout.addWidget(self.id_input)

        self.demo_btn = QPushButton("Demo Mode")
        self.demo_btn.setToolTip("Skip registration - data will not be saved")
        self.demo_btn.setFixedWidth(100)
        self.demo_btn.clicked.connect(self.on_demo_clicked)
        id_input_layout.addWidget(self.demo_btn)

        id_layout.addLayout(id_input_layout)
        layout.addWidget(id_group)

        # Lock Status Label
        self.lock_label = QLabel("⚠️ This time point is LOCKED and cannot be modified.")
        self.lock_label.setStyleSheet("color: #f44336; font-weight: bold; margin-bottom: 5px;")
        self.lock_label.setAlignment(Qt.AlignCenter)
        self.lock_label.setVisible(False)
        layout.addWidget(self.lock_label)

        # Enter Button
        self.enter_btn = QPushButton("Enter Launcher")
        self.enter_btn.setMinimumHeight(45)
        self.enter_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.enter_btn.clicked.connect(self.on_enter_clicked)
        layout.addWidget(self.enter_btn)

        layout.addStretch()

    def _on_session_type_clicked(self, button):
        """Show alert and update UI when user picks Screening or Assessment."""
        is_screening = (button is self.screening_radio)
        self._phase_label.setVisible(not is_screening)
        self.phase_combo.setVisible(not is_screening)
        self.update_lock_status()

        if is_screening:
            QMessageBox.information(
                self, "Screening Selected",
                "You have selected Screening.\n\n"
                "Only AP, ML, and MLAP workspace assessments are available.\n"
                "Arm Weight and Discrete Reaching are not performed at this stage."
            )
        else:
            QMessageBox.information(
                self, "Assessment Selected",
                "You have selected Assessment.\n\n"
                "All assessments are available.\n"
                "Please choose the assessment phase (A0, A1, or A2) below."
            )

    def _current_time_point(self):
        """Return selected time point string, or None if nothing selected."""
        if self.screening_radio.isChecked():
            return "Screening"
        if self.assessment_radio.isChecked():
            return self.phase_combo.currentText()
        return None

    def on_demo_clicked(self):
        """Handle demo button click."""
        # Use 'demo' as patient_id and 'A0' as default time_point for demo sessions
        # This allows saving data to data/demo/A0/session...
        self.entry_complete.emit("demo", "A0", True)

    def on_enter_clicked(self):
        """Handle enter button click."""
        time_point = self._current_time_point()
        if time_point is None:
            QMessageBox.warning(self, "No Session Type", "Please select Screening or Assessment.")
            return

        patient_id = self.id_input.text().strip()
        if not patient_id:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid HOMER ID or use Demo mode.")
            return

        self.entry_complete.emit(patient_id, time_point, False)

    def update_lock_status(self, _index=None):
        """Check if selected time point is locked."""
        patient_id = self.id_input.text().strip()
        time_point = self._current_time_point()

        if not patient_id or time_point is None:
            self.lock_label.setVisible(False)
            self.enter_btn.setEnabled(True)
            return

        from app_paths import get_lock_file
        lock_file = get_lock_file(patient_id, time_point)

        if lock_file.exists():
            self.lock_label.setVisible(True)
            self.enter_btn.setEnabled(False)
            self.enter_btn.setStyleSheet("background-color: #cccccc; color: grey;")
        else:
            self.lock_label.setVisible(False)
            self.enter_btn.setEnabled(True)
            self.enter_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-size: 11pt;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)


class MarsAssessmentLauncher(QMainWindow):
    """Main launcher window for MARS workspace assessments."""

    def __init__(self):
        super().__init__()
        self.mars = None
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)

        # Plane setup timer
        self._plane_timer = QTimer()
        self._plane_setup_attempts = 0

        # Session state
        self.patient_id = None
        self.time_point = "A0"
        self.is_demo = False
        # Session folder name resolved lazily per (limb, time_point) at launch,
        # so all assessments of one visit+limb share a folder. See
        # _resolve_session_subdir().
        self.session_cache = {}

        # Assessment windows
        self.ap_window = None
        self.ml_window = None
        self.mlap_window = None
        self.aw_window = None
        self.dr_window = None

        # Completion tracking
        self.completed_assessments = set()
        self.assessment_btns = {} # type -> QPushButton (main)
        self.redo_btns = {}       # type -> QPushButton (redo)
        self.assessment_rows = {} # type -> QWidget (row container)

        # Assessments not available during Screening
        self.screening_excluded = {"ArmWeight", "DiscreteReaching"}

        self.init_ui()
        self.populate_com_ports()

    def init_ui(self):
        """Create main window UI with stacked widget."""
        self.setWindowTitle("MARS Workspace Assessment System")
        self.setMinimumSize(500, 400)  # Allow shrinking on small displays
        self.resize(650, 800)          # Preferred size

        # Stacked widget for scene management
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Scene 1: Patient Entry
        self.entry_widget = PatientEntryWidget()
        self.entry_widget.entry_complete.connect(self.start_main_launcher)
        self.stack.addWidget(self.entry_widget)

        # Scene 2: Main Launcher Content (wrapped in scroll area so it stays
        # usable on small displays where the full content would be cropped)
        self.launcher_widget = QWidget()
        main_layout = QVBoxLayout(self.launcher_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.launcher_scroll = QScrollArea()
        self.launcher_scroll.setWidgetResizable(True)
        self.launcher_scroll.setFrameShape(QFrame.NoFrame)
        self.launcher_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.launcher_scroll.setWidget(self.launcher_widget)
        self.stack.addWidget(self.launcher_scroll)

        # Connection Group
        conn_group = QGroupBox("Device Connection")
        conn_layout = QVBoxLayout(conn_group)

        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        port_layout.addWidget(self.port_combo, 1)
        self.refresh_ports_btn = QPushButton("⟳")
        self.refresh_ports_btn.setFixedWidth(40)
        self.refresh_ports_btn.clicked.connect(self.populate_com_ports)
        port_layout.addWidget(self.refresh_ports_btn)
        conn_layout.addLayout(port_layout)

        # Connect button and status
        connect_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        connect_layout.addWidget(self.connect_btn)

        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        connect_layout.addWidget(self.status_label)
        connect_layout.addStretch()
        conn_layout.addLayout(connect_layout)

        main_layout.addWidget(conn_group)

        # Configuration Group
        config_group = QGroupBox("Device Configuration")
        config_layout = QVBoxLayout(config_group)

        # Limb selection
        limb_layout = QHBoxLayout()
        limb_layout.addWidget(QLabel("Limb:"))
        self.limb_combo = QComboBox()
        self.limb_combo.addItems(["RIGHT", "LEFT"])
        self.limb_combo.currentTextChanged.connect(self.on_limb_changed)
        limb_layout.addWidget(self.limb_combo)
        limb_layout.addStretch()
        config_layout.addLayout(limb_layout)

        # Calibrate button
        self.calibrate_btn = QPushButton("Calibrate Device")
        self.calibrate_btn.clicked.connect(self.on_calibrate)
        self.calibrate_btn.setEnabled(False)
        config_layout.addWidget(self.calibrate_btn)
        
        # Inline calibration status label
        self.calib_status_label = QLabel("Calibration Status: Not Calibrated")
        self.calib_status_label.setStyleSheet("color: #757575; font-style: italic;")
        self.calib_status_label.setAlignment(Qt.AlignCenter)
        self.calib_status_label.setWordWrap(True)
        config_layout.addWidget(self.calib_status_label)

        # Set plane button
        self.set_plane_btn = QPushButton("Set Plane (90°)")
        self.set_plane_btn.clicked.connect(self.on_set_plane)
        self.set_plane_btn.setEnabled(False)
        config_layout.addWidget(self.set_plane_btn)

        # Real-time angle display
        self.angle_display_label = QLabel("Current Angle: --°")
        self.angle_display_label.setStyleSheet("color: #757575; font-size: 10pt; font-weight: bold;")
        self.angle_display_label.setAlignment(Qt.AlignCenter)
        config_layout.addWidget(self.angle_display_label)

        main_layout.addWidget(config_group)

        # Workspace Assessments Group
        assess_group = QGroupBox("Workspace Assessments")
        self.assess_layout = QVBoxLayout(assess_group)
        self.assess_layout.setSpacing(25)

        # AP Assessment Row
        self.add_assessment_row("AP", "↕  Assess Anterior-Posterior", "(Forward/Backward Movement)", self.launch_ap_assessment)
        
        # ML Assessment Row
        self.add_assessment_row("ML", "↔  Assess Medio-Lateral", "(Side-to-Side Movement)", self.launch_ml_assessment)
        
        # MLAP Assessment Row
        self.add_assessment_row("MLAP", "⊕  Assess Combined (MLAP)", "(Full Workspace Envelope)", self.launch_mlap_assessment)
        
        # Arm Weight Assessment Row
        self.add_assessment_row("ArmWeight", "⚖  Assess Arm Weight", "(Force recording at 5 targets)", self.launch_arm_weight_assessment)
        
        # Discrete Reaching Assessment Row
        self.add_assessment_row("DiscreteReaching", "⊕  Assess Discrete Reaching", "(Home to 75% workspace targets)", self.launch_discrete_reach_assessment)

        main_layout.addWidget(assess_group)

        # Session Finalization Group
        lock_group = QGroupBox("Session Finalization")
        lock_layout = QVBoxLayout(lock_group)
        
        self.lock_btn = QPushButton("Complete & Lock All Assessments")
        self.lock_btn.setMinimumHeight(50)
        self.lock_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.lock_btn.clicked.connect(self.on_complete_and_lock)
        lock_layout.addWidget(self.lock_btn)
        
        main_layout.addWidget(lock_group)
        main_layout.addStretch()

    def start_main_launcher(self, patient_id, time_point, is_demo):
        """Transition from patient entry to main assessment launcher."""
        self.patient_id = patient_id
        self.time_point = time_point
        self.is_demo = is_demo

        # Session folder is resolved per-limb at assessment launch (limb is
        # chosen on this launcher screen, not here). Clear any cached names
        # from a previous patient/visit.
        self.session_cache = {}

        # Add session info to title
        session_info = f"[Demo Mode]" if is_demo else f"[Patient: {patient_id} | {time_point}]"
        self.setWindowTitle(f"MARS Assessment Launcher {session_info}")
        
        # Switch to launcher scene
        self.stack.setCurrentWidget(self.launcher_scroll)

        # Screening only allows AP, ML, MLAP. Hide the rest.
        is_screening = (time_point == "Screening")
        for a_type, row in self.assessment_rows.items():
            row.setVisible(not (is_screening and a_type in self.screening_excluded))
        
        # Disable lock button in demo mode
        self.lock_btn.setEnabled(not is_demo)
        if is_demo:
            self.lock_btn.setToolTip("Locking is disabled in Demo Mode")
        else:
            self.lock_btn.setToolTip("Finalize and lock this time point for this patient")

        print(f"Session started: {session_info}")

    def _resolve_session_subdir(self, limb: str) -> str:
        """Resolve (and cache) the session folder name for the current
        patient + given limb + time point.

        All assessments launched for the same limb during one visit reuse the
        same ``session<N>-<date>`` folder. The number auto-increments past any
        existing session folder that already holds CSV files.
        """
        key = (limb, self.time_point)
        if key in self.session_cache:
            return self.session_cache[key]

        from datetime import datetime
        from app_paths import get_assessment_dir
        date_str = datetime.now().strftime("%Y-%m-%d")
        parent_dir = get_assessment_dir(self.patient_id, limb, self.time_point)
        parent_dir.mkdir(parents=True, exist_ok=True)

        session_num = 1
        while True:
            candidate = parent_dir / f"session{session_num}-{date_str}"
            if not candidate.exists():
                subdir = f"session{session_num}-{date_str}"
                break
            if list(candidate.glob("*.csv")):
                session_num += 1
            else:
                subdir = f"session{session_num}-{date_str}"
                break

        self.session_cache[key] = subdir
        print(f"Resolved session folder for {limb}/{self.time_point}: {subdir}")
        return subdir

    def add_assessment_row(self, assess_type: str, title: str, subtitle: str, callback):
        """Add a row with main button and redo button.
        
        Args:
            assess_type: Unique identifier (AP, ML, MLAP, DiscreteReaching)
            title: Title for main button
            subtitle: Subtitle for main button
            callback: Function to launch assessment
        """
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(20)

        # Main button
        btn = QPushButton(f"{title}\n{subtitle}")
        btn.setMinimumHeight(60)
        btn.clicked.connect(callback)
        btn.setEnabled(False)
        row_layout.addWidget(btn, 1) # Give main button more space
        self.assessment_btns[assess_type] = btn

        # Redo button
        redo_btn = QPushButton("Redo")
        redo_btn.setMinimumHeight(60)
        redo_btn.setFixedWidth(80)
        redo_btn.clicked.connect(callback)
        redo_btn.setEnabled(False)
        redo_btn.setVisible(False) # Only show when completed
        row_layout.addWidget(redo_btn)
        self.redo_btns[assess_type] = redo_btn

        self.assessment_rows[assess_type] = row_widget
        self.assess_layout.addWidget(row_widget)

    def update_assessment_status(self, assess_type: str):
        """Update button style when assessment is completed.
        
        Args:
            assess_type: Type of assessment completed
        """
        print(f"Updating status for: {assess_type}")
        self.completed_assessments.add(assess_type)
        
        if assess_type in self.assessment_btns:
            btn = self.assessment_btns[assess_type]
            # Use green background for completed
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            
            # Show redo button
            if assess_type in self.redo_btns:
                self.redo_btns[assess_type].setVisible(True)
                self.redo_btns[assess_type].setEnabled(True)

    def connect_assessment_signals(self, window):
        """Connect completion signal from assessment window.
        
        Args:
            window: Assessment window instance
        """
        if hasattr(window, 'assessment_finished'):
            window.assessment_finished.connect(self.update_assessment_status)

    def populate_com_ports(self):
        """Populate COM port dropdown with available ports."""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)

        if self.port_combo.count() == 0:
            self.port_combo.addItem("No ports found")

    def toggle_connection(self):
        """Toggle device connection."""
        if self.mars is None:
            self.connect_device()
        else:
            self.disconnect_device()

    def connect_device(self):
        """Connect to MARS device."""
        port = self.port_combo.currentText()

        if port == "No ports found":
            QMessageBox.warning(self, "Connection Error",
                              "No COM ports available. Please check device connection.")
            return

        try:
            self.mars = QtMars(port=port, baudrate=115200, auto_heartbeat=False,
                               patient_id=self.patient_id, time_point=self.time_point)

            if not self.mars.is_connected():
                QMessageBox.critical(self, "Connection Error",
                                   f"Failed to connect to {port}.\n"
                                   "Please check:\n"
                                   "- Device is powered on\n"
                                   "- Correct COM port selected\n"
                                   "- No other application using the port")
                self.mars = None
                return

            # Connection sequence
            self.mars.get_version()
            time.sleep(0.05)
            self.mars.start_sensorstream()
            time.sleep(0.05)
            self.mars.set_diagnostic_mode()
            time.sleep(0.05)
            self.mars.send_heartbeat()
            time.sleep(0.05)
            
            # Send initial limb choice
            self.mars.set_limb(self.limb_combo.currentText())

            # Start heartbeat timer (every 3 seconds)
            self.heartbeat_timer.start(3000)

            # Connect data stream for angle updating
            self.mars.newdata.connect(self.update_angle_display)

            # Update UI
            self.connect_btn.setText("Disconnect")
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.port_combo.setEnabled(False)
            self.refresh_ports_btn.setEnabled(False)

            # Enable configuration controls
            self.calibrate_btn.setEnabled(True)
            self.set_plane_btn.setEnabled(True)
            
            # Reset calibration status
            self.calib_status_label.setText("Calibration Status: Not Calibrated")
            self.calib_status_label.setStyleSheet("color: #757575; font-style: italic;")

            # Enable assessment buttons
            for btn in self.assessment_btns.values():
                btn.setEnabled(True)
            for redo_btn in self.redo_btns.values():
                # Find key for this button
                a_type = [k for k, v in self.redo_btns.items() if v == redo_btn][0]
                if a_type in self.completed_assessments:
                    redo_btn.setEnabled(True)

            print(f"Connected to MARS device on {port}")

        except Exception as e:
            QMessageBox.critical(self, "Connection Error",
                               f"Connection failed: {str(e)}")
            self.mars = None

    def disconnect_device(self):
        """Disconnect from MARS device."""
        if self.mars:
            self.heartbeat_timer.stop()
            self.mars.stop_sensorstream()
            self.mars.close()
            self.mars = None

            # Update UI
            self.connect_btn.setText("Connect")
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            self.port_combo.setEnabled(True)
            self.refresh_ports_btn.setEnabled(True)

            # Disable configuration controls
            self.calibrate_btn.setEnabled(False)
            self.set_plane_btn.setEnabled(False)
            self.calib_status_label.setText("Calibration Status: Not Calibrated")
            self.calib_status_label.setStyleSheet("color: #757575; font-style: italic;")
            self.angle_display_label.setText("Current Angle: --°")

            # Disable assessment buttons
            for btn in self.assessment_btns.values():
                btn.setEnabled(False)
            for redo_btn in self.redo_btns.values():
                redo_btn.setEnabled(False)

            print("Disconnected from MARS device")

    def send_heartbeat(self):
        """Send periodic heartbeat to device."""
        if self.mars and self.mars.is_connected():
            self.mars.send_heartbeat()

    def on_limb_changed(self, limb: str):
        """Handle limb selection change.

        Args:
            limb: Selected limb ("LEFT" or "RIGHT")
        """
        if self.mars and self.mars.is_connected():
            try:
                self.mars.set_limb(limb)
                print(f"Limb set to: {limb}")
            except Exception as e:
                QMessageBox.warning(self, "Command Error",
                                  f"Failed to set limb: {str(e)}")

    def update_angle_display(self):
        """Update real-time angle display."""
        if self.mars and self.mars.is_connected() and self.mars.is_data_available():
            # Update the angle label with the base joint angle (plane angle)
            self.angle_display_label.setText(f"Current Angle: {self.mars.angle1:.1f}°")

    def on_calibrate(self):
        """Handle calibrate button click."""
        if self.mars and self.mars.is_connected():
            try:
                self.calib_status_label.setText("Waiting for MARS button to be pressed.")
                self.calib_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
                
                # Disconnect if previously connected to avoid multiple connections
                try:
                    self.mars.btnreleased.disconnect(self._do_calibrate)
                except Exception:
                    pass
                # Connect the signal
                self.mars.btnreleased.connect(self._do_calibrate)
                print("Waiting for physical button press to calibrate...")
            except Exception as e:
                self.calib_status_label.setText(f"Setup Error: {str(e)}")
                self.calib_status_label.setStyleSheet("color: #f44336; font-weight: bold;")

    def _do_calibrate(self):
        """Helper to send calibration command when physical button is pressed."""
        if self.mars and self.mars.is_connected():
            try:
                self.calib_status_label.setText("Calibrating...")
                self.calib_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
                
                self.mars.calibrate()
                print("Calibration command sent via physical button press.")
                try:
                    self.mars.btnreleased.disconnect(self._do_calibrate)
                except Exception:
                    pass
                # Check for calibration success via a short delay
                QTimer.singleShot(500, self._check_calibration_success)
            except Exception as e:
                print(f"Error sending calibration command: {e}")
                self.calib_status_label.setText("Error during calibration.")
                self.calib_status_label.setStyleSheet("color: #f44336; font-weight: bold;")

    def _check_calibration_success(self):
        """Check if calibration was successful."""
        if self.mars and self.mars.is_connected():
            if getattr(self.mars, 'calibration', 0) == 1:
                self.calib_status_label.setText("Calibration Successful ✓")
                self.calib_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.calib_status_label.setText("Calibration Failed. Keep still & retry.")
                self.calib_status_label.setStyleSheet("color: #f44336; font-weight: bold;")


    def on_set_plane(self):
        """Handle set plane button click - sets robot to -90 degrees.

        Note: Device should be calibrated before using this function.
        The robot will move to -90 degrees position (vertical plane).
        Target value is negative following mars_diagnostics.py convention.
        """
        if self.mars and self.mars.is_connected():
            try:
                # Ensure device is calibrated before setting position mode
                if getattr(self.mars, 'calibration', 0) == 0:
                    QMessageBox.warning(self, "Not Calibrated", "Please calibrate the device first.")
                    return

                # Repeatedly try to set control type and target
                self._plane_setup_attempts = 0
                self._plane_timer = QTimer()
                self._plane_timer.timeout.connect(self._plane_setup_step)
                self._plane_timer.start(100) # Check every 100ms

            except Exception as e:
                QMessageBox.warning(self, "Command Error",
                                  f"Failed to start setting plane: {str(e)}")

    def _plane_setup_step(self):
        """Helper to set plane target by confirming control type first."""
        if not self.mars or not self.mars.is_connected():
            self._plane_timer.stop()
            return
            
        try:
            # First ensure control type is POSITION
            if self.mars.controltype != 1: # 1 is POSITION mode
                self.mars.set_control_type("POSITION")
                self._plane_setup_attempts += 1
                if self._plane_setup_attempts > 20: # Timeout after 2 seconds
                    self._plane_timer.stop()
                    QMessageBox.warning(self, "Timeout", "Failed to set POSITION mode. Please check if device is calibrated properly.")
                return
            
            # Control type is now POSITION, so we can safely set target
            self.mars.set_control_target(-90.0)
            print("Plane target value sent: -90.0")
            self._plane_timer.stop()
        except Exception as e:
            print(f"Error setting control target: {e}")
            self._plane_timer.stop()

    def launch_ap_assessment(self):
        """Launch AP (Anterior-Posterior) assessment window."""
        if not self.mars or not self.mars.is_connected():
            QMessageBox.warning(self, "Connection Required",
                              "Please connect to device before starting assessment.")
            return

        if self.ap_window is None or not self.ap_window.isVisible():
            limb = self.limb_combo.currentText()
            session_subdir = self._resolve_session_subdir(limb)
            self.ap_window = AssessmentAPWindow(self.mars, self.patient_id, self.time_point, self.is_demo, session_subdir, self, limb)
            self.connect_assessment_signals(self.ap_window)
            self.ap_window.show()
            print("Launched AP assessment window")

    def launch_ml_assessment(self):
        """Launch ML (Medio-Lateral) assessment window."""
        if not self.mars or not self.mars.is_connected():
            QMessageBox.warning(self, "Connection Required",
                              "Please connect to device before starting assessment.")
            return

        if self.ml_window is None or not self.ml_window.isVisible():
            limb = self.limb_combo.currentText()
            session_subdir = self._resolve_session_subdir(limb)
            self.ml_window = AssessmentMLWindow(self.mars, self.patient_id, self.time_point, self.is_demo, session_subdir, self, limb)
            self.connect_assessment_signals(self.ml_window)
            self.ml_window.show()
            print("Launched ML assessment window")

    def launch_mlap_assessment(self):
        """Launch MLAP (Combined) assessment window."""
        if not self.mars or not self.mars.is_connected():
            QMessageBox.warning(self, "Connection Required",
                              "Please connect to device before starting assessment.")
            return

        if self.mlap_window is None or not self.mlap_window.isVisible():
            limb = self.limb_combo.currentText()
            session_subdir = self._resolve_session_subdir(limb)
            self.mlap_window = AssessmentMLAPWindow(self.mars, self.patient_id, self.time_point, self.is_demo, session_subdir, self, limb)
            self.connect_assessment_signals(self.mlap_window)
            self.mlap_window.show()
            print("Launched MLAP assessment window")

    def on_complete_and_lock(self):
        """Ask for confirmation and lock the session."""
        reply = QMessageBox.warning(self, "Confirm Finalization",
                                   f"Are you sure you want to COMPLETE and LOCK all assessments for "
                                   f"Patient: {self.patient_id}, Time Point: {self.time_point}?\n\n"
                                   "WARNING: You will NOT be able to add or modify any data for this "
                                   "specific time point once locked.",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.lock_session()
            QMessageBox.information(self, "Session Locked", 
                                  f"Assessment phase {self.time_point} for patient {self.patient_id} has been locked.")
            # Return to entry screen
            self.patient_id = None
            self.session_cache = {}
            self.completed_assessments.clear()
            # Reset button styles
            for btn in self.assessment_btns.values():
                btn.setStyleSheet("")
            for btn in self.redo_btns.values():
                btn.setVisible(False)
            
            self.entry_widget.id_input.clear()
            self.stack.setCurrentWidget(self.entry_widget)

    def lock_session(self):
        """Create the lock marker for this patient's time point (both limbs)."""
        from datetime import datetime
        from app_paths import get_lock_file
        lock_file = get_lock_file(self.patient_id, self.time_point)
        lock_file.parent.mkdir(parents=True, exist_ok=True)

        with open(lock_file, "w") as f:
            f.write(f"Locked on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"Locked session: {lock_file}")

    def launch_arm_weight_assessment(self):
        """Launch Arm Weight assessment window."""
        if not self.mars or not self.mars.is_connected():
            QMessageBox.warning(self, "Connection Required",
                              "Please connect to device before starting assessment.")
            return

        limb = self.limb_combo.currentText()

        # Check if MLAP data exists (required for targets) for this patient + limb
        from mars_arom_data import MarsArom
        if MarsArom.find_latest_assessment("MLAP", patient_id=self.patient_id, limb=limb) is None:
            QMessageBox.warning(self, "MLAP Data Required",
                              f"No MLAP assessment found for {limb} limb. Arm Weight requires MLAP targets.")
            return

        if self.aw_window is None or not self.aw_window.isVisible():
            session_subdir = self._resolve_session_subdir(limb)
            self.aw_window = AssessmentArmWeightWindow(self.mars, self.patient_id, self.time_point, self.is_demo, session_subdir, self, limb)
            self.connect_assessment_signals(self.aw_window)
            self.aw_window.show()
            print("Launched Arm Weight assessment window")

    def launch_discrete_reach_assessment(self):
        """Launch Discrete Reaching assessment window."""
        if not self.mars or not self.mars.is_connected():
            QMessageBox.warning(self, "Connection Required",
                              "Please connect to device before starting assessment.")
            return

        limb = self.limb_combo.currentText()

        # Check if MLAP data exists (required for targets) for this patient + limb
        from mars_arom_data import MarsArom
        if MarsArom.find_latest_assessment("MLAP", patient_id=self.patient_id, limb=limb) is None:
            reply = QMessageBox.question(self, "MLAP Data Required",
                                       f"No MLAP assessment found for {limb} limb. Discrete reaching requires MLAP targets.\n\n"
                                       "Do you want to launch it anyway?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        if self.dr_window is None or not self.dr_window.isVisible():
            session_subdir = self._resolve_session_subdir(limb)
            self.dr_window = AssessmentDiscreteReachWindow(self.mars, self.patient_id, self.time_point, self.is_demo, session_subdir, self, limb)
            self.connect_assessment_signals(self.dr_window)
            self.dr_window.show()
            print("Launched Discrete Reaching assessment window")

    def closeEvent(self, event):
        """Handle window close event."""
        self.disconnect_device()
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MarsAssessmentLauncher()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
