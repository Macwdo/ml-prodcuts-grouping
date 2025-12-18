import csv
from pathlib import Path


def to_dict(*, path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def get_header(*, path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        return next(reader)
