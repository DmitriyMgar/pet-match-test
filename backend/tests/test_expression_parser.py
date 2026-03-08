import pytest

from app.expression_parser import (
    ExpressionError,
    evaluate_expression,
    validate_expression,
)


class TestEvaluateExpression:
    def test_less_than(self):
        assert evaluate_expression("apartment_size_m2 < 30", {"apartment_size_m2": 20}) is True
        assert evaluate_expression("apartment_size_m2 < 30", {"apartment_size_m2": 30}) is False
        assert evaluate_expression("apartment_size_m2 < 30", {"apartment_size_m2": 50}) is False

    def test_greater_than(self):
        assert evaluate_expression("work_hours_per_day > 10", {"work_hours_per_day": 12}) is True
        assert evaluate_expression("work_hours_per_day > 10", {"work_hours_per_day": 8}) is False

    def test_equals(self):
        assert evaluate_expression("has_children == true", {"has_children": True}) is True
        assert evaluate_expression("has_children == false", {"has_children": True}) is False

    def test_not_equals(self):
        assert evaluate_expression("apartment_size_m2 != 30", {"apartment_size_m2": 20}) is True
        assert evaluate_expression("apartment_size_m2 != 30", {"apartment_size_m2": 30}) is False

    def test_less_equal(self):
        assert evaluate_expression("apartment_size_m2 <= 30", {"apartment_size_m2": 30}) is True
        assert evaluate_expression("apartment_size_m2 <= 30", {"apartment_size_m2": 31}) is False

    def test_greater_equal(self):
        assert evaluate_expression("work_hours_per_day >= 10", {"work_hours_per_day": 10}) is True
        assert evaluate_expression("work_hours_per_day >= 10", {"work_hours_per_day": 9}) is False

    def test_and_operator(self):
        values = {"apartment_size_m2": 20, "has_children": True}
        assert (
            evaluate_expression("apartment_size_m2 < 30 AND has_children == true", values) is True
        )
        values["has_children"] = False
        assert (
            evaluate_expression("apartment_size_m2 < 30 AND has_children == true", values) is False
        )

    def test_or_operator(self):
        assert (
            evaluate_expression(
                "apartment_size_m2 < 10 OR monthly_budget_rub < 3000",
                {"apartment_size_m2": 5, "monthly_budget_rub": 10000},
            )
            is True
        )
        assert (
            evaluate_expression(
                "apartment_size_m2 < 10 OR monthly_budget_rub < 3000",
                {"apartment_size_m2": 50, "monthly_budget_rub": 10000},
            )
            is False
        )

    def test_parentheses(self):
        values = {"apartment_size_m2": 50, "has_children": True, "monthly_budget_rub": 2000}
        expr = "(apartment_size_m2 < 30 AND has_children == true) OR monthly_budget_rub < 3000"
        assert evaluate_expression(expr, values) is True

        values["monthly_budget_rub"] = 10000
        assert evaluate_expression(expr, values) is False

    def test_catch_all_true(self):
        assert evaluate_expression("true", {}) is True
        assert evaluate_expression("  true  ", {}) is True

    def test_boolean_literal_in_comparison(self):
        assert evaluate_expression("has_children == true", {"has_children": True}) is True
        assert evaluate_expression("has_children == false", {"has_children": False}) is True

    def test_unknown_field_raises(self):
        with pytest.raises(ExpressionError, match="Unknown field"):
            evaluate_expression("nonexistent_field < 10", {"apartment_size_m2": 30})

    def test_invalid_syntax_raises(self):
        with pytest.raises(ExpressionError):
            evaluate_expression("< 10", {"x": 5})

    def test_empty_expression_raises(self):
        with pytest.raises(ExpressionError):
            evaluate_expression("", {"x": 5})


class TestValidateExpression:
    def test_valid_expression(self):
        validate_expression(
            "apartment_size_m2 < 30 AND has_children == true",
            {"apartment_size_m2", "has_children"},
        )

    def test_catch_all_true(self):
        validate_expression("true", set())

    def test_unknown_field(self):
        with pytest.raises(ExpressionError, match="Unknown fields"):
            validate_expression("bad_field < 10", {"apartment_size_m2"})

    def test_syntax_error(self):
        with pytest.raises(ExpressionError):
            validate_expression("apartment_size_m2 <", {"apartment_size_m2"})
