"""
계통도 그래프 구조: 노드(개폐기) + 엣지(선로)
"""
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Terminal:
    number: int          # 단자번호 (1~4)
    state: str = "투입"  # "투입" | "개방"

    def toggle(self):
        self.state = "개방" if self.state == "투입" else "투입"

    @property
    def color(self):
        return (220, 30, 30) if self.state == "투입" else (30, 180, 30)


@dataclass
class Switch:
    id: str
    x: float
    y: float
    label: str = ""
    terminals: dict = field(default_factory=dict)  # {num: Terminal}

    def __post_init__(self):
        if not self.terminals:
            for n in range(1, 5):
                self.terminals[n] = Terminal(number=n)

    def toggle_terminal(self, terminal_num: int):
        if terminal_num in self.terminals:
            self.terminals[terminal_num].toggle()


@dataclass
class Edge:
    id: str
    src_id: str   # Switch id
    dst_id: str   # Switch id
    line_type: str = "solid"  # "solid" | "dashed"


class SchematicGraph:
    def __init__(self):
        self.switches: dict[str, Switch] = {}
        self.edges: dict[str, Edge] = {}
        self._edge_counter = 0
        self._switch_counter = 0

    def add_switch(self, x: float, y: float, label: str = "") -> Switch:
        self._switch_counter += 1
        sid = f"sw_{self._switch_counter}"
        sw = Switch(id=sid, x=x, y=y, label=label)
        self.switches[sid] = sw
        return sw

    def add_edge(self, src_id: str, dst_id: str, line_type: str = "solid") -> Edge:
        self._edge_counter += 1
        eid = f"edge_{self._edge_counter}"
        edge = Edge(id=eid, src_id=src_id, dst_id=dst_id, line_type=line_type)
        self.edges[eid] = edge
        return edge

    def insert_switches_on_edge(self, edge_id: str, count: int) -> list[Switch]:
        """선로 위에 개폐기 N대를 균등 삽입."""
        edge = self.edges.pop(edge_id)
        src = self.switches[edge.src_id]
        dst = self.switches[edge.dst_id]

        new_switches = []
        for i in range(1, count + 1):
            t = i / (count + 1)
            x = src.x + (dst.x - src.x) * t
            y = src.y + (dst.y - src.y) * t
            sw = self.add_switch(x, y)
            new_switches.append(sw)

        # 기존 엣지를 새 노드들로 분할
        chain = [edge.src_id] + [s.id for s in new_switches] + [edge.dst_id]
        for a, b in zip(chain, chain[1:]):
            self.add_edge(a, b, edge.line_type)

        return new_switches

    def to_dict(self) -> dict:
        return {
            "switches": {
                sid: {
                    "id": s.id, "x": s.x, "y": s.y, "label": s.label,
                    "terminals": {
                        str(n): {"number": t.number, "state": t.state}
                        for n, t in s.terminals.items()
                    }
                }
                for sid, s in self.switches.items()
            },
            "edges": {
                eid: {"id": e.id, "src_id": e.src_id, "dst_id": e.dst_id, "line_type": e.line_type}
                for eid, e in self.edges.items()
            },
            "_switch_counter": self._switch_counter,
            "_edge_counter": self._edge_counter,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SchematicGraph":
        g = cls()
        g._switch_counter = data.get("_switch_counter", 0)
        g._edge_counter = data.get("_edge_counter", 0)
        for sid, s in data.get("switches", {}).items():
            terminals = {
                int(n): Terminal(number=t["number"], state=t["state"])
                for n, t in s.get("terminals", {}).items()
            }
            g.switches[sid] = Switch(
                id=s["id"], x=s["x"], y=s["y"], label=s.get("label", ""),
                terminals=terminals
            )
        for eid, e in data.get("edges", {}).items():
            g.edges[eid] = Edge(
                id=e["id"], src_id=e["src_id"], dst_id=e["dst_id"],
                line_type=e.get("line_type", "solid")
            )
        return g

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "SchematicGraph":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
