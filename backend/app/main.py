from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, DATABASE_PATH, RULES_PATH
from app.database import Database
from app.routes import evaluate, rules, stats
from app.rules_engine import RulesEngine


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    engine = RulesEngine(RULES_PATH)
    database = Database(DATABASE_PATH)
    await database.connect()

    application.state.engine = engine
    application.state.database = database

    yield

    await database.close()


app = FastAPI(title="PetMatch", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluate.router)
app.include_router(rules.router)
app.include_router(stats.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
