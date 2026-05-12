from __future__ import annotations

import unittest
from unittest.mock import patch

from vision_mouse.application.ports import (
    FrameSourcePort,
    IntentDispatchingPort,
    LandmarkProviderPort,
    MacroExecutionPort,
    PermissionMonitorPort,
    PointerOutputPort,
    TelemetryPort,
    WorkspaceNavigationPort,
)
from vision_mouse.application.routing import IntentRouter
from vision_mouse.capture.session import WebcamSession
from vision_mouse.config import CaptureConfig, MediaPipeConfig
from vision_mouse.domain.runtime import OperationalMode, OperationalState
from vision_mouse.observability.telemetry import PipelineTelemetry
from vision_mouse.platform.macos.input import MacOSInputAdapter
from vision_mouse.platform.macos.macros import AppleScriptMacroExecutor
from vision_mouse.platform.macos.permissions import MacOSPermissionMonitor
from vision_mouse.platform.macos.workspace import AppleScriptWorkspaceNavigator
from vision_mouse.vision.mediapipe_provider import MediaPipeLandmarkProvider


class ApplicationPortContractTests(unittest.TestCase):
    def test_capture_session_matches_frame_source_port(self) -> None:
        self.assertIsInstance(WebcamSession(CaptureConfig()), FrameSourcePort)

    def test_landmark_provider_matches_landmark_port(self) -> None:
        self.assertIsInstance(MediaPipeLandmarkProvider(MediaPipeConfig()), LandmarkProviderPort)

    def test_telemetry_matches_telemetry_port(self) -> None:
        self.assertIsInstance(PipelineTelemetry(), TelemetryPort)

    def test_permission_monitor_matches_permission_port(self) -> None:
        self.assertIsInstance(MacOSPermissionMonitor(), PermissionMonitorPort)

    def test_workspace_and_macro_adapters_match_ports(self) -> None:
        self.assertIsInstance(AppleScriptWorkspaceNavigator(), WorkspaceNavigationPort)
        self.assertIsInstance(AppleScriptMacroExecutor(), MacroExecutionPort)

    def test_pointer_output_and_router_match_ports(self) -> None:
        fake_mouse = FakeMouse()
        with patch.object(MacOSInputAdapter, "_build_mouse_controller", return_value=fake_mouse):
            pointer_output = MacOSInputAdapter()

        router = IntentRouter(
            pointer_output=pointer_output,
            workspace_navigator=AppleScriptWorkspaceNavigator(),
            macro_executor=AppleScriptMacroExecutor(),
            state_provider=lambda: OperationalState(
                mode=OperationalMode.READY,
                camera_ready=True,
                accessibility_ready=True,
                pipeline_healthy=True,
            ),
        )

        self.assertIsInstance(pointer_output, PointerOutputPort)
        self.assertIsInstance(router, IntentDispatchingPort)


class FakeMouse:
    def __init__(self) -> None:
        self.positions: list[tuple[int, int]] = []

    @property
    def position(self) -> tuple[int, int] | None:
        if not self.positions:
            return None
        return self.positions[-1]

    @position.setter
    def position(self, value: tuple[int, int]) -> None:
        self.positions.append(value)


if __name__ == "__main__":
    unittest.main()
