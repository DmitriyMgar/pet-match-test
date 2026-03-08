from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.database import Database
from app.rules_engine import RulesEngine


def _get_engine(request: Request) -> RulesEngine:
    return request.app.state.engine


def _get_database(request: Request) -> Database:
    return request.app.state.database


Engine = Annotated[RulesEngine, Depends(_get_engine)]
DatabaseDep = Annotated[Database, Depends(_get_database)]
