"""
메인 윈도우 — 파일 열기/저장, 캔버스 통합
"""
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QFileDialog,
    QMessageBox, QStatusBar, QLabel
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt

from .canvas import SchematicCanvas
from .graph import SchematicGraph
from .detector import build_graph_from_png
from .renderer import render_to_png


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADMS-EDITOR — 설비계통도 편집기")
        self.resize(1400, 900)

        self.canvas = SchematicCanvas()
        self.setCentralWidget(self.canvas)
        self.canvas.changed.connect(self._on_changed)

        self._png_path: str | None = None
        self._json_path: str | None = None
        self._graph: SchematicGraph | None = None
        self._dirty = False

        self._build_toolbar()
        self._build_statusbar()

    # ── 툴바 ────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = QToolBar("메인")
        tb.setMovable(False)
        self.addToolBar(tb)

        actions = [
            ("PNG 열기",    "Ctrl+O", self._open_png),
            ("저장 (PNG+JSON)", "Ctrl+S", self._save),
            ("다른 이름으로 저장", "Ctrl+Shift+S", self._save_as),
        ]
        for label, shortcut, slot in actions:
            act = QAction(label, self)
            act.setShortcut(shortcut)
            act.triggered.connect(slot)
            tb.addAction(act)

        tb.addSeparator()

        self._mode_label = QLabel("  모드: 편집")
        tb.addWidget(self._mode_label)

    def _build_statusbar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("PNG 파일을 열어 시작하세요  (Ctrl+O)")

    # ── 파일 I/O ────────────────────────────────────────────

    def _open_png(self):
        if self._dirty and not self._confirm_discard():
            return

        png, _ = QFileDialog.getOpenFileName(
            self, "계통도 PNG 열기", "", "PNG 파일 (*.png)")
        if not png:
            return

        json_path = Path(png).with_suffix(".json")

        if json_path.exists():
            reply = QMessageBox.question(
                self, "저장된 편집 발견",
                f"'{json_path.name}' 파일이 있습니다.\n저장된 편집 상태를 불러올까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                graph = SchematicGraph.load(str(json_path))
            else:
                graph = self._detect_or_empty(png)
        else:
            graph = self._detect_or_empty(png)

        self._png_path = png
        self._json_path = str(json_path)
        self._graph = graph
        self._dirty = False
        self.canvas.load(png, graph)
        self._status.showMessage(f"열림: {png}")

    def _detect_or_empty(self, png: str) -> SchematicGraph:
        try:
            graph = build_graph_from_png(png)
            n = len(graph.switches)
            if n:
                self._status.showMessage(f"자동인식: 개폐기 {n}개 검출")
            else:
                self._status.showMessage("자동인식 결과 없음 — 수동으로 선로를 클릭해 설비를 추가하세요")
        except Exception as e:
            QMessageBox.warning(self, "인식 오류", str(e))
            graph = SchematicGraph()
        return graph

    def _save(self):
        if not self._graph or not self._png_path:
            return
        self._do_save(self._png_path, self._json_path)

    def _save_as(self):
        if not self._graph or not self._png_path:
            return
        png, _ = QFileDialog.getSaveFileName(
            self, "다른 이름으로 저장", "", "PNG 파일 (*.png)")
        if not png:
            return
        json_path = str(Path(png).with_suffix(".json"))
        self._do_save(png, json_path)
        self._png_path = png
        self._json_path = json_path

    def _do_save(self, png_out: str, json_out: str):
        try:
            render_to_png(self._png_path, self._graph, png_out)
            self._graph.save(json_out)
            self._dirty = False
            self._status.showMessage(f"저장 완료: {png_out}")
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", str(e))

    # ── 이벤트 ──────────────────────────────────────────────

    def _on_changed(self):
        self._dirty = True
        self._status.showMessage("편집됨 (미저장)")

    def _confirm_discard(self) -> bool:
        reply = QMessageBox.question(
            self, "저장되지 않은 변경사항",
            "변경사항이 있습니다. 저장하지 않고 닫을까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        if self._dirty and not self._confirm_discard():
            event.ignore()
        else:
            event.accept()
