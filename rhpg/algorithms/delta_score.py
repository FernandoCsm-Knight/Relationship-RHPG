from statistics import mean

from rhpg.models.worker import Worker
from rhpg.models.group import Group
from rhpg.models.relationship import Relationship, RelationshipType


def compute_group_quality_score(
    group: Group,
    members: list[Worker],
    relationships: list[Relationship],
) -> float:
    """
    Composite group quality score in [0, 1]:
      0.35 * mean individual performance of members
      0.30 * mean collaboration quality of intra-group edges
      0.20 * group.project_outcome_score
      0.15 * group.baseline_work_quality
    """
    if not members:
        return group.baseline_work_quality

    member_ids = {m.id for m in members}
    intra_edges = [
        r for r in relationships
        if r.source_id in member_ids
        and r.target_id in member_ids
        and r.rel_type == RelationshipType.COLLABORATION
    ]

    mean_perf = mean(m.individual_performance_score for m in members)
    mean_collab = mean(e.collaboration_quality for e in intra_edges) if intra_edges else 0.5

    score = (
        0.35 * mean_perf
        + 0.30 * mean_collab
        + 0.20 * group.project_outcome_score
        + 0.15 * group.baseline_work_quality
    )
    return round(score, 4)


def compute_worker_delta(
    worker: Worker,
    group: Group,
    all_members: list[Worker],
    relationships: list[Relationship],
) -> float:
    """
    Relative delta: (quality_with - quality_without) / quality_without.
    Returns value in roughly [-1, +inf]; negative means the worker harms quality.
    """
    score_with = compute_group_quality_score(group, all_members, relationships)
    members_without = [m for m in all_members if m.id != worker.id]
    score_without = compute_group_quality_score(group, members_without, relationships)

    if score_without == 0:
        return score_with
    return round((score_with - score_without) / score_without, 4)


def compute_all_deltas(
    workers: list[Worker],
    groups: list[Group],
    memberships: dict[str, list[str]],
    relationships: list[Relationship],
) -> dict[str, dict[str, float]]:
    """Returns {worker_id: {group_id: delta}} for every worker in each group."""
    worker_map = {w.id: w for w in workers}

    result: dict[str, dict[str, float]] = {w.id: {} for w in workers}
    for group in groups:
        member_ids = memberships.get(group.id, [])
        group_members = [worker_map[wid] for wid in member_ids if wid in worker_map]
        group.member_ids = member_ids

        for worker in group_members:
            delta = compute_worker_delta(worker, group, group_members, relationships)
            result[worker.id][group.id] = delta

    return result
