"""Resolve the Character Info overview rest clip for every roster actor.

The runtime-reference render samples the animation the character rests in on
the Character Info overview tab. That clip was named inline at the two render
call sites, which does not generalise: the roster uses three different naming
conventions for the same state.

    A_actor_<actor>_ui_overview_loop_01     16 actors
    A_actor_<actor>_ui_overview_loop        14 actors
    A_actor_<actor>_ui_overview_start_loop   1 actor  (yvonne)

Actor casing is not reliable either: Karin's clip is A_actor_Karin_..., so
resolution is case-insensitive throughout.

This resolves the clip, not the pose. Which phase of the loop a reference
capture shows is not recovered, so a roster comparison still has to either
align or sweep the sample time.

Usage:
    python tools/build_charinfo_overview_clip_contract.py
    python tools/build_charinfo_overview_clip_contract.py --check
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYABLE_ROOT = os.path.join(
    PROJECT_ROOT,
    "Assets",
    "EndfieldGraphShaderLab",
    "Generated",
    "Characters",
    "Playable",
)
CONTRACT_PATH = os.path.join(
    PROJECT_ROOT,
    "Assets",
    "EndfieldGraphShaderLab",
    "Generated",
    "OriginalData",
    "CharInfoPresentation",
    "charinfo_overview_clip_contract.json",
)

# The two clips the lab already named inline. The resolver must reproduce both.
KNOWN = {
    "Wulfa": "A_actor_wulfa_ui_overview_loop_01",
    "Zhuangfy": "A_actor_zhuangfy_ui_overview_loop_01",
}
# Yvonne has no plain overview_loop; her rest state is the start loop.
FALLBACK_SUFFIXES = ("_ui_overview_loop", "_ui_overview_start_loop")


class ClipContractError(RuntimeError):
    """Fail-closed recovery error."""


def resolve(actor: str) -> tuple[str | None, str]:
    """Return (clip name, which naming convention matched)."""
    anim_dir = os.path.join(PLAYABLE_ROOT, actor, "Animations")
    if not os.path.isdir(anim_dir):
        return None, "no-animation-directory"

    names = [
        os.path.basename(p)[: -len(".anim")]
        for p in glob.glob(os.path.join(anim_dir, "*.anim"))
    ]
    lowered = actor.lower()
    for suffix in FALLBACK_SUFFIXES:
        stem = f"a_actor_{lowered}{suffix}"
        matches = sorted(
            n for n in names
            if n.lower() == stem or n.lower() == stem + "_01"
        )
        if len(matches) > 1:
            raise ClipContractError(
                f"{actor} has more than one overview rest clip: {matches}"
            )
        if matches:
            convention = matches[0].lower()[len(f"a_actor_{lowered}"):]
            return matches[0], convention
    return None, "unresolved"


def build() -> dict:
    if not os.path.isdir(PLAYABLE_ROOT):
        raise ClipContractError(f"missing playable root: {PLAYABLE_ROOT}")

    actors = sorted(
        d for d in os.listdir(PLAYABLE_ROOT)
        if d != "CharInfo" and os.path.isdir(os.path.join(PLAYABLE_ROOT, d))
    )
    entries, conventions, unresolved = [], {}, []
    for actor in actors:
        clip, convention = resolve(actor)
        if clip is None:
            unresolved.append(actor)
            continue
        conventions[convention] = conventions.get(convention, 0) + 1
        entries.append({"actor": actor, "clip": clip, "convention": convention})

    if unresolved:
        raise ClipContractError(
            "no overview rest clip for: " + ", ".join(unresolved)
        )

    resolved = {e["actor"]: e["clip"] for e in entries}
    for actor, expected in KNOWN.items():
        if resolved.get(actor) != expected:
            raise ClipContractError(
                f"{actor} resolved to {resolved.get(actor)}, expected {expected}"
            )

    return {
        "schema": "endfield.charinfo.overview-clip.v1",
        "boundary": "asset_name_resolution",
        "selfCheck": {
            "actors": sorted(KNOWN),
            "note": (
                "Reproduces the two clip names the lab already used inline, "
                "which is what ties this resolver to the existing render path."
            ),
        },
        "conventions": dict(sorted(conventions.items())),
        "conventionNote": (
            "The same overview rest state is named three ways across the "
            "roster, and Karin's clip capitalises the actor, so resolution is "
            "case-insensitive. yvonne has no plain _ui_overview_loop; her rest "
            "state is _ui_overview_start_loop."
        ),
        "unrecovered": (
            "The pose. This resolves which clip the character rests in, not "
            "which phase of it a reference capture shows, so a roster "
            "comparison still has to align or sweep the sample time."
        ),
        "actorCount": len(entries),
        "entries": entries,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        contract = build()
    except ClipContractError as error:
        print(f"clip contract failed: {error}", file=sys.stderr)
        return 2

    if args.check:
        if not os.path.isfile(CONTRACT_PATH):
            print(f"missing contract: {CONTRACT_PATH}", file=sys.stderr)
            return 2
        existing = json.load(io.open(CONTRACT_PATH, encoding="utf-8"))
        if existing != contract:
            print("contract differs from the imported animations", file=sys.stderr)
            return 1
        print(f"overview clip contract matches: {contract['actorCount']} actors")
        return 0

    os.makedirs(os.path.dirname(CONTRACT_PATH), exist_ok=True)
    with io.open(CONTRACT_PATH, "w", encoding="utf-8") as handle:
        json.dump(contract, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {os.path.relpath(CONTRACT_PATH, PROJECT_ROOT)}")
    print(f"  actors: {contract['actorCount']}, conventions: {contract['conventions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
