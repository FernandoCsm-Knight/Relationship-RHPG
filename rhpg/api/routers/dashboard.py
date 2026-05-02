from pathlib import Path
import jinja2
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
    cache_size=0,
)

router = APIRouter()


def _render(name: str, **ctx) -> HTMLResponse:
    html = _env.get_template(name).render(**ctx)
    return HTMLResponse(content=html)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return _render("dashboard.html", page="dashboard")


@router.get("/network", response_class=HTMLResponse)
def network(request: Request):
    return _render("network.html", page="network")


@router.get("/hypergraph", response_class=HTMLResponse)
def hypergraph(request: Request):
    return _render("hypergraph.html", page="hypergraph")
