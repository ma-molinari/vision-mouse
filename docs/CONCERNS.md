# Concerns

## Macro Gesture Support Is Wired But Currently Inert

**Risk:** medium

**Evidence:** `src/vision_mouse/gestures/macros.py` builds `MacroGestureRecognizer`, stores macro bindings, and emits `GestureIntentKind.MACRO`, but `_gesture_matches()` currently returns `False` unconditionally. `src/vision_mouse/platform/macos/macros.py` already implements at least one concrete action (`APP_SWITCHER`), so the execution path exists while recognition does not.

**Impact:** macro bindings can be configured but will never trigger at runtime, which is easy to mistake for an OS automation issue.

**Suggested fix:** either implement actual gesture matching for configured bindings, or validate at startup that macro gesture recognition is not yet supported and fail loudly instead of silently accepting the configuration.

## Test Execution Is Easy To Point At The Wrong Package

**Risk:** high for contributor experience, low for production runtime

**Evidence:** running `python3 -m unittest discover -s tests -v` on 2026-05-11 imported an installed `vision_mouse` package from `/Users/ma-molinari/Library/Python/3.9/lib/python/site-packages/vision_mouse/...` and produced `25` errors plus `4` failures. Running `env PYTHONPATH=src python3 -m unittest discover -s tests -v` against the local source tree passed all `53` tests.

**Impact:** developers can get misleading failures that do not reflect the checked-out code, especially if they have an older editable or non-editable install on the machine.

**Suggested fix:** keep recommending `make test`, add a fast-fail assertion that `vision_mouse.__file__` resolves inside the repo during tests, or provide a small wrapper script so the intended import path is unambiguous.

## Screen-Size Detection Can Silently Degrade Cursor Mapping

**Risk:** medium

**Evidence:** `src/vision_mouse/mapping/cursor_mapper.py` uses `pyautogui` in `DefaultScreenSizeProvider`, but neither `pyproject.toml` nor `setup.py` declares `pyautogui` as a dependency. If import fails, the provider silently falls back to `(1920, 1080)`.

**Impact:** cursor scaling can be wrong on Retina displays, ultrawide monitors, or multi-monitor setups, and the failure mode is silent rather than observable.

**Suggested fix:** replace the fallback with a macOS-native display query, or declare and validate the dependency explicitly. At minimum, log when the hard-coded fallback is used.

## Permission Probing Conflates Authorization With Runtime Availability

**Risk:** medium

**Evidence:** `OpenCVCameraReadinessProbe.is_camera_ready()` in `src/vision_mouse/platform/macos/permissions.py` returns `False` both when the camera is unavailable and when `cv2` cannot be imported. `MacOSPermissionMonitor.snapshot()` converts that single boolean into `PermissionState.DENIED`. `request_camera_access()` only rechecks readiness; it does not actively prompt the OS.

**Impact:** missing dependencies, camera hardware issues, and true permission problems are collapsed into the same blocked state, which can send users toward the wrong remediation path.

**Suggested fix:** split the camera probe into distinct outcomes such as dependency missing, device unavailable, and permission denied. Surface those separately in startup messaging and operational state.

## Real macOS And Hardware Paths Are Not Automatically Exercised

**Risk:** medium

**Evidence:** the inspected tests use fakes or patches for the webcam, MediaPipe result objects, `pynput` controller creation, permissions, and router collaborators. No automated tests were found for a live webcam, real accessibility trust state, or real `osascript` execution.

**Impact:** regressions in actual device access, OS automation permissions, or runtime packaging can slip through even when the fast local suite is green.

**Suggested fix:** add an opt-in macOS smoke suite, a manual validation checklist tied to releases, or a separate hardware verification script that exercises camera open, model load, input output, and Accessibility trust.

## Compatibility Facades Increase Import-Surface Drift Risk

**Risk:** low to medium

**Evidence:** `src/vision_mouse/app/bootstrap.py`, `src/vision_mouse/pipeline/runtime.py`, and `src/vision_mouse/pipeline/router.py` are thin facades or re-exports over the canonical implementations in `application/*`.

**Impact:** the public import surface is broader than the actual implementation surface, which makes refactors slightly harder and can lead to stale documentation or divergent tests if both namespaces continue to evolve.

**Suggested fix:** document which namespace is canonical for new code. Once downstream imports are stable, consider deprecating the redundant aliases.
