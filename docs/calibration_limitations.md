# MARS Calibration Limitations

## -90 Degree Calibration Inaccuracy

### Symptom
When performing the "Set Plane (90°)" calibration step, the MARS robotic arm may visibly settle at approximately **-87 degrees** instead of the commanded -90 degrees.

### Root Cause Analysis
This steady-state error of ~3 degrees is a known limitation caused by a combination of physical factors and firmware control configuration:

1. **Maximum Gravitational Pull**: At exactly -90 degrees, the robot arm is fully horizontal. In this position, the gravitational torque exerted on the base joint is at its absolute maximum.
2. **Firmware Controller Design**: The firmware's position controller (`controllaw.ino`) uses a Proportional-Derivative (PD) control scheme with the integral gain (`pcKi`) explicitly set to `0`. 
3. **Equilibrium State**: While the firmware includes a gravity compensation model, any slight under-estimation in this model combined with physical joint friction necessitates a small error term. Without an integral term to build up corrective torque over time, the proportional controller requires this ~3 degree physical error to generate enough motor current to hold the arm steady against gravity.

### Resolution
This error is considered acceptable for general assessment purposes and does not necessitate immediate correction.

If higher precision is required in the future, the following approaches can be evaluated:
1. **Software Offset**: Modify the `mars_assessment.py` launcher to command an intentionally overshot angle (e.g., `-93.0`) to physically pull the arm to -90.
2. **Firmware Tuning**: Introduce a small Integral gain (`pcKi > 0`) in the firmware's PID controller (`variable.h`), ensuring appropriate anti-windup measures are also implemented to prevent oscillation.
