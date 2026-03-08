"""Mini SQL-like expression parser for rules conditions.

Supports: <, >, <=, >=, ==, !=, AND, OR, parentheses.
Literal "true" as the entire condition string = catch-all (always True).
Boolean literals true/false inside expressions for comparisons (has_children == true).

No eval(), no external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_TOKEN_PATTERN = re.compile(
    r"\s*(?:"
    r"(<=|>=|==|!=|<|>)"  # comparison operators
    r"|(\(|\))"  # parentheses
    r"|(\d+)"  # integer literals
    r"|(\w+)"  # identifiers / keywords (AND, OR, true, false, field names)
    r")\s*"
)

_COMPARISON_OPS: dict[str, Any] = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class ExpressionError(Exception):
    pass


@dataclass
class Token:
    kind: str  # "OP", "PAREN", "INT", "IDENT"
    value: str


def _tokenize(expr: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(expr):
        m = _TOKEN_PATTERN.match(expr, pos)
        if not m or m.start() != pos:
            raise ExpressionError(f"Unexpected character at position {pos}: '{expr[pos]}'")
        if m.group(1):
            tokens.append(Token("OP", m.group(1)))
        elif m.group(2):
            tokens.append(Token("PAREN", m.group(2)))
        elif m.group(3):
            tokens.append(Token("INT", m.group(3)))
        elif m.group(4):
            word = m.group(4)
            if word in ("AND", "OR"):
                tokens.append(Token(word, word))
            elif word == "true":
                tokens.append(Token("BOOL", "true"))
            elif word == "false":
                tokens.append(Token("BOOL", "false"))
            else:
                tokens.append(Token("IDENT", word))
        pos = m.end()
    return tokens


class _Parser:
    """Recursive descent parser: OR -> AND -> comparison -> atom."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _consume(self, kind: str | None = None) -> Token:
        tok = self._peek()
        if tok is None:
            raise ExpressionError("Unexpected end of expression")
        if kind and tok.kind != kind:
            raise ExpressionError(f"Expected {kind}, got {tok.kind} ({tok.value!r})")
        self._pos += 1
        return tok

    def parse(self) -> dict:
        node = self._parse_or()
        if self._pos < len(self._tokens):
            tok = self._tokens[self._pos]
            raise ExpressionError(f"Unexpected token after expression: {tok.value!r}")
        return node

    def _parse_or(self) -> dict:
        left = self._parse_and()
        while self._peek() and self._peek().kind == "OR":  # type: ignore[union-attr]
            self._consume("OR")
            right = self._parse_and()
            left = {"op": "OR", "left": left, "right": right}
        return left

    def _parse_and(self) -> dict:
        left = self._parse_comparison()
        while self._peek() and self._peek().kind == "AND":  # type: ignore[union-attr]
            self._consume("AND")
            right = self._parse_comparison()
            left = {"op": "AND", "left": left, "right": right}
        return left

    def _parse_comparison(self) -> dict:
        left = self._parse_atom()
        tok = self._peek()
        if tok and tok.kind == "OP":
            self._consume("OP")
            right = self._parse_atom()
            return {"op": tok.value, "left": left, "right": right}
        return left

    def _parse_atom(self) -> dict:
        tok = self._peek()
        if tok is None:
            raise ExpressionError("Unexpected end of expression")
        if tok.kind == "PAREN" and tok.value == "(":
            self._consume("PAREN")
            node = self._parse_or()
            self._consume("PAREN")
            return node
        if tok.kind == "INT":
            self._consume("INT")
            return {"type": "literal", "value": int(tok.value)}
        if tok.kind == "BOOL":
            self._consume("BOOL")
            return {"type": "literal", "value": tok.value == "true"}
        if tok.kind == "IDENT":
            self._consume("IDENT")
            return {"type": "field", "name": tok.value}
        raise ExpressionError(f"Unexpected token: {tok.value!r}")


def _build_ast(expr: str) -> dict:
    tokens = _tokenize(expr)
    if not tokens:
        raise ExpressionError("Empty expression")
    return _Parser(tokens).parse()


def _eval_node(node: dict, values: dict[str, Any]) -> Any:
    if "type" in node:
        if node["type"] == "literal":
            return node["value"]
        if node["type"] == "field":
            name = node["name"]
            if name not in values:
                raise ExpressionError(f"Unknown field: {name!r}")
            return values[name]

    op = node["op"]
    if op == "AND":
        return _eval_node(node["left"], values) and _eval_node(node["right"], values)
    if op == "OR":
        return _eval_node(node["left"], values) or _eval_node(node["right"], values)
    if op in _COMPARISON_OPS:
        left = _eval_node(node["left"], values)
        right = _eval_node(node["right"], values)
        return _COMPARISON_OPS[op](left, right)

    raise ExpressionError(f"Unknown operator: {op!r}")


def _collect_fields(node: dict) -> set[str]:
    if "type" in node:
        if node["type"] == "field":
            return {node["name"]}
        return set()
    fields: set[str] = set()
    if "left" in node:
        fields |= _collect_fields(node["left"])
    if "right" in node:
        fields |= _collect_fields(node["right"])
    return fields


# --- Public API ---


def parse_expression(expr: str) -> dict:
    """Parse expression string into AST. Raises ExpressionError on invalid syntax."""
    return _build_ast(expr)


def evaluate_expression(expr: str, values: dict[str, Any]) -> bool:
    """Evaluate an expression with given values. Catch-all "true" always returns True."""
    if expr.strip() == "true":
        return True
    ast = _build_ast(expr)
    return bool(_eval_node(ast, values))


def validate_expression(expr: str, allowed_fields: set[str]) -> None:
    """Validate expression syntax and field names. Raises ExpressionError on problems."""
    if expr.strip() == "true":
        return
    ast = _build_ast(expr)
    used_fields = _collect_fields(ast)
    unknown = used_fields - allowed_fields
    if unknown:
        raise ExpressionError(f"Unknown fields in expression: {unknown}")
