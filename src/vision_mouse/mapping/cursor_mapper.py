from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from vision_mouse.config import OperationalWindow
from vision_mouse.domain.vision import (
    CursorSample,
    Landmark,
    NormalizedPoint,
    ProcessedLandmarkFrame,
    ScreenPoint,
)


class ScreenSizeProvider(Protocol):
    def screen_size(self) -> tuple[int, int]:
        ...


@dataclass(frozen=True)
class StaticScreenSizeProvider:
    width: int
    height: int

    def screen_size(self) -> tuple[int, int]:
        return self.width, self.height


class DefaultScreenSizeProvider:
    def screen_size(self) -> tuple[int, int]:
        try:
            import pyautogui  # type: ignore
        except ImportError:
            return 1920, 1080

        size = pyautogui.size()
        return int(size.width), int(size.height)


class CursorMapper:
    def __init__(
        self,
        screen_provider: ScreenSizeProvider,
        operational_window: OperationalWindow,
        reference_landmark_id: int = 8,
        stability_landmark_id: int = 5,
        reference_weight: float = 0.35,
    ) -> None:
        self.screen_provider = screen_provider
        self.operational_window = operational_window
        self.reference_landmark_id = reference_landmark_id
        self.stability_landmark_id = stability_landmark_id
        self.reference_weight = reference_weight
        self._screen_size = self.screen_provider.screen_size()

    def refresh_screen_size(self) -> tuple[int, int]:
        self._screen_size = self.screen_provider.screen_size()
        return self._screen_size

    def map_to_screen(
        self,
        frame: ProcessedLandmarkFrame,
        *,
        smoothed: bool = False,
    ) -> CursorSample:
        reference_point = self._reference_point(frame)
        if reference_point is None:
            raise ValueError("reference_landmark_missing")

        normalized = self.apply_operational_window(reference_point)
        screen_width, screen_height = self._screen_size
        screen_point = ScreenPoint(
            x=int(normalized.x * max(screen_width - 1, 1)),
            y=int(normalized.y * max(screen_height - 1, 1)),
        )

        return CursorSample(
            timestamp=frame.timestamp,
            reference_point=reference_point,
            normalized_position=normalized,
            screen_position=screen_point,
            smoothed=smoothed,
        )

    def _reference_point(self, frame: ProcessedLandmarkFrame) -> Landmark | None:
        reference_point = frame.landmark(self.reference_landmark_id)
        if reference_point is None:
            return None

        stable_point = frame.landmark(self.stability_landmark_id)
        if stable_point is None:
            return reference_point

        stable_weight = 1.0 - self.reference_weight
        return Landmark(
            id=self.reference_landmark_id,
            x=(reference_point.x * self.reference_weight) + (stable_point.x * stable_weight),
            y=(reference_point.y * self.reference_weight) + (stable_point.y * stable_weight),
            z=(reference_point.z * self.reference_weight) + (stable_point.z * stable_weight),
        )

    def apply_operational_window(self, point: Landmark) -> NormalizedPoint:
        x = self._normalize_axis(point.x, self.operational_window.x_min, self.operational_window.x_max)
        y = self._normalize_axis(point.y, self.operational_window.y_min, self.operational_window.y_max)
        return NormalizedPoint(x=x, y=y)

    @staticmethod
    def _normalize_axis(value: float, minimum: float, maximum: float) -> float:
        clamped = min(max(value, minimum), maximum)
        if maximum <= minimum:
            return 0.5
        return (clamped - minimum) / (maximum - minimum)
