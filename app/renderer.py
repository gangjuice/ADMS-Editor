"""
편집 결과를 원본 PNG 위에 오버레이하여 새 PNG로 저장
"""
import cv2
import numpy as np
from .graph import SchematicGraph, Switch


def _imread(path: str) -> np.ndarray | None:
    """cv2.imread의 한글/유니코드 경로 대응 버전."""
    buf = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def _imwrite(path: str, img: np.ndarray):
    """cv2.imwrite의 한글/유니코드 경로 대응 버전."""
    ext = path.rsplit('.', 1)[-1].lower()
    ok, buf = cv2.imencode(f'.{ext}', img)
    if not ok:
        raise IOError(f"이미지 인코딩 실패: {path}")
    buf.tofile(path)


TERMINAL_RADIUS = 10
TERMINAL_FONT_SCALE = 0.4
SWITCH_BODY_RADIUS = 22


def render_to_png(base_png: str, graph: SchematicGraph, output_path: str):
    """원본 PNG를 배경으로 그래프 상태를 오버레이하여 저장."""
    img = _imread(base_png)
    if img is None:
        raise FileNotFoundError(f"배경 PNG를 열 수 없습니다: {base_png}")

    overlay = img.copy()

    # 엣지(선로) 렌더링
    for edge in graph.edges.values():
        src = graph.switches.get(edge.src_id)
        dst = graph.switches.get(edge.dst_id)
        if not src or not dst:
            continue
        p1 = (int(src.x), int(src.y))
        p2 = (int(dst.x), int(dst.y))
        if edge.line_type == "dashed":
            _draw_dashed_line(overlay, p1, p2, (50, 50, 50), 2)
        else:
            cv2.line(overlay, p1, p2, (50, 50, 50), 2)

    # 개폐기 심볼 렌더링
    for sw in graph.switches.values():
        _draw_switch(overlay, sw)

    _imwrite(output_path, overlay)


def _draw_switch(img: np.ndarray, sw: Switch):
    cx, cy = int(sw.x), int(sw.y)

    # 외곽 원 (개폐기 본체)
    cv2.circle(img, (cx, cy), SWITCH_BODY_RADIUS, (80, 80, 80), 2)

    # 단자번호 배치 (1=상, 2=좌, 3=우, 4=하)
    offsets = {1: (0, -16), 2: (-16, 0), 3: (16, 0), 4: (0, 16)}
    for num, terminal in sw.terminals.items():
        ox, oy = offsets.get(num, (0, 0))
        tx, ty = cx + ox, cy + oy
        color = terminal.color
        cv2.circle(img, (tx, ty), TERMINAL_RADIUS, color, -1)
        cv2.circle(img, (tx, ty), TERMINAL_RADIUS, (255, 255, 255), 1)
        cv2.putText(img, str(num), (tx - 4, ty + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, TERMINAL_FONT_SCALE,
                    (255, 255, 255), 1, cv2.LINE_AA)


def _draw_dashed_line(img, p1, p2, color, thickness, dash=10, gap=6):
    x1, y1 = p1
    x2, y2 = p2
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if length == 0:
        return
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    pos = 0
    while pos < length:
        end = min(pos + dash, length)
        px1 = int(x1 + dx * pos)
        py1 = int(y1 + dy * pos)
        px2 = int(x1 + dx * end)
        py2 = int(y1 + dy * end)
        cv2.line(img, (px1, py1), (px2, py2), color, thickness)
        pos += dash + gap
