from fastapi import APIRouter

from app.routers import agents, knowledge


v1_router = APIRouter(prefix="/v1")
v1_router.include_router(agents.router)
v1_router.include_router(knowledge.router)
