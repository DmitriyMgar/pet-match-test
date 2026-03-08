from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from yaml import YAMLError

from app.dependencies import Engine
from app.rules_engine import RulesEngineError

router = APIRouter(prefix="/api")


@router.get("/pet-types")
async def pet_types(engine: Engine) -> list[dict[str, str]]:
    return engine.get_pet_types()


@router.get("/rules")
async def get_rules(engine: Engine) -> dict:
    return {
        "rules_version": engine.rules_version,
        **engine.config.model_dump(),
    }


@router.post("/rules/reload")
async def reload_rules(engine: Engine) -> dict:
    try:
        engine.reload()
        return {"status": "ok", "rules_version": engine.rules_version}
    except (RulesEngineError, YAMLError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/rules/validate")
async def validate_rules(engine: Engine) -> dict:
    try:
        return engine.validate_only()
    except (RulesEngineError, YAMLError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
