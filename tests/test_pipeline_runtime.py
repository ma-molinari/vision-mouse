from __future__ import annotations

import time
import unittest
from datetime import datetime, timedelta, timezone

from vision_mouse.capture.session import CaptureSessionError, CapturedFrame
from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind
from vision_mouse.domain.runtime import OperationalMode, OperationalState
from vision_mouse.domain.vision import FrameSize, Landmark, ProcessedLandmarkFrame
from vision_mouse.filters.temporal import ConfidenceGate, ExponentialCursorSmoother
from vision_mouse.gestures.engine import GestureEngine
from vision_mouse.mapping.cursor_mapper import CursorMapper, StaticScreenSizeProvider
from vision_mouse.mapping.pointer_assist import PointerAssistFilter
from vision_mouse.observability.telemetry import PipelineTelemetry
from vision_mouse.pipeline.runtime import PipelinePorts, PipelineProcessors, VisionMousePipeline
from vision_mouse.config import GestureConfig, OperationalWindow, PointerAssistConfig, SmoothingConfig
from vision_mouse.vision.mediapipe_provider import LandmarkProviderError


class PipelineRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_time = datetime(2026, 5, 10, tzinfo=timezone.utc)

    def test_pipeline_processes_only_latest_frame_when_backlogged(self) -> None:
        frames = [
            make_captured_frame(self.base_time),
            make_captured_frame(self.base_time + timedelta(milliseconds=10)),
            make_captured_frame(self.base_time + timedelta(milliseconds=20)),
        ]
        capture = FakeCaptureSession(frames)
        provider = FakeLandmarkProvider(delay_s=0.0)
        telemetry = PipelineTelemetry(max_records=200)
        pipeline = make_pipeline(capture, provider, telemetry)

        pipeline.start()
        time.sleep(0.03)
        pipeline.process_next_frame()
        pipeline.stop()

        self.assertEqual(provider.detected_timestamps, [frames[-1].timestamp])
        metrics = telemetry.snapshot()["metrics"]
        drop_rates = [metric["value"] for metric in metrics if metric["name"] == "capture_frame_drop_rate"]
        self.assertTrue(drop_rates)
        self.assertGreater(drop_rates[-1], 0.0)

    def test_pipeline_records_stage_metrics(self) -> None:
        frame = make_captured_frame(self.base_time)
        capture = FakeCaptureSession([frame])
        provider = FakeLandmarkProvider()
        telemetry = PipelineTelemetry(max_records=200)
        pipeline = make_pipeline(capture, provider, telemetry)

        pipeline.start()
        time.sleep(0.02)
        pipeline.process_next_frame()
        pipeline.stop()

        metric_names = {metric["name"] for metric in telemetry.snapshot()["metrics"]}
        self.assertTrue(
            {
                "capture_read_latency_ms",
                "frame_normalize_latency_ms",
                "mediapipe_prepare_latency_ms",
                "mediapipe_detect_latency_ms",
                "landmark_detect_total_latency_ms",
                "cursor_map_latency_ms",
                "cursor_smooth_latency_ms",
                "gesture_classify_latency_ms",
                "dispatch_latency_ms",
                "frame_processing_latency_ms",
                "frame_age_at_dispatch_ms",
            }.issubset(metric_names)
        )

    def test_pipeline_reports_health_on_landmark_failure(self) -> None:
        frame = make_captured_frame(self.base_time)
        capture = FakeCaptureSession([frame])
        provider = FakeLandmarkProvider(error=LandmarkProviderError("detect_failed"))
        health_updates: list[tuple[bool, str | None]] = []
        pipeline = make_pipeline(
            capture,
            provider,
            PipelineTelemetry(max_records=100),
            health_callback=lambda healthy, reason: health_updates.append((healthy, reason)),
        )

        pipeline.start()
        time.sleep(0.02)
        pipeline.process_next_frame()
        pipeline.stop()

        self.assertIn((False, "detect_failed"), health_updates)

    def test_pipeline_stop_releases_active_inputs(self) -> None:
        capture = FakeCaptureSession([])
        provider = FakeLandmarkProvider()
        input_adapter = FakeInputAdapter()
        pipeline = make_pipeline(
            capture,
            provider,
            PipelineTelemetry(max_records=50),
            input_adapter=input_adapter,
        )

        pipeline.start()
        pipeline.stop()

        self.assertEqual(input_adapter.release_count, 1)


def make_pipeline(
    capture_session: FakeCaptureSession,
    landmark_provider: FakeLandmarkProvider,
    telemetry: PipelineTelemetry,
    *,
    input_adapter: FakeInputAdapter | None = None,
    health_callback=None,
) -> VisionMousePipeline:
    adapter = input_adapter or FakeInputAdapter()
    router = FakeIntentRouter(adapter)
    return VisionMousePipeline(
        ports=PipelinePorts(
            frame_source=capture_session,
            landmark_provider=landmark_provider,
            intent_dispatcher=router,
            telemetry=telemetry,
            health_callback=health_callback,
        ),
        processors=PipelineProcessors(
            confidence_gate=ConfidenceGate(SmoothingConfig(min_confidence=0.1, reacquire_frames=1)),
            cursor_mapper=CursorMapper(
                screen_provider=StaticScreenSizeProvider(1920, 1080),
                operational_window=OperationalWindow(x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0),
            ),
            cursor_smoother=ExponentialCursorSmoother(
                SmoothingConfig(min_confidence=0.1, reacquire_frames=1)
            ),
            pointer_assist=PointerAssistFilter(PointerAssistConfig(), (1920, 1080)),
            gesture_engine=GestureEngine(GestureConfig()),
        ),
    )


def make_captured_frame(timestamp: datetime) -> CapturedFrame:
    return CapturedFrame(
        timestamp=timestamp,
        image="frame",
        frame_size=FrameSize(width=640, height=480),
        capture_latency_ms=1.0,
        normalize_latency_ms=0.5,
    )


class FakeCaptureSession:
    def __init__(self, frames: list[CapturedFrame]) -> None:
        self.frames = list(frames)
        self.opened = False
        self._index = 0

    def open(self) -> None:
        self.opened = True

    def read_frame(self) -> CapturedFrame:
        while self.opened and self._index >= len(self.frames):
            time.sleep(0.005)

        if not self.opened:
            raise CaptureSessionError("capture_session_not_open")

        frame = self.frames[self._index]
        self._index += 1
        return frame

    def close(self) -> None:
        self.opened = False


class FakeLandmarkProvider:
    def __init__(self, *, delay_s: float = 0.0, error: Exception | None = None) -> None:
        self.delay_s = delay_s
        self.error = error
        self.detected_timestamps: list[datetime] = []
        self.last_metrics = {
            "mediapipe_prepare_latency_ms": 0.2,
            "mediapipe_detect_latency_ms": 0.8,
        }

    def detect(self, frame: CapturedFrame) -> ProcessedLandmarkFrame:
        if self.delay_s:
            time.sleep(self.delay_s)
        if self.error is not None:
            raise self.error

        self.detected_timestamps.append(frame.timestamp)
        return ProcessedLandmarkFrame(
            timestamp=frame.timestamp,
            hand_detected=True,
            confidence=0.95,
            landmarks=(
                Landmark(id=5, x=0.4, y=0.4, z=0.0),
                Landmark(id=8, x=0.5, y=0.5, z=0.0),
            ),
            source_frame_size=frame.frame_size,
        )

    def close(self) -> None:
        return None


class FakeIntentRouter:
    def __init__(self, input_adapter: "FakeInputAdapter") -> None:
        self.input_adapter = input_adapter
        self.intents: list[GestureIntent] = []

    @property
    def pointer_exclusive_state(self) -> bool:
        return self.input_adapter.pointer_exclusive_state

    def dispatch_many(self, intents: list[GestureIntent]) -> None:
        self.intents.extend(intents)
        for intent in intents:
            if intent.intent is GestureIntentKind.MOVE_CURSOR and intent.cursor_sample is not None:
                self.input_adapter.move_pointer(intent.cursor_sample.screen_position)

    def release_active_inputs(self) -> None:
        self.input_adapter.release_active_inputs()


class FakeInputAdapter:
    def __init__(self) -> None:
        self.release_count = 0
        self.moves: list[tuple[int, int]] = []
        self.pointer_exclusive_state = False

    def move_pointer(self, screen_point) -> None:
        self.moves.append((screen_point.x, screen_point.y))

    def release_active_inputs(self) -> None:
        self.release_count += 1
        self.pointer_exclusive_state = False


if __name__ == "__main__":
    unittest.main()
