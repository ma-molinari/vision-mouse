# External Integrations

## Computer Vision Runtime

**Service:** MediaPipe Tasks Hand Landmarker

**Purpose:** detect hand landmarks from webcam frames for cursor mapping and gesture recognition

**Implementation:** `src/vision_mouse/vision/mediapipe_provider.py`

**Configuration:** `MediaPipeConfig` in `src/vision_mouse/config.py`; optional `model_asset_path` override; packaged fallback model at `src/vision_mouse/resources/models/hand_landmarker.task`

**Authentication:** none

## Camera Capture

**Service:** OpenCV VideoCapture

**Purpose:** open the webcam, resize frames, mirror input, and measure capture latency

**Implementation:** `src/vision_mouse/capture/session.py`

**Configuration:** `CaptureConfig` controls camera index, target size, and mirroring

**Authentication:** none

## Native Pointer Input

**Service:** `pynput`

**Purpose:** move the cursor, click, scroll, and hold drag state on macOS

**Implementation:** `src/vision_mouse/platform/macos/input.py`

**Configuration:** implicit; adapter builds a `pynput.mouse.Controller` at runtime

**Authentication:** macOS Accessibility permission is required at the OS level

## Accessibility And Permission Monitoring

**Service:** macOS ApplicationServices plus System Settings deep-link

**Purpose:** detect whether the process is trusted for accessibility and guide the user to the correct settings panel

**Implementation:** `src/vision_mouse/platform/macos/permissions.py`

**Configuration:** camera probing uses `CaptureConfig`; accessibility probing loads `/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices`

**Authentication:** OS-managed trust state

## Workspace Navigation

**Service:** AppleScript via `osascript`

**Purpose:** switch Mission Control workspaces with gesture-driven left or right navigation

**Implementation:** `src/vision_mouse/platform/macos/workspace.py`

**Configuration:** key codes are hard-coded to `123` and `124` with `control down`

**Authentication:** depends on macOS Accessibility permissions for System Events automation to succeed reliably

## Macro Execution

**Service:** AppleScript via `osascript`

**Purpose:** trigger desktop-level macro actions from recognized gestures

**Implementation:** `src/vision_mouse/platform/macos/macros.py`

**Configuration:** current concrete action is `MacroAction.APP_SWITCHER`, which maps to Command-Tab

**Authentication:** depends on macOS Accessibility permissions

## Screen Size Detection

**Service:** `pyautogui` when available

**Purpose:** read current screen dimensions for cursor mapping

**Implementation:** `DefaultScreenSizeProvider` in `src/vision_mouse/mapping/cursor_mapper.py`

**Configuration:** no explicit config; falls back to `1920x1080` if `pyautogui` cannot be imported

**Authentication:** none

## Local Profile Persistence

**Service:** local filesystem JSON storage

**Purpose:** persist calibration-derived thresholds between runs

**Implementation:** `src/vision_mouse/calibration/profile.py`

**Configuration:** default path is `~/.vision_mouse/profile.json`; override with `VISION_MOUSE_PROFILE_PATH`

**Authentication:** filesystem permissions only

## API Integrations

No HTTP, GraphQL, or third-party web API clients were found in the inspected code.

## Webhooks

No webhook handlers were found.

## Background Jobs

**Queue system:** none found

**Location:** none found

**Jobs:** none found
