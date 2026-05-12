from __future__ import annotations

from time import perf_counter
from typing import Any, Optional

from vision_mouse.application.contracts import CapturedFrame
from vision_mouse.application.errors import InfrastructureError
from vision_mouse.config import CaptureConfig
from vision_mouse.domain.vision import FrameSize, utc_now


class CaptureSessionError(InfrastructureError):
    pass


class WebcamSession:
    def __init__(self, config: CaptureConfig) -> None:
        self.config = config
        self._capture: Optional[Any] = None
        self._cv2: Optional[Any] = None

    def open(self) -> None:
        cv2 = self._import_cv2()
        capture = cv2.VideoCapture(self.config.camera_index)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.target_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.target_height)
        if hasattr(cv2, "CAP_PROP_FPS"):
            capture.set(cv2.CAP_PROP_FPS, 60)
        if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not capture.isOpened():
            capture.release()
            raise CaptureSessionError("unable_to_open_camera")

        self._cv2 = cv2
        self._capture = capture

    def read_frame(self) -> CapturedFrame:
        if self._capture is None or self._cv2 is None:
            raise CaptureSessionError("capture_session_not_open")

        capture_started_at = utc_now()
        capture_started_perf = perf_counter()
        ok, frame = self._capture.read()
        capture_latency_ms = (perf_counter() - capture_started_perf) * 1000
        if not ok:
            raise CaptureSessionError("failed_to_read_frame")

        normalized_frame, normalize_latency_ms = self._normalize_frame(frame)
        height, width = normalized_frame.shape[:2]
        return CapturedFrame(
            timestamp=capture_started_at,
            image=normalized_frame,
            frame_size=FrameSize(width=width, height=height),
            capture_latency_ms=capture_latency_ms,
            normalize_latency_ms=normalize_latency_ms,
        )

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self._cv2 = None

    def _normalize_frame(self, frame: Any) -> tuple[Any, float]:
        started_at = perf_counter()
        if self._cv2 is None:
            return frame, (perf_counter() - started_at) * 1000

        if self.config.mirror_input:
            frame = self._cv2.flip(frame, 1)

        current_height, current_width = frame.shape[:2]
        if current_width != self.config.target_width or current_height != self.config.target_height:
            frame = self._cv2.resize(frame, (self.config.target_width, self.config.target_height))

        return frame, (perf_counter() - started_at) * 1000

    @staticmethod
    def _import_cv2() -> Any:
        try:
            import cv2  # type: ignore
        except ImportError as error:  # pragma: no cover - dependency guard
            raise CaptureSessionError("opencv_not_installed") from error
        return cv2
