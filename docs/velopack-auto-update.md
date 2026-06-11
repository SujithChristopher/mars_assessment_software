# Auto-Update with Velopack (planned — not yet implemented)

Plan for adding automatic updates to the PySide6 desktop app
(`mars_assessment.py`) using **Velopack**, hosted on **GitHub Releases**.

Status: **spec only**. No code or dependency changes have been made yet.

## Why Velopack

- Official Python support (`velopack` on PyPI, Rust/pyo3 binding).
- Delta updates, handles permissions, applies update + restarts the app.
- Replaces the installed app folder on update, so user data under
  `~/Documents/HomerMarsData` (see `app_paths.py`) is left untouched.

## Requirements

### Build machine (one-time)
- **.NET SDK** — only needed to install the `vpk` CLI (end users never need it).
- `dotnet tool install -g vpk`
- Add `velopack` to `pyproject.toml` (`uv add velopack`).
- Build with PyInstaller **`--onedir`** (NOT `--onefile`). `pyinstaller` is
  already a dependency.

### End user
- Must install the first version via Velopack's generated `Setup.exe`.
  Only an app that Velopack *installed* can self-update — running from
  `uv`/source never updates.

## Code changes (in `mars_assessment.py`)

1. Velopack hook must run **first** in `main()`, before `QApplication`:

   ```python
   import velopack

   def main():
       velopack.App().run()        # handles install/update/restart hooks; may restart
       app = QApplication(sys.argv)
       ...
   ```

   Guard the import so dev `uv run` still launches if the package is absent.

2. Update check, wired to a **"Check for Updates"** button (clinic-safe — no
   surprise restarts). Exact API confirmed from Velopack's `velopack.pyi` stub:

   ```python
   from velopack import UpdateManager, GithubSource

   REPO_URL = "https://github.com/SujithChristopher/mars_assessment_software"

   def check_and_update():
       mgr = UpdateManager(GithubSource(REPO_URL, access_token=None, prerelease=False))
       info = mgr.check_for_updates()        # None if already up to date
       if not info:
           return
       # info.TargetFullRelease.Version -> show user before applying
       mgr.download_updates(info)
       mgr.apply_updates_and_restart(info)   # closes + relaunches updated app
   ```

   Useful manager methods: `get_current_version()`, `get_update_pending_restart()`,
   `download_updates(info, progress_callback)`, `apply_updates_and_exit(info)`,
   `wait_exit_then_apply_updates(info, silent, restart)`.

   `GithubSource(repo_url, access_token=None, prerelease=False)` — pass a token
   if the repo stays **private**; public repo needs no token (rate limited to
   60 req/hr/IP).

## Release process (each version)

```
pyinstaller --onedir --name MarsAssessment mars_assessment.py

vpk pack  --packId Homer.MarsAssessment --packVersion 1.0.0 \
          --packDir .\dist\MarsAssessment --mainExe MarsAssessment.exe

vpk upload github --repoUrl https://github.com/SujithChristopher/mars_assessment_software \
          --publish --releaseName "MARS 1.0.0" --tag v1.0.0 --token <GH_TOKEN>
```

- `--packVersion` must **increment** every release (the `0.1.0` in
  `pyproject.toml` is just the dev version).
- A GitHub Actions workflow can do build → pack → upload in CI later.

## Gotchas

| Gotcha | Detail |
| --- | --- |
| First install via `Setup.exe` | Only a Velopack-installed app self-updates. |
| Private repo | Clients need `GithubSource(..., access_token=...)`. |
| Version bump | Increment `--packVersion` each release. |
| Data safety | Update replaces app folder; `Documents/HomerMarsData` untouched. |
| `--onedir` + `_MEIPASS` | Resource path in `mars_assessment.py` still resolves. |
| Guard import | Wrap `App().run()`/import so dev `uv run` works without the package. |

## TODO when resuming

- [ ] `uv add velopack`
- [ ] Guarded `velopack.App().run()` at top of `main()`
- [ ] `check_and_update()` + "Check for Updates" button in the launcher UI
- [ ] App `__version__` constant (single source of truth, feeds packaging)
- [ ] `release.ps1` wrapping the pyinstaller + vpk pack + vpk upload steps
- [ ] Decide: public repo (no token) vs private (ship/inject token)
- [ ] Optional: GitHub Actions release workflow

## References

- Getting Started (Python): https://docs.velopack.io/getting-started/python
- GithubSource: https://docs.velopack.io/reference/cs/Velopack/Sources/GithubSource
- GitHub Actions: https://docs.velopack.io/distributing/github-actions
- PythonQt sample + `velopack.pyi`: https://github.com/velopack/velopack
