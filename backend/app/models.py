from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

# --- Domain models ---


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserProfile(BaseModel):
    apartment_size_m2: int = Field(ge=1, le=500)
    has_children: bool
    monthly_budget_rub: int = Field(ge=0, le=1_000_000)
    work_hours_per_day: int = Field(ge=0, le=24)


class EvaluationRequest(BaseModel):
    pet_type: str
    profile: UserProfile


class Alternative(BaseModel):
    pet_type: str
    name: str
    why: list[str]


class EvaluationResponse(BaseModel):
    compatible: bool
    risk_level: RiskLevel
    risk_score: int
    reasons: list[str]
    positives: list[str]
    alternatives: list[Alternative]


# --- Rules models ---


class Condition(BaseModel):
    condition: str
    risk_score: int = Field(ge=0, le=10)
    message: str


class Rule(BaseModel):
    name: str | None = None
    conditions: list[Condition]


class ScoringThresholds(BaseModel):
    low: int
    medium: int
    high: int

    @model_validator(mode="after")
    def check_order(self) -> ScoringThresholds:
        if not (self.low < self.medium < self.high):
            msg = (
                f"Thresholds must satisfy low < medium < high, "
                f"got {self.low}, {self.medium}, {self.high}"
            )
            raise ValueError(msg)
        return self


class ScoringConfig(BaseModel):
    thresholds: ScoringThresholds


class PetConfig(BaseModel):
    name: str
    rules: list[Rule]


class RulesConfig(BaseModel):
    scoring: ScoringConfig
    common_rules: list[Rule]
    pet_types: dict[str, PetConfig]
