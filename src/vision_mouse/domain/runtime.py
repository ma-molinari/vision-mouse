from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Optional

from .vision import utc_now


class OperationalMode(str, Enum):
    BLOCKED = "blocked"
    DEGRADED = "degraded"
    READY = "ready"


@dataclass(frozen=True)
class OperationalState:
    mode: OperationalMode
    camera_ready: bool
    accessibility_ready: bool
    pipeline_healthy: bool
    active_drag: bool = False
    last_failure_reason: Optional[str] = None
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def can_emit_input(self) -> bool:
        return (
            self.mode is OperationalMode.READY
            and self.camera_ready
            and self.accessibility_ready
            and self.pipeline_healthy
        )

    def with_active_drag(self, active_drag: bool) -> "OperationalState":
        return replace(self, active_drag=active_drag, updated_at=utc_now())
