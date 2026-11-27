"""從主機讀 Docker 控制面或 HTTP 資料面，不在腳本內改動容器。"""
import argparse
import json
import subprocess
from pathlib import Path
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
URL = "http://127.0.0.1:18080/sample"


def compose_status(context):
    result = subprocess.run(
        ["docker", "--context", context, "compose", "-p", "python-interop-lab",
         "-f", str(HERE / "compose.yaml"), "ps", "--all", "--format", "json", "telemetry"],
        check=True, capture_output=True, text=True, timeout=8,
    )
    raw = result.stdout.strip()
    if not raw:
        return []
    value = json.loads(raw) if raw.startswith("[") else [json.loads(line) for line in raw.splitlines()]
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError("unexpected Compose ps JSON")
    return value


def sample(url=URL):
    with urlopen(url, timeout=3) as response:
        if response.headers.get_content_type() != "application/json":
            raise ValueError("expected application/json")
        raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError("response exceeds 64 KiB")
        data = json.loads(raw)
    if not isinstance(data, dict) or data.get("schema") != 1 or data.get("quality") != "synthetic":
        raise ValueError("unexpected synthetic sample contract")
    return data


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["status", "sample"])
    p.add_argument("--context", help="status 必須明確指定已確認的 Docker context")
    args = p.parse_args()
    if args.action == "status" and not args.context:
        p.error("status requires --context")
    try:
        result = compose_status(args.context) if args.action == "status" else sample()
    except subprocess.CalledProcessError as exc:
        p.exit(1, f"Docker CLI exit {exc.returncode}: {(exc.stderr or '').strip()[:500]}\n")
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        p.exit(1, f"{type(exc).__name__}: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
