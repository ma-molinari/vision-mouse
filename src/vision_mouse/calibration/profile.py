from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from vision_mouse.config import AppConfig


class CalibrationProfileStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or self.default_path()

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}

        with self.path.open("r", encoding="utf-8") as profile_file:
            payload = json.load(profile_file)

        return payload if isinstance(payload, dict) else {}

    def save(self, profile: dict[str, Any]) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as profile_file:
            json.dump(profile, profile_file, indent=2, sort_keys=True)
        return self.path

    def apply(self, config: AppConfig) -> AppConfig:
        profile = self.load()
        if not profile:
            return config

        resolved = config
        if isinstance(profile.get("operational_window"), dict):
            resolved = replace(
                resolved,
                operational_window=replace(resolved.operational_window, **profile["operational_window"]),
            )
        if isinstance(profile.get("smoothing"), dict):
            resolved = replace(
                resolved,
                smoothing=replace(resolved.smoothing, **profile["smoothing"]),
            )
        if isinstance(profile.get("pointer_assist"), dict):
            resolved = replace(
                resolved,
                pointer_assist=replace(resolved.pointer_assist, **profile["pointer_assist"]),
            )
        if isinstance(profile.get("gestures"), dict):
            resolved = replace(
                resolved,
                gestures=replace(resolved.gestures, **profile["gestures"]),
            )
        return resolved

    @staticmethod
    def default_path() -> Path:
        override = os.environ.get("VISION_MOUSE_PROFILE_PATH")
        if override:
            return Path(override).expanduser()
        return Path.home() / ".vision_mouse" / "profile.json"
