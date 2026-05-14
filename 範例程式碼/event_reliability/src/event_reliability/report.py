from __future__ import annotations

import json
from pathlib import Path

from .pipeline import EventPipeline


def write_reliability_report(path: str | Path, pipeline: EventPipeline) -> Path:
    target = Path(path)
    target.write_text(
        json.dumps(pipeline.snapshot_report(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target
