from statistics import mean

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from rhpg.models.worker import Worker, PerformanceClass
from rhpg.models.group import Group
from rhpg.models.relationship import Relationship
from rhpg.models.schemas import WorkerAnalysisResult, ClassifyRequest
from rhpg.graph.nx_graph import WorkerGraph
from rhpg.graph.hypergraph import WorkerHypergraph
from rhpg.algorithms.delta_score import compute_all_deltas
from rhpg.algorithms.affinity import compute_affinity_matrix
from rhpg.algorithms.centrality import compute_all_centralities

DEFAULT_WEIGHTS: dict[str, float] = {
    "individual_performance": 0.30,
    "proficiency": 0.15,
    "pagerank": 0.20,
    "betweenness": 0.10,
    "mean_affinity": 0.10,
    "mean_delta": 0.15,
}


def _normalize_series(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series([0.5] * len(s), index=s.index)
    return (s - lo) / (hi - lo)


def compute_composite_scores(
    workers: list[Worker],
    centralities: pd.DataFrame,
    affinity_matrix: pd.DataFrame,
    delta_scores: dict[str, dict[str, float]],
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> dict[str, float]:
    wids = [w.id for w in workers]
    worker_map = {w.id: w for w in workers}

    ind_perf = pd.Series({w.id: w.individual_performance_score for w in workers})
    proficiency = pd.Series({w.id: w.proficiency_score for w in workers})

    pagerank = centralities.reindex(wids)["pagerank"].fillna(0.0) if "pagerank" in centralities.columns else pd.Series(0.0, index=wids)
    betweenness = centralities.reindex(wids)["betweenness"].fillna(0.0) if "betweenness" in centralities.columns else pd.Series(0.0, index=wids)

    mean_affinity = affinity_matrix.reindex(wids).mean(axis=1).fillna(0.0)

    raw_deltas = pd.Series(
        {
            wid: mean(vals.values()) if vals else 0.0
            for wid, vals in delta_scores.items()
        }
    ).reindex(wids).fillna(0.0)
    # Shift delta from [-1, +inf] toward [0, 1]
    mean_delta_norm = ((raw_deltas + 1.0) / 2.0).clip(0.0, 1.0)

    pagerank_norm = _normalize_series(pagerank)
    betweenness_norm = _normalize_series(betweenness)

    composite = (
        weights.get("individual_performance", 0.30) * ind_perf
        + weights.get("proficiency", 0.15) * proficiency
        + weights.get("pagerank", 0.20) * pagerank_norm
        + weights.get("betweenness", 0.10) * betweenness_norm
        + weights.get("mean_affinity", 0.10) * mean_affinity
        + weights.get("mean_delta", 0.15) * mean_delta_norm
    )

    return {wid: round(float(composite[wid]), 4) for wid in wids}


def classify_workers(
    composite_scores: dict[str, float],
    method: str = "percentile",
    high_threshold: float = 0.65,
    low_threshold: float = 0.40,
    n_clusters: int = 3,
) -> dict[str, PerformanceClass]:
    if not composite_scores:
        return {}

    scores = pd.Series(composite_scores)

    if method == "percentile":
        p70 = scores.quantile(0.70)
        p30 = scores.quantile(0.30)
        classes = scores.apply(
            lambda s: PerformanceClass.HIGH if s >= p70 else (PerformanceClass.LOW if s <= p30 else PerformanceClass.NEUTRAL)
        )
    elif method == "threshold":
        classes = scores.apply(
            lambda s: PerformanceClass.HIGH if s >= high_threshold else (PerformanceClass.LOW if s <= low_threshold else PerformanceClass.NEUTRAL)
        )
    else:  # kmeans
        k = min(n_clusters, len(scores))
        arr = scores.values.reshape(-1, 1)
        km = KMeans(n_clusters=k, random_state=42, n_init="auto").fit(arr)
        centers = km.cluster_centers_.flatten()
        rank_map = {int(np.argsort(centers)[i]): i for i in range(k)}
        # Map cluster rank to class: top → HIGH, bottom → LOW, rest → NEUTRAL
        def _to_class(label: int) -> PerformanceClass:
            r = rank_map[label]
            if r == k - 1:
                return PerformanceClass.HIGH
            if r == 0:
                return PerformanceClass.LOW
            return PerformanceClass.NEUTRAL

        classes = pd.Series(
            [_to_class(int(l)) for l in km.labels_], index=scores.index
        )

    return dict(classes)


def run_full_analysis(
    workers: list[Worker],
    groups: list[Group],
    relationships: list[Relationship],
    memberships: dict[str, list[str]],
    request: ClassifyRequest | None = None,
) -> list[WorkerAnalysisResult]:
    if not workers:
        return []

    req = request or ClassifyRequest()

    nx_graph = WorkerGraph()
    nx_graph.build(workers, groups, relationships)
    worker_subgraph = nx_graph.get_worker_subgraph()

    hyper = WorkerHypergraph()
    hyper.build(groups)

    delta_scores = compute_all_deltas(workers, groups, memberships, relationships)
    affinity_matrix = compute_affinity_matrix(workers, groups, memberships, relationships)
    centralities = compute_all_centralities(worker_subgraph)

    composite_scores = compute_composite_scores(
        workers, centralities, affinity_matrix, delta_scores, req.weights
    )
    classifications = classify_workers(
        composite_scores,
        method=req.method,
        high_threshold=req.high_threshold,
        low_threshold=req.low_threshold,
        n_clusters=req.n_clusters,
    )

    results: list[WorkerAnalysisResult] = []
    for worker in workers:
        wid = worker.id
        worker.composite_score = composite_scores.get(wid, 0.0)
        worker.performance_class = classifications.get(wid, PerformanceClass.NEUTRAL)
        worker.pagerank_score = float(
            centralities["pagerank"].get(wid, 0.0) if "pagerank" in centralities.columns else 0.0
        )
        worker.betweenness_centrality = float(
            centralities["betweenness"].get(wid, 0.0) if "betweenness" in centralities.columns else 0.0
        )
        worker.affinity_scores = {
            gid: float(affinity_matrix.at[wid, gid])
            for gid in affinity_matrix.columns
            if wid in affinity_matrix.index
        }

        results.append(
            WorkerAnalysisResult(
                worker_id=wid,
                name=worker.name,
                role=worker.role,
                department=worker.department,
                composite_score=worker.composite_score,
                performance_class=worker.performance_class,
                pagerank_score=worker.pagerank_score,
                betweenness_centrality=worker.betweenness_centrality,
                affinity_scores=worker.affinity_scores,
                delta_contributions=delta_scores.get(wid, {}),
            )
        )

    return results
