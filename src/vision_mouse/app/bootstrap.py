from __future__ import annotations

from vision_mouse.application.operational import OperationalStateController
from vision_mouse.application.ports import InputReleasePort, PipelineLifecyclePort

PipelineLifecycleControlling = PipelineLifecyclePort
SystemInputControlling = InputReleasePort


class AppBootstrapCoordinator(OperationalStateController):
    """Compatibility facade for the operational state controller."""
