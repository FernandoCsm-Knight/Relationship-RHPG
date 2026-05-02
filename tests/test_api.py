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


def test_create_worker_with_resume_and_list_candidates(client):
    worker = client.post("/workers/", json={
        "name": "Resume Worker",
        "role": "Data Scientist",
        "department": "Analytics",
        "proficiency_score": 0.82,
        "individual_performance_score": 0.78,
        "resume_text": "Built forecasting models and led analytics projects.",
        "skills": ["Python", "Forecasting", "SQL"],
        "past_projects": ["Demand forecasting", "Executive dashboard"],
    })
    assert worker.status_code == 201
    data = worker.json()
    assert data["skills"] == ["Python", "Forecasting", "SQL"]
    assert data["candidates"] == []

    listed = client.get("/workers/")
    assert listed.status_code == 200
    assert any(w["name"] == "Resume Worker" for w in listed.json())


def test_create_worker_with_optional_pdf_endpoint_without_file(client):
    resp = client.post("/workers/upload-pdf", data={
        "name": "Multipart Worker",
        "role": "Engineer",
        "department": "Engineering",
        "proficiency_score": "0.81",
        "individual_performance_score": "0.76",
        "tenure_years": "2.5",
        "resume_text": "API engineer with platform experience.",
        "skills": "Python, APIs\nSQL",
        "past_projects": "Billing API\nInternal developer portal",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["resume_text"] == "API engineer with platform experience."
    assert data["skills"] == ["Python", "APIs", "SQL"]
    assert data["past_projects"] == ["Billing API", "Internal developer portal"]


def test_candidate_crud_and_worker_summary(client):
    worker = client.post("/workers/", json={
        "name": "Candidate Worker",
        "role": "Backend Engineer",
        "department": "Engineering",
        "proficiency_score": 0.8,
        "individual_performance_score": 0.7,
    }).json()
    group = client.post("/groups/", json={
        "name": "Platform Team",
        "project_name": "Platform",
        "department": "Engineering",
        "baseline_work_quality": 0.7,
        "project_outcome_score": 0.75,
        "open_role_title": "Backend Engineer",
        "required_skills": ["Python", "APIs"],
    }).json()

    missing = client.post("/candidates/", json={
        "worker_id": "missing",
        "group_id": group["id"],
    })
    assert missing.status_code == 404

    created = client.post("/candidates/", json={
        "worker_id": worker["id"],
        "group_id": group["id"],
        "target_role": "Backend Engineer",
        "notes": "Strong API background.",
    })
    assert created.status_code == 201
    candidate = created.json()
    assert candidate["worker_name"] == "Candidate Worker"
    assert candidate["group_name"] == "Platform Team"

    updated = client.patch(f"/candidates/{candidate['id']}", json={"status": "SHORTLISTED"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "SHORTLISTED"

    worker_detail = client.get(f"/workers/{worker['id']}").json()
    assert worker_detail["candidates"][0]["group_name"] == "Platform Team"


def test_candidate_evaluate_with_mock(client, monkeypatch):
    from rhpg.models.schemas import CandidateAIEvaluationOut

    worker = client.post("/workers/", json={
        "name": "AI Candidate",
        "role": "ML Engineer",
        "department": "AI",
        "proficiency_score": 0.9,
        "individual_performance_score": 0.85,
        "skills": ["Python", "ML"],
    }).json()
    group = client.post("/groups/", json={
        "name": "AI Team",
        "project_name": "AI Platform",
        "department": "AI",
        "baseline_work_quality": 0.7,
        "project_outcome_score": 0.8,
        "required_skills": ["Python", "ML"],
    }).json()
    candidate = client.post("/candidates/", json={
        "worker_id": worker["id"],
        "group_id": group["id"],
    }).json()

    def fake_evaluate(worker_orm, group_orm, candidate_orm):
        return CandidateAIEvaluationOut(
            fit_score=0.88,
            recommendation="FIT",
            confidence=0.82,
            summary="Good technical match.",
            strengths=["Relevant ML work"],
            risks=["Confirm availability"],
            skill_matches=["Python", "ML"],
            skill_gaps=["MLOps depth"],
            interview_questions=["Describe a production ML system."],
        ), "mock-model"

    monkeypatch.setattr("rhpg.api.routers.candidates.evaluate_candidate_fit", fake_evaluate)
    resp = client.post(f"/candidates/{candidate['id']}/evaluate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fit_score"] == 0.88
    assert data["recommendation"] == "FIT"
    assert data["strengths"] == ["Relevant ML work"]


def test_candidate_evaluate_without_openai_key_returns_503(client, monkeypatch):
    worker = client.post("/workers/", json={
        "name": "No Key Candidate",
        "role": "Designer",
        "department": "Design",
        "proficiency_score": 0.7,
        "individual_performance_score": 0.7,
    }).json()
    group = client.post("/groups/", json={
        "name": "Design Team",
        "project_name": "Design System",
        "department": "Design",
        "baseline_work_quality": 0.6,
        "project_outcome_score": 0.7,
    }).json()
    candidate = client.post("/candidates/", json={
        "worker_id": worker["id"],
        "group_id": group["id"],
    }).json()

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post(f"/candidates/{candidate['id']}/evaluate")
    assert resp.status_code == 503


def test_openai_structured_output_schema_is_strict():
    from rhpg.models.schemas import CandidateAIEvaluationOut
    from rhpg.services.fit_evaluator import _strict_json_schema

    schema = _strict_json_schema(CandidateAIEvaluationOut.model_json_schema())
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"].keys())


def test_worker_ai_evaluation_with_mock(client, monkeypatch):
    from rhpg.models.schemas import WorkerAIEvaluationOut

    worker = client.post("/workers/", json={
        "name": "Context Worker",
        "role": "Tech Lead",
        "department": "Engineering",
        "proficiency_score": 0.88,
        "individual_performance_score": 0.82,
        "skills": ["Architecture", "Mentoring"],
        "resume_text": "Led platform teams and mentored engineers.",
    }).json()
    group = client.post("/groups/", json={
        "name": "Context Team",
        "project_name": "Platform Context",
        "department": "Engineering",
        "baseline_work_quality": 0.7,
        "project_outcome_score": 0.8,
        "member_ids": [worker["id"]],
        "team_context": "Critical platform team.",
    }).json()
    assert group["member_ids"] == [worker["id"]]

    def fake_evaluate(worker_obj, workers, groups, relationships, memberships, candidates):
        assert worker_obj.id == worker["id"]
        assert any(worker_obj.id in ids for ids in memberships.values())
        return WorkerAIEvaluationOut(
            overall_score=0.84,
            recommendation="KEEP_GROWING",
            confidence=0.79,
            summary="Strong internal contributor.",
            company_context_assessment="Has influence in engineering context.",
            team_context_assessment="Fits current platform context.",
            strengths=["Mentoring", "Architecture"],
            risks=["Watch overload"],
            growth_opportunities=["Broaden cross-team delegation"],
            suggested_actions=["Pair with product leadership"],
        ), "mock-model"

    monkeypatch.setattr("rhpg.api.routers.analysis.evaluate_worker_context", fake_evaluate)
    resp = client.post(f"/analysis/results/{worker['id']}/evaluate-ai")
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] == 0.84
    assert data["strengths"] == ["Mentoring", "Architecture"]


def test_worker_ai_evaluation_without_openai_key_returns_503(client, monkeypatch):
    worker = client.post("/workers/", json={
        "name": "No Key Worker",
        "role": "Engineer",
        "department": "Engineering",
        "proficiency_score": 0.7,
        "individual_performance_score": 0.7,
    }).json()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post(f"/analysis/results/{worker['id']}/evaluate-ai")
    assert resp.status_code == 503
