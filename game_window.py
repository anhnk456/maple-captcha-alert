from __future__ import annotations

import ctypes
from ctypes import wintypes


class WindowLookupError(RuntimeError):
    pass


def find_game_region(title: str) -> dict[str, int] | None:
    if not title.strip():
        raise WindowLookupError("Ten cua so khong duoc de trong")
    normalized_title = title.strip().casefold()
    titles = (
        {"maplestory", "maplestory n", "maplestoryn"}
        if normalized_title == "maplestory"
        else {normalized_title}
    )

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL

    matches: list[int] = []

    @callback_type
    def collect_window(handle: int, _parameter: int) -> bool:
        if not user32.IsWindowVisible(handle) or user32.IsIconic(handle):
            return True
        length = user32.GetWindowTextLengthW(handle)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buffer, length + 1)
        if buffer.value.strip().casefold() in titles:
            matches.append(handle)
        return True

    if not user32.EnumWindows(collect_window, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    if len(matches) > 1:
        raise WindowLookupError(
            f"Co nhieu cua so khop '{title}'; dong cua so trung ten "
            "hoac dung --window voi tieu de cu the hon"
        )
    if not matches:
        return None

    handle = matches[0]
    if user32.GetForegroundWindow() != handle:
        return None
    rectangle = wintypes.RECT()
    origin = wintypes.POINT()
    if not user32.GetClientRect(handle, ctypes.byref(rectangle)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not user32.ClientToScreen(handle, ctypes.byref(origin)):
        raise ctypes.WinError(ctypes.get_last_error())
    width = rectangle.right - rectangle.left
    height = rectangle.bottom - rectangle.top
    if width <= 0 or height <= 0 or user32.IsIconic(handle):
        return None
    return {"left": origin.x, "top": origin.y, "width": width, "height": height}
