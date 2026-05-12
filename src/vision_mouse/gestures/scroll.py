from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, Optional

from vision_mouse.config import GestureConfig
from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind
from vision_mouse.domain.vision import ProcessedLandmarkFrame

from .common import is_two_finger_gesture, landmark_x, landmark_y


@dataclass
class _ContinuousScrollState:
    active: bool = False
    neutral_y: Optional[float] = None
    last_emitted_at: Optional[datetime] = None


class ScrollGestureRecognizer:
    def __init__(self, config: GestureConfig) -> None:
        self.config = config
        self.history: Deque[tuple[datetime, float, float]] = deque()
        self.continuous_scroll = _ContinuousScrollState()

    @property
    def continuous_scroll_active(self) -> bool:
        return self.continuous_scroll.active

    @property
    def pinch_scroll_active(self) -> bool:
        return False

    @property
    def right_click_blocked(self) -> bool:
        return False

    def recognize(
        self,
        frame: ProcessedLandmarkFrame,
        *,
        pointer_exclusive: bool,
        drag_active: bool,
    ) -> list[GestureIntent]:
        if not frame.hand_detected:
            self.history.clear()
            self.continuous_scroll = _ContinuousScrollState()
            return []

        return self._recognize_continuous_scroll(
            frame,
            pointer_exclusive=pointer_exclusive or drag_active,
        )

    def _recognize_continuous_scroll(
        self,
        frame: ProcessedLandmarkFrame,
        *,
        pointer_exclusive: bool,
    ) -> list[GestureIntent]:
        if pointer_exclusive:
            self.history.clear()
            self.continuous_scroll = _ContinuousScrollState()
            return []

        wrist_x = landmark_x(frame, 0)
        wrist_y = landmark_y(frame, 0)
        if wrist_x is None or wrist_y is None:
            return []

        now = frame.timestamp
        self.history.append((now, wrist_x, wrist_y))
        cutoff = now - timedelta(milliseconds=self.config.scroll_history_ms)
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

        if not is_two_finger_gesture(frame, self.config):
            self.history.clear()
            self.continuous_scroll = _ContinuousScrollState()
            return []

        if len(self.history) < 2:
            return []

        delta_x = self.history[-1][1] - self.history[0][1]
        delta_y = self.history[-1][2] - self.history[0][2]

        if not self.continuous_scroll.active:
            dominant_vertical = abs(delta_y) > (abs(delta_x) * self.config.two_finger_axis_lock_ratio)
            if abs(delta_y) < self.config.continuous_scroll_step_px or not dominant_vertical:
                return []

            self.continuous_scroll = _ContinuousScrollState(
                active=True,
                neutral_y=self.history[0][2],
                last_emitted_at=None,
            )

        neutral_y = self.continuous_scroll.neutral_y if self.continuous_scroll.neutral_y is not None else wrist_y
        offset_y = wrist_y - neutral_y
        if abs(offset_y) < self.config.continuous_scroll_step_px:
            return []

        if self.continuous_scroll.last_emitted_at is not None:
            elapsed_ms = int((now - self.continuous_scroll.last_emitted_at).total_seconds() * 1000)
            if elapsed_ms < self.config.continuous_scroll_repeat_ms:
                return []

        units = round((-offset_y / self.config.continuous_scroll_step_px) * self.config.continuous_scroll_units)
        if units == 0:
            return []

        self.continuous_scroll.last_emitted_at = now
        return [
            GestureIntent(
                timestamp=now,
                intent=GestureIntentKind.SCROLL,
                confidence=frame.confidence,
                source_gesture="two_finger_vertical_scroll",
                requires_exclusive_pointer_state=False,
                scroll_delta=units,
            )
        ]
