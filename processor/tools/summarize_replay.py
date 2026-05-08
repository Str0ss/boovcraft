"""Summarize a Warcraft 3 replay events JSON via Claude Sonnet 4.6.

Usage:
    python processor/tools/summarize_replay.py <path-to-*.events.json>

Reads the events document, prepends `processor/EVENTS.md` as a cached
system preamble (reused across runs within the cache TTL), calls
Claude Sonnet 4.6, and prints the narrative summary to stdout. Usage
stats — including cache hits — are printed to stderr.

Requires the `summarize` extra:

    pip install -e 'processor[summarize]'

`ANTHROPIC_API_KEY` must be set.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVENTS_MD_PATH = HERE.parent / "EVENTS.md"

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

TASK_INSTRUCTIONS = """\
You are summarizing a Warcraft 3 replay using the events JSON document
passed in the next user turn, plus the schema documentation above. You
do not have access to the replay file, the analyzer output, or any
other source.

Write a 6-10 sentence narrative summary of the match. Rules:

1. Ground every claim in a specific event. Cite the event's `id` inline
   like (id: 8a3f2b1c9d4e5f60) so a reader can find it.

2. Use only the vocabulary the data supports. The extractor does NOT
   observe unit deaths, gold/lumber balances, fog of war, vision, or
   build completion. So:
   - For events with an `inferenceLabel` ending in `Candidate`
     (towerRush, baseIncursion, allyZoneCreeping, jointEngagement,
     intensityPeak), say "consistent with X" or "appears to be X" —
     never claim X happened.
   - Do NOT say "killed", "destroyed", "stole", "won the fight",
     "lost their hero", "took down the building", or anything that
     implies an outcome we did not observe.
   - Do say things like "creeping departure at 3:42", "tower placed
     closer to opponent's base than to own", "burst of joint actions
     near the enemy expo", "20-second idle period".

3. Convert in-game timestamps from milliseconds to mm:ss when you
   mention them.

4. Refer to players by `name` from `match.players[]`, not by numeric
   `id`. Mention team affiliation (teamId) when relevant.

5. Cover at least: an expo placement, a creeping departure, a joint
   engagement, and an idle period. Mention more if the events warrant
   it (tower rushes, tech timings, intensity peaks, large transfers).

6. Open with a one-sentence framing (game type, players, duration —
   from `match`). Close with the most strategically interesting beat.

7. If the document contains zero events of a kind you'd like to
   discuss, do not invent it.
"""


def _err(msg: str) -> int:
    print(f"[summarize_replay] error: {msg}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="summarize_replay",
        description=(
            "Summarize a Warcraft 3 replay events JSON via Claude Sonnet 4.6."
        ),
    )
    parser.add_argument("input_path", help="Path to a *.events.json file.")
    args = parser.parse_args(argv)

    try:
        import anthropic  # noqa: PLC0415
    except ImportError:
        return _err(
            "anthropic SDK not installed. Run "
            "`pip install -e 'processor[summarize]'` from repo root."
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _err("ANTHROPIC_API_KEY environment variable is not set.")

    input_path = Path(args.input_path)
    if not input_path.is_file():
        return _err(f"input not found or not a file: {input_path}")

    if not EVENTS_MD_PATH.is_file():
        return _err(f"EVENTS.md not found at {EVENTS_MD_PATH}")

    events_md = EVENTS_MD_PATH.read_text(encoding="utf-8")
    events_json = input_path.read_text(encoding="utf-8")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        # System prompt: the schema preamble is followed by the task
        # instructions. The `cache_control` marker on the LAST system
        # block caches everything before and including it (render order:
        # tools → system → messages). Both blocks are frozen across
        # replays, so they cache together. The events JSON in the user
        # turn varies per replay and is not cacheable.
        system=[
            {"type": "text", "text": events_md},
            {
                "type": "text",
                "text": TASK_INSTRUCTIONS,
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": events_json}],
    )

    for block in response.content:
        if block.type == "text":
            print(block.text)

    usage = response.usage
    print(
        f"[summarize_replay] usage: "
        f"input={usage.input_tokens} "
        f"cache_write={usage.cache_creation_input_tokens} "
        f"cache_read={usage.cache_read_input_tokens} "
        f"output={usage.output_tokens}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
