from __future__ import annotations

from dataclasses import replace
from typing import Callable, Optional

from vision_mouse.application.contracts import PermissionSnapshot
from vision_mouse.application.ports import InputReleasePort, PermissionMonitorPort, PipelineLifecyclePort
from vision_mouse.domain.runtime import OperationalMode, OperationalState
from vision_mouse.domain.vision import utc_now


class OperationalStateController:
    def __init__(
        self,
        permission_monitor: PermissionMonitorPort,
        pipeline: Optional[PipelineLifecyclePort] = None,
        input_controller: Optional[InputReleasePort] = None,
        initial_state: Optional[OperationalState] = None,
    ) -> None:
        self.permission_monitor = permission_monitor
        self.pipeline = pipeline
        self.input_controller = input_controller
        self.state_did_change: Optional[Callable[[OperationalState], None]] = None
        self._last_permission_snapshot: Optional[PermissionSnapshot] = None
        self.operational_state = initial_state or OperationalState(
            mode=OperationalMode.BLOCKED,
            camera_ready=False,
            accessibility_ready=False,
            pipeline_healthy=False,
            last_failure_reason="bootstrap_not_started",
        )

    def start(self, prompt_for_accessibility: bool = False) -> None:
        snapshot = self._refresh_permission_snapshot()

        if not snapshot.camera.is_granted:
            self.permission_monitor.request_camera_access()
            snapshot = self._refresh_permission_snapshot()

        if prompt_for_accessibility and not snapshot.accessibility.is_granted:
            self.permission_monitor.request_accessibility_prompt()
            snapshot = self._refresh_permission_snapshot()

        if not snapshot.camera.is_granted or not snapshot.accessibility.is_granted:
            self._transition(self._blocked_state(snapshot, self._permission_failure_reason(snapshot)))
            return

        try:
            if self.pipeline:
                self.pipeline.start()
            self._transition(self._ready_state(snapshot))
        except Exception as error:  # pragma: no cover - defensive path
            if self.input_controller:
                self.input_controller.release_active_inputs()
            self._transition(self._degraded_state(snapshot, f"pipeline_start_failed:{error}"))

    def refresh_operational_state(self) -> None:
        snapshot = self._refresh_permission_snapshot()

        if not snapshot.camera.is_granted or not snapshot.accessibility.is_granted:
            if self.input_controller:
                self.input_controller.release_active_inputs()
            self._transition(self._blocked_state(snapshot, self._permission_failure_reason(snapshot)))
            return

        if self.operational_state.mode is OperationalMode.DEGRADED:
            self._transition(
                self._degraded_state(
                    snapshot,
                    self.operational_state.last_failure_reason or "pipeline_degraded",
                )
            )
            return

        self._transition(self._ready_state(snapshot))

    def update_pipeline_health(self, is_healthy: bool, reason: Optional[str] = None) -> None:
        snapshot = self._permission_snapshot()

        if not snapshot.camera.is_granted or not snapshot.accessibility.is_granted:
            if self.input_controller:
                self.input_controller.release_active_inputs()
            self._transition(self._blocked_state(snapshot, self._permission_failure_reason(snapshot)))
            return

        if is_healthy:
            self._transition(self._ready_state(snapshot))
        else:
            if self.input_controller:
                self.input_controller.release_active_inputs()
            self._transition(self._degraded_state(snapshot, reason or "pipeline_unhealthy"))

    def stop(self) -> None:
        if self.pipeline:
            self.pipeline.stop()
        if self.input_controller:
            self.input_controller.release_active_inputs()

        snapshot = self._refresh_permission_snapshot()
        self._transition(
            OperationalState(
                mode=OperationalMode.BLOCKED,
                camera_ready=snapshot.camera.is_granted,
                accessibility_ready=snapshot.accessibility.is_granted,
                pipeline_healthy=False,
                active_drag=False,
                last_failure_reason="pipeline_stopped",
            )
        )

    def get_operational_state(self) -> OperationalState:
        return self.operational_state

    def _permission_snapshot(self) -> PermissionSnapshot:
        if self._last_permission_snapshot is not None:
            return self._last_permission_snapshot
        return self._refresh_permission_snapshot()

    def _refresh_permission_snapshot(self) -> PermissionSnapshot:
        snapshot = self.permission_monitor.snapshot()
        self._last_permission_snapshot = snapshot
        return snapshot

    def _transition(self, new_state: OperationalState) -> None:
        self.operational_state = replace(new_state, updated_at=utc_now())
        if self.state_did_change:
            self.state_did_change(self.operational_state)

    def _ready_state(self, snapshot: PermissionSnapshot) -> OperationalState:
        return OperationalState(
            mode=OperationalMode.READY,
            camera_ready=snapshot.camera.is_granted,
            accessibility_ready=snapshot.accessibility.is_granted,
            pipeline_healthy=True,
        )

    def _degraded_state(self, snapshot: PermissionSnapshot, reason: str) -> OperationalState:
        return OperationalState(
            mode=OperationalMode.DEGRADED,
            camera_ready=snapshot.camera.is_granted,
            accessibility_ready=snapshot.accessibility.is_granted,
            pipeline_healthy=False,
            last_failure_reason=reason,
        )

    def _blocked_state(self, snapshot: PermissionSnapshot, reason: str) -> OperationalState:
        return OperationalState(
            mode=OperationalMode.BLOCKED,
            camera_ready=snapshot.camera.is_granted,
            accessibility_ready=snapshot.accessibility.is_granted,
            pipeline_healthy=False,
            last_failure_reason=reason,
        )

    @staticmethod
    def _permission_failure_reason(snapshot: PermissionSnapshot) -> str:
        if not snapshot.camera.is_granted and not snapshot.accessibility.is_granted:
            return "camera_and_accessibility_permissions_required"
        if not snapshot.camera.is_granted:
            return "camera_permission_required"
        return "accessibility_permission_required"
