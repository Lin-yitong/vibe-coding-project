from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.game_router import router as game_router
from app.api.health_router import router as health_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(game_router)
