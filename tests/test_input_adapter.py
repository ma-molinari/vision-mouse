from __future__ import annotations

import unittest
from unittest.mock import patch

from vision_mouse.domain.vision import ScreenPoint
from vision_mouse.platform.macos.input import MacOSInputAdapter


class InputAdapterTests(unittest.TestCase):
    def test_move_pointer_suppresses_redundant_positions(self) -> None:
        fake_mouse = FakeMouse()
        with patch.object(MacOSInputAdapter, "_build_mouse_controller", return_value=fake_mouse):
            adapter = MacOSInputAdapter()

        adapter.move_pointer(ScreenPoint(x=100, y=200))
        adapter.move_pointer(ScreenPoint(x=100, y=200))
        adapter.move_pointer(ScreenPoint(x=120, y=220))

        self.assertEqual(fake_mouse.positions, [(100, 200), (120, 220)])


class FakeMouse:
    def __init__(self) -> None:
        self.positions: list[tuple[int, int]] = []

    @property
    def position(self) -> tuple[int, int] | None:
        if not self.positions:
            return None
        return self.positions[-1]

    @position.setter
    def position(self, value: tuple[int, int]) -> None:
        self.positions.append(value)


if __name__ == "__main__":
    unittest.main()
