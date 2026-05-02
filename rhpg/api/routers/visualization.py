from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from rhpg.api.dependencies import get_db
from rhpg.graph.builder import build_graphs
from rhpg.algorithms.classifier import run_full_analysis
from rhpg.storage.repository import GroupRepository

router = APIRouter()


@router.get("/network", response_class=HTMLResponse)
def get_network_html(
    groups: Optional[str] = None,
    db: Session = Depends(get_db),
):
    nx_graph, _, workers, group_list, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, group_list, relationships, memberships)
    classification = {r.worker_id: r.performance_class for r in results}

    filter_ids: Optional[list[str]] = None
    if groups:
        filter_ids = [g.strip() for g in groups.split(",") if g.strip()]

    from rhpg.visualization.network_plot import render_network_html
    return render_network_html(
        nx_graph.G,
        classification,
        memberships,
        group_list,
        filter_ids,
    )


@router.get("/hypergraph", response_class=HTMLResponse)
def get_hypergraph_html(
    group_filter: Optional[str] = Query(default=None, alias="groups"),
    db: Session = Depends(get_db),
):
    _, _, workers, group_list, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, group_list, relationships, memberships)
    result_map = {r.worker_id: r.performance_class for r in results}
    for w in workers:
        w.performance_class = result_map.get(w.id)

    filter_ids: Optional[list[str]] = None
    if group_filter:
        filter_ids = [g.strip() for g in group_filter.split(",") if g.strip()]

    from rhpg.visualization.hypergraph_plot import render_hypergraph_html
    return render_hypergraph_html(
        group_list,
        workers,
        memberships,
        relationships,
        filter_ids,
    )


@router.get("/performance-bar")
def get_performance_bar(db: Session = Depends(get_db)):
    _, _, workers, groups, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, groups, relationships, memberships)
    from rhpg.visualization.performance_charts import render_performance_bar
    return render_performance_bar(results)


@router.get("/score-scatter")
def get_score_scatter(db: Session = Depends(get_db)):
    _, _, workers, groups, relationships = build_graphs(db)
    memberships = GroupRepository(db).get_all_memberships()
    results = run_full_analysis(workers, groups, relationships, memberships)
    from rhpg.visualization.performance_charts import render_score_scatter
    return render_score_scatter(results)
