#!/usr/bin/env bash
set -euo pipefail

uv pip install -c external/whisper-diarization/constraints.txt \
  -r external/whisper-diarization/requirements.txt
uv pip install 'numpy>=2.2,<2.3'
