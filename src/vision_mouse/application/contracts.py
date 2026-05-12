from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from vision_mouse.domain.vision import FrameSize, utc_now


@dataclass(frozen=True)
class CapturedFrame:
    timestamp: datetime
    image: Any
    frame_size: FrameSize
    capture_latency_ms: float = 0.0
    normalize_latency_ms: float = 0.0


class PermissionState(str, Enum):
    AUTHORIZED = "authorized"
    DENIED = "denied"
    NOT_DETERMINED = "not_determined"
    RESTRICTED = "restricted"

    @property
    def is_granted(self) -> bool:
        return self is PermissionState.AUTHORIZED


@dataclass(frozen=True)
class PermissionSnapshot:
    camera: PermissionState
    accessibility: PermissionState
    timestamp: datetime = field(default_factory=utc_now)
