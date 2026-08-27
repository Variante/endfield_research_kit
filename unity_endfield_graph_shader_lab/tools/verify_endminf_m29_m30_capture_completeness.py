#!/usr/bin/env python3
"""Fail closed unless an EndfieldCapture session closes M29/M30 draw resources."""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_m29_m30_capture_completeness_latest.json"
)


class VerificationError(RuntimeError):
    pass


OWNERS = {
    "M29": {
        "vertex": 0xCE755059DEDDC2E0,
        "pixel": 0xF2AD2A14856044AC,
        "counts": {1386},
        "c1": (1.0, 0.0, 15.0, 1.3),
        "c4": (0.26225068, 0.15781066, 0.08437622, 1.0),
    },
    "M30": {
        "vertex": 0x62A5CE6C09171DE9,
        "pixel": 0x5558DEDDB1EE6188,
        "counts": {6, 12},
        "c1": (1.0, 0.0, 3.0, 0.5),
        "c4": (0.93269453, 0.52442606, 0.09170079, 1.0),
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def close(actual: tuple[float, ...], expected: tuple[float, ...]) -> bool:
    return all(math.isclose(a, e, rel_tol=0.0, abs_tol=2e-6)
               for a, e in zip(actual, expected))


def shaders(draw: dict[str, Any]) -> dict[int, int]:
    return {int(row["stage"]): int(row["identityHash"])
            for row in draw.get("shaders", [])}


def constant(draw: dict[str, Any], stage: int, slot: int) -> bytes:
    rows = [row for row in draw.get("constantBuffers", [])
            if int(row.get("stage", -1)) == stage
            and int(row.get("slot", -1)) == slot]
    require(len(rows) == 1, f"stage {stage} b{slot} is not unique")
    row = rows[0]
    require(row.get("rangeValid") is True and row.get("metadataValid") is True,
            f"stage {stage} b{slot} is invalid")
    payload = bytes.fromhex(str(row.get("dataHex", "")))
    require(payload and len(payload) % 16 == 0,
            f"stage {stage} b{slot} has no aligned payload")
    return payload


def vector(payload: bytes, index: int) -> tuple[float, float, float, float]:
    offset = index * 16
    require(offset + 16 <= len(payload), f"constant c{index} is absent")
    return struct.unpack_from("<4f", payload, offset)


def owner_name(draw: dict[str, Any]) -> str | None:
    pair = shaders(draw)
    for name, owner in OWNERS.items():
        if (int(draw.get("count", -1)) not in owner["counts"]
                or pair.get(0) != owner["vertex"]
                or pair.get(4) != owner["pixel"]):
            continue
        try:
            b3 = constant(draw, 4, 3)
        except VerificationError:
            continue
        if close(vector(b3, 1), owner["c1"]) and close(vector(b3, 4), owner["c4"]):
            return name
    return None


def resource_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (int(row.get("objectId", 0)), int(row.get("stage", -1)),
            int(row.get("slot", -1)))


def inspect_owner_draw(frame: int, draw_index: int, owner: str,
                       draw: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    resources = [row for row in draw.get("resources", []) if isinstance(row, dict)]
    require(resources,
            f"{owner} frame {frame} draw {draw_index} has no owner resources")
    selected = [row for row in metadata.get("selectedResourceRecords", [])
                if isinstance(row, dict)]
    selected_by_key = {resource_key(row): row for row in selected}
    selected_by_object: dict[int, list[dict[str, Any]]] = {}
    for row in selected:
        selected_by_object.setdefault(int(row.get("objectId", 0)), []).append(row)

    ps_slots = sorted({int(row["slot"]) for row in resources
                       if int(row.get("stage", -1)) == 4})
    ia = [row for row in resources if int(row.get("stage", -1)) == 0]
    require(ps_slots, f"{owner} frame {frame} has no owned PS resources")
    require(len(ia) >= 2, f"{owner} frame {frame} has incomplete owned IA resources")

    missing_payload = []
    unsupported = []
    for row in resources:
        key = resource_key(row)
        match = selected_by_key.get(key)
        if match is None:
            # IA aliases can share an object with a compute-selected carrier;
            # object identity still proves that the payload is retained.
            aliases = selected_by_object.get(key[0], [])
            match = next((item for item in aliases
                          if item.get("completed") is True
                          and int(item.get("blobBytes", 0)) > 0), None)
        if match is None:
            if int(row.get("byteSize", 0)) == 0:
                unsupported.append({"stage": key[1], "slot": key[2],
                                    "objectId": key[0]})
            else:
                missing_payload.append({"stage": key[1], "slot": key[2],
                                        "objectId": key[0]})
            continue
        if match.get("completed") is not True or int(match.get("blobBytes", 0)) <= 0:
            missing_payload.append({"stage": key[1], "slot": key[2],
                                    "objectId": key[0]})
    require(not missing_payload,
            f"{owner} frame {frame} draw {draw_index} has "
            f"{len(missing_payload)} missing resource payloads: "
            f"{json.dumps(missing_payload, sort_keys=True)}")
    return {
        "frame": frame,
        "drawIndex": draw_index,
        "indexCount": int(draw["count"]),
        "psSlots": ps_slots,
        "iaResourceCount": len(ia),
        "ownedResourceCount": len(resources),
        "unsupportedZeroByteBindings": unsupported,
    }


def build_report(capture: Path) -> dict[str, Any]:
    frame_root = capture / "graphics/frames"
    require(frame_root.is_dir(), f"graphics frame directory is absent: {frame_root}")
    paths = sorted(frame_root.glob("*/metadata.json"),
                   key=lambda path: int(path.parent.name))
    require(paths, "capture has no graphics metadata")
    owners: dict[str, list[dict[str, Any]]] = {name: [] for name in OWNERS}
    truncated_frames = []
    for path in paths:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        frame = int(metadata.get("frame", path.parent.name))
        if metadata.get("resourceSelectionTruncated") is True:
            truncated_frames.append(frame)
        for draw_index, draw in enumerate(metadata.get("drawRecords", [])):
            if not isinstance(draw, dict):
                continue
            name = owner_name(draw)
            if name is not None:
                owners[name].append(
                    inspect_owner_draw(frame, draw_index, name, draw, metadata))

    for name, rows in owners.items():
        require(rows, f"capture contains no exact {name} owner packets")
    return {
        "schema": "endfield.endminf-m29-m30-capture-completeness.v1",
        "status": "validated_exact_owner_resource_closure",
        "capture": str(capture.resolve()),
        "frameCount": len(paths),
        # The native package can omit unrelated broad-profile resources after
        # every exact owner binding above has obtained a byte-bearing payload.
        # Keep that global condition visible, but gate this focused report on
        # the owner-level closure inspected above instead of conflating it with
        # unrelated later resource pressure.
        "globalResourceSelectionTruncated": bool(truncated_frames),
        "resourceSelectionTruncatedFrames": truncated_frames,
        "owners": {
            name: {
                "packetCount": len(rows),
                "psSlots": sorted({slot for row in rows for slot in row["psSlots"]}),
                "minimumOwnedResourceCount": min(row["ownedResourceCount"] for row in rows),
                "packets": rows,
            }
            for name, rows in owners.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(args.capture.resolve())
    except (OSError, ValueError, VerificationError) as exc:
        diagnostic = {
            "schema": "endfield.endminf-m29-m30-capture-completeness.v1",
            "status": "validation_failed",
            "capture": str(args.capture.resolve()),
            "diagnostic": str(exc),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(diagnostic, indent=2) + "\n", encoding="utf-8")
        print(f"ERROR: {exc}")
        print(args.output)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
