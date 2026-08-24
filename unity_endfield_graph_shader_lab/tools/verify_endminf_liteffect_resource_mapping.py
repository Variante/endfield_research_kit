"""Verify the resource/reflection contract for Endminf's LitEffect HGBuffer.

This verifier intentionally keeps physical D3D registers separate from Unity's
descriptor names.  The representative DXBCs have no RDEF chunk, so constant
buffer names and offsets come from the serialized Shader metadata while
register arrays/signatures come from DXBC and the pinned Ruri output.  Any
mapping that cannot be made unique is recorded as a gap rather than inferred.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SIDE_ROOT = ROOT / "scratch" / "animestudio" / "endminf_liteffect_shader" / "sidecars"
BYTECODE_ROOT = SIDE_ROOT / "Shader" / "HGRP_LitEffect_p5936F49FA93F14DD.shader.bytecode"
EVIDENCE_PATH = ROOT / "unity_endfield_graph_shader_lab" / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "ExternalUiEffects" / "endminf_liteffect_subprogram_evidence.json"
CLOSURE_PATH = ROOT / "unity_endfield_graph_shader_lab" / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "ExternalUiEffects" / "endminf_material_closure.json"
MATERIAL_ROOT = ROOT / "export_full" / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "json_by_type" / "Material"
REPORT_PATH = ROOT / "unity_endfield_graph_shader_lab" / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "ExternalUiEffects" / "endminf_liteffect_resource_mapping.json"

VERTEX_FILE = "0114_endfield_dxbc_0.dxbc"
FRAGMENT_FILE = "0115_endfield_dxbc_1.dxbc"
VERTEX_SPIRV_FILE = "0117_endfield_spirv_0.spv"
FRAGMENT_SPIRV_FILE = "0119_endfield_spirv_1.spv"
VERTEX_RURI = SIDE_ROOT / "Shader" / "HGRP_LitEffect_p5936F49FA93F14DD.shader.bytecode" / "ruri_final" / "parallax_hgbuffer_vertex.hlsl"
FRAGMENT_RURI = SIDE_ROOT / "Shader" / "HGRP_LitEffect_p5936F49FA93F14DD.shader.bytecode" / "ruri_final" / "parallax_hgbuffer_fragment.hlsl"
SPIRV_CROSS = ROOT / "tools" / "RenderDoc_1.45" / "RenderDoc_1.45_64" / "plugins" / "spirv" / "spirv-cross.exe"

EXPECTED_SPIRV = {
    VERTEX_SPIRV_FILE: (15888, "29629b9daddd336e8c3a549ed459108f340d1af00186717bedf31c8e301ef362"),
    FRAGMENT_SPIRV_FILE: (20160, "5c4f933ae2a53e2f8ba8ee65d1db4b541621d3c0d6174dd0923025a8582de526"),
}

MATERIAL_NAMES = (
    "M_fx_endminm_gfx_01_p5A6341E8A834E421.json",
    "M_fx_endminm_gfx_27_pA531A88850690EB8.json",
    "M_fx_endminm_gfx_38_pAFCE491DD7BC5724.json",
)
TEXTURE_NAMES = (
    "_ParallaxNoiseMap",
    "_ParallaxMaskMap",
    "_ParallaxMap",
    "_NormalMap",
    "_MROMap",
    "_BaseColorMap",
)
PARALLAX_FLOATS = (
    "_EnableParallaxMap",
    "_ParallaxStrength",
    "_ParallaxMarchNum",
    "_ParallaxTilling",
    "_ParallaxAnimRandom",
    "_ParallaxAnimSpeed",
    "_ParallaxBrightInnerRadius",
    "_ParallaxBrightOuterRadius",
    "_ParallaxBrightStrength",
    "_ParallaxFresnelStrength",
    "_ParallaxIgnorePostExposure",
    "_ParallaxIntensity",
    "_ParallaxMaskMapColorStrength",
    "_ParallaxMinBrightness",
    "_ParallaxNoiseMapTilling",
    "_ParallaxCharPos",
    "_ParallaxMaskByLayerBlend",
    "_ParallaxLerpSchedule",
    "_ParallaxSignControl",
)
PARALLAX_COLORS = (
    "_ParallaxColor",
    "_ParallaxColorDark",
    "_ParallaxPatternColor",
    "_ParallaxPatternColorDark",
    "_ParallaxSignLerpFactor0",
    "_ParallaxSignLerpFactor1",
    "_WorldParallaxAdditionalColor",
)

EXPECTED_SELECTED_PARALLAX_FIELDS = {
    "_ParallaxStrength": (352, 4),
    "_ParallaxMarchNum": (384, 4),
    "_ParallaxTilling": (388, 4),
    "_ParallaxAnimSpeed": (392, 4),
    "_ParallaxAnimRandom": (396, 4),
    "_ParallaxMinBrightness": (400, 4),
    "_ParallaxFresnelStrength": (404, 4),
    "_ParallaxIgnorePostExposure": (408, 4),
    "_ParallaxMaskByLayerBlend": (420, 4),
    "_ParallaxNoiseMapTilling": (424, 4),
    "_ParallaxCharPos": (428, 4),
    "_ParallaxBrightOuterRadius": (432, 4),
    "_ParallaxBrightInnerRadius": (436, 4),
    "_ParallaxBrightStrength": (440, 4),
    "_ParallaxIntensity": (460, 4),
    "_ParallaxColor": (464, 16),
    "_ParallaxColorDark": (480, 16),
}


class VerificationError(ValueError):
    """Raised when evidence is absent, malformed, or no longer matches."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise VerificationError(f"missing JSON evidence: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"JSON evidence is not an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if len(data) < 32 or data[:4] != b"DXBC":
        raise VerificationError("not a DXBC container")
    count = struct.unpack_from("<I", data, 28)[0]
    table_end = 32 + count * 4
    if table_end > len(data):
        raise VerificationError("DXBC chunk table extends outside the container")
    chunks: list[tuple[bytes, bytes]] = []
    for offset in struct.unpack_from(f"<{count}I", data, 32):
        if offset < table_end or offset + 8 > len(data):
            raise VerificationError("DXBC chunk offset is outside the container")
        fourcc = data[offset : offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        end = offset + 8 + size
        if end > len(data):
            raise VerificationError("DXBC chunk extends outside the container")
        chunks.append((fourcc, data[offset + 8 : end]))
    return chunks


def _signature(data: bytes, wanted: tuple[bytes, ...]) -> list[dict[str, Any]]:
    for fourcc, chunk in _chunks(data):
        if fourcc not in wanted:
            continue
        if len(chunk) < 8:
            raise VerificationError(f"short {fourcc.decode('ascii', 'replace')} chunk")
        count = struct.unpack_from("<I", chunk, 0)[0]
        record_size = 32 if fourcc in (b"ISG1", b"OSG1") else 24
        result: list[dict[str, Any]] = []
        for index in range(count):
            offset = 8 + index * record_size
            if offset + 24 > len(chunk):
                raise VerificationError("short DXBC signature record")
            name_offset, semantic_index = struct.unpack_from("<II", chunk, offset)
            component_type = struct.unpack_from("<I", chunk, offset + 12)[0]
            register = struct.unpack_from("<I", chunk, offset + 16)[0]
            mask = chunk[offset + 20]
            if name_offset >= len(chunk):
                raise VerificationError("bad DXBC semantic name offset")
            name = chunk[name_offset:].split(b"\0", 1)[0].decode("ascii", errors="replace")
            result.append(
                {
                    "semantic": name,
                    "index": semantic_index,
                    "register": register,
                    "mask": mask,
                    "components": mask.bit_count(),
                    "componentType": {1: "uint", 2: "sint", 3: "float"}.get(component_type, str(component_type)),
                }
            )
        return result
    raise VerificationError(f"DXBC has none of {','.join(x.decode() for x in wanted)}")


def _dxbc_reflection(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    chunks = _chunks(data)
    names = [fourcc.decode("ascii", errors="replace") for fourcc, _ in chunks]
    has_rdef = b"RDEF" in {fourcc for fourcc, _ in chunks}
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": len(data),
        "sha256": _sha256(path),
        "chunks": names,
        "hasRdef": has_rdef,
        "inputs": _signature(data, (b"ISGN", b"ISG1")),
        "outputs": _signature(data, (b"OSGN", b"OSG1")),
    }


def _ruri_declarations(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise VerificationError(f"missing Ruri output: {path}")
    text = path.read_text(encoding="utf-8")
    cbuffer_pattern = re.compile(
        r"cbuffer\s+(?P<name>[^\s:{]+)\s*:\s*register\(b(?P<register>\d+)\s*,\s*space(?P<space>\d+)\)\s*\{(?P<body>.*?)\};",
        re.DOTALL,
    )
    cbuffer_aliases: list[dict[str, Any]] = []
    for match in cbuffer_pattern.finditer(text):
        arrays = []
        for array in re.finditer(r"float4\s+(\w+)\[(\d+)(?:u)?\]\s*:\s*packoffset\(c0\)", match.group("body")):
            arrays.append({"name": array.group(1), "arraySize": int(array.group(2)), "sizeBytes": int(array.group(2)) * 16})
        if not arrays:
            raise VerificationError(f"Ruri cbuffer has no float4 arrays: {path.name}:{match.group('name')}")
        cbuffer_aliases.append(
            {
                "name": match.group("name"),
                "register": int(match.group("register")),
                "space": int(match.group("space")),
                "arrays": arrays,
            }
        )
    if not cbuffer_aliases:
        raise VerificationError(f"Ruri output has no cbuffer declarations: {path}")

    resources: list[dict[str, Any]] = []
    resource_pattern = re.compile(
        r"(?P<kind>ByteAddressBuffer|StructuredBuffer(?:<[^>]+>)?|Texture2D(?:<[^>]+>)?)\s+(?P<name>\w+)\s*:\s*register\(t(?P<register>\d+)\s*,\s*space(?P<space>\d+)\)\s*;"
    )
    for match in resource_pattern.finditer(text):
        resources.append({"kind": match.group("kind"), "name": match.group("name"), "register": int(match.group("register")), "space": int(match.group("space"))})
    samplers: list[dict[str, Any]] = []
    sampler_pattern = re.compile(
        r"SamplerState\s+(?P<name>\w+)\s*:\s*register\(s(?P<register>\d+)\s*,\s*space(?P<space>\d+)\)\s*;"
    )
    for match in sampler_pattern.finditer(text):
        samplers.append({"name": match.group("name"), "register": int(match.group("register")), "space": int(match.group("space"))})

    physical: dict[str, dict[str, Any]] = {}
    for row in cbuffer_aliases:
        key = f"b{row['register']}@space{row['space']}"
        entry = physical.setdefault(key, {"register": row["register"], "space": row["space"], "arraySizes": [], "aliases": []})
        entry["aliases"].append(row["name"])
        for array in row["arrays"]:
            if array["arraySize"] not in entry["arraySizes"]:
                entry["arraySizes"].append(array["arraySize"])
    for entry in physical.values():
        entry["arraySizes"].sort()
        entry["sizeBytes"] = entry["arraySizes"][-1] * 16
        entry["aliases"].sort()
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "physicalCbuffers": sorted(physical.values(), key=lambda row: row["register"]),
        "resources": sorted(resources, key=lambda row: row["register"]),
        "samplers": sorted(samplers, key=lambda row: row["register"]),
    }


def _compact_metadata(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    required = ("ConstantBufferParameters", "BufferBindingParameters", "SamplerParameters", "DescriptorSetParameters")
    for key in required:
        if not isinstance(data.get(key), list):
            raise VerificationError(f"{path.name} missing {key}")
    for key, expected in (("SourceSubProgramIndex", 19), ("SourceProgramBlobIndex", 207), ("SourcePassName", "HGBuffer")):
        if data.get(key) != expected:
            raise VerificationError(f"{path.name} {key} mismatch: {data.get(key)!r}")
    descriptor_sets = []
    interesting_global = {4, 5, 6, 7, 8, 9, 10, 13, 16, 19, 20, 33}
    for descriptor_set in data["DescriptorSetParameters"]:
        set_id = descriptor_set.get("SetId")
        if set_id == 0:
            bindings = [row for row in descriptor_set.get("Bindings", []) if row.get("BindingIndex") in interesting_global]
        else:
            bindings = list(descriptor_set.get("Bindings", []))
        descriptor_sets.append({"Name": descriptor_set.get("Name"), "SetId": set_id, "MaxBindingIndex": descriptor_set.get("MaxBindingIndex"), "Bindings": bindings})
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": _sha256(path),
        "decodedStage": data.get("DecodedProgramStage"),
        "serializedStage": data.get("SourceSerializedProgramStage"),
        "sourceStage": data.get("DecodedProgramStage"),
        "shaderCab": data.get("ShaderCab"),
        "shaderPathId": data.get("ShaderPathId"),
        "shaderName": data.get("ShaderName"),
        "debugName": data.get("DebugName"),
        "passName": data.get("SourcePassName"),
        "passIndex": data.get("SourcePassIndex"),
        "subProgramIndex": data.get("SourceSubProgramIndex"),
        "programBlobIndex": data.get("SourceProgramBlobIndex"),
        "keywords": data.get("SourceCompiledKeywords", []),
        "constantBuffers": data["ConstantBufferParameters"],
        "bufferParameters": data.get("BufferParameters", []),
        "bufferBindings": data["BufferBindingParameters"],
        "samplers": data["SamplerParameters"],
        "descriptorSets": descriptor_sets,
        "sourceEndfieldParameterRecordParsed":
            data.get("SourceEndfieldParameterRecordParsed"),
        "sourceEndfieldConstantBufferTableParsed":
            data.get("SourceEndfieldConstantBufferTableParsed"),
    }


def _material_property_names(shader_source: Path) -> set[str]:
    if not shader_source.is_file():
        raise VerificationError(f"missing converted shader source: {shader_source}")
    text = shader_source.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"^\s*(?:\[[^\]]+\]\s*)?(_[A-Za-z0-9]+)\s*\(", text, re.MULTILINE))


def _texture_identity_map() -> dict[int, dict[str, Any]]:
    closure = _read_json(CLOSURE_PATH)
    result: dict[int, dict[str, Any]] = {}
    for identity in closure.get("identities", []):
        if not isinstance(identity, dict) or identity.get("targetType") != "Texture2D":
            continue
        path_id = identity.get("pathId")
        if isinstance(path_id, int):
            if path_id in result:
                raise VerificationError(f"duplicate Texture2D identity PathID: {path_id}")
            result[path_id] = identity
    return result


def _material_path_id_from_name(name: str) -> tuple[int, str]:
    match = re.search(r"_p([0-9A-Fa-f]{16})\.json$", name)
    if not match:
        raise VerificationError(f"material filename has no PathID suffix: {name}")
    unsigned = int(match.group(1), 16)
    signed = unsigned - (1 << 64) if unsigned >= (1 << 63) else unsigned
    return signed, match.group(1).upper()


def _material_rows(
    shader_source: Path,
    texture_identities: dict[int, dict[str, Any]],
    material_fields: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    declared = _material_property_names(shader_source)
    rows: list[dict[str, Any]] = []
    for name in MATERIAL_NAMES:
        path = MATERIAL_ROOT / name
        data = _read_json(path)
        material_path_id, material_path_id_hex = _material_path_id_from_name(name)
        if data.get("m_Shader", {}).get("m_PathID") != 6428594484694422749:
            raise VerificationError(f"{name} does not reference HGRP/LitEffect")
        if data.get("m_ValidKeywords") != ["_PARALLAX_MAP"]:
            raise VerificationError(f"{name} is not the _PARALLAX_MAP material variant")
        tex_envs = data.get("m_SavedProperties", {}).get("m_TexEnvs", {})
        textures = []
        for prop in TEXTURE_NAMES:
            tex = tex_envs.get(prop, {}).get("m_Texture")
            if not isinstance(tex, dict):
                raise VerificationError(f"{name} missing texture property {prop}")
            path_id = tex.get("m_PathID")
            is_null = tex.get("IsNull") is True or tex.get("m_FileID", 0) == 0 or path_id == 0
            identity = None if is_null else texture_identities.get(path_id)
            resolved = bool(identity and identity.get("status") in ("resolved", "resolved_byte_identical_mirror"))
            occurrence = None
            if not is_null:
                if not identity:
                    raise VerificationError(f"{name} PPtr {prop} has no closure identity: {path_id}")
                matches = [row for row in identity.get("occurrences", []) if isinstance(row, dict) and row.get("materialPathIdHex") == material_path_id_hex and row.get("property") == f"m_TexEnvs.{prop}.m_Texture"]
                if len(matches) != 1:
                    raise VerificationError(f"{name} PPtr {prop} closure occurrence count is {len(matches)}, expected exactly one")
                occurrence = matches[0]
                expected_artifact = str(path.relative_to(ROOT)).replace("\\", "/")
                if occurrence.get("materialArtifact") != expected_artifact or occurrence.get("materialPathId") != material_path_id or occurrence.get("fileId") != tex.get("m_FileID"):
                    raise VerificationError(f"{name} PPtr {prop} closure material artifact/PathID/fileId mismatch")
                if occurrence.get("material") != (data.get("Name") or data.get("m_Name")):
                    raise VerificationError(f"{name} PPtr {prop} closure material name mismatch")
                if identity.get("pathId") != path_id or identity.get("targetType") != "Texture2D" or not identity.get("serializedFile"):
                    raise VerificationError(f"{name} PPtr {prop} target CAB/PathID identity is incomplete")
            textures.append(
                {
                    "property": prop,
                    "fileId": tex.get("m_FileID"),
                    "pathId": path_id,
                    "isNull": is_null,
                    "status": "resolved" if resolved else "gap",
                    "targetName": identity.get("targetName") if identity else None,
                    "targetSerializedFile": identity.get("serializedFile") if identity else None,
                    "closureOccurrence": {key: occurrence.get(key) for key in ("materialPathIdHex", "materialArtifact", "property", "fileId")} if occurrence else None,
                    "artifact": identity.get("artifact") if identity else None,
                }
            )
        floats = data.get("m_SavedProperties", {}).get("m_Floats", {})
        colors = data.get("m_SavedProperties", {}).get("m_Colors", {})
        properties = []
        for prop in PARALLAX_FLOATS:
            selected = material_fields[prop]
            properties.append({"property": prop, "kind": "float", "value": floats.get(prop), "shaderPropertyDeclared": prop in declared, "constantBufferOffsetBytes": selected["offsetBytes"], "status": ("resolved_material_value_and_selected_variant_offset" if prop in floats and prop in declared and selected["offsetBytes"] is not None else "resolved_material_value_only_selected_variant_offset_absent" if prop in floats and prop in declared else "gap")})
        for prop in PARALLAX_COLORS:
            selected = material_fields[prop]
            properties.append({"property": prop, "kind": "color", "value": colors.get(prop), "shaderPropertyDeclared": prop in declared, "constantBufferOffsetBytes": selected["offsetBytes"], "status": ("resolved_material_value_and_selected_variant_offset" if prop in colors and prop in declared and selected["offsetBytes"] is not None else "resolved_material_value_only_selected_variant_offset_absent" if prop in colors and prop in declared else "gap")})
        rows.append(
            {
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "name": data.get("Name") or data.get("m_Name"),
                "shaderPathId": data["m_Shader"]["m_PathID"],
                "validKeywords": data["m_ValidKeywords"],
                "textures": textures,
                "parallaxProperties": properties,
            }
        )
    return rows


def _field_size(parameter: dict[str, Any]) -> int:
    if parameter.get("IsMatrix") or parameter.get("ColumnCount", 1) > 1:
        return int(parameter.get("RowCount", 1)) * int(parameter.get("ColumnCount", 1)) * 4 * max(1, int(parameter.get("ArraySize", 0) or 1))
    return int(parameter.get("RowCount", 1)) * 4 * max(1, int(parameter.get("ArraySize", 0) or 1))


def _common_fields(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for cb in metadata["constantBuffers"]:
        for parameter in cb.get("VectorParameters", []) + cb.get("MatrixParameters", []):
            fields.append(
                {
                    "buffer": cb.get("Name"),
                    "name": parameter.get("Name"),
                    "offsetBytes": parameter.get("Index"),
                    "sizeBytes": _field_size(parameter),
                    "arraySize": parameter.get("ArraySize", 0),
                    "isMatrix": bool(parameter.get("IsMatrix")),
                    "status": "serialized_parameter_resolved",
                }
            )
    return fields


def _selected_material_fields(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if metadata.get("sourceEndfieldParameterRecordParsed") is not True:
        raise VerificationError("selected fragment Endfield parameter record was not parsed")
    if metadata.get("sourceEndfieldConstantBufferTableParsed") is not True:
        raise VerificationError(
            "selected fragment Endfield constant-buffer table was not parsed")
    buffers = [
        row for row in metadata["constantBuffers"]
        if row.get("Name") == "UnityPerMaterial"
    ]
    if len(buffers) != 1:
        raise VerificationError(
            f"selected fragment has {len(buffers)} UnityPerMaterial tables")
    buffer = buffers[0]
    if buffer.get("Size") != 576 or buffer.get("IsPartialCB") is not True:
        raise VerificationError(
            "selected fragment UnityPerMaterial size/partial-table contract drifted")

    fields: dict[str, dict[str, Any]] = {}
    for parameter in (
        buffer.get("VectorParameters", []) + buffer.get("MatrixParameters", [])
    ):
        name = parameter.get("Name")
        offset = parameter.get("Index")
        size = _field_size(parameter)
        if not isinstance(name, str) or not name or name in fields:
            raise VerificationError(
                "selected fragment UnityPerMaterial has a missing or duplicate field")
        if not isinstance(offset, int) or offset < 0 or offset + size > 576:
            raise VerificationError(
                f"selected fragment UnityPerMaterial field is out of range: {name}")
        fields[name] = {
            "property": name,
            "constantBuffer": "UnityPerMaterial",
            "register": 3,
            "offsetBytes": offset,
            "sizeBytes": size,
            "type": parameter.get("Type"),
            "status": "resolved_selected_variant_offset",
            "basis": [
                "Endfield combined-program constant-buffer table",
                "serialized PerMaterial descriptor binding 12",
                "same-blob SPIR-V 576-byte layout",
                "DXBC/Ruri fragment b3 496-byte used prefix",
            ],
        }

    actual = {
        name: (fields[name]["offsetBytes"], fields[name]["sizeBytes"])
        for name in EXPECTED_SELECTED_PARALLAX_FIELDS
        if name in fields
    }
    if actual != EXPECTED_SELECTED_PARALLAX_FIELDS:
        raise VerificationError(
            f"selected fragment parallax field map drifted: {actual!r}")

    return {
        prop: fields.get(prop, {
            "property": prop,
            "constantBuffer": "UnityPerMaterial",
            "register": 3,
            "offsetBytes": None,
            "sizeBytes": None,
            "type": None,
            "status": "selected_variant_offset_absent",
            "reason": (
                "The recovered selected-subprogram constant table contains no "
                "field with this name; retain the serialized material value "
                "without inventing a b3 offset."
            ),
        })
        for prop in (*PARALLAX_FLOATS, *PARALLAX_COLORS)
    }


def _descriptor_bindings(metadata: dict[str, Any], set_id: int) -> list[dict[str, Any]]:
    rows = [row for row in metadata["descriptorSets"] if row.get("SetId") == set_id]
    if len(rows) != 1:
        raise VerificationError(f"serialized metadata has {len(rows)} descriptor sets with SetId {set_id}")
    return rows[0].get("Bindings", [])


def _packed_stage_register(binding: dict[str, Any], stage: str) -> int | None:
    packed = int(binding.get("PackedBinding", 0)) & 0xFFFFFFFF
    stage_mask = packed & 0xFF
    shift = 24 if stage == "vertex" else 16
    register = (packed >> shift) & 0xFF
    stage_bit = 1 if stage == "vertex" else 2
    return register if stage_mask & stage_bit and register != 0xFF else None


def _reflect_spirv_ubos(path: Path) -> list[dict[str, Any]]:
    expected_size, expected_hash = EXPECTED_SPIRV[path.name]
    if path.stat().st_size != expected_size or _sha256(path) != expected_hash:
        raise VerificationError(f"pinned SPIR-V identity drifted: {path.name}")
    try:
        completed = subprocess.run(
            [str(SPIRV_CROSS), str(path), "--reflect"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        reflection = json.loads(completed.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise VerificationError(f"could not reflect {path.name}: {exc}") from exc
    return [
        {
            "name": row.get("name"),
            "set": int(row["set"]),
            "binding": int(row["binding"]),
            "blockSize": int(row["block_size"]),
            "type": row.get("type"),
        }
        for row in reflection.get("ubos", [])
    ]


def _validate_descriptor_contract(metadata: dict[str, Any]) -> dict[str, Any]:
    global_bindings = {row.get("BindingIndex"): row for row in _descriptor_bindings(metadata, 0)}
    for index, name in ((13, "_TransformVariables"), (16, "ShaderVariablesGlobal"), (19, "_VertexSkinMatrices"), (33, "_TerrainSubsurfaceConstants")):
        row = global_bindings.get(index)
        if not row or row.get("Name") != name:
            raise VerificationError(f"Global descriptor binding {index} is not {name}")
    material = {row.get("BindingIndex"): row for row in _descriptor_bindings(metadata, 1)}
    expected = {**{index: name for index, name in enumerate(TEXTURE_NAMES)}, 6: TEXTURE_NAMES[0], 7: TEXTURE_NAMES[1], 8: TEXTURE_NAMES[2], 9: TEXTURE_NAMES[3], 10: TEXTURE_NAMES[4], 11: TEXTURE_NAMES[5], 12: "UnityPerMaterial"}
    for index, name in expected.items():
        row = material.get(index)
        if not row or row.get("Name") != name:
            raise VerificationError(f"PerMaterial descriptor binding {index} is not {name}")
    object_bindings = _descriptor_bindings(metadata, 2)
    if len(object_bindings) != 1 or object_bindings[0].get("BindingIndex") != 0 or object_bindings[0].get("Name") != "UnityPerDraw":
        raise VerificationError("PerObject descriptor binding 0 is not UnityPerDraw")
    return {
        "global": [global_bindings[index] for index in (13, 16, 19, 33)],
        "perMaterial": [material[index] for index in sorted(expected)],
        "perObject": object_bindings,
    }


def _target_evidence(vertex: dict[str, Any], fragment: dict[str, Any]) -> dict[str, Any]:
    evidence = _read_json(EVIDENCE_PATH)
    if evidence.get("status") != "verified":
        raise VerificationError("existing LitEffect evidence is not verified")
    reps = {row.get("fileName"): row for row in evidence.get("target", {}).get("representatives", []) if isinstance(row, dict)}
    manifest_path = BYTECODE_ROOT / "manifest.json"
    manifest = _read_json(manifest_path)
    shader = manifest.get("shader", {})
    if shader.get("cab") != "CAB-2c811ef28608ab220ecdb5c4e0629d2d" or shader.get("pathId") != 6428594484694422749 or shader.get("name") != "HGRP/LitEffect":
        raise VerificationError("manifest Shader CAB/PathID/name identity mismatch")
    manifest_rows = {row.get("fileName"): row for row in manifest.get("entries", []) if isinstance(row, dict)}
    for name, path in ((VERTEX_FILE, vertex), (FRAGMENT_FILE, fragment)):
        row = reps.get(name)
        if not row:
            raise VerificationError(f"existing evidence lacks representative {name}")
        if row.get("sha256") != path["sha256"] or row.get("byteCount") != path["bytes"]:
            raise VerificationError(f"representative evidence drifted for {name}")
        if row.get("subProgramIndex") != 19 or row.get("passName") != "HGBuffer" or "_PARALLAX_MAP" not in row.get("keywords", []):
            raise VerificationError(f"representative metadata mismatch for {name}")
        manifest_row = manifest_rows.get(name)
        if not manifest_row:
            raise VerificationError(f"manifest lacks representative {name}")
        expected_extra = {"platform": "d3d11", "shaderCab": "CAB-2c811ef28608ab220ecdb5c4e0629d2d", "shaderPathId": 6428594484694422749, "shaderName": "HGRP/LitEffect", "serializedStage": "vertex" if name == VERTEX_FILE else "vertex", "decodedStage": "vertex" if name == VERTEX_FILE else "fragment"}
        for key in ("sha256", "byteCount", "sourceOffset", "sourceSize", "passName", "subProgramIndex", "programBlobIndex", "platform", "keywords", "shaderCab", "shaderPathId", "shaderName", "serializedStage", "decodedStage"):
            expected = row.get(key, expected_extra.get(key))
            if manifest_row.get(key) != expected:
                raise VerificationError(f"manifest/evidence mismatch for {name}: {key}")
    return {
        "source": evidence.get("source"),
        "manifest": evidence.get("manifest"),
        "target": evidence.get("target"),
    }


def _validate_stage_metadata(metadata: dict[str, Any], reflection: dict[str, Any], evidence: dict[str, Any], filename: str, expected_stage: str) -> None:
    reps = {row.get("fileName"): row for row in evidence["target"]["representatives"] if isinstance(row, dict)}
    row = reps.get(filename)
    if not row:
        raise VerificationError(f"evidence lacks {filename}")
    if row.get("stage") != expected_stage or row.get("decodedStage") != expected_stage or row.get("stage") != row.get("decodedStage"):
        raise VerificationError(f"representative stage/decodedStage mismatch for {filename}")
    expected = {
        "sha256": reflection["sha256"],
        "decodedStage": expected_stage,
        "serializedStage": row.get("serializedStage"),
        "passName": "HGBuffer",
        "passIndex": 0,
        "subProgramIndex": 19,
        "programBlobIndex": 207,
        "keywords": ["HG_ENABLE_MV", "_PARALLAX_MAP"],
        "shaderCab": "CAB-2c811ef28608ab220ecdb5c4e0629d2d",
        "shaderPathId": 6428594484694422749,
        "shaderName": "HGRP/LitEffect",
    }
    metadata_path = BYTECODE_ROOT / (filename + ".metadata.json")
    if metadata.get("sha256") != _sha256(metadata_path):
        raise VerificationError(f"metadata file hash mismatch for {filename}")
    if metadata.get("debugName") != f"subshader0/pass0:HGBuffer/{row.get('serializedStage')}/blob207/33":
        raise VerificationError(f"metadata DebugName/stage mismatch for {filename}")
    for key in ("decodedStage", "serializedStage", "passName", "passIndex", "subProgramIndex", "programBlobIndex", "keywords"):
        if metadata.get(key) != expected[key]:
            raise VerificationError(f"metadata {key} mismatch for {filename}")
    # CAB/PathID/name are not fields in AnimeStudio's metadata JSON.  The
    # sidecar's manifest/evidence identity is therefore attached explicitly;
    # an entry with a different identity cannot pass the checks above.
    metadata["shaderCab"] = expected["shaderCab"]
    metadata["shaderPathId"] = expected["shaderPathId"]
    metadata["shaderName"] = expected["shaderName"]


def _map_vertex_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach the one exact physical range proven by the vertex register sizes.

    b0 is exactly the serialized _TransformVariables size.  b1/b2 are the
    contiguous 20+11 register global slice emitted by this representative;
    no fragment register is assigned to common named fields without a unique
    serialized/register proof.
    """
    result = []
    for field in fields:
        row = dict(field)
        if field["buffer"] == "_TransformVariables":
            row.update({"stage": "vertex", "register": 0, "registerOffsetBytes": field["offsetBytes"], "status": "resolved_register_range"})
        elif field["buffer"] == "ShaderVariablesGlobal" and field["offsetBytes"] < 320:
            row.update({"stage": "vertex", "register": 1, "registerOffsetBytes": field["offsetBytes"], "status": "resolved_register_range"})
        else:
            row.update({"stage": "vertex", "register": None, "registerOffsetBytes": None, "status": "gap"})
        result.append(row)
    return result


def build_report() -> dict[str, Any]:
    vertex_path = BYTECODE_ROOT / VERTEX_FILE
    fragment_path = BYTECODE_ROOT / FRAGMENT_FILE
    if not vertex_path.is_file() or not fragment_path.is_file():
        raise VerificationError("representative DXBC sidecars are missing")
    vertex_reflection = _dxbc_reflection(vertex_path)
    fragment_reflection = _dxbc_reflection(fragment_path)
    if vertex_reflection["hasRdef"] or fragment_reflection["hasRdef"]:
        raise VerificationError("RDEF unexpectedly present; do not mix RDEF and Endfield metadata paths")
    vertex_ruri = _ruri_declarations(VERTEX_RURI)
    fragment_ruri = _ruri_declarations(FRAGMENT_RURI)
    vertex_meta = _compact_metadata(BYTECODE_ROOT / (VERTEX_FILE + ".metadata.json"))
    fragment_meta = _compact_metadata(BYTECODE_ROOT / (FRAGMENT_FILE + ".metadata.json"))
    material_fields = _selected_material_fields(fragment_meta)
    descriptor_contract = _validate_descriptor_contract(fragment_meta)
    vertex_spirv_ubos = _reflect_spirv_ubos(BYTECODE_ROOT / VERTEX_SPIRV_FILE)
    fragment_spirv_ubos = _reflect_spirv_ubos(BYTECODE_ROOT / FRAGMENT_SPIRV_FILE)
    evidence = _target_evidence(vertex_reflection, fragment_reflection)
    _validate_stage_metadata(vertex_meta, vertex_reflection, evidence, VERTEX_FILE, "vertex")
    _validate_stage_metadata(fragment_meta, fragment_reflection, evidence, FRAGMENT_FILE, "fragment")
    ruri_evidence = {row.get("fileName"): row for row in _read_json(EVIDENCE_PATH).get("target", {}).get("ruriOutputs", []) if isinstance(row, dict)}
    for ruri_path in (VERTEX_RURI, FRAGMENT_RURI):
        name = ruri_path.name
        row = ruri_evidence.get(name)
        if not row or row.get("size") != ruri_path.stat().st_size or row.get("sha256") != _sha256(ruri_path):
            raise VerificationError(f"Ruri output hash/size mismatch for {name}")
    shader_source = SIDE_ROOT / "Shader" / "HGRP_LitEffect_p5936F49FA93F14DD.shader"
    texture_identities = _texture_identity_map()
    materials = _material_rows(shader_source, texture_identities, material_fields)

    expected_vertex = {0: 82, 1: 20, 2: 11}
    expected_fragment = {0: 45, 1: 106, 2: 5, 3: 31, 4: 1}
    for actual, expected, label in ((vertex_ruri["physicalCbuffers"], expected_vertex, "vertex"), (fragment_ruri["physicalCbuffers"], expected_fragment, "fragment")):
        found = {int(row["register"]): row["arraySizes"][-1] for row in actual}
        if found != expected:
            raise VerificationError(f"{label} Ruri cbuffer sizes mismatch: {found!r}")

    logical_descriptor_rows = {
        row["Name"]: row
        for row in (
            descriptor_contract["global"] +
            [row for row in descriptor_contract["perMaterial"] if row.get("DescriptorType") == 4] +
            descriptor_contract["perObject"]
        )
        if row.get("DescriptorType") == 4
    }
    expected_physical = {
        "vertex": {
            0: "_TransformVariables",
            1: "ShaderVariablesGlobal",
            2: "UnityPerDraw",
        },
        "fragment": {
            0: "_TransformVariables",
            1: "ShaderVariablesGlobal",
            2: "UnityPerDraw",
            3: "UnityPerMaterial",
            4: "_TerrainSubsurfaceConstants",
        },
    }
    for stage, expected in expected_physical.items():
        decoded = {
            register: name
            for name, row in logical_descriptor_rows.items()
            if (register := _packed_stage_register(row, stage)) is not None
        }
        if decoded != expected:
            raise VerificationError(
                f"{stage} PackedBinding register map mismatch: {decoded!r}")
    expected_spirv_ubos = {
        (0, 13): ("_TransformVariables", 1312),
        (0, 16): ("ShaderVariablesGlobal", 3200),
        (2, 0): ("UnityPerDraw", 256),
        (1, 12): ("UnityPerMaterial", 576),
        (0, 33): ("_TerrainSubsurfaceConstants", 16),
    }
    for rows, stage in ((vertex_spirv_ubos, "vertex"), (fragment_spirv_ubos, "fragment")):
        actual = {
            (row["set"], row["binding"]): row["blockSize"]
            for row in rows
        }
        expected = {
            location: size
            for location, (name, size) in expected_spirv_ubos.items()
            if _packed_stage_register(logical_descriptor_rows[name], stage) is not None
        }
        if actual != expected:
            raise VerificationError(
                f"{stage} SPIR-V UBO map mismatch: {actual!r}")

    dynamic_samplers = {row["BindPoint"]: row["Name"] for row in fragment_meta["samplers"] if isinstance(row.get("BindPoint"), int) and 0 <= row["BindPoint"] <= 5 and str(row.get("Name", "")).startswith("_")}
    if dynamic_samplers != {i: name for i, name in enumerate(TEXTURE_NAMES)}:
        raise VerificationError(f"PerMaterial sampler/name order mismatch: {dynamic_samplers!r}")
    vertex_resources = []
    for resource in vertex_ruri["resources"]:
        if resource["register"] == 0:
            vertex_resources.append({**resource, "logicalName": "_VertexSkinMatrices", "status": "resolved", "basis": ["DXBC/Ruri t0", "serialized BufferParameters", "Global descriptor binding 19"]})
    if len(vertex_resources) != 1:
        raise VerificationError("expected exactly one vertex t0 resource")
    fragment_resources = []
    if sorted(resource["register"] for resource in fragment_ruri["resources"]) != list(range(6)):
        raise VerificationError("fragment texture registers are not exactly t0..t5")
    expected_resource_names = {index: f"_{index + 8}" for index in range(6)}
    for resource in fragment_ruri["resources"]:
        slot = resource["register"]
        if resource.get("name") != expected_resource_names.get(slot):
            raise VerificationError(f"fragment texture resource name mismatch at t{slot}")
        logical = dynamic_samplers.get(slot)
        fragment_resources.append({**resource, "logicalName": logical, "status": "resolved" if logical else "gap", "basis": ["Ruri register", "serialized SamplerParameters BindPoint 0..5", "PerMaterial descriptor texture binding 6..11"] if logical else []})
    if len(fragment_resources) != 6:
        raise VerificationError(f"expected six fragment texture resources, got {len(fragment_resources)}")

    static_samplers = [{**row, "status": "resolved_static_name"} for row in fragment_ruri["samplers"]]
    if [row["register"] for row in static_samplers] != list(range(6)):
        raise VerificationError("fragment Ruri samplers are not the six s0..s5 slots")
    expected_ruri_samplers = ["sampler_LinearClamp", "sampler_LinearRepeat", "sampler_LinearMirror", "sampler_LinearMirrorOnce", "sampler_PointClamp", "sampler_PointRepeat"]
    if [row["name"] for row in static_samplers] != expected_ruri_samplers:
        raise VerificationError("fragment Ruri sampler declarations changed")
    static_metadata_names = {row.get("Name") for row in fragment_meta["samplers"] if isinstance(row.get("BindPoint"), int) and 5 <= row["BindPoint"] <= 10 and str(row.get("Name", "")).startswith("s_")}
    expected_metadata_names = {"s_trilinear_repeat_sampler", "s_trilinear_clamp_sampler", "s_point_repeat_sampler", "s_point_clamp_sampler", "s_linear_repeat_sampler", "s_linear_clamp_sampler"}
    if static_metadata_names != expected_metadata_names:
        raise VerificationError("serialized static sampler names changed")

    common_fields = _common_fields(vertex_meta)
    physical_vertex = [
        {"register": row["register"], "space": row["space"], "arraySize": row["arraySizes"][-1], "sizeBytes": row["sizeBytes"], "aliases": row["aliases"], "logicalName": expected_physical["vertex"][row["register"]], "status": "resolved_cross_platform_register", "basis": ["serialized PackedBinding stage/register bytes", "same-blob SPIR-V descriptor set/binding and block size", "DXBC/Ruri used-prefix size"]}
        for row in vertex_ruri["physicalCbuffers"]
    ]
    physical_fragment = [
        {"register": row["register"], "space": row["space"], "arraySize": row["arraySizes"][-1], "sizeBytes": row["sizeBytes"], "aliases": row["aliases"], "logicalName": expected_physical["fragment"][row["register"]], "status": "resolved_cross_platform_register", "basis": ["serialized PackedBinding stage/register bytes", "same-blob SPIR-V descriptor set/binding and block size", "DXBC/Ruri used-prefix size"]}
        for row in fragment_ruri["physicalCbuffers"]
    ]

    fragment_fields = []
    fragment_limits = {
        "_TransformVariables": (0, 720),
        "ShaderVariablesGlobal": (1, 1696),
        "_TerrainSubsurfaceConstants": (4, 16),
    }
    for field in common_fields:
        row = {**field, "stage": "fragment", "register": None,
               "registerOffsetBytes": None, "status": "gap"}
        if field["buffer"] in fragment_limits:
            register, limit = fragment_limits[field["buffer"]]
            if field["offsetBytes"] + field["sizeBytes"] <= limit:
                row.update({"register": register,
                            "registerOffsetBytes": field["offsetBytes"],
                            "status": "resolved_register_range"})
        fragment_fields.append(row)

    # The generated Shader JSON exposes parameter metadata, but does not emit
    # SerializedSubProgram.m_Channels.  Keep this absence explicit.
    bind_channels = {
        "status": "gap",
        "reason": "AnimeStudio Shader JSON omits ParserBindChannels.m_Channels; DXBC ISGN/OSGN signatures above are the available interface reflection.",
        "serializedMetadataClass": "ParserBindChannels",
    }
    report = {
        "schema": "endfield.endminf-liteffect-resource-mapping.v1",
        "status": "verified_with_selected_variant_material_offsets_and_consumer_gaps",
        "scope": {"shader": {"cab": "CAB-2c811ef28608ab220ecdb5c4e0629d2d", "pathId": 6428594484694422749, "name": "HGRP/LitEffect"}, "pass": "HGBuffer", "keywords": ["HG_ENABLE_MV", "_PARALLAX_MAP"], "subProgramIndex": 19, "platform": "d3d11"},
        "evidence": evidence,
        "reflection": {
            "vertex": {**vertex_reflection, "ruri": vertex_ruri, "metadata": vertex_meta},
            "fragment": {**fragment_reflection, "ruri": fragment_ruri, "metadata": fragment_meta},
        },
        "bindChannels": bind_channels,
        "vertexInputs": vertex_reflection["inputs"],
        "vertexOutputs": vertex_reflection["outputs"],
        "fragmentInputs": fragment_reflection["inputs"],
        "mrtOutputs": fragment_reflection["outputs"],
        "resources": {"vertex": vertex_resources, "fragmentTextures": fragment_resources, "fragmentSamplers": static_samplers},
        "crossPlatformSpirv": {
            "vertex": vertex_spirv_ubos,
            "fragment": fragment_spirv_ubos,
            "packedBindingDecode": "low byte is stage mask; byte 2 is fragment register; byte 3 is vertex register; 0xFF means unbound",
        },
        "constantBuffers": {
            "vertex": physical_vertex,
            "fragment": physical_fragment,
            "descriptorContract": descriptor_contract,
            "serializedFields": _map_vertex_fields(common_fields),
            "fragmentFieldMapping": fragment_fields,
            "materialConstantBufferFields": list(material_fields.values()),
        },
        "materials": materials,
        "gaps": [
            "DXBC has no RDEF chunk; named common-buffer fields come only from serialized Shader metadata.",
            "The selected b3 field map does not by itself close the other physical constant buffers or complete HGBuffer frame publication.",
            "ParserBindChannels.m_Channels is not exported by AnimeStudio's Shader JSON; do not substitute guessed ShaderLab channels.",
            "The null _ParallaxNoiseMap and _ParallaxMaskMap PPtrs remain unresolved by design.",
        ],
    }
    return report


def verify(report_path: Path | None = None) -> dict[str, Any]:
    report = build_report()
    if report_path is None:
        if not REPORT_PATH.is_file():
            raise VerificationError(f"durable report is missing: {REPORT_PATH}")
        current = _read_json(REPORT_PATH)
        if json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")) != json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")):
            raise VerificationError("durable report is stale; rerun with --write-report to update it")
    else:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true", help=f"write the durable report to {REPORT_PATH}")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = verify(REPORT_PATH if args.write_report else None)
    except VerificationError as exc:
        print(f"verification_failed: {exc}", file=sys.stderr)
        return 1
    print(f"status={report['status']} vertexInputs={len(report['vertexInputs'])} mrtOutputs={len(report['mrtOutputs'])} materials={len(report['materials'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
