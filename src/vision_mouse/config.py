from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class CaptureConfig:
    camera_index: int = 0
    target_width: int = 640
    target_height: int = 480
    mirror_input: bool = True


@dataclass(frozen=True)
class MediaPipeConfig:
    max_num_hands: int = 1
    min_detection_confidence: float = 0.65
    min_tracking_confidence: float = 0.55
    model_complexity: int = 0
    model_asset_path: Optional[str] = None


@dataclass(frozen=True)
class OperationalWindow:
    x_min: float = 0.10
    x_max: float = 0.90
    y_min: float = 0.08
    y_max: float = 0.92


@dataclass(frozen=True)
class SmoothingConfig:
    alpha: float = 0.32
    slow_alpha: float = 0.18
    fast_alpha: float = 0.55
    slow_movement_px: float = 10.0
    fast_movement_px: float = 140.0
    min_confidence: float = 0.65
    reacquire_frames: int = 2
    dropout_tolerance_frames: int = 2


@dataclass(frozen=True)
class PointerAssistConfig:
    deadzone_radius_px: int = 10
    deadzone_release_radius_px: int = 20
    edge_margin_px: int = 48
    edge_slowdown: float = 0.58
    corner_margin_px: int = 72
    corner_slowdown: float = 0.38


@dataclass(frozen=True)
class GestureConfig:
    click_confirmation_ms: int = 60
    click_cooldown_ms: int = 220
    pinch_activation_ms: int = 40
    pinch_strong_activation_margin: float = 0.015
    left_pinch_threshold: float = 0.055
    right_pinch_threshold: float = 0.060
    pinch_release_threshold: float = 0.085
    pre_click_lock_threshold: float = 0.075
    pre_click_lock_delta: float = 0.0025
    drag_hold_ms: int = 320
    scroll_history_ms: int = 120
    continuous_scroll_step_px: float = 0.04
    continuous_scroll_units: int = 8
    continuous_scroll_repeat_ms: int = 30
    two_finger_axis_lock_ratio: float = 1.35
    finger_extension_margin: float = 0.08
    finger_fold_margin: float = 0.05
    pinch_scroll_threshold: float = 0.060
    pinch_scroll_step_px: float = 0.03
    pinch_scroll_units: int = 12
    pinch_scroll_repeat_ms: int = 50
    pinch_scroll_activation_delta: float = 0.025
    open_hand_pinch_guard_margin: float = 0.020
    workspace_history_ms: int = 220
    workspace_swipe_delta: float = 0.14
    workspace_cooldown_ms: int = 900
    macro_hold_ms: int = 280
    macro_cooldown_ms: int = 900


@dataclass(frozen=True)
class MacroBindingConfig:
    gesture: str
    action: str


@dataclass(frozen=True)
class MacroConfig:
    bindings: tuple[MacroBindingConfig, ...] = ()


@dataclass(frozen=True)
class AppConfig:
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    mediapipe: MediaPipeConfig = field(default_factory=MediaPipeConfig)
    operational_window: OperationalWindow = field(default_factory=OperationalWindow)
    smoothing: SmoothingConfig = field(default_factory=SmoothingConfig)
    pointer_assist: PointerAssistConfig = field(default_factory=PointerAssistConfig)
    gestures: GestureConfig = field(default_factory=GestureConfig)
    macros: MacroConfig = field(default_factory=MacroConfig)
