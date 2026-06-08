
import os
import csv
from pathlib import Path
from datetime import datetime
from mars_arom_data import MarsArom

def test_multi_row_loading():
    print("Testing Multi-row CSV Loading...")
    
    # 1. Create a dummy multi-row AROM summary
    test_dir = Path("tmp_test_data")
    test_dir.mkdir(exist_ok=True)
    
    summary_path = test_dir / "mlap_test_summary.csv"
    raw_path = test_dir / "raw-mlap_test_summary.csv"
    
    now_iso = datetime.now().isoformat()
    
    # Summary CSV with 2 trials and an AVERAGE row
    header = ["DateTime", "PlaneAngle", "MovementType", "PatientId", "TimePoint", "TrialNumber", 
              "MLRange", "APRange", "TopY", "TopZ", "BottomY", "BottomZ", "LeftY", "LeftZ", "RightY", "RightZ"]
    
    # Trial 1: (0, 0.4), (0, 0), (-0.2, 0.2), (0.2, 0.2) -> ML Range: 0.4, AP Range: 0.4
    t1 = [now_iso, "-90.0", "MLAP", "test_id", "A0", "Trial 1", "0.4", "0.4", "0.0", "0.4", "0.0", "0.0", "-0.2", "0.2", "0.2", "0.2"]
    # Trial 2: (0, 0.5), (0, 0.1), (-0.3, 0.3), (0.3, 0.3) -> ML Range: 0.6, AP Range: 0.4
    t2 = [now_iso, "-90.0", "MLAP", "test_id", "A0", "Trial 2", "0.6", "0.4", "0.0", "0.5", "0.0", "0.1", "-0.3", "0.3", "0.3", "0.3"]
    # Average: (0, 0.45), (0, 0.05), (-0.25, 0.25), (0.25, 0.25) -> ML Range: 0.5, AP Range: 0.4
    avg = [now_iso, "-90.0", "MLAP", "test_id", "A0", "AVERAGE", "0.5", "0.4", "0.0", "0.45", "0.0", "0.05", "-0.25", "0.25", "0.25", "0.25"]
    
    with open(summary_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerow(t1)
        writer.writerow(t2)
        writer.writerow(avg)
        
    # 2. Load the CSV
    print(f"Loading from {summary_path}...")
    arom = MarsArom.load_from_csv(str(summary_path))
    
    if not arom:
        print("FAILED: MarsArom.load_from_csv returned None")
        return

    # 3. Verify Trial History
    print(f"Trials loaded: {len(arom.trial_corners_history)}")
    if len(arom.trial_corners_history) != 2:
        print(f"FAILED: Expected 2 trials, got {len(arom.trial_corners_history)}")
    
    # 4. Verify Averages
    print(f"Average Top: {arom.average_top}")
    expected_top = (0.0, 0.45)
    if arom.average_top != expected_top:
        print(f"FAILED: Expected average top {expected_top}, got {arom.average_top}")
    else:
        print("SUCCESS: Average Top matches!")

    print(f"Average ML Range: {arom.average_ml_range}")
    if abs(arom.average_ml_range - 0.5) > 0.01:
        print(f"FAILED: Expected average ML range 0.5, got {arom.average_ml_range}")
    else:
        print("SUCCESS: Average ML Range matches!")

    # 5. Verify initialization of dependent data
    from arm_weight_data import ArmWeightData, ArmWeightTarget
    print("Testing ArmWeightData initialization...")
    aw = ArmWeightData("test_id", "A0")
    aw.initialize_from_mlap(arom)
    
    print(f"AW Top Target: {aw.target_positions[ArmWeightTarget.TOP]}")
    if aw.target_positions[ArmWeightTarget.TOP] != expected_top:
        print(f"FAILED: AW Top Target should be {expected_top}, got {aw.target_positions[ArmWeightTarget.TOP]}")
    else:
        print("SUCCESS: AW Top Target matches Average Top!")

    # Cleanup
    summary_path.unlink()
    test_dir.rmdir()

if __name__ == "__main__":
    test_multi_row_loading()
