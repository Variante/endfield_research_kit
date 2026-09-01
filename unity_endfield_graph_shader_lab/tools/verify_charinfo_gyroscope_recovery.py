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
sys.path.insert(0, str(REPO))

from scripts.common import check_installed_native_inputs

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
PROFILE_MANIFEST = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "OriginalData"
    / "CharInfoPlayableProfiles"
    / "source_profiles.json"
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
CONTROLLER = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Viewer"
    / "CharacterRecoveryPresentationController.cs"
)
CAPTURE = (
    PROJECT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Editor"
    / "CharacterRecovery"
    / "EndfieldEndminfViewerPlayModeCapture.cs"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_pe_rva(path: Path, rva: int, size: int) -> bytes:
    """Read one bounded RVA span without adding a non-stdlib PE dependency."""
    with path.open("rb") as handle:
        dos = handle.read(64)
        require(len(dos) == 64 and dos[:2] == b"MZ", f"invalid DOS header: {path}")
        pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
        handle.seek(pe_offset)
        signature_and_coff = handle.read(24)
        require(
            len(signature_and_coff) == 24 and signature_and_coff[:4] == b"PE\0\0",
            f"invalid PE header: {path}",
        )
        section_count = struct.unpack_from("<H", signature_and_coff, 6)[0]
        optional_size = struct.unpack_from("<H", signature_and_coff, 20)[0]
        handle.seek(optional_size, 1)
        for _index in range(section_count):
            section = handle.read(40)
            require(len(section) == 40, f"truncated PE section table: {path}")
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
                "<IIII", section, 8
            )
            extent = max(virtual_size, raw_size)
            if virtual_address <= rva and rva + size <= virtual_address + extent:
                within = rva - virtual_address
                require(
                    within + size <= raw_size,
                    f"RVA span is not backed by raw bytes: 0x{rva:X}+{size}",
                )
                handle.seek(raw_offset + within)
                payload = handle.read(size)
                require(len(payload) == size, f"short RVA read: 0x{rva:X}+{size}")
                return payload
    raise AssertionError(f"RVA is outside PE sections: 0x{rva:X}+{size}")


def verify_native_span(
    gameassembly: Path,
    row: dict,
    rva_key: str,
    size_key: str,
    hash_key: str,
) -> None:
    rva = int(str(row[rva_key]), 16)
    size = int(row[size_key])
    actual = hashlib.sha256(read_pe_rva(gameassembly, rva, size)).hexdigest()
    require(actual == row[hash_key], f"native span drifted: {rva_key}=0x{rva:X}")


def parse_hex(value: str) -> int:
    return int(str(value), 16)


def require_bytes(payload: bytes, offset: int, expected: bytes, label: str) -> None:
    actual = payload[offset : offset + len(expected)]
    require(
        actual == expected,
        f"{label} instruction drifted at +0x{offset:X}: "
        f"expected={expected.hex()} actual={actual.hex()}",
    )


def decode_rel32_target(
    payload: bytes,
    body_rva: int,
    offset: int,
    opcode: bytes,
    label: str,
) -> int:
    require_bytes(payload, offset, opcode, label)
    displacement = struct.unpack_from("<i", payload, offset + len(opcode))[0]
    return body_rva + offset + len(opcode) + 4 + displacement


def decode_rip_relative_target(
    payload: bytes,
    body_rva: int,
    offset: int,
    prefix: bytes,
    label: str,
) -> int:
    require_bytes(payload, offset, prefix, label)
    displacement = struct.unpack_from("<i", payload, offset + len(prefix))[0]
    return body_rva + offset + len(prefix) + 4 + displacement


def native_float(gameassembly: Path, rva: int) -> float:
    return struct.unpack("<f", read_pe_rva(gameassembly, rva, 4))[0]


def verify_decoded_tick_contract(gameassembly: Path, driver: dict) -> dict:
    """Decode the native landmarks that establish the source Tick semantics."""
    tick_row = driver["tick"]
    body_rva = parse_hex(tick_row["native_rva"])
    payload = read_pe_rva(
        gameassembly,
        body_rva,
        int(tick_row["identity_window_size"]),
    )
    landmarks = driver["decoded_native_contract"]
    at = lambda key: parse_hex(landmarks[key])

    tick_option = read_pe_rva(
        gameassembly,
        parse_hex(driver["tick_option"]["native_rva"]),
        int(driver["tick_option"]["body_size"]),
    )
    tick_option_offset = at("tick_option_return_offset")
    require_bytes(
        tick_option,
        tick_option_offset,
        b"\xB8\x08\x00\x00\x00",
        "get_tickOption PreLate return",
    )
    decoded_tick_option = struct.unpack_from("<I", tick_option, tick_option_offset + 1)[0]
    require(decoded_tick_option == 8, "decoded tick option is no longer PreLate (8)")

    # The enabled desktop branch polls Beyond.Input directly. Its zero-input
    # branch skips to the same evaluated-target gate, so m_lastValue remains
    # the sole target-change gate regardless of provider path.
    require_bytes(payload, 0x86, b"\x40\x38\x7E\x68", "enableDetect field read")
    disabled_target = decode_rel32_target(
        payload, body_rva, 0x8A, b"\x0F\x84", "enableDetect disabled branch"
    )
    require(
        disabled_target == body_rva + at("raw_target_gate_offset"),
        "enableDetect disabled branch no longer joins the raw-target gate",
    )
    input_target = decode_rel32_target(
        payload,
        body_rva,
        at("input_poll_call_offset"),
        b"\xE8",
        "Beyond.Input mouse poll",
    )
    require(
        input_target == parse_hex(driver["mouse_provider"]["native_rva"]),
        "Tick no longer calls the pinned Beyond.Input.InputManager.get_mousePosition",
    )

    width_targets = [
        decode_rel32_target(payload, body_rva, parse_hex(value), b"\xE8", "Screen.width")
        for value in landmarks["screen_width_call_offsets"]
    ]
    height_targets = [
        decode_rel32_target(payload, body_rva, parse_hex(value), b"\xE8", "Screen.height")
        for value in landmarks["screen_height_call_offsets"]
    ]
    require(
        len(set(width_targets)) == 1 and len(set(height_targets)) == 1,
        "screen accessor call targets drifted within Tick",
    )
    require(width_targets[0] != height_targets[0], "screen width/height calls collapsed")

    half_width_rva = decode_rip_relative_target(
        payload,
        body_rva,
        at("half_width_scale_offset"),
        b"\xF3\x44\x0F\x59\x1D",
        "screen half-width scale",
    )
    half_height_rva = decode_rip_relative_target(
        payload,
        body_rva,
        at("half_height_scale_offset"),
        b"\xF3\x44\x0F\x59\x15",
        "screen half-height scale",
    )
    require(
        half_width_rva == half_height_rva
        and native_float(gameassembly, half_width_rva) == 0.5,
        "Tick no longer derives half screen extents with the native 0.5 constant",
    )
    for offset, expected, label in (
        (0x4DA, b"\x41\x0F\x2F\xF9", "mouse X lower clamp"),
        (0x4E7, b"\x44\x0F\x2F\xC8", "mouse X upper clamp"),
        (0x4F9, b"\xF3\x45\x0F\x5C\xCB", "mouse X half subtraction"),
        (0x503, b"\x41\x0F\x2F\xF8", "mouse Y lower clamp"),
        (0x510, b"\x44\x0F\x2F\xC0", "mouse Y upper clamp"),
        (0x524, b"\xF3\x45\x0F\x5C\xC2", "mouse Y half subtraction"),
        (at("normalized_y_divide_offset"), b"\xF3\x45\x0F\x5E\xC2", "mouse Y half normalization"),
        (at("normalized_x_divide_offset"), b"\xF3\x45\x0F\x5E\xCB", "mouse X half normalization"),
    ):
        require_bytes(payload, offset, expected, label)

    vertical_evaluate = decode_rel32_target(
        payload,
        body_rva,
        at("vertical_curve_evaluate_call_offset"),
        b"\xE8",
        "vertical AnimationCurve.Evaluate",
    )
    horizontal_evaluate = decode_rel32_target(
        payload,
        body_rva,
        at("horizontal_curve_evaluate_call_offset"),
        b"\xE8",
        "horizontal AnimationCurve.Evaluate",
    )
    require(
        vertical_evaluate == horizontal_evaluate,
        "vertical and horizontal target mapping no longer share AnimationCurve.Evaluate",
    )
    require_bytes(payload, 0x520, b"\x48\x8B\x46\x78", "vertical Param field")
    require_bytes(payload, 0x567, b"\x48\x8B\x86\x80\x00\x00\x00", "horizontal Param field")
    require_bytes(payload, 0x561, b"\xF3\x44\x0F\x59\x40\x10", "vertical maxAngle scale")
    require_bytes(payload, 0xE16, b"\xF3\x0F\x59\x70\x10", "horizontal maxAngle scale")

    gate_offset = at("raw_target_gate_offset")
    require_bytes(
        payload,
        gate_offset,
        b"\xF2\x0F\x10\x8E\x90\x00\x00\x00",
        "m_lastValue load",
    )
    threshold_offset = at("raw_target_threshold_load_offset")
    threshold_rva = decode_rip_relative_target(
        payload,
        body_rva,
        threshold_offset,
        b"\xF3\x0F\x10\x05",
        "raw-target threshold",
    )
    threshold_references = 0
    start = 0
    prefix = b"\xF3\x0F\x10\x05"
    while True:
        found = payload.find(prefix, start)
        if found < 0:
            break
        target = decode_rip_relative_target(
            payload, body_rva, found, prefix, "scalar RIP-relative load"
        )
        if target == threshold_rva:
            threshold_references += 1
        start = found + 1
    require(threshold_references == 1, "native Tick must contain one raw-target gate")
    require_bytes(payload, 0xE65, b"\x0F\x2F\xC3", "raw-target squared-distance compare")
    gate_skip_target = decode_rel32_target(
        payload,
        body_rva,
        at("raw_target_gate_skip_offset"),
        b"\x0F\x87",
        "raw-target unchanged skip",
    )
    require(
        gate_skip_target == body_rva + at("raw_target_gate_skip_target_offset"),
        "raw-target unchanged branch target drifted",
    )
    require_bytes(payload, 0xE76, b"\xF2\x44\x0F\x11\x8E\x90\x00\x00\x00", "m_lastValue update")

    active_offset = at("active_tween_branch_offset")
    require_bytes(payload, active_offset, b"\x48\x39\xBE\xD8\x00\x00\x00", "active tween lookup")
    inactive_target = decode_rel32_target(
        payload,
        body_rva,
        at("active_to_inactive_branch_offset"),
        b"\x0F\x84",
        "missing active tween branch",
    )
    require(
        inactive_target == body_rva + at("inactive_create_branch_offset"),
        "missing active tween no longer reaches the inactive create branch",
    )
    require_bytes(payload, at("active_snap_true_offset"), b"\x41\xB1\x01", "ChangeEndValue snapStartValue")
    require_bytes(payload, at("active_duration_preservation_move_offset"), b"\x41\x0F\x28\xD4", "ChangeEndValue duration argument")
    sentinel_rva = decode_rip_relative_target(
        payload,
        body_rva,
        at("duration_preservation_constant_load_offset"),
        b"\xF3\x44\x0F\x10\x25",
        "ChangeEndValue duration-preservation constant",
    )
    duration_sentinel = native_float(gameassembly, sentinel_rva)
    require(duration_sentinel == -1.0, "ChangeEndValue duration sentinel is no longer -1")
    change_target = decode_rel32_target(
        payload,
        body_rva,
        at("change_end_value_call_offset"),
        b"\xE8",
        "ChangeEndValue call",
    )
    require(
        change_target == parse_hex(landmarks["change_end_value_native_rva"]),
        "ChangeEndValue call target drifted",
    )

    duration_load_offset = at("inactive_duration_load_offset")
    require_bytes(
        payload,
        duration_load_offset,
        b"\xF3\x0F\x10\xB6\x8C\x00\x00\x00",
        "inactive tween serialized duration load",
    )
    create_target = decode_rel32_target(
        payload,
        body_rva,
        at("inactive_create_call_offset"),
        b"\xE8",
        "inactive tween create call",
    )
    require(
        create_target == parse_hex(landmarks["inactive_create_native_rva"]),
        "inactive tween create call target drifted",
    )
    require_bytes(
        payload,
        at("inactive_ease_load_offset"),
        b"\x44\x8B\xBE\x88\x00\x00\x00",
        "inactive tween serialized ease load",
    )
    require_bytes(
        payload,
        at("inactive_ease_store_offset"),
        b"\x45\x89\xBE\xB4\x00\x00\x00",
        "inactive tween ease application",
    )
    return {
        "tickOption": decoded_tick_option,
        "inputProviderRva": f"0x{input_target:X}",
        "screenWidthRva": f"0x{width_targets[0]:X}",
        "screenHeightRva": f"0x{height_targets[0]:X}",
        "curveEvaluateRva": f"0x{vertical_evaluate:X}",
        "rawTargetGateCount": threshold_references,
        "rawTargetThresholdSquared": native_float(gameassembly, threshold_rva),
        "activeDurationArgument": duration_sentinel,
        "activeSnapStartValue": True,
        "inactiveDurationFieldOffset": "0x8C",
        "inactiveEaseFieldOffset": "0x88",
    }


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
    for path in (
        MANIFEST,
        PORTRAIT_MANIFEST,
        PROFILE_MANIFEST,
        RUNTIME,
        SETUP,
        CONTROLLER,
        CAPTURE,
    ):
        require(path.is_file(), f"missing gyroscope recovery input: {path}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    portrait = json.loads(PORTRAIT_MANIFEST.read_text(encoding="utf-8"))
    profiles = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
    require(
        manifest["schema"] == "endfield.charinfo.gyroscope-camera-state.original-data.v2",
        "wrong gyroscope manifest schema",
    )
    native_gate = manifest["native_source_gate"]
    native = check_installed_native_inputs(
        native_gate["gameassembly_sha256"],
        native_gate["global_metadata_sha256"],
    )
    require(native.validated, native.detail or f"native gate is {native.status}")

    require(manifest["camera_extension"]["native_va"] == "0x18BBD3CCC", "native VA drifted")
    require(manifest["camera_extension"]["stage"] == "CinemachineCore.Stage.Finalize", "wrong stage")

    driver = manifest["input_driver"]
    require(driver["tick_option"]["return_value"] == 8, "tick option no longer selects PreLate")
    require(driver["tick_option"]["tick"] == "PreLate", "wrong driver tick phase")
    verify_native_span(
        native.gameassembly,
        driver["tick_option"],
        "native_rva",
        "body_size",
        "body_sha256",
    )
    verify_native_span(
        native.gameassembly,
        driver["on_awake"],
        "native_rva",
        "body_size",
        "body_sha256",
    )
    verify_native_span(
        native.gameassembly,
        driver["tick"],
        "native_rva",
        "identity_window_size",
        "identity_window_sha256",
    )
    verify_native_span(
        native.gameassembly,
        driver["tick"],
        "desktop_input_and_gate_rva",
        "desktop_input_and_gate_size",
        "desktop_input_and_gate_sha256",
    )
    verify_native_span(
        native.gameassembly,
        driver["tick"],
        "active_tween_change_end_value_rva",
        "active_tween_change_end_value_size",
        "active_tween_change_end_value_sha256",
    )
    verify_native_span(
        native.gameassembly,
        driver["mouse_provider"],
        "native_rva",
        "identity_window_size",
        "identity_window_sha256",
    )
    decoded_native = verify_decoded_tick_contract(native.gameassembly, driver)
    require(
        driver["mouse_provider"]["source_type"] == "Beyond.Input.InputManager"
        and driver["mouse_provider"]["source_method"] == "get_mousePosition",
        "retail mouse provider identity drifted",
    )
    for accessor in driver["delegate_accessors"].values():
        verify_native_span(
            native.gameassembly,
            accessor,
            "native_rva",
            "body_size",
            "body_sha256",
        )
    raw_gate = driver["raw_target_change_gate"]
    require(raw_gate["gate_count"] == 1, "source must have one raw-target gate")
    threshold_bytes = read_pe_rva(
        native.gameassembly,
        int(raw_gate["threshold_native_rva"], 16),
        4,
    )
    require(
        threshold_bytes.hex() == raw_gate["threshold_bytes_le"],
        "raw-target threshold bytes drifted",
    )
    native_threshold = struct.unpack("<f", threshold_bytes)[0]
    require(
        math.isclose(
            native_threshold,
            raw_gate["threshold_squared"],
            rel_tol=1e-7,
            abs_tol=0.0,
        ),
        "raw-target threshold value drifted",
    )

    vertical = (
        evaluate_curve(driver["vertical_curve_unweighted_keys"], 0.0)
        * driver["vertical_curve_scale"]
    )
    horizontal = (
        evaluate_curve(driver["horizontal_curve_unweighted_keys"], 0.0)
        * driver["horizontal_curve_scale"]
    )
    expected_center = driver["centered_mouse_settled_offsets_xy"]
    require(abs(horizontal - expected_center[0]) < 2e-9, "centered offsetX drifted")
    require(abs(vertical - expected_center[1]) < 2e-9, "centered offsetY drifted")

    analytic: dict[str, dict] = {}
    profile_by_actor = {row["root_name"]: row for row in profiles["characters"]}
    for actor in ("Wulfa", "Zhuangfy"):
        offsets = manifest["actors"][actor]["serialized_entry_offsets_xy"]
        require(
            profile_by_actor[actor]["camera"]["gyroscope_entry_offsets"] == offsets,
            f"{actor} presentation-profile gyroscope entry drifted",
        )
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

    for actor in ("Wulfa", "Zhuangfy", "Endminf"):
        actor_row = manifest["actors"][actor]
        for key, hash_key in (
            ("driver_source", "driver_raw_sha256"),
            ("extension_source", "extension_raw_sha256"),
        ):
            source_path = REPO / actor_row[key]
            require(source_path.is_file(), f"missing {actor} gyroscope source: {source_path}")
            source = json.loads(source_path.read_text(encoding="utf-8"))
            require(
                source["$animestudio"]["rawDataSha256"] == actor_row[hash_key],
                f"{actor} {key} raw payload hash drifted",
            )

    endminf = manifest["actors"]["Endminf"]
    require(endminf["serialized_entry_offsets_xy"] == [0.24835543, -0.1448596], "Endminf entry offsets drifted")
    require(
        profile_by_actor["Endminf"]["camera"]["gyroscope_entry_offsets"]
        == endminf["serialized_entry_offsets_xy"],
        "Endminf presentation-profile gyroscope entry drifted",
    )

    driver_source_path = REPO / endminf["driver_source"]
    driver_source = json.loads(driver_source_path.read_text(encoding="utf-8"))
    require(driver_source["enableDetect"] == 1, "Endminf enableDetect drifted")
    require(driver_source["time"] == driver["tween_seconds"], "source tween duration drifted")
    require(driver_source["ease"] == 6, "source tween ease is no longer OutQuad (6)")
    require(
        driver_source["time"] == 2.0
        and decoded_native["inactiveDurationFieldOffset"] == "0x8C",
        "native inactive creation no longer consumes the serialized two-second duration",
    )
    require(
        driver_source["ease"] == 6
        and decoded_native["inactiveEaseFieldOffset"] == "0x88",
        "native inactive creation no longer applies serialized ease 6",
    )
    require(
        driver_source["x"]["maxAngle"] == driver["vertical_curve_scale"],
        "source vertical maxAngle drifted",
    )
    require(
        driver_source["y"]["maxAngle"] == driver["horizontal_curve_scale"],
        "source horizontal maxAngle drifted",
    )
    for source_name, manifest_name in (
        ("x", "vertical_curve_unweighted_keys"),
        ("y", "horizontal_curve_unweighted_keys"),
    ):
        source_keys = driver_source[source_name]["valueCurve"]["m_Curve"]
        require(
            all(row["weightedMode"] == 0 for row in source_keys),
            f"{source_name} curve is no longer unweighted",
        )
        compact = [
            [row["time"], row["value"], row["inSlope"], row["outSlope"]]
            for row in source_keys
        ]
        require(compact == driver[manifest_name], f"{source_name} curve data drifted")

    runtime = RUNTIME.read_text(encoding="utf-8")
    for token in (
        '"ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE"',
        "RecoveryMode.NeutralCenteredInput",
        "RecoveryMode.SerializedEntry",
        "RecoveryMode.LiveInput",
        "RecoveryMode.RecordedInputEndpoint",
        "RecoveryMode.Invalid",
        "return RecoveryMode.Invalid;",
        "baseOrientation *",
        "new Vector3(offsets.x, offsets.y, 0.0f)",
        "Quaternion.LookRotation(",
        "referenceLookAt - correctedPosition",
        "SourceTweenDurationSeconds = 2.0f",
        "SourceRawTargetChangeThresholdSquared = 1e-10f",
        "new CurveKey(-0.5103161f, -0.85068125f, 0.504885f, 0.504885f)",
        "new CurveKey(0.0f, 0.005836278f, 2.6192734f, 2.6192734f)",
        "previousRawTarget = Vector2.zero",
        ".ShouldRetargetRawTarget(previousRawTarget, rawTarget)",
        "tween.RetargetRawTarget(rawTarget)",
        "entryOffsets = EvaluateCurrentOffsets();",
        "elapsed + Time.deltaTime",
        "sourcePhase=PreLate",
        "adapterCallback=LateUpdate",
        "equivalenceClaim=false",
    ):
        require(token in runtime, f"runtime gyroscope source contract missing {token!r}")
    require("Time.unscaledDeltaTime" not in runtime, "gyroscope tween uses the wrong time domain")
    require(
        runtime.count("1e-10f") == 1,
        "runtime must contain exactly one source raw-target threshold",
    )
    for forbidden in (
        "RecordingGyroscopeInput",
        "CleanReferenceGyroscopeTrack",
        "ReplayCleanReferenceGyroscopeTrack",
        "new Vector2(0.24835543f, -0.1448596f)",
    ):
        require(forbidden not in runtime, f"runtime contains recording-specific state: {forbidden}")
    setup = SETUP.read_text(encoding="utf-8")
    controller = CONTROLLER.read_text(encoding="utf-8")
    require(
        "EndfieldRecoveredCharInfoGyroscopeCameraState.TryApplyOverview("
        in setup,
        "runtime-reference camera does not apply the recovered Finalize specialization",
    )
    require(
        "presentationProfile.gyroscopeEntryOffsets" in setup,
        "editor camera does not use the source presentation-profile entry offsets",
    )
    require(
        "profile.gyroscopeEntryOffsets" in controller,
        "runtime camera does not use the source presentation-profile entry offsets",
    )
    capture = CAPTURE.read_text(encoding="utf-8")
    for token in (
        '"endfield.endminf-viewer-playmode-sequence.v19"',
        '"serialized-entry"',
        "ConfigureDeterministicGyroscopeCapture();",
        "RecoveryMode.LiveInput",
        "Canonical/batch Endminf capture rejects live-input",
        '"presentation-profile.gyroscopeEntryOffsets"',
        '"explicit-normalized-input-selector"',
        "gyroscopeInputProvider = captureGyroscopeInputProvider",
        "gyroscopeInputX = captureGyroscopeInputX",
        "gyroscopeInputY = captureGyroscopeInputY",
        'EndfieldPlayableCharInfoProfileBuilder.LoadProfile("Endminf")',
        "gyroscopeEntryOffsetX = captureGyroscopeEntryOffsetX",
        "gyroscopeEntryOffsetY = captureGyroscopeEntryOffsetY",
    ):
        require(token in capture, f"batch gyroscope contract missing {token!r}")
    for forbidden in (
        "RecordingGyroscopeInput",
        "CleanReferenceGyroscopeTrack",
        "ReplayCleanReferenceGyroscopeTrack",
    ):
        require(forbidden not in capture, f"capture contains fitted gyroscope track: {forbidden}")

    return {
        "valid": True,
        "nativeGate": {
            "status": native.status,
            "gameassemblySha256": native.gameassembly_sha256,
            "metadataSha256": native.metadata_sha256,
        },
        "decodedNativeContract": decoded_native,
        "centeredMouseSettledOffsets": [horizontal, vertical],
        "analytic": analytic,
        "boundary": (
            "Pinned native code plus serialized data close the Finalize callback, the retail "
            "Beyond.Input mouse-provider call, PreLate screen-clamp/half normalization, "
            "unweighted curve evaluation, the single evaluated-target change gate, inactive "
            "two-second/ease-6 creation, and active ChangeEndValue(-1, snap=true) retarget. "
            "The public-Unity lab does not implement Beyond.Input's virtual/controller provider; "
            "its LateUpdate mouse adapter makes no equivalence claim, capture-time samples remain "
            "external, and canonical batch capture rejects live input."
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
