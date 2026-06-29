from fastapi import FastAPI

from lineup.api.router import router

app = FastAPI(
    title="Lineup API",
    description="Generates water polo lineup documents.",
    version="0.1.0",
)

app.include_router(router)
