from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.text import Text


@dataclass(frozen=True)
class GraphNode:
    id: int
    labels: tuple[str, ...]
    properties: dict[str, object]
    display: str


@dataclass(frozen=True)
class GraphEdge:
    src: int
    dest: int
    type: str
    id: int | None = None
    properties: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphViewModel:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    truncated: bool = False
    total_nodes: int = 0
    total_edges: int = 0


@dataclass(frozen=True)
class Hitbox:
    node_id: int
    x0: int
    y0: int
    x1: int
    y1: int


@dataclass(frozen=True)
class AsciiCanvas:
    text: str
    hitboxes: tuple[Hitbox, ...]
    node_order: tuple[int, ...]
    rich: Text | None = None


@dataclass(frozen=True)
class NodePose:
    id: int
    x: float
    y: float
    r: float
    color_key: str | None


@dataclass(frozen=True)
class EdgePose:
    key: object
    x0: float
    y0: float
    x1: float
    y1: float
    type: str


@dataclass(frozen=True)
class GraphGeometry:
    nodes: tuple[NodePose, ...]
    edges: tuple[EdgePose, ...]
    node_order: tuple[int, ...]
    edge_order: tuple[object, ...]
    width: int
    height: int
