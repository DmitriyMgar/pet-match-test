import os
from pathlib import Path

RULES_PATH: Path = Path(os.getenv("RULES_PATH", "rules.yaml"))
DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "data/petmatch.db"))
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
