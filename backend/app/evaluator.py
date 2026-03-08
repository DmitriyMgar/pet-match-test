from __future__ import annotations

from app.database import Database
from app.models import EvaluationRequest, EvaluationResponse
from app.rules_engine import RulesEngine


async def evaluate_and_save(
    engine: RulesEngine,
    database: Database,
    request: EvaluationRequest,
) -> EvaluationResponse:
    result = engine.evaluate(request.pet_type, request.profile)

    await database.save_evaluation(
        pet_type=request.pet_type,
        profile=request.profile.model_dump(),
        compatible=result.compatible,
        risk_level=result.risk_level.value,
        risk_score=result.risk_score,
        reasons=result.reasons,
        positives=result.positives,
        alternatives=[alt.model_dump() for alt in result.alternatives],
        rules_version=engine.rules_version,
    )

    return result
