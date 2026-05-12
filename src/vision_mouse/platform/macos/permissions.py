from __future__ import annotations

import ctypes
import os
import subprocess
import tempfile
from typing import Any, Callable, Optional, Protocol

from vision_mouse.application.contracts import PermissionSnapshot, PermissionState
from vision_mouse.application.ports import PermissionMonitorPort
from vision_mouse.config import CaptureConfig


class CameraReadinessProbe(Protocol):
    def is_camera_ready(self) -> bool:
        ...


class CameraPermissionClient(Protocol):
    def authorization_state(self) -> Optional[PermissionState]:
        ...

    def request_access(self) -> Optional[bool]:
        ...


class OpenCVCameraReadinessProbe:
    def __init__(self, config: CaptureConfig) -> None:
        self.config = config

    def is_camera_ready(self) -> bool:
        try:
            import cv2  # type: ignore
        except ImportError:
            return False

        capture = cv2.VideoCapture(self.config.camera_index)
        is_ready = bool(capture.isOpened())
        capture.release()
        return is_ready


class SwiftCameraPermissionClient:
    _STATUS_BY_RAW_VALUE = {
        "0": PermissionState.NOT_DETERMINED,
        "1": PermissionState.RESTRICTED,
        "2": PermissionState.DENIED,
        "3": PermissionState.AUTHORIZED,
    }
    _STATUS_BY_NAME = {
        "authorized": PermissionState.AUTHORIZED,
        "denied": PermissionState.DENIED,
        "not_determined": PermissionState.NOT_DETERMINED,
        "restricted": PermissionState.RESTRICTED,
    }
    _AUTHORIZATION_STATUS_SCRIPT = """
import AVFoundation

print(AVCaptureDevice.authorizationStatus(for: .video).rawValue)
"""
    _REQUEST_ACCESS_SCRIPT = """
import AVFoundation
import Dispatch

let currentStatus = AVCaptureDevice.authorizationStatus(for: .video)
if currentStatus == .authorized {
    print("authorized")
} else if currentStatus == .denied {
    print("denied")
} else if currentStatus == .restricted {
    print("restricted")
} else {
    let semaphore = DispatchSemaphore(value: 0)
    var granted = false

    AVCaptureDevice.requestAccess(for: .video) { permissionGranted in
        granted = permissionGranted
        semaphore.signal()
    }

    _ = semaphore.wait(timeout: .now() + .seconds(30))
    print(granted ? "authorized" : "denied")
}
"""

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        swift_executable: str = "swift",
        module_cache_dir: Optional[str] = None,
    ) -> None:
        self.runner = runner
        self.swift_executable = swift_executable
        self.module_cache_dir = module_cache_dir or os.path.join(
            tempfile.gettempdir(),
            "vision-mouse-swift-module-cache",
        )

    def authorization_state(self) -> Optional[PermissionState]:
        return self._parse_state(self._run_swift(self._AUTHORIZATION_STATUS_SCRIPT))

    def request_access(self) -> Optional[bool]:
        state = self._parse_state(self._run_swift(self._REQUEST_ACCESS_SCRIPT))
        if state is None:
            return None
        return state is PermissionState.AUTHORIZED

    def _run_swift(self, script: str) -> Optional[str]:
        env = os.environ.copy()
        env["CLANG_MODULE_CACHE_PATH"] = self.module_cache_dir
        try:
            result = self.runner(
                [self.swift_executable, "-e", script],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
        except (OSError, TypeError):
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def _parse_state(self, raw_value: Optional[str]) -> Optional[PermissionState]:
        if raw_value is None:
            return None
        normalized = raw_value.strip().lower()
        if normalized in self._STATUS_BY_NAME:
            return self._STATUS_BY_NAME[normalized]
        return self._STATUS_BY_RAW_VALUE.get(normalized)


PermissionMonitoring = PermissionMonitorPort


class MacOSPermissionMonitor(PermissionMonitorPort):
    def __init__(
        self,
        camera_probe: Optional[CameraReadinessProbe] = None,
        camera_permission_client: Optional[CameraPermissionClient] = None,
    ) -> None:
        self.camera_probe = camera_probe or OpenCVCameraReadinessProbe(CaptureConfig())
        self.camera_permission_client = camera_permission_client or SwiftCameraPermissionClient()

    def snapshot(self) -> PermissionSnapshot:
        return PermissionSnapshot(
            camera=self._camera_state(),
            accessibility=self._accessibility_state(),
        )

    def request_camera_access(self) -> bool:
        if self.camera_probe.is_camera_ready():
            return True

        native_request_result = self.camera_permission_client.request_access()
        if native_request_result is False:
            return False
        return self.camera_probe.is_camera_ready()

    def request_accessibility_prompt(self) -> bool:
        try:
            subprocess.run(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
                ],
                check=False,
                capture_output=True,
            )
        except OSError:
            return False
        return self._accessibility_state().is_granted

    def _accessibility_state(self) -> PermissionState:
        library = self._load_application_services()
        if library is None:
            return PermissionState.DENIED

        library.AXIsProcessTrusted.restype = ctypes.c_bool
        return PermissionState.AUTHORIZED if library.AXIsProcessTrusted() else PermissionState.DENIED

    def _camera_state(self) -> PermissionState:
        native_state = self.camera_permission_client.authorization_state()
        if native_state is None:
            return PermissionState.AUTHORIZED if self.camera_probe.is_camera_ready() else PermissionState.DENIED
        if native_state is not PermissionState.AUTHORIZED:
            return native_state
        return PermissionState.AUTHORIZED if self.camera_probe.is_camera_ready() else PermissionState.DENIED

    @staticmethod
    def _load_application_services() -> Optional[Any]:
        try:
            return ctypes.CDLL(
                "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            )
        except OSError:
            return None
