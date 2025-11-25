import sys
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider,
    QToolButton, QFrame, QSizePolicy, QStackedLayout, QMessageBox
)
from PySide6.QtCore import Qt, QPoint, QSize, QRectF
from PySide6.QtGui import QPainter, QColor, QPainterPath
from src.workers.GameStateWorker import GameStateWorker
from src.workers.TopmostWorker import TopmostWorker
from src.workers.LocalSyncWorker import LocalSyncWorker
from .GridWidget import GridWidget
from src.UserData import UserData

# ============================== MAIN OVERLAY ==================================
class OverlayWidget(QWidget):
    BASE_PAD = 8
    BTN_H = 24
    BTN_W = 24
    visible = True
    loaded = False

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.userData = UserData()
        self._drag_pos: Optional[QPoint] = None
        self._locked = False
        self._in_game = False
        self._page = 0
        self._scale = self.userData.get("overlay_scale", 0.70)
        self._default_opacity = self.userData.get("overlay_opacity", 0.40)
        

        root = QVBoxLayout(self)
        root.setContentsMargins(self.BASE_PAD, self.BASE_PAD, self.BASE_PAD, self.BASE_PAD)
        root.setSpacing(6)

        # Top-right buttons
        topbar = QHBoxLayout(); topbar.addStretch(1)
        self.lock_btn = QToolButton(self); self.lock_btn.setText("🔓"); self.lock_btn.setToolTip("Lock/Unlock (Ctrl+L)")
        self.lock_btn.setAutoRaise(True); self.lock_btn.setFixedSize(self.BTN_W, self.BTN_H); self.lock_btn.clicked.connect(self.toggle_lock)
        topbar.addWidget(self.lock_btn)

        self.cog = QToolButton(self); self.cog.setText("⚙"); self.cog.setToolTip("Settings (Ctrl+,)")
        self.cog.setAutoRaise(True); self.cog.setFixedSize(self.BTN_W, self.BTN_H); self.cog.clicked.connect(self.toggle_page)
        topbar.addWidget(self.cog)
        root.addLayout(topbar)

        # Stacked pages
        self.stack = QStackedLayout(); root.addLayout(self.stack)

        # Page 0: GRID
        page_grid = QFrame(self); pg_layout = QVBoxLayout(page_grid); pg_layout.setContentsMargins(0,0,0,0); pg_layout.setSpacing(0)
        self.grid = GridWidget(scale=self._scale, parent=page_grid)
        pg_layout.addWidget(self.grid, 0, Qt.AlignTop | Qt.AlignLeft)
        self.stack.addWidget(page_grid)

        # Page 1: SETTINGS
        page_settings = QFrame(self); ps_layout = QVBoxLayout(page_settings); ps_layout.setContentsMargins(0,0,0,0); ps_layout.setSpacing(8)
        opacityName_lbl = QLabel("Opacity",page_settings); opacityName_lbl.setStyleSheet("color: white;")
        op_row = QHBoxLayout(); op_row.addWidget(opacityName_lbl, 0)
        self.slider_opacity = QSlider(Qt.Horizontal, page_settings); self.slider_opacity.setRange(20,100); self.slider_opacity.setValue(int(self._default_opacity*100))
        self.slider_opacity.valueChanged.connect(self.on_opacity_changed); self.slider_opacity.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        op_row.addWidget(self.slider_opacity,1); self.value_lbl = QLabel(f"{int(self._default_opacity*100)}%", page_settings); self.value_lbl.setStyleSheet("color: white; min-width: 36px;")
        op_row.addWidget(self.value_lbl,0); ps_layout.addLayout(op_row)
        scaleName_lbl = QLabel("Scale",page_settings); scaleName_lbl.setStyleSheet("color: white;")
        sc_row = QHBoxLayout(); sc_row.addWidget(scaleName_lbl, 0)
        self.slider_scale = QSlider(Qt.Horizontal, page_settings); self.slider_scale.setRange(50,200); self.slider_scale.setValue(int(self._scale*100))
        self.slider_scale.valueChanged.connect(self.on_scale_changed); sc_row.addWidget(self.slider_scale,1)
        self.scale_lbl = QLabel(f"{int(self._scale*100)}%", page_settings); self.scale_lbl.setStyleSheet("color: white; min-width: 44px;"); sc_row.addWidget(self.scale_lbl,0)
        ps_layout.addLayout(sc_row)
        help_lbl = QLabel("Controls:\n• Left-click — Start timer\n• Right-click — Reset timer")
        help_lbl.setStyleSheet("color: white;"); ps_layout.addWidget(help_lbl,0)
        self.stack.addWidget(page_settings)

        # init
        self.on_opacity_changed(self.slider_opacity.value())
        self.adjust_to_content()

        self.load_position()

        # topmost heartbeat (Windows): reassert every 3s just in case
        if IS_WINDOWS:
            self._topmost_worker = TopmostWorker()
            self._topmost_worker.status.connect(self._on_topmost_status)
            self._topmost_worker.start()

        self._game_worker = GameStateWorker()
        self._game_worker.status.connect(self._on_game_state)
        self._game_worker.start()

        self.show()

    # panel paint (explicit end to silence warnings)
    def paintEvent(self, _):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QColor(255, 255, 255, 60))

            # compute rounded rect and radius (scale-aware)
            rectf = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            radius = max(8, int(8 * getattr(self, "_scale", 1.0)))

            # background brush: different when dragging
            if self._drag_pos is not None:
                p.setBrush(QColor(50, 50, 50, 120))
            else:
                p.setBrush(QColor(30, 30, 30, 5))

            p.drawRoundedRect(rectf, float(radius), float(radius))

            try:
                path = QPainterPath()
                path.addRoundedRect(rectf, float(radius), float(radius))
                region = QRegion(path.toFillPolygon().toPolygon())
                self.setMask(region)
            except Exception:
                pass
        finally:
            p.end()

    def closeEvent(self, e):
            try:
                self.save_position()
            except Exception:
                pass
            # stop workers cleanly
            if IS_WINDOWS and getattr(self, "_topmost_worker", None):
                try:
                    self._topmost_worker.stop()
                    self._topmost_worker.wait(1000)
                except Exception:
                    pass
            if getattr(self, "_game_worker", None):
                try:
                    self._game_worker.stop()
                    self._game_worker.wait(1000)
                except Exception:
                    pass
            return super().closeEvent(e)

############################################
######## Topmost handling (Windows) ########
############################################

    def _on_topmost_status(self, league_active_window: bool):
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        # keep original focused logic but use the precomputed league_active_window
        focused = league_active_window or getattr(self, "_is_dragging", False) or self.isActiveWindow()
        should_show = self._in_game and focused# and self.loaded
        # print(f"[TOPMOST] ingame={self._in_game} focused={focused} loaded={self.loaded} -> show={should_show}")
        # perform minimal UI work on main thread
        try:
            if should_show and not self.visible:
                self.show()
                if IS_WINDOWS:
                    import ctypes, ctypes.wintypes as wt
                    hwnd = int(self.winId())
                    ctypes.windll.user32.SetWindowPos(
                        wt.HWND(hwnd), HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                    )
                self.visible = True
            elif not should_show and self.visible:
                self.hide()
                self.visible = False
        except Exception as e:
            print("[TOPMOST] Error updating window state:", e)

#############################################
############ Game state handling ############
#############################################

    def _on_game_state(self, in_game: bool):
        """Called from GameStateWorker (main thread) with the latest in-game status."""
        # game started
        if in_game and not getattr(self, "_in_game", False):
            print("[AUTO-SYNC] Game started, attempting sync…")
            # don't start another worker if one is already running
            if not getattr(self, "worker", None) or not self.worker.isRunning():
                self.worker = LocalSyncWorker()
                self.worker.finished_ok.connect(self.on_sync_ok)
                self.worker.failed.connect(self.on_sync_fail)
                self.worker.start()
                self.loaded = True
        elif not in_game and getattr(self, "_in_game", False):
            print("[AUTO-SYNC] Game ended, clearing grid.")
            self.grid.clear()
            self.loaded = False

############################################
########### Mouse drag handling ############
############################################

    def mousePressEvent(self, e):
        if not self._locked and e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft(); e.accept()
            self.update()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not self._locked and self._drag_pos is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_pos); e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = None; e.accept()
            self.update()
            try:
                self.save_position()
            except Exception:
                pass
        else:
            super().mouseReleaseEvent(e)

############################################
######### UI event handlers ################
############################################

    def on_opacity_changed(self, val):
        self.setWindowOpacity(val/100.0); self.value_lbl.setText(f"{val}%")
        self.userData.set("overlay_opacity", val/100.0)

    def on_scale_changed(self, val):
        self._scale = val/100.0; self.scale_lbl.setText(f"{val}%")
        self.grid.set_scale(self._scale); self.adjust_to_content(); #force_topmost(self)
        self.userData.set("overlay_scale", val/100.0)

    def toggle_lock(self):
        self._locked = not self._locked
        self.lock_btn.setText("🔒" if self._locked else "🔓")
        self.setCursor(Qt.ArrowCursor if self._locked else Qt.OpenHandCursor)

    def toggle_page(self):
        self._page = 1 - self._page; self.stack.setCurrentIndex(self._page); self.adjust_to_content(); #force_topmost(self)

    def adjust_to_content(self):
        tl = self.frameGeometry().topLeft()
        content = self.stack.currentWidget(); hint = content.sizeHint()
        w = hint.width() + 2*self.BASE_PAD; h = hint.height() + 2*self.BASE_PAD + self.BTN_H + 6
        self.setMinimumSize(QSize(w,h)); self.resize(w,h); self.move(tl)

############################################
######### Position persistence #############
############################################

    def save_position(self):
        """Save current top-left screen position to userData."""
        pt = self.frameGeometry().topLeft()
        self.userData.set("overlay_pos", {"x": int(pt.x()), "y": int(pt.y())})

    def load_position(self):
        """Load saved position from userData and move window if valid."""
        pos = self.userData.get("overlay_pos", None)
        if isinstance(pos, dict):
            try:
                x = int(pos.get("x", 0))
                y = int(pos.get("y", 0))
                # move only if values are sensible
                self.move(QPoint(x, y))
            except Exception:
                pass

############################################
######### Sync handling ####################
############################################

    def on_sync_ok(self, enemies: list):
        print("[SYNC] Retrieved enemy data:")
        print(enemies)
        for e in enemies:
            champ = e.get("champion", "Unknown"); spells = ", ".join(e.get("spells", [])) or "Unknown"
            print(f"[SYNC] {champ}: {spells}")
        self.grid.set_content_from_enemies(enemies)
        self._in_game = True

    def on_sync_fail(self, msg: str):
        print("[SYNC] Failed:", msg); QMessageBox.information(self, "Sync", msg)#; force_topmost(self)
        self.grid.clear()



IS_WINDOWS = sys.platform.startswith("win")
