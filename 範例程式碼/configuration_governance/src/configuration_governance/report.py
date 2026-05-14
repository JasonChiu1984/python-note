from __future__ import annotations

import json
from pathlib import Path

from .loader import LoadedConfig


def write_config_report(target: Path, loaded: LoadedConfig) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": loaded.config.schema_version,
        "precedence": loaded.precedence,
        "source_map": loaded.source_map,
        "effective_values": loaded.effective_values,
        "redacted_fields": sorted(loaded.redacted_fields),
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
