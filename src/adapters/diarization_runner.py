from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set

from src.usecases.ports import DiarizationRunResult, DiarizationRunner


@dataclass
class _RunResult:
    ok: bool
    srt_path: Optional[Path]
    stdout: str
    stderr: str
    returncode: int


logger = logging.getLogger(__name__)


class DiarizationSubprocessRunner(DiarizationRunner):
    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path

    def run(self, audio_path: Path, timeout: float | None = None) -> DiarizationRunResult:
        audio_path = audio_path.resolve()
        cmd = [sys.executable, "diarize.py", "-a", str(audio_path)]
        pre_existing = self._discover_temp_outputs()

        try:
            completed = subprocess.run(  # noqa: S603,S607
                cmd,
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            self._cleanup_temp_outputs(pre_existing)
            return _RunResult(
                ok=False,
                srt_path=None,
                stdout=stdout,
                stderr=stderr,
                returncode=-1,
            )

        srt_path = audio_path.with_suffix(".srt")
        self._cleanup_temp_outputs(pre_existing)
        return _RunResult(
            ok=returncode == 0 and srt_path.exists(),
            srt_path=srt_path if srt_path.exists() else None,
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
        )

    def _discover_temp_outputs(self) -> Set[Path]:
        return {
            path
            for path in self._repo_path.glob("temp_outputs*")
            if path.is_dir()
        }

    def _cleanup_temp_outputs(self, pre_existing: Set[Path]) -> None:
        current = self._discover_temp_outputs()
        for orphan in current - pre_existing:
            try:
                shutil.rmtree(orphan)
            except FileNotFoundError:
                continue
            except Exception:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to remove diarization temp outputs",
                    exc_info=True,
                    extra={"path": str(orphan)},
                )
