from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.dependencies import DatabaseDep, Engine
from app.evaluator import evaluate_and_save
from app.models import EvaluationRequest, EvaluationResponse
from app.rules_engine import RulesEngineError

router = APIRouter(prefix="/api")


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate(request: EvaluationRequest, engine: Engine, database: DatabaseDep):
    try:
        return await evaluate_and_save(engine, database, request)
    except RulesEngineError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
