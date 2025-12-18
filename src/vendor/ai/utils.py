from pathlib import Path


def read_prompt(*, path: Path) -> str:
    with open(path) as file:
        return file.read()
