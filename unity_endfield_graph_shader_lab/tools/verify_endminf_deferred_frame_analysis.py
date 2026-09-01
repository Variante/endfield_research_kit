#!/usr/bin/env python3
"""Audit the exact Endminf deferred pass in observer-only 3DMigoto frames."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
from pathlib import Path


VS_HASH = "7012cccc7727b990"
PS_HASH = "37eacbc3c84bb392"
LITEFFECT_VS_HASH = "40426f24c41b60b9"
LITEFFECT_PS_HASH = "ff0499fede675ad7"
LITEFFECT_EXPECTED_DRAWS = {
    "FrameAnalysis-2026-08-24-182534": [],
    "FrameAnalysis-2026-08-24-182646": [47, 48, 49, 50, 51, 52],
    "FrameAnalysis-2026-08-24-182744": [51, 52, 53, 54, 55, 56],
    "FrameAnalysis-2026-08-24-182819": [52, 53, 54, 55, 56, 57],
    "FrameAnalysis-2026-08-24-182850": [52],
}
LITEFFECT_EXPECTED_INDEX_COUNTS = {
    "FrameAnalysis-2026-08-24-182534": [],
    "FrameAnalysis-2026-08-24-182646": [72, 72, 72, 360, 360, 360],
    "FrameAnalysis-2026-08-24-182744": [72, 72, 72, 288, 288, 288],
    "FrameAnalysis-2026-08-24-182819": [72, 72, 72, 72, 144, 72],
    "FrameAnalysis-2026-08-24-182850": [1080],
}
LITEFFECT_TEXTURE_HASHES = {
    # Physical names come from serialized PackedBinding's fragment-register
    # byte, not descriptor-list order. The resource hashes remain attached to
    # their observed physical slots.
    "t0": ("_BaseColorMap", "4e770fc3"),
    "t1": ("_NormalMap", "30ff729f"),
    "t2": ("_MROMap", "0091dfae"),
    "t3": ("_ParallaxMap", "7fe21e44"),
    "t4": ("_ParallaxMaskMap", "bb5905b2"),
    "t5": ("_ParallaxNoiseMap", "bb5905b2"),
}
FRAME_NAMES = (
    "FrameAnalysis-2026-08-24-182534",
    "FrameAnalysis-2026-08-24-182646",
    "FrameAnalysis-2026-08-24-182744",
    "FrameAnalysis-2026-08-24-182819",
    "FrameAnalysis-2026-08-24-182850",
)
DEFAULT_REPORT = (
    Path(__file__).resolve().parents[2]
    / "reports/assets/character_recovery/endminf_deferred_pass0_frame_analysis.json"
)
TARGET_DSC_RE = re.compile(
    rf"^(?P<draw>\d{{6}})-(?P<binding>.+?)=(?P<resource>.+?)-"
    rf"vs={VS_HASH}-ps={PS_HASH}\.dsc$"
)
ANY_DSC_RE = re.compile(
    r"^(?P<draw>\d{6})-.+?-vs=(?P<vs>[0-9a-f]{16})-"
    r"ps=(?P<ps>[0-9a-f]{16})\.dsc$"
)
LITEFFECT_DSC_RE = re.compile(
    rf"^(?P<draw>\d{{6}})-.+-vs={LITEFFECT_VS_HASH}-ps={LITEFFECT_PS_HASH}\.dsc$"
)
LITEFFECT_TEXTURE_DSC_RE = re.compile(
    rf"^(?P<draw>\d{{6}})-ps-(?P<slot>t[0-5])=(?P<resource>[0-9a-f]+)-"
    rf"vs={LITEFFECT_VS_HASH}-ps={LITEFFECT_PS_HASH}\.dsc$"
)
RESOURCE_RE = re.compile(
    r"^\s+(?P<slot>\d+): .* hash=(?P<hash>[0-9a-f]+)(?:\s|$)"
)
DRAW_INDEXED_INSTANCED_RE = re.compile(
    r"^(?P<draw>\d{6}) DrawIndexedInstanced\("
    r"IndexCountPerInstance:(?P<index_count>\d+), InstanceCount:(?P<instance_count>\d+), "
    r"StartIndexLocation:(?P<start_index>\d+), BaseVertexLocation:(?P<base_vertex>-?\d+), "
    r"StartInstanceLocation:(?P<start_instance>\d+)\)$"
)


def fnv1_64(data: bytes) -> str:
    """Return 3DMigoto's unseeded 64-bit FNV-1 resource hash."""
    value = 0
    for byte in data:
        value = ((value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF) ^ byte
    return f"{value:016x}"


def encoded_report(report: dict) -> bytes:
    return (json.dumps(report, indent=2) + "\n").encode("utf-8")


def published_report_is_current(report: dict, output: Path) -> bool:
    if not output.is_file():
        return False
    return output.read_bytes().replace(b"\r\n", b"\n") == encoded_report(report)


def parse_descriptor(text: str) -> dict[str, object]:
    values: dict[str, object] = {}
    for token in shlex.split(text.strip()):
        key, separator, value = token.partition("=")
        if not separator:
            continue
        if value.isdecimal():
            values[key] = int(value)
        else:
            values[key] = value
    return values


def _draw_resource_hashes(log_lines: list[str], draw: str) -> dict[str, str]:
    marker = f"{draw} PSSetShaderResources(StartSlot:0, NumViews:28"
    for index, line in enumerate(log_lines):
        if marker not in line:
            continue
        resources: dict[str, str] = {}
        for following in log_lines[index + 1 : index + 30]:
            match = RESOURCE_RE.match(following)
            if match is None:
                break
            resources[f"t{int(match['slot'])}"] = match["hash"]
        return resources
    return {}


def audit_capture(frame_dir: Path) -> tuple[dict[str, object], list[str]]:
    failures: list[str] = []
    target_files: list[tuple[Path, re.Match[str]]] = []
    target_text_files: list[Path] = []
    neighboring_pairs: dict[int, tuple[str, str]] = {}
    liteffect_draws: set[int] = set()
    liteffect_textures: dict[int, dict[str, str]] = {}
    for path in frame_dir.iterdir():
        if not path.is_file():
            continue
        if (
            path.suffix.lower() == ".txt"
            and f"-vs={VS_HASH}-ps={PS_HASH}.txt" in path.name
        ):
            target_text_files.append(path)
        if path.suffix.lower() != ".dsc":
            continue
        liteffect_match = LITEFFECT_DSC_RE.match(path.name)
        if liteffect_match is not None:
            liteffect_draws.add(int(liteffect_match["draw"]))
        texture_match = LITEFFECT_TEXTURE_DSC_RE.match(path.name)
        if texture_match is not None:
            liteffect_textures.setdefault(int(texture_match["draw"]), {})[
                texture_match["slot"]
            ] = texture_match["resource"]
        match = TARGET_DSC_RE.match(path.name)
        if match is not None:
            target_files.append((path, match))
        any_match = ANY_DSC_RE.match(path.name)
        if any_match is not None:
            neighboring_pairs[int(any_match["draw"])] = (
                any_match["vs"],
                any_match["ps"],
            )

    draws = sorted({match["draw"] for _, match in target_files})
    expected_liteffect_draws = LITEFFECT_EXPECTED_DRAWS.get(frame_dir.name)
    if expected_liteffect_draws is not None and sorted(liteffect_draws) != expected_liteffect_draws:
        failures.append(
            f"capture={frame_dir.name}; check=liteffect_instanced_parallax_draws; "
            f"expected={expected_liteffect_draws}; actual={sorted(liteffect_draws)}"
        )
    expected_texture_hashes = {
        slot: row[1] for slot, row in LITEFFECT_TEXTURE_HASHES.items()
    }
    for liteffect_draw in sorted(liteffect_draws):
        actual_textures = liteffect_textures.get(liteffect_draw, {})
        if actual_textures != expected_texture_hashes:
            failures.append(
                f"capture={frame_dir.name}; draw={liteffect_draw:06d}; "
                f"check=liteffect_texture_resources; expected={expected_texture_hashes}; "
                f"actual={actual_textures}"
            )
    if len(draws) != 1:
        failures.append(
            f"capture={frame_dir.name}; check=exact_draw_count; expected=1; actual={len(draws)}"
        )
        return {
            "frame": frame_dir.name,
            "exactDraws": draws,
            "litEffectInstancedParallaxDraws": sorted(liteffect_draws),
        }, failures

    draw = draws[0]
    bindings: dict[str, dict[str, object]] = {}
    for path, match in target_files:
        binding = match["binding"]
        bindings[binding] = {
            "resourceHash": match["resource"],
            "descriptor": parse_descriptor(path.read_text(encoding="utf-8")),
        }

    expected_descriptor_bindings = {
        "o0", "oD", *(f"ps-cb{i}" for i in range(10)),
        "ps-t0", "ps-t1", "ps-t2", "ps-t3", "ps-t4", "ps-t5",
        "ps-t6", "ps-t7", "ps-t8", "ps-t9", "ps-t10", "ps-t11",
        "ps-t12", "ps-t13", "ps-t14", "ps-t16", "ps-t17", "ps-t24",
        "ps-t25", "ps-t26", "ps-t27", "ib",
    }
    missing = sorted(expected_descriptor_bindings - bindings.keys())
    if missing:
        failures.append(
            f"capture={frame_dir.name}; check=descriptor_bindings; missing={','.join(missing)}"
        )

    log_path = frame_dir / "log.txt"
    log_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    liteffect_draw_calls = []
    for liteffect_draw in sorted(liteffect_draws):
        prefix = f"{liteffect_draw:06d} DrawIndexedInstanced("
        draw_line = next((line.strip() for line in log_lines if line.startswith(prefix)), None)
        match = DRAW_INDEXED_INSTANCED_RE.match(draw_line or "")
        if match is None:
            failures.append(
                f"capture={frame_dir.name}; draw={liteffect_draw:06d}; "
                f"check=liteffect_draw_call; actual={draw_line!r}"
            )
            continue
        row = {key: int(value) for key, value in match.groupdict().items()}
        liteffect_draw_calls.append(row)
        if row["instance_count"] != 1 or row["start_instance"] != 0:
            failures.append(
                f"capture={frame_dir.name}; draw={liteffect_draw:06d}; "
                "check=liteffect_single_instance_record0; "
                f"instance_count={row['instance_count']}; "
                f"start_instance={row['start_instance']}"
            )
        if row["index_count"] % 72 != 0:
            failures.append(
                f"capture={frame_dir.name}; draw={liteffect_draw:06d}; "
                f"check=liteffect_72_index_mesh_multiple; actual={row['index_count']}"
            )
    actual_index_counts = [row["index_count"] for row in liteffect_draw_calls]
    expected_index_counts = LITEFFECT_EXPECTED_INDEX_COUNTS.get(frame_dir.name)
    if expected_index_counts is not None and actual_index_counts != expected_index_counts:
        failures.append(
            f"capture={frame_dir.name}; check=liteffect_index_counts; "
            f"expected={expected_index_counts}; actual={actual_index_counts}"
        )
    resources = _draw_resource_hashes(log_lines, draw)
    if set(resources) != {f"t{i}" for i in range(28)}:
        failures.append(
            f"capture={frame_dir.name}; check=log_resource_slots; expected=t0..t27; "
            f"actual={','.join(sorted(resources))}"
        )
    draw_call = next(
        (line.strip() for line in log_lines if line.startswith(f"{draw} Draw")),
        None,
    )
    expected_call = (
        f"{draw} DrawInstanced(VertexCountPerInstance:3, InstanceCount:1, "
        "StartVertexLocation:0, StartInstanceLocation:0)"
    )
    if draw_call != expected_call:
        failures.append(
            f"capture={frame_dir.name}; check=draw_call; expected={expected_call!r}; actual={draw_call!r}"
        )

    constant_buffer_dumps = []
    for slot in range(10):
        prefix = f"{draw}-ps-cb{slot}="
        candidates = [
            path for path in target_text_files if path.name.startswith(prefix)
        ]
        if len(candidates) != 1:
            failures.append(
                f"capture={frame_dir.name}; check=cb{slot}_dump_count; expected=1; actual={len(candidates)}"
            )
            continue
        path = candidates[0]
        constant_buffer_dumps.append({
            "slot": slot,
            "resourceHash": bindings[f"ps-cb{slot}"]["resourceHash"],
            "bytes": path.stat().st_size,
            "scope": "whole 4 MiB dynamic ring buffer; duplicated slot filename does not recover pFirstConstant",
        })

    target_index = int(draw)
    neighbors = [
        {"draw": index, "vs": pair[0], "ps": pair[1]}
        for index, pair in sorted(neighboring_pairs.items())
        if target_index - 3 <= index <= target_index + 3
    ]
    return {
        "frame": frame_dir.name,
        "draw": target_index,
        "drawCall": draw_call,
        "descriptorCount": len(target_files),
        "output": bindings.get("o0"),
        "depth": bindings.get("oD"),
        "resourceHashes": resources,
        "descriptorBackedTextureSlots": sorted(
            key for key in bindings if key.startswith("ps-t")
        ),
        "descriptorUnavailableTextureSlots": [
            "t15", "t18", "t19", "t20", "t21", "t22", "t23"
        ],
        "constantBufferDumps": constant_buffer_dumps,
        "neighborShaderSequence": neighbors,
        "litEffectInstancedParallaxDraws": sorted(liteffect_draws),
        "litEffectDrawCalls": liteffect_draw_calls,
        "litEffectExpandedMeshCopies": sum(
            row["index_count"] // 72 for row in liteffect_draw_calls
        ),
    }, failures


def build_report(
    frame_dirs: list[Path], vs_blob: Path, ps_blob: Path, shader_source: Path,
    liteffect_vs_blob: Path, liteffect_ps_blob: Path,
) -> dict[str, object]:
    failures: list[str] = []
    blobs = []
    for stage, path, expected in (
        ("vs", vs_blob, VS_HASH),
        ("ps", ps_blob, PS_HASH),
    ):
        data = path.read_bytes()
        actual = fnv1_64(data)
        blobs.append({
            "stage": stage,
            "path": path.as_posix(),
            "bytes": len(data),
            "expectedUnseededFnv1": expected,
            "actualUnseededFnv1": actual,
        })
        if actual != expected:
            failures.append(
                f"shader={stage}; check=unseeded_fnv1; expected={expected}; actual={actual}"
            )

    source = shader_source.read_text(encoding="utf-8", errors="replace")
    source_markers = (
        PS_HASH,
        "HG_ENABLE_SCREEN_SPACE_SHADOW_MASK",
        "HG_USE_SUBPASS_INPUT_UNDER_ONE_PASS_DEFERRED",
        "_SUBSURFACE_PROFILE_SIMPLE",
    )
    missing_markers = [marker for marker in source_markers if marker not in source]
    if missing_markers:
        failures.append(
            f"shader_source={shader_source}; check=variant_markers; missing={','.join(missing_markers)}"
        )

    captures = []
    for frame_dir in frame_dirs:
        capture, capture_failures = audit_capture(frame_dir)
        captures.append(capture)
        failures.extend(capture_failures)

    liteffect_blobs = []
    for stage, path, expected_hash, expected_sha256 in (
        ("vertex", liteffect_vs_blob, LITEFFECT_VS_HASH,
         "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c"),
        ("fragment", liteffect_ps_blob, LITEFFECT_PS_HASH,
         "92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e"),
    ):
        data = path.read_bytes()
        actual_hash = fnv1_64(data)
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if actual_hash != expected_hash or actual_sha256 != expected_sha256:
            failures.append(
                f"liteffect={stage}; check=blob_identity; expected_hash={expected_hash}; "
                f"actual_hash={actual_hash}; expected_sha256={expected_sha256}; "
                f"actual_sha256={actual_sha256}"
            )
        metadata = json.loads(path.with_name(path.name + ".metadata.json").read_text(encoding="utf-8"))
        expected_keywords = ["HG_ENABLE_MV", "SRP_INSTANCING_ON", "_PARALLAX_MAP"]
        if (metadata.get("SourcePassName") != "HGBuffer" or
                metadata.get("SourceSubProgramIndex") != 113 or
                metadata.get("DecodedProgramStage") != stage or
                metadata.get("SourceCompiledKeywords") != expected_keywords):
            failures.append(
                f"liteffect={stage}; check=metadata_variant_identity; "
                f"pass={metadata.get('SourcePassName')}; "
                f"subprogram={metadata.get('SourceSubProgramIndex')}; "
                f"decoded_stage={metadata.get('DecodedProgramStage')}; "
                f"keywords={metadata.get('SourceCompiledKeywords')}"
            )
        liteffect_blobs.append({
            "stage": stage,
            "path": path.as_posix(),
            "bytes": len(data),
            "sha256": actual_sha256,
            "unseededFnv1": actual_hash,
        })

    return {
        "status": "ok" if not failures else "failed",
        "contract": "endminf_ui_overview_exact_deferred_pass0_frame_analysis_v1",
        "observerOnly": True,
        "shaderIdentity": {
            "algorithm": "3DMigoto shader_hash=3dmigoto unseeded FNV-1 64-bit",
            "blobs": blobs,
            "source": shader_source.as_posix(),
            "requiredVariantMarkers": list(source_markers),
        },
        "captures": captures,
        "litEffectInstancedParallax": {
            "shader": "HGRP/LitEffect",
            "pass": "HGBuffer",
            "subProgramIndex": 113,
            "keywords": ["HG_ENABLE_MV", "SRP_INSTANCING_ON", "_PARALLAX_MAP"],
            "blobs": liteffect_blobs,
            "captureDrawCounts": {
                row["frame"]: len(row["litEffectInstancedParallaxDraws"])
                for row in captures
            },
            "textureResources": {
                slot: {"logicalName": row[0], "resourceHash": row[1]}
                for slot, row in LITEFFECT_TEXTURE_HASHES.items()
            },
            "drawTopology": {
                "allSelectedDraws": "DrawIndexedInstanced",
                "instanceCount": 1,
                "startInstanceLocation": 0,
                "sourceRockIndexCount": 72,
                "expandedMeshCopiesByCapture": {
                    row["frame"]: row.get("litEffectExpandedMeshCopies", 0)
                    for row in captures
                },
            },
            "interpretation": (
                "The active small rock/crystal geometry uses the SRP-instanced "
                "parallax variant, not representative non-instanced subprogram 19. "
                "Every selected retail draw still submits exactly one D3D instance "
                "at instance record 0; index counts are exact multiples of the "
                "72-index source rock, proving engine-expanded particle geometry "
                "rather than a UnityStandardParticleInstancing transform stream."
            ),
        },
        "evidenceBoundary": {
            "proves": [
                "the exact deferred pass-0 VS/PS pair was submitted once in each captured Endminf overview frame",
                "the production draw is a fullscreen three-vertex DrawInstanced call",
                "the draw binds ten pixel constant-buffer views and t0 through t27",
                "output/depth and dumpable texture descriptors identify retail dimensions and formats",
                "the captured rock/crystal draw family resolves byte-exactly to HGRP/LitEffect HGBuffer subprogram 113 with SRP_INSTANCING_ON and _PARALLAX_MAP",
                "all captured subprogram-113 draws use InstanceCount 1, StartInstanceLocation 0, and exact multiples of the 72-index source rock",
            ],
            "doesNotProve": [
                "pFirstConstant offsets or the active ranges within the shared 4 MiB dynamic constant-buffer ring",
                "binary content for skipped Texture3D slots t15 and t18 through t23",
                "b2 skin-palette active ranges or BeyondBoneCloth deformation state",
                "that the current Unity exact consumer should be presented as final screen color",
                "the unresolved active constant-buffer ranges or the numeric parallax/deferred equations of LitEffect subprogram 113",
            ],
        },
        "failures": failures,
    }


def main() -> int:
    lab_root = Path(__file__).resolve().parents[1]
    repo_root = lab_root.parent
    shader_root = (
        repo_root / "scratch/reverse_engineering/gacha_deferred_resolver_chain/"
        "deferred_lighting_export"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--capture-root",
        type=Path,
        default=repo_root / "scratch/character_recovery/3dmigoto-dev-v1.0.0/package",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the published report differs from current evidence",
    )
    parser.add_argument(
        "--vs-blob", type=Path,
        default=shader_root / "Shader/HGRP_DeferredLighting_p5F10B115E8D3AFDE."
        "shader.bytecode/0096_endfield_dxbc_0.dxbc",
    )
    parser.add_argument(
        "--ps-blob", type=Path,
        default=shader_root / "Shader/HGRP_DeferredLighting_p5F10B115E8D3AFDE."
        "shader.bytecode/0103_endfield_dxbc_1.dxbc",
    )
    parser.add_argument(
        "--shader-source", type=Path,
        default=shader_root / "Shader/HGRP_DeferredLighting_p5F10B115E8D3AFDE.shader",
    )
    liteffect_root = (
        repo_root / "scratch/animestudio/endminf_liteffect_shader/sidecars/Shader/"
        "HGRP_LitEffect_p5936F49FA93F14DD.shader.bytecode"
    )
    parser.add_argument(
        "--liteffect-vs-blob", type=Path,
        default=liteffect_root / "0678_endfield_dxbc_0.dxbc",
    )
    parser.add_argument(
        "--liteffect-ps-blob", type=Path,
        default=liteffect_root / "0679_endfield_dxbc_1.dxbc",
    )
    args = parser.parse_args()

    frame_dirs = [args.capture_root / name for name in FRAME_NAMES]
    missing = [path for path in frame_dirs if not path.is_dir()]
    if missing:
        for path in missing:
            print(f"missing capture: {path}")
        return 1
    report = build_report(
        frame_dirs, args.vs_blob, args.ps_blob, args.shader_source,
        args.liteffect_vs_blob, args.liteffect_ps_blob,
    )
    if args.check:
        if not published_report_is_current(report, args.output):
            print(f"stale generated report: {args.output}")
            return 1
        print(f"{report['status']} and current: {args.output}")
        return 0 if report["status"] == "ok" else 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded_report(report))
    print(f"{report['status']}: {args.output}")
    for failure in report["failures"]:
        print(f"failure: {failure}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
