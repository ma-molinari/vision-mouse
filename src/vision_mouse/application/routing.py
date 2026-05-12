from __future__ import annotations

from typing import Callable, Iterable

from vision_mouse.application.ports import MacroExecutionPort, PointerOutputPort, WorkspaceNavigationPort
from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind
from vision_mouse.domain.runtime import OperationalState


class IntentRouter:
    def __init__(
        self,
        pointer_output: PointerOutputPort,
        workspace_navigator: WorkspaceNavigationPort,
        macro_executor: MacroExecutionPort,
        state_provider: Callable[[], OperationalState],
    ) -> None:
        self.pointer_output = pointer_output
        self.workspace_navigator = workspace_navigator
        self.macro_executor = macro_executor
        self.state_provider = state_provider

    @property
    def pointer_exclusive_state(self) -> bool:
        return self.pointer_output.pointer_exclusive_state

    def dispatch_many(self, intents: Iterable[GestureIntent]) -> None:
        for intent in intents:
            self.dispatch(intent)

    def release_active_inputs(self) -> None:
        self.pointer_output.release_active_inputs()

    def dispatch(self, intent: GestureIntent) -> None:
        state = self.state_provider()
        if not state.can_emit_input:
            self.release_active_inputs()
            return

        if intent.intent is GestureIntentKind.MOVE_CURSOR and intent.cursor_sample is not None:
            self.pointer_output.move_pointer(intent.cursor_sample.screen_position)
            return

        if intent.intent is GestureIntentKind.LEFT_CLICK:
            self.pointer_output.click_primary()
            return

        if intent.intent is GestureIntentKind.RIGHT_CLICK:
            self.pointer_output.click_secondary()
            return

        if intent.intent is GestureIntentKind.SCROLL and intent.scroll_delta is not None:
            self.pointer_output.scroll_vertical(intent.scroll_delta)
            return

        if intent.intent is GestureIntentKind.BEGIN_DRAG:
            self.pointer_output.begin_drag(intent.cursor_sample)
            return

        if intent.intent is GestureIntentKind.UPDATE_DRAG:
            self.pointer_output.update_drag(intent.cursor_sample)
            return

        if intent.intent is GestureIntentKind.END_DRAG:
            self.pointer_output.end_drag()
            return

        if (
            intent.intent is GestureIntentKind.WORKSPACE_NAVIGATION
            and intent.workspace_direction is not None
            and not self.pointer_output.pointer_exclusive_state
        ):
            self.workspace_navigator.trigger_workspace_action(intent.workspace_direction)
            return

        if intent.intent is GestureIntentKind.MACRO and intent.macro_action is not None:
            self.macro_executor.execute(intent.macro_action)
