#!/usr/bin/env python3
"""Extract exact Default Lit resolver constant slices from EndfieldCapture."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


EXPECTED_VS_IDENTITY = 0xA6AFE2C96CAA3FD9
EXPECTED_PS_IDENTITY = 0xCA09544336A4D56E
# The live CharInfo frame selects a narrower Default Lit variant than the
# older 3DMigoto frame. Forty-nine consecutive packages identify this exact
# registered bytecode at the same family position (two passes before the
# eleven-range Subsurface resolver).
CURRENT_DEFAULT_PS_IDENTITY = 0xB21A1E35EDA1C5BC
# The old complete 3DMigoto frame records Default Lit as the sixteenth
# DrawInstanced(3,1) fullscreen pass, immediately before foliage and
# subsurface. EndfieldCapture stores zero-based fullscreen ordinals.
EXPECTED_DEFAULT_FULLSCREEN_ORDINAL = 15
REQUIRED_CONSTANTS = (45, 157, 259, 3, 2054, 401, 216, 15, 160, 4)
CONSTANT_BYTES = 16


class CaptureError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CaptureError(f"{path} must contain one JSON object")
    return value


def _shader_identity(resolver: dict, stage: int) -> int | None:
    rows = [
        row for row in resolver.get("shaders", [])
        if isinstance(row, dict) and row.get("stage") == stage
    ]
    if len(rows) != 1 or not isinstance(rows[0].get("identityHash"), int):
        return None
    return rows[0]["identityHash"]


def _resource_by_object(metadata: dict, object_id: int) -> dict:
    rows = [
        row for row in metadata.get("selectedResourceRecords", [])
        if isinstance(row, dict)
        and row.get("captureKind") == 2
        and row.get("objectId") == object_id
        and row.get("completed") is True
        and row.get("failure") in (None, 0)
    ]
    if len(rows) != 1:
        raise CaptureError(
            f"constant buffer {object_id} has {len(rows)} completed resource records"
        )
    return rows[0]


def _resource_bytes(blob: bytes, row: dict, object_id: int) -> bytes:
    try:
        start = int(row["blobOffset"])
        size = int(row["blobBytes"])
        byte_size = int(row["byteSize"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CaptureError(
            f"constant buffer {object_id} has invalid blob metadata"
        ) from exc
    end = start + size
    if start < 0 or size != byte_size or end > len(blob):
        raise CaptureError(
            f"constant buffer {object_id} blob range [{start}, {end}) is invalid "
            f"for {len(blob)} bytes"
        )
    return blob[start:end]


def _word_preview(data: bytes) -> dict:
    words = list(struct.unpack(f"<{len(data) // 4}I", data))
    return {
        "firstWordsHex": [f"{word:08x}" for word in words[:16]],
        "lastWordsHex": [f"{word:08x}" for word in words[-16:]],
    }


def decode_resolver(metadata: dict, blob: bytes, resolver: dict) -> tuple[dict, list[bytes]]:
    exact_identity_selection = resolver.get("priorityDefaultDeferred") is True
    family_order_selection = (
        resolver.get("_defaultSelectionEvidence")
        == "twoPassesBeforeElevenRangeSubsurfaceAnchor"
    )
    range_shape_selection = (
        resolver.get("priorityDeferredRangeShape") is True
        and resolver.get("fullscreenOrdinal") == EXPECTED_DEFAULT_FULLSCREEN_ORDINAL
    )
    if (not exact_identity_selection and not range_shape_selection
            and not family_order_selection):
        raise CaptureError(
            "resolver has neither the exact Default Lit identity nor its "
            "verified fullscreen ordinal/range-shape family order"
        )
    if resolver.get("vertexCountPerInstance") != 3 or resolver.get("instanceCount") != 1:
        raise CaptureError("Default Lit resolver is not DrawInstanced(3,1)")
    vs_identity = _shader_identity(resolver, 0)
    ps_identity = _shader_identity(resolver, 4)
    allowed_vs_identities = {EXPECTED_VS_IDENTITY}
    allowed_ps_identities = {
        EXPECTED_PS_IDENTITY,
        CURRENT_DEFAULT_PS_IDENTITY,
    }
    if ((range_shape_selection or family_order_selection)
            and not exact_identity_selection):
        # Shader objects created before hook attachment have no bytecode entry
        # and are serialized with identity zero (or no identity). A conflicting
        # registered identity still fails closed.
        allowed_vs_identities.update((None, 0))
        allowed_ps_identities.update((None, 0))
    if vs_identity not in allowed_vs_identities:
        raise CaptureError(
            f"Default Lit resolver VS identity is {vs_identity!r}, expected "
            f"{EXPECTED_VS_IDENTITY}"
        )
    if ps_identity not in allowed_ps_identities:
        raise CaptureError(
            f"Default Lit resolver PS identity is {ps_identity!r}, expected "
            f"one of {sorted(value for value in allowed_ps_identities if value)}"
            + (" or an absent pre-attachment identity"
               if None in allowed_ps_identities else "")
        )

    ranges = resolver.get("psConstantBuffers")
    if not isinstance(ranges, list):
        raise CaptureError("Default Lit resolver psConstantBuffers is not an array")
    by_slot: dict[int, dict] = {}
    for row in ranges:
        if not isinstance(row, dict) or not isinstance(row.get("slot"), int):
            raise CaptureError("Default Lit resolver has a malformed constant range")
        slot = row["slot"]
        if slot in by_slot:
            raise CaptureError(f"Default Lit resolver has duplicate PS b{slot}")
        by_slot[slot] = row
    current_variant = ps_identity == CURRENT_DEFAULT_PS_IDENTITY
    expected_slots = set(range(9 if current_variant else len(REQUIRED_CONSTANTS)))
    if set(by_slot) != expected_slots:
        raise CaptureError(
            f"Default Lit resolver slots are {sorted(by_slot)}, expected "
            f"{sorted(expected_slots)}"
        )

    resources: dict[int, bytes] = {}
    resource_rows: dict[int, dict] = {}
    decoded = []
    slices = []
    for slot in sorted(expected_slots):
        row = by_slot[slot]
        if row.get("rangeValid") is not True:
            raise CaptureError(f"Default Lit resolver PS b{slot} range is invalid")
        try:
            object_id = int(row["bufferId"])
            first = int(row["firstConstant"])
            bound = int(row["numConstants"])
            byte_width = int(row["byteWidth"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CaptureError(
                f"Default Lit resolver PS b{slot} has nonnumeric range metadata"
            ) from exc
        required = bound if current_variant else REQUIRED_CONSTANTS[slot]
        if object_id <= 0 or first < 0 or bound < required or byte_width <= 0:
            raise CaptureError(
                f"Default Lit resolver PS b{slot} cannot provide {required} constants: "
                f"object={object_id}, first={first}, bound={bound}, bytes={byte_width}"
            )
        if object_id not in resources:
            resource_row = _resource_by_object(metadata, object_id)
            resource_rows[object_id] = resource_row
            resources[object_id] = _resource_bytes(blob, resource_row, object_id)
        resource = resources[object_id]
        if byte_width != len(resource):
            raise CaptureError(
                f"Default Lit resolver PS b{slot} byteWidth {byte_width} differs "
                f"from captured buffer size {len(resource)}"
            )
        start = first * CONSTANT_BYTES
        end = start + required * CONSTANT_BYTES
        if end > len(resource):
            raise CaptureError(
                f"Default Lit resolver PS b{slot} slice [{start}, {end}) exceeds "
                f"buffer {object_id} ({len(resource)} bytes)"
            )
        data = resource[start:end]
        slices.append(data)
        decoded.append({
            "slot": slot,
            "bufferId": object_id,
            "firstConstant": first,
            "boundConstants": bound,
            "requiredConstants": required,
            "byteWidth": byte_width,
            "resourceBlobOffset": int(resource_rows[object_id]["blobOffset"]),
            "sliceByteOffset": start,
            "sliceBytes": len(data),
            "sliceSha256": hashlib.sha256(data).hexdigest(),
            **_word_preview(data),
        })
    return ({
        "selectionEvidence": (
            "exactShaderIdentity"
            if exact_identity_selection
            else resolver.get(
                "_defaultSelectionEvidence",
                "fullscreenOrdinal15AndDeferredRangeShape",
            )
        ),
        "fullscreenOrdinal": resolver.get("fullscreenOrdinal"),
        "vertexShaderIdentity": (
            f"{vs_identity:016x}" if vs_identity else None
        ),
        "pixelShaderIdentity": (
            f"{ps_identity:016x}" if ps_identity else None
        ),
        "pixelShaderVariant": (
            "liveCharInfoNarrowDefault"
            if current_variant else "legacySelectedDefault"
        ),
        "constantBuffers": decoded,
        "uniqueBackingBuffers": len(resources),
    }, slices)


def decode_frame(frame_dir: Path) -> list[tuple[dict, list[bytes]]]:
    metadata = load_json(frame_dir / "metadata.json")
    if metadata.get("schema") != "endfieldCapture.graphicsFrame.v1":
        raise CaptureError(f"{frame_dir} has an unsupported graphics schema")
    if metadata.get("captureIncomplete") or metadata.get("captureFailed"):
        raise CaptureError(f"{frame_dir} is incomplete or failed")
    all_resolvers = [
        row for row in metadata.get("fullscreenResolvers", [])
        if isinstance(row, dict)
    ]
    exact_resolvers = [
        row for row in all_resolvers
        if row.get("priorityDefaultDeferred") is True
    ]
    range_shape_resolvers = [
        row for row in all_resolvers
        if row.get("priorityDeferredRangeShape") is True
        and row.get("fullscreenOrdinal") == EXPECTED_DEFAULT_FULLSCREEN_ORDINAL
    ]
    family_resolvers = []
    if not exact_resolvers and not range_shape_resolvers:
        by_ordinal = {
            row.get("fullscreenOrdinal"): row for row in all_resolvers
            if isinstance(row.get("fullscreenOrdinal"), int)
        }
        for anchor in all_resolvers:
            anchor_slots = {
                row.get("slot") for row in anchor.get("psConstantBuffers", [])
                if isinstance(row, dict)
            }
            anchor_ordinal = anchor.get("fullscreenOrdinal")
            if (anchor.get("priorityDeferredRangeShape") is not True
                    or not isinstance(anchor_ordinal, int)
                    or anchor_ordinal not in {
                        EXPECTED_DEFAULT_FULLSCREEN_ORDINAL + 2,
                        EXPECTED_DEFAULT_FULLSCREEN_ORDINAL + 3,
                    }
                    or not set(range(11)).issubset(anchor_slots)):
                continue
            candidate = by_ordinal.get(anchor_ordinal - 2)
            if candidate is None:
                continue
            selected = dict(candidate)
            selected["_defaultSelectionEvidence"] = (
                "twoPassesBeforeElevenRangeSubsurfaceAnchor"
            )
            family_resolvers.append(selected)
    resolvers = exact_resolvers or range_shape_resolvers or family_resolvers
    if not resolvers:
        return []
    resource_name = metadata.get("resourcesFile")
    if not isinstance(resource_name, str):
        raise CaptureError(f"{frame_dir} has no resourcesFile")
    try:
        blob = (frame_dir / resource_name).read_bytes()
    except OSError as exc:
        raise CaptureError(f"cannot read resources for {frame_dir}: {exc}") from exc
    return [decode_resolver(metadata, blob, resolver) for resolver in resolvers]


def decode_session(session_root: Path, slice_dir: Path | None = None) -> dict:
    frames_root = session_root / "graphics" / "frames"
    if not frames_root.is_dir():
        raise CaptureError(f"graphics frame directory does not exist: {frames_root}")
    frame_dirs = sorted(
        (path for path in frames_root.iterdir() if path.is_dir()),
        key=lambda path: int(path.name),
    )
    matches = []
    failures = []
    for frame_dir in frame_dirs:
        try:
            decoded_rows = decode_frame(frame_dir)
            for resolver_index, (decoded, slices) in enumerate(decoded_rows):
                decoded["frame"] = int(frame_dir.name)
                decoded["frameDirectory"] = str(frame_dir.resolve())
                if slice_dir is not None:
                    slice_dir.mkdir(parents=True, exist_ok=True)
                    for slot, data in enumerate(slices):
                        name = (
                            f"frame_{frame_dir.name}_resolver_{resolver_index}_ps_b{slot}.bin"
                        )
                        (slice_dir / name).write_bytes(data)
                    decoded["sliceDirectory"] = str(slice_dir.resolve())
                matches.append(decoded)
        except CaptureError as exc:
            failures.append({"frame": frame_dir.name, "failure": str(exc)})
    if not matches:
        failures.append({
            "frame": None,
            "failure": "no complete prioritized Default Lit resolver was captured",
        })
    return {
        "schema": "endfield.endminfDefaultDeferredCapture.v1",
        "sessionRoot": str(session_root.resolve()),
        "valid": bool(matches) and not failures,
        "framesScanned": len(frame_dirs),
        "resolverMatches": matches,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("session_root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--slice-dir", type=Path)
    args = parser.parse_args()
    try:
        report = decode_session(args.session_root, args.slice_dir)
    except CaptureError as exc:
        report = {
            "schema": "endfield.endminfDefaultDeferredCapture.v1",
            "sessionRoot": str(args.session_root.resolve()),
            "valid": False,
            "framesScanned": 0,
            "resolverMatches": [],
            "failures": [{"frame": None, "failure": str(exc)}],
        }
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
