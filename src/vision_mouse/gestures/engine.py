from __future__ import annotations

from typing import Optional

from vision_mouse.config import GestureConfig, MacroConfig
from vision_mouse.domain.gestures import GestureIntent
from vision_mouse.domain.vision import CursorSample, ProcessedLandmarkFrame

from .clicks import ClickGestureRecognizer
from .drag import DragGestureRecognizer
from .macros import MacroGestureRecognizer
from .navigation import WorkspaceGestureRecognizer
from .scroll import ScrollGestureRecognizer


class GestureEngine:
    def __init__(self, config: GestureConfig, macros: MacroConfig | None = None) -> None:
        self.clicks = ClickGestureRecognizer(config)
        self.drag = DragGestureRecognizer(config)
        self.scroll = ScrollGestureRecognizer(config)
        self.navigation = WorkspaceGestureRecognizer(config)
        self.macros = MacroGestureRecognizer(config, macros or MacroConfig())

    def classify(
        self,
        frame: ProcessedLandmarkFrame,
        cursor_sample: Optional[CursorSample],
        *,
        pointer_exclusive: bool,
    ) -> tuple[list[GestureIntent], Optional[CursorSample]]:
        intents: list[GestureIntent] = []
        stabilized_cursor_sample = cursor_sample

        drag_intents = self.drag.recognize(frame, stabilized_cursor_sample)
        intents.extend(drag_intents)
        drag_active = self.drag.drag_active

        if drag_active:
            self.clicks.release_cursor_lock()

        scroll_intents = self.scroll.recognize(
            frame,
            pointer_exclusive=pointer_exclusive or self.navigation.swipe_lock_active,
            drag_active=drag_active,
        )
        intents.extend(scroll_intents)

        click_intents, stabilized_cursor_sample = self.clicks.recognize(
            frame,
            cursor_sample=cursor_sample,
            drag_active=drag_active,
            suppress_right_click=self.scroll.right_click_blocked,
        )

        intents.extend(click_intents)
        intents.extend(
            self.navigation.recognize(
                frame,
                pointer_exclusive=(
                    pointer_exclusive
                    or self.drag.drag_active
                    or self.scroll.pinch_scroll_active
                    or self.scroll.continuous_scroll_active
                ),
            )
        )
        intents.extend(
            self.macros.recognize(
                frame,
                pointer_exclusive=pointer_exclusive or self.drag.drag_active or self.scroll.pinch_scroll_active,
            )
        )
        return intents, stabilized_cursor_sample
