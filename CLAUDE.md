# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two separate applications for the MARS (Motor Assessment and Rehabilitation System) embedded device:

1. **Python/PySide6 Desktop Application** (root directory) - A desktop GUI for device communication, sensor data streaming, and assessment functionality
2. **Unity Game Application** (MARS-HOMER directory) - A game-based therapy and assessment application with multiple rehabilitation mini-games

Both applications communicate with the MARS embedded device using the JEDI serial communication protocol.

## Development Setup

### Python Application Dependencies

Install required Python packages:
```bash
pip install PySide6 pyserial
```

### Unity Application Dependencies

- Unity Editor 2023.2.20f1 or compatible version
- System.IO.Ports package (included via NuGet, see `MARS-HOMER/packages.config`)

### Running the Applications

**Python Application:**
The main Qt application modules can be run directly:
```bash
python qtmars.py
```

For standalone testing of the JEDI communication layer:
```bash
python qtjedi.py
```

**Unity Application:**
Open the `MARS-HOMER` directory as a Unity project in Unity Editor 2023.2.20f1 or later.

### Git Submodules

The `marsfire` directory is a git submodule containing the Arduino firmware for the MARS device.

Initialize and update the submodule:
```bash
git submodule init
git submodule update
```

Or clone with submodules:
```bash
git clone --recurse-submodules <repository-url>
```

The marsfire firmware repository: https://github.com/siva82kb/marsfire.git

## Architecture

### Python Application Architecture

#### High-Level Structure

```
GUI Layer (Qt/PySide6)
    ↓
Device Abstraction Layer (qtmars.py - QtPluto class)
    ↓
Protocol Layer (qtjedi.py - JediComm class)
    ↓
Serial Communication (pyserial)
    ↓
MARS Embedded Device (Arduino firmware in marsfire/)
```

#### Core Components

**qtmars.py - Device Abstraction (`QtPluto` class)**
- Wraps the JEDI protocol with a high-level Qt interface
- Emits Qt signals for device events: `newdata`, `btnpressed`, `btnreleased`, `controlmodechanged`, `armweightinoutofrange`
- Handles packet parsing based on data type (SENSORSTREAM, DIAGNOSTICS, VERSION)
- Manages sensor data unpacking (floats), packet numbers, timestamps, and frame rate estimation
- Provides 20+ named properties for accessing sensor data: `angle1`-`angle4`, `imu_angle1`-`imu_angle4`, `force`, `target`, `desired`, `control`, `err_p`, `err_d`, `err_i`, `gravity_compensation_torque`, `angular_velocity1`, etc.
- Provides properties for accessing device state: `status`, `datatype`, `button`, `controltype`, `limb`, `error`, `error_string`, `actuated`, etc.
- **Forward Kinematics**: Methods for calculating 3D endpoint position from joint angles (`forward_kinematics()`, `forward_kinematics_wrist()`, `forward_kinematics_hand()`)
- **Arm Weight Management**: Automatic estimation and validation using Recursive Least Squares algorithm
- **Safety Monitoring**: Frame rate monitoring with automatic control disabling on low frame rates (<85Hz warning, <20Hz safety cutoff)
- **Comprehensive Logging**: Built-in logger for device communication, errors, and state changes
- **Control Commands**: `set_control_type()`, `set_control_target()`, `calibrate()`, `set_limb()`, `set_diagnostic_mode()`, `reset_packet_number()`
- **Key Methods**: `start_sensorstream()`, `stop_sensorstream()`, `get_version()`, `send_heartbeat()`
- **Constants**: Arm geometry (L1-L4 link lengths), arm weight thresholds, frame rate thresholds

**qtjedi.py - JEDI Protocol (`JediComm` class)**
- QThread-based serial communication handler
- Implements JEDI protocol: Header `0xFF 0xFF`, length byte, payload, checksum (sum % 256)
- State machine for packet parsing (`JediParsingStates` enum)
- Emits `newdata_signal` when complete packets are received
- Methods: `send_message()`, `pause()`, `wakeup()`, `abort()`

**marsdefs.py - Protocol Definitions**
- Defines all communication constants and enums
- `InDataType`: Commands sent to device (GET_VERSION, START_STREAM, CALIBRATE, etc.)
- `OutDataType`: Data types received from device (VERSION, SENSORSTREAM, CONTROLPARAM, DIAGNOSTICS)
- `LimbType`, `ControlTypes`, `ErrorTypes`, `MovementTypes`: Device configuration enums
- `MarsSensorDataNumber`: Maps data types to expected float count in packets
- Helper function `get_name()` for reverse enum lookup

**RecursiveLeastSquares class (in qtmars.py)**
- Implements Recursive Least Squares (RLS) parameter estimation algorithm
- Used for real-time arm weight estimation from sensor data
- Methods: `reset_estimator()`, `update(x, y)` with Kalman gain calculation
- Properties: `theta` (parameter estimates), `P` (covariance matrix), forgetting factor `lambda_factor`

**ui/plutofullassessment.ui**
- Qt Designer UI file for the main assessment interface
- Window: "PLUTO Full Assessment" (1200x607 fixed size)
- Convert to Python using: `pyside6-uic ui/plutofullassessment.ui -o ui_plutofullassessment.py`

### Communication Protocol Details

**JEDI Protocol Frame Structure:**
- Outgoing: `[0xAA, 0xAA, length, ...payload, checksum]`
- Incoming: `[0xFF, 0xFF, length, ...payload, checksum]`
- Checksum: Sum of all bytes (headers + length + payload) modulo 256

**Packet Parsing Flow:**
1. Look for header bytes (0xFF 0xFF)
2. Read length byte (must be > 0)
3. Read payload bytes (length - 1)
4. Verify checksum
5. Emit signal with payload

**Device Data Packets:**
- Byte 0: Status (upper nibble = data type, lower nibble = flags)
- Bytes 1-2: Error code (little-endian)
- Byte 3: Actuated state
- Bytes 4-5: Packet number (little-endian)
- Bytes 6-9: Runtime (unsigned long, milliseconds)
- Remaining bytes: Float data (4 bytes each, count depends on data type)

#### Threading Model

- `JediComm` runs in its own QThread, continuously reading serial data
- Emits Qt signals when packets are complete
- `QtPluto` connects to these signals in the main thread
- Use `pause()`/`wakeup()` to temporarily halt processing without closing the connection

### Unity Application Architecture

#### High-Level Structure

```
Unity Game Scenes
    ↓
Scene Handlers (WelcomeSceneHandler, DiagnosticSceneHandler, etc.)
    ↓
Device Abstraction (MarsComm.cs)
    ↓
Protocol Layer (JediComm.cs - static class)
    ↓
Serial Communication (System.IO.Ports)
    ↓
MARS Embedded Device (Arduino firmware in marsfire/)
```

#### Core Components

**JediComm.cs - JEDI Protocol (Static Class)**
- Thread-based serial communication handler using System.IO.Ports
- Implements same JEDI protocol as Python version
- Headers: Incoming `0xFF 0xFF`, Outgoing `0xAA 0xAA`
- Methods: `InitSerialComm()`, `Connect()`, `Disconnect()`, `SendMessage()`
- Reads packets in background thread `serialreaderthread()`
- Calls `MarsComm.parseByteArray()` when full packets are received

**MarsComm.cs - Device Abstraction (Static Class)**
- Provides high-level interface for Unity scripts
- Defines device constants: `OUTDATATYPE`, `LIMBTYPE`, `CONTROLTYPE`, `INDATATYPE`, etc.
- Parses incoming data packets and updates device state
- Emits C# events: `OnMarsButtonReleased`, `OnNewMarsData`, `OnControlModeChange`, etc.
- Contains sensor data arrays and device state variables

**Scene Handlers**
- Each Unity scene has a corresponding handler script (e.g., `WelcomeSceneHandler.cs`, `DiagnosticSceneHandler.cs`)
- Handle UI interactions and game logic
- Subscribe to MarsComm events to receive device data
- Control scene flow and transitions

**Assessment Scripts**
- `MarsAssessAROM.cs` - Active Range of Motion assessment
- `assessArmWeight.cs` - Arm weight estimation
- `assessAP.cs`, `assessAROMML.cs`, etc. - Various assessment protocols
- Subscribe to device events and process sensor data for assessment metrics

**Key Directories**
- `Assets/scripts/` - Core MARS communication and scene management scripts
- `Assets/FlappyGame/` - Flappy Bird-style rehabilitation game
- `Assets/Ping Pong/` - Ping pong rehabilitation game
- `Assets/XCharts-master/` - Third-party charting library for data visualization
- `Assets/Scenes/` - Unity scene files for different application screens

#### Unity-Specific Notes

- Uses C# threading model instead of Unity Coroutines for serial communication
- `JediComm` and `MarsComm` are static classes - shared across all scenes
- Serial connection persists across scene changes via `DontDestroyOnLoad` pattern
- Event-driven architecture using C# delegates and events

## UI Development

### Python Application (Qt Designer)

The Python app UI is designed in Qt Designer (.ui files). To modify:

1. Open `ui/plutofullassessment.ui` in Qt Designer
2. Make changes
3. Convert to Python: `pyside6-uic ui/plutofullassessment.ui -o ui_plutofullassessment.py`
4. Import and use in main application code

### Unity Application (Unity Editor)

The Unity app UI uses Unity's built-in UI system (Canvas, UI elements). To modify:

1. Open scenes in Unity Editor (located in `Assets/Scenes/`)
2. Modify UI elements in the Scene view and Inspector
3. UI logic is handled in scene-specific handler scripts

## Device Communication Patterns (Python Application)

### Initialization Sequence
```python
pluto = QtPluto(port="COM5", baudrate=115200)
pluto.get_version()
pluto.send_heartbeat()
```

### Starting Data Stream
```python
pluto.start_sensorstream()
# Connect to signals to receive events
pluto.newdata.connect(handle_new_data)
pluto.btnpressed.connect(handle_button_press)
pluto.btnreleased.connect(handle_button_release)
pluto.controlmodechanged.connect(handle_control_mode_change)
pluto.armweightinoutofrange.connect(handle_arm_weight_alert)

def handle_new_data():
    # Access sensor data via named properties
    print(f"Angles: {pluto.angle1:.2f}, {pluto.angle2:.2f}, {pluto.angle3:.2f}")
    print(f"Force: {pluto.force:.2f}")
    # Or via forward kinematics
    x, y, z = pluto.forward_kinematics(pluto.angle1, pluto.angle2, pluto.angle3)
    print(f"Endpoint: ({x:.3f}, {y:.3f}, {z:.3f})")
```

### Stopping Communication
```python
pluto.stop_sensorstream()
pluto.dev.abort()
pluto.dev.quit()
pluto.dev.wait()
```

## Device Communication Patterns (Unity Application)

### Initialization Sequence
```csharp
JediComm.InitSerialComm("COM5");
JediComm.Connect();
// Send initial commands
MarsComm.GetVersion();
MarsComm.SendHeartBeat();
```

### Starting Data Stream
```csharp
// Subscribe to events first
MarsComm.OnNewMarsData += HandleNewData;
MarsComm.OnMarsButtonReleased += HandleButtonPress;

// Start streaming
MarsComm.StartStreaming();
```

### Stopping Communication
```csharp
MarsComm.StopStreaming();
JediComm.Disconnect();
```

## Code Patterns (Python Application)

### Adding New Device Commands

1. Add command constant to `marsdefs.py` in `InDataType`
2. Create method in `QtPluto` class:
```python
def new_command(self, param):
    if not self.is_connected():
        self._logger.warning("Cannot execute command: not connected")
        return
    _payload = [mdef.InDataType["NEW_COMMAND"]]
    # Add parameters using struct.pack for multi-byte values
    self._logger.info(f"Executing new command with param: {param}")
    self.dev.send_message(_payload)
```

### Using Control Commands

The `QtPluto` class provides comprehensive control commands for the MARS device:

```python
# Set control mode
pluto.set_control_type("IMPEDANCE")  # Options: "NONE", "POSITION", "VELOCITY", "IMPEDANCE", "TORQUE"

# Set control target value
pluto.set_control_target(45.0)  # Target value in appropriate units

# Calibrate device
pluto.calibrate()

# Set active limb
pluto.set_limb("RIGHT")  # Options: "LEFT", "RIGHT"

# Enable diagnostic mode
pluto.set_diagnostic_mode()

# Reset packet counter
pluto.reset_packet_number()
```

**Important**: All control commands automatically check connection status and log actions.

### Handling New Packet Types

1. Add type to `OutDataType` in `marsdefs.py`
2. Add handler method to `QtPluto`:
```python
def _handle_new_type(self, newdata: list[int]):
    # Parse packet data
    pass
```
3. Register handler in `_packet_type_handlers` dict in `__init__`

### Working with Sensor Data

Sensor data is always unpacked as floats (4 bytes each). The count depends on the data type as defined in `MarsSensorDataNumber`.

**Two ways to access sensor data:**

1. **Raw access via list**: `self.currsensordata` list contains all float values
2. **Named properties (recommended)**: Use descriptive property names for better readability

```python
# Named properties for sensor data
angles = [pluto.angle1, pluto.angle2, pluto.angle3, pluto.angle4]
imu_angles = [pluto.imu_angle1, pluto.imu_angle2, pluto.imu_angle3, pluto.imu_angle4]
force = pluto.force
control_signal = pluto.control
errors = [pluto.err_p, pluto.err_d, pluto.err_i]
gravity_comp = pluto.gravity_compensation_torque
velocity = pluto.angular_velocity1
```

**Forward Kinematics Example:**
```python
# Calculate 3D endpoint position from joint angles
x, y, z = pluto.forward_kinematics(pluto.angle1, pluto.angle2, pluto.angle3)
print(f"Endpoint position: ({x:.3f}, {y:.3f}, {z:.3f}) meters")
```

## Code Patterns (Unity Application)

### Adding New Device Commands

1. Add command byte code to `INDATATYPECODES` array in `MarsComm.cs`
2. Add command name to `INDATATYPE` array (must match index)
3. Create method in `MarsComm.cs`:

```csharp
public static void NewCommand(byte param)
{
    byte[] payload = new byte[] { INDATATYPECODES[index], param };
    JediComm.SendMessage(payload);
}
```

### Subscribing to Device Events

```csharp
void OnEnable()
{
    MarsComm.OnNewMarsData += HandleNewData;
    MarsComm.OnMarsButtonReleased += HandleButtonRelease;
}

void OnDisable()
{
    MarsComm.OnNewMarsData -= HandleNewData;
    MarsComm.OnMarsButtonReleased -= HandleButtonRelease;
}

void HandleNewData()
{
    // Access sensor data via MarsComm static fields
    float[] angles = MarsComm.currAngles;
    // Process data...
}
```

### Working with Sensor Data

Sensor data is parsed by `MarsComm.parseByteArray()` and stored in static fields like `currAngles`, `currVelocities`, etc. The count depends on the data type as defined in `SENSORNUMBER`.

## Important Notes

### Both Applications

- Serial port must be specified correctly (e.g., "COM5" on Windows, "/dev/ttyUSB0" on Linux)
- Device expects regular heartbeat messages to maintain connection
- Packet numbers and runtime help detect dropped packets and timing issues
- Both implementations use the same JEDI protocol for compatibility

### Python Application Specific

- **Full Feature Parity**: Python implementation now has feature parity with Unity version
- **Named Properties**: Use named properties (e.g., `angle1`, `force`) instead of raw list indices for better code readability
- **Safety Features**: Automatic frame rate monitoring with control disabling on low frame rates
- **Arm Weight Estimation**: Built-in RLS estimator for real-time arm weight calculation
- **Comprehensive Logging**: All device communication and errors are logged via Python logging module
- **Forward Kinematics**: Built-in methods for 3D position calculation from joint angles
- Frame rate estimation uses rolling window of 100 samples
- Always check `is_connected()` before sending commands
- Uses Qt's signal/slot mechanism for event handling
- Logger output format: `YYYY-MM-DD HH:MM:SS - QtPluto - LEVEL - message`

### Unity Application Specific

- `JediComm` and `MarsComm` are static classes - maintain state across scenes
- Serial communication runs on separate thread - use Unity's main thread for UI updates
- Always unsubscribe from events in `OnDisable()` to prevent memory leaks
- Uses `ConnectToRobot.isMARS` flag to track connection status
- Sample CSV data files available in `MARS-HOMER/` directory for testing
