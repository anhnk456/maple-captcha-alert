import ctypes
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from ctypes import wintypes
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import numpy as np
from mss.exception import ScreenShotError

from game_window import WindowLookupError, find_game_region
from main import Match, build_parser, monitor


class GameWindowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.titles = {101: "MapleStory N"}
        self.hidden: set[int] = set()
        self.minimized: set[int] = set()
        self.origin = (-1000, 25)
        self.size = (1235, 740)
        self.user32 = MagicMock()
        self.user32.EnumWindows.side_effect = self.enumerate_windows
        self.user32.IsWindowVisible.side_effect = lambda handle: handle not in self.hidden
        self.user32.IsIconic.side_effect = lambda handle: handle in self.minimized
        self.user32.GetForegroundWindow.return_value = 101
        self.user32.GetWindowTextLengthW.side_effect = lambda handle: len(self.titles[handle])
        self.user32.GetWindowTextW.side_effect = self.write_title
        self.user32.GetClientRect.side_effect = self.write_rectangle
        self.user32.ClientToScreen.side_effect = self.write_origin
        patcher = patch("game_window.ctypes.WinDLL", return_value=self.user32)
        patcher.start()
        self.addCleanup(patcher.stop)

    def enumerate_windows(self, callback, parameter) -> bool:
        for handle in self.titles:
            callback(handle, parameter)
        return True

    def write_title(self, handle, buffer, length) -> int:
        buffer.value = self.titles[handle]
        return len(buffer.value)

    def write_rectangle(self, handle, pointer) -> bool:
        rectangle = ctypes.cast(pointer, ctypes.POINTER(wintypes.RECT)).contents
        rectangle.left = rectangle.top = 0
        rectangle.right, rectangle.bottom = self.size
        return True

    def write_origin(self, handle, pointer) -> bool:
        origin = ctypes.cast(pointer, ctypes.POINTER(wintypes.POINT)).contents
        origin.x, origin.y = self.origin
        return True

    def test_finds_client_area_and_tracks_window_movement(self) -> None:
        self.assertEqual(
            find_game_region("MapleStory"),
            {"left": -1000, "top": 25, "width": 1235, "height": 740},
        )
        self.origin = (200, 100)
        self.size = (1280, 720)
        self.assertEqual(
            find_game_region("maplestory n"),
            {"left": 200, "top": 100, "width": 1280, "height": 720},
        )

    def test_ignores_browser_titles_hidden_and_minimized_windows(self) -> None:
        self.titles = {101: "MapleStory guide - Google Chrome"}
        self.assertIsNone(find_game_region("MapleStory"))
        self.titles[101] = "MapleStory N"
        self.hidden.add(101)
        self.assertIsNone(find_game_region("MapleStory"))
        self.hidden.clear()
        self.minimized.add(101)
        self.assertIsNone(find_game_region("MapleStory"))
        self.minimized.clear()
        self.size = (0, 0)
        self.assertIsNone(find_game_region("MapleStory"))

    def test_rejects_ambiguous_or_empty_titles(self) -> None:
        self.titles[102] = "MapleStory"
        with self.assertRaises(WindowLookupError):
            find_game_region("MapleStory")
        with self.assertRaises(WindowLookupError):
            find_game_region(" ")
        self.assertIsNotNone(find_game_region("MapleStory N"))

    def test_pauses_when_another_application_is_in_front(self) -> None:
        self.user32.GetForegroundWindow.return_value = 202
        self.assertIsNone(find_game_region("MapleStory"))
        self.user32.GetForegroundWindow.return_value = 101
        self.assertIsNotNone(find_game_region("MapleStory"))

    def test_surfaces_windows_api_errors(self) -> None:
        self.user32.EnumWindows.side_effect = None
        self.user32.EnumWindows.return_value = False
        with self.assertRaises(OSError):
            find_game_region("MapleStory")
        self.user32.EnumWindows.side_effect = self.enumerate_windows
        self.user32.GetClientRect.side_effect = None
        self.user32.GetClientRect.return_value = False
        with self.assertRaises(OSError):
            find_game_region("MapleStory")


class WindowMonitorTest(unittest.TestCase):
    def test_capture_options_are_required_and_mutually_exclusive(self) -> None:
        for arguments in (
            ["monitor"],
            ["monitor", "--region", "0,0,100,100", "--window", "MapleStory"],
        ):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    build_parser().parse_args(arguments)
                self.assertEqual(raised.exception.code, 2)

    def test_pauses_without_capturing_and_resets_confirmation_when_game_disappears(self) -> None:
        first = {"left": 10, "top": 20, "width": 100, "height": 100}
        second = {**first, "left": 200}
        with tempfile.TemporaryDirectory() as directory:
            args = build_parser().parse_args(
                ["monitor", "--window", "MapleStory", "--detections", directory]
            )
            output = io.StringIO()
            with (
                patch("main.CaptchaDetector") as detector,
                patch("main.mss.mss") as screen,
                patch("main.find_game_region", side_effect=[None, first, first, None, second, second]),
                patch("main.time.sleep", side_effect=[None] * 3 + [KeyboardInterrupt]),
                patch("main.time.monotonic", side_effect=[100, 101]),
                patch("main.alert") as sound,
                redirect_stdout(output),
            ):
                detector.return_value.detected.return_value = Match(Path("capcha1.png"), 0.9)
                grab = screen.return_value.__enter__.return_value.grab
                grab.return_value = np.zeros((100, 100, 4), dtype=np.uint8)
                self.assertEqual(monitor(args), 0)
            self.assertEqual(grab.call_args_list, [call(first), call(second)])
            self.assertEqual(output.getvalue().count("[TAM DUNG]"), 2)
            self.assertEqual(output.getvalue().count("[TIEP TUC]"), 2)
            sound.assert_not_called()

    def test_retries_capture_errors_without_false_detection(self) -> None:
        region = {"left": 0, "top": 0, "width": 100, "height": 100}
        with tempfile.TemporaryDirectory() as directory:
            args = build_parser().parse_args(
                ["monitor", "--window", "MapleStory", "--detections", directory]
            )
            output = io.StringIO()
            with (
                patch("main.CaptchaDetector") as detector,
                patch("main.mss.mss") as screen,
                patch("main.find_game_region", return_value=region),
                patch("main.time.sleep", side_effect=[None, KeyboardInterrupt]),
                patch("main.alert") as sound,
                redirect_stdout(output),
            ):
                grab = screen.return_value.__enter__.return_value.grab
                grab.side_effect = [
                    ScreenShotError("capture failed"),
                    np.zeros((100, 100, 4), dtype=np.uint8),
                ]
                self.assertEqual(monitor(args), 0)
            detector.return_value.detected.assert_called_once()
            sound.assert_not_called()
            self.assertIn("[LOI CHUP]", output.getvalue())

    def test_discards_frame_if_game_loses_focus_or_moves_during_capture(self) -> None:
        region = {"left": 0, "top": 0, "width": 100, "height": 100}
        for after_capture in (None, {**region, "left": 200}):
            with self.subTest(after_capture=after_capture), tempfile.TemporaryDirectory() as directory:
                args = build_parser().parse_args(
                    ["monitor", "--window", "MapleStory", "--detections", directory]
                )
                with (
                    patch("main.CaptchaDetector") as detector,
                    patch("main.mss.mss") as screen,
                    patch("main.find_game_region", side_effect=[region, after_capture]),
                    patch("main.time.sleep", side_effect=KeyboardInterrupt),
                    patch("main.alert") as sound,
                    patch("main.cv2.imwrite") as save,
                    redirect_stdout(io.StringIO()),
                ):
                    grab = screen.return_value.__enter__.return_value.grab
                    grab.return_value = np.zeros((100, 100, 4), dtype=np.uint8)
                    self.assertEqual(monitor(args), 0)
                grab.assert_called_once_with(region)
                detector.return_value.detected.assert_not_called()
                sound.assert_not_called()
                save.assert_not_called()

    def test_ambiguous_windows_stop_before_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = build_parser().parse_args(
                ["monitor", "--window", "MapleStory", "--detections", directory]
            )
            output = io.StringIO()
            with (
                patch("main.CaptchaDetector"),
                patch("main.mss.mss") as screen,
                patch("main.find_game_region", side_effect=WindowLookupError("Nhieu cua so")),
                redirect_stdout(output),
            ):
                self.assertEqual(monitor(args), 1)
            screen.return_value.__enter__.return_value.grab.assert_not_called()
            self.assertIn("[LOI CUA SO]", output.getvalue())
