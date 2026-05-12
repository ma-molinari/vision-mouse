# Code Conventions

## Naming Conventions

### Files

Observed pattern: lowercase `snake_case.py` module names grouped by feature area.

Examples: `main.py`, `cursor_mapper.py`, `mediapipe_provider.py`, `test_pointer_assist_and_calibration.py`

### Classes

Observed pattern: `PascalCase` for domain models, adapters, controllers, and recognizers.

Examples: `VisionMousePipeline`, `OperationalStateController`, `MediaPipeLandmarkProvider`, `PointerAssistFilter`

### Functions And Methods

Observed pattern: `snake_case` verbs, with leading underscores for internal helpers.

Examples: `build_app`, `load_app_config`, `process_next_frame`, `_detect_landmarks`, `_permission_failure_reason`

### Variables

Observed pattern: descriptive `snake_case`, often including units or role hints.

Examples: `capture_latency_ms`, `frame_age_at_dispatch_ms`, `pointer_exclusive`, `workspace_navigator`, `drag_active`

### Constants

Observed pattern: few module-level constants; defaults usually live as dataclass fields or enum members instead.

Examples:

- config defaults such as `click_cooldown_ms`, `workspace_swipe_delta`, `deadzone_radius_px`
- enum members such as `GestureIntentKind.LEFT_CLICK` and `OperationalMode.READY`
- Makefile variables such as `PYTHONPATH`, `APP_MODULE`, `VENV_PYTHON`

## Code Organization

### Import Style

Observed pattern:

1. `from __future__ import annotations`
2. standard-library imports
3. local package imports

Representative example: `src/vision_mouse/application/pipeline.py`

### File Structure

Observed pattern: small files with data structures first, then the main class, then private helpers.

Examples:

- `application/pipeline.py` defines `PipelinePorts` and `PipelineProcessors` before `VisionMousePipeline`
- `gestures/clicks.py` defines `_PinchState` before `ClickGestureRecognizer`
- `observability/telemetry.py` defines `MetricRecord` and `LogEvent` before `PipelineTelemetry`

### Public Surface

Observed pattern: production code sometimes preserves older import paths through thin wrapper modules.

Examples:

- `app/bootstrap.py` aliases `OperationalStateController`
- `pipeline/runtime.py` re-exports runtime classes from `application/pipeline.py`
- `pipeline/router.py` re-exports `IntentRouter`

## Type Safety And Documentation

**Approach:** typed Python using dataclasses, enums, `Protocol`, `Optional`, and selective `Any`

Examples:

- ports are expressed as runtime-checkable protocols in `application/ports.py`
- domain payloads such as `ProcessedLandmarkFrame` and `GestureIntent` are frozen dataclasses
- adapter boundaries use `Any` where third-party libraries are dynamic, such as OpenCV and `pynput`

There is no mypy or pyright configuration in the repo root, so type hints are used for readability and design discipline rather than enforced static analysis.

## Error Handling

**Pattern:** adapter and infrastructure failures are wrapped in domain-relevant exception types or machine-readable string reasons

Examples:

- `CaptureSessionError("unable_to_open_camera")`
- `PlatformInputError("pynput_not_installed")`
- `LandmarkProviderError("mediapipe_task_initialization_failed:...")`

User-facing CLI code translates those errors into actionable messages in `main.py`.

Inside the runtime loop, recoverable processing failures are logged and converted into degraded operational health rather than always crashing the process.

## Comments And Documentation

**Style:** comments are sparse and usually reserved for compatibility or defensive paths

Examples:

- `app/bootstrap.py` uses a short docstring for the compatibility facade
- `setup.py` documents that it is a compatibility shim for older Xcode-bundled tooling
- several imports have `# pragma: no cover` notes on defensive dependency guards

Most intent is carried by naming and small functions instead of explanatory comments.

## Testing Style

**Pattern:** `unittest` with fake collaborators, helper constructors, and patched adapter factories

Examples:

- `tests/test_pipeline_runtime.py` uses `FakeCaptureSession`, `FakeLandmarkProvider`, and `FakeInputAdapter`
- `tests/test_input_adapter.py` patches `_build_mouse_controller`
- `tests/test_application_ports.py` asserts protocol conformance with `isinstance(..., ProtocolType)`

The test suite favors behavior-level validation over snapshotting or fixtures.

## Language Split

Observed pattern: source identifiers and exception codes are in English, while user-facing README and some console prompts are in Portuguese.

Examples:

- code names: `GestureIntentKind`, `request_accessibility_prompt`
- README text: `Controle de cursor por gestos de mao`
- calibration prompts: `Calibracao guiada do Vision Mouse`
