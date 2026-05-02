from dataclasses import asdict
import networkx as nx

from rhpg.models.worker import Worker
from rhpg.models.group import Group
from rhpg.models.relationship import Relationship, RelationshipType


class WorkerGraph:
    """Directed weighted graph over workers and groups."""

    def __init__(self) -> None:
        self.G: nx.DiGraph = nx.DiGraph()

    def build(
        self,
        workers: list[Worker],
        groups: list[Group],
        relationships: list[Relationship],
    ) -> None:
        self.G.clear()
        for w in workers:
            self.G.add_node(w.id, node_type="worker", **asdict(w))
        for g in groups:
            self.G.add_node(g.id, node_type="group", **asdict(g))
        for r in relationships:
            self.G.add_edge(
                r.source_id,
                r.target_id,
                weight=r.weight,
                rel_type=r.rel_type.value,
            )

    def get_worker_subgraph(self) -> nx.DiGraph:
        """Subgraph containing only worker→worker edges."""
        worker_nodes = [
            n for n, d in self.G.nodes(data=True) if d.get("node_type") == "worker"
        ]
        return self.G.subgraph(worker_nodes).copy()

    def get_bipartite_subgraph(self) -> nx.DiGraph:
        """Subgraph containing only MEMBERSHIP edges (worker↔group)."""
        membership_edges = [
            (u, v)
            for u, v, d in self.G.edges(data=True)
            if d.get("rel_type") == RelationshipType.MEMBERSHIP.value
        ]
        nodes = {n for edge in membership_edges for n in edge}
        sub = self.G.subgraph(nodes).copy()
        return sub
