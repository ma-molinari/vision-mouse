from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING

from vision_mouse.config import AppConfig
from vision_mouse.platform.macos.input import PlatformInputError
from vision_mouse.vision.mediapipe_provider import LandmarkProviderError

if TYPE_CHECKING:
    from vision_mouse.app.bootstrap import AppBootstrapCoordinator


def load_app_config(config: AppConfig | None = None) -> AppConfig:
    from vision_mouse.calibration.profile import CalibrationProfileStore

    resolved = config or AppConfig()
    return CalibrationProfileStore().apply(resolved)


def build_app(config: AppConfig | None = None) -> AppBootstrapCoordinator:
    from vision_mouse.app.composition import build_app as compose_application

    return compose_application(load_app_config(config))


def _startup_error_message(error: PlatformInputError) -> str:
    if str(error) == "pynput_not_installed":
        return (
            "Missing runtime dependency 'pynput' for interpreter "
            f"{sys.executable}. Run `make install` or `make dev-install`, "
            "then rerun `make run`."
        )
    return f"Application startup failed: {error}"


def _landmark_provider_error_message(error: LandmarkProviderError) -> str:
    reason = str(error)
    if reason == "mediapipe_or_opencv_not_installed":
        return (
            "Missing runtime dependency 'mediapipe' or 'opencv-python' for interpreter "
            f"{sys.executable}. Run `make install` or `make dev-install`, "
            "then rerun `make run`."
        )
    if reason.startswith("mediapipe_model_asset_missing:"):
        return (
            "The MediaPipe hand-landmarker model asset is missing. Reinstall the project "
            "with `make install`, or set `MediaPipeConfig.model_asset_path` to a valid "
            "hand_landmarker.task file."
        )
    if reason.startswith("mediapipe_task_initialization_failed:"):
        detail = reason.split(":", 1)[1] or "unknown"
        return (
            "MediaPipe Hand Landmarker failed to initialize for interpreter "
            f"{sys.executable}: {detail}"
        )
    return f"Application startup failed: {error}"


def run_calibration(config: AppConfig | None = None) -> None:
    from vision_mouse.calibration.session import GuidedCalibrationSession

    resolved = config or AppConfig()
    GuidedCalibrationSession(resolved).run()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vision-mouse")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("run")
    subcommands.add_parser("calibrate")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv if argv is not None else [])
    if args.command == "calibrate":
        run_calibration()
        return

    try:
        coordinator = build_app()
    except PlatformInputError as error:
        raise SystemExit(_startup_error_message(error)) from error
    except LandmarkProviderError as error:
        raise SystemExit(_landmark_provider_error_message(error)) from error
    coordinator.start(prompt_for_accessibility=True)

    if not coordinator.get_operational_state().can_emit_input:
        return

    pipeline = coordinator.pipeline
    if pipeline is None:
        return

    try:
        pipeline.run_forever()
    except KeyboardInterrupt:
        coordinator.stop()


if __name__ == "__main__":
    main(sys.argv[1:])
