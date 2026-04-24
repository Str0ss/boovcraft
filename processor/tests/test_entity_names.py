import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPPING = REPO_ROOT / "processor" / "entity_names.json"

sys.path.insert(0, str(REPO_ROOT / "processor"))
from analyze import build_analysis  # noqa: E402


ID_RE = re.compile(r"^[A-Za-z0-9]{4}$")


def _load_mapping() -> dict:
    with MAPPING.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_mapping_shape():
    m = _load_mapping()
    assert isinstance(m, dict)
    for k, v in m.items():
        assert isinstance(k, str) and ID_RE.match(k), f"bad key: {k!r}"
        assert isinstance(v, str) and v.strip() != "", f"bad value for {k}: {v!r}"


def _collect_entity_ids(parser_output: dict) -> dict[str, set[str]]:
    """Group every 4-char ID in the fixture by category."""
    cats: dict[str, set[str]] = {
        "hero": set(),
        "ability": set(),
        "building": set(),
        "unit": set(),
        "upgrade": set(),
        "item": set(),
    }
    for p in parser_output.get("players", []):
        for h in p.get("heroes") or []:
            hid = h.get("id")
            if hid:
                cats["hero"].add(hid)
            for step in h.get("abilityOrder") or []:
                cats["ability"].add(step["value"])
            for ab_id in (h.get("abilities") or {}).keys():
                cats["ability"].add(ab_id)
        for cat_plural, cat_singular in [
            ("buildings", "building"),
            ("units", "unit"),
            ("upgrades", "upgrade"),
            ("items", "item"),
        ]:
            section = p.get(cat_plural) or {}
            for entry in section.get("order") or []:
                if entry.get("id"):
                    cats[cat_singular].add(entry["id"])
            for k in (section.get("summary") or {}).keys():
                if k:
                    cats[cat_singular].add(k)
    return cats


def test_fixture_coverage_base_1(base_1_parser_output):
    m = _load_mapping()
    missing: list[tuple[str, str]] = []
    for cat, ids in _collect_entity_ids(base_1_parser_output).items():
        for eid in ids:
            if eid not in m:
                missing.append((cat, eid))
    assert missing == [], f"unmapped in base_1: {missing}"


def test_fixture_coverage_base_2(base_2_parser_output):
    m = _load_mapping()
    missing: list[tuple[str, str]] = []
    for cat, ids in _collect_entity_ids(base_2_parser_output).items():
        for eid in ids:
            if eid not in m:
                missing.append((cat, eid))
    assert missing == [], f"unmapped in base_2: {missing}"


def test_no_unmapped_diagnostics_for_fixtures(base_1_parser_output, base_2_parser_output):
    m = _load_mapping()
    a1 = build_analysis(base_1_parser_output, m, set())
    a2 = build_analysis(base_2_parser_output, m, set())
    assert a1["diagnostics"]["unmappedEntityIds"] == []
    assert a2["diagnostics"]["unmappedEntityIds"] == []
