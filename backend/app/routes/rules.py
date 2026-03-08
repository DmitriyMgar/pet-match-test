from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ValidationError
from yaml import YAMLError

from app.dependencies import Engine
from app.rules_engine import RulesEngineError

router = APIRouter(prefix="/api")


class RulesUpload(BaseModel):
    yaml_content: str


@router.get("/pet-types")
async def pet_types(engine: Engine) -> list[dict[str, str]]:
    return engine.get_pet_types()


@router.get("/rules")
async def get_rules(engine: Engine) -> dict:
    return {
        "rules_version": engine.rules_version,
        **engine.config.model_dump(),
    }


@router.get("/rules/raw", response_class=PlainTextResponse)
async def get_rules_raw(engine: Engine) -> str:
    return engine.get_raw_yaml()


@router.post("/rules")
async def save_rules(body: RulesUpload, engine: Engine) -> dict:
    try:
        engine.save_yaml(body.yaml_content)
        return {"status": "ok", "rules_version": engine.rules_version}
    except (RulesEngineError, YAMLError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


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
