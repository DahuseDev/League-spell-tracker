from PySide6.QtCore import QThread, Signal
from src.commons import is_in_game

class GameStateWorker(QThread):
    """Background thread that periodically checks if a match is active (is_in_game)."""
    status = Signal(bool)  # in_game
    interval = 2000
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        while self._running:
            try:
                in_game = is_in_game()
            except Exception:
                in_game = False
            try:
                self.status.emit(in_game)
            except Exception:
                pass
            self.msleep(self.interval)

    def stop(self):
        self._running = False