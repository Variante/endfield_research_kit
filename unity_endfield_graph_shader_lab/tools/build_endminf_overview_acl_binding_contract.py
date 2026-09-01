#!/usr/bin/env python3
"""Build the compact Endminf overview ACL binding-asymmetry contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
ACL_ROOT = (
    LAB
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Playable"
    / "Endminf"
    / "Animations"
    / "ACL"
)
DEFAULT_START = ACL_ROOT / "A_actor_endminf_ui_overview_start.asset"
DEFAULT_LOOP = ACL_ROOT / "A_actor_endminf_ui_overview_loop.asset"
DEFAULT_OUTPUT = (
    LAB
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "OriginalData"
    / "CharInfoPresentation"
    / "endminf_overview_acl_binding_asymmetry_contract.json"
)

EXPECTED_START_CLIP = "A_actor_endminf_ui_overview_start"
EXPECTED_LOOP_CLIP = "A_actor_endminf_ui_overview_loop"

SOURCE_CLIP_RE = re.compile(r"^  sourceClipName: (\S+)\r?$", re.MULTILINE)
BINDING_RE = re.compile(
    r"^  - transformPath: (.+)\r?\n"
    r"    trackIndex: ([0-9]+)\r?\n"
    r"    components: ([0-9]+)\r?$",
    re.MULTILINE,
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(LAB.parent.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def parse_clip(path: Path, expected_clip: str) -> tuple[dict, dict[str, dict]]:
    source_bytes = path.read_bytes()
    source = source_bytes.decode("utf-8")
    identity = SOURCE_CLIP_RE.search(source)
    if identity is None or identity.group(1) != expected_clip:
        raise ValueError(
            f"{path} does not identify expected clip {expected_clip}"
        )

    normalized = source.replace("\r\n", "\n")
    binding_header = "  bindings:\n"
    binding_start = normalized.find(binding_header)
    if binding_start < 0:
        raise ValueError(f"{path} contains no RecoveredAclClipData bindings block")
    binding_start += len(binding_header)
    binding_end = normalized.find("  translations:\n", binding_start)
    binding_block = normalized[
        binding_start:binding_end if binding_end >= 0 else len(normalized)
    ]
    if re.fullmatch(
        r"(?:  - transformPath: [^\n]+\n"
        r"    trackIndex: [0-9]+\n"
        r"    components: [0-9]+\n)+",
        binding_block,
    ) is None:
        raise ValueError(
            f"{path} bindings block is malformed or contains unparsed fields"
        )

    rows = BINDING_RE.findall(binding_block)
    if not rows:
        raise ValueError(f"{path} contains no RecoveredAclClipData bindings")
    bindings: dict[str, dict] = {}
    track_indices: set[int] = set()
    for transform_path, track_text, components_text in rows:
        track_index = int(track_text)
        components = int(components_text)
        if transform_path in bindings:
            raise ValueError(f"{path} duplicates binding path {transform_path}")
        if track_index in track_indices:
            raise ValueError(f"{path} duplicates track index {track_index}")
        if components <= 0 or components & ~7:
            raise ValueError(
                f"{path} binding {transform_path} has invalid component mask {components}"
            )
        track_indices.add(track_index)
        bindings[transform_path] = {
            "transformPath": transform_path,
            "trackIndex": track_index,
            "components": components,
        }

    source_row = {
        "repoPath": _repo_path(path),
        "size": len(source_bytes),
        "sha256": _sha256(source_bytes),
        "sourceClipName": expected_clip,
        "bindingCount": len(bindings),
    }
    return source_row, bindings


def build_contract(start_path: Path, loop_path: Path) -> dict:
    start_source, start = parse_clip(start_path, EXPECTED_START_CLIP)
    loop_source, loop = parse_clip(loop_path, EXPECTED_LOOP_CLIP)
    start_paths = set(start)
    loop_paths = set(loop)
    shared_paths = start_paths & loop_paths

    start_only = [start[path] for path in sorted(start_paths - loop_paths)]
    loop_only = [loop[path] for path in sorted(loop_paths - start_paths)]
    shared_component_differences = [
        {
            "transformPath": path,
            "startTrackIndex": start[path]["trackIndex"],
            "loopTrackIndex": loop[path]["trackIndex"],
            "startComponents": start[path]["components"],
            "loopComponents": loop[path]["components"],
        }
        for path in sorted(shared_paths)
        if start[path]["components"] != loop[path]["components"]
    ]
    if not start_only or not loop_only:
        raise ValueError(
            "Endminf overview ACL clips no longer have the expected two-sided "
            "binding-path asymmetry"
        )

    contract = {
        "schema": "endfield.endminf.overview-acl-binding-asymmetry.v1",
        "status": "source_clip_binding_asymmetry_closed",
        "boundary": (
            "Source-hash-bound RecoveredAclClipData binding identities and component "
            "masks only. This contract contains no pose samples, positions, rotations, "
            "scales, curves, captured motion, or fitted timing."
        ),
        "componentMask": {
            "translation": 1,
            "rotation": 2,
            "scale": 4,
        },
        "sources": {
            "start": start_source,
            "loop": loop_source,
        },
        "summary": {
            "sharedBindingPathCount": len(shared_paths),
            "startOnlyBindingPathCount": len(start_only),
            "loopOnlyBindingPathCount": len(loop_only),
            "sharedComponentDifferenceCount": len(shared_component_differences),
        },
        "startOnlyBindings": start_only,
        "loopOnlyBindings": loop_only,
        "sharedComponentDifferences": shared_component_differences,
    }
    validate_contract(contract)
    return contract


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validated_binding_rows(
    contract: dict[str, Any],
    key: str,
    fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    rows = contract.get(key)
    _require(isinstance(rows, list), f"{key} is not a list")
    identities: list[str] = []
    for index, row in enumerate(rows):
        _require(isinstance(row, dict), f"{key}[{index}] is not an object")
        _require(set(row) == set(fields), f"{key}[{index}] fields drifted")
        path = row.get("transformPath")
        _require(
            isinstance(path, str) and path.startswith("Root/") and
            not path.endswith("/") and "//" not in path,
            f"{key}[{index}] Transform path is invalid",
        )
        identities.append(path)
        for field in fields:
            if field.endswith("TrackIndex") or field == "trackIndex":
                value = row.get(field)
                _require(
                    isinstance(value, int) and not isinstance(value, bool) and
                    value >= 0,
                    f"{key}[{index}] {field} is invalid",
                )
            if field.endswith("Components") or field == "components":
                value = row.get(field)
                _require(
                    isinstance(value, int) and not isinstance(value, bool) and
                    value > 0 and not value & ~7,
                    f"{key}[{index}] {field} is invalid",
                )
        if "startComponents" in row:
            _require(
                row["startComponents"] != row["loopComponents"],
                f"{key}[{index}] does not contain a component difference",
            )
    _require(identities == sorted(identities), f"{key} is not path-sorted")
    _require(len(identities) == len(set(identities)), f"{key} duplicates a path")
    return rows


def validate_contract(contract: dict[str, Any]) -> None:
    """Validate the compact published evidence without the ignored ACL assets.

    Source-byte regeneration remains the stronger check when the generated ACL
    assets are present. This structural gate deliberately does not pretend that
    the source files exist in a clean checkout.
    """
    _require(
        set(contract) == {
            "schema", "status", "boundary", "componentMask", "sources",
            "summary", "startOnlyBindings", "loopOnlyBindings",
            "sharedComponentDifferences",
        },
        "ACL binding contract fields drifted",
    )
    _require(
        contract.get("schema") ==
        "endfield.endminf.overview-acl-binding-asymmetry.v1",
        "ACL binding contract schema drifted",
    )
    _require(
        contract.get("status") == "source_clip_binding_asymmetry_closed",
        "ACL binding contract status drifted",
    )
    _require(
        contract.get("boundary") == (
            "Source-hash-bound RecoveredAclClipData binding identities and "
            "component masks only. This contract contains no pose samples, "
            "positions, rotations, scales, curves, captured motion, or fitted "
            "timing."
        ),
        "ACL binding evidence boundary drifted",
    )
    _require(
        contract.get("componentMask") == {
            "translation": 1,
            "rotation": 2,
            "scale": 4,
        },
        "ACL binding component-mask schema drifted",
    )
    sources = contract.get("sources")
    _require(
        isinstance(sources, dict) and set(sources) == {"start", "loop"},
        "ACL binding source identities drifted",
    )
    for key, expected_name in (
        ("start", EXPECTED_START_CLIP),
        ("loop", EXPECTED_LOOP_CLIP),
    ):
        source = sources[key]
        _require(isinstance(source, dict), f"{key} source is not an object")
        _require(
            set(source) == {
                "repoPath", "size", "sha256", "sourceClipName", "bindingCount"
            },
            f"{key} source fields drifted",
        )
        _require(
            isinstance(source["repoPath"], str) and source["repoPath"],
            f"{key} source path is invalid",
        )
        _require(
            isinstance(source["size"], int) and
            not isinstance(source["size"], bool) and source["size"] > 0,
            f"{key} source size is invalid",
        )
        _require(
            isinstance(source["sha256"], str) and
            SHA256_RE.fullmatch(source["sha256"]) is not None,
            f"{key} source SHA-256 is invalid",
        )
        _require(
            source["sourceClipName"] == expected_name,
            f"{key} source clip identity drifted",
        )
        _require(
            isinstance(source["bindingCount"], int) and
            not isinstance(source["bindingCount"], bool) and
            source["bindingCount"] > 0,
            f"{key} binding count is invalid",
        )

    start_only = _validated_binding_rows(
        contract,
        "startOnlyBindings",
        ("transformPath", "trackIndex", "components"),
    )
    loop_only = _validated_binding_rows(
        contract,
        "loopOnlyBindings",
        ("transformPath", "trackIndex", "components"),
    )
    differences = _validated_binding_rows(
        contract,
        "sharedComponentDifferences",
        (
            "transformPath", "startTrackIndex", "loopTrackIndex",
            "startComponents", "loopComponents",
        ),
    )
    start_paths = {row["transformPath"] for row in start_only}
    loop_paths = {row["transformPath"] for row in loop_only}
    difference_paths = {row["transformPath"] for row in differences}
    _require(start_paths and loop_paths, "ACL binding asymmetry is not two-sided")
    _require(
        not start_paths & loop_paths and
        not start_paths & difference_paths and
        not loop_paths & difference_paths,
        "ACL exclusive/shared binding path sets overlap",
    )
    _require(
        len({row["trackIndex"] for row in start_only}) == len(start_only) and
        len({row["trackIndex"] for row in loop_only}) == len(loop_only),
        "ACL exclusive binding track indices are duplicated",
    )
    start_known_tracks = (
        [row["trackIndex"] for row in start_only] +
        [row["startTrackIndex"] for row in differences]
    )
    loop_known_tracks = (
        [row["trackIndex"] for row in loop_only] +
        [row["loopTrackIndex"] for row in differences]
    )
    _require(
        len(start_known_tracks) == len(set(start_known_tracks)) and
        len(loop_known_tracks) == len(set(loop_known_tracks)),
        "ACL published binding track indices are duplicated",
    )

    summary = contract.get("summary")
    _require(
        isinstance(summary, dict) and set(summary) == {
            "sharedBindingPathCount", "startOnlyBindingPathCount",
            "loopOnlyBindingPathCount", "sharedComponentDifferenceCount",
        },
        "ACL binding summary fields drifted",
    )
    _require(
        all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in summary.values()),
        "ACL binding summary contains an invalid count",
    )
    shared_count = summary["sharedBindingPathCount"]
    _require(shared_count >= len(differences), "ACL shared binding count is impossible")
    _require(
        summary["startOnlyBindingPathCount"] == len(start_only) and
        summary["loopOnlyBindingPathCount"] == len(loop_only) and
        summary["sharedComponentDifferenceCount"] == len(differences),
        "ACL binding summary/list counts disagree",
    )
    _require(
        sources["start"]["bindingCount"] == shared_count + len(start_only) and
        sources["loop"]["bindingCount"] == shared_count + len(loop_only),
        "ACL source/summary binding counts disagree",
    )


def serialize_contract(contract: dict) -> str:
    validate_contract(contract)
    return json.dumps(contract, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=Path, default=DEFAULT_START)
    parser.add_argument("--loop", type=Path, default=DEFAULT_LOOP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail unless the existing output is byte-identical to regenerated data.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Validate the existing compact contract without reading the ignored "
            "generated ACL source assets."
        ),
    )
    args = parser.parse_args()

    if args.check and args.validate_only:
        parser.error("--check and --validate-only are mutually exclusive")
    if args.validate_only:
        if not args.output.is_file():
            raise SystemExit(f"missing ACL binding contract: {args.output}")
        try:
            existing = json.loads(args.output.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                raise ValueError("ACL binding contract root is not an object")
            validate_contract(existing)
        except (json.JSONDecodeError, ValueError) as exc:
            raise SystemExit(f"invalid ACL binding contract: {exc}") from exc
        print(f"validated {args.output}")
        return 0

    serialized = serialize_contract(build_contract(args.start, args.loop))
    if args.check:
        if not args.output.is_file():
            raise SystemExit(f"missing ACL binding contract: {args.output}")
        existing = args.output.read_text(encoding="utf-8")
        try:
            loaded = json.loads(existing)
            if not isinstance(loaded, dict):
                raise ValueError("ACL binding contract root is not an object")
            validate_contract(loaded)
        except (json.JSONDecodeError, ValueError) as exc:
            raise SystemExit(f"invalid ACL binding contract: {exc}") from exc
        if existing != serialized:
            raise SystemExit(
                "ACL binding contract differs from the source assets; regenerate "
                f"{args.output}"
            )
        print(f"verified {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
