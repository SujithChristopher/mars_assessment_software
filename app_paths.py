"""Central filesystem paths for the MARS application.

All persistent data (assessments, logs, CSVs) lives under a single root so it
survives being packaged into a built executable (PyInstaller/Nuitka), where the
current working directory is not a reliable place to write.

Windows-only for now: root is ``%USERPROFILE%\\Documents\\HomerMarsData``.
"""

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
