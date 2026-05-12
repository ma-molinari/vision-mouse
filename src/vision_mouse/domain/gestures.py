from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .vision import CursorSample


class GestureIntentKind(str, Enum):
    NO_OP = "no_op"
    MOVE_CURSOR = "move_cursor"
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    BEGIN_DRAG = "begin_drag"
    UPDATE_DRAG = "update_drag"
    END_DRAG = "end_drag"
    SCROLL = "scroll"
    WORKSPACE_NAVIGATION = "workspace_nav"
    MACRO = "macro"


class WorkspaceDirection(str, Enum):
    LEFT = "left"
    RIGHT = "right"


class MacroAction(str, Enum):
    APP_SWITCHER = "app_switcher"


@dataclass(frozen=True)
class GestureIntent:
    timestamp: datetime
    intent: GestureIntentKind
    confidence: float
    source_gesture: str
    requires_exclusive_pointer_state: bool
    cursor_sample: Optional[CursorSample] = None
    scroll_delta: Optional[int] = None
    workspace_direction: Optional[WorkspaceDirection] = None
    macro_action: Optional[MacroAction] = None
