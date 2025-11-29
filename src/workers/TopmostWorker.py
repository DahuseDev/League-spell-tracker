from PySide6.QtCore import QThread, Signal
import pygetwindow as gw

class TopmostWorker(QThread):
    """Background thread that checks game/window state and emits booleans."""
    status = Signal(bool)  # focused
    interval = 200
    TARGET_WINDOWS = ["League of Legends", "League of Legends (TM) Client"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        while self._running:
            # print("[TOPMOST WORKER] Checking game/window state…")
            try:
                focused = self.is_league_active_window()
            except Exception:
                focused = False
            try:
                self.status.emit(focused)
            except Exception:
                pass
            self.msleep(self.interval)

    def stop(self):
        self._running = False

    def is_league_active_window(self):
        try:
            active = gw.getActiveWindow()
            if not active:
                return False
            return any(title in active.title for title in TopmostWorker.TARGET_WINDOWS)
        except:
            return False