"""
OpenCV 기반 개폐기 심볼 자동인식 및 선로 검출
"""
import cv2
import numpy as np
from pathlib import Path
from .graph import SchematicGraph


SYMBOL_DIR = Path(__file__).parent.parent / "assets" / "symbols"

# 인식 임계값 (0~1, 높을수록 엄격)
MATCH_THRESHOLD = 0.75


def load_templates() -> dict[str, np.ndarray]:
    """assets/symbols/ 의 PNG 파일들을 템플릿으로 로드."""
    templates = {}
    if SYMBOL_DIR.exists():
        for p in SYMBOL_DIR.glob("*.png"):
            img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                templates[p.stem] = img
    return templates


def detect_switches(png_path: str) -> list[dict]:
    """
    PNG에서 개폐기 위치를 템플릿 매칭으로 검출.
    반환: [{"label": str, "x": int, "y": int, "w": int, "h": int}, ...]
    """
    templates = load_templates()
    img = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"PNG 파일을 열 수 없습니다: {png_path}")

    results = []
    seen_positions = []

    for label, tmpl in templates.items():
        th, tw = tmpl.shape
        res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
        locs = np.where(res >= MATCH_THRESHOLD)

        for pt in zip(*locs[::-1]):
            cx, cy = pt[0] + tw // 2, pt[1] + th // 2
            # 근접 중복 제거 (30px 이내)
            if any(abs(cx - s[0]) < 30 and abs(cy - s[1]) < 30 for s in seen_positions):
                continue
            seen_positions.append((cx, cy))
            results.append({"label": label, "x": cx, "y": cy, "w": tw, "h": th})

    return results


def detect_lines(png_path: str) -> list[dict]:
    """
    Hough 변환으로 수평/수직 선로 검출.
    반환: [{"x1":int,"y1":int,"x2":int,"y2":int,"type":"solid"|"dashed"}, ...]
    """
    img = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return []

    edges = cv2.Canny(img, 50, 150, apertureSize=3)
    raw = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                          minLineLength=40, maxLineGap=10)
    if raw is None:
        return []

    lines = []
    for line in raw:
        x1, y1, x2, y2 = line[0]
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        # 수평/수직만 취급
        if dx > dy:
            if dy > 10:
                continue
        else:
            if dx > 10:
                continue
        lines.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "type": "solid"})

    return lines


def build_graph_from_png(png_path: str) -> SchematicGraph:
    """
    PNG → 자동 인식 → SchematicGraph 구성.
    템플릿이 없거나 인식 실패 시 빈 그래프 반환.
    """
    graph = SchematicGraph()
    switches_detected = detect_switches(png_path)

    id_map = {}
    for det in switches_detected:
        sw = graph.add_switch(det["x"], det["y"], det["label"])
        id_map[(det["x"], det["y"])] = sw.id

    # 검출된 선로로 엣지 연결 (가장 가까운 두 개폐기 연결)
    lines = detect_lines(png_path)
    switch_positions = [(s.x, s.y, s.id) for s in graph.switches.values()]

    for line in lines:
        p1 = (line["x1"], line["y1"])
        p2 = (line["x2"], line["y2"])
        src = _nearest_switch(p1, switch_positions)
        dst = _nearest_switch(p2, switch_positions)
        if src and dst and src != dst:
            # 중복 엣지 방지
            existing = {(e.src_id, e.dst_id) for e in graph.edges.values()}
            if (src, dst) not in existing and (dst, src) not in existing:
                graph.add_edge(src, dst, line["type"])

    return graph


def _nearest_switch(point: tuple, positions: list, max_dist: int = 60) -> str | None:
    px, py = point
    best_id, best_d = None, max_dist
    for x, y, sid in positions:
        d = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
        if d < best_d:
            best_d, best_id = d, sid
    return best_id
