from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from vision_mouse.calibration.profile import CalibrationProfileStore
from vision_mouse.calibration.session import CalibrationAnalyzer
from vision_mouse.config import AppConfig, PointerAssistConfig
from vision_mouse.domain.vision import (
    CursorSample,
    FrameSize,
    Landmark,
    NormalizedPoint,
    ProcessedLandmarkFrame,
    ScreenPoint,
)
from vision_mouse.mapping.pointer_assist import PointerAssistFilter


class PointerAssistTests(unittest.TestCase):
    def test_deadzone_holds_cursor_when_jitter_is_small(self) -> None:
        assist = PointerAssistFilter(PointerAssistConfig(deadzone_radius_px=12, deadzone_release_radius_px=20), (200, 200))

        first = assist.apply(make_cursor_sample(100, 100))
        second = assist.apply(make_cursor_sample(106, 104))

        self.assertEqual(first.screen_position, ScreenPoint(x=100, y=100))
        self.assertEqual(second.screen_position, ScreenPoint(x=100, y=100))

    def test_edge_resistance_slows_cursor_near_screen_edge(self) -> None:
        assist = PointerAssistFilter(
            PointerAssistConfig(
                deadzone_radius_px=0,
                deadzone_release_radius_px=0,
                edge_margin_px=30,
                edge_slowdown=0.4,
                corner_margin_px=40,
                corner_slowdown=0.2,
            ),
            (200, 200),
        )

        assist.apply(make_cursor_sample(120, 80))
        slowed = assist.apply(make_cursor_sample(190, 80))

        self.assertLess(slowed.screen_position.x, 190)
        self.assertGreater(slowed.screen_position.x, 120)


class CalibrationTests(unittest.TestCase):
    def test_analyzer_derives_profile_from_captured_frames(self) -> None:
        analyzer = CalibrationAnalyzer()
        movement_frames = [
            make_frame(0.20 + (index * 0.10), 0.25 + (index * 0.06), thumb_x=0.50)
            for index in range(7)
        ]
        steady_frames = [
            make_frame(0.50 + jitter, 0.50 + jitter, thumb_x=0.50)
            for jitter in (0.0, 0.001, -0.001, 0.0015, -0.0015, 0.0005)
        ]
        pinch_frames = [
            make_frame(0.55, 0.50, thumb_x=0.50),
            make_frame(0.53, 0.50, thumb_x=0.50),
            make_frame(0.51, 0.50, thumb_x=0.50),
            make_frame(0.58, 0.50, thumb_x=0.50),
            make_frame(0.64, 0.50, thumb_x=0.50),
            make_frame(0.67, 0.50, thumb_x=0.50),
        ]

        result = analyzer.analyze(movement_frames, steady_frames, pinch_frames)

        self.assertLess(result.operational_window["x_min"], 0.25)
        self.assertGreater(result.operational_window["x_max"], 0.75)
        self.assertGreater(result.pointer_assist["deadzone_radius_px"], 0)
        self.assertLess(
            result.gestures["left_pinch_threshold"],
            result.gestures["pinch_release_threshold"],
        )

    def test_profile_store_saves_and_applies_calibration_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CalibrationProfileStore(Path(tmpdir) / "profile.json")
            store.save(
                {
                    "operational_window": {"x_min": 0.2, "x_max": 0.8},
                    "smoothing": {"slow_alpha": 0.09},
                    "pointer_assist": {"deadzone_radius_px": 18},
                    "gestures": {"pre_click_lock_threshold": 0.07},
                }
            )

            resolved = store.apply(AppConfig())

            self.assertEqual(resolved.operational_window.x_min, 0.2)
            self.assertEqual(resolved.operational_window.x_max, 0.8)
            self.assertEqual(resolved.smoothing.slow_alpha, 0.09)
            self.assertEqual(resolved.pointer_assist.deadzone_radius_px, 18)
            self.assertEqual(resolved.gestures.pre_click_lock_threshold, 0.07)


def make_frame(index_x: float, index_y: float, *, thumb_x: float) -> ProcessedLandmarkFrame:
    landmarks = []
    for landmark_id in range(21):
        x = 0.4
        y = 0.6
        if landmark_id == 4:
            x, y = thumb_x, 0.50
        elif landmark_id == 5:
            x, y = index_x, index_y
        elif landmark_id == 8:
            x, y = index_x, index_y
        landmarks.append(Landmark(id=landmark_id, x=x, y=y, z=0.0))

    return ProcessedLandmarkFrame(
        timestamp=datetime(2026, 5, 11, tzinfo=timezone.utc),
        hand_detected=True,
        confidence=0.95,
        landmarks=tuple(landmarks),
        source_frame_size=FrameSize(width=640, height=480),
    )


def make_cursor_sample(x: int, y: int) -> CursorSample:
    return CursorSample(
        timestamp=datetime(2026, 5, 11, tzinfo=timezone.utc),
        reference_point=Landmark(id=8, x=0.5, y=0.5, z=0.0),
        normalized_position=NormalizedPoint(x=0.5, y=0.5),
        screen_position=ScreenPoint(x=x, y=y),
        smoothed=True,
    )


if __name__ == "__main__":
    unittest.main()
