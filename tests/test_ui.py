"""Quick UI test to verify button visibility."""
import sys
from PySide6.QtWidgets import QApplication
from mars_assessment import MarsAssessmentLauncher

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MarsAssessmentLauncher()

    # Print widget geometry for debugging
    print(f"Window size: {window.width()}x{window.height()}")
    print(f"Connection group visible: {window.findChild(type(window), 'Device Connection') is not None}")
    print(f"Connect button visible: {window.connect_btn.isVisible()}")
    print(f"AP button visible: {window.ap_btn.isVisible()}")
    print(f"ML button visible: {window.ml_btn.isVisible()}")
    print(f"MLAP button visible: {window.mlap_btn.isVisible()}")

    window.show()
    print("\nUI displayed successfully!")
    print("Close the window to continue...")

    sys.exit(app.exec())
