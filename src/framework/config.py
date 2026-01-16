from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ALLOWED_LANGUAGE_VALUES = {"turbo"}
ALLOWED_MODEL_VALUES = {"turbo", "large-v3"}
DEFAULT_TIMEOUT_SECONDS = 600.0
DEFAULT_LOG_LEVEL = "INFO"
SUBMODULE_RELATIVE_PATH = Path("external/whisper-diarization")
LOG_FILE_RELATIVE_PATH = Path("logs/app.jsonl")
JSON_OUTPUT_EXTENSION = ".json"


@dataclass(frozen=True)
class Settings:
    language_token: str
    model_size: str
    request_timeout_seconds: float
    fallback_enabled: bool
    log_level: str
    diarization_repo_path: Path
    logs_file_path: Path

    @property
    def fallback_language(self) -> str | None:
        # "turbo" acts as sentinel for auto language detection per requirements.
        if self.language_token.lower() == "turbo":
            return None
        return self.language_token


def load_settings(project_root: Path | None = None) -> Settings:
    load_dotenv()

    language = os.getenv("LANGUAGE", "turbo").strip()
    if language not in ALLOWED_LANGUAGE_VALUES:
        raise ValueError(
            f"LANGUAGE must be in {sorted(ALLOWED_LANGUAGE_VALUES)}, received '{language}'."
        )

    model_size = os.getenv("MODEL_SIZE", "large-v3").strip()
    if model_size not in ALLOWED_MODEL_VALUES:
        raise ValueError(
            f"MODEL_SIZE must be in {sorted(ALLOWED_MODEL_VALUES)}, received '{model_size}'."
        )

    timeout_raw = os.getenv("REQUEST_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)).strip()
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise ValueError("REQUEST_TIMEOUT_SECONDS must be numeric") from exc
    if timeout_seconds <= 0:
        raise ValueError("REQUEST_TIMEOUT_SECONDS must be positive")

    fallback_enabled = os.getenv("FALLBACK_ENABLED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    log_level = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip().upper()

    root = project_root or Path(__file__).resolve().parents[2]
    repo_path = (root / SUBMODULE_RELATIVE_PATH).resolve()
    if not repo_path.exists():
        raise FileNotFoundError(
            f"Expected diarization submodule at '{repo_path}' – ensure git submodules are initialised."
        )

    logs_file_path = (root / LOG_FILE_RELATIVE_PATH).resolve()
    logs_file_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        language_token=language,
        model_size=model_size,
        request_timeout_seconds=timeout_seconds,
        fallback_enabled=fallback_enabled,
        log_level=log_level,
        diarization_repo_path=repo_path,
        logs_file_path=logs_file_path,
    )
