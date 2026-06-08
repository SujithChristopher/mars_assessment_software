---
description: MARS Assessment System Architecture and Data Pipeline
---

# MARS Assessment System Architecture

This document describes the architectural patterns and data pipelines of the MARS Assessment Software specifically relating to multi-trial workspace assessment (`mars_assessment.py`).

## Data Model & Pipeline (`mars_arom_data.py`)

### 1. Multi-Trial Tracking
- **Storage Strategy**: The system supports 3 trials per assessment (AP, ML, MLAP).
- **Expansion Logic**: The `MarsArom` bounds (like `top`, `bottom`, `left`, `right`) expand dynamically during an active trial if the user reaches a new extrema.
- **Trial Recording**: When a trial completes, the *current state* of these corners is appended to the `trial_corners_history` list.
- **State Reset**: `MarsArom.reset_tracking()` resets the active bounding box bounds (e.g., `top = -999.0`) so the next trial starts fresh. The history and cumulative trajectories are preserved.

### 2. Averages & Maximums
- **Mean Calculation**: Properties like `average_top`, `average_bottom`, `average_ml_range_cm`, etc., dynamically calculate the statistical mean across all completed trials in `trial_corners_history`.
- **Global Maximums**: Variables specifically defined with `max_` or the primary bounds (`top`, `bottom`, etc. when evaluated historically) represent the absolute maximum reach across all trials.

### 3. File Exports (`save_to_csv`)
- **Main Assessment CSV (`ap-{date}.csv`)**: Contains only summary statistics. Writes individual Trial rows, a calculated `AVERAGE` row, and a `MAXIMUM` row. It *does not* contain full point-by-point trajectories.
- **Raw Trajectory CSV (`raw-ap-{date}.csv`)**: Contains every time-stamped `(y, z)` sample alongside its corresponding `trial_number`. Useful for post-hoc analysis without cluttering the summary file.

## Dependent Assessments

- **Arm Weight (`arm_weight_data.py`)**: Uses the **average MLAP** corners (`average_top`, `average_bottom`, `average_left`, `average_right`) to initialize its 5 force targets (Home, N, S, E, W).
- **Discrete Reaching (`discrete_reach_data.py`)**: Also uses the **average MLAP** corners to position its targets at 75% of the user's average workspace radius.

> **CRITICAL RULE**: All dependent target setups should reference the `average_` variables on the MLAP `MarsArom` object. They should fallback to legacy `adjusted_` maximums only for backward compatibility with old data files.

## UI Design Patterns (`assessment_base.py`)

### Screen Space & Navigation
- Assessment windows run fully maximized (`showMaximized()`) to preserve OS controls (close/minimize) rather than strict full-screen headless mode.
- `WorkspaceAssessmentCanvas` scales dynamically based on widget `.width()` and `.height()`. It relies on a `pixels_per_unity_unit` metric derived dynamically, rather than hardcoded sizing.

### Boundary Rendering
- **Blue**: Represents the current context (Current active trial track, boundary, UI labels).
- **Red**: Represents the historical context (Max global boundary, Average boundary track).
- **States**: The system uses `BaseAssessmentState` (`INIT`, `ASSESSROM`, `TRIAL_PAUSE`, `DONE`). Rendering heavily depends on the active state (e.g., showing Blue Trial vs Red Avg in `TRIAL_PAUSE`).

### Real-Time Diagnostics
- Use the `angle_display_label` technique implemented in `mars_assessment.py` to bind live variables (`qtmars.angle1`) directly into Qt labels via the `newdata` signal.
- **Known Calibration Quirk**: Setting target to -90 degrees resolves physically at ~-87 degrees due to zero Integral gain (`pcKi = 0`) in the firmware acting against maximum gravitational pull. Documented in `docs/calibration_limitations.md`.
