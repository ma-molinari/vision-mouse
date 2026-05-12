from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Landmark:
    id: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class FrameSize:
    width: int
    height: int


@dataclass(frozen=True)
class NormalizedPoint:
    x: float
    y: float


@dataclass(frozen=True)
class ScreenPoint:
    x: int
    y: int


@dataclass(frozen=True)
class ProcessedLandmarkFrame:
    timestamp: datetime
    hand_detected: bool
    confidence: float
    landmarks: tuple[Landmark, ...]
    source_frame_size: FrameSize

    def landmark(self, landmark_id: int) -> Optional[Landmark]:
        for landmark in self.landmarks:
            if landmark.id == landmark_id:
                return landmark
        return None

    @classmethod
    def no_hand_detected(
        cls,
        source_frame_size: FrameSize,
        confidence: float = 0.0,
        timestamp: Optional[datetime] = None,
    ) -> "ProcessedLandmarkFrame":
        return cls(
            timestamp=timestamp or utc_now(),
            hand_detected=False,
            confidence=confidence,
            landmarks=tuple(),
            source_frame_size=source_frame_size,
        )


@dataclass(frozen=True)
class CursorSample:
    timestamp: datetime
    reference_point: Landmark
    normalized_position: NormalizedPoint
    screen_position: ScreenPoint
    smoothed: bool
