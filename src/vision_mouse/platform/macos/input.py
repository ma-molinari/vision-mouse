from __future__ import annotations

from enum import Enum
from typing import Any

from vision_mouse.application.errors import InfrastructureError
from vision_mouse.application.ports import PointerOutputPort
from vision_mouse.domain.vision import CursorSample, ScreenPoint


class PointerButton(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class PlatformInputError(InfrastructureError):
    pass


class MacOSInputAdapter(PointerOutputPort):
    def __init__(self) -> None:
        self._mouse = self._build_mouse_controller()
        self._drag_active = False
        self._last_pointer_position: tuple[int, int] | None = None

    @property
    def pointer_exclusive_state(self) -> bool:
        return self._drag_active

    @property
    def drag_active(self) -> bool:
        return self._drag_active

    @drag_active.setter
    def drag_active(self, active: bool) -> None:
        self._drag_active = active

    def move_pointer(self, screen_point: ScreenPoint) -> None:
        target = (screen_point.x, screen_point.y)
        if self._last_pointer_position == target:
            return

        self._mouse.position = target
        self._last_pointer_position = target

    def click_primary(self) -> None:
        self.click(PointerButton.PRIMARY)

    def click_secondary(self) -> None:
        self.click(PointerButton.SECONDARY)

    def click(self, button: PointerButton) -> None:
        native_button = self._button(button)
        self._mouse.click(native_button, 1)

    def scroll_vertical(self, amount: int) -> None:
        self._mouse.scroll(0, amount)

    def begin_drag(self, cursor_sample: CursorSample | None) -> None:
        if cursor_sample is not None:
            self.move_pointer(cursor_sample.screen_position)
        if not self._drag_active:
            self._mouse.press(self._button(PointerButton.PRIMARY))
            self._drag_active = True

    def update_drag(self, cursor_sample: CursorSample | None) -> None:
        if cursor_sample is not None:
            self.move_pointer(cursor_sample.screen_position)

    def end_drag(self) -> None:
        if self._drag_active:
            self._mouse.release(self._button(PointerButton.PRIMARY))
            self._drag_active = False

    def release_active_inputs(self) -> None:
        self.end_drag()

    @staticmethod
    def _build_mouse_controller() -> Any:
        try:
            from pynput.mouse import Controller  # type: ignore
        except ImportError as error:  # pragma: no cover - dependency guard
            raise PlatformInputError("pynput_not_installed") from error
        return Controller()

    @staticmethod
    def _button(button: PointerButton) -> Any:
        try:
            from pynput.mouse import Button  # type: ignore
        except ImportError as error:  # pragma: no cover - dependency guard
            raise PlatformInputError("pynput_not_installed") from error

        return Button.left if button is PointerButton.PRIMARY else Button.right
