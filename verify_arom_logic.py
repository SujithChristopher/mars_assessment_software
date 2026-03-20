from mars_arom_data import MarsArom
import os

def test_mars_arom_logic():
    print("Testing MarsArom expansion-only logic...")
    arom = MarsArom("MLAP", patient_id="test_user", time_point="A0")
    
    # Trial 1: (0,0) to (1,1)
    arom.start_assessment()
    arom.add_data_point(0, 0)
    arom.add_data_point(0.1, 0.1)
    arom.add_data_point(0.2, 0.2)
    arom.add_data_point(0.3, 0.3)
    arom.add_data_point(0.4, 0.4)
    arom.add_data_point(1.0, 1.0)
    arom.pause_assessment()
    
    print(f"Trial 1 Max AP: {arom.ap_range:.2f} m")
    print(f"Trial 1 Avg AP: {arom.ap_average:.2f} m")
    print(f"Trial 1 Avg Top Y: {arom.average_top[0]:.2f} m")
    
    # Trial 2: Smaller move (0,0) to (0.5, 0.5)
    arom.resume_assessment()
    arom.add_data_point(0, 0)
    arom.add_data_point(0.1, 0.1)
    arom.add_data_point(0.2, 0.2)
    arom.add_data_point(0.3, 0.3)
    arom.add_data_point(0.4, 0.4)
    arom.add_data_point(0.5, 0.5)
    arom.pause_assessment()
    
    print(f"After Trial 2 (smaller):")
    print(f"Max AP: {arom.ap_range:.2f} m (Should be ~1.0)")
    print(f"Avg AP: {arom.ap_average:.2f} m (Should be ~0.75)")
    print(f"Avg Top Y: {arom.average_top[0]:.2f} m (Should be ~0.75)")
    
    # Trial 3: Larger move (0,0) to (2.0, 2.0)
    arom.resume_assessment()
    arom.add_data_point(0, 0)
    arom.add_data_point(1.0, 1.0)
    arom.add_data_point(1.5, 1.5)
    arom.add_data_point(2.0, 2.0)
    arom.add_data_point(1.8, 1.8)
    arom.add_data_point(1.9, 1.9)
    arom.stop_assessment()
    
    print(f"After Trial 3 (larger):")
    print(f"Max AP: {arom.ap_range:.2f} m (Should be ~2.0)")
    print(f"Avg AP: {arom.ap_average:.2f} m (Should be ~1.16)")

    # Test Save/Load
    save_path = arom.save_to_csv(base_dir="tmp_test_data")
    print(f"Saved to {save_path}")
    
    loaded_arom = MarsArom.load_from_csv(save_path)
    print(f"Loaded Max AP: {loaded_arom.ap_range:.2f}")
    print(f"Loaded Avg AP: {loaded_arom.ap_average:.2f}")
    print(f"Loaded Trial Ranges: {loaded_arom.trial_ranges}")
    
    # Cleanup
    if os.path.exists(save_path):
        os.remove(save_path)
    os.removedirs(os.path.dirname(save_path))

if __name__ == "__main__":
    test_mars_arom_logic()
