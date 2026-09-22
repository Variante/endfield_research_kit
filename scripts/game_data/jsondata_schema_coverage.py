"""Measure how much of each binary JsonData file a framing actually names.

The family registry in `jsondata_corpus.py` answers a different question: it
proves the exported tree is the current VFS byte-for-byte and routes each
identity to a reader. It reports a per-file *status* -- `schema_decoded`,
`bounded_partial` -- and that status is what a consumer must gate on.

A status does not say how much of the file is understood, and the obvious
proxy is wrong. `bytesConsumed` is how far the cursor reached, not how much it
named: a framing anchored on a file's tail reports EOF while declaring an
explicit opaque prefix, so reading it as coverage scores that file 100% when
almost none of it is named. Measuring LevelScriptData that way overstates the
family by more than twenty points.

This module computes the honest figure instead:

    named = min(bytesConsumed, size) - the declared opaque spans inside it

Both subtractions matter and they are different omissions. The unreached tail
of a prefix framing was never looked at. A declared opaque span was looked at,
bounded, and left anonymous on purpose. Either way the bytes are not named, so
neither may be counted, and a reader that declares its opaque ranges is being
more honest than one that stops early without saying so -- not less covered.

The result ranks recovery work by unnamed bytes, which is the quantity a new
codec actually removes. It is a measurement, not evidence of a schema: naming
a byte range here means a framing claims it, and the claim is only as good as
the reader's own fixtures and corpus gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.jsondata-schema-coverage.v1"

DEFAULT_JSON_ROOT = REPO_ROOT / "export_full" / "game" / "Json"

# A range key naming one of these is a span the framing bounded but left
# anonymous. Everything else under ``ranges`` is a span it named.
OPAQUE_RANGE_TOKENS = ("opaque", "unread", "remainder", "unknown", "unnamed")


class CoverageError(RuntimeError):
    """The coverage sweep could not read what it was pointed at."""


def is_opaque_range_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in OPAQUE_RANGE_TOKENS)


def iter_ranges(ranges: Any, path: str = "") -> Iterator[tuple[str, int, int]]:
    """Yield every ``(path, start, end)`` span a framing detail declares."""

    if isinstance(ranges, dict):
        start = ranges.get("startOffset")
        end = ranges.get("endOffset")
        if isinstance(start, int) and isinstance(end, int):
            yield path, start, end
            return
        for key, value in ranges.items():
            yield from iter_ranges(value, f"{path}.{key}" if path else str(key))
    elif isinstance(ranges, list):
        for index, value in enumerate(ranges):
            yield from iter_ranges(value, f"{path}[{index}]")


def declares_opaque_content(detail: dict[str, Any]) -> bool:
    """Whether the framing's own status says it left something anonymous."""

    status = str(detail.get("status") or "")
    return is_opaque_range_key(status) or str(detail.get("schemaStatus")) == "partial"


def is_measurable(detail: dict[str, Any], size: int) -> bool:
    """Whether this detail carries enough to measure its named bytes.

    A framing that reaches EOF, declares no opaque span, and yet advertises
    opaque content in its own status cannot be scored: the bytes it left
    anonymous are real but unlocated. Counting it as fully named is the exact
    error this module exists to avoid, so such a file is reported separately
    instead of inflating a coverage figure.
    """

    if not declares_opaque_content(detail):
        return True
    reach = detail.get("bytesConsumed")
    if isinstance(reach, int) and reach < size:
        return True
    return any(
        is_opaque_range_key(path.rsplit(".", 1)[-1].split("[", 1)[0])
        for path, _start, _end in iter_ranges(detail.get("ranges") or {})
    )


def named_bytes(detail: dict[str, Any], size: int) -> tuple[int, int, int]:
    """Return ``(named, opaque, unreached)`` for one framing detail.

    Spans are clamped to the reached region and merged before subtraction, so
    a detail that reports a range twice, or one that overlaps another, cannot
    push the opaque total past the file.
    """

    if size < 0:
        raise ValueError(f"negative file size: {size}")
    reach = detail.get("bytesConsumed")
    reach = size if not isinstance(reach, int) else max(0, min(reach, size))
    unreached = size - reach

    spans: list[tuple[int, int]] = []
    for path, start, end in iter_ranges(detail.get("ranges") or {}):
        leaf = path.rsplit(".", 1)[-1].split("[", 1)[0]
        if not is_opaque_range_key(leaf):
            continue
        low = max(0, min(start, reach))
        high = max(0, min(end, reach))
        if high > low:
            spans.append((low, high))

    # Merge overlaps rather than double-counting them.
    merged: list[list[int]] = []
    for low, high in sorted(spans):
        if merged and low <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])
    opaque = sum(high - low for low, high in merged)

    return reach - opaque, opaque, unreached


def sweep(
    root: Path,
    framers: Iterable[Callable[[bytes], dict[str, Any]]],
    errors: tuple[type[BaseException], ...],
) -> dict[str, Any]:
    """Frame every file under ``root`` with the first framer that accepts it."""

    directory = Path(root)
    if not directory.is_dir():
        raise CoverageError(f"family directory not found: {directory}")

    buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "files": 0,
            "size": 0,
            "named": 0,
            "opaque": 0,
            "unreached": 0,
            "unmeasurableFiles": 0,
            "unmeasurableBytes": 0,
        }
    )
    files = 0
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        files += 1
        data = path.read_bytes()
        detail = None
        for framer in framers:
            try:
                detail = framer(data)
                break
            except errors:
                continue
        if detail is None:
            row = buckets["<unframed>"]
            row["files"] += 1
            row["size"] += len(data)
            row["unreached"] += len(data)
            continue
        row = buckets[str(detail.get("status") or "<no status>")]
        row["files"] += 1
        row["size"] += len(data)
        if not is_measurable(detail, len(data)):
            row["unmeasurableFiles"] += 1
            row["unmeasurableBytes"] += len(data)
            continue
        named, opaque, unreached = named_bytes(detail, len(data))
        row["named"] += named
        row["opaque"] += opaque
        row["unreached"] += unreached

    total_size = sum(row["size"] for row in buckets.values())
    total_named = sum(row["named"] for row in buckets.values())
    unmeasurable = sum(row["unmeasurableBytes"] for row in buckets.values())
    # The share is over the bytes that could be scored; unmeasurable bytes are
    # reported beside it rather than folded into either side.
    measurable = total_size - unmeasurable
    rows = [
        {
            "status": status,
            **row,
            "namedShare": (
                round(row["named"] / (row["size"] - row["unmeasurableBytes"]), 4)
                if row["size"] - row["unmeasurableBytes"]
                else None
            ),
            "unnamedBytes": row["size"] - row["unmeasurableBytes"] - row["named"],
        }
        for status, row in buckets.items()
    ]
    rows.sort(key=lambda row: (-row["unnamedBytes"], -row["unmeasurableBytes"]))
    return {
        "root": str(directory),
        "files": files,
        "bytes": total_size,
        "namedBytes": total_named,
        "measurableBytes": measurable,
        "unmeasurableBytes": unmeasurable,
        "namedShare": round(total_named / measurable, 4) if measurable else None,
        "buckets": rows,
    }


#: Set by `build_report` when a caller opts into derived declarations. The
#: registry functions below are called with no arguments by `FAMILIES`, so the
#: choice is carried here rather than threaded through every signature.
_DECLARATIONS: Any = None


def levelscript_framers() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
    """The LevelScriptData framers, in the registry's own attempt order."""

    from scripts.game_data import levelscript_binary as levelscript

    declared: tuple[Callable[[bytes], dict[str, Any]], ...] = ()
    if _DECLARATIONS is not None:
        # First, because it names strictly more of a file than the prefix and
        # terminal framings it would otherwise fall through to.
        declared = (
            lambda data: levelscript.frame_levelscript_declared_root(
                data, _DECLARATIONS
            ),
            lambda data: levelscript.frame_levelscript_declared_action_map(
                data, _DECLARATIONS
            ),
        )

    return (
        (
            *declared,
            levelscript.frame_levelscript_empty_action_map_sequential,
            levelscript.frame_levelscript_null_action_map_sequential,
            levelscript.frame_levelscript_single_call_server_leader_enter,
            levelscript.frame_levelscript_current_action_sequence_leader_enter,
            levelscript.frame_levelscript_terminal_suffix,
            levelscript.frame_levelscript_empty_action_map_top_level,
            levelscript.frame_levelscript_action_map_named_prefix,
            levelscript.frame_levelscript_empty_action_map_prefix,
        ),
        (levelscript.LevelScriptTopLevelFramingError, ValueError),
    )


def levelscript_template_framers() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
    from scripts.game_data import levelscript_binary as levelscript
    from scripts.game_data import levelscript_template_binary as template

    declared: tuple[Callable[[bytes], dict[str, Any]], ...] = ()
    if _DECLARATIONS is not None:
        declared = (
            lambda data: levelscript.frame_levelscript_declared_root(
                data, _DECLARATIONS, root="LevelScriptTemplateData"
            ),
        )

    return (
        (*declared, template.frame_levelscript_template),
        (getattr(template, "LevelScriptTemplateFramingError", ValueError), ValueError),
    )


def frame_plain_json(data: bytes) -> dict[str, Any]:
    """Frame a file that is simply UTF-8 JSON.

    Several families are plain text, and a successful parse names every byte
    of them. Treating that as a framing keeps the coverage report the whole
    answer for a family instead of something a reader has to correct by hand.
    """

    json.loads(data.decode("utf-8-sig"))
    return {
        "status": "exact_plain_json",
        "schemaStatus": "complete",
        "bytesConsumed": len(data),
        "ranges": {"document": {"startOffset": 0, "endOffset": len(data)}},
        "evidenceBoundary": "The file parses as JSON; its keys are its schema.",
    }


def plain_json_framers() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
    return ((frame_plain_json,), (ValueError, UnicodeDecodeError))


def mixed_json_framers(
    *roots: str,
) -> Callable[[], tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]]:
    """A directory holding both plain JSON and MemoryPack table roots."""

    declared = declared_root_framers(*roots)

    def registry() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
        framers, errors = declared()
        return (frame_plain_json, *framers), (
            ValueError, UnicodeDecodeError, *errors,
        )

    return registry


def npc_framers() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
    """`NPC/` is plain JSON plus the binary montage corpus.

    The montages are the animation-lane payload -- 3,631 files, of which the
    Endminf set is one directory -- and they have a reviewed reader that
    closes every one at EOF. Registering only the JSON framer would report the
    family at 88% while a stronger reader already names the rest.
    """

    from scripts.game_data.memorypack import npc_montage

    return (
        (frame_plain_json, npc_montage.frame_npc_montage),
        (ValueError, UnicodeDecodeError),
    )


def animation_config_framers() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
    """AnimationConfig has a reviewed reader that already closes every file.

    Registering the derived whole-root path here instead would report a far
    lower figure for a family that is in fact exact, so the stronger reader
    wins and the family is measured identically at both tiers.
    """

    from scripts.game_data import animation_config_binary as animation

    return ((animation.frame_animation_config,), (ValueError,))


def char_interact_perform_framers() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
    """Likewise for CharInteractPerformCfgs: the reviewed frame reaches EOF."""

    from scripts.game_data import char_interact_perform_binary as perform

    return ((perform.decode_char_interact_complete_frame,), (ValueError,))


def lipsync_framers() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
    """LipSync is 85% of this lane's bytes, and it has a reviewed reader.

    Leaving it unregistered did not report it as an open family: it left it out
    of the sweep entirely, so the lane figure was computed over the 124 MB that
    happened to be registered and read as though it covered all 826 MB. An
    absent family is the one failure mode a coverage report must not have,
    which is why it is registered here rather than noted somewhere as known.
    """

    from scripts.game_data.memorypack import lipsync

    return ((lipsync.frame_lipsync,), (ValueError,))


def navmesh_framers() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
    """NavMesh has a reviewed reader that closes all twelve files at EOF.

    The derived whole-root framing does not, and the reason is worth keeping
    where the registration is. It stops at
    ``surfTileIDToSceneStateBucketsMask[*].value``, an eight-``ulong`` bucket
    record written with **no** MemoryPack member-count byte, so the framer
    reads the first byte of the first bucket as a member count and refuses.
    The structurally identical value inside ``surfTileIDToSceneStateBucketsSet``
    *is* written with the count byte, which is why one map frames and the other
    does not. That is a wire-form fact about one record, not an unread schema:
    the reviewed reader distinguishes the wrapped and unwrapped spellings and
    names every field of both.

    Registering the derived path here instead would report four files as
    unframed and the family at 23%, understating a family that is in fact
    exact. Both decoders guard on their own leading member count and refuse any
    file they do not close at EOF, so trying them in turn cannot admit a wrong
    reading of the other root.
    """

    from scripts.game_data import navmesh_binary as navmesh

    return (
        (navmesh.decode_navmesh_state_container, navmesh.decode_luna_area),
        (ValueError,),
    )


def declared_root_framers(
    *roots: str,
) -> Callable[[], tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]]:
    """A family measured only by the derived whole-root framing.

    Several roots may share one directory -- `Interactive/` holds three -- so
    each is tried in turn. A root framing refuses any file it does not close
    at EOF, so trying more than one cannot admit a wrong reading.

    With no declarations the registry yields no framer at all, so the family
    is reported as not measured rather than as zero. That is the honest
    reviewed-tier answer for these: nothing here claims to name them.
    """

    def registry() -> tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]:
        from scripts.game_data import levelscript_binary as levelscript

        if _DECLARATIONS is None:
            return (), (levelscript.LevelScriptTopLevelFramingError, ValueError)
        return (
            tuple(
                (lambda data, chosen=root: levelscript.frame_levelscript_declared_root(
                    data, _DECLARATIONS, root=chosen
                ))
                for root in roots
            ),
            (levelscript.LevelScriptTopLevelFramingError, ValueError),
        )

    return registry


FAMILIES: dict[str, Callable[[], tuple[tuple[Callable[[bytes], dict[str, Any]], ...], tuple[type[BaseException], ...]]]] = {
    "LevelScriptData": levelscript_framers,
    "LevelScriptTemplateData": levelscript_template_framers,
    "SkillData": declared_root_framers("SkillData"),
    "LevelData": declared_root_framers("LevelData"),
    "BuffData": declared_root_framers("BuffData"),
    "LevelConfig": declared_root_framers("LevelConfig"),
    "AnimationConfig": animation_config_framers,
    "CharInteractPerformCfgs": char_interact_perform_framers,
    "AtmosphericNpcData": declared_root_framers("NpcAtmosphericDataTable"),
    "SpawnerConfig": declared_root_framers("SpawnerConfigData"),
    "GPUISystemConfig": declared_root_framers(
        "ExtendedPrefabGroupSerializeData", "PrefabGroupSerializeData",
    ),
    "GameplayConfig": mixed_json_framers(
        "AetherEnergyLockConfigDataTable", "DialogIdTable",
        "TeleportValidationDataTable",
    ),
    "NonGeneratedConfigs": mixed_json_framers("BambooRaftTaskTable", "MatrixShockWaveBeatConfigTable"),
    "NavMesh": navmesh_framers,
    "LipSync": lipsync_framers,
    "MissionRuntimeAsset": plain_json_framers,
    "NPC": npc_framers,
    "UILevelMapLoadConfig": plain_json_framers,
    "InteractiveData": plain_json_framers,
    "LevelGenForRuntime": plain_json_framers,
    "MapConfig": plain_json_framers,
    "LevelMountPoint": plain_json_framers,
    "AIConfig": plain_json_framers,
    "Interactive": declared_root_framers(
        "InteractiveTemplateData",
        "ModelViewStateController.MVSCModelViewStateControllerData",
        "InteractiveTable",
    ),
}


def build_report(
    json_root: Path = DEFAULT_JSON_ROOT,
    families: Iterable[str] = (),
    declarations_report: Path | None = None,
) -> dict[str, Any]:
    global _DECLARATIONS
    _DECLARATIONS = None
    if declarations_report is not None:
        from scripts.game_data.codecs.levelscript import action_map

        _DECLARATIONS = action_map.Declarations.from_report(
            json.loads(Path(declarations_report).read_bytes().decode("utf-8-sig"))
        )
    selected = list(families) or list(FAMILIES)
    unknown = [name for name in selected if name not in FAMILIES]
    if unknown:
        raise CoverageError(
            f"no framer registry for {unknown}; known families: {sorted(FAMILIES)}"
        )
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "jsonRoot": str(json_root),
        "evidenceTier": "direct" if declarations_report is not None else "exact",
        "method": (
            "named = min(bytesConsumed, size) - declared opaque spans within reach; "
            "an unreached tail and a declared opaque span both count as unnamed"
        ),
        "families": {},
    }
    for name in selected:
        framers, errors = FAMILIES[name]()
        if not framers:
            # No framer claims this family at this tier. That is not zero
            # coverage -- it is an absence of measurement, and reporting it as
            # 0% would understate readers that live outside this registry.
            report["families"][name] = {
                "root": str(Path(json_root) / name),
                "measured": False,
                "reason": "no framer registered at this evidence tier",
            }
            continue
        report["families"][name] = sweep(Path(json_root) / name, framers, errors)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure named-byte coverage of the binary JsonData families whose "
            "framings declare their opaque ranges."
        )
    )
    parser.add_argument("--json-root", type=Path, default=DEFAULT_JSON_ROOT)
    parser.add_argument(
        "--family",
        action="append",
        default=[],
        help="limit the sweep to this family; repeatable",
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--declarations",
        type=Path,
        help=(
            "a levelscript_union_layouts report; measures at the derived "
            "`direct` tier instead of the reviewed `exact` tier"
        ),
    )
    args = parser.parse_args(argv)

    try:
        report = build_report(args.json_root, args.family, args.declarations)
    except CoverageError as exc:
        print(f"JsonData coverage unavailable: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
        for name, family in report["families"].items():
            if not family.get("measured", True):
                print(f"{name}: not measured at this tier ({family['reason']})")
                continue
            share = family["namedShare"]
            share_text = "n/a" if share is None else f"{share:.1%}"
            print(
                f"{name}: {share_text} of {family['measurableBytes'] / 1e6:.2f} MB "
                f"measurable named across {family['files']} files"
                + (
                    f"; {family['unmeasurableBytes'] / 1e6:.2f} MB unmeasurable"
                    if family["unmeasurableBytes"]
                    else ""
                )
            )
        print(f"-> {args.report}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - documented entry point
    if not __package__:
        raise SystemExit("run as: python -m scripts.game_data.jsondata_schema_coverage")
    raise SystemExit(main())
