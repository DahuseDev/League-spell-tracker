from logging import root
import sys, re, unicodedata, os, time, json
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider,
    QToolButton, QFrame, QSizePolicy, QStackedLayout, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, QPoint, QSize, QRect, QThread, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QShortcut, QKeySequence, QPixmap, QFont
# ============================== GRID CONTENT ==================================

class GridWidget(QWidget):
    """
    4 rows x 5 cols:
      row 0: champions (no timer)
      row 1: summoner #1
      row 2: summoner #2
      row 3: ultimate
    Click: left=start, shift+left=custom, right=reset
    """
    def __init__(self, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self._scale = scale
        self.metrics = GridMetrics()
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.content = GridContent()
        self._cache: Dict[str, QPixmap] = {}
        self.label_font = QFont(); self.label_font.setPointSize(9)

        self.timers: Dict[Tuple[int,int], CellTimer] = {}
        self.ult_cd_map = load_ult_cd_map()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(250)

    def set_scale(self, s: float):
        self._scale = max(0.25, s)
        self.updateGeometry()
        self.update()

    def set_content_from_enemies(self, enemies: List[Dict]):
        self.content.set_enemies(enemies)
        self.timers.clear()
        self.update()

    def clear(self):
        self.set_content_from_enemies([])

    def sizeHint(self) -> QSize:
        m, s = self.metrics, self._scale
        margin = int(m.margin * s); spacing = int(m.spacing * s); square = int(m.square * s)
        grid_w = 5 * square + 4 * spacing
        grid_h = square + (spacing // 2) + 3 * square + 2 * spacing
        return QSize(grid_w + 2 * margin, grid_h + 2 * margin)

    def cell_rect(self, row: int, col: int) -> QRect:
        m, s = self.metrics, self._scale
        margin = int(m.margin * s); spacing = int(m.spacing * s); square = int(m.square * s)
        if row == 0: y0 = margin
        else: y0 = margin + square + spacing // 2 + spacing + (row - 1) * (square + spacing)
        x = margin + col * (square + spacing)
        return QRect(x, y0, square, square)

    def _get_pixmap(self, path: str) -> Optional[QPixmap]:
        if not path: return None
        if path in self._cache: return self._cache[path]
        if os.path.exists(path):
            pm = QPixmap(path); self._cache[path] = pm; return pm
        return None

    def paintEvent(self, _):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QColor(255, 255, 255, 220))
            p.setBrush(Qt.NoBrush)

            m, s = self.metrics, self._scale
            margin = int(m.margin * s); spacing = int(m.spacing * s); square = int(m.square * s)

            # grid outlines
            for c in range(5):
                p.drawRect(self.cell_rect(0, c))
            y_sep = margin + square + spacing // 2
            p.drawLine(margin, y_sep, margin + 5 * (square + spacing) - spacing, y_sep)
            for r in range(1, 4):
                for c in range(5):
                    p.drawRect(self.cell_rect(r, c))

            # contents
            for i in range(min(5, len(self.content.enemies))):
                # champions
                rect0 = self.cell_rect(0, i)
                pm = self._get_pixmap(self.content.hero_path(i))
                if pm: draw_pixmap_fit_center(p, pm, rect0)
                else:  self._draw_label(p, rect0, self.content.enemies[i].champion)

                # spell1
                rect1 = self.cell_rect(1, i)
                pm = self._get_pixmap(self.content.spell1_path(i))
                if pm: draw_pixmap_fit_center(p, pm, rect1)
                else:  self._draw_label(p, rect1, self.content.enemies[i].spells[0] or "—")
                self._draw_timer_overlay(p, 1, i, rect1)

                # spell2
                rect2 = self.cell_rect(2, i)
                pm = self._get_pixmap(self.content.spell2_path(i))
                if pm: draw_pixmap_fit_center(p, pm, rect2)
                else:  self._draw_label(p, rect2, self.content.enemies[i].spells[1] or "—")
                self._draw_timer_overlay(p, 2, i, rect2)

                # ultimate
                rect3 = self.cell_rect(3, i)
                pm = self._get_pixmap(self.content.ultimate_path(i))
                if pm: draw_pixmap_fit_center(p, pm, rect3)
                else:  self._draw_label(p, rect3, "R")
                self._draw_timer_overlay(p, 3, i, rect3)
        finally:
            p.end()

    def _draw_label(self, p: QPainter, rect: QRect, text: str):
        if not text: text = "?"
        p.save()
        f = QFont(self.label_font); f.setPointSize(max(7, int(9 * self._scale))); p.setFont(f)
        p.setPen(QColor(255, 255, 255, 230))
        p.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, text)
        p.restore()

    def _draw_timer_overlay(self, p: QPainter, row: int, col: int, rect: QRect):
        t = self.timers.get((row, col))
        if not t: return
        if t.running:
            txt = fmt_mmss(t.remaining); bg = QColor(0, 0, 0, 140)
        else:
            if t.remaining <= 0: txt = "UP"; bg = QColor(0, 120, 0, 160)
            else: return
        p.save()
        pill_h = max(14, int(16 * self._scale))
        r = QRect(rect.x()+2, rect.bottom()-pill_h-2, rect.width()-4, pill_h)
        p.setBrush(bg); p.setPen(Qt.NoPen); p.drawRoundedRect(r, 4, 4)
        f = QFont(self.label_font); f.setBold(True); f.setPointSize(max(8, int(10 * self._scale))); p.setFont(f)
        p.setPen(QColor(255,255,255,230)); p.drawText(r, Qt.AlignCenter, txt)
        p.restore()

    def _on_tick(self):
        changed = False
        for t in self.timers.values():
            before = (t.running, t.remaining); t.tick(); after = (t.running, t.remaining)
            if before != after: changed = True
        if changed: self.update()

    def _spell_base_cd(self, display_name: str) -> int:
        key = slugify(display_name); return SUMMONER_CD.get(key, 0)

    def _ult_base_cd(self, champ_name: str) -> int:
        key = slugify(champ_name); return self.ult_cd_map.get(key, DEFAULT_ULT_CD)

    def mousePressEvent(self, e):
        if e.button() not in (Qt.LeftButton, Qt.RightButton):
            return super().mousePressEvent(e)
        pos = e.position().toPoint()
        for row in range(4):
            for col in range(5):
                r = self.cell_rect(row, col)
                if r.contains(pos):
                    self._handle_cell_click(row, col, e); return
        super().mousePressEvent(e)

    def _handle_cell_click(self, row: int, col: int, e):
        if row == 0:  # champs: no timer
            return
        if e.button() == Qt.RightButton:
            t = self.timers.get((row, col))
            if t: t.reset(); self.update()
            return
        duration = 0
        if row in (1, 2):
            if col < len(self.content.enemies):
                idx = 0 if row == 1 else 1
                disp = self.content.enemies[col].spells[idx]
                duration = self._spell_base_cd(disp)
        elif row == 3:
            if col < len(self.content.enemies):
                champ = self.content.enemies[col].champion
                duration = self._ult_base_cd(champ)
        if (e.modifiers() & Qt.ShiftModifier) or duration <= 0:
            from PySide6.QtWidgets import QInputDialog
            secs, ok = QInputDialog.getInt(self, "Custom cooldown", "Seconds:", max(0, duration), 0, 9999, 1)
            if not ok: return
            duration = secs
        t = self.timers.get((row, col))
        if not t: t = CellTimer(); self.timers[(row, col)] = t
        t.start(float(duration)); self.update()


class GridContent:
    def __init__(self, heroes_dir="heroes", spells_dir="spells", ultimates_dir="ultimates"):
        self.heroes_dir = heroes_dir
        self.spells_dir = spells_dir
        self.ultimates_dir = ultimates_dir
        self.enemies: List[EnemyInfo] = []

    def set_enemies(self, enemies: List[Dict]):
        out: List[EnemyInfo] = []
        for e in enemies[:5]:
            champ = e.get("champion", "") or ""
            spells = (e.get("spells", []) or []) + ["", ""]
            out.append(EnemyInfo(champion=champ, spells=spells[:2]))
        self.enemies = out

    def hero_path(self, idx: int) -> str:
        if idx >= len(self.enemies): return ""
        return os.path.join(self.heroes_dir, f"{slugify(self.enemies[idx].champion)}.png")

    def spell1_path(self, idx: int) -> str:
        if idx >= len(self.enemies): return ""
        return os.path.join(self.spells_dir, f"{slugify(self.enemies[idx].spells[0])}.png")

    def spell2_path(self, idx: int) -> str:
        if idx >= len(self.enemies): return ""
        return os.path.join(self.spells_dir, f"{slugify(self.enemies[idx].spells[1])}.png")

    def ultimate_path(self, idx: int) -> str:
        if idx >= len(self.enemies): return ""
        return os.path.join(self.ultimates_dir, f"{slugify(self.enemies[idx].champion)}.png")

# ============================== GRID WIDGET ===================================
@dataclass
class GridMetrics:
    margin: int = 20
    spacing: int = 10
    square: int = 50

@dataclass
class CellTimer:
    running: bool = False
    duration: float = 0.0
    start_time: float = 0.0
    remaining: float = 0.0
    def start(self, duration: float):
        self.running = True
        self.duration = max(0.0, duration)
        self.start_time = time.monotonic()
        self.remaining = self.duration
    def reset(self):
        self.running = False
        self.remaining = 0.0
    def tick(self):
        if not self.running: return
        elapsed = time.monotonic() - self.start_time
        self.remaining = max(0.0, self.duration - elapsed)
        if self.remaining <= 0: self.running = False

@dataclass
class EnemyInfo:
    champion: str
    spells: List[str]  # [spell1, spell2]

# ============================== COOLDOWNS =====================================
SUMMONER_CD = {
    "flash": 300,
    "ignite": 180,
    "teleport": 360,
    "heal": 240,
    "barrier": 180,
    "exhaust": 210,
    "ghost": 210,
    "cleanse": 210,
    "smite": 15,
    "clarity": 240,
    "mark": 80,
    "porobelt": 10,
    "poro_toss": 10,
}
DEFAULT_ULT_CD = 120

def load_ult_cd_map(path="ult_cooldowns.json") -> Dict[str, int]:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {slugify(k): int(v) for k, v in raw.items() if isinstance(v, (int, float, str))}
        except Exception as e:
            print("[ULT-CD] Failed to load ult_cooldowns.json:", e)
    return {}

# ============================== HELPERS =======================================
def slugify(name: str) -> str:
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^\w]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def draw_pixmap_fit_center(p: QPainter, pix: QPixmap, rect: QRect):
    if pix.isNull() or rect.width() <= 0 or rect.height() <= 0:
        return
    target = pix.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    x = rect.x() + (rect.width() - target.width()) // 2
    y = rect.y() + (rect.height() - target.height()) // 2
    p.drawPixmap(x, y, target)

def fmt_mmss(seconds: float) -> str:
    if seconds < 0: seconds = 0
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:01d}:{s:02d}"

