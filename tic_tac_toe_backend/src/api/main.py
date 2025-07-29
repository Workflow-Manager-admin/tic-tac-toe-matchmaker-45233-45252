from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

tags_metadata = [
    {
        "name": "auth",
        "description": "User registration and login"
    },
    {
        "name": "games",
        "description": "Start a new game or make moves"
    },
    {
        "name": "leaderboard",
        "description": "Get leaderboard stats"
    },
    {
        "name": "history",
        "description": "Match history for games"
    }
]

app = FastAPI(
    title="Tic Tac Toe Backend API",
    description="Backend API for fullstack Tic Tac Toe game with user authentication, gameplay, leaderboard, history, and real-time board updates.",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["health"])
def health_check():
    """Healthcheck endpoint for service availability."""
    return {"message": "Healthy"}

app.include_router(router)

# WebSocket route is handled in routes.py and documented for OpenAPI
