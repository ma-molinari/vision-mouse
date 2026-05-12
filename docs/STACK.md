# Tech Stack

**Analyzed:** 2026-05-11

## Core

- Framework: no web framework; modular local desktop pipeline assembled in `src/vision_mouse/app/composition.py`
- Language: Python `>=3.9`
- Runtime: CPython, usually from `.venv` through `Makefile`
- Package manager: `pip`
- Build system: `setuptools>=68.0`
- Packaging layout: `src/` layout with a legacy `setup.py` compatibility shim for older Xcode-bundled tooling

## Desktop / Runtime

- Application style: local, single-process hand-tracking pipeline
- CLI entrypoint: `vision_mouse.main`
- Configuration style: immutable dataclass configs in `src/vision_mouse/config.py`
- Packaging asset: bundled MediaPipe model at `src/vision_mouse/resources/models/hand_landmarker.task`

## Vision / Input

- Hand tracking: `mediapipe>=0.10.0`
- Camera capture and frame normalization: `opencv-python>=4.10.0`
- Native pointer input: `pynput>=1.7.0`
- Optional screen-size lookup: `pyautogui` imported lazily in `DefaultScreenSizeProvider` but not declared as a project dependency

## Architecture Support

- Contract layer: `typing.Protocol` ports in `src/vision_mouse/application/ports.py`
- Domain modeling: dataclasses and enums in `src/vision_mouse/domain/*`
- Telemetry: in-memory metric/event recorder in `src/vision_mouse/observability/telemetry.py`
- Persistence: JSON calibration profiles in `src/vision_mouse/calibration/profile.py`

## Platform Integration

- Native permissions: macOS ApplicationServices via `ctypes`
- System settings deep-link: `open x-apple.systempreferences:...`
- Workspace switching: `osascript`
- Macro execution: `osascript`

## Backend

- API style: none; in-process pipeline only
- Database: none
- ORM / query builder: none
- Authentication: none

## Testing

- Unit and integration-style tests: Python `unittest`
- Pytest configuration: only `pythonpath = ["src"]` in `pyproject.toml`
- Coverage tool: none found
- E2E framework: none found

## External Services

- Computer vision runtime: MediaPipe Tasks Hand Landmarker
- Operating system automation: macOS System Events via AppleScript
- Operating system trust check: ApplicationServices accessibility API
- User profile storage: local filesystem at `~/.vision_mouse/profile.json` unless overridden by `VISION_MOUSE_PROFILE_PATH`

## Development Tools

- Task runner: `Makefile`
- Test command: `make test`
- Bytecode validation: `make build` using `compileall`
- Packaging: `make package` / `python -m build`
