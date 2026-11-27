"""Every extension example runs and every page's generated section is up to date."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_extension_sections_are_current():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_extensions.py"), "--check"],
                          capture_output=True, text=True, cwd=ROOT, timeout=900)
    assert proc.returncode == 0, proc.stdout + proc.stderr
