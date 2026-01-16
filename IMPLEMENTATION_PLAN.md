# Implementation Plan

## Initial Understanding (Round v1)
- Project bootstrapping phase: awaiting user responses to clarification questions captured in `docs/v1.md` before drafting technical design or writing code.
  
## Clarifications from Round v1 Responses
- **Audio ingestion**: Single trusted client passes absolute path to existing audio file on shared server. Need to validate diarization output location matches audio directory; add regression test to confirm behavior. No format, duration, or size constraints required.
- **Output schema expectations**: JSON response must carry usual transcript data plus an explicit flag indicating whether diarization or faster-whisper produced the result. Full field requirements pending deeper review of sample SRT and subsequent discussion.
- **Fallback strategy**: Primary diarization pipeline may fail catastrophically on low-quality audio; on any failure (exception/exit) invoke single fallback attempt via faster-whisper with no retry/backoff loop beyond that.
- **Operational profile**: Service will run single-threaded for one co-located client on the same bare-metal host; no concurrency goals beyond serialized handling. Progress/status reporting approach remains undecided.
- **Environment & configuration**: Deployment target offers 32 GB RAM, 16 CPU cores, and an RTX 3080 (10 GB). Language and model size must be configurable via `.env`/environment variables exposed through UV-managed runtime.

## Clarifications from Round v2 Responses
- **Transcript JSON schema**: Output must be a single JSON file per request (named `<source>.json`), containing segment sequence numbers, timestamps, speaker labels (pending format decision), text, and high-level metadata; design should remain readable for humans and machine-consumable for Ollama.
- **Fallback provenance**: Diarization is treated as pass/fail. On failure, fall back immediately to faster-whisper; if fallback also fails, return structured error `{type: "diarization", message: "diarization failed"}` and log original failure reason.
- **Synchronous processing window**: HTTP endpoint remains blocking, with full response expected under 10 minutes. Introduce configurable timeout (default 10 minutes) via `.env`.
- **Configuration validation**: Enforce strict whitelists for language and model-size environment values; no additional tuning knobs required.
- **Artifact retention & logging**: No archival/cleanup automation necessary beyond default behavior. Maintain standard dual-sink logging; include diarization failure reason when fallback triggers.
- **Repository integration**: Whisper diarization dependency must be consumed as a git submodule pinned to latest upstream commit, not via PyPI.

## Clarifications from Round v3 Responses
- **Speaker handling**: Extract speaker labels into a dedicated `speaker` field (e.g., `"Speaker 2"`) while keeping caption text free of the prefix; retain human-readable labels rather than numeric remapping to support downstream LLM substitution.
- **Metadata scope**: Aggregate metadata limited to `total_duration` and `speaker_count`, with provenance flag stored once at the top level.
- **Error surfaces**: Error responses remain `{type: "diarization", message: "diarization failed"}` without extra detail field; detailed exception plus diarization subprocess stdout/stderr captured in logs via RichHandler.
- **Config whitelists**: Restrict environment-configurable model identifiers to `turbo` and `large-v3`; timeout remains `.env`-only (no per-request overrides).
- **Submodule operations**: Deployment tooling will handle `git submodule update --init --recursive`. Project should document and pin a specific commit hash for the diarization submodule to guarantee reproducibility.

## Clarifications from Round v4 Responses
- **API surface**: Expose `POST /transcribe` endpoint accepting JSON body `{ "audio_path": "..." }`. Respond directly with transcript JSON object (no envelope).
- **Security posture**: Service operates on trusted internal network; no auth or directory allow-list enforcement required.
- **Process execution**: Invoke diarization via CLI (`python diarize.py -a <audio_path>`) using `subprocess`. Allow downstream tools (including faster-whisper) to auto-detect GPU availability.
- **Testing strategy**: Provide integration tests that execute the submodule pipeline end-to-end (likely guarded for runtime cost) plus committed small audio fixtures to support repeatable test runs.
- **Documentation & reproducibility**: Pin submodule commit hash within `.gitmodules`; augment README with setup/run instructions (UV sync, submodule init, env config) instead of separate runbook.

## Clarifications from Round v5 Responses
- **Timestamps & duration**: Emit segment timestamps as floating-point seconds; represent `total_duration` as numeric seconds. When diarization fails, report `speaker_count` as `0`.
- **Fallback defaults**: Use faster-whisper `large-v3` model for fallback runs. Successful fallback only produces JSON output; no extra artifact persistence required.
- **Integration testing**: Include long-running integration coverage executing the real diarization submodule with both high-quality and failure-case fixtures; target ≤10 minutes runtime for any test exercising the full pipeline. Clarify marker usage to balance default vs. opt-in execution.
- **Fixtures**: Store ~10-minute audio fixtures (covering pass/fail scenarios) under `tests/fixtures/audio/` with repo size considerations acknowledged.
- **Operational docs**: README will document environment activation, dependency install (`pip install -c constraints.txt -r requirements.txt` via UV equivalent), submodule sync, and guidance for updating the pinned submodule hash.

## Clarifications from Round v6 Responses
- **Integration cadence**: Run diarization integration tests by default in `uv run -m pytest -q`, leveraging 2-minute curated samples (with potential future low-quality trims) to keep runtime manageable.
- **Submodule policy**: Keep upstream diarization CLI scripts untouched; build external orchestration without modifying submodule contents.
- **Dependency install**: Use UV to replicate upstream install command (`uv pip install -c constraints.txt -r requirements.txt`) during setup, ensuring consistency with constraints while staying within UV-managed environment.
