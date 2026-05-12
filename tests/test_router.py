from __future__ import annotations

import unittest
from datetime import datetime, timezone

from vision_mouse.domain.gestures import GestureIntent, GestureIntentKind, MacroAction, WorkspaceDirection
from vision_mouse.domain.runtime import OperationalMode, OperationalState
from vision_mouse.pipeline.router import IntentRouter


class RouterTests(unittest.TestCase):
    def test_router_blocks_when_operational_state_is_not_ready(self) -> None:
        input_adapter = FakeInputAdapter()
        router = IntentRouter(
            pointer_output=input_adapter,
            workspace_navigator=FakeWorkspaceNavigator(),
            macro_executor=FakeMacroExecutor(),
            state_provider=lambda: OperationalState(
                mode=OperationalMode.BLOCKED,
                camera_ready=False,
                accessibility_ready=False,
                pipeline_healthy=False,
            ),
        )

        router.dispatch(
            GestureIntent(
                timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
                intent=GestureIntentKind.LEFT_CLICK,
                confidence=0.9,
                source_gesture="thumb_index_pinch",
                requires_exclusive_pointer_state=True,
            )
        )

        self.assertEqual(input_adapter.release_count, 1)
        self.assertEqual(input_adapter.clicks, [])

    def test_workspace_navigation_is_suppressed_during_drag(self) -> None:
        input_adapter = FakeInputAdapter()
        input_adapter.pointer_exclusive_state = True
        workspace = FakeWorkspaceNavigator()
        router = IntentRouter(
            pointer_output=input_adapter,
            workspace_navigator=workspace,
            macro_executor=FakeMacroExecutor(),
            state_provider=lambda: OperationalState(
                mode=OperationalMode.READY,
                camera_ready=True,
                accessibility_ready=True,
                pipeline_healthy=True,
            ),
        )

        router.dispatch(
            GestureIntent(
                timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
                intent=GestureIntentKind.WORKSPACE_NAVIGATION,
                confidence=0.9,
                source_gesture="workspace_swipe",
                requires_exclusive_pointer_state=False,
                workspace_direction=WorkspaceDirection.LEFT,
            )
        )

        self.assertEqual(workspace.directions, [])

    def test_scroll_intent_is_forwarded_to_input_adapter(self) -> None:
        input_adapter = FakeInputAdapter()
        router = IntentRouter(
            pointer_output=input_adapter,
            workspace_navigator=FakeWorkspaceNavigator(),
            macro_executor=FakeMacroExecutor(),
            state_provider=lambda: OperationalState(
                mode=OperationalMode.READY,
                camera_ready=True,
                accessibility_ready=True,
                pipeline_healthy=True,
            ),
        )

        router.dispatch(
            GestureIntent(
                timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
                intent=GestureIntentKind.SCROLL,
                confidence=0.9,
                source_gesture="two_finger_vertical_scroll",
                requires_exclusive_pointer_state=False,
                scroll_delta=24,
            )
        )

        self.assertEqual(input_adapter.scrolls, [24])

    def test_macro_intent_is_forwarded_to_executor(self) -> None:
        executor = FakeMacroExecutor()
        router = IntentRouter(
            pointer_output=FakeInputAdapter(),
            workspace_navigator=FakeWorkspaceNavigator(),
            macro_executor=executor,
            state_provider=lambda: OperationalState(
                mode=OperationalMode.READY,
                camera_ready=True,
                accessibility_ready=True,
                pipeline_healthy=True,
            ),
        )

        router.dispatch(
            GestureIntent(
                timestamp=datetime(2026, 5, 10, tzinfo=timezone.utc),
                intent=GestureIntentKind.MACRO,
                confidence=0.9,
                source_gesture="peace_sign",
                requires_exclusive_pointer_state=False,
                macro_action=MacroAction.APP_SWITCHER,
            )
        )

        self.assertEqual(executor.actions, [MacroAction.APP_SWITCHER])


class FakeInputAdapter:
    def __init__(self) -> None:
        self.pointer_exclusive_state = False
        self.release_count = 0
        self.clicks: list[str] = []
        self.scrolls: list[int] = []

    def move_pointer(self, screen_point) -> None:
        return None

    def click_primary(self) -> None:
        self.clicks.append("primary")

    def click_secondary(self) -> None:
        self.clicks.append("secondary")

    def scroll_vertical(self, amount: int) -> None:
        self.scrolls.append(amount)

    def begin_drag(self, cursor_sample) -> None:
        self.pointer_exclusive_state = True

    def update_drag(self, cursor_sample) -> None:
        return None

    def end_drag(self) -> None:
        self.pointer_exclusive_state = False

    def release_active_inputs(self) -> None:
        self.release_count += 1
        self.pointer_exclusive_state = False


class FakeWorkspaceNavigator:
    def __init__(self) -> None:
        self.directions: list[WorkspaceDirection] = []

    def trigger_workspace_action(self, direction: WorkspaceDirection) -> None:
        self.directions.append(direction)


class FakeMacroExecutor:
    def __init__(self) -> None:
        self.actions: list[MacroAction] = []

    def execute(self, action: MacroAction) -> None:
        self.actions.append(action)


if __name__ == "__main__":
    unittest.main()
