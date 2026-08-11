#!/usr/bin/env python3
"""Project an authorized LightCullResult capture into the Gacha frame contract.

This is an intake step only.  It never guesses a row identity, b31 payload,
shadow cache index, or runtime light count.  An optional, separately captured
raw b31 payload is accepted only after its row indices, eight-record stride,
and native producer hashes validate.  Unknown rows remain explicit in the
output and therefore cannot silently become authored room or character
lights.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


LAB_ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "gacha_light_survivor_transport.json"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "gacha_light_cull_capture_contract.json"
)
DECODER_PATH = LAB_ROOT / "tools/decode_light_cull_capture.py"
DECODER_SPEC = importlib.util.spec_from_file_location(
    "endfield_decode_light_cull_capture", DECODER_PATH
)
assert DECODER_SPEC and DECODER_SPEC.loader
DECODER = importlib.util.module_from_spec(DECODER_SPEC)
DECODER_SPEC.loader.exec_module(DECODER)

SCHEMA = "endfield.gacha-light-cull-capture-contract.v1"
VALIDATOR = "gacha_light_cull_capture_contract"
B31_PAYLOAD_SCHEMA = "endfield.prepare-cpu-data-b31-payload.v1"
B31_RECORD_STRIDE_BYTES = 8 * 16
B31_RECORDS_PER_LIGHT = 8
# This is the same body hash enforced by audit_gacha_deferred_light_data.py.
# A whole GameAssembly pin is not sufficient for a detached payload because
# the b31 row layout is produced by one specific native method body.
PREPARE_CPU_DATA_BODY_SHA256 = (
    "c55bd6dc86c971123c433a5dd29b446b557f8713f73b132da25c257369e9bd0b"
)


class CaptureContractError(ValueError):
    """Raised when a capture cannot be projected without inference."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureContractError(f"validator={VALIDATOR}; {message}")


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def f32_bits(value: float) -> str:
    return f"0x{struct.unpack('<I', struct.pack('<f', f32(value)))[0]:08X}"


def vector_bits(values: Iterable[float]) -> tuple[str, ...]:
    return tuple(f32_bits(value) for value in values)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_capture_document(capture_path: Path) -> Mapping[str, Any]:
    try:
        document = json.loads(capture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureContractError(
            f"validator={VALIDATOR}; check=capture_document; "
            f"source={capture_path}; cannot read JSON capture"
        ) from exc
    require(
        isinstance(document, Mapping),
        "check=capture_document; expected=object; actual=" + type(document).__name__,
    )
    return document


def validate_native_b31_payload(
    document: Mapping[str, Any], visible_light_count: int
) -> dict[str, Any]:
    """Validate an optional detached capture of raw eight-record b31 rows.

    The payload is keyed by the original VisibleLight capture row index.  No
    SetupState order or authored identity is inferred here; those remain
    separate, audited projections in the returned contract.
    """

    empty = {
        "present": False,
        "validated": False,
        "schema": None,
        "recordStrideBytes": B31_RECORD_STRIDE_BYTES,
        "recordsPerLight": B31_RECORDS_PER_LIGHT,
        "rows": [],
        "blockedBy": "capture does not contain nativeB31Payload",
    }
    if "nativeB31Payload" not in document:
        return empty

    payload = document["nativeB31Payload"]
    require(
        isinstance(payload, Mapping),
        "check=b31_payload_shape; expected=object; actual="
        + type(payload).__name__,
    )
    require(
        payload.get("schema") == B31_PAYLOAD_SCHEMA,
        f"check=b31_payload_schema; expected={B31_PAYLOAD_SCHEMA}; "
        f"actual={payload.get('schema')!r}",
    )

    pins = payload.get("sourcePins")
    require(
        isinstance(pins, Mapping),
        "check=b31_payload_source_pins; expected=object; actual="
        + type(pins).__name__,
    )
    require(
        str(pins.get("gameAssemblySha256", "")).lower()
        == DECODER.GAME_ASSEMBLY_SHA256,
        "check=b31_payload_gameassembly_sha256; expected="
        + DECODER.GAME_ASSEMBLY_SHA256
        + "; actual="
        + str(pins.get("gameAssemblySha256")),
    )
    require(
        str(pins.get("prepareCpuDataBodySha256", "")).lower()
        == PREPARE_CPU_DATA_BODY_SHA256,
        "check=b31_payload_prepare_cpu_data_sha256; expected="
        + PREPARE_CPU_DATA_BODY_SHA256
        + "; actual="
        + str(pins.get("prepareCpuDataBodySha256")),
    )
    require(
        payload.get("recordStrideBytes") == B31_RECORD_STRIDE_BYTES,
        f"check=b31_payload_record_stride; expected={B31_RECORD_STRIDE_BYTES}; "
        f"actual={payload.get('recordStrideBytes')!r}",
    )
    require(
        payload.get("recordsPerLight") == B31_RECORDS_PER_LIGHT,
        f"check=b31_payload_records_per_light; expected={B31_RECORDS_PER_LIGHT}; "
        f"actual={payload.get('recordsPerLight')!r}",
    )

    rows = payload.get("rows")
    require(
        isinstance(rows, list),
        "check=b31_payload_rows; expected=array; actual=" + type(rows).__name__,
    )
    require(
        len(rows) == visible_light_count,
        f"check=b31_payload_row_count; expected={visible_light_count}; actual={len(rows)}",
    )

    normalized: list[dict[str, Any]] = []
    indices: list[int] = []
    expected_hex_length = B31_RECORD_STRIDE_BYTES * 2
    for payload_index, row in enumerate(rows):
        require(
            isinstance(row, Mapping),
            f"check=b31_payload_row_shape; row={payload_index}; expected=object; "
            f"actual={type(row).__name__}",
        )
        capture_row_index = row.get("captureRowIndex")
        require(
            isinstance(capture_row_index, int)
            and not isinstance(capture_row_index, bool),
            f"check=b31_payload_capture_row_index; row={payload_index}; "
            f"expected=integer; actual={capture_row_index!r}",
        )
        require(
            0 <= capture_row_index < visible_light_count,
            f"check=b31_payload_capture_row_index_range; row={payload_index}; "
            f"expected=0..{max(visible_light_count - 1, 0)}; actual={capture_row_index}",
        )
        raw_hex = row.get("rawRecordsHex")
        require(
            isinstance(raw_hex, str),
            f"check=b31_payload_raw_records; row={payload_index}; expected=hex string; "
            f"actual={type(raw_hex).__name__}",
        )
        require(
            len(raw_hex) == expected_hex_length,
            f"check=b31_payload_raw_records_length; row={capture_row_index}; "
            f"expected={expected_hex_length} hex chars; actual={len(raw_hex)}",
        )
        try:
            raw = bytes.fromhex(raw_hex)
        except ValueError as exc:
            raise CaptureContractError(
                f"validator={VALIDATOR}; check=b31_payload_raw_records_hex; "
                f"row={capture_row_index}; invalid hexadecimal payload"
            ) from exc
        require(
            len(raw) == B31_RECORD_STRIDE_BYTES,
            f"check=b31_payload_raw_records_bytes; row={capture_row_index}; "
            f"expected={B31_RECORD_STRIDE_BYTES}; actual={len(raw)}",
        )
        indices.append(capture_row_index)
        normalized.append(
            {
                "captureRowIndex": capture_row_index,
                "rawRecordsHex": raw.hex(),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )

    expected_indices = list(range(visible_light_count))
    require(
        sorted(indices) == expected_indices,
        f"check=b31_payload_capture_row_indices; expected={expected_indices}; "
        f"actual={sorted(indices)}",
    )
    normalized.sort(key=lambda row: row["captureRowIndex"])
    return {
        "present": True,
        "validated": True,
        "schema": B31_PAYLOAD_SCHEMA,
        "sourcePins": {
            "gameAssemblySha256": DECODER.GAME_ASSEMBLY_SHA256,
            "prepareCpuDataBodySha256": PREPARE_CPU_DATA_BODY_SHA256,
        },
        "recordStrideBytes": B31_RECORD_STRIDE_BYTES,
        "recordsPerLight": B31_RECORDS_PER_LIGHT,
        "rows": normalized,
        "blockedBy": None,
    }


def _row_distance_bits(
    row: Mapping[str, Any], camera_position: Sequence[float]
) -> tuple[str, float]:
    position = row["worldPosition"]
    require(
        len(camera_position) == 3,
        "check=camera_position; expected=3 values; actual=" + str(len(camera_position)),
    )
    delta = [f32(f32(position[index]) - f32(camera_position[index])) for index in range(3)]
    squared = f32(
        f32(delta[0] * delta[0]) +
        f32(delta[1] * delta[1]) +
        f32(delta[2] * delta[2])
    )
    return f32_bits(squared), squared


def sort_setup_state_rows(
    rows: Sequence[Mapping[str, Any]], camera_position: Sequence[float]
) -> list[dict[str, Any]]:
    """Apply the audited SetupState priority/distance order to capture rows."""

    annotated: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        light_type = int(row["lightType"])
        require(
            light_type in (0, 2),
            f"check=setupstate_light_type; row={index}; expected=0_or_2; actual={light_type}",
        )
        distance_bits, distance = _row_distance_bits(row, camera_position)
        annotated.append(
            {
                "captureRowIndex": index,
                "lightType": light_type,
                "priority": int(row["priority"]),
                "cameraDistanceSquared": {
                    "bits": distance_bits,
                    "value": distance,
                },
            }
        )

    for left_index, left in enumerate(annotated):
        for right in annotated[left_index + 1 :]:
            if (
                left["priority"] == right["priority"] and
                left["cameraDistanceSquared"]["bits"] ==
                right["cameraDistanceSquared"]["bits"]
            ):
                raise CaptureContractError(
                    f"validator={VALIDATOR}; check=setupstate_tie; "
                    f"rows={left['captureRowIndex']},{right['captureRowIndex']}; "
                    "native sort tie-break is not source-closed"
                )

    annotated.sort(
        key=lambda item: (
            -item["priority"],
            item["cameraDistanceSquared"]["value"],
        )
    )
    return annotated


def _room_records(transport: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        row for row in transport["selection"]["records"]
        if row.get("source") == "SceneLight6Rarity"
    ]


def _match_room_row(
    row: Mapping[str, Any], room_records: Sequence[Mapping[str, Any]]
) -> list[str]:
    row_position_bits = vector_bits(row["worldPosition"])
    row_forward_bits = vector_bits(row["localToWorldColumn2"][:3])
    matches: list[str] = []
    for candidate in room_records:
        static = candidate["staticRecordTerms"]
        authored = candidate["candidate"]
        if int(static["unityLightType"]) != int(row["lightType"]):
            continue
        authored_position_bits = tuple(
            authored["worldPosition"]["bits"]
        )
        authored_forward_bits = tuple(authored["worldForward"]["bits"])
        if row_position_bits == authored_position_bits and row_forward_bits == authored_forward_bits:
            matches.append(str(candidate["name"]))
    return matches


def build_contract(
    capture_path: Path,
    camera_position: Sequence[float],
    *,
    require_selected_room: bool = True,
) -> dict[str, Any]:
    document = _load_capture_document(capture_path)
    try:
        decoded = DECODER.decode_capture(document)
    except DECODER.CaptureDecodeError as exc:
        raise CaptureContractError(
            f"validator={VALIDATOR}; check=decode_capture; source={capture_path}; {exc}"
        ) from exc

    require(
        decoded["callSite"] == "normal",
        f"check=call_site; expected=normal; actual={decoded['callSite']}",
    )
    transport = json.loads(TRANSPORT.read_text(encoding="utf-8"))
    room_records = _room_records(transport)
    require(
        len(room_records) == 11,
        f"check=source_room_records; expected=11; actual={len(room_records)}",
    )
    native_b31_payload = validate_native_b31_payload(
        document, decoded["result"]["visibleLightCount"]
    )

    room_matches: list[dict[str, Any]] = []
    unmatched_rows: list[int] = []
    ambiguous_rows: list[dict[str, Any]] = []
    for row in decoded["rows"]:
        matches = _match_room_row(row, room_records)
        if len(matches) == 1:
            room_matches.append(
                {
                    "captureRowIndex": row["index"],
                    "sourceName": matches[0],
                }
            )
        elif len(matches) == 0:
            unmatched_rows.append(row["index"])
        else:
            ambiguous_rows.append(
                {"captureRowIndex": row["index"], "matches": matches}
            )

    require(
        not ambiguous_rows,
        f"check=room_row_identity_ambiguity; actual={ambiguous_rows}",
    )
    matched_names = [item["sourceName"] for item in room_matches]
    duplicate_names = sorted(
        name for name in set(matched_names) if matched_names.count(name) > 1
    )
    require(
        not duplicate_names,
        f"check=room_row_identity_duplicate; actual={duplicate_names}",
    )
    expected_names = [row["name"] for row in room_records]
    missing_names = [name for name in expected_names if name not in matched_names]
    if require_selected_room:
        require(
            not missing_names,
            f"check=selected_room_capture_rows; expected={expected_names}; "
            f"actual={matched_names}; missing={missing_names}; "
            f"unmatchedCaptureRows={unmatched_rows}",
        )

    setup_state = sort_setup_state_rows(decoded["rows"], camera_position)
    setup_state_names = {
        item["captureRowIndex"]: next(
            (
                match["sourceName"]
                for match in room_matches
                if match["captureRowIndex"] == item["captureRowIndex"]
            ),
            None,
        )
        for item in setup_state
    }
    for item in setup_state:
        item["sourceName"] = setup_state_names[item["captureRowIndex"]]

    return {
        "schema": SCHEMA,
        "status": "authorized_target_frame_capture_intake",
        "capture": {
            "path": capture_path.as_posix(),
            "sha256": sha256(capture_path),
            "gameBuild": decoded["gameBuild"],
            "callSite": decoded["callSite"],
            "visibleLightsPtr": decoded["result"]["visibleLightsPtr"],
            "visibleLightCount": decoded["result"]["visibleLightCount"],
            "rowStrideBytes": decoded["result"]["rowStrideBytes"],
        },
        "camera": {
            "position": [f32(value) for value in camera_position],
            "positionBits": list(vector_bits(camera_position)),
        },
        "roomIdentity": {
            "matchedCount": len(room_matches),
            "expectedCount": len(expected_names),
            "matches": room_matches,
            "unmatchedCaptureRows": unmatched_rows,
            "missingSourceRows": missing_names,
        },
        "setupState": {
            "sort": "priority descending, squared camera distance ascending",
            "rowIndices": [item["captureRowIndex"] for item in setup_state],
            "rows": setup_state,
        },
        "targetFrame": {
            "pointerCountObserved": True,
            "rowsObserved": True,
            "runtimeCustomCarryIn": "identity unknown unless separately matched",
            "nativeB31Payload": native_b31_payload,
            "b31Ready": False,
            "b31BlockedBy": [
                *([] if native_b31_payload["validated"] else [
                    "native PrepareCPUData b31 payload is absent or not validated",
                    "OBB packed rows and point shadow cache indices require native producer capture",
                ]),
                "runtime/custom carry-in identity and final retail b31 publication remain open",
            ],
        },
        "sourceEvidence": {
            "authoredSurvivorTransport": TRANSPORT.relative_to(
                LAB_ROOT.parent
            ).as_posix(),
            "authoredSurvivorTransportSha256": sha256(TRANSPORT),
        },
        "boundary": {
            "closed": [
                "authorized LightCullResult pointer/count and raw 148-byte rows",
                "exact SetupState priority/distance row-index transport",
                "bit-exact identity match for captured selected room rows when present",
                "raw b31 eight-record rows when the optional build-pinned native payload validates",
            ],
            "open": [
                "unmatched runtime/custom rows",
                *([] if native_b31_payload["validated"] else [
                    "PrepareCPUData payload when the optional native capture is absent",
                ]),
                "retail b31 publication and final lighting consumer",
            ],
            "decision": "consume only after capture validation; never synthesize missing rows",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a strict Gacha LightCullResult capture contract"
    )
    parser.add_argument("capture", type=Path)
    parser.add_argument(
        "--camera-position",
        nargs=3,
        type=float,
        required=True,
        metavar=("X", "Y", "Z"),
    )
    parser.add_argument("--allow-missing-room", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    contract = build_contract(
        args.capture,
        args.camera_position,
        require_selected_room=not args.allow_missing_room,
    )
    rendered = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(
        "Gacha LightCullResult capture contract: "
        f"count={contract['capture']['visibleLightCount']}, "
        f"roomMatches={contract['roomIdentity']['matchedCount']}/"
        f"{contract['roomIdentity']['expectedCount']}, "
        f"b31Ready={contract['targetFrame']['b31Ready']}, output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
