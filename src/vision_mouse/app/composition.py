from __future__ import annotations

from vision_mouse.app.bootstrap import AppBootstrapCoordinator
from vision_mouse.application.pipeline import PipelinePorts, PipelineProcessors, VisionMousePipeline
from vision_mouse.application.routing import IntentRouter
from vision_mouse.capture.session import WebcamSession
from vision_mouse.config import AppConfig
from vision_mouse.filters.temporal import ConfidenceGate, ExponentialCursorSmoother
from vision_mouse.gestures.engine import GestureEngine
from vision_mouse.mapping.cursor_mapper import CursorMapper, DefaultScreenSizeProvider
from vision_mouse.mapping.pointer_assist import PointerAssistFilter
from vision_mouse.observability.telemetry import PipelineTelemetry
from vision_mouse.platform.macos.input import MacOSInputAdapter
from vision_mouse.platform.macos.macros import AppleScriptMacroExecutor
from vision_mouse.platform.macos.permissions import MacOSPermissionMonitor
from vision_mouse.platform.macos.workspace import AppleScriptWorkspaceNavigator
from vision_mouse.vision.mediapipe_provider import MediaPipeLandmarkProvider


def build_app(config: AppConfig) -> AppBootstrapCoordinator:
    telemetry = PipelineTelemetry()
    permission_monitor = MacOSPermissionMonitor()
    pointer_output = MacOSInputAdapter()
    workspace_navigator = AppleScriptWorkspaceNavigator()
    macro_executor = AppleScriptMacroExecutor()
    landmark_provider = MediaPipeLandmarkProvider(config.mediapipe)
    landmark_provider.validate_runtime()

    screen_provider = DefaultScreenSizeProvider()
    coordinator = AppBootstrapCoordinator(
        permission_monitor=permission_monitor,
        input_controller=pointer_output,
    )
    router = IntentRouter(
        pointer_output=pointer_output,
        workspace_navigator=workspace_navigator,
        macro_executor=macro_executor,
        state_provider=coordinator.get_operational_state,
    )
    pipeline = VisionMousePipeline(
        ports=PipelinePorts(
            frame_source=WebcamSession(config.capture),
            landmark_provider=landmark_provider,
            intent_dispatcher=router,
            telemetry=telemetry,
            health_callback=coordinator.update_pipeline_health,
        ),
        processors=PipelineProcessors(
            confidence_gate=ConfidenceGate(config.smoothing),
            cursor_mapper=CursorMapper(screen_provider, config.operational_window),
            cursor_smoother=ExponentialCursorSmoother(config.smoothing),
            pointer_assist=PointerAssistFilter(
                config.pointer_assist,
                screen_provider.screen_size(),
            ),
            gesture_engine=GestureEngine(config.gestures, config.macros),
        ),
    )
    coordinator.pipeline = pipeline
    return coordinator
