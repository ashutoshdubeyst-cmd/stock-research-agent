from fastapi import APIRouter

from app.api.routes import agent, health, stock


api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(stock.router)
api_router.include_router(agent.router)