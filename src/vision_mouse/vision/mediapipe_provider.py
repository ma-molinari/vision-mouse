from __future__ import annotations

from datetime import datetime
from importlib import resources
from pathlib import Path
from time import perf_counter
from typing import Any, Optional

from vision_mouse.application.contracts import CapturedFrame
from vision_mouse.application.errors import InfrastructureError
from vision_mouse.config import MediaPipeConfig
from vision_mouse.domain.vision import Landmark, ProcessedLandmarkFrame


class LandmarkProviderError(InfrastructureError):
    pass


class MediaPipeLandmarkProvider:
    def __init__(self, config: MediaPipeConfig) -> None:
        self.config = config
        self._cv2 = None
        self._mp = None
        self._landmarker = None
        self.last_metrics: dict[str, float] = {}

    def validate_runtime(self) -> None:
        self._ensure_runtime()

    def detect(self, frame: CapturedFrame) -> ProcessedLandmarkFrame:
        self._ensure_runtime()
        prepare_started_at = perf_counter()
        mp_image = self._to_mp_image(frame)
        prepare_latency_ms = (perf_counter() - prepare_started_at) * 1000

        detect_started_at = perf_counter()
        result = self._landmarker.detect_for_video(mp_image, self._frame_timestamp_ms(frame.timestamp))
        detect_latency_ms = (perf_counter() - detect_started_at) * 1000
        self.last_metrics = {
            "mediapipe_prepare_latency_ms": prepare_latency_ms,
            "mediapipe_detect_latency_ms": detect_latency_ms,
        }

        if not result.hand_landmarks:
            return ProcessedLandmarkFrame.no_hand_detected(
                source_frame_size=frame.frame_size,
                timestamp=frame.timestamp,
            )

        raw_landmarks = result.hand_landmarks[0]
        landmarks = tuple(
            Landmark(id=index, x=landmark.x, y=landmark.y, z=landmark.z)
            for index, landmark in enumerate(raw_landmarks)
        )

        if getattr(result, "handedness", None):
            self.last_metrics["mediapipe_handedness_score"] = float(result.handedness[0][0].score)

        return ProcessedLandmarkFrame(
            timestamp=frame.timestamp,
            hand_detected=True,
            confidence=1.0,
            landmarks=landmarks,
            source_frame_size=frame.frame_size,
        )

    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
        self._landmarker = None

    def _ensure_runtime(self) -> None:
        if self._landmarker is not None and self._cv2 is not None and self._mp is not None:
            return

        try:
            import cv2  # type: ignore
            import mediapipe as mp  # type: ignore
        except ImportError as error:  # pragma: no cover - dependency guard
            raise LandmarkProviderError("mediapipe_or_opencv_not_installed") from error

        self._cv2 = cv2
        self._mp = mp

        try:
            base_options = mp.tasks.BaseOptions(
                model_asset_path=str(self._model_asset_path()),
                delegate=mp.tasks.BaseOptions.Delegate.CPU,
            )
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=self.config.max_num_hands,
                min_hand_detection_confidence=self.config.min_detection_confidence,
                min_hand_presence_confidence=self.config.min_tracking_confidence,
                min_tracking_confidence=self.config.min_tracking_confidence,
            )
            self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        except FileNotFoundError as error:
            raise LandmarkProviderError(f"mediapipe_model_asset_missing:{error}") from error
        except (ValueError, RuntimeError) as error:
            raise LandmarkProviderError(f"mediapipe_task_initialization_failed:{error}") from error

    def _model_asset_path(self) -> Path:
        if self.config.model_asset_path:
            return Path(self.config.model_asset_path)
        return resources.files("vision_mouse").joinpath("resources/models/hand_landmarker.task")

    def _to_mp_image(self, frame: CapturedFrame) -> Any:
        if self._cv2 is None or self._mp is None:
            raise LandmarkProviderError("mediapipe_runtime_not_initialized")

        rgb_frame = self._cv2.cvtColor(frame.image, self._cv2.COLOR_BGR2RGB)
        return self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb_frame)

    @staticmethod
    def _frame_timestamp_ms(timestamp: datetime) -> int:
        return int(timestamp.timestamp() * 1000)
