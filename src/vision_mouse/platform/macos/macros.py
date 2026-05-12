from __future__ import annotations

import subprocess

from vision_mouse.application.errors import InfrastructureError
from vision_mouse.domain.gestures import MacroAction


class MacroExecutionError(InfrastructureError):
    pass


class AppleScriptMacroExecutor:
    def execute(self, action: MacroAction) -> None:
        if action is MacroAction.APP_SWITCHER:
            script = 'tell application "System Events" to key code 48 using command down'
        else:  # pragma: no cover - defensive guard
            raise MacroExecutionError(f"unsupported_macro:{action}")

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode != 0:
            raise MacroExecutionError(result.stderr.strip() or f"macro_failed:{action.value}")
