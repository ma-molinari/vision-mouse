from __future__ import annotations

from typing import Iterable, Optional, Protocol, runtime_checkable

from vision_mouse.application.contracts import CapturedFrame, PermissionSnapshot
from vision_mouse.domain.gestures import GestureIntent, MacroAction, WorkspaceDirection
from vision_mouse.domain.vision import CursorSample, ProcessedLandmarkFrame, ScreenPoint


@runtime_checkable
class FrameSourcePort(Protocol):
    def open(self) -> None:
        ...

    def read_frame(self) -> CapturedFrame:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class LandmarkProviderPort(Protocol):
    @property
    def last_metrics(self) -> dict[str, float]:
        ...

    def validate_runtime(self) -> None:
        ...

    def detect(self, frame: CapturedFrame) -> ProcessedLandmarkFrame:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class PointerOutputPort(Protocol):
    @property
    def pointer_exclusive_state(self) -> bool:
        ...

    def move_pointer(self, screen_point: ScreenPoint) -> None:
        ...

    def click_primary(self) -> None:
        ...

    def click_secondary(self) -> None:
        ...

    def scroll_vertical(self, amount: int) -> None:
        ...

    def begin_drag(self, cursor_sample: CursorSample | None) -> None:
        ...

    def update_drag(self, cursor_sample: CursorSample | None) -> None:
        ...

    def end_drag(self) -> None:
        ...

    def release_active_inputs(self) -> None:
        ...


@runtime_checkable
class WorkspaceNavigationPort(Protocol):
    def trigger_workspace_action(self, direction: WorkspaceDirection) -> None:
        ...


@runtime_checkable
class MacroExecutionPort(Protocol):
    def execute(self, action: MacroAction) -> None:
        ...


@runtime_checkable
class TelemetryPort(Protocol):
    def record_metric(self, name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        ...

    def log_event(
        self,
        level: str,
        message: str,
        context: Optional[dict[str, object]] = None,
    ) -> None:
        ...


@runtime_checkable
class PermissionMonitorPort(Protocol):
    def snapshot(self) -> PermissionSnapshot:
        ...

    def request_camera_access(self) -> bool:
        ...

    def request_accessibility_prompt(self) -> bool:
        ...


@runtime_checkable
class IntentDispatchingPort(Protocol):
    @property
    def pointer_exclusive_state(self) -> bool:
        ...

    def dispatch_many(self, intents: Iterable[GestureIntent]) -> None:
        ...

    def release_active_inputs(self) -> None:
        ...


@runtime_checkable
class PipelineLifecyclePort(Protocol):
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...


@runtime_checkable
class InputReleasePort(Protocol):
    def release_active_inputs(self) -> None:
        ...
