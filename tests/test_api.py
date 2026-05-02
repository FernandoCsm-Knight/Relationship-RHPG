def test_create_and_list_workers(client):
    resp = client.post("/workers/", json={
        "name": "Test Worker",
        "role": "Engineer",
        "department": "Engineering",
        "proficiency_score": 0.8,
        "individual_performance_score": 0.75,
        "tenure_years": 3.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Worker"
    worker_id = data["id"]

    resp = client.get("/workers/")
    assert resp.status_code == 200
    assert any(w["id"] == worker_id for w in resp.json())


def test_create_group_and_add_member(client):
    # Create worker first
    w = client.post("/workers/", json={
        "name": "Group Member",
        "role": "Designer",
        "department": "Design",
        "proficiency_score": 0.7,
        "individual_performance_score": 0.65,
    }).json()

    resp = client.post("/groups/", json={
        "name": "Test Group",
        "project_name": "Test Project",
        "department": "Design",
        "baseline_work_quality": 0.6,
        "project_outcome_score": 0.7,
        "member_ids": [w["id"]],
    })
    assert resp.status_code == 201
    group = resp.json()
    assert w["id"] in group["member_ids"]


def test_create_relationship(client):
    w1 = client.post("/workers/", json={
        "name": "W1", "role": "Engineer", "department": "Eng",
        "proficiency_score": 0.8, "individual_performance_score": 0.8,
    }).json()
    w2 = client.post("/workers/", json={
        "name": "W2", "role": "Engineer", "department": "Eng",
        "proficiency_score": 0.7, "individual_performance_score": 0.7,
    }).json()

    resp = client.post("/relationships/", json={
        "source_id": w1["id"],
        "target_id": w2["id"],
        "rel_type": "COLLABORATION",
        "interaction_frequency": 0.8,
        "collaboration_quality": 0.9,
    })
    assert resp.status_code == 201
    rel = resp.json()
    assert abs(rel["weight"] - 0.72) < 0.01


def test_analysis_run(client):
    # Seed minimal data
    w1 = client.post("/workers/", json={
        "name": "Ana", "role": "Tech Lead", "department": "Eng",
        "proficiency_score": 0.9, "individual_performance_score": 0.9, "tenure_years": 5.0,
    }).json()
    w2 = client.post("/workers/", json={
        "name": "Bob", "role": "Engineer", "department": "Eng",
        "proficiency_score": 0.5, "individual_performance_score": 0.4, "tenure_years": 1.0,
    }).json()

    client.post("/groups/", json={
        "name": "Core Team", "project_name": "Core", "department": "Eng",
        "baseline_work_quality": 0.6, "project_outcome_score": 0.7,
        "member_ids": [w1["id"], w2["id"]],
    })
    client.post("/relationships/", json={
        "source_id": w1["id"], "target_id": w2["id"],
        "rel_type": "COLLABORATION",
        "interaction_frequency": 0.9, "collaboration_quality": 0.85,
    })

    resp = client.post("/analysis/run")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 2
    for r in results:
        assert "composite_score" in r
        assert r["performance_class"] in ("HIGH", "NEUTRAL", "LOW")
