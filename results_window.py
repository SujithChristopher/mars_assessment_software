"""
Screening Results Viewer.

Read-only window showing basic AROM statistics (AP and ML) for the most
recent screening assessment of a given patient + limb. Launched from the
main launcher's "View Results" button (Screening only).
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QPushButton, QGroupBox, QGridLayout,
                               QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from mars_arom_data import MarsArom


class ResultsWindow(QDialog):
    """Read-only viewer for screening AROM stats (AP and ML)."""

    def __init__(self, patient_id: str, limb: str, parent=None):
        super().__init__(parent)
        self.patient_id = patient_id
        self.limb = limb

        self.setWindowTitle(f"Screening Results - {patient_id}")
        self.setMinimumSize(480, 420)

        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Screening AROM Results")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.subtitle = QLabel()
        self.subtitle.setStyleSheet("color: #757575;")
        self.subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle)

        # Limb selector (lets the clinician flip between limbs without reopening)
        limb_row = QHBoxLayout()
        limb_row.addStretch()
        limb_row.addWidget(QLabel("Limb:"))
        self.limb_combo = QComboBox()
        self.limb_combo.addItems(["RIGHT", "LEFT"])
        self.limb_combo.setCurrentText(self.limb)
        self.limb_combo.currentTextChanged.connect(self._on_limb_changed)
        limb_row.addWidget(self.limb_combo)
        limb_row.addStretch()
        layout.addLayout(limb_row)

        # Stats cards (populated in refresh)
        self.ap_group = self._make_stat_group("AP  (Anterior-Posterior)")
        self.ml_group = self._make_stat_group("ML  (Medio-Lateral)")
        layout.addWidget(self.ap_group["box"])
        layout.addWidget(self.ml_group["box"])

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(38)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _make_stat_group(self, header: str) -> dict:
        """Build a group box with labelled value fields. Returns refs for update."""
        box = QGroupBox(header)
        grid = QGridLayout(box)
        grid.setColumnStretch(1, 1)

        fields = {}
        rows = [
            ("trials", "Trials:"),
            ("avg", "Average Range:"),
            ("max", "Maximum Range:"),
            ("date", "Assessed:"),
        ]
        for r, (key, label) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #555;")
            val = QLabel("-")
            val.setFont(QFont("Segoe UI", 10, QFont.Bold))
            grid.addWidget(lbl, r, 0)
            grid.addWidget(val, r, 1)
            fields[key] = val

        return {"box": box, "fields": fields}

    def _on_limb_changed(self, limb: str):
        self.limb = limb
        self.refresh()

    def refresh(self):
        """Reload latest AP/ML assessments for current patient + limb."""
        self.subtitle.setText(f"Patient: {self.patient_id}   |   Limb: {self.limb}")

        ap = MarsArom.find_latest_assessment("AP", patient_id=self.patient_id, limb=self.limb)
        ml = MarsArom.find_latest_assessment("ML", patient_id=self.patient_id, limb=self.limb)

        # AP card shows the AP range; ML card shows the ML range (each
        # assessment's primary axis). Ranges stored in meters -> show cm.
        self._fill_card(self.ap_group["fields"], ap, axis="ap")
        self._fill_card(self.ml_group["fields"], ml, axis="ml")

    def _fill_card(self, fields: dict, arom: 'MarsArom', axis: str):
        if arom is None:
            for v in fields.values():
                v.setText("No data")
                v.setStyleSheet("color: #f44336;")
            return

        n_trials = len(arom.trial_ranges)
        if axis == "ap":
            avg_m = arom.average_ap_range
            max_m = arom.ap_range
        else:
            avg_m = arom.average_ml_range
            max_m = arom.ml_range

        fields["trials"].setText(str(n_trials))
        fields["avg"].setText(f"{avg_m * 100:.1f} cm")
        fields["max"].setText(f"{max_m * 100:.1f} cm")
        fields["date"].setText(arom.timestamp.strftime("%Y-%m-%d %H:%M"))
        for v in fields.values():
            v.setStyleSheet("color: #2e7d32;")
