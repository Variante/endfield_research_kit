#!/usr/bin/env python3
"""Audit the exact Endminf deferred pass in observer-only 3DMigoto frames."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path


VS_HASH = "7012cccc7727b990"
PS_HASH = "37eacbc3c84bb392"
FRAME_NAMES = (
    "FrameAnalysis-2026-08-24-182534",
    "FrameAnalysis-2026-08-24-182646",
    "FrameAnalysis-2026-08-24-182744",
    "FrameAnalysis-2026-08-24-182819",
    "FrameAnalysis-2026-08-24-182850",
)
TARGET_DSC_RE = re.compile(
    rf"^(?P<draw>\d{{6}})-(?P<binding>.+?)=(?P<resource>.+?)-"
    rf"vs={VS_HASH}-ps={PS_HASH}\.dsc$"
)
ANY_DSC_RE = re.compile(
    r"^(?P<draw>\d{6})-.+?-vs=(?P<vs>[0-9a-f]{16})-"
    r"ps=(?P<ps>[0-9a-f]{16})\.dsc$"
)
RESOURCE_RE = re.compile(
    r"^\s+(?P<slot>\d+): .* hash=(?P<hash>[0-9a-f]+)(?:\s|$)"
)


def fnv1_64(data: bytes) -> str:
    """Return 3DMigoto's unseeded 64-bit FNV-1 resource hash."""
    value = 0
    for byte in data:
        value = ((value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF) ^ byte
    return f"{value:016x}"


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
    if len(draws) != 1:
        failures.append(
            f"capture={frame_dir.name}; check=exact_draw_count; expected=1; actual={len(draws)}"
        )
        return {"frame": frame_dir.name, "exactDraws": draws}, failures

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
    }, failures


def build_report(
    frame_dirs: list[Path], vs_blob: Path, ps_blob: Path, shader_source: Path
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
        "evidenceBoundary": {
            "proves": [
                "the exact deferred pass-0 VS/PS pair was submitted once in each captured Endminf overview frame",
                "the production draw is a fullscreen three-vertex DrawInstanced call",
                "the draw binds ten pixel constant-buffer views and t0 through t27",
                "output/depth and dumpable texture descriptors identify retail dimensions and formats",
            ],
            "doesNotProve": [
                "pFirstConstant offsets or the active ranges within the shared 4 MiB dynamic constant-buffer ring",
                "binary content for skipped Texture3D slots t15 and t18 through t23",
                "b2 skin-palette active ranges or BeyondBoneCloth deformation state",
                "that the current Unity exact consumer should be presented as final screen color",
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
        default=repo_root / "reports/assets/character_recovery/"
        "endminf_deferred_pass0_frame_analysis.json",
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
    args = parser.parse_args()

    frame_dirs = [args.capture_root / name for name in FRAME_NAMES]
    missing = [path for path in frame_dirs if not path.is_dir()]
    if missing:
        for path in missing:
            print(f"missing capture: {path}")
        return 1
    report = build_report(frame_dirs, args.vs_blob, args.ps_blob, args.shader_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['status']}: {args.output}")
    for failure in report["failures"]:
        print(f"failure: {failure}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
