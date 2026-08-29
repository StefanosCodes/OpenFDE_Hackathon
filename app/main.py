from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api import v1_router
from app.core.database import connect, disconnect
from app.core.settings import settings
from app.integrations.github.client import GitHubAPIError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await connect()
    yield
    await disconnect()


app = FastAPI(title="OpenFDE Agent Knowledge API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(GitHubAPIError)
async def github_error_handler(_request: Request, exc: GitHubAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": {"message": "GitHub connection failed", "reason": str(exc)}},
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo", response_class=HTMLResponse)
async def demo() -> str:
    with open("app/static/demo.html", encoding="utf-8") as handle:
        return handle.read()
