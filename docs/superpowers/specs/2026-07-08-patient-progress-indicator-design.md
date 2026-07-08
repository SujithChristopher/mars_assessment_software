# Patient Entry: Existing-Patient Progress Indicator

Date: 2026-07-08

## Problem

On the Patient Entry screen (`PatientEntryWidget` in `mars_assessment.py`), a
clinician types a HOMER ID and picks a session type (Screening or
Assessment + phase A0/A1/A2). Today the only feedback is the lock check:
if the time point is locked, the entry button switches to a blue
"View Results (Locked)" state. There is no indication that the patient
already has *some* assessment data for this time point before locking.

## Goal

Detect existing progress for the entered patient_id + time_point and show
a status label so the clinician knows this is a returning patient with
partial or complete data, before they even connect the device.

## Scope

- Screening: required assessment types = `{AP, ML}`
- Assessment (A0/A1/A2): required assessment types = `{AP, ML, MLAP,
  ArmWeight, DiscreteReaching}`
- Limb is irrelevant to this check — it's a robot configuration
  (LEFT/RIGHT arm), not a patient attribute. A completed assessment file
  in either limb's directory counts as "done" for that assessment type.
- Locked state takes priority and is unchanged: once
  `get_lock_file(patient_id, time_point)` exists, the existing red
  lock banner + blue "View Results (Locked)" button behavior applies as-is.
  This spec only adds the pre-lock progress label.

## Detection

New helper function (e.g. in `app_paths.py`):

```python
def get_completed_assessment_types(patient_id: str, time_point: str) -> set[str]:
    """Return which of AP/ML/MLAP/ArmWeight/DiscreteReaching have a saved
    summary CSV for this patient_id + time_point, checking both limbs.
    """
```

For each assessment type, check for its known summary filename under
`get_assessment_dir(patient_id, limb, time_point)/session*/` for
`limb in ("LEFT", "RIGHT")`:

| Type            | Filename            |
|-----------------|----------------------|
| AP              | `ap-rom.csv`         |
| ML              | `ml-rom.csv`         |
| MLAP            | `mlap-rom.csv`       |
| ArmWeight       | `armweight.csv`      |
| DiscreteReaching| `discrete-reach.csv` |

A type counts as done if the file exists under any `session*` folder for
either limb. Use `Path.glob("session*/<filename>")` — no need to parse
session numbers.

## UI Changes

`PatientEntryWidget`:

- New `QLabel self.progress_label`, added directly below `self.lock_label`
  in `init_ui()`. Hidden by default (`setVisible(False)`).
- `update_lock_status()` (already triggered by `id_input.textChanged` and
  `phase_combo.currentIndexChanged`) gains a progress branch, evaluated
  only when **not locked** (locked branch returns/continues to hide
  progress label instead of showing it — mutually exclusive with the lock
  banner):

  1. If `patient_id` or `time_point` is empty → hide `progress_label`
     (same guard as the existing early return).
  2. Else compute `done = get_completed_assessment_types(patient_id, time_point)`
     restricted to the required set for this time_point, `n = len(done)`,
     `total = len(required)`.
     - `n == 0` → hide `progress_label`.
     - `0 < n < total` → show `progress_label`, green style, text:
       `f"Existing patient — {n}/{total} assessments done for {time_point}"`.
     - `n == total` → show `progress_label`, same green style, text:
       `f"All {total} assessments complete for {time_point} — remember to lock"`.
  3. If locked → `progress_label.setVisible(False)` (lock banner takes over
     the messaging).

- Style: reuse a green style consistent with existing green button style
  in the file (`color: #2e7d32` text or similar — match `lock_label`'s
  approach of a stylesheet on the label, e.g.
  `"color: #2e7d32; font-weight: bold;"`), centered, word-wrap on.

## Out of Scope

- No change to `MarsAssessmentLauncher` (the main launcher's per-assessment
  green button / redo logic already works within an active session).
- No change to lock/redo semantics — locked always means view-only, as
  today.
- No per-limb breakdown in the label.
