"""Detailed UI test to check layout and visibility."""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from mars_assessment import MarsAssessmentLauncher

def check_ui(window):
    """Check UI after it's fully initialized."""
    print(f"\n=== UI DEBUGGING INFO ===")
    print(f"Window size: {window.width()}x{window.height()}")
    print(f"Window visible: {window.isVisible()}")

    # Check buttons directly
    print(f"\n--- Buttons ---")
    print(f"Connect button: exists={window.connect_btn is not None}, visible={window.connect_btn.isVisible()}, enabled={window.connect_btn.isEnabled()}")
    print(f"  Size: {window.connect_btn.width()}x{window.connect_btn.height()}")
    print(f"  Position: ({window.connect_btn.x()}, {window.connect_btn.y()})")
    print(f"  Text: '{window.connect_btn.text()}'")

    print(f"\nCalibrate button: exists={window.calibrate_btn is not None}, visible={window.calibrate_btn.isVisible()}, enabled={window.calibrate_btn.isEnabled()}")
    print(f"  Size: {window.calibrate_btn.width()}x{window.calibrate_btn.height()}")
    print(f"  Position: ({window.calibrate_btn.x()}, {window.calibrate_btn.y()})")

    print(f"\nAP button: exists={window.ap_btn is not None}, visible={window.ap_btn.isVisible()}, enabled={window.ap_btn.isEnabled()}")
    print(f"  Size: {window.ap_btn.width()}x{window.ap_btn.height()}")
    print(f"  Position: ({window.ap_btn.x()}, {window.ap_btn.y()})")
    print(f"  Text: '{window.ap_btn.text()}'")

    print(f"\nML button: exists={window.ml_btn is not None}, visible={window.ml_btn.isVisible()}, enabled={window.ml_btn.isEnabled()}")
    print(f"  Size: {window.ml_btn.width()}x{window.ml_btn.height()}")
    print(f"  Position: ({window.ml_btn.x()}, {window.ml_btn.y()})")

    print(f"\nMLAP button: exists={window.mlap_btn is not None}, visible={window.mlap_btn.isVisible()}, enabled={window.mlap_btn.isEnabled()}")
    print(f"  Size: {window.mlap_btn.width()}x{window.mlap_btn.height()}")
    print(f"  Position: ({window.mlap_btn.x()}, {window.mlap_btn.y()})")

    # Check status label
    print(f"\n--- Status Label ---")
    print(f"Status label: visible={window.status_label.isVisible()}, text='{window.status_label.text()}'")

    print(f"\n=== END DEBUG INFO ===\n")
    print("UI is displayed. You can interact with it now.")
    print("Close the window when done...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MarsAssessmentLauncher()
    window.show()

    # Check UI after a short delay to ensure it's fully rendered
    QTimer.singleShot(500, lambda: check_ui(window))

    sys.exit(app.exec())
