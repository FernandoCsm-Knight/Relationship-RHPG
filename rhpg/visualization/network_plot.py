import re
from typing import Optional
import networkx as nx
from pyvis.network import Network

from rhpg.models.worker import PerformanceClass

_BG        = "#f5f6fa"
_FONT      = "#1a1d2e"
_BRIDGE    = "#f4a261"   # orange — bridge worker border + cross-group edges

_PERF_COLOR = {
    PerformanceClass.HIGH:    "#00a878",
    PerformanceClass.LOW:     "#d63557",
    PerformanceClass.NEUTRAL: "#8899aa",
}

# One distinct color per group (cycled)
GROUP_PALETTE = [
    "#5b4de8",  # indigo
    "#d63097",  # pink
    "#0a84e8",  # blue
    "#7209b7",  # violet
    "#008080",  # teal
    "#b45309",  # amber
]


def _short_worker_label(name: str, max_len: int = 16) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return name[:max_len]
    if len(parts) == 1:
        return parts[0][:max_len]
    label = f"{parts[0]} {parts[-1][0]}."
    return label if len(label) <= max_len else parts[0][:max_len]


def _rel_label(rel_type) -> str:
    value = rel_type.value if hasattr(rel_type, "value") else str(rel_type)
    labels = {
        "COLLABORATION": "Colab.",
        "CROSS_GROUP": "Entre grupos",
        "MEMBERSHIP": "Membro",
    }
    return labels.get(value, value.replace("_", " ").title())


def render_network_html(
    G: nx.DiGraph,
    classification: dict[str, PerformanceClass],
    memberships: dict[str, list[str]],   # group_id → [worker_ids]
    groups: list,                         # list of Group dataclass objects
    filter_group_ids: Optional[list[str]] = None,
) -> str:
    # ── Group color map ──────────────────────────────────────────────────────
    group_color: dict[str, str] = {
        g.id: GROUP_PALETTE[i % len(GROUP_PALETTE)]
        for i, g in enumerate(groups)
    }

    # ── Worker → groups mapping ───────────────────────────────────────────────
    worker_groups: dict[str, list[str]] = {}
    for gid, members in memberships.items():
        for wid in members:
            worker_groups.setdefault(wid, []).append(gid)

    # Primary group = first group the worker belongs to
    worker_primary: dict[str, str] = {
        wid: gids[0] for wid, gids in worker_groups.items() if gids
    }

    # Bridge workers = members of ≥ 2 groups
    bridge_workers: set[str] = {
        wid for wid, gids in worker_groups.items() if len(gids) >= 2
    }

    # ── Filter: which workers to show ────────────────────────────────────────
    visible: Optional[set[str]] = None
    if filter_group_ids:
        visible = set()
        for gid in filter_group_ids:
            visible.update(memberships.get(gid, []))

    # ── Build network ─────────────────────────────────────────────────────────
    net = Network(
        height="100vh", width="100%", directed=True,
        bgcolor=_BG, font_color=_FONT,
        cdn_resources="in_line",
    )
    net.barnes_hut(gravity=-9000, central_gravity=0.4, spring_length=140)

    group_name_map = {g.id: g.name for g in groups}

    # ── Nodes ─────────────────────────────────────────────────────────────────
    for node, data in G.nodes(data=True):
        if data.get("node_type") == "group":
            continue
        if visible is not None and node not in visible:
            continue

        perf  = classification.get(node) or PerformanceClass.NEUTRAL
        score = data.get("composite_score", 0.0)
        pc    = _PERF_COLOR[perf]
        is_bridge = node in bridge_workers
        gids  = worker_groups.get(node, [])
        gnames = ", ".join(group_name_map.get(g, g) for g in gids)

        tooltip = (
            f"{data.get('name', node)}\n"
            f"{data.get('role', '')} - {data.get('department', '')}\n"
            f"Score: {score:.3f}\n"
            f"Grupos: {gnames or '-'}"
            + ("\nBridge worker" if is_bridge else "")
        )

        if is_bridge:
            color = {
                "background": pc + "44",
                "border":     _BRIDGE,
                "highlight":  {"background": pc + "77", "border": _BRIDGE},
            }
            border_w = 4
            size = max(18, int(score * 46))
        else:
            color = {
                "background": pc + "33",
                "border":     pc,
                "highlight":  {"background": pc + "66", "border": pc},
            }
            border_w = 2
            size = max(13, int(score * 38))

        net.add_node(
            node,
            label=_short_worker_label(data.get("name", node)),
            shape="dot",
            size=size,
            color=color,
            borderWidth=border_w,
            font={"color": _FONT, "size": 13, "face": "Inter", "strokeWidth": 3, "strokeColor": _BG},
            title=tooltip,
        )

    # ── Edges ─────────────────────────────────────────────────────────────────
    shown = set(net.get_nodes())
    for u, v, edata in G.edges(data=True):
        if u not in shown or v not in shown:
            continue

        rel = edata.get("rel_type", "COLLABORATION")
        if rel == "MEMBERSHIP":
            continue

        weight = edata.get("weight", 0.1)
        rel_text = _rel_label(rel)

        if rel == "CROSS_GROUP":
            # Cross-group edges: orange, bold
            edge_color = _BRIDGE
            width = max(2.5, weight * 7)
        else:
            # Intra-group collaboration: source worker's group color
            src_gid = worker_primary.get(u)
            tgt_gid = worker_primary.get(v)
            if src_gid and tgt_gid and src_gid != tgt_gid:
                # Workers in different groups connected by COLLABORATION
                edge_color = _BRIDGE
                width = max(2.0, weight * 6)
            else:
                edge_color = group_color.get(src_gid, "#aaaaaa") if src_gid else "#aaaaaa"
                width = max(1.0, weight * 4)

        net.add_edge(
            u, v,
            label=f"{weight:.2f}",
            width=width,
            color={"color": edge_color + "99", "highlight": edge_color},
            font={"size": 10, "color": "#465166", "strokeWidth": 3, "strokeColor": _BG, "align": "middle"},
            title=f"{rel_text}\nPeso: {weight:.2f}",
        )

    # ── Post-process HTML ─────────────────────────────────────────────────────
    html = net.generate_html()
    html = re.sub(
        r"<body\b[^>]*>",
        f'<body style="margin:0;padding:0;overflow:hidden;background:{_BG};">',
        html,
    )
    html = re.sub(
        r'(id=["\']mynetwork["\'][^>]*style=["\'])([^"\']*)',
        r"\g<1>width:100%;height:100vh;",
        html,
    )
    html = html.replace(
        "</head>",
        "<style>.vis-tooltip{white-space:pre-line;font-family:Inter,'Segoe UI',sans-serif;line-height:1.35}</style></head>",
    )
    return html
