
import os
import shutil
import csv
from pathlib import Path
from mars_arom_data import MarsArom
from discrete_reach_data import DiscreteReachData
from arm_weight_data import ArmWeightData

def test_patient_save():
    print("Testing Patient Mode Save...")
    patient_id = "VERIFY_NEW"
    time_point = "A1"
    
    # Test MarsArom
    arom = MarsArom("MLAP", patient_id, time_point, False)
    arom._is_recording = True
    for i in range(25): arom.add_data_point(0.1*i, 0.2*i)
    arom.stop_assessment()
    
    csv_path = arom.save_to_csv(base_dir="test_data")
    print(f"MarsArom saved to: {csv_path}")
    
    # Check CSV Content
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        data = next(reader)
        data_dict = dict(zip(header, data))
        assert data_dict['movement_type'] == "MLAP"
        assert data_dict['patient_id'] == patient_id
        assert data_dict['time_point'] == time_point

def test_polluted_load():
    print("\nTesting Backward Compatibility for Polluted CSV...")
    os.makedirs("test_data/buggy/A0/session1-2026-03-02", exist_ok=True)
    buggy_path = "test_data/buggy/A0/session1-2026-03-02/mlap-2026-03-02-09-00-00.csv"
    
    with open(buggy_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['datetime', 'plane_angle', 'movement_type'])
        writer.writerow(['2026-03-02T09:00:00', '90.0', 'buggy/A0/MLAP'])
        writer.writerow([])
        writer.writerow(['Trajectory Data'])
        writer.writerow(['y (m)', 'z (m)'])
        for i in range(25): writer.writerow([0.1, 0.2])

    arom = MarsArom.load_from_csv(buggy_path)
    assert arom.movement_type == "MLAP"
    assert arom.patient_id == "buggy"
    assert arom.time_point == "A0"
    print("Backward compatibility check passed!")

if __name__ == "__main__":
    if os.path.exists("test_data"): shutil.rmtree("test_data")
    try:
        test_patient_save()
        test_polluted_load()
        print("\nAll data saving and loading tests passed!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists("test_data"): shutil.rmtree("test_data")
