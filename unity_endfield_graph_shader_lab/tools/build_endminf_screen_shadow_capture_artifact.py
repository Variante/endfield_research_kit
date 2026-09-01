#!/usr/bin/env python3
"""Build a diagnostic-only Endminf retail t11 payload artifact.

The strict screen-shadow capture verifier remains the admission authority. This
builder accepts only its single fully validated packet, then independently
rejoins and hashes the three raw draw-local RG8 payloads before emitting the
producer-2 payload. The artifact is evidence for bounded replay only; it does
not authorize presentation or certify the Unity procedural producer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import verify_endminf_screen_shadow_capture as VERIFIER


SCHEMA = "endfield.endminf-screen-shadow-capture-artifact.v1"
MANIFEST_NAME = "endminf_screen_shadow_t11_artifact.json"
PAYLOAD_NAME = "endminf_screen_shadow_t11_p2_rg8_3840x2160.bytes"
WIDTH = 3840
HEIGHT = 2160
BYTES_PER_PIXEL = 2
EXPECTED_BYTES = WIDTH * HEIGHT * BYTES_PER_PIXEL
TEXTURE_FORMATS = {48, 49}  # DXGI R8G8_Typeless / R8G8_UNorm
VIEW_FORMAT = 49  # DXGI R8G8_UNorm
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ArtifactError(RuntimeError):
    pass


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ArtifactError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactError(f"{path} must contain one JSON object")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactError(message)


def _require_sha256(value: Any, label: str) -> str:
    _require(isinstance(value, str) and HEX64.fullmatch(value) is not None,
             f"{label} is not a lowercase SHA-256")
    return value


def _resolve_contained(root: Path, candidate: Path, label: str) -> Path:
    root = root.resolve(strict=True)
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ArtifactError(f"{label} escapes the authenticated capture") from exc
    current = root
    for part in relative.parts:
        _require(part not in ("", ".", ".."),
                 f"{label} contains a non-normal path component")
        current = current / part
        _require(not current.is_symlink(), f"{label} contains a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ArtifactError(f"{label} is unavailable: {exc}") from exc
    _require(resolved == current.resolve(strict=True),
             f"{label} changed while resolving")
    return resolved


def _require_no_symlink_components(path: Path, label: str) -> None:
    absolute = path.absolute()
    for candidate in (absolute, *absolute.parents):
        if candidate.exists():
            _require(not candidate.is_symlink(),
                     f"{label} contains a symlink component: {candidate}")


def _normalized_child(parent: Path, value: Any, label: str) -> Path:
    _require(isinstance(value, str) and value != "", f"{label} is missing")
    relative = Path(value)
    _require(not relative.is_absolute() and "\\" not in value and
             all(part not in ("", ".", "..") for part in relative.parts),
             f"{label} is not a normalized relative path")
    return _resolve_contained(parent, parent / relative, label)


def _record_by_name(candidate: dict[str, Any], name: str) -> dict[str, Any]:
    rows = [row for row in candidate.get("records", [])
            if isinstance(row, dict) and row.get("name") == name]
    _require(len(rows) == 1, f"validated report has {len(rows)} {name} records")
    return rows[0]


def _selected_row(metadata: dict[str, Any], report_row: dict[str, Any],
                  label: str) -> dict[str, Any]:
    keys = (
        "objectId", "slot", "deferredOwner", "deferredCopyPhase",
        "deferredOwnerOccurrence", "deferredUnifiedCallOrdinal",
        "deferredPresentEpoch", "blobOffset", "blobBytes",
    )
    matches = [
        row for row in metadata.get("selectedResourceRecords", [])
        if isinstance(row, dict) and all(row.get(key) == report_row.get(key)
                                         for key in keys)
    ]
    _require(len(matches) == 1,
             f"{label} does not rejoin exactly one selected resource row")
    row = matches[0]
    _require(row.get("captureKind") == 3 and row.get("resourceKind") == 1 and
             row.get("stage") == 4 and row.get("subresource") == 0,
             f"{label} capture identity is invalid")
    _require(row.get("width") == WIDTH and row.get("height") == HEIGHT,
             f"{label} dimensions are not {WIDTH}x{HEIGHT}")
    _require(row.get("format") in TEXTURE_FORMATS and
             row.get("viewFormat") == VIEW_FORMAT,
             f"{label} is not an R8G8_UNorm-compatible capture")
    for key in ("byteSize", "requestedBytes", "blobBytes"):
        _require(row.get(key) == EXPECTED_BYTES,
                 f"{label} {key} is not {EXPECTED_BYTES}")
    _require(row.get("attempted") is True and row.get("completed") is True and
             row.get("failure") == 0 and row.get("hresult") == 0,
             f"{label} readback is incomplete or failed")
    return row


def _payload(blob: bytes, row: dict[str, Any], label: str) -> bytes:
    offset = row.get("blobOffset")
    size = row.get("blobBytes")
    _require(isinstance(offset, int) and not isinstance(offset, bool) and offset >= 0,
             f"{label} blob offset is invalid")
    _require(size == EXPECTED_BYTES, f"{label} blob size is invalid")
    end = offset + size
    _require(end <= len(blob), f"{label} payload exceeds resources.bin")
    return blob[offset:end]


def _channel_summary(payload: bytes, channel: int) -> dict[str, int]:
    histogram = [0] * 256
    for value in payload[channel::BYTES_PER_PIXEL]:
        histogram[value] += 1
    present = [value for value, count in enumerate(histogram) if count]
    return {
        "minimum": present[0],
        "maximum": present[-1],
        "distinctValues": len(present),
        "neutral255Pixels": histogram[255],
        "zeroPixels": histogram[0],
    }


def _summaries(payload: bytes) -> dict[str, dict[str, int]]:
    return {"r": _channel_summary(payload, 0),
            "g": _channel_summary(payload, 1)}


def _validate_authentication(capture: Path, report: dict[str, Any]) -> dict[str, str]:
    authentication = report.get("authentication")
    _require(isinstance(authentication, dict),
             "validated report has no authentication object")
    game_build = authentication.get("gameBuild")
    _require(game_build == VERIFIER.EXPECTED_GAME_BUILD,
             f"game build is not pinned to {VERIFIER.EXPECTED_GAME_BUILD}")
    runtime_sha = _require_sha256(authentication.get("runtimeSha256"),
                                  "runtimeSha256")
    target_sha = _require_sha256(authentication.get("targetSha256"),
                                 "targetSha256")
    inventory_sha = _require_sha256(authentication.get("inventorySha256"),
                                    "inventorySha256")

    session_path = _resolve_contained(capture, capture / "session.json", "session.json")
    inventory_path = _resolve_contained(
        capture, capture / "collected" / "inventory.json", "collector inventory")
    session = _load_json(session_path)
    _require(session.get("schema") == "endfieldCapture.session.v1",
             "session schema is invalid")
    _require(session.get("gameBuild") == game_build and
             session.get("runtimeSha256") == runtime_sha and
             session.get("targetSha256") == target_sha,
             "session identity differs from the validated report")
    _require(_sha256_file(inventory_path) == inventory_sha,
             "collector inventory hash differs from the validated report")
    return {
        "gameBuild": game_build,
        "runtimeSha256": runtime_sha,
        "targetSha256": target_sha,
        "inventorySha256": inventory_sha,
    }


def _validate_inventory_resource(capture: Path, resource_path: Path,
                                 payload: bytes) -> None:
    inventory = _load_json(capture / "collected" / "inventory.json")
    relative = resource_path.relative_to(capture).as_posix()
    rows = [row for row in inventory.get("artifacts", [])
            if isinstance(row, dict) and row.get("path") == relative]
    _require(len(rows) == 1,
             "resources payload is not uniquely authenticated by the inventory")
    row = rows[0]
    _require(row.get("bytes") == len(payload),
             "resources payload byte count differs from the inventory")
    expected_sha = _require_sha256(row.get("sha256"), "resources inventory SHA-256")
    _require(_sha256_bytes(payload) == expected_sha,
             "resources payload hash differs from the inventory")


def build_artifact(capture: Path, output_dir: Path) -> dict[str, Any]:
    _require_no_symlink_components(capture, "capture path")
    capture = capture.resolve(strict=True)
    _require_no_symlink_components(output_dir, "output directory")
    output_resolved = output_dir.resolve(strict=False)
    try:
        output_resolved.relative_to(capture)
    except ValueError:
        pass
    else:
        raise ArtifactError(
            "output directory must be outside the authenticated capture"
        )
    report = VERIFIER.build_report(capture)
    _require(report.get("schema") == "endfield.endminf-screen-shadow-capture.v1",
             "strict verifier report schema is invalid")
    _require(report.get("status") == "validated" and
             report.get("failures") == [],
             "strict verifier did not fully validate the capture")
    candidates = report.get("candidates")
    _require(report.get("candidateCount") == 1 and
             report.get("validCandidateCount") == 1 and
             isinstance(candidates, list) and len(candidates) == 1,
             "strict verifier did not select exactly one valid candidate")
    candidate = candidates[0]
    _require(isinstance(candidate, dict) and candidate.get("valid") is True and
             candidate.get("failures") == [],
             "selected verifier candidate is not fully valid")
    content = candidate.get("content")
    required_content = (
        "producer1ToProducer2Changed", "sceneRPreserved",
        "characterGChanged", "producer2EqualsConsumer",
    )
    _require(isinstance(content, dict) and
             all(content.get(key) is True for key in required_content),
             "validated report content gates are incomplete")

    identity = _validate_authentication(capture, report)
    frame_directory = candidate.get("frameDirectory")
    _require(isinstance(frame_directory, str) and frame_directory != "",
             "validated report frame directory is missing")
    frame = _resolve_contained(capture, Path(frame_directory),
                               "validated frame directory")
    _require(frame.is_dir(), "validated frame directory is not a directory")
    metadata_path = _resolve_contained(frame, frame / "metadata.json", "metadata.json")
    metadata = _load_json(metadata_path)
    _require(metadata.get("schema") == VERIFIER.SCHEMA,
             "frame metadata schema is invalid")
    resource_path = _normalized_child(frame, metadata.get("resourcesFile"),
                                      "resourcesFile")
    try:
        resource_blob = resource_path.read_bytes()
    except OSError as exc:
        raise ArtifactError(f"cannot read authenticated resources payload: {exc}") from exc
    _validate_inventory_resource(capture, resource_path, resource_blob)

    report_rows = {
        "producer1After": _record_by_name(candidate, "producer1After"),
        "producer2After": _record_by_name(candidate, "producer2After"),
        "consumerT11Before": _record_by_name(candidate, "consumerT11Before"),
    }
    selected_rows = {
        name: _selected_row(metadata, row, name)
        for name, row in report_rows.items()
    }
    p1_row = selected_rows["producer1After"]
    p2_row = selected_rows["producer2After"]
    consumer_row = selected_rows["consumerT11Before"]
    _require(
        p1_row.get("objectId") == p2_row.get("objectId")
        == consumer_row.get("objectId"),
        "selected producer/consumer object identity differs",
    )
    _require(
        p1_row.get("deferredOwner") == VERIFIER.SCREEN_SHADOW_OUTPUT_OWNER
        and p1_row.get("deferredCopyPhase") == VERIFIER.COPY_AFTER_OWNER
        and p1_row.get("deferredOwnerOccurrence") == 1
        and p2_row.get("deferredOwner") == VERIFIER.SCREEN_SHADOW_OUTPUT_OWNER
        and p2_row.get("deferredCopyPhase") == VERIFIER.COPY_AFTER_OWNER
        and p2_row.get("deferredOwnerOccurrence") == 2
        and p1_row.get("slot") == p2_row.get("slot")
        and isinstance(p1_row.get("slot"), int)
        and p1_row["slot"] >= VERIFIER.OUTPUT_SLOT_BASE,
        "selected producer ownership identity is invalid",
    )
    _require(
        consumer_row.get("deferredOwner") == VERIFIER.DEFAULT_OWNER
        and consumer_row.get("deferredCopyPhase") == VERIFIER.COPY_BEFORE_OWNER
        and consumer_row.get("slot") == VERIFIER.SCREEN_SHADOW_SLOT,
        "selected consumer ownership identity is invalid",
    )
    payloads = {
        name: _payload(resource_blob, row, name)
        for name, row in selected_rows.items()
    }

    for name, payload in payloads.items():
        digest = _sha256_bytes(payload)
        _require(report_rows[name].get("sha256") == digest,
                 f"{name} SHA-256 differs from the validated report")
        _require(report_rows[name].get("channels") == _summaries(payload),
                 f"{name} channel summary differs from the validated report")

    p1 = payloads["producer1After"]
    p2 = payloads["producer2After"]
    consumer = payloads["consumerT11Before"]
    _require(p1 != p2, "producer-1 and producer-2 payloads are identical")
    _require(p1[0::2] == p2[0::2], "producer-2 does not preserve scene-shadow R")
    _require(p1[1::2] != p2[1::2], "producer-2 does not change character-shadow G")
    _require(p2 == consumer, "producer-2 and consumer-before t11 bytes differ")
    p1_summary = _summaries(p1)
    p2_summary = _summaries(p2)
    _require(p1_summary["r"]["distinctValues"] >= 2,
             "producer-1 scene-shadow R is constant")
    _require(p2_summary["g"]["distinctValues"] >= 2,
             "producer-2 character-shadow G is constant")

    epochs = {row.get("deferredPresentEpoch") for row in selected_rows.values()}
    _require(len(epochs) == 1 and None not in epochs and 0 not in epochs,
             "selected payload Present epochs are invalid")
    ordinals = [selected_rows[name].get("deferredUnifiedCallOrdinal") for name in
                ("producer1After", "producer2After", "consumerT11Before")]
    _require(all(isinstance(value, int) and not isinstance(value, bool)
                 for value in ordinals) and ordinals[0] < ordinals[1] < ordinals[2],
             "selected payload chronology is invalid")

    payload_sha = _sha256_bytes(p2)
    records = {}
    for name in ("producer1After", "producer2After", "consumerT11Before"):
        records[name] = {
            "sha256": _sha256_bytes(payloads[name]),
            "callOrdinal": selected_rows[name]["deferredUnifiedCallOrdinal"],
            "presentEpoch": selected_rows[name]["deferredPresentEpoch"],
            "channels": _summaries(payloads[name]),
        }
    manifest = {
        "schema": SCHEMA,
        "gameBuild": identity["gameBuild"],
        "runtimeSha256": identity["runtimeSha256"],
        "targetSha256": identity["targetSha256"],
        "inventorySha256": identity["inventorySha256"],
        "texture": {
            "width": WIDTH,
            "height": HEIGHT,
            "graphicsFormat": "R8G8_UNorm",
            "bytesPerPixel": BYTES_PER_PIXEL,
            "nativeRowOrder": "captured-native-no-flip",
        },
        "presentEpoch": next(iter(epochs)),
        "records": records,
        "payload": {
            "filename": PAYLOAD_NAME,
            "bytes": len(p2),
            "sha256": payload_sha,
            "source": "producer2After",
        },
        "presentationAuthorized": False,
        "proceduralProducerCertified": False,
        "diagnosticReplayOnly": True,
    }

    output_resolved.mkdir(parents=True, exist_ok=True)
    _require(output_resolved.is_dir() and not output_resolved.is_symlink(),
             "output directory is unavailable or is a symlink")
    payload_path = output_resolved / PAYLOAD_NAME
    manifest_path = output_resolved / MANIFEST_NAME
    _require(not payload_path.is_symlink() and not manifest_path.is_symlink(),
             "output artifact path is a symlink")
    payload_path.write_bytes(p2)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = build_artifact(args.capture, args.output_dir)
    except (OSError, ValueError, ArtifactError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(args.output_dir / MANIFEST_NAME)
    print(args.output_dir / PAYLOAD_NAME)
    print(manifest["payload"]["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
