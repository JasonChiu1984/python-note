from importlib.metadata import version
from importlib.resources import files


def message() -> str:
    return files(__package__).joinpath("message.txt").read_text(encoding="utf-8").strip()


def main() -> None:
    print(f"{version('release-note-lab')}: {message()}")
