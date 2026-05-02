import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from rhpg.api.dependencies import get_db
from rhpg.models.schemas import WorkerCreate, WorkerOut, WorkerCandidateSummary
from rhpg.storage.repository import WorkerRepository, GroupRepository, CandidateRepository, load_json_list

router = APIRouter()


def _worker_to_out(worker, db: Session) -> WorkerOut:
    group_repo = GroupRepository(db)
    summaries: list[WorkerCandidateSummary] = []
    for candidate in CandidateRepository(db).get_all(worker_id=worker.id):
        group = group_repo.get_by_id(candidate.group_id)
        summaries.append(
            WorkerCandidateSummary(
                candidate_id=candidate.id,
                group_id=candidate.group_id,
                group_name=group.name if group else "Equipe removida",
                status=candidate.status,
                target_role=candidate.target_role,
                fit_score=candidate.fit_score,
                recommendation=candidate.recommendation,
            )
        )
    return WorkerOut(
        id=worker.id,
        name=worker.name,
        role=worker.role,
        department=worker.department,
        proficiency_score=worker.proficiency_score,
        individual_performance_score=worker.individual_performance_score,
        tenure_years=worker.tenure_years,
        pagerank_score=worker.pagerank_score,
        betweenness_centrality=worker.betweenness_centrality,
        composite_score=worker.composite_score,
        performance_class=worker.performance_class,
        email=worker.email,
        location=worker.location,
        seniority_level=worker.seniority_level,
        resume_text=worker.resume_text,
        skills=load_json_list(worker.skills_json),
        education=load_json_list(worker.education_json),
        certifications=load_json_list(worker.certifications_json),
        languages=load_json_list(worker.languages_json),
        past_projects=load_json_list(worker.past_projects_json),
        achievements_text=worker.achievements_text,
        availability_notes=worker.availability_notes,
        linkedin_url=worker.linkedin_url,
        portfolio_url=worker.portfolio_url,
        candidates=summaries,
    )


@router.post("/", response_model=WorkerOut, status_code=201)
def create_worker(data: WorkerCreate, db: Session = Depends(get_db)):
    return _worker_to_out(WorkerRepository(db).create(data), db)


def _parse_list_field(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


async def _extract_pdf_text(file: UploadFile | None) -> str:
    if not file or not file.filename:
        return ""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="resume_pdf must be a PDF file")
    content = await file.read()
    if not content:
        return ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read resume PDF") from exc


@router.post("/upload-pdf", response_model=WorkerOut, status_code=201)
async def create_worker_with_pdf(
    name: str = Form(...),
    role: str = Form(...),
    department: str = Form(...),
    proficiency_score: float = Form(...),
    individual_performance_score: float = Form(...),
    tenure_years: float = Form(0.0),
    email: str | None = Form(None),
    location: str | None = Form(None),
    seniority_level: str | None = Form(None),
    resume_text: str | None = Form(None),
    skills: str | None = Form(None),
    education: str | None = Form(None),
    certifications: str | None = Form(None),
    languages: str | None = Form(None),
    past_projects: str | None = Form(None),
    achievements_text: str | None = Form(None),
    availability_notes: str | None = Form(None),
    linkedin_url: str | None = Form(None),
    portfolio_url: str | None = Form(None),
    resume_pdf: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    pdf_text = await _extract_pdf_text(resume_pdf)
    combined_resume = "\n\n".join(part for part in [resume_text, pdf_text] if part)
    data = WorkerCreate(
        name=name,
        role=role,
        department=department,
        proficiency_score=proficiency_score,
        individual_performance_score=individual_performance_score,
        tenure_years=tenure_years,
        email=email,
        location=location,
        seniority_level=seniority_level,
        resume_text=combined_resume or None,
        skills=_parse_list_field(skills),
        education=_parse_list_field(education),
        certifications=_parse_list_field(certifications),
        languages=_parse_list_field(languages),
        past_projects=_parse_list_field(past_projects),
        achievements_text=achievements_text,
        availability_notes=availability_notes,
        linkedin_url=linkedin_url,
        portfolio_url=portfolio_url,
    )
    return _worker_to_out(WorkerRepository(db).create(data), db)


@router.get("/", response_model=list[WorkerOut])
def list_workers(db: Session = Depends(get_db)):
    return [_worker_to_out(worker, db) for worker in WorkerRepository(db).get_all()]


@router.get("/{worker_id}", response_model=WorkerOut)
def get_worker(worker_id: str, db: Session = Depends(get_db)):
    worker = WorkerRepository(db).get_by_id(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return _worker_to_out(worker, db)


@router.put("/{worker_id}", response_model=WorkerOut)
def update_worker(worker_id: str, data: WorkerCreate, db: Session = Depends(get_db)):
    updated = WorkerRepository(db).update(worker_id, data.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Worker not found")
    return _worker_to_out(updated, db)


@router.delete("/{worker_id}", status_code=204)
def delete_worker(worker_id: str, db: Session = Depends(get_db)):
    if not WorkerRepository(db).delete(worker_id):
        raise HTTPException(status_code=404, detail="Worker not found")
