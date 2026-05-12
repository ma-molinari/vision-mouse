from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from vision_mouse.config import GestureConfig
from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind
from vision_mouse.domain.vision import CursorSample, ProcessedLandmarkFrame

from .common import distance_between


@dataclass
class DragState:
    pinch_started_at: Optional[datetime] = None
    drag_active: bool = False


class DragGestureRecognizer:
    def __init__(self, config: GestureConfig) -> None:
        self.config = config
        self.state = DragState()

    @property
    def drag_active(self) -> bool:
        return self.state.drag_active

    def recognize(
        self,
        frame: ProcessedLandmarkFrame,
        cursor_sample: Optional[CursorSample],
    ) -> list[GestureIntent]:
        now = frame.timestamp
        if not frame.hand_detected:
            return self._end_drag(now, frame.confidence, "hand_lost")

        distance = distance_between(frame, 4, 8)
        if distance is None:
            return self._end_drag(now, frame.confidence, "missing_landmarks")

        if distance <= self.config.left_pinch_threshold:
            if self.state.pinch_started_at is None:
                self.state.pinch_started_at = now
                return []

            duration_ms = int((now - self.state.pinch_started_at).total_seconds() * 1000)
            if not self.state.drag_active and duration_ms >= self.config.drag_hold_ms:
                self.state.drag_active = True
                return [
                    GestureIntent(
                        timestamp=now,
                        intent=GestureIntentKind.BEGIN_DRAG,
                        confidence=frame.confidence,
                        source_gesture="sustained_thumb_index_pinch",
                        requires_exclusive_pointer_state=True,
                        cursor_sample=cursor_sample,
                    )
                ]

            if self.state.drag_active:
                return [
                    GestureIntent(
                        timestamp=now,
                        intent=GestureIntentKind.UPDATE_DRAG,
                        confidence=frame.confidence,
                        source_gesture="sustained_thumb_index_pinch",
                        requires_exclusive_pointer_state=True,
                        cursor_sample=cursor_sample,
                    )
                ]

            return []

        if distance >= self.config.pinch_release_threshold:
            return self._end_drag(now, frame.confidence, "drag_release")

        return []

    def _end_drag(self, now: datetime, confidence: float, source: str) -> list[GestureIntent]:
        pinch_started = self.state.pinch_started_at
        was_active = self.state.drag_active
        self.state = DragState()

        if not was_active and pinch_started is None:
            return []

        if not was_active:
            return []

        return [
            GestureIntent(
                timestamp=now,
                intent=GestureIntentKind.END_DRAG,
                confidence=confidence,
                source_gesture=source,
                requires_exclusive_pointer_state=True,
            )
        ]
