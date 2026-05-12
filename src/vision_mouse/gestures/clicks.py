from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from vision_mouse.config import GestureConfig
from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind
from vision_mouse.domain.vision import CursorSample, ProcessedLandmarkFrame

from .common import distance_between


@dataclass
class _PinchState:
    active: bool = False
    candidate_started_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    last_emitted_at: Optional[datetime] = None
    previous_distance: Optional[float] = None
    lock_active: bool = False
    locked_cursor_sample: Optional[CursorSample] = None


class ClickGestureRecognizer:
    def __init__(self, config: GestureConfig) -> None:
        self.config = config
        self.left_state = _PinchState()
        self.right_state = _PinchState()

    def release_cursor_lock(self) -> None:
        self._clear_lock(self.left_state)

    def recognize(
        self,
        frame: ProcessedLandmarkFrame,
        *,
        cursor_sample: Optional[CursorSample] = None,
        drag_active: bool = False,
        suppress_right_click: bool = False,
    ) -> tuple[list[GestureIntent], Optional[CursorSample]]:
        intents: list[GestureIntent] = []
        effective_cursor_sample = cursor_sample

        if not frame.hand_detected:
            self.left_state = _PinchState()
            self.right_state = _PinchState()
            return intents, effective_cursor_sample

        effective_cursor_sample = self._apply_cursor_lock(
            frame,
            self.left_state,
            cursor_sample,
            drag_active=drag_active,
        )

        intents.extend(
            self._handle_pinch(
                frame=frame,
                state=self.left_state,
                target="thumb_index_pinch",
                threshold=self.config.left_pinch_threshold,
                landmark_pair=(4, 8),
                intent_kind=GestureIntentKind.LEFT_CLICK,
                max_duration_ms=self.config.drag_hold_ms,
                drag_active=drag_active,
            )
        )
        intents.extend(
            self._handle_pinch(
                frame=frame,
                state=self.right_state,
                target="thumb_middle_pinch",
                threshold=self.config.right_pinch_threshold,
                landmark_pair=(4, 12),
                intent_kind=GestureIntentKind.RIGHT_CLICK,
                max_duration_ms=None,
                drag_active=drag_active,
                suppressed=suppress_right_click,
            )
        )
        return intents, effective_cursor_sample

    def _handle_pinch(
        self,
        *,
        frame: ProcessedLandmarkFrame,
        state: _PinchState,
        target: str,
        threshold: float,
        landmark_pair: tuple[int, int],
        intent_kind: GestureIntentKind,
        max_duration_ms: Optional[int],
        drag_active: bool,
        suppressed: bool = False,
    ) -> list[GestureIntent]:
        distance = distance_between(frame, landmark_pair[0], landmark_pair[1])
        if distance is None:
            state.previous_distance = None
            self._clear_lock(state)
            return []

        now = frame.timestamp
        cooldown_ms = self.config.click_cooldown_ms
        if distance <= threshold and not state.active:
            state.previous_distance = distance
            if distance <= (threshold - self.config.pinch_strong_activation_margin):
                state.active = True
                state.candidate_started_at = now
                state.started_at = now
                return []

            if state.candidate_started_at is None:
                state.candidate_started_at = now
                return []

            held_ms = int((now - state.candidate_started_at).total_seconds() * 1000)
            if held_ms < self.config.pinch_activation_ms:
                return []

            state.active = True
            state.started_at = state.candidate_started_at
            return []

        if distance <= threshold:
            state.previous_distance = distance
            return []

        if distance >= self.config.pinch_release_threshold and state.active:
            started_at = state.started_at or now
            duration_ms = int((now - started_at).total_seconds() * 1000)
            state.active = False
            state.candidate_started_at = None
            state.started_at = None
            state.previous_distance = distance
            self._clear_lock(state)

            if drag_active:
                return []

            if suppressed:
                return []

            if duration_ms < self.config.click_confirmation_ms:
                return []

            if max_duration_ms is not None and duration_ms >= max_duration_ms:
                return []

            if state.last_emitted_at is not None:
                since_last_ms = int((now - state.last_emitted_at).total_seconds() * 1000)
                if since_last_ms < cooldown_ms:
                    return []

            state.last_emitted_at = now
            return [
                GestureIntent(
                    timestamp=now,
                    intent=intent_kind,
                    confidence=frame.confidence,
                    source_gesture=target,
                    requires_exclusive_pointer_state=True,
                )
            ]

        state.candidate_started_at = None
        state.previous_distance = distance
        return []

    def _apply_cursor_lock(
        self,
        frame: ProcessedLandmarkFrame,
        state: _PinchState,
        cursor_sample: Optional[CursorSample],
        *,
        drag_active: bool,
    ) -> Optional[CursorSample]:
        distance = distance_between(frame, 4, 8)
        if distance is None or cursor_sample is None or drag_active:
            state.previous_distance = distance
            self._clear_lock(state)
            return cursor_sample

        closing_fast_enough = (
            state.previous_distance is not None
            and (state.previous_distance - distance) >= self.config.pre_click_lock_delta
        )
        entering_lock_zone = distance <= self.config.pre_click_lock_threshold
        should_lock = entering_lock_zone and (closing_fast_enough or state.active or state.lock_active)

        if should_lock and not state.lock_active:
            state.lock_active = True
            state.locked_cursor_sample = cursor_sample
        elif distance >= self.config.pinch_release_threshold:
            self._clear_lock(state)

        state.previous_distance = distance
        return state.locked_cursor_sample if state.lock_active else cursor_sample

    @staticmethod
    def _clear_lock(state: _PinchState) -> None:
        state.lock_active = False
        state.locked_cursor_sample = None
