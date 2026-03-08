from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_type TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    compatible BOOLEAN NOT NULL,
    risk_level TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    reasons_json TEXT NOT NULL,
    positives_json TEXT NOT NULL,
    alternatives_json TEXT NOT NULL,
    rules_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evaluations_created_at ON evaluations(created_at);
CREATE INDEX IF NOT EXISTS idx_evaluations_pet_type ON evaluations(pet_type);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._db

    async def save_evaluation(
        self,
        pet_type: str,
        profile: dict,
        compatible: bool,
        risk_level: str,
        risk_score: int,
        reasons: list[str],
        positives: list[str],
        alternatives: list[dict],
        rules_version: str,
    ) -> None:
        db = self._conn()
        await db.execute(
            """
            INSERT INTO evaluations
                (pet_type, profile_json, compatible, risk_level, risk_score,
                 reasons_json, positives_json, alternatives_json, rules_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pet_type,
                json.dumps(profile, ensure_ascii=False),
                compatible,
                risk_level,
                risk_score,
                json.dumps(reasons, ensure_ascii=False),
                json.dumps(positives, ensure_ascii=False),
                json.dumps(alternatives, ensure_ascii=False),
                rules_version,
            ),
        )
        await db.commit()

    async def get_evaluations(self, limit: int = 20, offset: int = 0) -> list[dict]:
        db = self._conn()
        cursor = await db.execute(
            """
            SELECT id, pet_type, profile_json, compatible, risk_level, risk_score,
                   reasons_json, positives_json, alternatives_json, rules_version, created_at
            FROM evaluations
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [_row_to_dict(row) for row in rows]

    async def get_stats(self) -> dict:
        db = self._conn()

        cursor = await db.execute("SELECT COUNT(*) FROM evaluations")
        total_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM evaluations WHERE compatible = 1")
        compatible_count = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM evaluations WHERE DATE(created_at) = DATE('now')"
        )
        today_count = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT pet_type, COUNT(*) as cnt FROM evaluations GROUP BY pet_type"
        )
        by_pet_type = {row[0]: row[1] for row in await cursor.fetchall()}

        return {
            "total_count": total_count,
            "compatible_count": compatible_count,
            "incompatible_count": total_count - compatible_count,
            "today_count": today_count,
            "by_pet_type": by_pet_type,
        }


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return {
        "id": row["id"],
        "pet_type": row["pet_type"],
        "profile": json.loads(row["profile_json"]),
        "compatible": bool(row["compatible"]),
        "risk_level": row["risk_level"],
        "risk_score": row["risk_score"],
        "reasons": json.loads(row["reasons_json"]),
        "positives": json.loads(row["positives_json"]),
        "alternatives": json.loads(row["alternatives_json"]),
        "rules_version": row["rules_version"],
        "created_at": row["created_at"],
    }
