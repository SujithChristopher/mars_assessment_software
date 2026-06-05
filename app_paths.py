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
