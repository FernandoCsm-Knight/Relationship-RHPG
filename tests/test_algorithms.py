from rhpg.models.worker import Worker
from rhpg.models.group import Group
from rhpg.models.relationship import Relationship, RelationshipType
from rhpg.algorithms.delta_score import compute_group_quality_score, compute_worker_delta
from rhpg.algorithms.affinity import compute_affinity


def _worker(id: str, perf: float = 0.7, prof: float = 0.7, tenure: float = 2.0) -> Worker:
    return Worker(id=id, name=id, role="Eng", department="Eng",
                  proficiency_score=prof, individual_performance_score=perf, tenure_years=tenure)


def _group() -> Group:
    return Group(id="g1", name="G1", project_name="P1", department="Eng",
                 baseline_work_quality=0.6, project_outcome_score=0.7)


def _collab(src: str, tgt: str, freq: float = 0.8, quality: float = 0.8) -> Relationship:
    return Relationship(id=f"{src}-{tgt}", source_id=src, target_id=tgt,
                        rel_type=RelationshipType.COLLABORATION,
                        interaction_frequency=freq, collaboration_quality=quality)


def test_group_quality_empty_members():
    g = _group()
    score = compute_group_quality_score(g, [], [])
    assert score == g.baseline_work_quality


def test_group_quality_with_members():
    g = _group()
    members = [_worker("w1", 0.9), _worker("w2", 0.8), _worker("w3", 0.6)]
    rels = [_collab("w1", "w2"), _collab("w2", "w3")]
    score = compute_group_quality_score(g, members, rels)
    assert 0.0 <= score <= 1.0


def test_worker_delta_positive_contributor():
    g = _group()
    members = [_worker("w1", 0.9), _worker("w2", 0.4), _worker("w3", 0.4)]
    rels = [_collab("w1", "w2", 0.9, 0.9), _collab("w1", "w3", 0.9, 0.9)]
    delta = compute_worker_delta(members[0], g, members, rels)
    # w1 has high performance and good collab — delta should be positive
    assert delta > 0


def test_worker_delta_low_contributor():
    g = _group()
    members = [_worker("w1", 0.9), _worker("w2", 0.9), _worker("w3", 0.1)]
    rels = [_collab("w1", "w2", 0.9, 0.9)]
    delta = compute_worker_delta(members[2], g, members, rels)
    # w3 has low performance — removing them should not hurt the group much
    assert delta < 0.1


def test_affinity_no_edges():
    g = _group()
    w = _worker("w1")
    members = [w, _worker("w2"), _worker("w3")]
    score = compute_affinity(w, g, members, [])
    # No edges → edge_density=0 → affinity=0
    assert score == 0.0


def test_affinity_with_edges():
    g = _group()
    w = _worker("w1", tenure=5.0)
    others = [_worker("w2"), _worker("w3")]
    members = [w] + others
    rels = [_collab("w1", "w2", 1.0, 1.0), _collab("w1", "w3", 1.0, 1.0)]
    score = compute_affinity(w, g, members, rels)
    assert 0.0 < score <= 1.0
