"""Tests for display-only metre-to-centimetre conversion."""

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from display_units import format_centimeters, meters_to_centimeters
from mars_diagnostics import MarsDisplayWindow


class DisplayUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_distance_formatter_converts_metres_to_centimetres(self):
        self.assertEqual(meters_to_centimeters(0.1234), 12.34)
        self.assertEqual(format_centimeters(0.1234), "12.3 cm")
        self.assertEqual(format_centimeters(-0.005, 2), "-0.50 cm")

    def test_diagnostics_endpoint_values_are_displayed_in_centimetres(self):
        window = MarsDisplayWindow()
        window.mars = SimpleNamespace(
            angle1=0.0,
            angle2=0.0,
            angle3=0.0,
            angle4=0.0,
            imu_angle1=0.0,
            imu_angle2=0.0,
            imu_angle3=0.0,
            imu_angle4=0.0,
            force=0.0,
            target=0.0,
            desired=0.0,
            control=0.0,
            err_p=0.0,
            err_d=0.0,
            err_i=0.0,
            status=0,
            datatype=0,
            controltype=0,
            limb=0,
            error=0,
            packet_number=1,
            runtime=1.0,
            framerate=30.0,
            ep_pos=(0.1234, -0.5, 0.001),
            error_string="No Error",
        )

        try:
            window.update_display()
            self.assertEqual(window.value_labels["ep_x"].text(), "12.34")
            self.assertEqual(window.value_labels["ep_y"].text(), "-50.00")
            self.assertEqual(window.value_labels["ep_z"].text(), "0.10")
        finally:
            window.mars = None
            window.close()


if __name__ == "__main__":
    unittest.main()
