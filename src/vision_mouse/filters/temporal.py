from __future__ import annotations

from dataclasses import replace
from typing import Optional

from vision_mouse.config import SmoothingConfig
from vision_mouse.domain.vision import CursorSample, NormalizedPoint, ScreenPoint


class ConfidenceGate:
    def __init__(self, config: SmoothingConfig) -> None:
        self.config = config
        self._stable_frames = 0
        self._dropout_frames = 0
        self._operational = False

    def is_operational(self, hand_detected: bool, confidence: float) -> bool:
        if hand_detected and confidence >= self.config.min_confidence:
            self._dropout_frames = 0
            self._stable_frames += 1
            if self._stable_frames >= self.config.reacquire_frames:
                self._operational = True
            return self._operational

        if self._operational:
            self._dropout_frames += 1
            if self._dropout_frames <= self.config.dropout_tolerance_frames:
                return True

        self._stable_frames = 0
        self._dropout_frames = 0
        self._operational = False
        return False


class ExponentialCursorSmoother:
    def __init__(self, config: SmoothingConfig) -> None:
        self.alpha = config.alpha
        self.slow_alpha = config.slow_alpha
        self.fast_alpha = config.fast_alpha
        self.slow_movement_px = config.slow_movement_px
        self.fast_movement_px = config.fast_movement_px
        self._last_sample: Optional[CursorSample] = None

    def smooth(self, sample: CursorSample) -> CursorSample:
        if self._last_sample is None:
            self._last_sample = replace(sample, smoothed=True)
            return self._last_sample

        alpha = self._dynamic_alpha(sample)
        normalized = NormalizedPoint(
            x=self._blend(self._last_sample.normalized_position.x, sample.normalized_position.x, alpha),
            y=self._blend(self._last_sample.normalized_position.y, sample.normalized_position.y, alpha),
        )
        screen = ScreenPoint(
            x=round(self._blend(self._last_sample.screen_position.x, sample.screen_position.x, alpha)),
            y=round(self._blend(self._last_sample.screen_position.y, sample.screen_position.y, alpha)),
        )

        smoothed_sample = CursorSample(
            timestamp=sample.timestamp,
            reference_point=sample.reference_point,
            normalized_position=normalized,
            screen_position=screen,
            smoothed=True,
        )
        self._last_sample = smoothed_sample
        return smoothed_sample

    def reset(self) -> None:
        self._last_sample = None

    def _blend(self, previous: float, current: float, alpha: float) -> float:
        return previous + alpha * (current - previous)

    def _dynamic_alpha(self, sample: CursorSample) -> float:
        if self._last_sample is None:
            return self.alpha

        delta_x = sample.screen_position.x - self._last_sample.screen_position.x
        delta_y = sample.screen_position.y - self._last_sample.screen_position.y
        movement_px = (delta_x**2 + delta_y**2) ** 0.5

        if movement_px <= self.slow_movement_px:
            return self.slow_alpha

        if movement_px >= self.fast_movement_px:
            return self.fast_alpha

        span = self.fast_movement_px - self.slow_movement_px
        if span <= 0:
            return self.alpha

        progress = (movement_px - self.slow_movement_px) / span
        return self.slow_alpha + (self.fast_alpha - self.slow_alpha) * progress
