import base64
import io
import math
import re
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pyvis.network import Network

_BG      = "#f5f6fa"
_CARD_BG = "#ffffff"
_TEXT    = "#1a1d2e"
_MUTED   = "#8491a5"
_HIGH    = "#00a878"
_NEUTRAL = "#8899aa"
_LOW     = "#d63557"
_EDGE_COLOR = "#667799"

_GROUP_PALETTES = [
    ("#5b4de8", "#ede9fe"),
    ("#d63097", "#fce7f5"),
    ("#7209b7", "#f3e8ff"),
    ("#0a84e8", "#e0f0ff"),
    ("#c05000", "#fff0e6"),
]

_GROUP_COLORS = ["#5b4de8", "#d63097", "#0a84e8", "#7209b7", "#008080", "#b45309"]
_MEMBERSHIP = "#8f99ad"
_RELATIONSHIP = "#f4a261"


def _pc_color(pc) -> str:
    if pc is None:
        return _NEUTRAL
    v = (pc.value if hasattr(pc, "value") else str(pc)).upper()
    if v == "HIGH":
        return _HIGH
    if v == "LOW":
        return _LOW
    return _NEUTRAL


def _short_label(text: str, max_len: int = 18) -> str:
    parts = [p for p in text.split() if p]
    if not parts:
        return text[:max_len]
    if len(parts) == 1:
        return parts[0][:max_len]
    label = f"{parts[0]} {parts[-1][0]}."
    return label if len(label) <= max_len else parts[0][:max_len]


def _group_label(name: str, max_len: int = 22) -> str:
    return name if len(name) <= max_len else name[: max_len - 1].rstrip() + "."


def _rel_label(rel_type) -> str:
    value = rel_type.value if hasattr(rel_type, "value") else str(rel_type)
    labels = {
        "COLLABORATION": "Colab.",
        "CROSS_GROUP": "Entre grupos",
        "MEMBERSHIP": "Membro",
    }
    return labels.get(value, value.replace("_", " ").title())


def render_hypergraph_html(
    groups: list,
    workers: list,
    memberships: dict[str, list[str]],
    relationships: list = None,
    filter_group_ids: Optional[list[str]] = None,
) -> str:
    """Render the hypergraph as an interactive bipartite PyVis network."""
    if not groups or not workers:
        return ""

    selected_groups = set(filter_group_ids or [])
    visible_group_ids = selected_groups or {g.id for g in groups}
    visible_workers: set[str] = set()
    for gid in visible_group_ids:
        visible_workers.update(memberships.get(gid, []))

    worker_map = {w.id: w for w in workers}
    group_color = {
        g.id: _GROUP_COLORS[i % len(_GROUP_COLORS)]
        for i, g in enumerate(groups)
    }

    worker_groups: dict[str, list[str]] = {}
    for gid, member_ids in memberships.items():
        for wid in member_ids:
            worker_groups.setdefault(wid, []).append(gid)

    group_name = {g.id: g.name for g in groups}

    net = Network(
        height="100vh",
        width="100%",
        directed=False,
        bgcolor=_BG,
        font_color=_TEXT,
        cdn_resources="in_line",
    )
    net.barnes_hut(gravity=-6500, central_gravity=0.22, spring_length=155)

    for idx, group in enumerate(groups):
        if group.id not in visible_group_ids:
            continue

        color = group_color[group.id]
        member_count = len(memberships.get(group.id, []))
        tooltip = (
            f"{group.name}\n"
            f"Projeto: {group.project_name}\n"
            f"Departamento: {group.department}\n"
            f"Membros: {member_count}\n"
            f"Qualidade base: {group.baseline_work_quality:.2f}\n"
            f"Resultado do projeto: {group.project_outcome_score:.2f}"
        )
        net.add_node(
            f"group:{group.id}",
            label=_group_label(group.name),
            shape="box",
            size=34,
            level=0,
            color={
                "background": color + "22",
                "border": color,
                "highlight": {"background": color + "44", "border": color},
            },
            borderWidth=3,
            font={"color": _TEXT, "size": 15, "face": "Inter", "bold": True, "multi": "html"},
            title=tooltip,
        )

    for wid in sorted(visible_workers):
        worker = worker_map.get(wid)
        if not worker:
            continue

        perf_color = _pc_color(worker.performance_class)
        groups_for_worker = [gid for gid in worker_groups.get(wid, []) if gid in visible_group_ids]
        is_bridge = len(worker_groups.get(wid, [])) >= 2
        group_labels = ", ".join(group_name.get(gid, gid) for gid in groups_for_worker)
        score = getattr(worker, "composite_score", 0.0) or 0.0
        tooltip = (
            f"{worker.name}\n"
            f"{worker.role} - {worker.department}\n"
            f"Score composto: {score:.3f}\n"
            f"Performance: {(worker.performance_class or 'NEUTRAL')}\n"
            f"Grupos visíveis: {group_labels or '-'}"
            + ("\nParticipa de múltiplos grupos" if is_bridge else "")
        )
        net.add_node(
            f"worker:{wid}",
            label=_short_label(worker.name),
            shape="dot",
            size=max(15, int(score * 42)),
            level=1,
            color={
                "background": perf_color + ("55" if is_bridge else "33"),
                "border": _RELATIONSHIP if is_bridge else perf_color,
                "highlight": {"background": perf_color + "77", "border": _RELATIONSHIP if is_bridge else perf_color},
            },
            borderWidth=4 if is_bridge else 2,
            font={"color": _TEXT, "size": 13, "face": "Inter", "strokeWidth": 3, "strokeColor": _BG},
            title=tooltip,
        )

    shown = set(net.get_nodes())
    for gid, member_ids in memberships.items():
        group_node = f"group:{gid}"
        if group_node not in shown:
            continue
        for wid in member_ids:
            worker_node = f"worker:{wid}"
            if worker_node not in shown:
                continue
            color = group_color.get(gid, _MEMBERSHIP)
            net.add_edge(
                group_node,
                worker_node,
                label="membro",
                width=1.8,
                color={"color": color + "88", "highlight": color},
                font={"size": 9, "color": "#5c667a", "strokeWidth": 3, "strokeColor": _BG, "align": "middle"},
                title=f"Membro de {group_name.get(gid, gid)}",
            )

    if relationships:
        for rel in relationships:
            source = f"worker:{rel.source_id}"
            target = f"worker:{rel.target_id}"
            if source not in shown or target not in shown:
                continue
            weight = getattr(rel, "weight", 0.1) or 0.1
            rel_type = getattr(rel, "rel_type", "RELATIONSHIP")
            rel_text = _rel_label(rel_type)
            net.add_edge(
                source,
                target,
                label=f"{weight:.2f}",
                width=max(1.0, weight * 3.5),
                dashes=True,
                color={"color": _RELATIONSHIP + "77", "highlight": _RELATIONSHIP},
                font={"size": 10, "color": "#465166", "strokeWidth": 3, "strokeColor": _BG, "align": "middle"},
                title=f"{rel_text}\nPeso: {weight:.2f}",
            )

    net.set_options(
        """
        {
          "nodes": { "shadow": { "enabled": true, "size": 8, "x": 1, "y": 2 } },
          "edges": { "smooth": { "type": "dynamic" }, "selectionWidth": 2 },
          "interaction": {
            "hover": true,
            "tooltipDelay": 80,
            "hideEdgesOnDrag": true,
            "navigationButtons": true,
            "keyboard": true
          },
          "physics": {
            "stabilization": { "iterations": 180 },
            "barnesHut": {
              "avoidOverlap": 0.35,
              "gravitationalConstant": -6500,
              "centralGravity": 0.22,
              "springLength": 155
            }
          }
        }
        """
    )

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


def render_hypergraph_png(
    groups: list,
    workers: list,
    memberships: dict[str, list[str]],
    relationships: list = None,
) -> str:
    if not groups or not workers:
        return ""

    worker_map = {w.id: w for w in workers}
    n_groups = len(groups)

    cols = min(3, n_groups)
    rows = math.ceil(n_groups / cols)

    cell_w  = 4.6
    cell_h  = 4.0
    gap_x   = 1.4
    gap_y   = 1.0

    slot_w = cell_w + gap_x
    slot_h = cell_h + gap_y

    fig_w = cols * slot_w + 0.8
    fig_h = rows * slot_h + 1.2

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.set_aspect("equal")
    ax.axis("off")

    group_centers: dict[str, tuple[float, float]] = {}

    for g_idx, group in enumerate(groups):
        col = g_idx % cols
        row = g_idx // cols

        slot_x = col * slot_w + gap_x / 2
        slot_y = -(row * slot_h + gap_y / 2)

        cx = slot_x + cell_w / 2
        cy = slot_y - cell_h / 2

        group_centers[group.id] = (cx, cy)

        border_color, fill_color = _GROUP_PALETTES[g_idx % len(_GROUP_PALETTES)]
        member_ids = memberships.get(group.id, getattr(group, "member_ids", []))

        shadow = FancyBboxPatch(
            (cx - cell_w / 2 + 0.06, cy - cell_h / 2 - 0.06),
            cell_w, cell_h,
            boxstyle="round,pad=0.12",
            linewidth=0, facecolor="#00000012", zorder=1,
        )
        ax.add_patch(shadow)

        rect = FancyBboxPatch(
            (cx - cell_w / 2, cy - cell_h / 2),
            cell_w, cell_h,
            boxstyle="round,pad=0.12",
            linewidth=1.8,
            edgecolor=border_color,
            facecolor=fill_color,
            zorder=2,
        )
        ax.add_patch(rect)

        ax.text(cx, cy + cell_h / 2 - 0.22, group.name,
                color=border_color, fontsize=9.5, fontweight="bold",
                ha="center", va="top", zorder=4)
        ax.text(cx, cy + cell_h / 2 - 0.52, group.project_name,
                color=border_color,
                fontsize=7.5, ha="center", va="top", zorder=4, alpha=0.7)

        n = len(member_ids)
        if n == 0:
            continue

        inner_cols = min(4, n)
        inner_rows = math.ceil(n / inner_cols)
        usable_w = cell_w - 0.9
        usable_h = cell_h - 1.1
        x_step = usable_w / max(inner_cols, 1)
        y_step = usable_h / max(inner_rows, 1)

        x_start = cx - usable_w / 2 + x_step / 2
        y_start = cy + cell_h / 2 - 0.85 - y_step / 2

        for w_idx, wid in enumerate(member_ids):
            w = worker_map.get(wid)
            if not w:
                continue
            wi = w_idx % inner_cols
            wj = w_idx // inner_cols
            wx = x_start + wi * x_step
            wy = y_start - wj * y_step

            node_color = _pc_color(w.performance_class)

            ax.add_patch(plt.Circle((wx + 0.03, wy - 0.03), 0.22,
                                     color="#00000018", zorder=3))
            ax.add_patch(plt.Circle((wx, wy), 0.22,
                                     color=node_color, zorder=4))
            ax.add_patch(plt.Circle((wx, wy), 0.08,
                                     color="white", alpha=0.4, zorder=5))

            short = w.name.split()[0]
            ax.text(wx, wy - 0.33, short,
                    color=_TEXT, fontsize=6.5, ha="center", va="top", zorder=5)

    # ── Inter-group edges ──────────────────────────────────────────────────────
    if relationships:
        worker_to_groups: dict[str, list[str]] = {}
        for gid, members in memberships.items():
            for wid in members:
                worker_to_groups.setdefault(wid, []).append(gid)

        inter: dict[tuple[str, str], float] = {}
        for rel in relationships:
            rel_weight = getattr(rel, "weight", 0.1)
            src_groups = worker_to_groups.get(rel.source_id, [])
            tgt_groups = worker_to_groups.get(rel.target_id, [])
            for sg in src_groups:
                for tg in tgt_groups:
                    if sg == tg:
                        continue
                    key = (min(sg, tg), max(sg, tg))
                    inter[key] = inter.get(key, 0.0) + rel_weight

        # Alternate arc direction per pair to avoid overlapping curves
        pair_list = sorted(inter.keys())
        for pair_idx, (gid1, gid2) in enumerate(pair_list):
            total_w = inter[(gid1, gid2)]
            if gid1 not in group_centers or gid2 not in group_centers:
                continue
            p1 = group_centers[gid1]
            p2 = group_centers[gid2]
            lw = 1.2 + min(total_w * 1.5, 4.5)
            rad = 0.22 if pair_idx % 2 == 0 else -0.22
            arrow = FancyArrowPatch(
                p1, p2,
                connectionstyle=f"arc3,rad={rad}",
                arrowstyle="-",
                linewidth=lw,
                color=_EDGE_COLOR,
                alpha=0.38,
                zorder=1,
            )
            ax.add_patch(arrow)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_items = [
        mpatches.Patch(color=_HIGH,    label="Alta performance"),
        mpatches.Patch(color=_NEUTRAL, label="Neutro"),
        mpatches.Patch(color=_LOW,     label="Baixa performance"),
        mpatches.Patch(color=_EDGE_COLOR, alpha=0.6, label="Relação entre grupos"),
    ]
    ax.legend(handles=legend_items, loc="lower center", ncol=4,
              fontsize=8, framealpha=0, labelcolor=_TEXT,
              bbox_to_anchor=(0.5, 0.0))

    ax.autoscale_view()
    plt.tight_layout(pad=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=_BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
