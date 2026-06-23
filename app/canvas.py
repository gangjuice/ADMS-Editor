"""
PyQt6 편집 캔버스 — 개폐기 클릭(투개방), 선로 클릭(설비 삽입)
"""
from PyQt6.QtWidgets import QWidget, QInputDialog
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from .graph import SchematicGraph, Switch


HIT_RADIUS = 18      # 단자 클릭 감지 범위(px)
EDGE_HIT_WIDTH = 8   # 선로 클릭 감지 폭(px)
SWITCH_BODY_R = 22
TERMINAL_R = 10
TERMINAL_OFFSETS = {1: (0, -16), 2: (-16, 0), 3: (16, 0), 4: (0, 16)}

COLOR_INVESTED = QColor(220, 30, 30)
COLOR_OPEN = QColor(30, 180, 30)
COLOR_EDGE = QColor(50, 50, 50)
COLOR_EDGE_DASH = QColor(80, 80, 80)


class SchematicCanvas(QWidget):
    changed = pyqtSignal()  # 편집 발생 시 메인윈도우에 알림

    def __init__(self, parent=None):
        super().__init__(parent)
        self.graph: SchematicGraph | None = None
        self.pixmap: QPixmap | None = None
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        self._drag_start = None
        self._drag_offset = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def load(self, png_path: str, graph: SchematicGraph):
        # Qt PNG 플러그인 누락 문제를 우회: cv2로 읽어 QImage 직접 생성
        import cv2
        import numpy as np
        from PyQt6.QtGui import QImage
        buf = np.fromfile(png_path, dtype=np.uint8)
        img_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img_bgr is not None:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            h, w, c = img_rgb.shape
            qimg = QImage(img_rgb.tobytes(), w, h, w * c, QImage.Format.Format_RGB888)
            self.pixmap = QPixmap.fromImage(qimg)
        else:
            self.pixmap = None
        self.graph = graph
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        self.update()

    # ── 렌더링 ──────────────────────────────────────────────

    def paintEvent(self, event):
        if self.pixmap is None or self.pixmap.isNull() or self.graph is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 배경 PNG
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)
        painter.drawPixmap(0, 0, self.pixmap)

        # 선로
        for edge in self.graph.edges.values():
            src = self.graph.switches.get(edge.src_id)
            dst = self.graph.switches.get(edge.dst_id)
            if not src or not dst:
                continue
            pen = QPen(COLOR_EDGE, 2)
            if edge.line_type == "dashed":
                pen.setStyle(Qt.PenStyle.DashLine)
                pen.setColor(COLOR_EDGE_DASH)
            painter.setPen(pen)
            painter.drawLine(int(src.x), int(src.y), int(dst.x), int(dst.y))

        # 개폐기
        for sw in self.graph.switches.values():
            self._draw_switch(painter, sw)

        painter.end()

    def _draw_switch(self, painter: QPainter, sw: Switch):
        cx, cy = int(sw.x), int(sw.y)
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        painter.setBrush(Qt.BrushPattern.NoBrush)
        painter.drawEllipse(cx - SWITCH_BODY_R, cy - SWITCH_BODY_R,
                            SWITCH_BODY_R * 2, SWITCH_BODY_R * 2)

        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        for num, terminal in sw.terminals.items():
            ox, oy = TERMINAL_OFFSETS[num]
            tx, ty = cx + ox, cy + oy
            color = COLOR_INVESTED if terminal.state == "투입" else COLOR_OPEN
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.drawEllipse(tx - TERMINAL_R, ty - TERMINAL_R,
                                TERMINAL_R * 2, TERMINAL_R * 2)
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(QRect(tx - TERMINAL_R, ty - TERMINAL_R,
                                   TERMINAL_R * 2, TERMINAL_R * 2),
                             Qt.AlignmentFlag.AlignCenter, str(num))

    # ── 마우스 이벤트 ────────────────────────────────────────

    def mousePressEvent(self, event):
        if not self.graph:
            return

        scene_pos = self._to_scene(event.position().toPoint())
        sx, sy = scene_pos.x(), scene_pos.y()

        if event.button() == Qt.MouseButton.LeftButton:
            # 단자 클릭 → 투개방 토글
            hit = self._hit_terminal(sx, sy)
            if hit:
                sw_id, term_num = hit
                self.graph.switches[sw_id].toggle_terminal(term_num)
                self.changed.emit()
                self.update()
                return

            # 선로 클릭 → 설비 삽입
            hit_edge = self._hit_edge(sx, sy)
            if hit_edge:
                count, ok = QInputDialog.getInt(
                    self, "설비 삽입", "삽입할 개폐기 수:", 1, 1, 10)
                if ok and count > 0:
                    self.graph.insert_switches_on_edge(hit_edge, count)
                    self.changed.emit()
                    self.update()
                return

        elif event.button() == Qt.MouseButton.MiddleButton:
            self._drag_start = event.position().toPoint()
            self._drag_offset = self.offset

    def mouseMoveEvent(self, event):
        if self._drag_start and event.buttons() & Qt.MouseButton.MiddleButton:
            delta = event.position().toPoint() - self._drag_start
            self.offset = self._drag_offset + delta
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._drag_start = None

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale = max(0.2, min(5.0, self.scale * factor))
        self.update()

    # ── 좌표 변환 / 히트 테스트 ─────────────────────────────

    def _to_scene(self, widget_pos: QPoint) -> QPoint:
        return QPoint(
            int((widget_pos.x() - self.offset.x()) / self.scale),
            int((widget_pos.y() - self.offset.y()) / self.scale),
        )

    def _hit_terminal(self, sx, sy) -> tuple[str, int] | None:
        for sw in self.graph.switches.values():
            cx, cy = int(sw.x), int(sw.y)
            for num, (ox, oy) in TERMINAL_OFFSETS.items():
                tx, ty = cx + ox, cy + oy
                if (sx - tx) ** 2 + (sy - ty) ** 2 <= HIT_RADIUS ** 2:
                    return sw.id, num
        return None

    def _hit_edge(self, sx, sy) -> str | None:
        for eid, edge in self.graph.edges.items():
            src = self.graph.switches.get(edge.src_id)
            dst = self.graph.switches.get(edge.dst_id)
            if not src or not dst:
                continue
            dist = _point_to_segment_dist(
                sx, sy, src.x, src.y, dst.x, dst.y)
            if dist <= EDGE_HIT_WIDTH:
                return eid
        return None


def _point_to_segment_dist(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    nx, ny = x1 + t * dx, y1 + t * dy
    return ((px - nx) ** 2 + (py - ny) ** 2) ** 0.5
