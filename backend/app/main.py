from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.api import auth, projects, milestones, payments, reputation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Autonomous AI Payment & Project Agent — intelligent intermediary for freelancing",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(milestones.router, prefix="/milestones", tags=["Milestones"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(reputation.router, prefix="/reputation", tags=["Reputation"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.version}
