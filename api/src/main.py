from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.errors import AppError, app_error_handler
from src.routers import episodes, feeds, podcasts, rss

app = FastAPI(title="Podcast UI Editor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(feeds.router)
app.include_router(podcasts.router)
app.include_router(episodes.router)
app.include_router(rss.router)
