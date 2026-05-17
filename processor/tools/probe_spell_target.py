#!/usr/bin/env python3
"""Phase 0 probe — `0x14` action shape for cooperative spell-cast detection.

Walks both committed fixtures' `events[]` streams; for every `0x14`
action, dumps the (orderId1, orderId2, owner, category, flags, targetA,
targetB) combination with sample counts. The goal is to determine
whether the data permits distinguishing a spell cast on an ally unit
from a self-targeted or enemy-targeted cast.

The decision recorded in `research.md § R1`:
- YES → implement `team/support.py::detect_support_spell_casts` (T028)
- NO  → drop `supportSpellCast` emission, write a single
        `diagnostics.cohesionMetricGaps[]` entry on every run

Usage:
    python3 processor/tools/probe_spell_target.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROCESSOR_DIR = HERE.parent
REPO_ROOT = PROCESSOR_DIR.parent
FIXTURES = [
    REPO_ROOT / "sample_replays" / "base_1.w3g.json",
    REPO_ROOT / "sample_replays" / "base_2.w3g.json",
]


def _decode_order_id(raw: list[int]) -> str:
    """w3gjs encodes 4-byte order ids as a list of 4 ints (sometimes
    reversed). Decode to a 4-char ASCII string when possible; fall back
    to the raw integer tuple."""
    if not isinstance(raw, list) or len(raw) != 4:
        return repr(raw)
    try:
        # WC3 typically encodes as little-endian; reverse to get the
        # human-readable id.
        as_bytes = bytes(reversed(raw))
        decoded = as_bytes.decode("ascii")
        if all(c.isalnum() for c in decoded):
            return decoded
        # Not printable — try forward order
        as_bytes = bytes(raw)
        decoded = as_bytes.decode("ascii", errors="replace")
        return decoded
    except Exception:
        return repr(raw)


def main() -> int:
    print(f"=== Phase 0 probe: 0x14 (TWO_TARGETS) action shape ===\n")

    overall_count = 0
    by_order = Counter()
    by_owner = Counter()
    by_category = Counter()
    samples = []

    for fixture in FIXTURES:
        if not fixture.exists():
            print(f"[probe] warning: {fixture} not found", file=sys.stderr)
            continue
        print(f"--- {fixture.name} ---")
        with fixture.open(encoding="utf-8") as f:
            data = json.load(f)
        fixture_count = 0
        for evt in data.get("events", []):
            if evt.get("id") != 31:
                continue
            for cb in evt.get("commandBlocks", []) or []:
                player_id = cb.get("playerId")
                for action in cb.get("actions", []) or []:
                    if action.get("id") != 0x14:
                        continue
                    fixture_count += 1
                    overall_count += 1
                    order1 = _decode_order_id(action.get("orderId1", []))
                    order2 = _decode_order_id(action.get("orderId2", []))
                    owner = action.get("owner")
                    category = action.get("category")
                    by_order[(order1, order2)] += 1
                    by_owner[owner] += 1
                    by_category[category] += 1
                    if len(samples) < 12:
                        samples.append({
                            "fixture": fixture.name,
                            "playerId": player_id,
                            "order1": order1,
                            "order2": order2,
                            "owner": owner,
                            "category": category,
                            "flags": action.get("flags"),
                            "targetA": action.get("targetA"),
                            "targetB": action.get("targetB"),
                        })
        print(f"  0x14 events: {fixture_count}")

    print()
    print(f"=== Aggregate (across both fixtures) ===")
    print(f"Total 0x14 actions: {overall_count}")
    print()
    print(f"By (orderId1, orderId2) — top 10:")
    for (order1, order2), n in by_order.most_common(10):
        print(f"  ({order1!r}, {order2!r}): {n}")
    print()
    print(f"By owner field:")
    for owner, n in by_owner.most_common():
        print(f"  owner={owner}: {n}")
    print()
    print(f"By category field:")
    for category, n in by_category.most_common():
        print(f"  category={category}: {n}")
    print()
    print(f"=== Sample actions (first 12) ===")
    for s in samples:
        print(f"  {s}")

    print()
    print("=== Decision criteria ===")
    print("YES (implement supportSpellCast) iff at least ONE of these holds:")
    print("  * `owner` field reliably names the target unit's slot id (0..15)")
    print("    AND distinguishes ally from self from enemy")
    print("  * `category` discriminates ally-target vs self-target vs enemy-target")
    print("NO otherwise — drop the metric, emit cohesionMetricGaps row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
