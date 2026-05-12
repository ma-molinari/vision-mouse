# Testing Infrastructure

## Test Frameworks

**Unit / integration-style tests:** Python standard library `unittest`

**E2E:** none found

**Coverage:** no coverage tool or threshold configuration found

## Test Organization

**Location:** `tests/`

**Naming:** flat `test_*.py` modules

**Structure:** one file per subsystem or concern, with helper fakes defined inline when needed

Representative files:

- `test_gestures.py`
- `test_mapping_filters.py`
- `test_pipeline_runtime.py`
- `test_bootstrap.py`
- `test_application_ports.py`

## Testing Patterns

### Unit Tests

**Approach:** direct behavior checks on pure or mostly pure classes

**Location:** `tests/test_gestures.py`, `tests/test_mapping_filters.py`, `tests/test_pointer_assist_and_calibration.py`, `tests/test_contracts.py`

Observed patterns:

- synthetic `ProcessedLandmarkFrame` values are built directly in tests
- gesture recognizers are exercised with timestamped frame sequences
- mapping, smoothing, and pointer assist logic are verified numerically
- calibration analysis is validated from constructed landmark samples

### Integration-Style Tests

**Approach:** orchestrator-level tests with fake adapters instead of real hardware or OS calls

**Location:** `tests/test_pipeline_runtime.py`, `tests/test_bootstrap.py`, `tests/test_router.py`, `tests/test_application_ports.py`

Observed patterns:

- fake capture sessions, landmark providers, and input adapters stand in for infrastructure
- the threaded pipeline is started and stopped for real inside tests
- port conformance is asserted with `isinstance(..., ProtocolType)`
- routing tests verify operational gating and intent forwarding

### Adapter Tests

**Approach:** patch concrete adapter factories and inspect effects on test doubles

**Location:** `tests/test_input_adapter.py`, `tests/test_main.py`, `tests/test_mediapipe_provider.py`

Observed patterns:

- `unittest.mock.patch` replaces `pynput` controller creation
- fake MediaPipe result objects validate mapping into domain models
- CLI startup errors are checked for actionable messages

### E2E Tests

**Approach:** none found

**Location:** none found

There are no automated tests that exercise a real webcam, real MediaPipe runtime, Accessibility trust flow, `pynput`, or AppleScript on macOS hardware.

## Test Execution

**Primary command:** `make test`

**Equivalent local command:** `env PYTHONPATH=src python3 -m unittest discover -s tests -v`

**Build validation:** `make build`

## Configuration

**Project config:** `pyproject.toml` sets `pythonpath = ["src"]` for pytest-compatible runners

**Makefile config:** `Makefile` exports `PYTHONPATH=src` for `run`, `test`, and `build`

**Observed gotcha:** running `python3 -m unittest discover -s tests -v` without `PYTHONPATH=src` can import an installed `vision_mouse` package instead of the local source tree if one exists in site-packages

## Coverage Targets

**Current:** no automated percentage reporting found

**Goals:** none documented in the repo files inspected

**Enforcement:** none found

## Verified Status

On 2026-05-11, the local suite passed when executed against the repo source with:

```bash
env PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Observed result: `Ran 53 tests in 4.131s` and `OK`.
