"""Validate one saved Map water capture against its authored and native source.

The v1 recorder compared a managed decimal-string pointer with the numeric
source ID, then included that invalid comparison in ``complete``. The selected
live call matched source ID and scene at Setup entry. This reader retains the
legacy raw bit, marks its semantic result unknown, and recomputes the other
bounded success gates; it never rewrites the raw receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from scripts.game_data.map_water_capture_preflight import (
    DEFAULT_PROFILE,
    NATIVE_CONTRACT,
    _bind_profile,
)
from scripts.game_data.map_water_surface_join import (
    CONTRACT as SURFACE_CONTRACT,
    validate_map_water_surface_join,
)


SCHEMA = "endfield.map-water-live-capture-validation.v1"
PROVIDER_MASK = 64


def _json(path: Path, limit: int = 128 * 1024) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"map_water_live:missing-or-oversized:{path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"map_water_live:not-an-object:{path.name}")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"map_water_live:{label}")


def _true(value: dict[str, Any], key: str) -> None:
    _equal(value.get(key), True, key)


def _zero(value: dict[str, Any], key: str) -> None:
    _equal(value.get(key), 0, key)


def validate_map_water_live_capture(
    session_root: Path, *, authored: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {"schema": SCHEMA, "status": "unresolved"}
    try:
        root = session_root.resolve(strict=True)
        profile = _json(DEFAULT_PROFILE)
        staged_profile = _json(root / "private" / "map-water-manifest.json")
        _equal(staged_profile, profile, "staged-profile")
        native = _json(NATIVE_CONTRACT)
        surface_contract = _json(SURFACE_CONTRACT)
        _bind_profile(profile, native, surface_contract)
        if authored is None:
            authored = validate_map_water_surface_join()
        if authored.get("status") != "validated":
            raise ValueError("map_water_live:authored-gate:" +
                             str(authored.get("diagnostic") or authored.get("status")))

        session = _json(root / "session.json")
        _equal(session.get("schema"), "endfieldCapture.session.v1", "session-schema")
        _equal(session.get("sessionId"), root.name, "session-id")
        _equal(session.get("providers"), PROVIDER_MASK, "provider-mask")
        _equal(session.get("gameBuild"), profile["gameBuild"], "game-build")
        _equal(session.get("targetSha256", "").upper(),
               profile["files"]["executable"]["sha256"].upper(), "executable-sha256")
        staged_runtime = root / "private" / "EndfieldCapture.dll"
        runtime_hash = hashlib.sha256(staged_runtime.read_bytes()).hexdigest().upper()
        _equal(session.get("runtimeSha256", "").upper(), runtime_hash, "runtime-sha256")
        number = session.get("numericSessionId")
        if type(number) is not int or number <= 0:
            raise ValueError("map_water_live:numeric-session-id")
        if not (root / "runtime.ready").is_file() or (root / "runtime.error").exists():
            raise ValueError("map_water_live:runtime-state")

        collected = _json(root / "collected" / "summary.json")
        _equal(collected.get("schema"), "endfieldCapture.summary.v1", "collected-schema")
        _true(collected, "complete")
        _equal(collected.get("records"), 2, "event-count")
        for key in ("dropped", "invalidRecords"):
            _zero(collected, key)
        _equal(collected.get("writerError"), False, "writer-error")
        events = [json.loads(line) for line in (root / "events.jsonl").read_text(
            encoding="utf-8").splitlines() if line]
        if len(events) != 2:
            raise ValueError("map_water_live:event-rows")
        for index, event in enumerate(events, 1):
            if (event.get("provider"), event.get("type"), event.get("sessionId"),
                    event.get("producerSequence"), event.get("writerSequence")) != (
                        PROVIDER_MASK, index, number, index, index):
                raise ValueError(f"map_water_live:event-{index}")

        receipt_path = root / "map-water-volume" / "receipt.json"
        receipt = _json(receipt_path)
        schema = receipt.get("schema")
        if schema not in ("endfieldCapture.mapWaterVolume.v1",
                          "endfieldCapture.mapWaterVolume.v2"):
            raise ValueError("map_water_live:receipt-schema")
        target = profile["capture"]
        for key in ("sceneId", "waterVolumeId"):
            _equal(receipt.get(key), target[key], f"receipt-{key}")
        _equal(receipt.get("expectedMeshPathHash"), target["meshPathHash"],
               "expected-mesh-hash")
        _true(receipt, "hooksInstalled")
        _true(receipt, "quiescentCleanup")
        for key in ("targetSetupCalls", "getMeshCalls", "published"):
            _equal(receipt.get(key), 1, key)
        for key in ("wrongSceneCalls", "capacityRejections", "unreadableIdentity",
                    "invalidPositions", "nestedRejections"):
            _zero(receipt, key)
        for key, file_key in (("nativeGameAssemblySha256", "gameAssembly"),
                              ("nativeMetadataSha256", "metadata"),
                              ("nativeUnityPlayerSha256", "unityPlayer")):
            _equal(receipt.get(key, "").upper(),
                   profile["files"][file_key]["sha256"].upper(), key)

        rows = receipt.get("observations")
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise ValueError("map_water_live:one-observation")
        row = rows[0]
        for key in ("sceneId", "waterVolumeId"):
            _equal(row.get(key), target[key], f"observation-{key}")
        _equal(row.get("requestedMeshPathHash"), target["meshPathHash"],
               "requested-mesh-hash")
        if type(row.get("threadId")) is not int or row["threadId"] <= 0:
            raise ValueError("map_water_live:thread-id")
        for key in ("getMeshReturned", "updataMeshCalled", "updataMeshAssetNonnull",
                    "updataMeshReceiverMatchesReturn", "storedHashMatchesAfterSetup",
                    "surfaceMonoMatchesReturnAfterSetup", "assetSuccess"):
            _true(row, key)
        post_id = row.get("waterVolumeIdMatchesAfterSetup")
        if type(post_id) is not bool or type(receipt.get("complete")) is not bool:
            raise ValueError("map_water_live:completion-shape")
        if schema.endswith(".v1"):
            _equal(receipt["complete"], post_id, "legacy-completion")
        else:
            _true(receipt, "complete")

        position = row.get("requestedPosition")
        if (not isinstance(position, list) or len(position) != 3 or
                any(type(value) not in (int, float) or not math.isfinite(value)
                    for value in position)):
            raise ValueError("map_water_live:requested-position")
        authored_row = authored["waterSurface"]
        expected_position = [authored_row["pivot"][0],
                             authored["conditionalInitialPlane"]["requestedPlaneY"],
                             authored_row["pivot"][2]]
        if max(abs(float(a) - float(b)) for a, b in zip(position, expected_position)) > 0.001:
            raise ValueError("map_water_live:authored-position-join")
        _equal(str(target["waterVolumeId"]), str(authored_row["waterVolumeId"]),
               "authored-volume-id")
        _equal(str(target["meshPathHash"]), str(authored_row["meshPathHash"]),
               "authored-mesh-hash")

        legacy = schema.endswith(".v1")
        report.update(
            status="validated", sceneId=target["sceneId"],
            waterVolumeId=str(target["waterVolumeId"]),
            meshPathHash=str(target["meshPathHash"]),
            requestedPosition=position,
            postSetupWaterVolumeIdMatched=None if legacy else post_id,
            postSetupIdComparison=("legacy_pointer_compared_as_integer"
                                   if legacy else "managed_decimal_string_compared"),
            legacyRawPostSetupIdMatch=post_id if legacy else None,
            meshAssetDeliveredToUpdataMesh=True,
            receiptSha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest().upper(),
            evidenceBoundary=(
                "Direct selected Setup/GetMesh/UpdataMesh mesh delivery. The v1 "
                "post-Setup waterVolumeId bit compared a managed string pointer as "
                "an integer and cannot establish ID equality; final surface height "
                "and renderer visibility are not observed."
                if legacy else
                "Direct selected Setup/GetMesh/UpdataMesh mesh delivery with a "
                "managed-string post-Setup ID comparison; final surface height "
                "and renderer visibility are not observed."
            ),
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        report["diagnostic"] = str(exc)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_map_water_live_capture(args.session_root)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
