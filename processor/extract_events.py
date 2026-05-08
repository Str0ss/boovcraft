"""Processor layer (stage 2): reads a feature-006 analyzer output and
emits a per-replay narrative-events JSON file.

Contract: see specs/006-event-extraction/contracts/extract-events-cli.md
Output shape: see specs/006-event-extraction/contracts/events-output-shape.md
                and processor/EVENTS.md (operative copy)
Per-kind field tables: see specs/006-event-extraction/data-model.md
Per-replay threshold derivation: see specs/006-event-extraction/research.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.cluster import DBSCAN

HERE = Path(__file__).resolve().parent
PYPROJECT_PATH = HERE / "pyproject.toml"

REQUIRED_ANALYSIS_KEYS = {
    "match",
    "settings",
    "map",
    "players",
    "observers",
    "chat",
    "diagnostics",
}

# Per-replay time thresholds (research.md §R5, §R6, §R10).
IDLE_MIN_GAP_MS = 15_000
PRODUCTION_STALL_MIN_GAP_MS = 45_000
TRANSFER_BURST_GAP_MS = 30_000
INTENSITY_WINDOW_SECONDS = 30
INTENSITY_PEAK_SIGMA = 2.0

# Per-replay spatial threshold ratios (research.md §R3, §R4).
HOME_RADIUS_DIAGONAL_FRACTION = 0.10
ENGAGEMENT_RADIUS_DIAGONAL_FRACTION = 0.05
REBUILD_BUCKET_DIAGONAL_FRACTION = 0.01
ENGAGEMENT_TIME_WINDOW_SECONDS = 5
ENGAGEMENT_MIN_SAMPLES = 4

# Creeping-departure parameters (research.md §R3, FR-014).
CREEPING_ROLLING_WINDOW_MS = 10_000
CREEPING_MIN_DURATION_MS = 20_000

# Base-incursion / ally-zone parameters.
INCURSION_GAP_SPLIT_MS = 30_000
ALLY_ZONE_INNER_RATIO = 1.0
ALLY_ZONE_OUTER_RATIO = 2.0
ALLY_ZONE_MIN_ACTIONS = 10

# Home-derivation windows (research.md §R2, §R3).
HOME_BUILDING_WINDOW_MS = 120_000
HOME_RADIUS_BUILDING_WINDOW_MS = 180_000
HOME_RADIUS_MIN_BUILDINGS = 3
HOME_FALLBACK_FIRST_ACTIONS = 25

# Tower entity-id catalog (research.md §R7).
TOWER_ENTITY_IDS = {
    "hgtw": "Guard Tower",
    "hctw": "Cannon Tower",
    "hatw": "Arcane Tower",
    "hwtw": "Scout Tower",
    "otto": "Watch Tower",
    "uzg1": "Spirit Tower",
    "uzg2": "Nerubian Tower",
    "usep": "Sacrificial Pit",  # adjacent — kept for filter completeness
}

# Tech-milestone entity-id catalog (research.md §R8).
TIER2_HALL_IDS = {"hkee", "ostr", "unp1", "etoa"}
TIER3_HALL_IDS = {"hcas", "ofrt", "unp2", "etoe"}
ALTAR_IDS = {"halt", "oalt", "uaod", "eaoe"}
KEY_TECH_BUILDING_IDS = {"hlum", "ofor", "usep", "eaom"}
MAIN_HALL_IDS = {
    "htow", "ogre", "unpl", "etol",
    *TIER2_HALL_IDS,
    *TIER3_HALL_IDS,
}

# Hero teleport item-id catalog (research.md §R9).
HERO_TELEPORT_ITEM_IDS = {
    "stwp": "Scroll of Town Portal",
    "stel": "Staff of Teleportation",
    "mtel": "Mass Teleport Scroll",
}

# In-place upgrades — for the rebuild detector, these are NOT
# placement events (so a "second hkee" is a normal tier upgrade, not a
# rebuild). The rebuild detector skips them.
IN_PLACE_UPGRADE_IDS = TIER2_HALL_IDS | TIER3_HALL_IDS | {
    "hgtw", "hctw", "hatw", "uzg1", "uzg2",
}

# Categories whose timed-action entries carry positions when present.
COORD_BEARING_CATEGORIES = frozenset({"rightclick", "ability", "buildtrain", "item"})


def _err(msg: str) -> int:
    print(f"[extract_events] error: {msg}", file=sys.stderr)
    return 1


def _warn(msg: str) -> None:
    print(f"[extract_events] warn: {msg}", file=sys.stderr)


def _read_extractor_version() -> str:
    try:
        with PYPROJECT_PATH.open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "0.0.0"


# ---------------------------------------------------------------
# CLI scaffolding
# ---------------------------------------------------------------


def _derive_output_path(input_path: Path) -> Path:
    """Per contracts/extract-events-cli.md §Output."""
    name = input_path.name
    if name.endswith(".analysis.json"):
        return input_path.with_name(name[: -len(".analysis.json")] + ".events.json")
    if name.endswith(".json"):
        return input_path.with_name(name[: -len(".json")] + ".events.json")
    return input_path.with_name(name + ".events.json")


def _validate_analysis_shape(obj: Any) -> None:
    if not isinstance(obj, dict):
        raise ValueError("analyzer output must be a JSON object at the root")
    missing = REQUIRED_ANALYSIS_KEYS - obj.keys()
    if missing:
        raise ValueError(
            "analyzer output is missing required top-level keys: "
            + ", ".join(sorted(missing))
        )
    # Probe for feature-006 coord retention. A single coord-bearing
    # entry anywhere is enough to confirm the post-006 contract.
    for p in obj.get("players") or []:
        for entry in (p.get("actions") or {}).get("timedActions") or []:
            if "x" in entry and "y" in entry:
                return
        for cat in ("buildings", "units", "upgrades", "items"):
            for entry in ((p.get("production") or {}).get(cat) or {}).get("order") or []:
                if "x" in entry and "y" in entry:
                    return
    raise ValueError(
        "analyzer output appears to predate feature 006 — no coordinate "
        "fields found on any timed-action or production-order entry. "
        "Re-run processor/analyze.py from the post-006 codebase."
    )


def _atomic_write_json(path: Path, payload: dict) -> None:
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


# ---------------------------------------------------------------
# Phase 4b — per-replay derived values
# ---------------------------------------------------------------


def _load_actions_dataframe(analysis: dict) -> pd.DataFrame:
    """Build a DataFrame of every coord-bearing timed action across all
    players. Columns: timeMs, playerId, teamId, x, y, category.
    """
    team_by_player = {p["id"]: p["teamId"] for p in analysis["players"]}
    rows: list[dict] = []
    for p in analysis["players"]:
        pid = p["id"]
        tid = team_by_player[pid]
        for entry in (p.get("actions") or {}).get("timedActions") or []:
            if "x" not in entry or "y" not in entry:
                continue
            rows.append(
                {
                    "timeMs": entry["timeMs"],
                    "playerId": pid,
                    "teamId": tid,
                    "x": float(entry["x"]),
                    "y": float(entry["y"]),
                    "category": entry["category"],
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=["timeMs", "playerId", "teamId", "x", "y", "category"]
        )
    return pd.DataFrame(rows)


def _compute_map_active_region(df: pd.DataFrame) -> tuple[float, float, float, float, float]:
    """Returns (min_x, max_x, min_y, max_y, diagonal). On an empty df,
    returns zeros — every spatial event kind degenerates to no-op.
    """
    if df.empty:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    min_x, max_x = float(df["x"].min()), float(df["x"].max())
    min_y, max_y = float(df["y"].min()), float(df["y"].max())
    diag = math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2)
    return (min_x, max_x, min_y, max_y, diag)


def _building_placements(p: dict) -> list[dict]:
    """Coord-bearing building placements in chronological order."""
    return [
        o
        for o in (p.get("production") or {}).get("buildings", {}).get("order") or []
        if "x" in o and "y" in o
    ]


def _derive_player_homes(
    analysis: dict, df: pd.DataFrame
) -> tuple[dict[int, tuple[float, float]], dict[int, str]]:
    """Per research.md §R2."""
    homes: dict[int, tuple[float, float]] = {}
    methods: dict[int, str] = {}
    for p in analysis["players"]:
        pid = p["id"]
        early = [
            (o["x"], o["y"])
            for o in _building_placements(p)
            if o["timeMs"] <= HOME_BUILDING_WINDOW_MS
        ]
        if early:
            cx = sum(x for x, _ in early) / len(early)
            cy = sum(y for _, y in early) / len(early)
            homes[pid] = (cx, cy)
            methods[pid] = "primary"
            continue
        # Fallback: centroid of player's first N coord-bearing actions.
        player_df = df[df["playerId"] == pid].sort_values("timeMs")
        head = player_df.head(HOME_FALLBACK_FIRST_ACTIONS)
        if not head.empty:
            homes[pid] = (float(head["x"].mean()), float(head["y"].mean()))
            methods[pid] = "fallback:firstActions"
        else:
            homes[pid] = (0.0, 0.0)
            methods[pid] = "fallback:absent"
    return homes, methods


def _derive_player_home_radii(
    analysis: dict,
    homes: dict[int, tuple[float, float]],
    map_diagonal: float,
) -> tuple[dict[int, float], dict[int, str]]:
    """Per research.md §R3."""
    floor = HOME_RADIUS_DIAGONAL_FRACTION * map_diagonal
    radii: dict[int, float] = {}
    methods: dict[int, str] = {}
    for p in analysis["players"]:
        pid = p["id"]
        home = homes.get(pid, (0.0, 0.0))
        early = [
            o
            for o in _building_placements(p)
            if o["timeMs"] <= HOME_RADIUS_BUILDING_WINDOW_MS
        ]
        if len(early) >= HOME_RADIUS_MIN_BUILDINGS:
            max_d = max(
                math.hypot(o["x"] - home[0], o["y"] - home[1]) for o in early
            )
            radii[pid] = max(max_d, floor)
            methods[pid] = "primary"
        else:
            radii[pid] = floor
            methods[pid] = "fallback:diagonalFloor"
    return radii, methods


def _engagement_radius(map_diagonal: float) -> float:
    return ENGAGEMENT_RADIUS_DIAGONAL_FRACTION * map_diagonal


def _engagement_time_scale(map_diagonal: float) -> float:
    radius = _engagement_radius(map_diagonal)
    return radius / ENGAGEMENT_TIME_WINDOW_SECONDS if radius > 0 else 0.0


def _rebuild_bucket_size(map_diagonal: float) -> float:
    return REBUILD_BUCKET_DIAGONAL_FRACTION * map_diagonal


# ---------------------------------------------------------------
# Phase 4c — stable event id
# ---------------------------------------------------------------


def _event_id(
    kind: str,
    start_time_ms: int,
    participants: list[int],
    disambiguator: str = "",
) -> str:
    """Per research.md §R11."""
    canonical = "|".join(
        [
            kind,
            str(start_time_ms),
            ",".join(sorted(str(p) for p in participants)),
            disambiguator,
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _make_event(
    kind: str,
    start_time_ms: int,
    participants: list[int],
    *,
    end_time_ms: int | None = None,
    inference_label: str | None = None,
    thresholds: dict | None = None,
    disambiguator: str = "",
    **fields: Any,
) -> dict:
    event: dict = {
        "id": _event_id(kind, start_time_ms, participants, disambiguator),
        "kind": kind,
        "startTimeMs": int(start_time_ms),
        "participants": list(participants),
        "inferenceLabel": inference_label,
    }
    if end_time_ms is not None:
        event["endTimeMs"] = int(end_time_ms)
    event["thresholds"] = thresholds or {}
    event.update(fields)
    return event


# ---------------------------------------------------------------
# Phase 4d — event-kind detectors
# ---------------------------------------------------------------


def _detect_idle_periods(analysis: dict) -> list[dict]:
    """FR-010."""
    out: list[dict] = []
    duration_ms = analysis["match"]["durationMs"]
    for p in analysis["players"]:
        pid = p["id"]
        ta = (p.get("actions") or {}).get("timedActions") or []
        # Treat 0 and duration_ms as virtual bookends so an idle stretch
        # at the start or end of the game is still counted.
        timestamps = [0] + [e["timeMs"] for e in ta] + [duration_ms]
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i - 1]
            if gap < IDLE_MIN_GAP_MS:
                continue
            start = timestamps[i - 1]
            end = timestamps[i]
            out.append(
                _make_event(
                    "idlePeriod",
                    start,
                    [pid],
                    end_time_ms=end,
                    thresholds={"idleMinGapMs": IDLE_MIN_GAP_MS},
                    disambiguator=str(end),
                    playerId=pid,
                    durationMs=end - start,
                )
            )
    return out


def _detect_building_rebuilds(
    analysis: dict, map_diagonal: float
) -> list[dict]:
    """FR-011."""
    out: list[dict] = []
    bucket = _rebuild_bucket_size(map_diagonal)
    if bucket <= 0:
        return out
    for p in analysis["players"]:
        pid = p["id"]
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for o in _building_placements(p):
            if o["id"] in IN_PLACE_UPGRADE_IDS:
                continue
            key = (
                o["id"],
                int(round(o["x"] / bucket)),
                int(round(o["y"] / bucket)),
            )
            groups[key].append(o)
        for key, placements in groups.items():
            if len(placements) < 2:
                continue
            placements.sort(key=lambda o: o["timeMs"])
            for prev, curr in zip(placements, placements[1:]):
                if curr["timeMs"] - prev["timeMs"] < 60_000:
                    continue
                out.append(
                    _make_event(
                        "buildingRebuild",
                        curr["timeMs"],
                        [pid],
                        thresholds={"rebuildBucketSize": bucket},
                        disambiguator=f"{key[0]}@{key[1]},{key[2]}",
                        playerId=pid,
                        entityId=key[0],
                        entityName=prev.get("name", key[0]),
                        original={
                            "timeMs": prev["timeMs"],
                            "x": prev["x"],
                            "y": prev["y"],
                        },
                        rebuild={
                            "timeMs": curr["timeMs"],
                            "x": curr["x"],
                            "y": curr["y"],
                        },
                        gapMs=curr["timeMs"] - prev["timeMs"],
                    )
                )
    return out


def _detect_tech_milestones(analysis: dict) -> list[dict]:
    """FR-012."""
    out: list[dict] = []

    def _emit(player_id: int, label: str, entity_id: str, name: str, t: int) -> None:
        out.append(
            _make_event(
                "techMilestone",
                t,
                [player_id],
                disambiguator=label,
                playerId=player_id,
                milestone=label,
                entityId=entity_id,
                entityName=name,
            )
        )

    for p in analysis["players"]:
        pid = p["id"]
        prod = p.get("production") or {}
        seen: set[str] = set()

        # Tier-2/3 hall, altar, key tech buildings — first occurrence per label.
        for o in (prod.get("buildings") or {}).get("order") or []:
            eid = o["id"]
            for label, ids in (
                ("tier2Hall", TIER2_HALL_IDS),
                ("tier3Hall", TIER3_HALL_IDS),
                ("altar", ALTAR_IDS),
                ("keyTechBuilding", KEY_TECH_BUILDING_IDS),
            ):
                if eid in ids and label not in seen:
                    _emit(pid, label, eid, o.get("name", eid), o["timeMs"])
                    seen.add(label)

        # Major upgrade start — first upgrade per player.
        upgrades = (prod.get("upgrades") or {}).get("order") or []
        if upgrades and "majorUpgradeStart" not in seen:
            first = upgrades[0]
            _emit(
                pid,
                "majorUpgradeStart",
                first["id"],
                first.get("name", first["id"]),
                first["timeMs"],
            )

    return out


def _detect_expo_placements(
    analysis: dict,
    homes: dict[int, tuple[float, float]],
    home_radii: dict[int, float],
) -> list[dict]:
    """FR-013. The first hall placement (often the player's main, when
    placed) is skipped; subsequent halls beyond home radius are expos.
    """
    out: list[dict] = []
    for p in analysis["players"]:
        pid = p["id"]
        home = homes.get(pid, (0.0, 0.0))
        radius = home_radii.get(pid, 0.0)
        halls = [
            o
            for o in (p.get("production") or {}).get("buildings", {}).get("order")
            or []
            if o["id"] in MAIN_HALL_IDS and "x" in o and "y" in o
        ]
        # Skip the first hall — it's often the player's main re-placed
        # or a tier upgrade visible because it has coords.
        for o in halls[1:]:
            d = math.hypot(o["x"] - home[0], o["y"] - home[1])
            if d <= radius:
                continue
            out.append(
                _make_event(
                    "expoPlacement",
                    o["timeMs"],
                    [pid],
                    thresholds={"homeRadius": radius},
                    playerId=pid,
                    entityId=o["id"],
                    entityName=o.get("name", o["id"]),
                    placement={"x": o["x"], "y": o["y"]},
                    home={"x": home[0], "y": home[1]},
                    homeRadius=radius,
                    distanceFromHome=d,
                )
            )
    return out


def _detect_creeping_departures(
    df: pd.DataFrame,
    homes: dict[int, tuple[float, float]],
    home_radii: dict[int, float],
) -> list[dict]:
    """FR-014. Detects sustained excursions outside the home circle by
    walking each player's coord-bearing actions chronologically: a run of
    actions outside home that lasts >= CREEPING_MIN_DURATION_MS becomes
    one event.
    """
    out: list[dict] = []
    for pid, group in df.groupby("playerId"):
        home = homes.get(int(pid), (0.0, 0.0))
        radius = home_radii.get(int(pid), 0.0)
        if radius <= 0:
            continue
        sub = group.sort_values("timeMs").reset_index(drop=True)
        sub["dist"] = ((sub["x"] - home[0]) ** 2 + (sub["y"] - home[1]) ** 2) ** 0.5
        sub["outside"] = sub["dist"] > radius

        # Find runs of consecutive "outside" rows.
        run_start: int | None = None
        run_xs: list[float] = []
        run_ys: list[float] = []
        for i in range(len(sub)):
            row = sub.iloc[i]
            if row["outside"]:
                if run_start is None:
                    run_start = int(row["timeMs"])
                    run_xs = []
                    run_ys = []
                run_xs.append(float(row["x"]))
                run_ys.append(float(row["y"]))
            else:
                if run_start is not None:
                    run_end = int(sub.iloc[i - 1]["timeMs"])
                    if run_end - run_start >= CREEPING_MIN_DURATION_MS:
                        cx = sum(run_xs) / len(run_xs)
                        cy = sum(run_ys) / len(run_ys)
                        out.append(
                            _make_event(
                                "creepingDeparture",
                                run_start,
                                [int(pid)],
                                end_time_ms=run_end,
                                thresholds={
                                    "homeRadius": radius,
                                    "minDurationMs": CREEPING_MIN_DURATION_MS,
                                },
                                playerId=int(pid),
                                destinationCentroid={"x": cx, "y": cy},
                                distanceFromHome=math.hypot(
                                    cx - home[0], cy - home[1]
                                ),
                                actionCount=len(run_xs),
                            )
                        )
                    run_start = None
        if run_start is not None and run_xs:
            run_end = int(sub.iloc[-1]["timeMs"])
            if run_end - run_start >= CREEPING_MIN_DURATION_MS:
                cx = sum(run_xs) / len(run_xs)
                cy = sum(run_ys) / len(run_ys)
                out.append(
                    _make_event(
                        "creepingDeparture",
                        run_start,
                        [int(pid)],
                        end_time_ms=run_end,
                        thresholds={
                            "homeRadius": radius,
                            "minDurationMs": CREEPING_MIN_DURATION_MS,
                        },
                        playerId=int(pid),
                        destinationCentroid={"x": cx, "y": cy},
                        distanceFromHome=math.hypot(cx - home[0], cy - home[1]),
                        actionCount=len(run_xs),
                    )
                )
    return out


def _detect_tower_rush_candidates(
    analysis: dict,
    homes: dict[int, tuple[float, float]],
    home_radii: dict[int, float],
) -> list[dict]:
    """FR-015."""
    out: list[dict] = []
    teams = {p["id"]: p["teamId"] for p in analysis["players"]}
    for p in analysis["players"]:
        pid = p["id"]
        own_home = homes.get(pid)
        own_team = teams[pid]
        if own_home is None:
            continue
        for o in _building_placements(p):
            if o["id"] not in TOWER_ENTITY_IDS:
                continue
            d_own = math.hypot(o["x"] - own_home[0], o["y"] - own_home[1])
            best_opp_id: int | None = None
            best_opp_d = math.inf
            for opp in analysis["players"]:
                if opp["id"] == pid or opp["teamId"] == own_team:
                    continue
                opp_home = homes.get(opp["id"])
                if opp_home is None:
                    continue
                d_opp = math.hypot(o["x"] - opp_home[0], o["y"] - opp_home[1])
                if d_opp < best_opp_d:
                    best_opp_d = d_opp
                    best_opp_id = opp["id"]
            if best_opp_id is None or best_opp_d >= d_own:
                continue
            out.append(
                _make_event(
                    "towerRushCandidate",
                    o["timeMs"],
                    [pid, best_opp_id],
                    inference_label="towerRushCandidate",
                    thresholds={"homeRadius": home_radii.get(pid, 0.0)},
                    playerId=pid,
                    entityId=o["id"],
                    entityName=o.get("name", o["id"]),
                    placement={"x": o["x"], "y": o["y"]},
                    distanceToOwnHome=d_own,
                    threatenedOpponentId=best_opp_id,
                    distanceToThreatenedHome=best_opp_d,
                )
            )
    return out


def _detect_base_incursions(
    df: pd.DataFrame,
    homes: dict[int, tuple[float, float]],
    home_radii: dict[int, float],
    teams: dict[int, int],
) -> list[dict]:
    """FR-016."""
    out: list[dict] = []
    if df.empty:
        return out
    for pid, group in df.groupby("playerId"):
        own_team = teams[int(pid)]
        for opp_id, opp_home in homes.items():
            if opp_id == int(pid):
                continue
            if teams.get(opp_id) == own_team:
                continue
            opp_radius = home_radii.get(opp_id, 0.0)
            if opp_radius <= 0:
                continue
            sub = group.copy()
            sub["d"] = ((sub["x"] - opp_home[0]) ** 2 + (sub["y"] - opp_home[1]) ** 2) ** 0.5
            inside = sub[sub["d"] <= opp_radius].sort_values("timeMs")
            if inside.empty:
                continue
            # Split runs by gap.
            run_rows: list = []
            prev_t: int | None = None
            for _, row in inside.iterrows():
                t = int(row["timeMs"])
                if prev_t is not None and t - prev_t > INCURSION_GAP_SPLIT_MS:
                    if run_rows:
                        out.append(
                            _emit_incursion(int(pid), opp_id, run_rows, opp_radius)
                        )
                        run_rows = []
                run_rows.append(row)
                prev_t = t
            if run_rows:
                out.append(_emit_incursion(int(pid), opp_id, run_rows, opp_radius))
    return out


def _emit_incursion(pid: int, opp_id: int, rows: list, opp_radius: float) -> dict:
    xs = [float(r["x"]) for r in rows]
    ys = [float(r["y"]) for r in rows]
    times = [int(r["timeMs"]) for r in rows]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    return _make_event(
        "baseIncursion",
        min(times),
        [pid, opp_id],
        end_time_ms=max(times),
        inference_label="baseIncursionCandidate",
        thresholds={"opponentHomeRadius": opp_radius},
        playerId=pid,
        opponentId=opp_id,
        actionCount=len(rows),
        centroid={"x": cx, "y": cy},
    )


def _detect_ally_zone_creeping(
    df: pd.DataFrame,
    homes: dict[int, tuple[float, float]],
    home_radii: dict[int, float],
    teams: dict[int, int],
) -> list[dict]:
    """FR-017."""
    out: list[dict] = []
    if df.empty:
        return out
    for pid, group in df.groupby("playerId"):
        pid_int = int(pid)
        own_team = teams[pid_int]
        own_home = homes.get(pid_int)
        own_radius = home_radii.get(pid_int, 0.0)
        if own_home is None or own_radius <= 0:
            continue
        for ally_id, ally_home in homes.items():
            if ally_id == pid_int or teams.get(ally_id) != own_team:
                continue
            ally_radius = home_radii.get(ally_id, 0.0)
            if ally_radius <= 0:
                continue
            sub = group.copy()
            sub["d_ally"] = (
                (sub["x"] - ally_home[0]) ** 2 + (sub["y"] - ally_home[1]) ** 2
            ) ** 0.5
            sub["d_own"] = (
                (sub["x"] - own_home[0]) ** 2 + (sub["y"] - own_home[1]) ** 2
            ) ** 0.5
            in_band = sub[
                (sub["d_ally"] >= ally_radius * ALLY_ZONE_INNER_RATIO)
                & (sub["d_ally"] <= ally_radius * ALLY_ZONE_OUTER_RATIO)
                & (sub["d_own"] > own_radius * ALLY_ZONE_OUTER_RATIO)
            ]
            if len(in_band) < ALLY_ZONE_MIN_ACTIONS:
                continue
            in_band = in_band.sort_values("timeMs")
            xs = in_band["x"].astype(float).tolist()
            ys = in_band["y"].astype(float).tolist()
            times = in_band["timeMs"].astype(int).tolist()
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            out.append(
                _make_event(
                    "allyZoneCreeping",
                    min(times),
                    [pid_int, ally_id],
                    end_time_ms=max(times),
                    inference_label="allyZoneCreepingCandidate",
                    thresholds={
                        "allyHomeRadius": ally_radius,
                        "minActionCount": ALLY_ZONE_MIN_ACTIONS,
                    },
                    playerId=pid_int,
                    allyId=ally_id,
                    actionCount=len(in_band),
                    centroid={"x": cx, "y": cy},
                )
            )
    return out


def _detect_joint_engagements(
    df: pd.DataFrame, map_diagonal: float, teams: dict[int, int]
) -> list[dict]:
    """FR-018."""
    out: list[dict] = []
    if df.empty or map_diagonal <= 0:
        return out
    eps = _engagement_radius(map_diagonal)
    scale = _engagement_time_scale(map_diagonal)
    if eps <= 0 or scale <= 0:
        return out

    # Group by team — only same-team clusters become joint engagements.
    for team_id, group in df.groupby("teamId"):
        if group["playerId"].nunique() < 2:
            continue  # solo team
        points = group[["x", "y", "timeMs"]].to_numpy(dtype=float)
        points_3d = points.copy()
        points_3d[:, 2] = points_3d[:, 2] / 1000.0 * scale  # ms → s → space-equivalent
        labels = DBSCAN(eps=eps, min_samples=ENGAGEMENT_MIN_SAMPLES).fit_predict(
            points_3d
        )
        for cluster_id in set(labels):
            if cluster_id == -1:
                continue
            mask = labels == cluster_id
            cluster_rows = group.iloc[mask]
            participants = sorted(cluster_rows["playerId"].unique().tolist())
            if len(participants) < 2:
                continue
            xs = cluster_rows["x"].astype(float).tolist()
            ys = cluster_rows["y"].astype(float).tolist()
            times = cluster_rows["timeMs"].astype(int).tolist()
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            tightness = (
                sum(math.hypot(x - cx, y - cy) for x, y in zip(xs, ys)) / len(xs)
            )
            per_player: dict[str, int] = {}
            for p in cluster_rows["playerId"].astype(int).tolist():
                per_player[str(p)] = per_player.get(str(p), 0) + 1
            out.append(
                _make_event(
                    "jointEngagement",
                    min(times),
                    participants,
                    end_time_ms=max(times),
                    inference_label="jointEngagementCandidate",
                    thresholds={
                        "engagementRadius": eps,
                        "engagementTimeWindowSeconds": ENGAGEMENT_TIME_WINDOW_SECONDS,
                    },
                    playerIds=participants,
                    centroid={"x": cx, "y": cy},
                    actionCount=int(mask.sum()),
                    perParticipantCounts=per_player,
                    tightness=tightness,
                )
            )
    return out


def _detect_hero_teleports(analysis: dict) -> list[dict]:
    """FR-019."""
    out: list[dict] = []
    for p in analysis["players"]:
        pid = p["id"]
        items = (p.get("production") or {}).get("items", {}).get("order") or []
        for o in items:
            if o["id"] not in HERO_TELEPORT_ITEM_IDS:
                continue
            origin = (
                {"x": o["x"], "y": o["y"]}
                if "x" in o and "y" in o
                else None
            )
            # Hero attribution is best-effort. We have no direct selection
            # state on the order entry, so we surface the player and time
            # without a hero id and note the gap.
            out.append(
                _make_event(
                    "heroTeleport",
                    o["timeMs"],
                    [pid],
                    playerId=pid,
                    itemId=o["id"],
                    itemName=o.get("name", o["id"]),
                    originPosition=origin,
                    heroId=None,
                    attributionNote="hero attribution not available from analyzer output",
                )
            )
    return out


def _detect_production_stalls(analysis: dict) -> list[dict]:
    """FR-020."""
    out: list[dict] = []
    for p in analysis["players"]:
        pid = p["id"]
        prod = p.get("production") or {}
        prod_times: list[int] = []
        for cat in ("buildings", "units", "upgrades", "items"):
            for o in (prod.get(cat) or {}).get("order") or []:
                prod_times.append(o["timeMs"])
        if not prod_times:
            continue
        prod_times.sort()
        ta = sorted(
            (e["timeMs"] for e in (p.get("actions") or {}).get("timedActions") or [])
        )
        if not ta:
            continue
        # Walk gaps in production stream; the gap counts as a stall if
        # the player issued any actions during it.
        for prev, curr in zip(prod_times, prod_times[1:]):
            gap = curr - prev
            if gap < PRODUCTION_STALL_MIN_GAP_MS:
                continue
            during = sum(1 for t in ta if prev < t < curr)
            if during == 0:
                continue
            input_rate = during / (gap / 60_000.0)
            out.append(
                _make_event(
                    "productionStall",
                    prev,
                    [pid],
                    end_time_ms=curr,
                    thresholds={
                        "productionStallMinGapMs": PRODUCTION_STALL_MIN_GAP_MS
                    },
                    disambiguator=str(curr),
                    playerId=pid,
                    durationMs=gap,
                    inputRateDuringStall=input_rate,
                )
            )
    return out


def _detect_intensity_peaks(analysis: dict) -> list[dict]:
    """FR-021."""
    out: list[dict] = []
    duration_ms = analysis["match"]["durationMs"]
    if duration_ms <= 0:
        return out
    duration_s = duration_ms // 1000

    # Build per-team and "all" timed-action time-series.
    teams: dict[int, list[int]] = defaultdict(list)
    all_actions: list[int] = []
    for p in analysis["players"]:
        team_id = p["teamId"]
        for entry in (p.get("actions") or {}).get("timedActions") or []:
            t_s = entry["timeMs"] // 1000
            if 0 <= t_s <= duration_s:
                teams[team_id].append(t_s)
                all_actions.append(t_s)

    def _find_peaks_for(name: str, samples: list[int], participants: list[int]) -> None:
        if not samples:
            return
        s = pd.Series(0, index=range(duration_s + 1), dtype="int64")
        counts = pd.Series(samples).value_counts()
        for idx, c in counts.items():
            if 0 <= int(idx) <= duration_s:
                s.iloc[int(idx)] = int(c)
        rolled = s.rolling(window=INTENSITY_WINDOW_SECONDS, min_periods=1).sum()
        mean = float(rolled.mean())
        std = float(rolled.std())
        if std <= 0:
            return
        threshold = mean + INTENSITY_PEAK_SIGMA * std
        # Local maxima within ±15s neighborhood that exceed threshold.
        half = INTENSITY_WINDOW_SECONDS // 2
        values = rolled.to_numpy()
        for t in range(len(values)):
            v = float(values[t])
            if v < threshold:
                continue
            lo = max(0, t - half)
            hi = min(len(values), t + half + 1)
            if v < values[lo:hi].max():
                continue
            # Avoid duplicate peaks at adjacent ticks: require strict-greater than left neighbor.
            if t > 0 and v <= values[t - 1]:
                continue
            out.append(
                _make_event(
                    "intensityPeak",
                    t * 1000,
                    list(participants),
                    inference_label="intensityPeakCandidate",
                    thresholds={
                        "windowSeconds": INTENSITY_WINDOW_SECONDS,
                        "peakSigma": INTENSITY_PEAK_SIGMA,
                    },
                    disambiguator=name,
                    scope=name,
                    peakValue=v,
                    baseline={"mean": mean, "std": std},
                )
            )

    _find_peaks_for(
        "all",
        all_actions,
        [p["id"] for p in analysis["players"]],
    )
    for team_id, samples in teams.items():
        _find_peaks_for(
            f"team:{team_id}",
            samples,
            [p["id"] for p in analysis["players"] if p["teamId"] == team_id],
        )
    return out


def _detect_resource_transfers(analysis: dict) -> list[dict]:
    """FR-022."""
    out: list[dict] = []
    # Group raw transfers by (sender, receiver) and merge bursts.
    pairs: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for p in analysis["players"]:
        sender_id = p["id"]
        for rt in p.get("resourceTransfers") or []:
            pairs[(sender_id, rt["toPlayerId"])].append(rt)
    for (sender_id, receiver_id), transfers in pairs.items():
        transfers.sort(key=lambda r: r["timeMs"])
        burst: list[dict] = []
        for rt in transfers:
            if not burst or rt["timeMs"] - burst[-1]["timeMs"] <= TRANSFER_BURST_GAP_MS:
                burst.append(rt)
            else:
                out.append(_emit_transfer_burst(sender_id, receiver_id, burst))
                burst = [rt]
        if burst:
            out.append(_emit_transfer_burst(sender_id, receiver_id, burst))
    return out


def _emit_transfer_burst(
    sender_id: int, receiver_id: int, burst: list[dict]
) -> dict:
    start = burst[0]["timeMs"]
    end = burst[-1]["timeMs"]
    end_time_ms = end if len(burst) > 1 else None
    return _make_event(
        "resourceTransfer",
        start,
        [sender_id, receiver_id],
        end_time_ms=end_time_ms,
        thresholds={"burstGapMs": TRANSFER_BURST_GAP_MS},
        senderId=sender_id,
        receiverId=receiver_id,
        count=len(burst),
        totalGold=sum(r.get("gold", 0) for r in burst),
        totalLumber=sum(r.get("lumber", 0) for r in burst),
    )


# ---------------------------------------------------------------
# Phase 4e — assembly
# ---------------------------------------------------------------


def _build_match_block(analysis: dict) -> dict:
    return {
        "parserId": analysis["diagnostics"]["parserId"],
        "durationMs": analysis["match"]["durationMs"],
        "players": [
            {"id": p["id"], "teamId": p["teamId"], "name": p["name"]}
            for p in analysis["players"]
        ],
    }


def _build_diagnostics_block(
    analysis: dict,
    *,
    home_methods: dict[int, str],
    home_radius_methods: dict[int, str],
    map_diagonal: float,
    events: list[dict],
) -> dict:
    counts: dict[str, int] = defaultdict(int)
    for e in events:
        counts[e["kind"]] += 1
    return {
        "extractorVersion": _read_extractor_version(),
        "parserId": analysis["diagnostics"]["parserId"],
        "players": {
            str(pid): {
                "homeDerivation": home_methods.get(pid, "absent"),
                "homeRadiusDerivation": home_radius_methods.get(pid, "absent"),
            }
            for pid in (p["id"] for p in analysis["players"])
        },
        "thresholds": {
            "mapActiveDiagonal": map_diagonal,
            "engagementRadius": _engagement_radius(map_diagonal),
            "rebuildBucketSize": _rebuild_bucket_size(map_diagonal),
            "idleMinGapMs": IDLE_MIN_GAP_MS,
            "productionStallMinGapMs": PRODUCTION_STALL_MIN_GAP_MS,
            "transferBurstGapMs": TRANSFER_BURST_GAP_MS,
            "engagementTimeWindowSeconds": ENGAGEMENT_TIME_WINDOW_SECONDS,
            "intensityWindowSeconds": INTENSITY_WINDOW_SECONDS,
            "intensityPeakSigma": INTENSITY_PEAK_SIGMA,
        },
        "eventCounts": dict(sorted(counts.items())),
    }


def build_events_document(analysis: dict) -> dict:
    """Pure function: AnalysisDocument → EventsDocument."""
    df = _load_actions_dataframe(analysis)
    map_region = _compute_map_active_region(df)
    map_diagonal = map_region[4]
    homes, home_methods = _derive_player_homes(analysis, df)
    home_radii, home_radius_methods = _derive_player_home_radii(
        analysis, homes, map_diagonal
    )
    teams = {p["id"]: p["teamId"] for p in analysis["players"]}

    events: list[dict] = []
    events.extend(_detect_idle_periods(analysis))
    events.extend(_detect_building_rebuilds(analysis, map_diagonal))
    events.extend(_detect_tech_milestones(analysis))
    events.extend(_detect_expo_placements(analysis, homes, home_radii))
    events.extend(_detect_creeping_departures(df, homes, home_radii))
    events.extend(_detect_tower_rush_candidates(analysis, homes, home_radii))
    events.extend(_detect_base_incursions(df, homes, home_radii, teams))
    events.extend(_detect_ally_zone_creeping(df, homes, home_radii, teams))
    events.extend(_detect_joint_engagements(df, map_diagonal, teams))
    events.extend(_detect_hero_teleports(analysis))
    events.extend(_detect_production_stalls(analysis))
    events.extend(_detect_intensity_peaks(analysis))
    events.extend(_detect_resource_transfers(analysis))

    events.sort(
        key=lambda e: (
            e["startTimeMs"],
            e["kind"],
            tuple(sorted(e["participants"])),
        )
    )

    diagnostics = _build_diagnostics_block(
        analysis,
        home_methods=home_methods,
        home_radius_methods=home_radius_methods,
        map_diagonal=map_diagonal,
        events=events,
    )

    return {
        "match": _build_match_block(analysis),
        "events": events,
        "diagnostics": diagnostics,
    }


# ---------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="extract_events",
        description=(
            "Transform an analyzer-output JSON into a per-replay narrative "
            "events JSON file."
        ),
    )
    parser.add_argument("input_path", help="Path to the analyzer-output JSON file.")
    args = parser.parse_args(argv)

    input_path = Path(args.input_path)
    if not input_path.is_file():
        return _err(f"input not found or not a file: {input_path}")

    try:
        with input_path.open("r", encoding="utf-8") as f:
            analysis = json.load(f)
    except json.JSONDecodeError as exc:
        return _err(f"input is not valid JSON ({input_path}): {exc}")
    except OSError as exc:
        return _err(f"could not read input ({input_path}): {exc}")

    try:
        _validate_analysis_shape(analysis)
    except ValueError as exc:
        return _err(str(exc))

    document = build_events_document(analysis)
    output_path = _derive_output_path(input_path)
    try:
        _atomic_write_json(output_path, document)
    except OSError as exc:
        return _err(f"could not write output ({output_path}): {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
