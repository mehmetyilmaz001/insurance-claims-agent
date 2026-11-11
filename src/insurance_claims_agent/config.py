"""Settings for the local model and checkpoint database."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model_url: str = "http://127.0.0.1:1234/v1"
    model_name: str = "gemma-4-e4b-it"
    database: Path = Path("intake.sqlite")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_url=os.getenv("LM_STUDIO_BASE_URL", cls.model_url),
            model_name=os.getenv("LM_STUDIO_MODEL", cls.model_name),
            database=Path(os.getenv("CLAIMS_DB_PATH", "intake.sqlite")),
        )
