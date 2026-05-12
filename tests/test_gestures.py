from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from vision_mouse.config import GestureConfig
from vision_mouse.domain.gestures import GestureIntentKind, WorkspaceDirection
from vision_mouse.domain.vision import (
    CursorSample,
    FrameSize,
    Landmark,
    NormalizedPoint,
    ProcessedLandmarkFrame,
    ScreenPoint,
)
from vision_mouse.gestures.engine import GestureEngine


class GestureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = GestureEngine(GestureConfig())
        self.frame_size = FrameSize(width=640, height=480)
        self.base_time = datetime(2026, 5, 10, tzinfo=timezone.utc)

    def test_left_click_emits_on_pinch_release(self) -> None:
        pinch_frame = make_frame(
            self.base_time,
            {
                4: (0.50, 0.50, 0.0),
                8: (0.53, 0.50, 0.0),
            },
        )
        release_frame = make_frame(
            self.base_time + timedelta(milliseconds=120),
            {
                4: (0.50, 0.50, 0.0),
                8: (0.65, 0.50, 0.0),
            },
        )

        intents, _ = self.engine.classify(pinch_frame, None, pointer_exclusive=False)
        self.assertEqual(intents, [])
        intents, _ = self.engine.classify(release_frame, None, pointer_exclusive=False)

        self.assertEqual([intent.intent for intent in intents], [GestureIntentKind.LEFT_CLICK])

    def test_sustained_pinch_begins_and_ends_drag(self) -> None:
        pinch_frame = make_frame(
            self.base_time,
            {
                4: (0.50, 0.50, 0.0),
                8: (0.53, 0.50, 0.0),
            },
        )
        hold_frame = make_frame(
            self.base_time + timedelta(milliseconds=400),
            {
                4: (0.50, 0.50, 0.0),
                8: (0.53, 0.50, 0.0),
            },
        )
        release_frame = make_frame(
            self.base_time + timedelta(milliseconds=520),
            {
                4: (0.50, 0.50, 0.0),
                8: (0.68, 0.50, 0.0),
            },
        )

        self.engine.classify(pinch_frame, None, pointer_exclusive=False)
        begin_intents, _ = self.engine.classify(hold_frame, None, pointer_exclusive=False)
        end_intents, _ = self.engine.classify(release_frame, None, pointer_exclusive=False)

        self.assertEqual([intent.intent for intent in begin_intents], [GestureIntentKind.BEGIN_DRAG])
        self.assertEqual([intent.intent for intent in end_intents], [GestureIntentKind.END_DRAG])

    def test_workspace_swipe_requires_open_hand_pose(self) -> None:
        start_frame = make_open_hand_frame(self.base_time, wrist_x=0.2)
        end_frame = make_open_hand_frame(
            self.base_time + timedelta(milliseconds=200),
            wrist_x=0.5,
        )

        intents, _ = self.engine.classify(start_frame, None, pointer_exclusive=False)
        self.assertEqual(intents, [])
        intents, _ = self.engine.classify(end_frame, None, pointer_exclusive=False)

        self.assertEqual([intent.intent for intent in intents], [GestureIntentKind.WORKSPACE_NAVIGATION])
        self.assertEqual(intents[0].workspace_direction, WorkspaceDirection.RIGHT)

    def test_workspace_swipe_is_blocked_when_thumb_is_too_close_to_index(self) -> None:
        start_frame = make_open_hand_frame(
            self.base_time,
            wrist_x=0.2,
            thumb=(0.30, 0.33, 0.0),
            index_tip=(0.35, 0.30, 0.0),
        )
        end_frame = make_open_hand_frame(
            self.base_time + timedelta(milliseconds=200),
            wrist_x=0.5,
            thumb=(0.40, 0.33, 0.0),
            index_tip=(0.45, 0.30, 0.0),
        )

        self.engine.classify(start_frame, None, pointer_exclusive=False)
        intents, _ = self.engine.classify(end_frame, None, pointer_exclusive=False)

        self.assertEqual(intents, [])

    def test_left_pinch_locks_cursor_before_release(self) -> None:
        engine = GestureEngine(
            GestureConfig(pre_click_lock_threshold=0.075, pre_click_lock_delta=0.002)
        )
        first_frame = make_frame(
            self.base_time,
            {
                4: (0.50, 0.50, 0.0),
                8: (0.58, 0.50, 0.0),
            },
        )
        lock_frame = make_frame(
            self.base_time + timedelta(milliseconds=16),
            {
                4: (0.50, 0.50, 0.0),
                8: (0.57, 0.50, 0.0),
            },
        )
        drifting_frame = make_frame(
            self.base_time + timedelta(milliseconds=32),
            {
                4: (0.50, 0.50, 0.0),
                8: (0.53, 0.50, 0.0),
            },
        )

        _, stabilized = engine.classify(
            first_frame,
            make_cursor_sample(first_frame.timestamp, 500, 500),
            pointer_exclusive=False,
        )
        self.assertEqual(stabilized.screen_position.x, 500)

        _, stabilized = engine.classify(
            lock_frame,
            make_cursor_sample(lock_frame.timestamp, 520, 500),
            pointer_exclusive=False,
        )
        self.assertEqual(stabilized.screen_position.x, 520)

        _, stabilized = engine.classify(
            drifting_frame,
            make_cursor_sample(drifting_frame.timestamp, 620, 500),
            pointer_exclusive=False,
        )
        self.assertEqual(stabilized.screen_position.x, 520)

    def test_two_finger_vertical_motion_emits_continuous_scroll(self) -> None:
        start_frame = make_two_finger_frame(self.base_time, wrist_x=0.30, wrist_y=0.72)
        end_frame = make_two_finger_frame(
            self.base_time + timedelta(milliseconds=120),
            wrist_x=0.31,
            wrist_y=0.55,
        )

        intents, _ = self.engine.classify(start_frame, None, pointer_exclusive=False)
        self.assertEqual(intents, [])
        intents, _ = self.engine.classify(end_frame, None, pointer_exclusive=False)

        self.assertEqual([intent.intent for intent in intents], [GestureIntentKind.SCROLL])
        self.assertGreater(intents[0].scroll_delta, 0)

    def test_two_finger_scroll_is_blocked_when_thumb_looks_like_pinch(self) -> None:
        start_frame = make_two_finger_frame(
            self.base_time,
            wrist_x=0.30,
            wrist_y=0.72,
            thumb=(0.30, 0.33, 0.0),
            index_tip=(0.35, 0.30, 0.0),
        )
        end_frame = make_two_finger_frame(
            self.base_time + timedelta(milliseconds=120),
            wrist_x=0.31,
            wrist_y=0.55,
            thumb=(0.30, 0.33, 0.0),
            index_tip=(0.35, 0.30, 0.0),
        )

        self.engine.classify(start_frame, None, pointer_exclusive=False)
        intents, _ = self.engine.classify(end_frame, None, pointer_exclusive=False)

        self.assertEqual(intents, [])

    def test_one_finger_pose_does_not_trigger_scroll(self) -> None:
        start_frame = make_one_finger_frame(self.base_time, wrist_x=0.30, wrist_y=0.72)
        end_frame = make_one_finger_frame(
            self.base_time + timedelta(milliseconds=120),
            wrist_x=0.31,
            wrist_y=0.55,
        )

        self.engine.classify(start_frame, None, pointer_exclusive=False)
        intents, _ = self.engine.classify(end_frame, None, pointer_exclusive=False)

        self.assertEqual(intents, [])

    def test_two_finger_scroll_continues_without_resetting_gesture(self) -> None:
        engine = GestureEngine(
            GestureConfig(
                continuous_scroll_step_px=0.04,
                continuous_scroll_units=16,
                continuous_scroll_repeat_ms=30,
            )
        )
        start_frame = make_two_finger_frame(self.base_time, wrist_x=0.30, wrist_y=0.74)
        engage_frame = make_two_finger_frame(
            self.base_time + timedelta(milliseconds=100),
            wrist_x=0.31,
            wrist_y=0.58,
        )
        sustained_frame = make_two_finger_frame(
            self.base_time + timedelta(milliseconds=180),
            wrist_x=0.31,
            wrist_y=0.58,
        )

        engine.classify(start_frame, None, pointer_exclusive=False)
        first_intents, _ = engine.classify(engage_frame, None, pointer_exclusive=False)
        second_intents, _ = engine.classify(sustained_frame, None, pointer_exclusive=False)

        self.assertEqual([intent.intent for intent in first_intents], [GestureIntentKind.SCROLL])
        self.assertEqual([intent.intent for intent in second_intents], [GestureIntentKind.SCROLL])
        self.assertEqual(first_intents[0].scroll_delta, second_intents[0].scroll_delta)

    def test_two_finger_vertical_motion_does_not_trigger_workspace_swipe(self) -> None:
        start_frame = make_two_finger_frame(self.base_time, wrist_x=0.30, wrist_y=0.74)
        end_frame = make_two_finger_frame(
            self.base_time + timedelta(milliseconds=120),
            wrist_x=0.40,
            wrist_y=0.52,
        )

        self.engine.classify(start_frame, None, pointer_exclusive=False)
        intents, _ = self.engine.classify(end_frame, None, pointer_exclusive=False)

        self.assertEqual([intent.intent for intent in intents], [GestureIntentKind.SCROLL])

    def test_open_hand_horizontal_motion_does_not_trigger_scroll(self) -> None:
        start_frame = make_open_hand_frame(self.base_time, wrist_x=0.18, wrist_y=0.60)
        end_frame = make_open_hand_frame(
            self.base_time + timedelta(milliseconds=120),
            wrist_x=0.38,
            wrist_y=0.64,
        )

        self.engine.classify(start_frame, None, pointer_exclusive=False)
        intents, _ = self.engine.classify(end_frame, None, pointer_exclusive=False)

        self.assertEqual([intent.intent for intent in intents], [GestureIntentKind.WORKSPACE_NAVIGATION])

    def test_thumb_middle_pinch_vertical_motion_does_not_emit_scroll(self) -> None:
        engine = GestureEngine(GestureConfig())
        pinch_start = make_frame(
            self.base_time,
            {
                4: (0.50, 0.50, 0.0),
                12: (0.54, 0.52, 0.0),
            },
        )
        pinch_move = make_frame(
            self.base_time + timedelta(milliseconds=80),
            {
                4: (0.50, 0.50, 0.0),
                12: (0.52, 0.45, 0.0),
            },
        )
        release = make_frame(
            self.base_time + timedelta(milliseconds=160),
            {
                4: (0.50, 0.50, 0.0),
                12: (0.70, 0.44, 0.0),
            },
        )

        engine.classify(pinch_start, None, pointer_exclusive=False)
        intents, _ = engine.classify(pinch_move, None, pointer_exclusive=False)
        release_intents, _ = engine.classify(release, None, pointer_exclusive=False)

        self.assertEqual(intents, [])
        self.assertEqual([intent.intent for intent in release_intents], [GestureIntentKind.RIGHT_CLICK])

    def test_brief_thumb_index_contact_does_not_emit_click(self) -> None:
        engine = GestureEngine(GestureConfig(pinch_activation_ms=40))
        pinch_frame = make_frame(
            self.base_time,
            {
                4: (0.50, 0.50, 0.0),
                8: (0.53, 0.50, 0.0),
            },
        )
        release_frame = make_frame(
            self.base_time + timedelta(milliseconds=20),
            {
                4: (0.50, 0.50, 0.0),
                8: (0.68, 0.50, 0.0),
            },
        )

        engine.classify(pinch_frame, None, pointer_exclusive=False)
        intents, _ = engine.classify(release_frame, None, pointer_exclusive=False)

        self.assertEqual(intents, [])

def make_frame(timestamp: datetime, overrides: dict[int, tuple[float, float, float]]) -> ProcessedLandmarkFrame:
    landmarks = []
    for landmark_id in range(21):
        x, y, z = overrides.get(landmark_id, (0.4, 0.6, 0.0))
        landmarks.append(Landmark(id=landmark_id, x=x, y=y, z=z))
    return ProcessedLandmarkFrame(
        timestamp=timestamp,
        hand_detected=True,
        confidence=0.9,
        landmarks=tuple(landmarks),
        source_frame_size=FrameSize(width=640, height=480),
    )

def make_two_finger_frame(
    timestamp: datetime,
    wrist_x: float,
    wrist_y: float = 0.8,
    *,
    thumb: tuple[float, float, float] = (0.22, 0.48, 0.0),
    index_tip: tuple[float, float, float] = (0.35, 0.30, 0.0),
    middle_tip: tuple[float, float, float] = (0.45, 0.28, 0.0),
    ring_tip: tuple[float, float, float] = (0.55, 0.68, 0.0),
    pinky_tip: tuple[float, float, float] = (0.65, 0.70, 0.0),
) -> ProcessedLandmarkFrame:
    overrides = {
        0: (wrist_x, wrist_y, 0.0),
        4: thumb,
        6: (0.35, 0.55, 0.0),
        8: index_tip,
        10: (0.45, 0.55, 0.0),
        12: middle_tip,
        14: (0.55, 0.58, 0.0),
        16: ring_tip,
        18: (0.65, 0.60, 0.0),
        20: pinky_tip,
    }
    return make_frame(timestamp, overrides)


def make_one_finger_frame(
    timestamp: datetime,
    wrist_x: float,
    wrist_y: float = 0.8,
    *,
    thumb: tuple[float, float, float] = (0.22, 0.48, 0.0),
    index_tip: tuple[float, float, float] = (0.35, 0.30, 0.0),
    middle_tip: tuple[float, float, float] = (0.45, 0.52, 0.0),
    ring_tip: tuple[float, float, float] = (0.55, 0.68, 0.0),
    pinky_tip: tuple[float, float, float] = (0.65, 0.70, 0.0),
) -> ProcessedLandmarkFrame:
    overrides = {
        0: (wrist_x, wrist_y, 0.0),
        4: thumb,
        6: (0.35, 0.55, 0.0),
        8: index_tip,
        10: (0.45, 0.55, 0.0),
        12: middle_tip,
        14: (0.55, 0.58, 0.0),
        16: ring_tip,
        18: (0.65, 0.60, 0.0),
        20: pinky_tip,
    }
    return make_frame(timestamp, overrides)


def make_open_hand_frame(
    timestamp: datetime,
    wrist_x: float,
    wrist_y: float = 0.8,
    *,
    thumb: tuple[float, float, float] = (0.22, 0.48, 0.0),
    index_tip: tuple[float, float, float] = (0.35, 0.30, 0.0),
    middle_tip: tuple[float, float, float] = (0.45, 0.28, 0.0),
    ring_tip: tuple[float, float, float] = (0.55, 0.26, 0.0),
    pinky_tip: tuple[float, float, float] = (0.65, 0.25, 0.0),
) -> ProcessedLandmarkFrame:
    overrides = {
        0: (wrist_x, wrist_y, 0.0),
        4: thumb,
        6: (0.35, 0.55, 0.0),
        8: index_tip,
        10: (0.45, 0.55, 0.0),
        12: middle_tip,
        14: (0.55, 0.58, 0.0),
        16: ring_tip,
        18: (0.65, 0.60, 0.0),
        20: pinky_tip,
    }
    return make_frame(timestamp, overrides)


def make_cursor_sample(timestamp: datetime, x: int, y: int) -> CursorSample:
    return CursorSample(
        timestamp=timestamp,
        reference_point=Landmark(id=8, x=0.5, y=0.5, z=0.0),
        normalized_position=NormalizedPoint(x=0.5, y=0.5),
        screen_position=ScreenPoint(x=x, y=y),
        smoothed=True,
    )


if __name__ == "__main__":
    unittest.main()
