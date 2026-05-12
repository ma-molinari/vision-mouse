from __future__ import annotations

import math
from typing import Optional

from vision_mouse.config import GestureConfig
from vision_mouse.domain.vision import Landmark, ProcessedLandmarkFrame


def distance_between(
    frame: ProcessedLandmarkFrame,
    first_id: int,
    second_id: int,
) -> Optional[float]:
    first = frame.landmark(first_id)
    second = frame.landmark(second_id)
    if first is None or second is None:
        return None

    return math.sqrt(
        (first.x - second.x) ** 2
        + (first.y - second.y) ** 2
        + (first.z - second.z) ** 2
    )


def landmark_y(frame: ProcessedLandmarkFrame, landmark_id: int) -> Optional[float]:
    landmark = frame.landmark(landmark_id)
    return None if landmark is None else landmark.y


def landmark_x(frame: ProcessedLandmarkFrame, landmark_id: int) -> Optional[float]:
    landmark = frame.landmark(landmark_id)
    return None if landmark is None else landmark.x


def is_two_finger_gesture(frame: ProcessedLandmarkFrame, config: GestureConfig) -> bool:
    return _matches_upright_finger_pose(
        frame,
        config,
        upright_finger_tips=(8, 12),
        folded_finger_tips=(16, 20),
    )


def is_open_hand_gesture(frame: ProcessedLandmarkFrame, config: GestureConfig) -> bool:
    return _matches_upright_finger_pose(
        frame,
        config,
        upright_finger_tips=(8, 12, 16, 20),
        folded_finger_tips=(),
    )


def _matches_upright_finger_pose(
    frame: ProcessedLandmarkFrame,
    config: GestureConfig,
    *,
    upright_finger_tips: tuple[int, ...],
    folded_finger_tips: tuple[int, ...],
) -> bool:
    index_tip = landmark_y(frame, 8)
    index_pip = landmark_y(frame, 6)
    middle_tip = landmark_y(frame, 12)
    middle_pip = landmark_y(frame, 10)
    ring_tip = landmark_y(frame, 16)
    ring_pip = landmark_y(frame, 14)
    pinky_tip = landmark_y(frame, 20)
    pinky_pip = landmark_y(frame, 18)

    if None in (index_tip, index_pip, middle_tip, middle_pip, ring_tip, ring_pip, pinky_tip, pinky_pip):
        return False

    tip_to_pip = {
        8: (index_tip, index_pip),
        12: (middle_tip, middle_pip),
        16: (ring_tip, ring_pip),
        20: (pinky_tip, pinky_pip),
    }

    if any(
        tip_to_pip[finger_tip][0] > (tip_to_pip[finger_tip][1] - config.finger_extension_margin)
        for finger_tip in upright_finger_tips
    ):
        return False

    if any(
        tip_to_pip[finger_tip][0] < (tip_to_pip[finger_tip][1] + config.finger_fold_margin)
        for finger_tip in folded_finger_tips
    ):
        return False

    guard_threshold = min(
        config.left_pinch_threshold,
        config.pinch_scroll_threshold,
    ) + config.open_hand_pinch_guard_margin

    thumb_index_distance = distance_between(frame, 4, 8)
    if thumb_index_distance is not None and thumb_index_distance <= guard_threshold:
        return False

    thumb_middle_distance = distance_between(frame, 4, 12)
    if thumb_middle_distance is not None and thumb_middle_distance <= guard_threshold:
        return False

    return True
