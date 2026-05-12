from __future__ import annotations

import unittest
from unittest.mock import patch

from vision_mouse.main import _landmark_provider_error_message, _startup_error_message, main
from vision_mouse.platform.macos.input import PlatformInputError
from vision_mouse.vision.mediapipe_provider import LandmarkProviderError


class MainTests(unittest.TestCase):
    def test_startup_error_message_guides_dependency_install(self) -> None:
        message = _startup_error_message(PlatformInputError("pynput_not_installed"))

        self.assertIn("pynput", message)
        self.assertIn("make install", message)
        self.assertIn("make dev-install", message)
        self.assertIn("make run", message)

    def test_main_exits_cleanly_when_pynput_is_missing(self) -> None:
        with patch("vision_mouse.main.build_app", side_effect=PlatformInputError("pynput_not_installed")):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertIn("pynput", str(context.exception))

    def test_landmark_provider_error_message_guides_mediapipe_compatibility(self) -> None:
        message = _landmark_provider_error_message(
            LandmarkProviderError("mediapipe_task_initialization_failed:missing model")
        )

        self.assertIn("MediaPipe", message)
        self.assertIn("missing model", message)
        self.assertIn("Hand Landmarker", message)

    def test_main_exits_cleanly_when_mediapipe_runtime_is_incompatible(self) -> None:
        with patch(
            "vision_mouse.main.build_app",
            side_effect=LandmarkProviderError("mediapipe_task_initialization_failed:missing model"),
        ):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertIn("Hand Landmarker", str(context.exception))

    def test_main_routes_to_calibration_command(self) -> None:
        with patch("vision_mouse.main.run_calibration") as run_calibration:
            main(["calibrate"])

        run_calibration.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
