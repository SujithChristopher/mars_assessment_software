"""Central filesystem paths for the MARS application.

All persistent data (assessments, logs, CSVs) lives under a single root so it
survives being packaged into a built executable (PyInstaller/Nuitka), where the
current working directory is not a reliable place to write.

Windows-only for now: root is ``%USERPROFILE%\\Documents\\HomerMarsData``.
"""

import json
from pathlib import Path

APP_DIR_NAME = "HomerMarsData"


def get_data_dir() -> Path:
    """Return the data root, creating it if needed.

    Returns ``~/Documents/HomerMarsData``. On Windows this resolves to the
    user's Documents folder regardless of where the app was launched from.
    """
    data_dir = Path.home() / "Documents" / APP_DIR_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_assessment_dir(patient_id: str, limb: str, time_point: str) -> Path:
    """Return the parent directory for a patient's assessment session folders.

    Layout:
        Screening:   <root>/Screening/<patient>/<limb>/
        A0/A1/A2:    <root>/Assessment/<patient>/<limb>/<time_point>/

    Session folders (``session<N>-<date>/``) are created beneath this. The
    directory is not created here; callers create it when writing.
    """
    root = get_data_dir()
    if time_point == "Screening":
        return root / "Screening" / patient_id / limb
    return root / "Assessment" / patient_id / limb / time_point


def get_log_dir(patient_id: str = "") -> Path:
    """Return the log directory, creating it if needed.

    Layout mirrors the assessment tree, rooted under a single ``logs`` folder:
        With patient:    <root>/logs/<patient_id>/
        Without patient: <root>/logs/
    """
    log_dir = get_data_dir() / "logs"
    if patient_id:
        log_dir = log_dir / patient_id
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_config_file() -> Path:
    """Return the path to the application config JSON (in the data root)."""
    return get_data_dir() / "config.json"


def load_config() -> dict:
    """Load the config dict, returning {} if missing or unreadable."""
    cfg = get_config_file()
    if cfg.exists():
        try:
            with open(cfg, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(config: dict) -> None:
    """Write the config dict to the config JSON."""
    with open(get_config_file(), "w") as f:
        json.dump(config, f, indent=2)


def get_saved_com_port() -> str | None:
    """Return the saved COM port, or None if not configured."""
    return load_config().get("com_port")


def set_saved_com_port(port: str) -> None:
    """Persist the chosen COM port to the config JSON."""
    config = load_config()
    config["com_port"] = port
    save_config(config)


def get_lock_file(patient_id: str, time_point: str) -> Path:
    """Return the lock-marker path for a patient's time point.

    Locks are limb-independent (a time point is locked across both limbs), so
    the marker lives above the ``<limb>`` level:
        Screening:   <root>/Screening/<patient>/.locked
        A0/A1/A2:    <root>/Assessment/<patient>/<time_point>.locked
    """
    root = get_data_dir()
    if time_point == "Screening":
        return root / "Screening" / patient_id / ".locked"
    return root / "Assessment" / patient_id / f"{time_point}.locked"
