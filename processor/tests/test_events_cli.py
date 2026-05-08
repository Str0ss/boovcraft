"""CLI surface tests for `processor/extract_events.py`.

Covers: argparse usage, exit codes, output-path derivation, missing
input, malformed JSON, and the pre-006 detection guard.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSOR = REPO_ROOT / "processor"
EXTRACTOR = PROCESSOR / "extract_events.py"


def _run(args: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(EXTRACTOR), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def base_1_analysis_path(tmp_path_factory) -> Path:
    """Generate the analyzer output once per session into a tmp dir so
    these tests don't pollute sample_replays/."""
    sys.path.insert(0, str(PROCESSOR))
    from analyze import build_analysis, load_mapping  # noqa: PLC0415

    parser_path = REPO_ROOT / "sample_replays" / "base_1.w3g.json"
    with parser_path.open() as f:
        parser_output = json.load(f)
    analysis = build_analysis(parser_output, load_mapping(), set())

    out_dir = tmp_path_factory.mktemp("events-cli")
    out_path = out_dir / "base_1.w3g.analysis.json"
    with out_path.open("w") as f:
        json.dump(analysis, f)
    return out_path


def test_no_args_exits_2(tmp_path):
    proc = _run([])
    assert proc.returncode == 2
    assert "usage" in proc.stderr.lower()


def test_missing_input_exits_1():
    proc = _run([str(REPO_ROOT / "nonexistent.json")])
    assert proc.returncode == 1
    assert proc.stderr.startswith("[extract_events] error:")


def test_invalid_json_exits_1(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not valid json {")
    proc = _run([str(bad)])
    assert proc.returncode == 1
    assert proc.stderr.startswith("[extract_events] error:")


def test_pre006_input_exits_1(tmp_path, base_1_analysis_path):
    """An analyzer output stripped of all x/y is rejected as pre-006."""
    with base_1_analysis_path.open() as f:
        analysis = json.load(f)

    def strip(obj):
        if isinstance(obj, dict):
            return {k: strip(v) for k, v in obj.items() if k not in ("x", "y")}
        if isinstance(obj, list):
            return [strip(x) for x in obj]
        return obj

    stripped_path = tmp_path / "pre006.analysis.json"
    with stripped_path.open("w") as f:
        json.dump(strip(analysis), f)
    proc = _run([str(stripped_path)])
    assert proc.returncode == 1
    assert "predate feature 006" in proc.stderr or "feature 006" in proc.stderr


def test_happy_path_writes_events_file(tmp_path, base_1_analysis_path):
    work_path = tmp_path / "base_1.w3g.analysis.json"
    shutil.copy(base_1_analysis_path, work_path)
    proc = _run([str(work_path)])
    assert proc.returncode == 0, proc.stderr
    out_path = tmp_path / "base_1.w3g.events.json"
    assert out_path.exists()
    with out_path.open() as f:
        doc = json.load(f)
    assert set(doc.keys()) == {"match", "events", "diagnostics"}


def test_overwrites_existing_output(tmp_path, base_1_analysis_path):
    work_path = tmp_path / "base_1.w3g.analysis.json"
    shutil.copy(base_1_analysis_path, work_path)
    out_path = tmp_path / "base_1.w3g.events.json"
    out_path.write_text("{}\n")  # pre-existing junk
    proc = _run([str(work_path)])
    assert proc.returncode == 0
    with out_path.open() as f:
        doc = json.load(f)
    assert "events" in doc


def test_silent_stdout_on_success(tmp_path, base_1_analysis_path):
    work_path = tmp_path / "base_1.w3g.analysis.json"
    shutil.copy(base_1_analysis_path, work_path)
    proc = _run([str(work_path)])
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_output_path_derivation_strips_analysis_suffix(tmp_path, base_1_analysis_path):
    work_path = tmp_path / "myreplay.w3g.analysis.json"
    shutil.copy(base_1_analysis_path, work_path)
    proc = _run([str(work_path)])
    assert proc.returncode == 0
    assert (tmp_path / "myreplay.w3g.events.json").exists()


def test_output_path_derivation_appends_when_no_json(tmp_path, base_1_analysis_path):
    work_path = tmp_path / "myreplay"
    shutil.copy(base_1_analysis_path, work_path)
    proc = _run([str(work_path)])
    assert proc.returncode == 0
    assert (tmp_path / "myreplay.events.json").exists()
