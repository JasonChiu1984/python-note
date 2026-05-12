from __future__ import annotations

import json

import numpy as np
import pytest

from numpy_feature_pipeline.pipeline import build_feature_matrix, write_feature_outputs


def test_build_feature_matrix_shape_and_dtype(tmp_path):
    csv_path = tmp_path / "features.csv"
    csv_path.write_text("temperature,humidity,pressure\n21.5,63.0,1012.2\n", encoding="utf-8")

    matrix = build_feature_matrix(csv_path)

    assert matrix.shape == (1, 3)
    assert matrix.dtype == np.float32


def test_invalid_numeric_value_fails_fast(tmp_path):
    csv_path = tmp_path / "features.csv"
    csv_path.write_text("temperature,humidity,pressure\nbad,63.0,1012.2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid numeric value"):
        build_feature_matrix(csv_path)


def test_write_feature_outputs(tmp_path):
    csv_path = tmp_path / "features.csv"
    csv_path.write_text(
        "temperature,humidity,pressure\n21.5,63.0,1012.2\n22.1,61.5,1011.8\n",
        encoding="utf-8",
    )

    result = write_feature_outputs(csv_path, tmp_path / "out")
    stats = json.loads(result.stats_path.read_text(encoding="utf-8"))

    assert result.matrix_path.exists()
    assert stats["shape"] == [2, 3]
    assert stats["columns"] == ["temperature", "humidity", "pressure"]
