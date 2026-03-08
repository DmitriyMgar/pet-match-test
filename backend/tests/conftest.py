from pathlib import Path

import pytest
import yaml

from app.rules_engine import RulesEngine

RULES_DATA = {
    "scoring": {"thresholds": {"low": 5, "medium": 8, "high": 10}},
    "common_rules": [
        {
            "name": "Бюджет (общий)",
            "conditions": [
                {
                    "condition": "monthly_budget_rub < 3000",
                    "risk_score": 5,
                    "message": "Бюджет ниже минимума для содержания любого питомца",
                },
                {
                    "condition": "monthly_budget_rub < 5000",
                    "risk_score": 2,
                    "message": "Бюджет на нижней границе для большинства питомцев",
                },
                {
                    "condition": "true",
                    "risk_score": 0,
                    "message": "Бюджет достаточный для большинства питомцев",
                },
            ],
        }
    ],
    "pet_types": {
        "dog": {
            "name": "Собака",
            "rules": [
                {
                    "name": "Пространство",
                    "conditions": [
                        {
                            "condition": "apartment_size_m2 < 15",
                            "risk_score": 8,
                            "message": "Критически мало пространства для собаки",
                        },
                        {
                            "condition": "apartment_size_m2 < 30 AND has_children == true",
                            "risk_score": 6,
                            "message": "Маленькая квартира с детьми — риск для крупной собаки",
                        },
                        {
                            "condition": "apartment_size_m2 < 30",
                            "risk_score": 3,
                            "message": "Маловато пространства для собаки",
                        },
                        {
                            "condition": "true",
                            "risk_score": 0,
                            "message": "Площадь жилья подходит для собаки",
                        },
                    ],
                },
                {
                    "name": "Бюджет на собаку",
                    "conditions": [
                        {
                            "condition": "monthly_budget_rub < 15000",
                            "risk_score": 4,
                            "message": "Бюджет ниже рекомендуемого для содержания собаки",
                        },
                        {
                            "condition": "true",
                            "risk_score": 0,
                            "message": "Бюджет достаточный для содержания собаки",
                        },
                    ],
                },
                {
                    "name": "Время и внимание",
                    "conditions": [
                        {
                            "condition": "work_hours_per_day > 10",
                            "risk_score": 3,
                            "message": "Собаке не будет хватать внимания при таком графике",
                        },
                        {
                            "condition": "true",
                            "risk_score": 0,
                            "message": "Графика работы достаточно для ухода за собакой",
                        },
                    ],
                },
            ],
        },
        "cat": {
            "name": "Кошка",
            "rules": [
                {
                    "name": "Бюджет на кошку",
                    "conditions": [
                        {
                            "condition": "monthly_budget_rub < 8000",
                            "risk_score": 4,
                            "message": "Бюджет ниже рекомендуемого для кошки",
                        },
                        {
                            "condition": "true",
                            "risk_score": 0,
                            "message": "Бюджет достаточный для кошки",
                        },
                    ],
                },
                {
                    "name": "Пространство",
                    "conditions": [
                        {
                            "condition": "apartment_size_m2 < 10",
                            "risk_score": 5,
                            "message": "Слишком мало пространства даже для кошки",
                        },
                        {
                            "condition": "true",
                            "risk_score": 0,
                            "message": "Площадь жилья подходит для кошки",
                        },
                    ],
                },
            ],
        },
        "fish": {
            "name": "Рыбки",
            "rules": [
                {
                    "name": "Бюджет на аквариум",
                    "conditions": [
                        {
                            "condition": "monthly_budget_rub < 3000",
                            "risk_score": 3,
                            "message": "Бюджет может быть недостаточен для аквариума",
                        },
                        {
                            "condition": "true",
                            "risk_score": 0,
                            "message": "Бюджет достаточный для аквариума",
                        },
                    ],
                }
            ],
        },
    },
}


@pytest.fixture()
def rules_yaml_path(tmp_path: Path) -> Path:
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.dump(RULES_DATA, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture()
def engine(rules_yaml_path: Path) -> RulesEngine:
    return RulesEngine(rules_yaml_path)
