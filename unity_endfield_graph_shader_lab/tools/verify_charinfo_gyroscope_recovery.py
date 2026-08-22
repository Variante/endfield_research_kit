#!/usr/bin/env python3
"""Verify the source-derived CharInfo Cinemachine gyroscope endpoint recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
MANIFEST = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "OriginalData"
    / "CharInfoGyroscope"
    / "source_manifest.json"
)
PORTRAIT_MANIFEST = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "OriginalData"
    / "CharInfoBackgroundPortrait"
    / "source_manifest.json"
)
RUNTIME = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Rendering"
    / "EndfieldRecoveredCharInfoGyroscopeCameraState.cs"
)
SETUP = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Editor"
    / "CharacterRecovery"
    / "EndfieldManifestCharacterSetup.cs"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def evaluate_curve(keys: list[list[float]], time: float) -> float:
    if time <= keys[0][0]:
        return keys[0][1]
    if time >= keys[-1][0]:
        return keys[-1][1]
    for left, right in zip(keys, keys[1:]):
        if time > right[0]:
            continue
        duration = right[0] - left[0]
        t = (time - left[0]) / duration
        t2 = t * t
        t3 = t2 * t
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        return (
            h00 * left[1]
            + h10 * duration * left[3]
            + h01 * right[1]
            + h11 * duration * right[2]
        )
    raise AssertionError("curve segment not found")


def add(a: tuple[float, float, float], b: tuple[float, float, float]):
    return tuple(x + y for x, y in zip(a, b))


def sub(a: tuple[float, float, float], b: tuple[float, float, float]):
    return tuple(x - y for x, y in zip(a, b))


def mul(a: tuple[float, float, float], scalar: float):
    return tuple(x * scalar for x in a)


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def cross(a: tuple[float, float, float], b: tuple[float, float, float]):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalized(v: tuple[float, float, float]):
    length = math.sqrt(dot(v, v))
    require(length > 1e-12, "zero-length vector")
    return mul(v, 1.0 / length)


def quat_rotate(q: list[float], v: tuple[float, float, float]):
    qv = (q[0], q[1], q[2])
    t = mul(cross(qv, v), 2.0)
    return add(add(v, mul(t, q[3])), cross(qv, t))


def camera_basis(position, look_at):
    forward = normalized(sub(look_at, position))
    right = normalized(cross((0.0, 1.0, 0.0), forward))
    up = cross(forward, right)
    return right, up, forward


def project(point, position, look_at, fov_degrees: float):
    right, up, forward = camera_basis(position, look_at)
    relative = sub(point, position)
    z = dot(relative, forward)
    require(z > 0.0, "portrait point is behind the camera")
    tangent = math.tan(math.radians(fov_degrees) * 0.5)
    aspect = 3840.0 / 2160.0
    ndc_x = dot(relative, right) / (z * tangent * aspect)
    ndc_y = dot(relative, up) / (z * tangent)
    return ((ndc_x * 0.5 + 0.5) * 3840.0, (0.5 - ndc_y * 0.5) * 2160.0)


def analytic_shift(actor: str, offset: list[float], portrait: dict):
    if actor == "Wulfa":
        position = (0.0, 0.998, 3.46)
        fov = 20.0
    else:
        position = (0.0, 1.25, 3.5)
        fov = 20.007383
    actor_data = portrait["actors"][actor]
    look_at = tuple(actor_data["look_at_local_position"])
    q = actor_data["overview_vcam_local_rotation_xyzw"]
    local_card = (-0.48, 0.08, 0.8)
    card_center = add(look_at, quat_rotate(q, local_card))
    right, up, _forward = camera_basis(position, look_at)
    correction = add(mul(right, offset[0]), mul(up, offset[1]))
    corrected_position = add(position, correction)
    before = project(card_center, position, look_at, fov)
    after = project(card_center, corrected_position, look_at, fov)
    return [after[0] - before[0], after[1] - before[1]], list(correction), list(card_center)


def verify() -> dict:
    for path in (MANIFEST, PORTRAIT_MANIFEST, RUNTIME, SETUP):
        require(path.is_file(), f"missing gyroscope recovery input: {path}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    portrait = json.loads(PORTRAIT_MANIFEST.read_text(encoding="utf-8"))
    require(
        manifest["schema"] == "endfield.charinfo.gyroscope-camera-state.original-data.v1",
        "wrong gyroscope manifest schema",
    )
    require(manifest["camera_extension"]["native_va"] == "0x18BBD3CCC", "native VA drifted")
    require(manifest["camera_extension"]["stage"] == "CinemachineCore.Stage.Finalize", "wrong stage")

    driver = manifest["input_driver"]
    vertical = evaluate_curve(driver["vertical_curve_unweighted_keys"], 0.0) * 0.15
    horizontal = evaluate_curve(driver["horizontal_curve_unweighted_keys"], 0.0) * -0.25
    expected_center = driver["centered_mouse_settled_offsets_xy"]
    require(abs(horizontal - expected_center[0]) < 2e-9, "centered offsetX drifted")
    require(abs(vertical - expected_center[1]) < 2e-9, "centered offsetY drifted")

    analytic: dict[str, dict] = {}
    for actor in ("Wulfa", "Zhuangfy"):
        source_path = REPO / manifest["actors"][actor]["driver_source"]
        extension_path = REPO / manifest["actors"][actor]["extension_source"]
        for path, key in ((source_path, "driver_raw_sha256"), (extension_path, "extension_raw_sha256")):
            require(path.is_file(), f"missing source object: {path}")
            source = json.loads(path.read_text(encoding="utf-8"))
            require(
                source["$animestudio"]["rawDataSha256"] == manifest["actors"][actor][key],
                f"{actor} source raw hash drifted: {path.name}",
            )

        offsets = manifest["actors"][actor]["serialized_entry_offsets_xy"]
        shift, correction, card_center = analytic_shift(actor, offsets, portrait)
        expected_shift = manifest["actors"][actor][
            "serialized_entry_analytic_portrait_shift_pixels_3840x2160"
        ]
        require(
            max(abs(a - b) for a, b in zip(shift, expected_shift)) < 0.06,
            f"{actor} analytic serialized-entry shift drifted: {shift}",
        )
        neutral_shift, _, _ = analytic_shift(actor, expected_center, portrait)
        analytic[actor] = {
            "serializedEntryOffsets": offsets,
            "serializedEntryPositionCorrection": correction,
            "serializedEntryPortraitShiftPixels": shift,
            "neutralCenteredPortraitShiftPixels": neutral_shift,
            "portraitCardCenter": card_center,
        }

    endminf = manifest["actors"]["Endminf"]
    for key, hash_key in (("driver_source", "driver_raw_sha256"), ("extension_source", "extension_raw_sha256")):
        source_path = REPO / endminf[key]
        require(source_path.is_file(), f"missing Endminf gyroscope source: {source_path}")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        require(source["$animestudio"]["rawDataSha256"] == endminf[hash_key], f"Endminf {key} hash drifted")
    require(endminf["serialized_entry_offsets_xy"] == [0.24835543, -0.1448596], "Endminf entry offsets drifted")

    runtime = RUNTIME.read_text(encoding="utf-8")
    for token in (
        '"ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE"',
        "RecoveryMode.NeutralCenteredInput",
        "RecoveryMode.SerializedEntry",
        "RecoveryMode.RecordedInputEndpoint",
        "baseOrientation *",
        "new Vector3(offsets.x, offsets.y, 0.0f)",
        "Quaternion.LookRotation(",
        "referenceLookAt - correctedPosition",
        "SourceTweenDurationSeconds = 2.0f",
        "new CurveKey(-0.5103161f, -0.85068125f, 0.504885f, 0.504885f)",
        "new CurveKey(0.0f, 0.005836278f, 2.6192734f, 2.6192734f)",
        "new Vector2(0.24835543f, -0.1448596f)",
    ):
        require(token in runtime, f"runtime gyroscope source contract missing {token!r}")
    setup = SETUP.read_text(encoding="utf-8")
    require(
        "EndfieldRecoveredCharInfoGyroscopeCameraState.TryApplyOverview("
        in setup,
        "runtime-reference camera does not apply the recovered Finalize specialization",
    )

    return {
        "valid": True,
        "centeredMouseSettledOffsets": [horizontal, vertical],
        "analytic": analytic,
        "boundary": (
            "Static data closes the Finalize callback, curves, serialized entry state, and "
            "source-defined endpoints. Capture-time cursor/controller input and the two-second "
            "transition timeline remain external/deferred."
        ),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_runtime(actor: str, mode: str, log_path: Path, png_path: Path) -> dict:
    require(log_path.is_file() and log_path.stat().st_size > 0, f"missing runtime log: {log_path}")
    require(png_path.is_file() and png_path.stat().st_size > 0, f"missing runtime PNG: {png_path}")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    require(
        f"Recovered CharInfo gyroscope camera state active: actor={actor}, mode={mode}"
        in log,
        "runtime log is missing the requested gyroscope mode",
    )
    require(
        "Recovered CharInfo gyroscope camera state failed closed" not in log,
        "runtime gyroscope mode failed closed",
    )
    header = png_path.read_bytes()[:24]
    require(header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR", "invalid PNG")
    width, height = struct.unpack(">II", header[16:24])
    require((width, height) == (3840, 2160), f"runtime PNG is {width}x{height}")
    return {
        "actor": actor,
        "mode": mode,
        "log": str(log_path),
        "png": str(png_path),
        "pngSha256": sha256(png_path),
        "width": width,
        "height": height,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--actor", choices=("Wulfa", "Zhuangfy"))
    parser.add_argument(
        "--mode",
        choices=("neutral-centered-input", "serialized-entry", "recorded-input-endpoint"),
    )
    parser.add_argument("--log", type=Path)
    parser.add_argument("--png", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = verify()
    runtime_args = (args.actor, args.mode, args.log, args.png)
    if any(value is not None for value in runtime_args):
        require(all(value is not None for value in runtime_args), "runtime validation requires --actor, --mode, --log, and --png")
        result["runtime"] = verify_runtime(
            args.actor,
            args.mode,
            args.log.resolve(),
            args.png.resolve(),
        )
    if args.report:
        report = args.report.resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
