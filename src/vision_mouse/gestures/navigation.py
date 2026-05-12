from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Optional

from vision_mouse.config import GestureConfig
from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind, WorkspaceDirection
from vision_mouse.domain.vision import ProcessedLandmarkFrame

from .common import is_open_hand_gesture, landmark_x, landmark_y


class WorkspaceGestureRecognizer:
    def __init__(self, config: GestureConfig) -> None:
        self.config = config
        self.history: Deque[tuple[datetime, float, float]] = deque()
        self.last_emitted_at: Optional[datetime] = None
        self._swipe_lock_active = False

    @property
    def swipe_lock_active(self) -> bool:
        return self._swipe_lock_active

    def recognize(
        self,
        frame: ProcessedLandmarkFrame,
        *,
        pointer_exclusive: bool,
    ) -> list[GestureIntent]:
        if pointer_exclusive or not frame.hand_detected:
            self.history.clear()
            self._swipe_lock_active = False
            return []

        wrist_x = landmark_x(frame, 0)
        wrist_y = landmark_y(frame, 0)
        if wrist_x is None or wrist_y is None:
            return []

        now = frame.timestamp
        self.history.append((now, wrist_x, wrist_y))
        cutoff = now - timedelta(milliseconds=self.config.workspace_history_ms)
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

        if not is_open_hand_gesture(frame, self.config):
            self.history.clear()
            self._swipe_lock_active = False
            return []

        if self.last_emitted_at is not None:
            elapsed = int((now - self.last_emitted_at).total_seconds() * 1000)
            if elapsed < self.config.workspace_cooldown_ms:
                return []

        if len(self.history) < 2:
            return []

        delta_x = self.history[-1][1] - self.history[0][1]
        delta_y = self.history[-1][2] - self.history[0][2]
        dominant_horizontal = abs(delta_x) > (abs(delta_y) * self.config.two_finger_axis_lock_ratio)
        if abs(delta_x) < self.config.workspace_swipe_delta or not dominant_horizontal:
            return []

        self.last_emitted_at = now
        self._swipe_lock_active = True
        direction = WorkspaceDirection.RIGHT if delta_x > 0 else WorkspaceDirection.LEFT
        return [
            GestureIntent(
                timestamp=now,
                intent=GestureIntentKind.WORKSPACE_NAVIGATION,
                confidence=frame.confidence,
                source_gesture="workspace_swipe",
                requires_exclusive_pointer_state=False,
                workspace_direction=direction,
            )
        ]
