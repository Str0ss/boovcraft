"""Split-engagement attribution + executive summary ranking.

Phase 4 implementation of FR-022 / FR-023.

Pure stdlib; no external imports.
"""

from __future__ import annotations

import math
from typing import Any

# --- Heuristic constants (research.md § R3) ---------------------------------

ATTRIBUTION_TEI_THRESHOLD = 1.0      # team lost the trade
ATTRIBUTION_OUTLIER_MULTIPLIER = 1.5

# Severity weights for executive summary
SEVERITY_WEIGHTS = {
    "splitEngagement":      3.0,
    "missedSave":           2.0,
    "lowTei":               1.5,
    "ignoredPing":          1.2,
    "sharedControlDisabled": 1.0,
    "wrongItemTransfer":    0.8,
}
EXECUTIVE_DURATION_CAP = 3.0
EXECUTIVE_TOP_N = 3


def detect_attributions(
    battles: list[dict[str, Any]],
    battle_summary_tei: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Emit Attribution rows when split-engagement + low TEI + outlier
    centroid coincide.

    Outlier definition: a player whose centroid distance to the team's
    mean centroid > ATTRIBUTION_OUTLIER_MULTIPLIER * mean_pairwise_distance
    on the player's side.
    """
    out: list[dict[str, Any]] = []
    tei_by_index = {row["battleIndex"]: row for row in battle_summary_tei}

    for battle in battles:
        split = battle.get("splitEngagement") or {}
        if not split.get("flagged"):
            continue
        battle_idx = battle["index"]
        tei_row = tei_by_index.get(battle_idx)
        if tei_row is None:
            continue

        # Determine which side the flagged pair is on
        flagged_slots = split.get("flaggedSlots") or []
        if len(flagged_slots) != 2:
            continue
        side_a = set(battle["sides"]["teamA"])
        side_b = set(battle["sides"]["teamB"])
        if set(flagged_slots).issubset(side_a):
            player_side = "teamA"
            side_slots = sorted(side_a)
        elif set(flagged_slots).issubset(side_b):
            player_side = "teamB"
            side_slots = sorted(side_b)
        else:
            continue

        # TEI threshold check
        side_tei = tei_row.get("teamSideTei", {}).get(player_side)
        if side_tei is None or side_tei >= ATTRIBUTION_TEI_THRESHOLD:
            continue

        # Outlier check
        centroids_by_slot = {c["slot"]: c for c in battle.get("centroids", [])}
        side_centroids = [centroids_by_slot.get(s) for s in side_slots]
        side_centroids = [c for c in side_centroids if c and c.get("x") is not None]
        if len(side_centroids) < 2:
            continue
        mean_x = sum(c["x"] for c in side_centroids) / len(side_centroids)
        mean_y = sum(c["y"] for c in side_centroids) / len(side_centroids)

        # mean_pairwise_distance — limited to allied distances on this side
        allied = [
            d for d in battle.get("alliedDistances", [])
            if d["fromSlot"] in set(side_slots) and d["toSlot"] in set(side_slots)
        ]
        if not allied:
            continue
        mean_pair = sum(d["distance"] for d in allied) / len(allied)
        if mean_pair == 0:
            continue
        threshold = ATTRIBUTION_OUTLIER_MULTIPLIER * mean_pair

        for c in side_centroids:
            d = math.hypot(c["x"] - mean_x, c["y"] - mean_y)
            if d > threshold:
                out.append({
                    "playerSlot":  c["slot"],
                    "battleIndex": battle_idx,
                    "reason":      "splitEngagement",
                })

    return out


def compute_executive(
    team_block: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build the top-3 executive summary by weighted severity."""
    findings: list[tuple[float, str, dict[str, Any]]] = []

    battles = team_block.get("battles", []) or []
    item_transfers = team_block.get("itemTransfers", []) or []
    support_events = team_block.get("supportEvents", []) or []
    top_findings = team_block.get("findings", []) or []
    tei_rows = team_block.get("battleSummary", {}).get("tei", []) or []
    tei_by_idx = {row["battleIndex"]: row for row in tei_rows}

    def _battle_duration_factor(battle: dict[str, Any]) -> float:
        dur_s = (battle.get("endMs", 0) - battle.get("startMs", 0)) / 1000
        return min(dur_s / 60.0, EXECUTIVE_DURATION_CAP)

    # 1. splitEngagement findings
    for battle in battles:
        if battle.get("splitEngagement", {}).get("flagged"):
            weight = SEVERITY_WEIGHTS["splitEngagement"] * _battle_duration_factor(battle)
            ts = battle["startMs"] // 1000
            mm, ss = ts // 60, ts % 60
            findings.append((
                weight,
                "splitEngagement",
                {
                    "kind":             "splitEngagement",
                    "battleIndex":      battle["index"],
                    "summary":          f"Split engagement at {mm}:{ss:02d}",
                    "evidenceRef":      {"kind": "battle", "battleIndex": battle["index"]},
                    "weightedSeverity": weight,
                },
            ))

    # 2. missedSave findings
    for i, evt in enumerate(support_events):
        if evt.get("type") == "missedSave":
            ts = evt.get("deathTimeMs", 0) // 1000
            mm, ss = ts // 60, ts % 60
            weight = SEVERITY_WEIGHTS["missedSave"]
            findings.append((
                weight,
                "missedSave",
                {
                    "kind":             "missedSave",
                    "battleIndex":      None,
                    "summary":          f"Missed save at {mm}:{ss:02d}",
                    "evidenceRef":      {"kind": "supportEvent", "index": i},
                    "weightedSeverity": weight,
                },
            ))

    # 3. lowTei (battles with TEI < 0.7 and no other finding)
    for battle in battles:
        if battle.get("splitEngagement", {}).get("flagged"):
            continue  # already attributed via splitEngagement
        idx = battle["index"]
        tei_row = tei_by_idx.get(idx)
        if tei_row is None:
            continue
        tei_a = tei_row.get("teamSideTei", {}).get("teamA")
        tei_b = tei_row.get("teamSideTei", {}).get("teamB")
        worst = min((t for t in (tei_a, tei_b) if t is not None), default=None)
        if worst is not None and worst < 0.7:
            weight = SEVERITY_WEIGHTS["lowTei"] * _battle_duration_factor(battle)
            ts = battle["startMs"] // 1000
            mm, ss = ts // 60, ts % 60
            findings.append((
                weight,
                "lowTei",
                {
                    "kind":             "lowTei",
                    "battleIndex":      idx,
                    "summary":          f"Lopsided trade at {mm}:{ss:02d}",
                    "evidenceRef":      {"kind": "battle", "battleIndex": idx},
                    "weightedSeverity": weight,
                },
            ))

    # 4. wrongItemTransfer
    for i, it in enumerate(item_transfers):
        if it.get("recipientFitClass") == "wrong":
            ts = it.get("timeMs", 0) // 1000
            mm, ss = ts // 60, ts % 60
            weight = SEVERITY_WEIGHTS["wrongItemTransfer"]
            findings.append((
                weight,
                "wrongItemTransfer",
                {
                    "kind":             "wrongItemTransfer",
                    "battleIndex":      None,
                    "summary":          f"Wrong-attribute item give at {mm}:{ss:02d}",
                    "evidenceRef":      {"kind": "itemTransfer", "index": i},
                    "weightedSeverity": weight,
                },
            ))

    # 5. sharedControlDisabled (top-level finding)
    if "sharedControlDisabled" in top_findings:
        weight = SEVERITY_WEIGHTS["sharedControlDisabled"]
        findings.append((
            weight,
            "sharedControlDisabled",
            {
                "kind":             "sharedControlDisabled",
                "battleIndex":      None,
                "summary":          "Shared unit control was not enabled",
                "evidenceRef":      {"kind": "globalFlag", "name": "sharedControlDisabled"},
                "weightedSeverity": weight,
            },
        ))

    # Sort: weight desc, then chronological battleIndex asc (None last)
    def sort_key(f):
        weight, _kind, finding = f
        battle_idx = finding.get("battleIndex")
        return (-weight, battle_idx if battle_idx is not None else 999_999)

    findings.sort(key=sort_key)

    # Apply top-N cap
    out: list[dict[str, Any]] = []
    for rank, (_w, _k, finding) in enumerate(findings[:EXECUTIVE_TOP_N], start=1):
        finding_with_rank = dict(finding)
        finding_with_rank["rank"] = rank
        out.append(finding_with_rank)

    return out
