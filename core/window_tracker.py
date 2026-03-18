"""Track the foreground window so we can paste text back into it."""

import ctypes
import ctypes.wintypes
import os

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class WindowTracker:
    """Tracks which window was active before our app got focus."""

    def __init__(self):
        self._own_pid = os.getpid()
        self._own_hwnds: set[int] = set()
        self.last_external_hwnd: int = 0
        self._recording_hwnd: int = 0

    def add_own_hwnd(self, hwnd: int):
        """Register one of our own window handles to ignore."""
        if hwnd:
            self._own_hwnds.add(hwnd)

    def set_own_hwnd(self, hwnd: int):
        """Compatibility — adds to the set."""
        self.add_own_hwnd(hwnd)

    def _is_own_window(self, hwnd: int) -> bool:
        """Check if hwnd belongs to our process."""
        if hwnd in self._own_hwnds:
            return True
        # Also check by PID
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == self._own_pid

    def poll(self):
        """Poll foreground window. Call every ~200ms."""
        hwnd = user32.GetForegroundWindow()
        if hwnd and not self._is_own_window(hwnd):
            self.last_external_hwnd = hwnd

    def snapshot(self):
        """Save current external HWND as recording target."""
        self._recording_hwnd = self.last_external_hwnd

    def get_target_window(self) -> int:
        return self._recording_hwnd or self.last_external_hwnd

    def activate_target(self) -> bool:
        """Bring target window to foreground."""
        hwnd = self.get_target_window()
        if not hwnd or not user32.IsWindow(hwnd):
            return False

        foreground = user32.GetForegroundWindow()
        if foreground == hwnd:
            return True

        current_thread = kernel32.GetCurrentThreadId()
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)

        if current_thread != target_thread:
            user32.AttachThreadInput(current_thread, target_thread, True)

        try:
            user32.ShowWindow(hwnd, 5)  # SW_SHOW
            user32.SetForegroundWindow(hwnd)
        finally:
            if current_thread != target_thread:
                user32.AttachThreadInput(current_thread, target_thread, False)

        # Give window time to activate
        import time
        time.sleep(0.05)

        return user32.GetForegroundWindow() == hwnd

    def target_changed(self) -> bool:
        """Check if foreground window changed since snapshot."""
        if not self._recording_hwnd:
            return False
        current = user32.GetForegroundWindow()
        return (not self._is_own_window(current)
                and current != self._recording_hwnd)
