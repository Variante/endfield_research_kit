#!/usr/bin/env python3
"""Audit archived M27 c105 bytes without promoting them to a live publisher.

The admitted result is intentionally narrow: it can authenticate one draw-local
ShaderVariablesGlobal observation.  Even an admitted observation cannot replace
HGVFXManager.GetAnchorWaveBright or establish a sequence-wide default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_SESSION = (
    REPO_ROOT
    / "scratch/reverse_engineering/endfield_capture/20260826T091023Z"
)
DEFAULT_CONTRACT = (
    REPO_ROOT
    / "reports/assets/character_recovery/endminf_anchor_wave_bright_contract.json"
)
ALIGNMENT_RELATIVE_PATH = "graphics/endminf_m27_c105_source_alignment.json"
METADATA_RELATIVE_PATH = "graphics/frames/1405/metadata.json"
RUNTIME_RELATIVE_PATH = "private/EndfieldCaptureD3D11.dll"
RESULT_SCHEMA = "endfield.endminf-m27-c105-existing-session-authority.v1"
EXPECTED_SESSION_ID = "20260826T091023Z"
EXPECTED_NUMERIC_SESSION_ID = 32116871635745008
EXPECTED_FRAME = 1405
EXPECTED_GAME_BUILD = "endfield-2026-07-11-gameassembly-0c557367"
EXPECTED_TARGET_SHA256 = (
    "a9726459d9ab90cf01d7536a4250315e85ebfe12da493ac16f7bad3b68e7df99"
)
EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_VERTEX_IDENTITY = 0xC0266E7FAC0046C1
EXPECTED_PIXEL_IDENTITY = 0x92D80A93ADD9C714
EXPECTED_VERTEX_BYTES = 8148
EXPECTED_PIXEL_BYTES = 8200
EXPECTED_INDEX_COUNT = 1080
EXPECTED_INSTANCE_COUNT = 1
MAX_DIAGNOSTIC_CHARS = 512
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PINNED_ARCHIVED_HASHES = {
    "session.json": "e2fc5d2c4ab6c756c5c65563e466900540f7c693247c33e0c4875c0464c4c33a",
    "runtime.status.json": "febab4c5700566aedaa546a41ae38a551db21dfa81b5392c184a30d795ff2e6b",
    "collected/summary.json": "45322db2b5e4ad92b74d708d8390666c371a3b4c915514a29fc2f29f6e19a447",
    RUNTIME_RELATIVE_PATH: "80437e0deff3d75ff884eaed8f8caf9f525b2db760c4cf8a5935344629f08b30",
    "private/runtime.conf": "5dc027fa887ecae659cd6998683a45704164644ad229e2693661683a3f89bc15",
    "private/proxy.loaded": "4bef2df32fa677d1cc2a0a91590eff2c8006f878a659c44bd9289c2c8039b516",
    METADATA_RELATIVE_PATH: "b30127c9089d342eb8435b427c727964842ee11c22599dbb688d5c6866938e80",
}


class AuthorityError(RuntimeError):
    def __init__(self, gate: str, message: str) -> None:
        super().__init__(message)
        self.gate = gate


def _require(condition: bool, gate: str, message: str) -> None:
    if not condition:
        raise AuthorityError(gate, message)


def _load_json(path: Path, label: str, gate: str) -> dict[str, Any]:
    _require(path.is_file(), gate, f"missing {label}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityError(gate, f"invalid {label}: {exc}") from exc
    _require(isinstance(value, dict), gate, f"{label} must be an object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _validate_static_contract(path: Path) -> dict[str, Any]:
    contract = _load_json(path, "AnchorWaveBright contract", "static_contract")
    _require(
        contract.get("schema")
        == "endfield.charinfo.endminf-anchor-wave-bright-contract.v1",
        "static_contract",
        "AnchorWaveBright contract schema mismatch",
    )
    _require(
        contract.get("nativeContractClosed") is True
        and contract.get("selectedFrameValueClosed") is False
        and contract.get("safeToInventSelectedFrameValue") is False,
        "static_contract",
        "AnchorWaveBright authority boundary drift",
    )
    gate = contract.get("nativeGate")
    _require(isinstance(gate, dict), "static_contract", "native gate is missing")
    _require(gate.get("status") == "validated", "static_contract", "native gate is not validated")
    game_assembly = gate.get("gameAssembly")
    global_metadata = gate.get("globalMetadata")
    _require(
        isinstance(game_assembly, dict) and isinstance(global_metadata, dict),
        "static_contract",
        "native source identities are missing",
    )
    _require(
        game_assembly.get("sha256") == EXPECTED_GAME_ASSEMBLY_SHA256,
        "static_contract",
        "GameAssembly identity mismatch",
    )
    _require(
        global_metadata.get("sha256") == EXPECTED_METADATA_SHA256,
        "static_contract",
        "global-metadata identity mismatch",
    )
    publisher = contract.get("shaderVariablesGlobalPublisher")
    _require(isinstance(publisher, dict), "static_contract", "global publisher is missing")
    _require(
        publisher.get("method")
        == "HG.Rendering.Runtime.HGRenderPathBase.UpdateShaderVariablesGlobalVFX"
        and publisher.get("destinationByteOffset") == "0x690"
        and publisher.get("destinationRegister") == "c105",
        "static_contract",
        "c105 publisher identity or destination drift",
    )
    getter = contract.get("getterContract", {}).get("value")
    _require(
        getter
        == [
            "m_anchorPosition.x",
            "m_anchorPosition.y",
            "m_anchorRadius",
            "m_anchorBrightIntensity * (m_anchorBrightFlag ? 1.0 : 0.0)",
        ],
        "static_contract",
        "GetAnchorWaveBright equation drift",
    )
    return contract


def _validate_session_descriptor(session_root: Path) -> dict[str, Any]:
    session = _load_json(
        session_root / "session.json", "session descriptor", "session_identity"
    )
    _require(
        session.get("schema") == "endfieldCapture.session.v1",
        "session_identity",
        "session descriptor schema mismatch",
    )
    expected = {
        "sessionId": EXPECTED_SESSION_ID,
        "numericSessionId": EXPECTED_NUMERIC_SESSION_ID,
        "providers": 1,
        "graphicsProfile": "targeted",
        "evidenceLabel": "forced-d3d11",
        "gameBuild": EXPECTED_GAME_BUILD,
        "targetSha256": EXPECTED_TARGET_SHA256,
    }
    for key, wanted in expected.items():
        _require(
            session.get(key) == wanted,
            "session_identity",
            f"session {key} mismatch: expected {wanted!r}, got {session.get(key)!r}",
        )
    return session


def _validate_runtime_status(session_root: Path) -> dict[str, Any]:
    status = _load_json(
        session_root / "runtime.status.json", "runtime status", "runtime_status"
    )
    _require(
        status.get("schema") == "endfieldCapture.runtimeStatus.v1",
        "runtime_status",
        "runtime status schema mismatch",
    )
    required = {
        "runtimeMode": "d3d11-proxy",
        "graphicsSelected": True,
        "graphicsProfile": "targeted",
        "graphicsHooksInstalled": True,
        "graphicsAttached": True,
        "graphicsSequenceFrames": 49,
        "graphicsDropped": 0,
        "framePending": False,
        "frameCompleted": True,
        "frameIncomplete": False,
        "frameFailed": False,
    }
    for key, wanted in required.items():
        _require(
            status.get(key) == wanted,
            "runtime_status",
            f"runtime status {key} mismatch: expected {wanted!r}, got {status.get(key)!r}",
        )
    summary = _load_json(
        session_root / "collected" / "summary.json",
        "provider summary",
        "provider_summary",
    )
    _require(
        summary.get("schema") == "endfieldCapture.summary.v1"
        and summary.get("complete") is True
        and summary.get("dropped") == 0
        and summary.get("invalidRecords") == 0
        and summary.get("writerError") is False,
        "provider_summary",
        "provider summary is incomplete, lossy, invalid, or reports a writer error",
    )
    return status


def _inventory_map(
    session_root: Path,
    expected_artifact_hashes: dict[str, str],
) -> dict[str, dict[str, Any]]:
    inventory = _load_json(
        session_root / "collected" / "inventory.json",
        "collection inventory",
        "inventory_binding",
    )
    _require(
        inventory.get("schema") == "endfieldCapture.collection.v1",
        "inventory_binding",
        "collection inventory schema mismatch",
    )
    _require(
        inventory.get("session") == EXPECTED_SESSION_ID,
        "inventory_binding",
        "collection inventory session mismatch",
    )
    rows = inventory.get("artifacts")
    _require(isinstance(rows, list), "inventory_binding", "inventory artifacts are missing")
    _require(
        inventory.get("files") == len(rows),
        "inventory_binding",
        "inventory file count mismatch",
    )
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "inventory_binding", "invalid inventory row")
        relative = row.get("path")
        _require(
            isinstance(relative, str) and relative and relative not in result,
            "inventory_binding",
            f"invalid or duplicate inventory path: {relative!r}",
        )
        result[relative] = row
    required = (
        "session.json",
        "runtime.status.json",
        "collected/summary.json",
        RUNTIME_RELATIVE_PATH,
        "private/runtime.conf",
        "private/proxy.loaded",
        METADATA_RELATIVE_PATH,
        ALIGNMENT_RELATIVE_PATH,
    )
    for relative in required:
        row = result.get(relative)
        _require(
            row is not None,
            "inventory_binding",
            f"inventory omits required artifact: {relative}",
        )
        path = session_root / Path(relative)
        _require(path.is_file(), "inventory_binding", f"inventoried artifact is missing: {relative}")
        _require(
            row.get("bytes") == path.stat().st_size,
            "inventory_binding",
            f"inventory size mismatch: {relative}",
        )
        _require(
            row.get("sha256") == _sha256(path),
            "inventory_binding",
            f"inventory hash mismatch: {relative}",
        )
        pinned = expected_artifact_hashes.get(relative)
        if pinned is not None:
            _require(
                row.get("sha256") == pinned,
                "archived_artifact_identity",
                f"archived artifact hash drift: {relative}",
            )
    return result


def _validate_source_alignment(
    session_root: Path, session_sha256: str, metadata_sha256: str
) -> dict[str, Any]:
    alignment = _load_json(
        session_root / ALIGNMENT_RELATIVE_PATH,
        "source-frame alignment marker",
        "source_frame_alignment",
    )
    _require(
        alignment.get("schema")
        == "endfield.endminf-m27-c105-source-frame-alignment.v1",
        "source_frame_alignment",
        "source-frame alignment schema mismatch",
    )
    _require(
        alignment.get("authoritative") is True
        and alignment.get("sessionId") == EXPECTED_SESSION_ID
        and alignment.get("runtimeFrame") == EXPECTED_FRAME,
        "source_frame_alignment",
        "alignment does not authorize the exact archived session/frame",
    )
    _require(
        alignment.get("sessionSha256") == session_sha256
        and alignment.get("metadataSha256") == metadata_sha256,
        "source_frame_alignment",
        "alignment artifact hashes do not bind the archived session/frame",
    )
    reference = alignment.get("reference")
    _require(isinstance(reference, dict), "source_frame_alignment", "alignment reference is missing")
    _require(
        isinstance(reference.get("path"), str)
        and bool(reference["path"])
        and isinstance(reference.get("frame"), int)
        and reference["frame"] >= 0
        and isinstance(reference.get("sha256"), str)
        and SHA256_RE.fullmatch(reference["sha256"]) is not None,
        "source_frame_alignment",
        "alignment reference path/frame/SHA-256 is incomplete",
    )
    _require(
        isinstance(alignment.get("method"), str) and bool(alignment["method"]),
        "source_frame_alignment",
        "alignment method is missing",
    )
    return alignment


def _shader_map(draw: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = draw.get("shaders")
    _require(isinstance(rows, list), "draw_identity", "M27 draw has no shader rows")
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "draw_identity", "invalid shader row")
        stage = row.get("stage")
        _require(type(stage) is int and stage not in result, "draw_identity", "invalid or duplicate shader stage")
        result[stage] = row
    return result


def _decode_draw(metadata: dict[str, Any]) -> dict[str, Any]:
    _require(metadata.get("frame") == EXPECTED_FRAME, "draw_identity", "metadata frame mismatch")
    for key in ("captureIncomplete", "captureFailed", "drawRecordsTruncated", "resourceSelectionTruncated"):
        _require(metadata.get(key) is False, "capture_completeness", f"frame reports {key}")
    _require(metadata.get("droppedEvents") == 0, "capture_completeness", "frame reports lost events")
    _require(metadata.get("readbackHresult") == 0 and metadata.get("readbackFailure") == 0,
             "capture_completeness", "frame readback failed")
    draw_records = metadata.get("drawRecords")
    _require(isinstance(draw_records, list), "draw_identity", "frame drawRecords are missing")
    rows = [
        row
        for row in draw_records
        if isinstance(row, dict)
        and row.get("count") == EXPECTED_INDEX_COUNT
        and row.get("instanceCount") == EXPECTED_INSTANCE_COUNT
    ]
    _require(len(rows) == 1, "draw_identity", f"expected one M27 draw candidate, found {len(rows)}")
    draw = rows[0]
    required = {
        "indexedInstanced": True,
        "priorityShaderPair": True,
        "priorityM27Geometry": True,
        "startInstance": 0,
    }
    for key, wanted in required.items():
        _require(draw.get(key) == wanted, "draw_identity", f"M27 draw {key} mismatch")
    shaders = _shader_map(draw)
    for stage, identity, size, label in (
        (0, EXPECTED_VERTEX_IDENTITY, EXPECTED_VERTEX_BYTES, "vertex"),
        (4, EXPECTED_PIXEL_IDENTITY, EXPECTED_PIXEL_BYTES, "pixel"),
    ):
        row = shaders.get(stage)
        _require(row is not None, "draw_identity", f"missing {label} shader")
        _require(
            row.get("identityHash") == identity and row.get("bytecodeSize") == size,
            "draw_identity",
            f"M27 {label} shader identity drift",
        )
    bindings: dict[tuple[int, int], dict[str, Any]] = {}
    constant_buffers = draw.get("constantBuffers")
    _require(isinstance(constant_buffers, list), "draw_constants", "M27 constantBuffers are missing")
    for row in constant_buffers:
        _require(isinstance(row, dict), "draw_constants", "invalid constant-buffer row")
        key = (row.get("stage"), row.get("slot"))
        _require(key not in bindings, "draw_constants", f"duplicate constant-buffer row {key}")
        bindings[key] = row
    global_row = bindings.get((4, 1))
    _require(global_row is not None, "draw_constants", "M27 PS b1 is missing")
    _require(
        global_row.get("rangeValid") is True
        and global_row.get("metadataValid") is True
        and global_row.get("capturedConstants", 0) >= 106
        and global_row.get("truncated") is True,
        "draw_constants",
        "M27 PS b1 range is not the complete captured c0-c105 prefix",
    )
    data_hex = global_row.get("dataHex")
    _require(isinstance(data_hex, str), "draw_constants", "M27 PS b1 dataHex is missing")
    try:
        payload = bytes.fromhex(data_hex)
    except ValueError as exc:
        raise AuthorityError("draw_constants", f"M27 PS b1 dataHex is invalid: {exc}") from exc
    _require(len(payload) >= 106 * 16, "draw_constants", "M27 PS b1 payload is incomplete")
    c105_payload = payload[105 * 16 : 106 * 16]
    values = list(struct.unpack("<4f", c105_payload))
    bits = list(struct.unpack("<4I", c105_payload))
    _require(bits == [0, 0, 0, 0], "draw_constants", f"archived M27 c105 bits drifted: {bits}")
    return {
        "runtimeFrame": EXPECTED_FRAME,
        "indexCount": EXPECTED_INDEX_COUNT,
        "instanceCount": EXPECTED_INSTANCE_COUNT,
        "vertexShaderIdentity": f"{EXPECTED_VERTEX_IDENTITY:016x}",
        "pixelShaderIdentity": f"{EXPECTED_PIXEL_IDENTITY:016x}",
        "psB1FirstConstant": global_row.get("firstConstant"),
        "psB1NumConstants": global_row.get("numConstants"),
        "psB1CapturedConstants": global_row.get("capturedConstants"),
        "c105Float": values,
        "c105Bits": bits,
        "c105PayloadSha256": hashlib.sha256(c105_payload).hexdigest(),
    }


def inspect_validation_only_observation(session_root: Path) -> dict[str, Any] | None:
    try:
        metadata = _load_json(
            session_root / METADATA_RELATIVE_PATH,
            "M27 frame metadata",
            "draw_identity",
        )
        return _decode_draw(metadata)
    except (OSError, TypeError, ValueError, AuthorityError):
        return None


def verify(
    session_root: Path,
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    expected_artifact_hashes: dict[str, str] = PINNED_ARCHIVED_HASHES,
) -> dict[str, Any]:
    _validate_static_contract(contract_path)
    _validate_session_descriptor(session_root)
    _validate_runtime_status(session_root)
    inventory = _inventory_map(session_root, expected_artifact_hashes)
    metadata_path = session_root / METADATA_RELATIVE_PATH
    alignment = _validate_source_alignment(
        session_root,
        inventory["session.json"]["sha256"],
        inventory[METADATA_RELATIVE_PATH]["sha256"],
    )
    metadata = _load_json(metadata_path, "M27 frame metadata", "draw_identity")
    draw = _decode_draw(metadata)
    return {
        "schema": RESULT_SCHEMA,
        "status": "admitted_draw_local_validation_receipt",
        "sessionId": EXPECTED_SESSION_ID,
        "sourceAlignment": {
            "runtimeFrame": EXPECTED_FRAME,
            "reference": alignment["reference"],
            "method": alignment["method"],
        },
        "drawLocalObservation": draw,
        "authority": {
            "drawLocalC105Receipt": True,
            "capturedConstantsUsedAsProducerSource": False,
            "liveHGVFXManagerSourceClosed": False,
            "sequenceWideDefaultAuthorized": False,
            "canonicalM27PublisherCanBePopulated": False,
            "presentationAuthority": False,
        },
        "boundary": (
            "This admits only c105 bytes observed at one aligned exact M27 draw. "
            "It does not prove the HGVFXManager field lifecycle, setter call, or "
            "values at any neighboring frame."
        ),
    }


def _rejected_result(
    exc: BaseException, observation: dict[str, Any] | None
) -> dict[str, Any]:
    reason = str(exc).replace("\r", " ").replace("\n", " ")[:MAX_DIAGNOSTIC_CHARS]
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "status": "rejected",
        "validator": "verify_endminf_m27_c105_existing_session",
        "failedGate": getattr(exc, "gate", "unexpected_error"),
        "reason": reason,
        "sessionId": EXPECTED_SESSION_ID,
        "authority": {
            "drawLocalC105Receipt": False,
            "capturedConstantsUsedAsProducerSource": False,
            "liveHGVFXManagerSourceClosed": False,
            "sequenceWideDefaultAuthorized": False,
            "canonicalM27PublisherCanBePopulated": False,
            "presentationAuthority": False,
        },
    }
    if observation is not None:
        result["validationOnlyObservation"] = observation
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_root", type=Path, nargs="?", default=DEFAULT_SESSION)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.session_root, args.contract)
    except (OSError, KeyError, TypeError, ValueError, AuthorityError) as exc:
        result = _rejected_result(exc, inspect_validation_only_observation(args.session_root))
        print(
            "Endminf M27 c105 existing-session authority failed "
            f"[{result['failedGate']}]: {result['reason']}",
            file=sys.stderr,
        )
        if args.output:
            try:
                _write_json(args.output, result)
            except OSError as output_exc:
                print(f"failed to write rejection report: {output_exc}", file=sys.stderr)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if args.output:
        _write_json(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
