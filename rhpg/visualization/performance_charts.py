import plotly.graph_objects as go

from rhpg.models.schemas import WorkerAnalysisResult
from rhpg.models.worker import PerformanceClass

_CLASS_COLOR = {
    PerformanceClass.HIGH: "#2ECC71",
    PerformanceClass.NEUTRAL: "#95A5A6",
    PerformanceClass.LOW: "#E74C3C",
}


def render_performance_bar(results: list[WorkerAnalysisResult]) -> dict:
    sorted_r = sorted(results, key=lambda r: r.composite_score, reverse=True)
    names = [r.name for r in sorted_r]
    colors = [_CLASS_COLOR[r.performance_class] for r in sorted_r]

    fig = go.Figure(
        data=[
            go.Bar(name="Composite Score", x=names, y=[r.composite_score for r in sorted_r], marker_color=colors),
            go.Bar(name="PageRank", x=names, y=[r.pagerank_score for r in sorted_r], marker_color="#3498DB"),
        ]
    )
    fig.update_layout(
        barmode="group",
        title=dict(text="Worker Performance Scores", x=0.02, xanchor="left", y=0.96),
        xaxis_title="Worker",
        yaxis_title="Score",
        legend_title="Metric",
        margin=dict(t=56, b=64, l=54, r=24),
        template="plotly_dark",
    )
    return fig.to_dict()


def render_score_scatter(results: list[WorkerAnalysisResult]) -> dict:
    fig = go.Figure()

    for perf_class, color in _CLASS_COLOR.items():
        subset = [r for r in results if r.performance_class == perf_class]
        if not subset:
            continue
        deltas = [
            sum(r.delta_contributions.values()) / max(1, len(r.delta_contributions))
            for r in subset
        ]
        fig.add_trace(
            go.Scatter(
                x=[r.pagerank_score for r in subset],
                y=[r.composite_score for r in subset],
                mode="markers+text",
                name=perf_class.value,
                marker=dict(color=color, size=[max(8, d * 20 + 10) for d in deltas]),
                text=[r.name for r in subset],
                textposition="top center",
                hovertemplate="<b>%{text}</b><br>PageRank: %{x:.4f}<br>Composite: %{y:.4f}",
            )
        )

    fig.update_layout(
        title=dict(text="PageRank vs Composite Score", x=0.02, xanchor="left", y=0.96),
        xaxis_title="PageRank Score (Network Influence)",
        yaxis_title="Composite Score",
        margin=dict(t=56, b=64, l=54, r=24),
        template="plotly_dark",
    )
    return fig.to_dict()
