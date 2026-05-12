from __future__ import annotations

import unittest
from datetime import datetime, timezone

from vision_mouse.config import OperationalWindow, SmoothingConfig
from vision_mouse.domain.vision import FrameSize, Landmark, ProcessedLandmarkFrame
from vision_mouse.filters.temporal import ConfidenceGate, ExponentialCursorSmoother
from vision_mouse.mapping.cursor_mapper import CursorMapper, StaticScreenSizeProvider


class MappingAndFiltersTests(unittest.TestCase):
    def test_cursor_mapper_applies_operational_window(self) -> None:
        frame = ProcessedLandmarkFrame(
            timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
            hand_detected=True,
            confidence=0.9,
            landmarks=(
                Landmark(id=5, x=0.90, y=0.92, z=0.0),
                Landmark(id=8, x=0.90, y=0.92, z=0.0),
            ),
            source_frame_size=FrameSize(width=640, height=480),
        )
        mapper = CursorMapper(
            screen_provider=StaticScreenSizeProvider(1920, 1080),
            operational_window=OperationalWindow(),
        )

        sample = mapper.map_to_screen(frame)

        self.assertEqual(sample.screen_position.x, 1919)
        self.assertEqual(sample.screen_position.y, 1079)

    def test_cursor_mapper_blends_tip_with_stable_joint(self) -> None:
        frame = ProcessedLandmarkFrame(
            timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
            hand_detected=True,
            confidence=0.9,
            landmarks=(
                Landmark(id=5, x=0.20, y=0.20, z=0.0),
                Landmark(id=8, x=0.80, y=0.80, z=0.0),
            ),
            source_frame_size=FrameSize(width=640, height=480),
        )
        mapper = CursorMapper(
            screen_provider=StaticScreenSizeProvider(1000, 1000),
            operational_window=OperationalWindow(x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0),
        )

        sample = mapper.map_to_screen(frame)

        self.assertEqual(sample.screen_position.x, 409)
        self.assertEqual(sample.screen_position.y, 409)

    def test_cursor_mapper_caches_screen_size(self) -> None:
        provider = CountingScreenSizeProvider((1920, 1080))
        mapper = CursorMapper(
            screen_provider=provider,
            operational_window=OperationalWindow(),
        )
        frame = ProcessedLandmarkFrame(
            timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
            hand_detected=True,
            confidence=0.9,
            landmarks=(
                Landmark(id=5, x=0.90, y=0.92, z=0.0),
                Landmark(id=8, x=0.90, y=0.92, z=0.0),
            ),
            source_frame_size=FrameSize(width=640, height=480),
        )

        mapper.map_to_screen(frame)
        mapper.map_to_screen(frame)

        self.assertEqual(provider.call_count, 1)

    def test_confidence_gate_requires_reacquire_frames(self) -> None:
        gate = ConfidenceGate(
            SmoothingConfig(
                min_confidence=0.7,
                reacquire_frames=2,
                dropout_tolerance_frames=0,
            )
        )

        self.assertFalse(gate.is_operational(hand_detected=True, confidence=0.9))
        self.assertTrue(gate.is_operational(hand_detected=True, confidence=0.9))
        self.assertFalse(gate.is_operational(hand_detected=False, confidence=0.0))
        self.assertFalse(gate.is_operational(hand_detected=True, confidence=0.9))

    def test_confidence_gate_tolerates_brief_dropouts(self) -> None:
        gate = ConfidenceGate(
            SmoothingConfig(min_confidence=0.7, reacquire_frames=2, dropout_tolerance_frames=2)
        )

        self.assertFalse(gate.is_operational(hand_detected=True, confidence=0.9))
        self.assertTrue(gate.is_operational(hand_detected=True, confidence=0.9))
        self.assertTrue(gate.is_operational(hand_detected=False, confidence=0.0))
        self.assertTrue(gate.is_operational(hand_detected=True, confidence=0.4))
        self.assertFalse(gate.is_operational(hand_detected=False, confidence=0.0))
        self.assertFalse(gate.is_operational(hand_detected=True, confidence=0.9))

    def test_exponential_smoother_reduces_jitter(self) -> None:
        mapper = CursorMapper(
            screen_provider=StaticScreenSizeProvider(1000, 1000),
            operational_window=OperationalWindow(x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0),
        )
        smoother = ExponentialCursorSmoother(SmoothingConfig(alpha=0.5))
        first = mapper.map_to_screen(
            ProcessedLandmarkFrame(
                timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
                hand_detected=True,
                confidence=0.9,
                landmarks=(Landmark(id=8, x=0.2, y=0.2, z=0.0),),
                source_frame_size=FrameSize(width=640, height=480),
            )
        )
        second = mapper.map_to_screen(
            ProcessedLandmarkFrame(
                timestamp=datetime(2026, 5, 10, 0, 0, 1, tzinfo=timezone.utc),
                hand_detected=True,
                confidence=0.9,
                landmarks=(Landmark(id=8, x=0.8, y=0.8, z=0.0),),
                source_frame_size=FrameSize(width=640, height=480),
            )
        )

        smoother.smooth(first)
        smoothed = smoother.smooth(second)

        self.assertTrue(200 < smoothed.screen_position.x < 800)
        self.assertTrue(200 < smoothed.screen_position.y < 800)

    def test_exponential_smoother_uses_stronger_smoothing_for_small_movements(self) -> None:
        mapper = CursorMapper(
            screen_provider=StaticScreenSizeProvider(1000, 1000),
            operational_window=OperationalWindow(x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0),
        )
        smoother = ExponentialCursorSmoother(
            SmoothingConfig(
                alpha=0.32,
                slow_alpha=0.1,
                fast_alpha=0.5,
                slow_movement_px=10.0,
                fast_movement_px=100.0,
            )
        )
        first = mapper.map_to_screen(
            ProcessedLandmarkFrame(
                timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
                hand_detected=True,
                confidence=0.9,
                landmarks=(
                    Landmark(id=5, x=0.20, y=0.20, z=0.0),
                    Landmark(id=8, x=0.20, y=0.20, z=0.0),
                ),
                source_frame_size=FrameSize(width=640, height=480),
            )
        )
        second = mapper.map_to_screen(
            ProcessedLandmarkFrame(
                timestamp=datetime(2026, 5, 10, 0, 0, 1, tzinfo=timezone.utc),
                hand_detected=True,
                confidence=0.9,
                landmarks=(
                    Landmark(id=5, x=0.206, y=0.206, z=0.0),
                    Landmark(id=8, x=0.206, y=0.206, z=0.0),
                ),
                source_frame_size=FrameSize(width=640, height=480),
            )
        )

        smoother.smooth(first)
        smoothed = smoother.smooth(second)

        self.assertEqual(smoothed.screen_position.x, 200)
        self.assertEqual(smoothed.screen_position.y, 200)


class CountingScreenSizeProvider:
    def __init__(self, size: tuple[int, int]) -> None:
        self.size = size
        self.call_count = 0

    def screen_size(self) -> tuple[int, int]:
        self.call_count += 1
        return self.size


if __name__ == "__main__":
    unittest.main()
