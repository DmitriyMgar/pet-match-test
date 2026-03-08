from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies import DatabaseDep

router = APIRouter(prefix="/api")


@router.get("/stats")
async def get_stats(database: DatabaseDep) -> dict:
    return await database.get_stats()


@router.get("/evaluations")
async def get_evaluations(
    database: DatabaseDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return await database.get_evaluations(limit=limit, offset=offset)
