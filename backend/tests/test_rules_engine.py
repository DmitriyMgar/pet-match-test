import pytest
import yaml

from app.models import UserProfile
from app.rules_engine import RulesEngine, RulesEngineError


class TestEvaluateCompatible:
    """Good profile -> low risk, compatible, positives present."""

    def test_dog_compatible(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=80,
            has_children=False,
            monthly_budget_rub=30000,
            work_hours_per_day=8,
        )
        result = engine.evaluate("dog", profile)

        assert result.compatible is True
        assert result.risk_level == "low"
        assert result.risk_score == 0
        assert len(result.reasons) == 0
        assert len(result.positives) > 0

    def test_fish_compatible(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=30,
            has_children=True,
            monthly_budget_rub=10000,
            work_hours_per_day=10,
        )
        result = engine.evaluate("fish", profile)

        assert result.compatible is True
        assert result.risk_score < engine.config.scoring.thresholds.high


class TestEvaluateIncompatible:
    """Bad profile -> high risk, incompatible, reasons present."""

    def test_dog_incompatible_tiny_apartment_low_budget(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=10,
            has_children=True,
            monthly_budget_rub=2000,
            work_hours_per_day=12,
        )
        result = engine.evaluate("dog", profile)

        assert result.compatible is False
        assert result.risk_level == "high"
        assert result.risk_score >= engine.config.scoring.thresholds.high
        assert len(result.reasons) > 0

    def test_cat_incompatible_tiny_apartment_low_budget(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=5,
            has_children=False,
            monthly_budget_rub=2000,
            work_hours_per_day=8,
        )
        result = engine.evaluate("cat", profile)

        assert result.compatible is False
        assert len(result.reasons) > 0


class TestAlternatives:
    def test_incompatible_dog_gets_alternatives(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=10,
            has_children=False,
            monthly_budget_rub=2000,
            work_hours_per_day=12,
        )
        result = engine.evaluate("dog", profile)

        assert result.compatible is False
        alt_types = [a.pet_type for a in result.alternatives]
        assert "dog" not in alt_types
        for alt in result.alternatives:
            assert len(alt.why) > 0

    def test_compatible_pet_still_gets_alternatives(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=80,
            has_children=False,
            monthly_budget_rub=30000,
            work_hours_per_day=8,
        )
        result = engine.evaluate("dog", profile)
        assert result.compatible is True
        assert isinstance(result.alternatives, list)

    def test_alternatives_are_only_compatible(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=5,
            has_children=False,
            monthly_budget_rub=1000,
            work_hours_per_day=12,
        )
        result = engine.evaluate("dog", profile)

        thresholds = engine.config.scoring.thresholds
        for alt in result.alternatives:
            alt_result = engine.evaluate(alt.pet_type, profile)
            assert alt_result.risk_score < thresholds.high


class TestPositives:
    def test_positives_from_default_branches(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=80,
            has_children=False,
            monthly_budget_rub=30000,
            work_hours_per_day=8,
        )
        result = engine.evaluate("dog", profile)

        assert "Бюджет достаточный для большинства питомцев" in result.positives
        assert "Площадь жилья подходит для собаки" in result.positives
        assert "Бюджет достаточный для содержания собаки" in result.positives
        assert "Графика работы достаточно для ухода за собакой" in result.positives

    def test_mixed_reasons_and_positives(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=20,
            has_children=False,
            monthly_budget_rub=30000,
            work_hours_per_day=8,
        )
        result = engine.evaluate("dog", profile)

        assert len(result.reasons) > 0
        assert len(result.positives) > 0


class TestUnknownPetType:
    def test_raises_on_unknown(self, engine: RulesEngine):
        profile = UserProfile(
            apartment_size_m2=50,
            has_children=False,
            monthly_budget_rub=10000,
            work_hours_per_day=8,
        )
        with pytest.raises(RulesEngineError, match="Unknown pet type"):
            engine.evaluate("hamster", profile)


class TestGetPetTypes:
    def test_returns_all_types(self, engine: RulesEngine):
        pet_types = engine.get_pet_types()
        ids = {pt["id"] for pt in pet_types}
        assert ids == {"dog", "cat", "fish"}
        for pt in pet_types:
            assert "name" in pt


class TestSafeReload:
    def test_successful_reload(self, engine: RulesEngine, rules_yaml_path):
        rules_yaml_path.write_text(rules_yaml_path.read_text(encoding="utf-8"), encoding="utf-8")
        engine.reload()
        assert engine.config is not None

    def test_broken_yaml_keeps_old_rules(self, engine: RulesEngine, rules_yaml_path):
        old_version = engine.rules_version
        old_config = engine.config

        rules_yaml_path.write_text("invalid: yaml: [[[", encoding="utf-8")

        with pytest.raises((RulesEngineError, yaml.YAMLError, ValueError)):
            engine.reload()

        assert engine.rules_version == old_version
        assert engine.config is old_config

    def test_invalid_expression_keeps_old_rules(self, engine: RulesEngine, rules_yaml_path):
        old_version = engine.rules_version

        bad_data = {
            "scoring": {"thresholds": {"low": 5, "medium": 8, "high": 10}},
            "common_rules": [
                {
                    "name": "Bad rule",
                    "conditions": [
                        {
                            "condition": "nonexistent_field < 10",
                            "risk_score": 5,
                            "message": "bad",
                        }
                    ],
                }
            ],
            "pet_types": {
                "dog": {"name": "Dog", "rules": []},
            },
        }
        rules_yaml_path.write_text(yaml.dump(bad_data), encoding="utf-8")

        with pytest.raises(RulesEngineError):
            engine.reload()

        assert engine.rules_version == old_version


class TestValidateOnly:
    def test_valid_rules(self, engine: RulesEngine):
        result = engine.validate_only()
        assert result["valid"] is True

    def test_invalid_rules_on_disk(self, engine: RulesEngine, rules_yaml_path):
        rules_yaml_path.write_text("not: valid: rules:", encoding="utf-8")
        with pytest.raises((RulesEngineError, ValueError, yaml.YAMLError)):
            engine.validate_only()


class TestRulesVersion:
    def test_version_is_hex_string(self, engine: RulesEngine):
        assert isinstance(engine.rules_version, str)
        assert len(engine.rules_version) == 16
        int(engine.rules_version, 16)
