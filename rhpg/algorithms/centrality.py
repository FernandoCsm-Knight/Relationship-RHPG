import networkx as nx
import pandas as pd


def compute_pagerank(G: nx.DiGraph, alpha: float = 0.85) -> dict[str, float]:
    if G.number_of_nodes() == 0:
        return {}
    return nx.pagerank(G, alpha=alpha, weight="weight")


def compute_betweenness(G: nx.DiGraph) -> dict[str, float]:
    if G.number_of_nodes() == 0:
        return {}
    return nx.betweenness_centrality(G, normalized=True, weight="weight")


def compute_eigenvector(G: nx.DiGraph) -> dict[str, float]:
    if G.number_of_nodes() == 0:
        return {}
    try:
        return nx.eigenvector_centrality_numpy(G, weight="weight")
    except (nx.PowerIterationFailedConvergence, nx.NetworkXException):
        n = G.number_of_nodes()
        return {node: 1.0 / n for node in G.nodes()}


def compute_all_centralities(G: nx.DiGraph) -> pd.DataFrame:
    """
    Returns DataFrame with columns [pagerank, betweenness, eigenvector]
    indexed by node ID.
    """
    pagerank = compute_pagerank(G)
    betweenness = compute_betweenness(G)
    eigenvector = compute_eigenvector(G)

    all_nodes = list(G.nodes())
    return pd.DataFrame(
        {
            "pagerank": [pagerank.get(n, 0.0) for n in all_nodes],
            "betweenness": [betweenness.get(n, 0.0) for n in all_nodes],
            "eigenvector": [eigenvector.get(n, 0.0) for n in all_nodes],
        },
        index=all_nodes,
    )
