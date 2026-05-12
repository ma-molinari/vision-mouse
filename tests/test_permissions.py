from __future__ import annotations

import unittest
from subprocess import CompletedProcess
from unittest.mock import Mock

from vision_mouse.application.contracts import PermissionState
from vision_mouse.platform.macos.permissions import (
    MacOSPermissionMonitor,
    SwiftCameraPermissionClient,
)


class PermissionMonitorTests(unittest.TestCase):
    def test_snapshot_preserves_not_determined_camera_state_before_first_prompt(self) -> None:
        probe = FakeCameraProbe([False])
        permission_client = FakeCameraPermissionClient(
            authorization_state=PermissionState.NOT_DETERMINED
        )
        monitor = MacOSPermissionMonitor(
            camera_probe=probe,
            camera_permission_client=permission_client,
        )

        snapshot = monitor.snapshot()

        self.assertEqual(snapshot.camera, PermissionState.NOT_DETERMINED)
        self.assertEqual(probe.calls, 0)

    def test_request_camera_access_triggers_native_prompt_and_rechecks_camera(self) -> None:
        probe = FakeCameraProbe([False, True])
        permission_client = FakeCameraPermissionClient(request_result=True)
        monitor = MacOSPermissionMonitor(
            camera_probe=probe,
            camera_permission_client=permission_client,
        )

        access_granted = monitor.request_camera_access()

        self.assertTrue(access_granted)
        self.assertEqual(permission_client.request_calls, 1)
        self.assertEqual(probe.calls, 2)

    def test_snapshot_keeps_camera_blocked_until_device_can_open(self) -> None:
        probe = FakeCameraProbe([False])
        permission_client = FakeCameraPermissionClient(
            authorization_state=PermissionState.AUTHORIZED
        )
        monitor = MacOSPermissionMonitor(
            camera_probe=probe,
            camera_permission_client=permission_client,
        )

        snapshot = monitor.snapshot()

        self.assertEqual(snapshot.camera, PermissionState.DENIED)
        self.assertEqual(probe.calls, 1)


class SwiftCameraPermissionClientTests(unittest.TestCase):
    def test_authorization_state_parses_raw_status_and_sets_module_cache(self) -> None:
        runner = Mock(
            return_value=CompletedProcess(
                args=["swift", "-e", "status"],
                returncode=0,
                stdout="0\n",
                stderr="",
            )
        )
        client = SwiftCameraPermissionClient(
            runner=runner,
            swift_executable="swift",
            module_cache_dir="/tmp/vision-mouse-swift-cache",
        )

        state = client.authorization_state()

        self.assertEqual(state, PermissionState.NOT_DETERMINED)
        self.assertEqual(
            runner.call_args.kwargs["env"]["CLANG_MODULE_CACHE_PATH"],
            "/tmp/vision-mouse-swift-cache",
        )

    def test_request_access_parses_authorized_response(self) -> None:
        runner = Mock(
            return_value=CompletedProcess(
                args=["swift", "-e", "request"],
                returncode=0,
                stdout="authorized\n",
                stderr="",
            )
        )
        client = SwiftCameraPermissionClient(runner=runner)

        self.assertTrue(client.request_access())


class FakeCameraProbe:
    def __init__(self, responses: list[bool]) -> None:
        self.responses = responses
        self.calls = 0

    def is_camera_ready(self) -> bool:
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return self.responses[index]


class FakeCameraPermissionClient:
    def __init__(
        self,
        authorization_state: PermissionState | None = None,
        request_result: bool | None = None,
    ) -> None:
        self._authorization_state = authorization_state
        self._request_result = request_result
        self.request_calls = 0

    def authorization_state(self) -> PermissionState | None:
        return self._authorization_state

    def request_access(self) -> bool | None:
        self.request_calls += 1
        return self._request_result


if __name__ == "__main__":
    unittest.main()
