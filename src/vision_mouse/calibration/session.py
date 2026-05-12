from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from time import monotonic, sleep
from typing import Iterable, Sequence

from vision_mouse.capture.session import WebcamSession
from vision_mouse.config import AppConfig
from vision_mouse.domain.vision import Landmark, ProcessedLandmarkFrame
from vision_mouse.vision.mediapipe_provider import LandmarkProviderError, MediaPipeLandmarkProvider

from .profile import CalibrationProfileStore


@dataclass(frozen=True)
class CalibrationResult:
    operational_window: dict[str, float]
    smoothing: dict[str, float]
    pointer_assist: dict[str, int | float]
    gestures: dict[str, float]

    def as_profile(self) -> dict[str, object]:
        return asdict(self)


class CalibrationAnalyzer:
    def analyze(
        self,
        movement_frames: Sequence[ProcessedLandmarkFrame],
        steady_frames: Sequence[ProcessedLandmarkFrame],
        pinch_frames: Sequence[ProcessedLandmarkFrame],
    ) -> CalibrationResult:
        movement_landmarks = [self._reference_landmark(frame) for frame in movement_frames]
        steady_landmarks = [self._reference_landmark(frame) for frame in steady_frames]
        pinch_distances = [distance for distance in self._pinch_distances(pinch_frames) if distance is not None]
        movement_deltas = self._movement_deltas(movement_landmarks)

        if len(movement_landmarks) < 5:
            raise ValueError("insufficient_movement_samples")
        if len(steady_landmarks) < 5:
            raise ValueError("insufficient_steady_samples")
        if len(pinch_distances) < 5:
            raise ValueError("insufficient_pinch_samples")

        x_values = [landmark.x for landmark in movement_landmarks]
        y_values = [landmark.y for landmark in movement_landmarks]
        jitter_values = self._center_distances(steady_landmarks)

        closed_distance = self._quantile(pinch_distances, 0.10)
        open_distance = self._quantile(pinch_distances, 0.85)
        pinch_span = max(open_distance - closed_distance, 0.01)
        slow_delta = self._quantile(movement_deltas, 0.35) if movement_deltas else 10.0
        fast_delta = self._quantile(movement_deltas, 0.85) if movement_deltas else 140.0
        deadzone_radius = max(8, min(28, round(self._quantile(jitter_values, 0.90) * 2200)))

        return CalibrationResult(
            operational_window={
                "x_min": max(0.0, self._quantile(x_values, 0.05) - 0.035),
                "x_max": min(1.0, self._quantile(x_values, 0.95) + 0.035),
                "y_min": max(0.0, self._quantile(y_values, 0.05) - 0.035),
                "y_max": min(1.0, self._quantile(y_values, 0.95) + 0.035),
            },
            smoothing={
                "slow_alpha": 0.08,
                "fast_alpha": 0.48,
                "slow_movement_px": max(6.0, round(slow_delta * 1600, 2)),
                "fast_movement_px": max(round(slow_delta * 1600, 2) + 40.0, round(fast_delta * 1800, 2)),
            },
            pointer_assist={
                "deadzone_radius_px": deadzone_radius,
                "deadzone_release_radius_px": max(deadzone_radius + 8, round(deadzone_radius * 1.6)),
                "edge_margin_px": 52,
                "edge_slowdown": 0.55,
                "corner_margin_px": 84,
                "corner_slowdown": 0.34,
            },
            gestures={
                "left_pinch_threshold": round(closed_distance + (pinch_span * 0.28), 4),
                "pinch_release_threshold": round(closed_distance + (pinch_span * 0.78), 4),
                "pre_click_lock_threshold": round(closed_distance + (pinch_span * 0.55), 4),
                "pre_click_lock_delta": 0.0025,
            },
        )

    @staticmethod
    def _reference_landmark(frame: ProcessedLandmarkFrame) -> Landmark:
        stable_point = frame.landmark(5)
        tip_point = frame.landmark(8)
        if stable_point is None and tip_point is None:
            raise ValueError("missing_reference_landmarks")
        if stable_point is None:
            return tip_point  # type: ignore[return-value]
        if tip_point is None:
            return stable_point
        return Landmark(
            id=8,
            x=(tip_point.x * 0.35) + (stable_point.x * 0.65),
            y=(tip_point.y * 0.35) + (stable_point.y * 0.65),
            z=(tip_point.z * 0.35) + (stable_point.z * 0.65),
        )

    @staticmethod
    def _pinch_distances(frames: Iterable[ProcessedLandmarkFrame]) -> list[float | None]:
        distances: list[float | None] = []
        for frame in frames:
            thumb = frame.landmark(4)
            index = frame.landmark(8)
            if thumb is None or index is None:
                distances.append(None)
                continue
            distances.append(
                ((thumb.x - index.x) ** 2 + (thumb.y - index.y) ** 2 + (thumb.z - index.z) ** 2) ** 0.5
            )
        return distances

    @staticmethod
    def _movement_deltas(landmarks: Sequence[Landmark]) -> list[float]:
        deltas: list[float] = []
        for previous, current in zip(landmarks, landmarks[1:]):
            deltas.append(((current.x - previous.x) ** 2 + (current.y - previous.y) ** 2) ** 0.5)
        return deltas

    @staticmethod
    def _center_distances(landmarks: Sequence[Landmark]) -> list[float]:
        center_x = mean(point.x for point in landmarks)
        center_y = mean(point.y for point in landmarks)
        return [((point.x - center_x) ** 2 + (point.y - center_y) ** 2) ** 0.5 for point in landmarks]

    @staticmethod
    def _quantile(values: Sequence[float], quantile: float) -> float:
        ordered = sorted(values)
        if not ordered:
            raise ValueError("empty_values")
        index = min(max(round((len(ordered) - 1) * quantile), 0), len(ordered) - 1)
        return ordered[index]


class GuidedCalibrationSession:
    def __init__(
        self,
        config: AppConfig,
        *,
        store: CalibrationProfileStore | None = None,
    ) -> None:
        self.config = config
        self.store = store or CalibrationProfileStore()
        self.analyzer = CalibrationAnalyzer()

    def run(self) -> None:
        print("Calibracao guiada do Vision Mouse")
        print("Vamos medir alcance, estabilidade e pinça. O processo leva cerca de 30 a 45 segundos.\n")

        session = WebcamSession(self.config.capture)
        provider = MediaPipeLandmarkProvider(self.config.mediapipe)
        provider.validate_runtime()

        try:
            session.open()
            movement_frames = self._capture_phase(
                session,
                provider,
                prompt="Mova a mao confortavelmente ate os extremos por 8 segundos.",
                duration_seconds=8.0,
            )
            steady_frames = self._capture_phase(
                session,
                provider,
                prompt="Agora mantenha a mao o mais parada possivel por 5 segundos.",
                duration_seconds=5.0,
            )
            pinch_frames = self._capture_phase(
                session,
                provider,
                prompt="Faca 3 a 5 pinças naturais com polegar e indicador nos proximos 8 segundos.",
                duration_seconds=8.0,
            )
            result = self.analyzer.analyze(movement_frames, steady_frames, pinch_frames)
            saved_path = self.store.save(result.as_profile())
        except LandmarkProviderError as error:
            raise SystemExit(f"Calibration failed: {error}") from error
        finally:
            session.close()
            provider.close()

        print("\nPerfil salvo com sucesso.")
        print(saved_path)
        print("\nResumo sugerido:")
        print(result.as_profile())

    def _capture_phase(
        self,
        session: WebcamSession,
        provider: MediaPipeLandmarkProvider,
        *,
        prompt: str,
        duration_seconds: float,
    ) -> list[ProcessedLandmarkFrame]:
        input(f"{prompt}\nPressione Enter para iniciar.")
        deadline = monotonic() + duration_seconds
        frames: list[ProcessedLandmarkFrame] = []
        while monotonic() < deadline:
            captured_frame = session.read_frame()
            detected = provider.detect(captured_frame)
            if detected.hand_detected:
                frames.append(detected)
            sleep(0.01)
        return frames
