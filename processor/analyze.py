"""Processor layer: reads a Parser-layer JSON file and emits a
visualizer-ready analysis JSON file.

Contract: see specs/002-replay-analyzer/contracts/analyzer-cli.md
Output shape: see specs/002-replay-analyzer/contracts/output-shape.md
Entity-name mapping: see processor/entity_names.json and
specs/002-replay-analyzer/contracts/mapping-shape.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
MAPPING_PATH = HERE / "entity_names.json"
PYPROJECT_PATH = HERE / "pyproject.toml"

REQUIRED_PARSER_KEYS = {
    "apm",
    "buildNumber",
    "chat",
    "creator",
    "duration",
    "events",
    "expansion",
    "gamename",
    "id",
    "map",
    "matchup",
    "observers",
    "parseTime",
    "players",
    "randomseed",
    "settings",
    "startSpots",
    "type",
    "version",
    "winningTeamId",
}


def _err(msg: str) -> int:
    print(f"[analyze] error: {msg}", file=sys.stderr)
    return 1


def _warn(category: str, entity_id: str, seen: set[tuple[str, str]]) -> None:
    key = (category, entity_id)
    if key in seen:
        return
    seen.add(key)
    print(f'[analyze] warn: unmapped {category} id "{entity_id}"', file=sys.stderr)


def _output_path(input_path: Path) -> Path:
    s = str(input_path)
    if s.endswith(".json"):
        return Path(s[: -len(".json")] + ".analysis.json")
    return Path(s + ".analysis.json")


def _write_json_atomic(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def load_mapping() -> dict[str, str]:
    with MAPPING_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("entity_names.json root must be an object")
    return data


def _read_analyzer_version() -> str:
    try:
        with PYPROJECT_PATH.open("rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "0.0.0"


def _resolve_entity(
    category: str,
    entity_id: str,
    mapping: dict[str, str],
    warn_fn: Callable[[str, str], None],
) -> dict[str, Any]:
    if entity_id in mapping:
        return {"id": entity_id, "name": mapping[entity_id], "unknown": False}
    warn_fn(category, entity_id)
    return {"id": entity_id, "name": entity_id, "unknown": True}


def _build_match(p: dict) -> dict:
    wt = p["winningTeamId"]
    winner = {"teamId": wt} if isinstance(wt, int) and wt >= 0 else None
    return {
        "version": p["version"],
        "buildNumber": p["buildNumber"],
        "durationMs": p["duration"],
        "gameType": p["type"],
        "matchup": p["matchup"],
        "startSpots": p["startSpots"],
        "expansion": p["expansion"],
        "gameName": p["gamename"],
        "creator": p["creator"],
        "randomSeed": p["randomseed"],
        "winner": winner,
    }


def _build_settings(p: dict) -> dict:
    return dict(p["settings"])


def _build_map(p: dict) -> dict:
    return dict(p["map"])


def _build_observers(p: dict) -> list[str]:
    return list(p["observers"])


def _build_production(
    player: dict, mapping: dict[str, str], warn_fn: Callable[[str, str], None]
) -> dict:
    singular = {
        "buildings": "building",
        "units": "unit",
        "upgrades": "upgrade",
        "items": "item",
    }
    out: dict[str, dict] = {}
    for cat_plural, cat_singular in singular.items():
        section = player.get(cat_plural) or {}
        order_src = section.get("order") or []
        summary_src = section.get("summary") or {}

        order_out = [
            {
                **_resolve_entity(cat_singular, entry["id"], mapping, warn_fn),
                "timeMs": entry["ms"],
            }
            for entry in order_src
        ]
        summary_out = {
            eid: {
                **_resolve_entity(cat_singular, eid, mapping, warn_fn),
                "count": count,
            }
            for eid, count in summary_src.items()
        }
        out[cat_plural] = {"order": order_out, "summary": summary_out}
    return out


def _build_heroes(
    player: dict, mapping: dict[str, str], warn_fn: Callable[[str, str], None]
) -> list[dict]:
    heroes_out: list[dict] = []
    for h in player.get("heroes") or []:
        hero_id = h.get("id")
        if hero_id:
            hero_ref = _resolve_entity("hero", hero_id, mapping, warn_fn)
        else:
            # w3gjs sometimes emits a hero entry with abilities but no unit id
            # (random-race hero that never surfaced as a trained unit). The
            # sentinel is a Processor convention, not a missing-mapping gap,
            # so it does NOT go through warn_fn.
            hero_ref = {"id": "UNKN", "name": "UNKN", "unknown": True}

        ability_counter: dict[str, int] = {}
        ability_order_out: list[dict] = []
        for step in h.get("abilityOrder") or []:
            ab_id = step["value"]
            ability_counter[ab_id] = ability_counter.get(ab_id, 0) + 1
            ab_ref = _resolve_entity("ability", ab_id, mapping, warn_fn)
            ability_order_out.append(
                {
                    **ab_ref,
                    "timeMs": step["time"],
                    "level": ability_counter[ab_id],
                }
            )

        ability_summary_out: dict[str, dict] = {}
        for ab_id, final_level in (h.get("abilities") or {}).items():
            ab_ref = _resolve_entity("ability", ab_id, mapping, warn_fn)
            ability_summary_out[ab_id] = {**ab_ref, "level": final_level}

        heroes_out.append(
            {
                **hero_ref,
                "level": h.get("level", 0),
                "abilityOrder": ability_order_out,
                "abilitySummary": ability_summary_out,
            }
        )
    return heroes_out


def _build_actions(player: dict, tracking_interval_ms: int) -> dict:
    actions = player.get("actions") or {}
    totals = {k: v for k, v in actions.items() if k != "timed"}
    return {
        "apmTimeline": {
            "bucketWidthMs": tracking_interval_ms,
            "buckets": list(actions.get("timed") or []),
        },
        "totals": totals,
    }


def _build_resource_transfers(player: dict) -> list[dict]:
    return [
        {
            "fromSlot": rt["slot"],
            "toPlayerId": rt["playerId"],
            "toPlayerName": rt["playerName"],
            "gold": rt["gold"],
            "lumber": rt["lumber"],
            "timeMs": rt["msElapsed"],
        }
        for rt in (player.get("resourceTransfers") or [])
    ]


def _build_player(
    player: dict,
    tracking_interval_ms: int,
    winning_team_id: int | None,
    mapping: dict[str, str],
    warn_fn: Callable[[str, str], None],
) -> dict:
    team_id = player["teamid"]
    return {
        "id": player["id"],
        "name": player["name"],
        "teamId": team_id,
        "color": player["color"],
        "race": player["race"],
        "raceDetected": player["raceDetected"],
        "apm": player["apm"],
        "isWinner": winning_team_id is not None and team_id == winning_team_id,
        "actions": _build_actions(player, tracking_interval_ms),
        "groupHotkeys": dict(player.get("groupHotkeys") or {}),
        "heroes": _build_heroes(player, mapping, warn_fn),
        "production": _build_production(player, mapping, warn_fn),
        "resourceTransfers": _build_resource_transfers(player),
    }


def _build_chat(p: dict) -> list[dict]:
    return [
        {
            "playerId": c["playerId"],
            "playerName": c["playerName"],
            "mode": c["mode"],
            "text": c["message"],
            "timeMs": c["timeMS"],
        }
        for c in (p.get("chat") or [])
    ]


def _build_diagnostics(
    p: dict, unmapped: set[tuple[str, str]], analyzer_version: str
) -> dict:
    return {
        "parserId": p["id"],
        "parserParseTimeMs": p["parseTime"],
        "unmappedEntityIds": [
            {"category": cat, "id": eid}
            for cat, eid in sorted(unmapped)
        ],
        "analyzerVersion": analyzer_version,
    }


def build_analysis(
    parser_output: dict,
    mapping: dict[str, str],
    unmapped: set[tuple[str, str]] | None = None,
) -> dict:
    """Pure function: (ParserOutput, EntityNamesMapping) -> AnalysisDocument.

    `unmapped` is an optional set that is populated in-place with
    (category, id) tuples for every unmapped entity encountered.
    """
    if unmapped is None:
        unmapped = set()

    def warn_fn(category: str, entity_id: str) -> None:
        _warn(category, entity_id, unmapped)

    match_obj = _build_match(parser_output)
    winning_team_id = match_obj["winner"]["teamId"] if match_obj["winner"] else None
    tracking_interval_ms = parser_output["apm"]["trackingInterval"]

    players = [
        _build_player(p, tracking_interval_ms, winning_team_id, mapping, warn_fn)
        for p in parser_output["players"]
    ]

    return {
        "match": match_obj,
        "settings": _build_settings(parser_output),
        "map": _build_map(parser_output),
        "players": players,
        "observers": _build_observers(parser_output),
        "chat": _build_chat(parser_output),
        "diagnostics": _build_diagnostics(parser_output, unmapped, _read_analyzer_version()),
    }


def _validate_parser_output(obj: Any) -> None:
    if not isinstance(obj, dict):
        raise ValueError("parser output must be a JSON object at the root")
    missing = REQUIRED_PARSER_KEYS - obj.keys()
    if missing:
        raise ValueError(
            "parser output is missing required top-level keys: "
            + ", ".join(sorted(missing))
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="analyze",
        description="Transform Parser-layer JSON into visualizer-ready analysis JSON.",
    )
    parser.add_argument("parser_output", help="Path to the Parser-layer JSON file.")
    args = parser.parse_args(argv)

    input_path = Path(args.parser_output)
    if not input_path.is_file():
        return _err(f"input file not found: {input_path}")

    try:
        with input_path.open("r", encoding="utf-8") as f:
            parser_output = json.load(f)
    except json.JSONDecodeError as exc:
        return _err(f"input is not valid JSON ({input_path}): {exc}")
    except OSError as exc:
        return _err(f"cannot read input {input_path}: {exc}")

    try:
        _validate_parser_output(parser_output)
    except ValueError as exc:
        return _err(str(exc))

    if not MAPPING_PATH.is_file():
        return _err(f"mapping file missing: {MAPPING_PATH}")
    try:
        mapping = load_mapping()
    except (json.JSONDecodeError, ValueError) as exc:
        return _err(f"mapping file malformed ({MAPPING_PATH}): {exc}")

    unmapped: set[tuple[str, str]] = set()
    analysis = build_analysis(parser_output, mapping, unmapped)

    output_path = _output_path(input_path)
    try:
        _write_json_atomic(output_path, analysis)
    except OSError as exc:
        return _err(f"cannot write output to {output_path}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
