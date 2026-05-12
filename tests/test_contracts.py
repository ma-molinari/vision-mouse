from __future__ import annotations

import unittest
from datetime import datetime, timezone

from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind
from vision_mouse.domain.runtime import OperationalMode, OperationalState
from vision_mouse.domain.vision import (
    CursorSample,
    FrameSize,
    Landmark,
    NormalizedPoint,
    ProcessedLandmarkFrame,
    ScreenPoint,
)


class ContractsTests(unittest.TestCase):
    def test_contracts_remain_framework_agnostic(self) -> None:
        timestamp = datetime.fromtimestamp(1000, tz=timezone.utc)
        frame = ProcessedLandmarkFrame(
            timestamp=timestamp,
            hand_detected=True,
            confidence=0.95,
            landmarks=(Landmark(id=8, x=0.5, y=0.25, z=-0.02),),
            source_frame_size=FrameSize(width=1280, height=720),
        )

        cursor_sample = CursorSample(
            timestamp=timestamp,
            reference_point=frame.landmarks[0],
            normalized_position=NormalizedPoint(x=0.5, y=0.25),
            screen_position=ScreenPoint(x=960, y=540),
            smoothed=True,
        )
        intent = GestureIntent(
            timestamp=timestamp,
            intent=GestureIntentKind.MOVE_CURSOR,
            confidence=0.9,
            source_gesture="index_tip",
            requires_exclusive_pointer_state=False,
            cursor_sample=cursor_sample,
        )
        state = OperationalState(
            mode=OperationalMode.READY,
            camera_ready=True,
            accessibility_ready=True,
            pipeline_healthy=True,
        )

        self.assertEqual(frame.landmark(8), frame.landmarks[0])
        self.assertEqual(intent.cursor_sample, cursor_sample)
        self.assertTrue(state.can_emit_input)


if __name__ == "__main__":
    unittest.main()
