from __future__ import annotations

import subprocess

from vision_mouse.application.errors import InfrastructureError
from vision_mouse.domain.gestures import WorkspaceDirection


class WorkspaceNavigationError(InfrastructureError):
    pass


class AppleScriptWorkspaceNavigator:
    def trigger_workspace_action(self, direction: WorkspaceDirection) -> None:
        key_code = "123" if direction is WorkspaceDirection.LEFT else "124"
        script = f'tell application "System Events" to key code {key_code} using control down'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode != 0:
            raise WorkspaceNavigationError(result.stderr.strip() or "workspace_navigation_failed")
