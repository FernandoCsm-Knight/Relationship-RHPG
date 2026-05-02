import hypernetx as hnx

from rhpg.models.group import Group


class WorkerHypergraph:
    """
    Hypergraph where each Group is a hyperedge containing its member worker IDs.
    Enables multi-group membership analysis via HyperNetX.
    """

    def __init__(self) -> None:
        self.H: hnx.Hypergraph | None = None

    def build(self, groups: list[Group]) -> None:
        scenes = {g.id: set(g.member_ids) for g in groups if g.member_ids}
        try:
            self.H = hnx.Hypergraph(scenes)
        except Exception:
            # HyperNetX may be incompatible with the installed pandas version;
            # fall back to a plain membership index so the rest of the pipeline works.
            self.H = None
            self._fallback_memberships: dict[str, list[str]] = {}
            for gid, member_ids in scenes.items():
                for wid in member_ids:
                    self._fallback_memberships.setdefault(wid, []).append(gid)

    def get_node_memberships(self, worker_id: str) -> list[str]:
        """Group IDs that the worker belongs to."""
        if self.H is None:
            return getattr(self, "_fallback_memberships", {}).get(worker_id, [])
        if worker_id not in self.H.nodes:
            return []
        return list(self.H.nodes[worker_id].memberships)

    def get_hyperedge_size(self, group_id: str) -> int:
        if self.H is None or group_id not in self.H.edges:
            return 0
        return len(self.H.edges[group_id])

    def compute_s_centrality(self, s: int = 1) -> dict[str, float]:
        """
        s-betweenness centrality across overlapping hyperedges.
        Returns {worker_id: score}.
        """
        if self.H is None:
            return {}
        try:
            return hnx.algorithms.s_betweenness_centrality(self.H, s=s)
        except Exception:
            return {}
