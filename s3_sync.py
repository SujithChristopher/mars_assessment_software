"""S3 backup sync for MARS assessment data.

Mirrors the local data root (``~/Documents/HomerMarsData``) to
``s3://<bucket>/<prefix>/`` as an *upload-only* backup: only new or changed
files are uploaded, nothing in the cloud is ever deleted or pulled back down.

All work runs on a background thread so the UI never blocks. Credentials and
the target are read from the project ``.env``::

    AWS_S3_BUCKET, AWS_S3_PREFIX, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    AWS_REGION

If credentials are missing the manager is simply ``disabled`` and does nothing.
"""

import json
import os
import threading
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from app_paths import get_data_dir

MANIFEST_NAME = ".s3sync-manifest.json"
# Never uploaded.
_SKIP_NAMES = {MANIFEST_NAME}


class S3SyncManager(QObject):
    """Background, upload-only sync of the data root to an S3 prefix.

    States emitted via ``status_changed``: ``disabled``, ``idle``,
    ``syncing``, ``synced``, ``offline``, ``error``.
    """

    status_changed = Signal(str, str)   # (state, detail)
    last_sync_changed = Signal(str)     # human time string e.g. "12:03"

    def __init__(self, parent=None):
        super().__init__(parent)
        from dotenv import load_dotenv
        load_dotenv()

        self.bucket = os.environ.get("AWS_S3_BUCKET", "").strip()
        self.prefix = os.environ.get("AWS_S3_PREFIX", "").strip().strip("/")
        self.access_key = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
        self.secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
        self.region = os.environ.get("AWS_REGION", "").strip() or None

        self.data_root = get_data_dir()
        self.manifest_path = self.data_root / MANIFEST_NAME

        self._client = None
        self._lock = threading.Lock()   # only one sync in flight at a time
        self._pending = False           # change arrived while a sync was running
        self._state = "idle"

        if not (self.bucket and self.access_key and self.secret_key):
            self._state = "disabled"

    # ---- public API -----------------------------------------------------
    @property
    def enabled(self) -> bool:
        return self._state != "disabled"

    def request_sync(self):
        """Kick a background sync. Coalesces if one is already running."""
        if not self.enabled:
            return
        if self._lock.locked():
            self._pending = True
            return
        threading.Thread(target=self._sync_thread, daemon=True).start()

    # ---- internals ------------------------------------------------------
    def _emit_status(self, state: str, detail: str = ""):
        self._state = state
        self.status_changed.emit(state, detail)

    def _get_client(self):
        """Create (and cache) the S3 client, resolving the bucket's region."""
        if self._client is not None:
            return self._client
        import boto3

        def make(region):
            return boto3.client(
                "s3",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=region,
            )

        client = make(self.region or "us-east-1")
        # Resolve the bucket's real region so uploads don't fail on redirects.
        try:
            loc = client.get_bucket_location(Bucket=self.bucket).get("LocationConstraint")
            real = loc or "us-east-1"
            if real != (self.region or "us-east-1"):
                self.region = real
                client = make(real)
        except Exception:
            pass

        self._client = client
        return client

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_manifest(self, manifest: dict):
        try:
            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f)
        except OSError:
            pass

    def _iter_files(self):
        for p in self.data_root.rglob("*"):
            if p.is_file() and p.name not in _SKIP_NAMES:
                yield p

    def _sync_thread(self):
        with self._lock:
            self._pending = False
            try:
                self._emit_status("syncing")
                client = self._get_client()
                manifest = self._load_manifest()
                changed = 0
                for path in self._iter_files():
                    rel = path.relative_to(self.data_root).as_posix()
                    st = path.stat()
                    sig = [st.st_size, int(st.st_mtime)]
                    if manifest.get(rel) == sig:
                        continue  # unchanged since last upload
                    key = f"{self.prefix}/{rel}" if self.prefix else rel
                    client.upload_file(str(path), self.bucket, key)
                    manifest[rel] = sig
                    changed += 1
                self._save_manifest(manifest)
                self._emit_status("synced", f"{changed} uploaded" if changed else "up to date")
                self.last_sync_changed.emit(datetime.now().strftime("%H:%M"))
            except Exception as e:
                from botocore.exceptions import EndpointConnectionError
                if isinstance(e, EndpointConnectionError):
                    self._emit_status("offline", "no network connection")
                else:
                    self._emit_status("error", str(e))

        # A change arrived mid-sync -> run once more to catch it.
        if self._pending:
            self.request_sync()
