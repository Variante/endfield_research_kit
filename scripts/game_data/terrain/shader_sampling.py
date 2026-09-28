"""Gate one authored Terrain shader texture binding against selected installed bytes.

The targeted AnimeStudio conversion is a disposable input, produced with
``ANIMESTUDIO_EXPORT_SHADER_BYTECODE_SIDECARS=1`` and a one-object filter. The
reviewed contract authenticates its source CHK and the selected program bytes.
No WebUI export is published by this validator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.terrain-shader-sampling-contract.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "terrain_shader_sampling.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/terrain/shader_sampling_latest.json"
SPV_MAGIC = 0x07230203


def _same_file(a: str | Path, b: Path, label: str) -> None:
    try:
        if not Path(a).samefile(b):
            raise ValueError(f"{label}:source-path-differs")
    except OSError as error:
        raise ValueError(f"{label}:source-path-unavailable:{error}") from error


def _one(rows: list[Any], label: str) -> Any:
    if len(rows) != 1:
        raise ValueError(f"{label}:expected-one,actual={len(rows)}")
    return rows[0]


def _sha(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise ValueError(f"{label}:missing:{path}")
    actual = sha256_file_upper(path)
    if actual != expected.upper():
        raise ValueError(f"{label}:sha256:expected={expected.upper()},actual={actual}")
    return actual


def _instructions(data: bytes) -> list[tuple[int, int, tuple[int, ...]]]:
    if len(data) < 20 or len(data) % 4:
        raise ValueError("spirv:header-or-alignment")
    words = struct.unpack(f"<{len(data) // 4}I", data)
    if words[0] != SPV_MAGIC or not 0 < words[3] < 1 << 24:
        raise ValueError("spirv:magic-or-id-bound")
    result: list[tuple[int, int, tuple[int, ...]]] = []
    cursor = 5
    while cursor < len(words):
        count, opcode = words[cursor] >> 16, words[cursor] & 0xFFFF
        if not count or cursor + count > len(words):
            raise ValueError(f"spirv:instruction-boundary:word={cursor}")
        result.append((cursor, opcode, words[cursor + 1:cursor + count]))
        cursor += count
    return result


def trace_spirv_texture_samples(data: bytes, *, descriptor_set: int,
                                binding: int, entry_model: int,
                                image_dimension: int, arrayed: int,
                                sample_opcode: int, component: int,
                                expected_count: int) -> dict[str, Any]:
    """Trace UniformConstant image -> sampled image -> sample -> component.

    Only the simple, exact SSA path visible in the selected SPIR-V is accepted.
    Other SPIR-V encodings are unresolved, not guessed through.
    """
    instructions = _instructions(data)
    entries = [args[0] for _, op, args in instructions if op == 15 and len(args) >= 3]
    if entries != [entry_model]:
        raise ValueError(f"spirv:entrypoint-model:expected={[entry_model]},actual={entries}")

    decorations: dict[int, dict[int, int]] = {}
    for _, op, args in instructions:
        if op != 71 or len(args) != 3 or args[1] not in (33, 34):
            continue
        row = decorations.setdefault(args[0], {})
        if args[1] in row:
            raise ValueError(f"spirv:duplicate-decoration:id={args[0]},decoration={args[1]}")
        row[args[1]] = args[2]
    variable_id = _one(
        [identifier for identifier, row in decorations.items()
         if row.get(34) == descriptor_set and row.get(33) == binding],
        "spirv:texture-binding",
    )
    variable = _one(
        [args for _, op, args in instructions if op == 59 and len(args) >= 3
         and args[1] == variable_id], "spirv:texture-variable",
    )
    if variable[2] != 0:
        raise ValueError("spirv:texture-storage-class")
    pointer = _one(
        [args for _, op, args in instructions if op == 32 and len(args) == 3
         and args[0] == variable[0]], "spirv:texture-pointer-type",
    )
    if pointer[1] != 0:
        raise ValueError("spirv:texture-pointer-storage-class")
    image = _one(
        [args for _, op, args in instructions if op == 25 and len(args) >= 8
         and args[0] == pointer[2]], "spirv:texture-image-type",
    )
    if (image[2], image[4]) != (image_dimension, arrayed):
        raise ValueError(
            f"spirv:texture-image-shape:expected={(image_dimension, arrayed)},"
            f"actual={(image[2], image[4])}"
        )

    image_loads = {args[1] for _, op, args in instructions
                   if op == 61 and len(args) >= 3 and args[2] == variable_id}
    sampled_images = {args[1] for _, op, args in instructions
                      if op == 86 and len(args) == 4 and args[2] in image_loads}
    samples = [(position, args[1]) for position, op, args in instructions
               if op == sample_opcode and len(args) >= 5 and args[2] in sampled_images]
    if len(samples) != expected_count or len({result for _, result in samples}) != len(samples):
        raise ValueError(f"spirv:texture-sample-count:expected={expected_count},actual={len(samples)}")
    extracts = {result: [] for _, result in samples}
    for position, op, args in instructions:
        if op == 81 and len(args) == 4 and args[2] in extracts:
            extracts[args[2]].append((position, args[3]))
    for result, rows in extracts.items():
        if len(rows) != 1 or rows[0][1] != component:
            raise ValueError(f"spirv:sample-component:result={result},expected={component},actual={rows}")
    return {
        "entryPointModel": entry_model,
        "descriptorSet": descriptor_set,
        "binding": binding,
        "variableId": variable_id,
        "imageDimension": image_dimension,
        "arrayed": arrayed,
        "sampleOpcode": sample_opcode,
        "sampleWordOffsets": [position for position, _ in samples],
        "componentIndex": component,
        "componentExtractWordOffsets": [extracts[result][0][0] for _, result in samples],
    }


def validate_shader_sampling(*, game_root: Path, evidence_root: Path,
                             contract: dict[str, Any], contract_sha: str) -> dict[str, Any]:
    asset = contract["assetInput"]
    program = contract["selectedProgram"]
    source = game_root / asset["relativeSource"]
    source_sha = _sha(source, asset["sourceSha256"], "installed-shader-source")

    manifest_path = evidence_root / "manifest.jsonl"
    if not manifest_path.is_file():
        raise ValueError(f"targeted-manifest:missing:{manifest_path}")
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line]
    output = _one([row for row in rows if row.get("kind") == "output"], "targeted-manifest:output")
    summary = _one([row for row in rows if row.get("kind") == "summary"], "targeted-manifest:summary")
    if not (summary.get("complete") is True and summary.get("exactOnly") is True
            and summary.get("outputCount") == 1 and summary.get("excludedCount") == 0):
        raise ValueError("targeted-manifest:incomplete-or-nonexact")
    if (output.get("output") != asset["output"] or output.get("type") != "Shader"
            or output.get("name") != asset["shaderName"]
            or output.get("pathId") != asset["pathId"]
            or output.get("serializedFile") != asset["cab"]
            or output.get("sourceOffset") != asset["sourceOffset"]):
        raise ValueError("targeted-manifest:shader-identity")
    _same_file(output["source"], source, "targeted-manifest")

    sidecar_root = evidence_root / "output" / (asset["output"] + ".bytecode")
    sidecar_manifest_path = sidecar_root / "manifest.json"
    if not sidecar_manifest_path.is_file():
        raise ValueError(f"shader-sidecar-manifest:missing:{sidecar_manifest_path}")
    sidecar_manifest = json.loads(sidecar_manifest_path.read_text(encoding="utf-8"))
    if sidecar_manifest.get("schema") != "animestudio.shader-subprogram.v1":
        raise ValueError("shader-sidecar-manifest:schema")
    shader = sidecar_manifest["shader"]
    if (shader.get("cab") != asset["cab"] or shader.get("pathId") != asset["pathId"]
            or shader.get("name") != asset["shaderName"]):
        raise ValueError("shader-sidecar-manifest:shader-identity")
    _same_file(shader["sourceOriginalPath"], source, "shader-sidecar-manifest")
    entry = _one([row for row in sidecar_manifest["entries"]
                  if row.get("fileName") == program["fileName"]], "shader-sidecar-manifest:program")
    if (entry.get("encoding") != "SPIR-V" or entry.get("platform") != program["platform"]
            or entry.get("passName") != program["passName"]
            or entry.get("subShaderIndex") != program["subShaderIndex"]
            or entry.get("passIndex") != program["passIndex"]
            or entry.get("programBlobIndex") != program["programBlobIndex"]
            or entry.get("sha256", "").upper() != program["sha256"]):
        raise ValueError("shader-sidecar-manifest:program-identity")
    _same_file(entry["shaderSourceOriginalPath"], source, "shader-sidecar-entry")

    spv_path = sidecar_root / program["fileName"]
    metadata_path = sidecar_root / (program["fileName"] + ".metadata.json")
    spv_sha = _sha(spv_path, program["sha256"], "selected-spirv")
    metadata_sha = _sha(metadata_path, program["metadataSha256"], "selected-shader-metadata")
    spv_bytes = spv_path.read_bytes()
    if entry.get("byteCount") != len(spv_bytes):
        raise ValueError("shader-sidecar-manifest:program-byte-count")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (metadata.get("SourceCompilerPlatform") != program["platform"]
            or metadata.get("SourcePassName") != program["passName"]
            or metadata.get("SourceSubShaderIndex") != program["subShaderIndex"]
            or metadata.get("SourcePassIndex") != program["passIndex"]
            or metadata.get("SourceProgramBlobIndex") != program["programBlobIndex"]):
        raise ValueError("shader-metadata:program-identity")
    actual_textures = [(row.get("Name"), row.get("Index"), row.get("Dim"))
                       for row in metadata["TextureParameters"]]
    expected_textures = [(row["name"], row["binding"], row["dim"])
                         for row in program["textureParameters"]]
    if (actual_textures != expected_textures or len({name for name, _, _ in actual_textures}) != len(actual_textures)
            or len({index for _, index, _ in actual_textures}) != len(actual_textures)):
        raise ValueError("shader-metadata:texture-parameters")
    selected = program["sampledTexture"]
    if _one([row for row in program["textureParameters"] if row["name"] == selected["name"]],
            "shader-contract:selected-texture")["binding"] != selected["binding"]:
        raise ValueError("shader-contract:texture-binding")
    trace = trace_spirv_texture_samples(
        spv_bytes, descriptor_set=selected["descriptorSet"], binding=selected["binding"],
        entry_model=program["entryPointModel"], image_dimension=selected["spvImageDimension"],
        arrayed=selected["spvArrayed"], sample_opcode=selected["sampleOpcode"],
        component=selected["componentIndex"], expected_count=selected["sampleCount"],
    )
    return {
        "schema": "endfield.terrain-shader-sampling-report.v1",
        "status": "validated",
        "contractSha256": contract_sha,
        "assetInput": {"source": str(source), "sourceSha256": source_sha,
                       "sourceOffset": asset["sourceOffset"], "cab": asset["cab"],
                       "pathId": asset["pathId"], "shaderName": asset["shaderName"]},
        "selectedProgram": {"passName": program["passName"], "platform": program["platform"],
                            "spirvSha256": spv_sha, "metadataSha256": metadata_sha,
                            "textureParameters": actual_textures, "trace": trace},
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True,
                        help="Selected Endfield_Data directory; installed CHK bytes are hash-gated.")
    parser.add_argument("--evidence-root", type=Path, required=True,
                        help="One-object targeted AnimeStudio Shader:Both conversion output directory.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        contract, digest = read_reviewed_contract(
            args.contract, schema=SCHEMA, label="terrain-shader-sampling", status="validated",
        )
        report = validate_shader_sampling(game_root=args.game_root, evidence_root=args.evidence_root,
                                          contract=contract, contract_sha=digest)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"terrain-shader-sampling: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".partial")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"terrain-shader-sampling: validated {report['assetInput']['shaderName']} "
          f"{report['selectedProgram']['passName']} _ConeMaps "
          f"samples={len(report['selectedProgram']['trace']['sampleWordOffsets'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
