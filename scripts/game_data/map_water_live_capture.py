"""Validate one saved Map water capture against its authored and native source.

The v1 recorder compared a managed decimal-string pointer with the numeric
source ID, then included that invalid comparison in ``complete``. The selected
live call matched source ID and scene at Setup entry. This reader retains the
legacy raw bit, marks its semantic result unknown, and recomputes the other
bounded success gates; it never rewrites the raw receipt. A v3 receipt can
independently validate the mesh-delivery row while its optional near-stop
Transform witness remains absent. A v4 receipt selects an actual position
read at Setup return and reports later selected setter samples separately.
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
    SETUP_POSITION_PROFILE,
    TRANSFORM_PROFILE,
    _bind_profile,
)
from scripts.game_data.map_water_surface_join import (
    CONTRACT as SURFACE_CONTRACT,
    validate_map_water_surface_join,
)


SCHEMA = "endfield.map-water-live-capture-validation.v3"
PROVIDER_MASK = 64
MAX_NEAR_STOP_AGE_MS = 2000


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


def _finite_position(value: Any, label: str) -> list[int | float]:
    if (not isinstance(value, list) or len(value) != 3 or
            any(type(axis) not in (int, float) or not math.isfinite(axis)
                for axis in value)):
        raise ValueError(f"map_water_live:{label}")
    return value


def validate_map_water_live_capture(
    session_root: Path, *, authored: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {"schema": SCHEMA, "status": "unresolved"}
    try:
        root = session_root.resolve(strict=True)
        staged_profile = _json(root / "private" / "map-water-manifest.json")
        profile_schema = staged_profile.get("schema")
        profile_path = {
            "endfieldCapture.mapWaterVolumeBuild.v1": DEFAULT_PROFILE,
            "endfieldCapture.mapWaterVolumeBuild.v2": TRANSFORM_PROFILE,
            "endfieldCapture.mapWaterVolumeBuild.v3": SETUP_POSITION_PROFILE,
        }.get(profile_schema)
        if profile_path is None:
            raise ValueError("map_water_live:staged-profile-schema")
        profile = _json(profile_path)
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
        allowed_receipt_schemas = {
            "endfieldCapture.mapWaterVolumeBuild.v1": (
                "endfieldCapture.mapWaterVolume.v1",
                "endfieldCapture.mapWaterVolume.v2"),
            "endfieldCapture.mapWaterVolumeBuild.v2": (
                "endfieldCapture.mapWaterVolume.v3",),
            "endfieldCapture.mapWaterVolumeBuild.v3": (
                "endfieldCapture.mapWaterVolume.v4",),
        }[profile_schema]
        if schema not in allowed_receipt_schemas:
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
        elif schema.endswith(".v2"):
            _true(receipt, "complete")

        transform_status = "not_requested"
        transform_position = None
        setup_return_position = None
        last_setter_return_position = None
        selected_set_position_calls = None
        if schema.endswith((".v3", ".v4")):
            _true(receipt, "surfaceArmed")
            for key in ("tokenMismatches", "selectedRecycleCalls",
                        "sampleContentions"):
                _zero(receipt, key)
            if schema.endswith(".v3"):
                _zero(receipt, "invalidPositionSamples")
            counters = {}
            for key in ("selectedTickCalls", "positionSamples", "firstSampleMillis",
                        "lastSampleMillis", "stopMillis", "lastSampleAgeMs",
                        "invalidPositionSamples"):
                value = receipt.get(key)
                if type(value) is not int or value < 0:
                    raise ValueError(f"map_water_live:{key}")
                counters[key] = value
            if counters["stopMillis"] == 0:
                raise ValueError("map_water_live:stopMillis")
            first_position = _finite_position(
                receipt.get("firstObservedPosition"), "firstObservedPosition")
            last_position = _finite_position(
                receipt.get("lastObservedPosition"), "lastObservedPosition")
            if schema.endswith(".v4"):
                _true(receipt, "complete")
                _true(row, "setupReturnPositionObserved")
                setup_return_millis = row.get("setupReturnPositionMillis")
                if (type(setup_return_millis) is not int or
                        not 0 < setup_return_millis <= counters["stopMillis"]):
                    raise ValueError("map_water_live:setup-return-millis")
                setup_return_position = _finite_position(
                    row.get("setupReturnPosition"), "setup-return-position")
                _zero(receipt, "invalidSetterPositionSamples")
                selected_set_position_calls = receipt.get("selectedSetPositionCalls")
                setter_samples = receipt.get("setterPositionSamples")
                if (type(selected_set_position_calls) is not int or
                        selected_set_position_calls < 0 or
                        type(setter_samples) is not int or
                        setter_samples != selected_set_position_calls):
                    raise ValueError("map_water_live:setter-samples")
                first_setter_millis = receipt.get("firstSetterSampleMillis")
                last_setter_millis = receipt.get("lastSetterSampleMillis")
                if (type(first_setter_millis) is not int or
                        type(last_setter_millis) is not int):
                    raise ValueError("map_water_live:setter-millis")
                first_setter_position = _finite_position(
                    receipt.get("firstSetterReturnPosition"),
                    "first-setter-return-position")
                last_setter_position = _finite_position(
                    receipt.get("lastSetterReturnPosition"),
                    "last-setter-return-position")
                if setter_samples == 0:
                    if (first_setter_millis, last_setter_millis,
                            first_setter_position, last_setter_position) != (
                                0, 0, [0, 0, 0], [0, 0, 0]):
                        raise ValueError("map_water_live:no-setter-sentinel")
                elif (not setup_return_millis <= first_setter_millis <=
                      last_setter_millis <= counters["stopMillis"]):
                    raise ValueError("map_water_live:setter-millis")
                else:
                    last_setter_return_position = last_setter_position
                transform_status = "setup_return_position_observed"
            elif receipt["complete"]:
                _true(receipt, "nearStopPositionFresh")
                if (counters["positionSamples"] < 2 or
                        counters["selectedTickCalls"] < counters["positionSamples"] or
                        counters["firstSampleMillis"] == 0 or
                        not counters["firstSampleMillis"] <= counters["lastSampleMillis"] <= counters["stopMillis"] or
                        counters["lastSampleAgeMs"] != counters["stopMillis"] - counters["lastSampleMillis"] or
                        counters["lastSampleAgeMs"] > MAX_NEAR_STOP_AGE_MS):
                    raise ValueError("map_water_live:near-stop-samples")
                transform_status = "near_stop_position_observed"
                transform_position = last_position
            else:
                _equal(receipt.get("nearStopPositionFresh"), False,
                       "near-stop-not-fresh")
                for key in ("selectedTickCalls", "positionSamples",
                            "firstSampleMillis", "lastSampleMillis", "lastSampleAgeMs"):
                    _zero(receipt, key)
                if first_position != [0, 0, 0] or last_position != [0, 0, 0]:
                    raise ValueError("map_water_live:no-tick-position-sentinel")
                transform_status = "no_tick_samples"

        position = _finite_position(row.get("requestedPosition"), "requested-position")
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
            status=("validated_mesh_only" if transform_status == "no_tick_samples"
                    else "validated"), sceneId=target["sceneId"],
            waterVolumeId=str(target["waterVolumeId"]),
            meshPathHash=str(target["meshPathHash"]),
            requestedPosition=position,
            postSetupWaterVolumeIdMatched=None if legacy else post_id,
            postSetupIdComparison=("legacy_pointer_compared_as_integer"
                                   if legacy else "managed_decimal_string_compared"),
            legacyRawPostSetupIdMatch=post_id if legacy else None,
            meshAssetDeliveredToUpdataMesh=True,
            transformObservationStatus=transform_status,
            nearStopObservedPosition=transform_position,
            setupReturnObservedPosition=setup_return_position,
            selectedSetPositionCalls=selected_set_position_calls,
            lastSetterReturnPosition=last_setter_return_position,
            receiptSha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest().upper(),
            evidenceBoundary=(
                "Direct selected Setup/GetMesh/UpdataMesh mesh delivery. The v1 "
                "post-Setup waterVolumeId bit compared a managed string pointer as "
                "an integer and cannot establish ID equality; final surface height "
                "and renderer visibility are not observed."
                if legacy else
                "Direct selected Setup/GetMesh/UpdataMesh mesh delivery with a "
                "managed-string post-Setup ID comparison. The selected surface "
                "had no Tick calls or Transform samples in this session; final "
                "surface height and renderer visibility are not observed."
                if transform_status == "no_tick_samples" else
                "Direct selected Setup/GetMesh/UpdataMesh mesh delivery and a "
                "near-stop post-Tick Transform position. Renderer visibility "
                "is not observed."
                if transform_status == "near_stop_position_observed" else
                "Direct selected Setup/GetMesh/UpdataMesh mesh delivery and "
                "an actual same-Mono Transform position at Setup return. "
                "Selected set_position returns are separately counted; the "
                "Setup-return position is not a final height or a renderer "
                "visibility observation."
                if transform_status == "setup_return_position_observed" else
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
