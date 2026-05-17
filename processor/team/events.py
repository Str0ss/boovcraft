"""Action-id constants for the parser-output `events[]` stream, plus a
single helper that yields per-action tuples in chronological order.

Action ids are the discriminator on entries in
`commandBlocks[i].actions[j]` of every TimeSlot block (`event.id == 31`)
inside `parser_output.events[]`. The id values match w3gjs's
ActionParser; field shapes are documented in
`specs/007-team-cohesion-analysis/data-model.md` § Action-id reference.

Pure stdlib; no external imports.
"""

from __future__ import annotations

from typing import Any, Iterator

# --- TimeSlot / control-block discriminators -------------------------------

TIMESLOT_BLOCK_ID = 31
CHAT_BLOCK_ID = 32
LEAVEGAME_BLOCK_ID = 23

# --- Action ids consumed by feature 007 ------------------------------------

ACT_NO_TARGET = 0x10                    # build / train / cast no-target
ACT_TARGET_POSITION = 0x11              # right-click move / cast on ground
ACT_TARGET_POSITION_AND_UNIT = 0x12     # right-click on a unit (target + unit handle)
ACT_GIVE_ITEM = 0x13                    # give item to ally hero
ACT_TWO_TARGETS = 0x14                  # two-target ability (e.g., spell on ally)
ACT_SELECTION = 0x16                    # selection change
ACT_HOTKEY_GROUP = 0x17                 # hotkey group with units list
ACT_TRANSFER_RESOURCES = 0x51           # gold/lumber transfer to ally
ACT_MINIMAP_SIGNAL = 0x68               # minimap ping

# Neutral / creep slot ids — handles owned by these slots are excluded
# from ownership and centroid math.
NEUTRAL_SLOT_IDS = frozenset({12, 15})


def iter_command_actions(
    parser_output: dict[str, Any],
) -> Iterator[tuple[int, int, dict[str, Any]]]:
    """Yield ``(time_ms, player_id, action_dict)`` tuples in chronological order.

    Walks ``parser_output["events"][]`` filtering to TimeSlot blocks
    (``id == 31``); for each ``commandBlock`` inside, yields one tuple
    per ``action`` it contains. ``time_ms`` is accumulated from the
    ``timeIncrement`` of preceding TimeSlot blocks.

    Skips TimeSlots whose ``commandBlocks`` is missing or empty (the
    bulk of TimeSlots are empty — there are ~95k TimeSlots vs. ~15k
    actions on the smaller fixture).
    """
    time_ms = 0
    for evt in parser_output.get("events", []):
        if evt.get("id") != TIMESLOT_BLOCK_ID:
            continue
        time_ms += evt.get("timeIncrement", 0)
        for cb in evt.get("commandBlocks") or []:
            player_id = cb.get("playerId")
            if player_id is None:
                continue
            for action in cb.get("actions") or []:
                yield time_ms, player_id, action
