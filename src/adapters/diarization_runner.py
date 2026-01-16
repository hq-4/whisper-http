from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.usecases.ports import DiarizationRunResult, DiarizationRunner


@dataclass
class _RunResult:
    ok: bool
    srt_path: Optional[Path]
    stdout: str
    stderr: str
    returncode: int


class DiarizationSubprocessRunner(DiarizationRunner):
    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path

    def run(self, audio_path: Path, timeout: float | None = None) -> DiarizationRunResult:
        audio_path = audio_path.resolve()
        cmd = [sys.executable, "diarize.py", "-a", str(audio_path)]

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
            return _RunResult(
                ok=False,
                srt_path=None,
                stdout=stdout,
                stderr=stderr,
                returncode=-1,
            )

        srt_path = audio_path.with_suffix(".srt")
        return _RunResult(
            ok=returncode == 0 and srt_path.exists(),
            srt_path=srt_path if srt_path.exists() else None,
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
        )
