from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from app.expression_parser import ExpressionError, evaluate_expression, validate_expression
from app.models import (
    Alternative,
    EvaluationResponse,
    PetConfig,
    RiskLevel,
    Rule,
    RulesConfig,
    UserProfile,
)

_USER_PROFILE_FIELDS = set(UserProfile.model_fields.keys())


class RulesEngineError(Exception):
    pass


def _load_and_validate(path: Path) -> tuple[RulesConfig, str]:
    """Load YAML, parse via Pydantic, validate all expressions, compute hash."""
    raw = path.read_text(encoding="utf-8")
    rules_version = hashlib.sha256(raw.encode()).hexdigest()[:16]

    data = yaml.safe_load(raw)
    config = RulesConfig.model_validate(data)

    all_rules = list(config.common_rules)
    for pet_cfg in config.pet_types.values():
        all_rules.extend(pet_cfg.rules)

    for rule in all_rules:
        for cond in rule.conditions:
            try:
                validate_expression(cond.condition, _USER_PROFILE_FIELDS)
            except ExpressionError as e:
                rule_name = rule.name or "<unnamed>"
                msg = f"Rule '{rule_name}', condition '{cond.condition}': {e}"
                raise RulesEngineError(msg) from e

    return config, rules_version


def _evaluate_rules(rules: list[Rule], values: dict) -> tuple[int, list[str], list[str]]:
    """Evaluate a list of rules (if-else chains). Returns (total_score, reasons, positives)."""
    total_score = 0
    reasons: list[str] = []
    positives: list[str] = []

    for rule in rules:
        for cond in rule.conditions:
            if evaluate_expression(cond.condition, values):
                if cond.risk_score > 0:
                    total_score += cond.risk_score
                    reasons.append(cond.message)
                else:
                    positives.append(cond.message)
                break

    return total_score, reasons, positives


class RulesEngine:
    def __init__(self, rules_path: Path) -> None:
        self._path = rules_path
        self._config, self._rules_version = _load_and_validate(rules_path)

    @property
    def config(self) -> RulesConfig:
        return self._config

    @property
    def rules_version(self) -> str:
        return self._rules_version

    def reload(self) -> None:
        """Safe reload: load -> validate -> atomic swap. On error old rules stay."""
        new_config, new_version = _load_and_validate(self._path)
        self._config = new_config
        self._rules_version = new_version

    def validate_only(self) -> dict:
        """Dry-run validation of YAML on disk without applying."""
        _load_and_validate(self._path)
        return {"valid": True, "message": "Rules are valid"}

    def get_pet_types(self) -> list[dict[str, str]]:
        return [
            {"id": pet_id, "name": pet_cfg.name}
            for pet_id, pet_cfg in self._config.pet_types.items()
        ]

    def evaluate(self, pet_type: str, profile: UserProfile) -> EvaluationResponse:
        if pet_type not in self._config.pet_types:
            msg = f"Unknown pet type: {pet_type!r}"
            raise RulesEngineError(msg)

        values = profile.model_dump()
        thresholds = self._config.scoring.thresholds

        common_score, common_reasons, common_positives = _evaluate_rules(
            self._config.common_rules, values
        )
        pet_rules = self._config.pet_types[pet_type].rules
        pet_score, pet_reasons, pet_positives = _evaluate_rules(pet_rules, values)

        total_score = common_score + pet_score
        reasons = common_reasons + pet_reasons
        positives = common_positives + pet_positives

        risk_level = self._determine_risk_level(total_score, thresholds)
        compatible = total_score < thresholds.high

        alternatives = self._find_alternatives(pet_type, values, total_score) if True else []

        return EvaluationResponse(
            compatible=compatible,
            risk_level=risk_level,
            risk_score=total_score,
            reasons=reasons,
            positives=positives,
            alternatives=alternatives,
        )

    @staticmethod
    def _determine_risk_level(total_score: int, thresholds) -> RiskLevel:
        if total_score < thresholds.low:
            return RiskLevel.LOW
        if total_score < thresholds.medium:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    def _find_alternatives(
        self, original_pet_type: str, values: dict, original_score: int
    ) -> list[Alternative]:
        thresholds = self._config.scoring.thresholds
        candidates: list[tuple[int, str, PetConfig, list[str]]] = []

        for pet_id, pet_cfg in self._config.pet_types.items():
            if pet_id == original_pet_type:
                continue

            common_score, _, common_positives = _evaluate_rules(self._config.common_rules, values)
            pet_score, _, pet_positives = _evaluate_rules(pet_cfg.rules, values)
            alt_total = common_score + pet_score

            if alt_total >= thresholds.high:
                continue

            all_positives = common_positives + pet_positives
            why = all_positives or [f"Общий уровень риска ниже: {alt_total} vs {original_score}"]

            candidates.append((alt_total, pet_id, pet_cfg, why))

        candidates.sort(key=lambda c: c[0])
        return [
            Alternative(pet_type=pet_id, name=pet_cfg.name, why=why)
            for _, pet_id, pet_cfg, why in candidates[:3]
        ]
