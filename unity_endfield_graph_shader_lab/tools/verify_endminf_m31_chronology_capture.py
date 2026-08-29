#!/usr/bin/env python3
"""Validate the exact Endminf M31 three-draw chronology sidecar."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_OBSERVER_SHA256 = (
    "3EC03A67FD2ACE782AF51DD34483EDD75468A0A829851E7C23344BC9FEE1B35B")
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_draw_contract_capture",
    HERE / "verify_endminf_draw_contract_capture.py")
assert SPEC and SPEC.loader
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


class ChronologyError(RuntimeError):
    pass


# Exact pairs already maintained by EndfieldCapture's owner gates. Shared
# VFXBaseV2 bytecode is deliberately labelled as a family: constants and
# resources, not the shader pair alone, distinguish M14/M20/M30/M31.
OWNER_SHADER_PAIRS = {
    (0xE8F38F2F7519383D, 0xFEA38543389B6FF4): "M20",
    (0x04BEF98C73CA34880, 0x246A0F4F2D3C34F4): "M20Instanced",
    (0xE7F5568D34FD467B, 0xC5B21FEE8E9936A6): "M21",
    (0x7D1953E7B7D5310F, 0x601242F701CB4380): "M18",
    (0x7F5111CF80387BEE, 0xA3C9BFC94F0CAEA9): "M28",
    (0xCE755059DEDDC2E0, 0xF2AD2A14856044AC): "M29",
    (0x96A93DCB3965CBED, 0x0265C7A6806A095F): "M13",
    (0xC0266E7FAC0046C1, 0x92D80A93ADD9C714): "M27",
    (0x297E7323CB0A7C42, 0x76DB04F0BC22DD3E): "OpeningStrip",
    (0xA8C084C37EBA0ECC, 0xDE96A55F118305EA): "NormalUber",
    (0xF246D3A8B632882E, 0x6481DAAB2B862054): "SphereOutside",
    (0x62A5CE6C09171DE9, 0x5558DEDDB1EE6188): "VFXBaseV2Shared",
}


def classify_owner(kind: int, vertex_shader: int,
                   pixel_shader: int) -> str | None:
    if kind == 4:
        return None
    return OWNER_SHADER_PAIRS.get((vertex_shader, pixel_shader))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ChronologyError(message)


def integer(value: Any, label: str, minimum: int = 0) -> int:
    require(isinstance(value, int) and not isinstance(value, bool) and
            value >= minimum, f"{label} is not an integer >= {minimum}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_summary(capture: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    session = BASE.validate_session(capture)
    path = capture / "graphics/summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    true_fields = (
        "m31ChronologyRequested", "m31ChronologyTriggered",
        "m31ChronologyTriadComplete", "m31ChronologyGpuComplete",
        "m31ChronologyPublished")
    for field in true_fields:
        require(summary.get(field) is True,
                f"graphics summary {field} gate is not true")
    require(summary.get("m31ChronologyFailed") is False,
            "graphics summary reports M31 chronology failure")
    require(summary.get("m31ChronologyCensusTruncated") is False,
            "graphics summary reports a truncated M31 chronology census")
    require(integer(summary.get("m31ChronologyFailureHresult"),
                    "M31 chronology failure HRESULT") == 0,
            "graphics summary reports a nonzero M31 chronology HRESULT")
    count = integer(summary.get("m31ChronologyCensusCount"),
                    "M31 chronology census count")
    require(count <= 64, "M31 chronology census count exceeds capacity 64")
    staging = integer(summary.get("m31ChronologyStagingBytes"),
                      "M31 chronology staging bytes", 1)
    return session, {field: summary[field] for field in true_fields} | {
        "m31ChronologyFailed": False,
        "m31ChronologyCensusCount": count,
        "m31ChronologyCensusTruncated": False,
        "m31ChronologyStagingBytes": staging,
        "m31ChronologyFailureHresult": 0,
    }


def validate_target(row: Any, label: str, width: int, height: int,
                    expected: dict[str, int]) -> dict[str, Any]:
    require(isinstance(row, dict), f"{label} descriptor is absent")
    require(row.get("bound") is True, f"{label} is not bound")
    result = {"bound": True}
    for field in ("viewId", "resourceId"):
        result[field] = integer(row.get(field), f"{label} {field}", 1)
    for field in ("width", "height", "textureFormat", "viewFormat",
                  "viewDimension", "sampleCount", "sampleQuality", "flags"):
        result[field] = integer(row.get(field), f"{label} {field}")
    require(result["width"] == width and result["height"] == height,
            f"{label} dimensions differ from {width}x{height}")
    for field, value in expected.items():
        require(result[field] == value,
                f"{label} {field} differs from expected {value}")
    return result


def changed_bytes(left: Path, right: Path) -> int:
    changed = 0
    with left.open("rb") as before, right.open("rb") as after:
        while True:
            a = before.read(1024 * 1024)
            b = after.read(1024 * 1024)
            require(len(a) == len(b),
                    f"blob sizes differ: {left.name}, {right.name}")
            if not a:
                return changed
            changed += sum(x != y for x, y in zip(a, b))


def build_report(capture: Path, *,
                 expected_observer_sha256: str = DEFAULT_OBSERVER_SHA256,
                 expected_width: int = 3840,
                 expected_height: int = 2160) -> dict[str, Any]:
    capture = capture.resolve()
    observer = capture / "private/EndfieldCapture.dll"
    require(observer.is_file(), f"captured observer binary is absent: {observer}")
    observed_sha = sha256(observer)
    require(observed_sha == expected_observer_sha256.upper(),
            "captured observer SHA-256 differs from the corrected M31 "
            f"chronology build: expected {expected_observer_sha256.upper()}, "
            f"observed {observed_sha}")
    session, summary = validate_summary(capture)

    root = capture / "graphics/m31_chronology"
    metadata_path = root / "metadata.json"
    require(metadata_path.is_file(),
            f"M31 chronology metadata is absent: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    require(metadata.get("schema") == "endfieldCapture.m31Chronology.v1",
            "M31 chronology metadata schema is invalid")
    require(metadata.get("observationOnly") is True,
            "M31 chronology observation-only gate is false")
    require(metadata.get("originalCallsForwardedExactlyOnce") is True,
            "M31 chronology exact-forwarding gate is false")
    require(metadata.get("complete") is True,
            "M31 chronology metadata complete gate is false")
    require(metadata.get("triad") == [1082, 443, 32],
            "M31 chronology base-vertex triad is not [1082, 443, 32]")
    require(integer(metadata.get("censusCapacity"), "census capacity") == 64,
            "M31 chronology census capacity is not 64")
    census_count = integer(metadata.get("censusCount"), "census count")
    require(census_count == summary["m31ChronologyCensusCount"],
            "metadata and graphics-summary census counts differ")
    require(metadata.get("censusTruncated") is False,
            "M31 chronology metadata reports a truncated census")
    require(integer(metadata.get("reservedStagingBytes"),
                    "reserved staging bytes", 1) ==
            summary["m31ChronologyStagingBytes"],
            "metadata and graphics-summary staging byte counts differ")

    targets = metadata.get("targets")
    require(isinstance(targets, list) and len(targets) == 3,
            "M31 chronology metadata does not contain three target rows")
    validated_targets = []
    for index, row in enumerate(targets):
        require(isinstance(row, dict) and row.get("drawIndex") == index,
                f"M31 target row {index} has the wrong drawIndex")
        validated_targets.append({
            "drawIndex": index,
            "rtv0": validate_target(row.get("rtv0"), f"draw {index} RTV0",
                expected_width, expected_height,
                {"textureFormat": 26, "viewFormat": 26,
                 "viewDimension": 4, "sampleCount": 1,
                 "sampleQuality": 0, "flags": 0}),
            "rtv1": validate_target(row.get("rtv1"), f"draw {index} RTV1",
                expected_width, expected_height,
                {"viewDimension": 4, "sampleCount": 1,
                 "sampleQuality": 0, "flags": 0}),
            "dsv": validate_target(row.get("dsv"), f"draw {index} DSV",
                expected_width, expected_height,
                {"textureFormat": 19, "viewFormat": 20,
                 "viewDimension": 3, "sampleCount": 1,
                 "sampleQuality": 0}),
        })
        require(validated_targets[-1]["rtv1"]["textureFormat"] > 0 and
                validated_targets[-1]["rtv1"]["viewFormat"] > 0,
                f"draw {index} RTV1 has an invalid format")
        require(validated_targets[-1]["dsv"]["flags"] in (1, 3),
                f"draw {index} DSV flags do not make depth read-only")
    for name in ("rtv0", "rtv1", "dsv"):
        require(all(row[name] == validated_targets[0][name]
                    for row in validated_targets[1:]),
                f"{name.upper()} descriptor changed across the M31 triad")

    census = metadata.get("census")
    require(isinstance(census, list) and len(census) == census_count,
            "M31 chronology census length differs from censusCount")
    argument_counts = {0: 2, 1: 3, 2: 4, 3: 5, 4: 3}
    validated_census = []
    for index, row in enumerate(census):
        require(isinstance(row, dict), f"census row {index} is not an object")
        kind = integer(row.get("kind"), f"census row {index} kind")
        require(kind in argument_counts, f"census row {index} kind is invalid")
        after = integer(row.get("afterM31Draw"),
                        f"census row {index} afterM31Draw")
        require(after in (1, 2),
                f"census row {index} is not between M31 triad draws")
        arguments = row.get("arguments")
        require(isinstance(arguments, list) and
                len(arguments) == argument_counts[kind] and
                all(isinstance(value, int) and not isinstance(value, bool)
                    for value in arguments),
                f"census row {index} arguments do not match call kind {kind}")
        vertex_shader = integer(row.get("vertexShaderIdentity"),
                                f"census row {index} vertex shader identity")
        pixel_shader = integer(row.get("pixelShaderIdentity"),
                               f"census row {index} pixel shader identity")
        compute_shader = integer(row.get("computeShaderIdentity"),
                                 f"census row {index} compute shader identity")
        validated_census.append({"kind": kind, "afterM31Draw": after,
                                 "arguments": arguments,
                                 "owner": classify_owner(
                                     kind, vertex_shader, pixel_shader),
                                 "vertexShaderIdentity":
                                     f"{vertex_shader:016X}",
                                 "pixelShaderIdentity":
                                     f"{pixel_shader:016X}",
                                 "computeShaderIdentity":
                                     f"{compute_shader:016X}"})

    blobs = metadata.get("blobs")
    names = [f"draw{draw}_{phase}.bin" for draw in range(3)
             for phase in ("pre", "post")]
    require(isinstance(blobs, list) and len(blobs) == 6,
            "M31 chronology metadata does not contain six blob rows")
    validated_blobs = []
    paths: dict[str, Path] = {}
    for index, (row, expected_name) in enumerate(zip(blobs, names)):
        require(isinstance(row, dict), f"blob row {index} is not an object")
        require(row.get("file") == expected_name,
                f"blob row {index} is not {expected_name}")
        require(row.get("drawIndex") == index // 2,
                f"blob {expected_name} has the wrong drawIndex")
        require(row.get("afterDraw") is (index % 2 == 1),
                f"blob {expected_name} has the wrong afterDraw value")
        row_pitch = integer(row.get("rowPitch"),
                            f"blob {expected_name} rowPitch",
                            expected_width * 4)
        byte_count = integer(row.get("bytes"),
                             f"blob {expected_name} bytes", 1)
        require(byte_count == row_pitch * expected_height,
                f"blob {expected_name} byte count is not rowPitch*height")
        path = root / expected_name
        require(path.is_file(), f"M31 chronology blob is absent: {path}")
        require(path.stat().st_size == byte_count,
                f"blob {expected_name} file size differs from metadata")
        paths[expected_name] = path
        validated_blobs.append({"name": expected_name,
                                "drawIndex": index // 2,
                                "afterDraw": index % 2 == 1,
                                "rowPitch": row_pitch, "bytes": byte_count,
                                "sha256": sha256(path)})
    deltas = []
    for draw in range(3):
        before = paths[f"draw{draw}_pre.bin"]
        after = paths[f"draw{draw}_post.bin"]
        changed = changed_bytes(before, after)
        require(changed > 0,
                f"M31 draw {draw} did not change any RTV0 bytes")
        deltas.append({"drawIndex": draw, "changedBytes": changed,
                       "changedFraction": changed / before.stat().st_size})

    return {
        "schema": "endfield.endminf-m31-chronology-capture.v1",
        "status": "validated_m31_three_draw_chronology_boundary_evidence",
        "capture": str(capture),
        "observerSha256": observed_sha,
        "session": session,
        "summary": summary,
        "presentOrdinal": integer(metadata.get("presentOrdinal"),
                                  "present ordinal"),
        "targets": validated_targets,
        "census": validated_census,
        "blobs": validated_blobs,
        "drawDeltas": deltas,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.capture / "m31_chronology_verification.json"
    try:
        report = build_report(args.capture)
    except (OSError, ValueError, json.JSONDecodeError, ChronologyError,
            BASE.ContractError) as exc:
        report = {
            "schema": "endfield.endminf-m31-chronology-capture.v1",
            "status": "validation_failed",
            "capture": str(args.capture.resolve()),
            "diagnostic": str(exc),
        }
        exit_code = 1
    else:
        exit_code = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if exit_code:
        print("ERROR: " + report["diagnostic"])
    print(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
