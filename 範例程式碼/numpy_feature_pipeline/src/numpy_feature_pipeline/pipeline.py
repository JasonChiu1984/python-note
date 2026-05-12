from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FEATURE_COLUMNS = ("temperature", "humidity", "pressure")


@dataclass(frozen=True)
class FeatureOutput:
    matrix_path: Path
    stats_path: Path
    shape: tuple[int, int]


def build_feature_matrix(csv_path: Path) -> np.ndarray:
    with csv_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError("CSV header is required")
        missing = set(FEATURE_COLUMNS) - set(reader.fieldnames)
        if missing:
            raise ValueError(f"missing feature columns: {sorted(missing)}")

        rows = []
        for row_number, row in enumerate(reader, start=2):
            try:
                rows.append([float(row[column]) for column in FEATURE_COLUMNS])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid numeric value at row {row_number}") from exc

    matrix = np.asarray(rows, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != len(FEATURE_COLUMNS):
        raise ValueError(f"expected matrix shape (*, {len(FEATURE_COLUMNS)}), got {matrix.shape}")
    if not np.isfinite(matrix).all():
        raise ValueError("feature matrix contains non-finite values")
    return matrix


def summarize_matrix(matrix: np.ndarray) -> dict[str, object]:
    return {
        "columns": list(FEATURE_COLUMNS),
        "shape": list(matrix.shape),
        "dtype": str(matrix.dtype),
        "mean": np.round(matrix.mean(axis=0), 4).tolist(),
        "std": np.round(matrix.std(axis=0), 4).tolist(),
    }


def write_feature_outputs(csv_path: Path, out_dir: Path) -> FeatureOutput:
    matrix = build_feature_matrix(csv_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / "features.npy"
    stats_path = out_dir / "stats.json"

    np.save(matrix_path, matrix)
    stats_path.write_text(json.dumps(summarize_matrix(matrix), ensure_ascii=False, indent=2), encoding="utf-8")
    return FeatureOutput(matrix_path=matrix_path, stats_path=stats_path, shape=matrix.shape)
