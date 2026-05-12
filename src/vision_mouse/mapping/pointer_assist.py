from __future__ import annotations

from dataclasses import replace
from math import hypot

from vision_mouse.config import PointerAssistConfig
from vision_mouse.domain.vision import CursorSample, ScreenPoint


class PointerAssistFilter:
    def __init__(self, config: PointerAssistConfig, screen_size: tuple[int, int]) -> None:
        self.config = config
        self.screen_width, self.screen_height = screen_size
        self._last_output: ScreenPoint | None = None
        self._deadzone_anchor: ScreenPoint | None = None

    def apply(self, sample: CursorSample) -> CursorSample:
        proposed = sample.screen_position
        stabilized = self._apply_deadzone(proposed)
        constrained = self._apply_edge_resistance(stabilized)
        output = replace(sample, screen_position=constrained)
        self._last_output = constrained
        return output

    def reset(self) -> None:
        self._last_output = None
        self._deadzone_anchor = None

    def _apply_deadzone(self, proposed: ScreenPoint) -> ScreenPoint:
        if self._last_output is None:
            self._deadzone_anchor = proposed
            return proposed

        anchor = self._deadzone_anchor or self._last_output
        distance = self._distance(anchor, proposed)

        if distance <= self.config.deadzone_radius_px:
            self._deadzone_anchor = anchor
            return anchor

        if distance <= self.config.deadzone_release_radius_px:
            return anchor

        self._deadzone_anchor = proposed
        return proposed

    def _apply_edge_resistance(self, proposed: ScreenPoint) -> ScreenPoint:
        if self._last_output is None:
            return proposed

        horizontal_factor = self._axis_factor(proposed.x, self.screen_width - 1)
        vertical_factor = self._axis_factor(proposed.y, self.screen_height - 1)
        factor = min(horizontal_factor, vertical_factor, self._corner_factor(proposed))

        adjusted_x = round(self._last_output.x + ((proposed.x - self._last_output.x) * factor))
        adjusted_y = round(self._last_output.y + ((proposed.y - self._last_output.y) * factor))
        return ScreenPoint(x=adjusted_x, y=adjusted_y)

    def _axis_factor(self, position: int, maximum: int) -> float:
        distance_to_edge = min(position, maximum - position)
        if distance_to_edge >= self.config.edge_margin_px:
            return 1.0

        margin = max(self.config.edge_margin_px, 1)
        progress = max(distance_to_edge, 0) / margin
        return self.config.edge_slowdown + ((1.0 - self.config.edge_slowdown) * progress)

    def _corner_factor(self, point: ScreenPoint) -> float:
        corner_margin = max(self.config.corner_margin_px, 1)
        near_horizontal = min(point.x, (self.screen_width - 1) - point.x)
        near_vertical = min(point.y, (self.screen_height - 1) - point.y)

        if near_horizontal >= corner_margin or near_vertical >= corner_margin:
            return 1.0

        horizontal_progress = max(near_horizontal, 0) / corner_margin
        vertical_progress = max(near_vertical, 0) / corner_margin
        progress = max(horizontal_progress, vertical_progress)
        return self.config.corner_slowdown + ((1.0 - self.config.corner_slowdown) * progress)

    @staticmethod
    def _distance(first: ScreenPoint, second: ScreenPoint) -> float:
        return hypot(second.x - first.x, second.y - first.y)
