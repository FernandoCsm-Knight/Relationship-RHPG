from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from rhpg.storage.database import init_db
from rhpg.api.routers import workers, groups, relationships, analysis, visualization, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Relationship Hypergraph System",
    description="HR performance analysis via hypergraph theory",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")


app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"], include_in_schema=False)
app.include_router(workers.router, prefix="/workers", tags=["Workers"])
app.include_router(groups.router, prefix="/groups", tags=["Groups"])
app.include_router(relationships.router, prefix="/relationships", tags=["Relationships"])
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
app.include_router(visualization.router, prefix="/viz", tags=["Visualization"])
