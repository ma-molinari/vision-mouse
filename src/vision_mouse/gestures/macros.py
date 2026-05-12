from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from vision_mouse.config import GestureConfig, MacroConfig
from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind, MacroAction
from vision_mouse.domain.vision import ProcessedLandmarkFrame

@dataclass
class _MacroState:
    gesture_name: Optional[str] = None
    started_at: Optional[datetime] = None
    last_emitted_at: Optional[datetime] = None


class MacroGestureRecognizer:
    def __init__(self, gesture_config: GestureConfig, macro_config: MacroConfig) -> None:
        self.gesture_config = gesture_config
        self.macro_config = macro_config
        self.state = _MacroState()

    def recognize(
        self,
        frame: ProcessedLandmarkFrame,
        *,
        pointer_exclusive: bool,
    ) -> list[GestureIntent]:
        if pointer_exclusive or not frame.hand_detected:
            self.state = _MacroState(last_emitted_at=self.state.last_emitted_at)
            return []

        matched_gesture = self._matched_gesture(frame)
        if matched_gesture is None:
            self.state.gesture_name = None
            self.state.started_at = None
            return []

        now = frame.timestamp
        if self.state.gesture_name != matched_gesture:
            self.state.gesture_name = matched_gesture
            self.state.started_at = now
            return []

        if self.state.started_at is None:
            self.state.started_at = now
            return []

        held_ms = int((now - self.state.started_at).total_seconds() * 1000)
        if held_ms < self.gesture_config.macro_hold_ms:
            return []

        if self.state.last_emitted_at is not None:
            cooldown_ms = int((now - self.state.last_emitted_at).total_seconds() * 1000)
            if cooldown_ms < self.gesture_config.macro_cooldown_ms:
                return []

        self.state.last_emitted_at = now
        action = next(
            MacroAction(binding.action)
            for binding in self.macro_config.bindings
            if binding.gesture == matched_gesture
        )
        return [
            GestureIntent(
                timestamp=now,
                intent=GestureIntentKind.MACRO,
                confidence=frame.confidence,
                source_gesture=matched_gesture,
                requires_exclusive_pointer_state=False,
                macro_action=action,
            )
        ]

    def _matched_gesture(self, frame: ProcessedLandmarkFrame) -> Optional[str]:
        for binding in self.macro_config.bindings:
            if self._gesture_matches(frame, binding.gesture):
                return binding.gesture
        return None

    def _gesture_matches(self, frame: ProcessedLandmarkFrame, gesture_name: str) -> bool:
        return False
