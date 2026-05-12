# Project Structure

**Root:** `/Users/ma-molinari/Documents/projects/m-tech/vision-mouse`

## Directory Tree

```text
vision-mouse/
├── Makefile
├── README.md
├── docs/
│   ├── MVP_VALIDATION.md
│   └── TDD.md
├── src/
│   └── vision_mouse/
│       ├── app/
│       ├── application/
│       ├── calibration/
│       ├── capture/
│       ├── domain/
│       ├── filters/
│       ├── gestures/
│       ├── mapping/
│       ├── observability/
│       ├── pipeline/
│       ├── platform/
│       ├── resources/
│       ├── vision/
│       ├── config.py
│       └── main.py
├── tests/
│   ├── test_application_ports.py
│   ├── test_bootstrap.py
│   ├── test_gestures.py
│   ├── test_pipeline_runtime.py
│   └── ...
├── pyproject.toml
└── setup.py
```

## Module Organization

### Runtime Assembly

**Purpose:** build and start the application

**Location:** `src/vision_mouse/app/` and `src/vision_mouse/main.py`

**Key files:** `main.py`, `app/composition.py`, `app/bootstrap.py`

### Application Core

**Purpose:** orchestration, ports, routing, and operational state

**Location:** `src/vision_mouse/application/`

**Key files:** `application/pipeline.py`, `application/routing.py`, `application/operational.py`, `application/ports.py`

### Domain Models

**Purpose:** shared data contracts and enums

**Location:** `src/vision_mouse/domain/`

**Key files:** `domain/vision.py`, `domain/gestures.py`, `domain/runtime.py`

### Signal Processing

**Purpose:** cursor normalization, smoothing, stability gating, and pointer assist

**Location:** `src/vision_mouse/mapping/` and `src/vision_mouse/filters/`

**Key files:** `mapping/cursor_mapper.py`, `mapping/pointer_assist.py`, `filters/temporal.py`

### Gesture Recognition

**Purpose:** classify clicks, drag, scroll, workspace switching, and macros

**Location:** `src/vision_mouse/gestures/`

**Key files:** `gestures/engine.py`, `gestures/clicks.py`, `gestures/drag.py`, `gestures/scroll.py`, `gestures/navigation.py`, `gestures/macros.py`

### Infrastructure Adapters

**Purpose:** talk to webcam, MediaPipe, and macOS

**Location:** `src/vision_mouse/capture/`, `src/vision_mouse/vision/`, `src/vision_mouse/platform/macos/`

**Key files:** `capture/session.py`, `vision/mediapipe_provider.py`, `platform/macos/input.py`, `platform/macos/permissions.py`

### Calibration

**Purpose:** guided calibration and persistent profile storage

**Location:** `src/vision_mouse/calibration/`

**Key files:** `calibration/session.py`, `calibration/profile.py`

### Observability

**Purpose:** collect metrics and structured events in memory and via logging

**Location:** `src/vision_mouse/observability/`

**Key files:** `observability/telemetry.py`

## Where Things Live

**Cursor movement:**

- UI / interface: CLI entrypoint in `main.py`
- Business logic: `application/pipeline.py`, `mapping/cursor_mapper.py`, `filters/temporal.py`
- Data access / system access: `capture/session.py`, `vision/mediapipe_provider.py`, `platform/macos/input.py`
- Configuration: `config.py`, optional calibration overlay from `calibration/profile.py`

**Gesture recognition:**

- UI / interface: none directly; results are emitted as intents
- Business logic: `gestures/`
- Data access / system access: `application/routing.py` forwards to macOS adapters
- Configuration: `GestureConfig` and `MacroConfig` in `config.py`

**Calibration:**

- UI / interface: console prompts in `calibration/session.py`
- Business logic: `CalibrationAnalyzer`
- Data access / system access: webcam and MediaPipe reused from shared adapters
- Configuration: saved JSON profile at `~/.vision_mouse/profile.json` or `VISION_MOUSE_PROFILE_PATH`

**Permissions and macOS automation:**

- UI / interface: startup flow in `OperationalStateController`
- Business logic: permission gating and router checks
- Data access / system access: `platform/macos/permissions.py`, `workspace.py`, `macros.py`, `input.py`
- Configuration: implicit OS state plus `CaptureConfig`

## Special Directories

**`docs/`:**

**Purpose:** product and technical documentation that complements the code

**Examples:** `TDD.md`, `MVP_VALIDATION.md`

**`tests/`:**

**Purpose:** flat automated test suite covering units, contracts, and integration-style runtime behavior

**Examples:** `test_gestures.py`, `test_pipeline_runtime.py`, `test_bootstrap.py`

**`src/vision_mouse/resources/`:**

**Purpose:** packaged runtime assets

**Examples:** `resources/models/hand_landmarker.task`

**`.specs/`:**

**Purpose:** feature planning artifacts and state tracking

**Examples:** `.specs/features/visionmouse-pro-macos-mvp/`, `.specs/STATE.md`

**`.codex/`:**

**Purpose:** local Codex rules and project skills

**Examples:** `.codex/skills/map-codebase/`, `.codex/rules/engineering/`
