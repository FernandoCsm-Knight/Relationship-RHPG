from statistics import mean

import pandas as pd

from rhpg.models.worker import Worker
from rhpg.models.group import Group
from rhpg.models.relationship import Relationship


def compute_affinity(
    worker: Worker,
    group: Group,
    members: list[Worker],
    relationships: list[Relationship],
) -> float:
    """
    affinity(w, G) = edge_density * mean_collab_quality * tenure_bonus

    edge_density  = edges between w and G members / max(1, |G| - 1)
    tenure_bonus  = min(1.0, tenure_years / 5.0)
    """
    other_member_ids = {m.id for m in members if m.id != worker.id}
    if not other_member_ids:
        return 0.0

    relevant = [
        r for r in relationships
        if (r.source_id == worker.id and r.target_id in other_member_ids)
        or (r.target_id == worker.id and r.source_id in other_member_ids)
    ]

    edge_density = len(relevant) / max(1, len(other_member_ids))
    mean_collab = mean(r.collaboration_quality for r in relevant) if relevant else 0.5
    tenure_bonus = min(1.0, worker.tenure_years / 5.0)

    affinity = edge_density * mean_collab * tenure_bonus
    return round(min(1.0, max(0.0, affinity)), 4)


def compute_affinity_matrix(
    workers: list[Worker],
    groups: list[Group],
    memberships: dict[str, list[str]],
    relationships: list[Relationship],
) -> pd.DataFrame:
    """
    DataFrame shape (n_workers × n_groups).
    Rows = worker IDs, Columns = group IDs.
    Non-members receive 0.0.
    """
    worker_map = {w.id: w for w in workers}
    worker_ids = [w.id for w in workers]
    group_ids = [g.id for g in groups]

    data: dict[str, list[float]] = {gid: [0.0] * len(workers) for gid in group_ids}
    worker_index = {wid: i for i, wid in enumerate(worker_ids)}

    for group in groups:
        member_ids = memberships.get(group.id, group.member_ids)
        group_members = [worker_map[wid] for wid in member_ids if wid in worker_map]
        for worker in group_members:
            score = compute_affinity(worker, group, group_members, relationships)
            data[group.id][worker_index[worker.id]] = score

    return pd.DataFrame(data, index=worker_ids)
