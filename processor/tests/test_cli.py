import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYZE = REPO_ROOT / "processor" / "analyze.py"


def _run(*args, cwd=REPO_ROOT):
    return subprocess.run(
        [sys.executable, str(ANALYZE), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _expected_output_path(parser_output_path: Path) -> Path:
    s = str(parser_output_path)
    if s.endswith(".json"):
        return Path(s[: -len(".json")] + ".analysis.json")
    return Path(s + ".analysis.json")


@pytest.fixture
def clean_base_1_output(base_1_parser_output_path):
    out = _expected_output_path(base_1_parser_output_path)
    if out.exists():
        out.unlink()
    yield out
    if out.exists():
        out.unlink()


@pytest.fixture
def clean_base_2_output(base_2_parser_output_path):
    out = _expected_output_path(base_2_parser_output_path)
    if out.exists():
        out.unlink()
    yield out
    if out.exists():
        out.unlink()


def test_exits_zero_and_writes_output_base_1(base_1_parser_output_path, clean_base_1_output):
    result = _run(str(base_1_parser_output_path))
    assert result.returncode == 0, result.stderr
    assert clean_base_1_output.exists()
    assert result.stdout == ""


def test_exits_zero_and_writes_output_base_2(base_2_parser_output_path, clean_base_2_output):
    result = _run(str(base_2_parser_output_path))
    assert result.returncode == 0, result.stderr
    assert clean_base_2_output.exists()
    assert result.stdout == ""


def test_exits_nonzero_on_missing_input(tmp_path):
    missing = tmp_path / "does-not-exist.json"
    result = _run(str(missing))
    assert result.returncode == 1
    assert "[analyze] error:" in result.stderr


def test_exits_nonzero_on_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json at all {{{")
    result = _run(str(bad))
    assert result.returncode == 1
    assert "[analyze] error:" in result.stderr


def test_exits_nonzero_on_missing_required_keys(tmp_path):
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps({"version": "2.00"}))
    result = _run(str(incomplete))
    assert result.returncode == 1
    assert "[analyze] error:" in result.stderr


def test_rerun_is_byte_identical_modulo_parse_time(
    base_1_parser_output_path, clean_base_1_output
):
    r1 = _run(str(base_1_parser_output_path))
    assert r1.returncode == 0
    first = clean_base_1_output.read_bytes()
    clean_base_1_output.unlink()

    r2 = _run(str(base_1_parser_output_path))
    assert r2.returncode == 0
    second = clean_base_1_output.read_bytes()

    d1 = json.loads(first)
    d2 = json.loads(second)
    d1["diagnostics"].pop("parserParseTimeMs", None)
    d2["diagnostics"].pop("parserParseTimeMs", None)
    assert d1 == d2
