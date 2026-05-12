from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from vision_mouse.capture.session import CapturedFrame
from vision_mouse.config import MediaPipeConfig
from vision_mouse.domain.vision import FrameSize
from vision_mouse.vision.mediapipe_provider import MediaPipeLandmarkProvider


class MediaPipeLandmarkProviderTests(unittest.TestCase):
    def test_detect_maps_tasks_result_to_processed_landmarks(self) -> None:
        provider = MediaPipeLandmarkProvider(MediaPipeConfig())
        provider._cv2 = FakeCV2()
        provider._mp = FakeMediaPipeModule()
        provider._landmarker = FakeLandmarker(
            FakeHandLandmarkerResult(
                hand_landmarks=[
                    [
                        SimpleNamespace(x=0.25, y=0.5, z=-0.1),
                        SimpleNamespace(x=0.75, y=0.6, z=-0.2),
                    ]
                ],
                handedness=[[SimpleNamespace(score=0.91)]],
            )
        )

        frame = CapturedFrame(
            timestamp=datetime(2026, 5, 11, tzinfo=timezone.utc),
            image="bgr-frame",
            frame_size=FrameSize(width=640, height=480),
        )

        processed = provider.detect(frame)

        self.assertTrue(processed.hand_detected)
        self.assertEqual(processed.confidence, 1.0)
        self.assertEqual(len(processed.landmarks), 2)
        self.assertEqual(processed.landmarks[0].x, 0.25)
        self.assertEqual(processed.landmarks[1].id, 1)
        self.assertEqual(provider._landmarker.calls[0][1], 1778457600000)
        self.assertEqual(provider.last_metrics["mediapipe_handedness_score"], 0.91)

    def test_detect_returns_no_hand_when_tasks_result_is_empty(self) -> None:
        provider = MediaPipeLandmarkProvider(MediaPipeConfig())
        provider._cv2 = FakeCV2()
        provider._mp = FakeMediaPipeModule()
        provider._landmarker = FakeLandmarker(FakeHandLandmarkerResult(hand_landmarks=[], handedness=[]))

        frame = CapturedFrame(
            timestamp=datetime(2026, 5, 11, tzinfo=timezone.utc),
            image="bgr-frame",
            frame_size=FrameSize(width=320, height=240),
        )

        processed = provider.detect(frame)

        self.assertFalse(processed.hand_detected)
        self.assertEqual(processed.landmarks, tuple())

    def test_model_asset_path_prefers_configured_override(self) -> None:
        provider = MediaPipeLandmarkProvider(MediaPipeConfig(model_asset_path="/tmp/custom.task"))

        self.assertEqual(provider._model_asset_path(), Path("/tmp/custom.task"))

    def test_model_asset_path_defaults_to_packaged_task_file(self) -> None:
        provider = MediaPipeLandmarkProvider(MediaPipeConfig())

        asset_path = provider._model_asset_path()

        self.assertEqual(asset_path.name, "hand_landmarker.task")
        self.assertIn("resources/models", str(asset_path))


class FakeCV2:
    COLOR_BGR2RGB = "COLOR_BGR2RGB"

    @staticmethod
    def cvtColor(image: str, conversion: str) -> str:
        return f"{image}:{conversion}"


class FakeMediaPipeModule:
    ImageFormat = SimpleNamespace(SRGB="srgb")

    class Image:
        def __init__(self, image_format: str, data: str) -> None:
            self.image_format = image_format
            self.data = data


class FakeLandmarker:
    def __init__(self, result: "FakeHandLandmarkerResult") -> None:
        self.result = result
        self.calls: list[tuple[object, int]] = []

    def detect_for_video(self, image: object, timestamp_ms: int) -> "FakeHandLandmarkerResult":
        self.calls.append((image, timestamp_ms))
        return self.result


class FakeHandLandmarkerResult:
    def __init__(self, hand_landmarks: list[list[SimpleNamespace]], handedness: list[list[SimpleNamespace]]) -> None:
        self.hand_landmarks = hand_landmarks
        self.handedness = handedness


if __name__ == "__main__":
    unittest.main()
