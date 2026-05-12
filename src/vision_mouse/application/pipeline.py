from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Callable, Optional

from vision_mouse.application.contracts import CapturedFrame
from vision_mouse.application.errors import InfrastructureError
from vision_mouse.application.ports import (
    FrameSourcePort,
    IntentDispatchingPort,
    LandmarkProviderPort,
    PipelineLifecyclePort,
    TelemetryPort,
)
from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind
from vision_mouse.domain.vision import utc_now
from vision_mouse.filters.temporal import ConfidenceGate, ExponentialCursorSmoother
from vision_mouse.gestures.engine import GestureEngine
from vision_mouse.mapping.cursor_mapper import CursorMapper
from vision_mouse.mapping.pointer_assist import PointerAssistFilter


@dataclass(frozen=True)
class PipelinePorts:
    frame_source: FrameSourcePort
    landmark_provider: LandmarkProviderPort
    intent_dispatcher: IntentDispatchingPort
    telemetry: TelemetryPort
    health_callback: Optional[Callable[[bool, Optional[str]], None]] = None


@dataclass(frozen=True)
class PipelineProcessors:
    confidence_gate: ConfidenceGate
    cursor_mapper: CursorMapper
    cursor_smoother: ExponentialCursorSmoother
    pointer_assist: PointerAssistFilter
    gesture_engine: GestureEngine


class VisionMousePipeline(PipelineLifecyclePort):
    def __init__(self, ports: PipelinePorts, processors: PipelineProcessors) -> None:
        self.ports = ports
        self.processors = processors
        self.running = False
        self._capture_thread: threading.Thread | None = None
        self._frame_condition = threading.Condition()
        self._latest_frame: CapturedFrame | None = None
        self._capture_error: Exception | None = None
        self._captured_frames = 0
        self._processed_frames = 0
        self._dropped_frames = 0
        self._last_capture_timestamp: datetime | None = None
        self._last_processed_timestamp: datetime | None = None
        self._last_drop_sample: tuple[int, int] = (0, 0)

    def start(self) -> None:
        self.ports.frame_source.open()
        self.running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name="vision-mouse-capture",
            daemon=True,
        )
        self._capture_thread.start()
        self.ports.telemetry.log_event("info", "capture_session_opened")
        self._report_health(True)

    def process_next_frame(self) -> None:
        if not self.running:
            raise RuntimeError("pipeline_not_started")

        started_at = perf_counter()
        try:
            captured_frame = self._next_frame(timeout_s=0.1)
            if captured_frame is None:
                return

            self._record_capture_step_metrics(captured_frame)
            processed_frame = self._detect_landmarks(captured_frame)
            intents = self._build_intents(processed_frame)
            dispatch_latency_ms = self._dispatch_intents(intents)

            total_latency_ms = (perf_counter() - started_at) * 1000
            frame_age_at_dispatch_ms = (utc_now() - captured_frame.timestamp).total_seconds() * 1000
            self._processed_frames += 1

            self.ports.telemetry.record_metric("dispatch_latency_ms", dispatch_latency_ms)
            self.ports.telemetry.record_metric("frame_processing_latency_ms", total_latency_ms)
            self.ports.telemetry.record_metric("frame_age_at_dispatch_ms", frame_age_at_dispatch_ms)
            self._record_inference_fps(processed_frame.timestamp)
            self._record_drop_metrics()
            self._report_health(True)
        except (InfrastructureError, ValueError) as error:
            self._handle_processing_error(error)

    def run_forever(self) -> None:
        while self.running:
            self.process_next_frame()

    def stop(self) -> None:
        self.running = False
        with self._frame_condition:
            self._frame_condition.notify_all()

        if self._capture_thread is not None:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None

        self.ports.frame_source.close()
        self.ports.landmark_provider.close()
        self.ports.intent_dispatcher.release_active_inputs()
        self.processors.cursor_smoother.reset()
        self.processors.pointer_assist.reset()
        with self._frame_condition:
            self._latest_frame = None
            self._capture_error = None
        self.ports.telemetry.log_event("info", "pipeline_stopped")

    def _capture_loop(self) -> None:
        while self.running:
            try:
                frame = self.ports.frame_source.read_frame()
            except InfrastructureError as error:
                with self._frame_condition:
                    self._capture_error = error
                    self._frame_condition.notify_all()
                return

            with self._frame_condition:
                self._captured_frames += 1
                if self._latest_frame is not None:
                    self._dropped_frames += 1
                self._latest_frame = frame
                self._frame_condition.notify_all()

            self._record_capture_fps(frame)

    def _next_frame(self, timeout_s: float) -> CapturedFrame | None:
        with self._frame_condition:
            while self.running and self._latest_frame is None and self._capture_error is None:
                self._frame_condition.wait(timeout=timeout_s)
                if self._latest_frame is None and self._capture_error is None:
                    return None

            if self._capture_error is not None:
                error = self._capture_error
                self._capture_error = None
                if isinstance(error, InfrastructureError):
                    raise error
                raise InfrastructureError(str(error))

            frame = self._latest_frame
            self._latest_frame = None
            return frame

    def _record_capture_step_metrics(self, captured_frame: CapturedFrame) -> None:
        self.ports.telemetry.record_metric("capture_read_latency_ms", captured_frame.capture_latency_ms)
        self.ports.telemetry.record_metric("frame_normalize_latency_ms", captured_frame.normalize_latency_ms)

    def _detect_landmarks(self, captured_frame: CapturedFrame):
        detect_started_at = perf_counter()
        processed_frame = self.ports.landmark_provider.detect(captured_frame)
        detect_total_ms = (perf_counter() - detect_started_at) * 1000
        self.ports.telemetry.record_metric("landmark_detect_total_latency_ms", detect_total_ms)
        for metric_name, metric_value in self.ports.landmark_provider.last_metrics.items():
            self.ports.telemetry.record_metric(metric_name, metric_value)
        self.ports.telemetry.record_metric("hand_detection_confidence", processed_frame.confidence)
        return processed_frame

    def _build_intents(self, processed_frame):
        map_latency_ms = 0.0
        smooth_latency_ms = 0.0
        gesture_latency_ms = 0.0

        intents: list[GestureIntent] = []
        is_operational = self.processors.confidence_gate.is_operational(
            processed_frame.hand_detected,
            processed_frame.confidence,
        )

        cursor_sample = None
        if is_operational and processed_frame.hand_detected:
            map_started_at = perf_counter()
            raw_sample = self.processors.cursor_mapper.map_to_screen(processed_frame)
            map_latency_ms = (perf_counter() - map_started_at) * 1000

            smooth_started_at = perf_counter()
            cursor_sample = self.processors.pointer_assist.apply(
                self.processors.cursor_smoother.smooth(raw_sample)
            )
            smooth_latency_ms = (perf_counter() - smooth_started_at) * 1000
        elif not is_operational:
            self.processors.cursor_smoother.reset()
            self.processors.pointer_assist.reset()

        gesture_started_at = perf_counter()
        gesture_intents, cursor_sample = self.processors.gesture_engine.classify(
            processed_frame,
            cursor_sample,
            pointer_exclusive=self.ports.intent_dispatcher.pointer_exclusive_state,
        )
        gesture_latency_ms = (perf_counter() - gesture_started_at) * 1000

        if cursor_sample is not None:
            intents.append(
                GestureIntent(
                    timestamp=processed_frame.timestamp,
                    intent=GestureIntentKind.MOVE_CURSOR,
                    confidence=processed_frame.confidence,
                    source_gesture="stable_index_tracking",
                    requires_exclusive_pointer_state=False,
                    cursor_sample=cursor_sample,
                )
            )
        intents.extend(gesture_intents)

        self.ports.telemetry.record_metric("cursor_map_latency_ms", map_latency_ms)
        self.ports.telemetry.record_metric("cursor_smooth_latency_ms", smooth_latency_ms)
        self.ports.telemetry.record_metric("gesture_classify_latency_ms", gesture_latency_ms)
        return intents

    def _dispatch_intents(self, intents: list[GestureIntent]) -> float:
        dispatch_started_at = perf_counter()
        self.ports.intent_dispatcher.dispatch_many(intents)
        return (perf_counter() - dispatch_started_at) * 1000

    def _handle_processing_error(self, error: Exception) -> None:
        self.ports.telemetry.log_event("warning", "pipeline_degraded", {"reason": str(error)})
        self.ports.intent_dispatcher.release_active_inputs()
        self._report_health(False, str(error))

    def _record_capture_fps(self, frame: CapturedFrame) -> None:
        if self._last_capture_timestamp is not None:
            elapsed_s = (frame.timestamp - self._last_capture_timestamp).total_seconds()
            if elapsed_s > 0:
                self.ports.telemetry.record_metric("capture_fps", 1.0 / elapsed_s)
        self._last_capture_timestamp = frame.timestamp

    def _record_inference_fps(self, timestamp: datetime) -> None:
        if self._last_processed_timestamp is not None:
            elapsed_s = (timestamp - self._last_processed_timestamp).total_seconds()
            if elapsed_s > 0:
                self.ports.telemetry.record_metric("inference_fps", 1.0 / elapsed_s)
        self._last_processed_timestamp = timestamp

    def _record_drop_metrics(self) -> None:
        previous_captured, previous_dropped = self._last_drop_sample
        captured_delta = self._captured_frames - previous_captured
        dropped_delta = self._dropped_frames - previous_dropped
        if captured_delta > 0:
            drop_rate = dropped_delta / captured_delta
            self.ports.telemetry.record_metric("capture_frame_drop_rate", drop_rate)
        self._last_drop_sample = (self._captured_frames, self._dropped_frames)

    def _report_health(self, is_healthy: bool, reason: Optional[str] = None) -> None:
        if self.ports.health_callback is not None:
            self.ports.health_callback(is_healthy, reason)
