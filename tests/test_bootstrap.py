from __future__ import annotations

import unittest

from vision_mouse.app.bootstrap import AppBootstrapCoordinator
from vision_mouse.domain.runtime import OperationalMode
from vision_mouse.platform.macos.permissions import PermissionSnapshot, PermissionState


class BootstrapTests(unittest.TestCase):
    def test_start_blocks_when_permissions_are_missing(self) -> None:
        permissions = FakePermissionMonitor(
            PermissionSnapshot(
                camera=PermissionState.DENIED,
                accessibility=PermissionState.AUTHORIZED,
            )
        )
        pipeline = FakePipeline()
        input_controller = FakeInputController()
        coordinator = AppBootstrapCoordinator(
            permission_monitor=permissions,
            pipeline=pipeline,
            input_controller=input_controller,
        )

        coordinator.start()
        state = coordinator.get_operational_state()

        self.assertEqual(state.mode, OperationalMode.BLOCKED)
        self.assertFalse(state.can_emit_input)
        self.assertEqual(state.last_failure_reason, "camera_permission_required")
        self.assertEqual(pipeline.start_count, 0)
        self.assertEqual(input_controller.release_count, 0)

    def test_start_transitions_to_ready(self) -> None:
        permissions = FakePermissionMonitor(
            PermissionSnapshot(
                camera=PermissionState.AUTHORIZED,
                accessibility=PermissionState.AUTHORIZED,
            )
        )
        pipeline = FakePipeline()
        coordinator = AppBootstrapCoordinator(
            permission_monitor=permissions,
            pipeline=pipeline,
            input_controller=FakeInputController(),
        )

        observed_modes = []
        coordinator.state_did_change = lambda state: observed_modes.append(state.mode)

        coordinator.start()
        state = coordinator.get_operational_state()

        self.assertEqual(state.mode, OperationalMode.READY)
        self.assertTrue(state.can_emit_input)
        self.assertEqual(pipeline.start_count, 1)
        self.assertEqual(observed_modes, [OperationalMode.READY])

    def test_failed_pipeline_start_degrades_and_stop_cleans_up(self) -> None:
        permissions = FakePermissionMonitor(
            PermissionSnapshot(
                camera=PermissionState.AUTHORIZED,
                accessibility=PermissionState.AUTHORIZED,
            )
        )
        pipeline = FakePipeline(start_error=RuntimeError("failed"))
        input_controller = FakeInputController()
        coordinator = AppBootstrapCoordinator(
            permission_monitor=permissions,
            pipeline=pipeline,
            input_controller=input_controller,
        )

        coordinator.start()
        degraded_state = coordinator.get_operational_state()
        coordinator.stop()
        stopped_state = coordinator.get_operational_state()

        self.assertEqual(degraded_state.mode, OperationalMode.DEGRADED)
        self.assertFalse(degraded_state.can_emit_input)
        self.assertEqual(input_controller.release_count, 2)
        self.assertEqual(pipeline.stop_count, 1)
        self.assertEqual(stopped_state.mode, OperationalMode.BLOCKED)
        self.assertEqual(stopped_state.last_failure_reason, "pipeline_stopped")

    def test_update_pipeline_health_reuses_cached_permission_snapshot(self) -> None:
        permissions = FakePermissionMonitor(
            PermissionSnapshot(
                camera=PermissionState.AUTHORIZED,
                accessibility=PermissionState.AUTHORIZED,
            )
        )
        coordinator = AppBootstrapCoordinator(
            permission_monitor=permissions,
            pipeline=FakePipeline(),
            input_controller=FakeInputController(),
        )

        coordinator.start()
        snapshot_calls_after_start = permissions.snapshot_calls

        coordinator.update_pipeline_health(True)
        coordinator.update_pipeline_health(True)
        coordinator.update_pipeline_health(False, "detect_failed")

        self.assertEqual(permissions.snapshot_calls, snapshot_calls_after_start)
        self.assertEqual(coordinator.get_operational_state().mode, OperationalMode.DEGRADED)


class FakePipeline:
    def __init__(self, start_error: Exception | None = None) -> None:
        self.start_count = 0
        self.stop_count = 0
        self.start_error = start_error

    def start(self) -> None:
        self.start_count += 1
        if self.start_error is not None:
            raise self.start_error

    def stop(self) -> None:
        self.stop_count += 1


class FakeInputController:
    def __init__(self) -> None:
        self.release_count = 0

    def release_active_inputs(self) -> None:
        self.release_count += 1


class FakePermissionMonitor:
    def __init__(self, snapshot: PermissionSnapshot) -> None:
        self._snapshot = snapshot
        self.snapshot_calls = 0

    def snapshot(self) -> PermissionSnapshot:
        self.snapshot_calls += 1
        return self._snapshot

    def request_camera_access(self) -> bool:
        return self._snapshot.camera.is_granted

    def request_accessibility_prompt(self) -> bool:
        return self._snapshot.accessibility.is_granted


if __name__ == "__main__":
    unittest.main()
