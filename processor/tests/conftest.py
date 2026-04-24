import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_REPLAYS = REPO_ROOT / "sample_replays"


def _load_parser_output(name: str) -> dict:
    path = SAMPLE_REPLAYS / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def base_1_parser_output() -> dict:
    return _load_parser_output("base_1.w3g.json")


@pytest.fixture(scope="session")
def base_2_parser_output() -> dict:
    return _load_parser_output("base_2.w3g.json")


@pytest.fixture(scope="session")
def base_1_parser_output_path() -> Path:
    return SAMPLE_REPLAYS / "base_1.w3g.json"


@pytest.fixture(scope="session")
def base_2_parser_output_path() -> Path:
    return SAMPLE_REPLAYS / "base_2.w3g.json"
