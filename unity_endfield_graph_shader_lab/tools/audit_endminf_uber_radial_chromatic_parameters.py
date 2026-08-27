#!/usr/bin/env python3
"""Pin and decode the retail Uber radial/chromatic parameter producer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import struct
import sys
from bisect import bisect_right
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import common  # noqa: E402
from scripts.story_builder.animestudio_story_objects import (  # noqa: E402
    REVERSE_GAMEASSEMBLY_SHA256,
    REVERSE_METADATA_SHA256,
)


OUTPUT = (
    ROOT / "reports/assets/character_recovery"
    / "endminf_uber_radial_chromatic_native_parameters.json"
)
MAPPING_HELPER = ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"
IMAGE_NAME = "HG.RenderPipelines.Runtime.dll"
TYPE_NAME = "HG.Rendering.Runtime.UberPostPassUtils"
METHOD_NAME = "PrepareRadialBlurAndChromaticAberrationParameters"
METHOD_INDEX = 286_867
METHOD_TOKEN = 0x06000F0F
METHOD_VA = 0x189B860F0
METHOD_NEXT_VA = 0x189B86648
METHOD_SIZE = METHOD_NEXT_VA - METHOD_VA
METHOD_SHA256 = "a5711413dc91ff5271fcf50298292f339a3bba23be9f0feab6536b9e83c75d75"

EXPECTED_PARAMETERS = [
    ("settingParameters", "HG.Rendering.Runtime.HGSettingParameters"),
    ("data", "HG.Rendering.Runtime.UberPostPassUtils+UberPostPassData"),
    ("camera", "HG.Rendering.Runtime.HGCamera+ViewConstants&"),
    ("radialBlur", "HG.Rendering.Runtime.HGRadialBlur"),
    ("chromaticAbberation", "HG.Rendering.Runtime.HGChromaticAbberation"),
]
EXPECTED_FIELDS = {
    "HG.Rendering.Runtime.HGRadialBlur": [
        "enabled", "center", "intensity", "power", "averageSteps",
        "enableGlobalCenter", "globalCenter",
    ],
    "HG.Rendering.Runtime.HGChromaticAbberation": [
        "enabled", "center", "intensity", "averageStep",
        "enableGlobalCenter", "globalCenter",
    ],
}
EXPECTED_PASS_FIELDS = {
    "radialBlurParams": "0x50",
    "radialBlurParams2": "0x60",
}


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_bytes(body: bytes, offset: int, expected: bytes, label: str) -> None:
    actual = body[offset:offset + len(expected)]
    require(actual == expected,
            f"{label} instruction drifted at body+0x{offset:X}: "
            f"expected {expected.hex()}, got {actual.hex()}")


def decode_rip_scalar(
    body: bytes,
    method_va: int,
    offset: int,
    prefix: bytes,
    fmt: str,
    read_va: Callable[[int, int], bytes],
    label: str,
) -> tuple[float, int]:
    require_bytes(body, offset, prefix, label)
    displacement_offset = offset + len(prefix)
    require(displacement_offset + 4 <= len(body),
            f"{label} displacement exceeds method body")
    displacement = struct.unpack_from("<i", body, displacement_offset)[0]
    instruction_size = len(prefix) + 4
    target = method_va + offset + instruction_size + displacement
    size = struct.calcsize(fmt)
    raw = read_va(target, size)
    require(len(raw) == size, f"{label} scalar target is not mapped")
    value = float(struct.unpack(fmt, raw)[0])
    require(math.isfinite(value), f"{label} scalar is not finite")
    return value, target


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def evaluate_active_lanes(
    *,
    radial_active: bool,
    chromatic_active: bool,
    radial_intensity: float,
    radial_power: float,
    chromatic_intensity: float,
    radial_average_steps: bool,
    chromatic_average_step: bool,
    center: tuple[float, float] = (0.5, 0.5),
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    """Executable form of the audited branch equations for focused tests."""
    require(radial_active or chromatic_active,
            "native producer does not write either vector when both effects are inactive")
    if radial_active and chromatic_active:
        require(chromatic_intensity > 0.0,
                "both-active evaluation requires positive chromatic intensity")
        weight = clamp01(radial_intensity / chromatic_intensity)
        effective_power = 1.0 + (radial_power - 1.0) * weight
    elif radial_active:
        effective_power = radial_power
    else:
        effective_power = 1.0
    mode = 6.0 if (
        radial_active and chromatic_active and radial_intensity > 0.01
    ) else 3.0
    c0 = (
        float(center[0]),
        float(center[1]),
        float(radial_intensity if radial_active else 0.0),
        float(effective_power),
    )
    c25 = (
        mode,
        float(chromatic_intensity),
        float(bool(radial_average_steps)) if radial_active else 0.0,
        float(bool(chromatic_average_step)) if chromatic_active else 0.0,
    )
    return c0, c25


def decode_body_contract(
    body: bytes,
    read_va: Callable[[int, int], bytes],
) -> dict[str, Any]:
    require(len(body) == METHOD_SIZE,
            f"method body is {len(body)} bytes, expected {METHOD_SIZE}")
    require(sha256_bytes(body) == METHOD_SHA256, "method body SHA-256 drifted")

    # These landmarks make the report's semantics auditable rather than merely
    # attaching prose to a whole-body hash. The exact body hash remains the
    # primary fail-closed gate.
    landmarks = [
        (0x09C, "488b8eb8010000", "radial settings gate at settingParameters+0x1B8"),
        (0x0DB, "488b8ec0010000", "chromatic settings gate at settingParameters+0x1C0"),
        (0x37E, "488b5340", "radial intensity read"),
        (0x392, "488b5740", "chromatic intensity read for power ratio"),
        (0x3A9, "f30f5ef0", "radial/chromatic intensity division"),
        (0x3B9, "488b5348", "radial power read"),
        (0x3E4, "488b5350", "radial averageSteps read"),
        (0x41C, "488b5748", "chromatic averageStep read"),
        (0x43F, "4584e7", "both-active mode predicate"),
        (0x44B, "488b5340", "mode radial-intensity read"),
        (0x460, "b806000000", "mode-6 candidate"),
        (0x46C, "8d48fd", "mode-3 candidate"),
        (0x477, "0f46c1", "mode-3 select for intensity <= threshold"),
        (0x496, "f3410f7f4550", "radialBlurParams store at data+0x50"),
        (0x4CD, "f3410f7f4560", "radialBlurParams2 store at data+0x60"),
    ]
    for offset, encoded, label in landmarks:
        require_bytes(body, offset, bytes.fromhex(encoded), label)

    scalar_specs = {
        "centerDefault": (0x14D, bytes.fromhex("f3440f1005"), "<f"),
        "centerNdcScale": (0x2A7, bytes.fromhex("f30f100d"), "<f"),
        "centerUnit": (0x2BF, bytes.fromhex("f3440f101d"), "<f"),
        "farCenterRadius": (0x2F1, bytes.fromhex("660f2f0d"), "<d"),
        "centerEdgeScale": (0x14D, bytes.fromhex("f3440f1005"), "<f"),
        "temporaryPowerSeed": (0x345, bytes.fromhex("f30f103d"), "<f"),
        "modeThreshold": (0x46F, bytes.fromhex("660f2f0d"), "<d"),
    }
    constants: dict[str, dict[str, Any]] = {}
    for name, (offset, prefix, fmt) in scalar_specs.items():
        value, target = decode_rip_scalar(
            body, METHOD_VA, offset, prefix, fmt, read_va, name
        )
        constants[name] = {
            "value": value,
            "sourceVirtualAddress": f"0x{target:X}",
        }
    expected_values = {
        "centerDefault": 0.5,
        "centerNdcScale": 2.0,
        "centerUnit": 1.0,
        "farCenterRadius": 1.414,
        "centerEdgeScale": 0.5,
        "temporaryPowerSeed": 1.2000000476837158,
        "modeThreshold": 0.01,
    }
    for name, expected in expected_values.items():
        require(constants[name]["value"] == expected,
                f"{name} constant drifted")

    return {
        "constants": constants,
        "landmarks": [
            {"bodyOffset": f"0x{offset:X}", "bytes": encoded, "meaning": label}
            for offset, encoded, label in landmarks
        ],
    }


def load_mapping_helper() -> Any:
    spec = importlib.util.spec_from_file_location(
        "endfield_uber_parameter_body_map", MAPPING_HELPER
    )
    require(spec is not None and spec.loader is not None,
            f"cannot load mapping helper: {MAPPING_HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def exact_type(md: Any, full_name: str) -> Any:
    matches = [row for row in md.types if md.type_full_name(row) == full_name]
    require(len(matches) == 1,
            f"metadata type {full_name} resolved {len(matches)} times")
    return matches[0]


def field_names(md: Any, type_def: Any) -> list[str]:
    return [
        md.string(md.fields[index].name_index)
        for index in range(
            type_def.field_start, type_def.field_start + type_def.field_count
        )
    ]


def build(gate: common.InstalledNativeInputs) -> dict[str, Any]:
    require(gate.validated, f"pinned native input gate failed: {gate.detail}")
    mapping = load_mapping_helper()
    catalog = mapping.load_catalog_module()
    md = catalog.Metadata(gate.metadata)
    pe = mapping.PeImage(gate.gameassembly)
    modules = mapping.parse_codegen_modules(pe, mapping.DEFAULT_CODE_REGISTRATION)
    ranges = mapping.image_method_ranges(md)
    pointers, _pointer_rows = mapping.build_pointer_indexes(
        pe, md, modules, ranges
    )

    target_type = exact_type(md, TYPE_NAME)
    matches = []
    for index in range(
        target_type.method_start,
        target_type.method_start + target_type.method_count,
    ):
        method = md.methods[index]
        if (md.string(method.name_index) == METHOD_NAME
                and method.token == METHOD_TOKEN):
            matches.append((index, method))
    require(len(matches) == 1,
            f"target metadata method resolved {len(matches)} times")
    method_index, method = matches[0]
    require(method_index == METHOD_INDEX, "target method index drifted")
    method_row = catalog.method_row(md, method)
    actual_parameters = [
        (row["name"], row["typeName"])
        for row in method_row["parameterDetails"]
    ]
    require(actual_parameters == EXPECTED_PARAMETERS,
            "target method parameter contract drifted")

    require(IMAGE_NAME in ranges and IMAGE_NAME in pointers,
            f"codegen image is missing: {IMAGE_NAME}")
    image_range = ranges[IMAGE_NAME]
    slot = method_index - image_range["methodStart"]
    require(0 <= slot < len(pointers[IMAGE_NAME]),
            "target method slot is outside codegen pointer table")
    method_va = pointers[IMAGE_NAME][slot]
    require(method_va == METHOD_VA,
            f"target method VA drifted: 0x{method_va:X}")
    all_pointers = sorted({
        value for rows in pointers.values() for value in rows if value
    })
    next_index = bisect_right(all_pointers, method_va)
    require(next_index < len(all_pointers), "target method has no bounded successor")
    next_va = all_pointers[next_index]
    require(next_va == METHOD_NEXT_VA,
            f"target method successor drifted: 0x{next_va:X}")
    body = pe.bytes_at_va(method_va, next_va - method_va)
    decoded = decode_body_contract(body, pe.bytes_at_va)

    metadata_fields: dict[str, list[str]] = {}
    for full_name, expected in EXPECTED_FIELDS.items():
        actual = field_names(md, exact_type(md, full_name))
        require(actual == expected, f"{full_name} field contract drifted")
        metadata_fields[full_name] = actual
    pass_type_name = "HG.Rendering.Runtime.UberPostPassUtils+UberPostPassData"
    pass_fields = field_names(md, exact_type(md, pass_type_name))
    for name in EXPECTED_PASS_FIELDS:
        require(name in pass_fields, f"pass-data field is missing: {name}")

    return {
        "schema": "endfield.endminf-uber-radial-chromatic-native-parameters.v1",
        "status": "validated_exact_native_parameter_contract",
        "nativeEvidence": {
            "gate": gate.status,
            "gameAssembly": str(gate.gameassembly),
            "gameAssemblySha256": gate.gameassembly_sha256,
            "globalMetadata": str(gate.metadata),
            "globalMetadataSha256": gate.metadata_sha256,
            "codeRegistrationVa": f"0x{mapping.DEFAULT_CODE_REGISTRATION:X}",
        },
        "target": {
            "image": IMAGE_NAME,
            "type": TYPE_NAME,
            "method": METHOD_NAME,
            "methodIndex": method_index,
            "token": f"0x{METHOD_TOKEN:08X}",
            "virtualAddress": f"0x{method_va:X}",
            "nextMethodVirtualAddress": f"0x{next_va:X}",
            "boundedSizeBytes": len(body),
            "bodySha256": sha256_bytes(body),
            "parameters": [
                {"name": name, "type": type_name}
                for name, type_name in actual_parameters
            ],
        },
        "metadataFields": metadata_fields,
        "decodedNativeBody": decoded,
        "activity": {
            "radialActive": (
                "radialBlur.IsActive() && settingParameters.radialBlurEnabled"
            ),
            "chromaticActive": (
                "chromaticAbberation.IsActive() && "
                "settingParameters.chromaticAberrationEnabled"
            ),
            "inactiveBehavior": (
                "when both effective activity flags are false, the method returns "
                "without writing radialBlurParams or radialBlurParams2"
            ),
            "keywordSelection": {
                "radialOnly": "RADIAL_BLUR",
                "chromaticActive": "RADIAL_BLUR_CHROMATIC_ABERRATION",
            },
        },
        "centerSelection": {
            "default": [0.5, 0.5],
            "precedence": [
                "chromatic center when chromatic is active and either center.overrideState or enableGlobalCenter.value is true",
                "radial center when radial is active and either center.overrideState or enableGlobalCenter.value is true",
                "default center",
            ],
            "localCenter": "selected center.value",
            "globalCenter": "camera.WorldToViewportPoint(globalCenter.value).xy",
            "commonRemap": (
                "q = 2*center-1; when length(q)>1.414, center=(normalize(q)+1)*0.5; "
                "then center.x and center.y are independently Clamp01"
            ),
        },
        "shaderAbi": {
            "buffer": "exact combined Uber pixel pass cbuffer (PS b1)",
            "vectors": [
                {
                    "passDataField": "radialBlurParams",
                    "passDataOffset": EXPECTED_PASS_FIELDS["radialBlurParams"],
                    "shaderProperty": "_RadialBlurParams",
                    "shaderRegister": "c0",
                    "lanes": {
                        "x": "selected/remapped center.x",
                        "y": "selected/remapped center.y",
                        "z": "radialBlur.intensity.value, or 0 when radial is inactive",
                        "w": "effective radial power",
                    },
                },
                {
                    "passDataField": "radialBlurParams2",
                    "passDataOffset": EXPECTED_PASS_FIELDS["radialBlurParams2"],
                    "shaderProperty": "_RadialBlurParams2",
                    "shaderRegister": "c25",
                    "lanes": {
                        "x": "mode as float (3 or 6)",
                        "y": "chromaticAbberation.intensity.value",
                        "z": "float(radialBlur.averageSteps.value), or 0 when radial is inactive",
                        "w": "float(chromaticAbberation.averageStep.value), or 0 when chromatic is inactive",
                    },
                },
            ],
        },
        "scalingAndSelection": {
            "radialIntensityScaling": "none",
            "chromaticIntensityScaling": "none",
            "averageStepEncoding": "BooleanParameter value converted exactly to float 0.0 or 1.0",
            "effectivePower": {
                "radialOnly": "radialBlur.power.value",
                "chromaticOnly": "1.0",
                "bothActive": (
                    "lerp(1.0, radialBlur.power.value, "
                    "Clamp01(radialBlur.intensity.value / "
                    "chromaticAbberation.intensity.value))"
                ),
                "temporarySeed": (
                    "1.2000000476837158 is loaded before branching but is replaced "
                    "on every path that writes output; it is not an effective output power"
                ),
            },
            "modeSelection": {
                "mode6": (
                    "radialActive && chromaticActive && "
                    "double(radialBlur.intensity.value) > 0.01"
                ),
                "mode3": "all other output-writing states",
                "comparison": (
                    "the float intensity is converted to double and compared with the "
                    "pinned double literal 0.01; <= and unordered select mode 3"
                ),
            },
        },
        "scopeBoundary": (
            "This report decodes the managed IL2CPP producer and its exact recovered "
            "Uber c0/c25 ABI. It does not modify or approximate Unity beauty rendering."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    gate = common.check_installed_native_inputs(
        REVERSE_GAMEASSEMBLY_SHA256,
        REVERSE_METADATA_SHA256,
    )
    try:
        report = build(gate)
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    except (OSError, ValueError, struct.error, AuditError) as exc:
        print(f"audit_endminf_uber_radial_chromatic_parameters: FAIL: {exc}",
              file=sys.stderr)
        return 1
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != payload:
            print(
                "audit_endminf_uber_radial_chromatic_parameters: "
                f"stale report: {OUTPUT}",
                file=sys.stderr,
            )
            return 1
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(payload, encoding="utf-8", newline="\n")
    print(
        "audit_endminf_uber_radial_chromatic_parameters: OK "
        "c0=xy_center,z_radial,w_power c25=x_mode,y_chromatic,z_radialAvg,w_chromaticAvg"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
