from html import unescape
from pathlib import Path
import re
import subprocess
import sys

import pytest


KIT = Path(__file__).resolve().parents[1] / "python-312-learning-kit"


@pytest.mark.parametrize("suffix", ["", ".en"], ids=["zh", "en"])
def test_core_examples_run_independently_from_the_page(suffix):
    page = (KIT / f"python-312-complete-guide{suffix}.html").read_text(encoding="utf-8")
    for n in range(1, 17):
        code_id = f"c{n:02}"
        article = re.search(rf'<article id="{code_id}">(.*?)</article>', page, re.S)
        assert article is not None, code_id
        block = re.search(r"<pre\b[^>]*><code>(.*?)</code></pre>", article[1], re.S)
        assert block is not None, code_id
        example = unescape(block[1])
        result = subprocess.run(
            [sys.executable, "-I", "-W", "error::SyntaxWarning", "-c", example],
            timeout=5, capture_output=True, text=True,
        )
        assert result.returncode == 0, (code_id, result.stderr)
        assert result.stdout.strip() == f"{code_id.upper()} OK"
