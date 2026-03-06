
import os
from pathlib import Path
import shutil
from qtmars import QtMars

def test_logging_directory():
    test_patient = "test_patient_123"
    test_data_dir = Path("data") / test_patient / "logs"
    
    # Remove existing test directory if it was there
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir.parent)
        
    print(f"Creating QtMars instance for patient {test_patient}...")
    # NOTE: We don't need a real port to test the __init__ and _setup_logger
    mars = QtMars(port=None, patient_id=test_patient)
    
    if test_data_dir.exists():
        print(f"SUCCESS: Log directory created at {test_data_dir}")
        logs = list(test_data_dir.glob("*.csv"))
        if logs:
            print(f"SUCCESS: Found log file: {logs[0].name}")
        else:
            print("FAILURE: No log file found in the directory.")
    else:
        print(f"FAILURE: Log directory {test_data_dir} was NOT created.")
        
    # Cleanup
    mars.close()
    # shutil.rmtree(test_data_dir.parent)

if __name__ == "__main__":
    test_logging_directory()
