"""Determinism check: re-running the extractor on the same analyzer
output yields a byte-identical events document (FR-035 / SC-006)."""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "processor"))

from analyze import build_analysis, load_mapping  # noqa: E402
from extract_events import build_events_document  # noqa: E402


@pytest.fixture(scope="session", params=["base_1", "base_2"], ids=["base_1", "base_2"])
def fixture_name(request):
    return request.param


def test_repeated_extraction_is_byte_identical(
    fixture_name, base_1_parser_output, base_2_parser_output
):
    parser_output = (
        base_1_parser_output if fixture_name == "base_1" else base_2_parser_output
    )
    analysis = build_analysis(parser_output, load_mapping(), set())
    a = build_events_document(analysis)
    b = build_events_document(analysis)
    # The extractor's diagnostics block carries no wall-clock fields,
    # so the two documents must be byte-identical when serialized.
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
