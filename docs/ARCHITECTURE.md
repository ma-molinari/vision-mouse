# Architecture

**Pattern:** modular monolith with a ports-and-adapters structure around a real-time gesture pipeline

## High-Level Structure

The codebase is organized around a local runtime that converts webcam frames into gesture intents and then routes those intents to macOS input adapters.

```text
main.py
  -> app/composition.py
     -> build adapters and processors
        -> application/pipeline.py
           -> capture/session.py
           -> vision/mediapipe_provider.py
           -> mapping/*
           -> filters/temporal.py
           -> gestures/*
           -> application/routing.py
           -> platform/macos/*
```

There is also a second path for guided calibration:

```text
main.py calibrate
  -> calibration/session.py
     -> capture/session.py
     -> vision/mediapipe_provider.py
     -> calibration/profile.py
```

## Identified Patterns

### Ports And Adapters

**Location:** `src/vision_mouse/application/ports.py` plus concrete adapters under `capture/`, `vision/`, `platform/`, and `observability/`

**Purpose:** keep the core pipeline expressed in capability-oriented interfaces instead of binding directly to OpenCV, MediaPipe, or macOS APIs

**Implementation:** runtime-checkable `Protocol` types such as `FrameSourcePort`, `LandmarkProviderPort`, `PointerOutputPort`, and `PermissionMonitorPort` are injected into `VisionMousePipeline` and `IntentRouter`

**Example:** `MacOSInputAdapter` satisfies `PointerOutputPort`; `MediaPipeLandmarkProvider` satisfies `LandmarkProviderPort`

### Composition Root

**Location:** `src/vision_mouse/app/composition.py`

**Purpose:** centralize dependency wiring for production runtime

**Implementation:** `build_app(config)` creates telemetry, permission monitoring, macOS adapters, MediaPipe provider, cursor processors, gesture engine, router, and coordinator before attaching them to one `VisionMousePipeline`

**Example:** `build_app()` validates MediaPipe runtime before the pipeline is returned

### Operational State Gate

**Location:** `src/vision_mouse/application/operational.py`

**Purpose:** prevent input emission when camera access, accessibility access, or pipeline health is not ready

**Implementation:** `OperationalStateController` owns the current `OperationalState`, caches permission snapshots, starts or blocks the pipeline, and releases active inputs when the system degrades

**Example:** `IntentRouter.dispatch()` checks `state_provider()` and immediately releases active inputs if `can_emit_input` is false

### Stateful Temporal Recognizers

**Location:** `src/vision_mouse/gestures/*`

**Purpose:** recognize gestures from motion over time instead of frame-by-frame stateless thresholds

**Implementation:** each recognizer owns internal state such as pinch timestamps, swipe history, cooldowns, or drag state

**Example:** `ClickGestureRecognizer` tracks pinch activation, release, cooldown, and cursor locking; `WorkspaceGestureRecognizer` stores recent wrist positions in a deque

### Data-First Domain Modeling

**Location:** `src/vision_mouse/domain/*` and `src/vision_mouse/application/contracts.py`

**Purpose:** keep pipeline payloads serializable, testable, and framework-light

**Implementation:** dataclasses model frames, landmarks, cursor samples, gesture intents, permission snapshots, and operational state

**Example:** `ProcessedLandmarkFrame`, `CursorSample`, and `GestureIntent`

### Compatibility Facades

**Location:** `src/vision_mouse/app/bootstrap.py`, `src/vision_mouse/pipeline/runtime.py`, `src/vision_mouse/pipeline/router.py`

**Purpose:** preserve older import paths while the application layer becomes the canonical implementation

**Implementation:** thin facades or re-exports wrap `OperationalStateController`, `VisionMousePipeline`, and `IntentRouter`

**Example:** `pipeline/runtime.py` re-exports `PipelinePorts`, `PipelineProcessors`, and `VisionMousePipeline` from `application/pipeline.py`

## Data Flow

### Runtime Gesture Flow

1. `main.py` resolves `AppConfig`, optionally overlays saved calibration, and asks `app/composition.py` to build the runtime.
2. `OperationalStateController.start()` checks camera and accessibility readiness before starting the pipeline.
3. `VisionMousePipeline.start()` opens `WebcamSession` and spawns a dedicated capture thread.
4. The capture thread continually reads frames and keeps only the latest frame when processing falls behind.
5. `process_next_frame()` sends the latest `CapturedFrame` to `MediaPipeLandmarkProvider.detect()`.
6. `ConfidenceGate` decides whether the current stream is operational enough to move the cursor.
7. `CursorMapper` projects the tracked hand point into screen coordinates.
8. `ExponentialCursorSmoother` and `PointerAssistFilter` reduce jitter and edge overshoot.
9. `GestureEngine` merges click, drag, scroll, workspace, and macro recognizers into semantic `GestureIntent` values.
10. `IntentRouter` translates intents into macOS pointer actions, AppleScript workspace actions, or macro execution.
11. `PipelineTelemetry` records per-stage latency, FPS, and health events during the whole loop.

### Calibration Flow

1. `main.py calibrate` creates `GuidedCalibrationSession`.
2. Calibration reuses `WebcamSession` and `MediaPipeLandmarkProvider` instead of duplicating capture or detection logic.
3. Three guided phases capture movement, steady hold, and pinch samples.
4. `CalibrationAnalyzer` derives operational window, smoothing, pointer assist, and gesture thresholds from the captured landmarks.
5. `CalibrationProfileStore` writes the resulting JSON profile to disk.
6. Future runs call `CalibrationProfileStore.apply()` during startup to overlay the saved values onto `AppConfig`.

### Failure And Recovery Flow

1. Dependency or runtime validation failures are surfaced before the app begins emitting input.
2. Processing failures in the pipeline are treated as degraded health, logged via telemetry, and followed by `release_active_inputs()`.
3. Permission loss or accessibility unavailability forces the operational mode back to `BLOCKED`.

## Code Organization

**Approach:** feature-oriented package layout with a lightweight layered split between domain contracts, application orchestration, and infrastructure adapters

**Structure:**

- `app/`: composition and compatibility bootstrap
- `application/`: ports, routing, operational control, and main pipeline orchestration
- `domain/`: pure dataclasses and enums
- `capture/`, `vision/`, `platform/`: infrastructure adapters
- `mapping/`, `filters/`, `gestures/`: signal-processing and intent-building logic
- `calibration/`: profile persistence and guided calibration flow
- `observability/`: telemetry sink

**Module boundaries:**

- Domain types do not import concrete OpenCV, MediaPipe, or macOS libraries.
- Application orchestration depends on ports plus domain objects.
- Infrastructure adapters own vendor imports and OS calls.
- Tests rely heavily on fake adapters to validate behavior at module boundaries.

The result is a codebase that is small but intentionally segmented, with most cross-module coordination happening through explicit dataclasses and protocol ports.
