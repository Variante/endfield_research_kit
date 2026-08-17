#!/usr/bin/env python3
"""Enumerate recovered D3D11 VFXBaseV2 shader pairs and test M23 IA fit.

The shader export contains one ``*_dxbc_0`` vertex blob and the following
``*_dxbc_1`` fragment blob for each D3D11 program.  This tool reads the DXBC
ISGN/ISG1 chunks directly, so the report does not depend on a local fxc
installation or on decompiler text.  It is intentionally a static report:
an input-signature fit is not evidence that Unity's renderer selected the
pair or that a retail descriptor table was captured.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "endfield.lizhiyan-m23-vfxbasev2-d3d11-variants.v1"
LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_ROOT = (
    REPO_ROOT
    / "scratch/character_recovery/vfx_shader_variants/shader_export/Shader"
    / "HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode"
)

M23_KEYWORDS = (
    "HG_ENABLE_MV",
    "_SAMPLE_TEX0",
    "_SAMPLE_TEX1",
    "_SAMPLE_TEX2",
    "_SAMPLE_TEX3",
    "_USE_FRESNEL",
)
EXPECTED_PAIR_COUNT = 1358
EXPECTED_FAMILY_COUNT = 14
EXPECTED_TARGETS = {
    138: (1277, 10720, 8100,
          "7d0a508f7b1e5c9aef0b89489feae97f8669a8cddaba1de0ccc0e26fd0eb2ca0",
          "0ff508aa08112122c14a3ece17d12f15778eaf39ad0c639c946512dc996b6f83"),
    4212: (1956, 11016, 8188,
           "3d25b7d2e557cd1a292851556ef5db6b03594fd82b63b05d1c18a1ae9e2d41e0",
           "23c0bef565c6f30b4d5bd094848655768408d308a179e9cd0f067b599ba310d7"),
}

# The serialized source renderer's authored six streams.  34 is the
# ParticleSystem Custom1 stream, not a D3D input semantic number.
AUTHORED_STREAMS = {
    0: {"semantic": "POSITION", "bytes": 12, "format": "R32G32B32_FLOAT"},
    1: {"semantic": "NORMAL", "bytes": 12, "format": "R32G32B32_FLOAT"},
    3: {"semantic": "COLOR", "bytes": 4, "format": "R8G8B8A8_UNORM"},
    4: {"semantic": "TEXCOORD0", "bytes": 8, "format": "R32G32_FLOAT"},
    5: {"semantic": "TEXCOORD1", "bytes": 8, "format": "R32G32_FLOAT"},
    34: {"semantic": "TEXCOORD4", "bytes": 16, "format": "R32G32B32A32_FLOAT"},
}
AUTHORED_SEMANTICS = {
    ("POSITION", 0),
    ("NORMAL", 0),
    ("COLOR", 0),
    ("TEXCOORD", 0),
    ("TEXCOORD", 1),
    ("TEXCOORD", 4),
}
SYSTEM_SEMANTICS = {
    "SV_INSTANCEID",
    "SV_VERTEXID",
    "SV_PRIMITIVEID",
}


def _chunks(data: bytes) -> Iterable[tuple[bytes, bytes]]:
    if data[:4] != b"DXBC" or len(data) < 32:
        raise ValueError("not a DXBC container")
    count = struct.unpack_from("<I", data, 28)[0]
    offsets = struct.unpack_from(f"<{count}I", data, 32)
    for offset in offsets:
        if offset + 8 > len(data):
            raise ValueError("DXBC chunk offset is outside the container")
        fourcc = data[offset : offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        end = offset + 8 + size
        if end > len(data):
            raise ValueError("DXBC chunk extends outside the container")
        yield fourcc, data[offset + 8 : end]


def _signature(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    for fourcc, chunk in _chunks(data):
        if fourcc not in (b"ISGN", b"ISG1"):
            continue
        if len(chunk) < 8:
            raise ValueError(f"short {fourcc.decode()} chunk in {path}")
        count = struct.unpack_from("<I", chunk, 0)[0]
        # ISGN records are 24 bytes. ISG1 adds stream/min-precision fields;
        # the name/index/type/register/mask fields retain these offsets.
        record_size = 24 if fourcc == b"ISGN" else 32
        first = 8
        result = []
        for index in range(count):
            offset = first + index * record_size
            if offset + 24 > len(chunk):
                raise ValueError(f"short signature record in {path}")
            name_offset, semantic_index = struct.unpack_from("<II", chunk, offset)
            component_type = struct.unpack_from("<I", chunk, offset + 12)[0]
            register = struct.unpack_from("<I", chunk, offset + 16)[0]
            mask = chunk[offset + 20]
            if name_offset >= len(chunk):
                raise ValueError(f"bad semantic name offset in {path}")
            name = chunk[name_offset:].split(b"\0", 1)[0].decode(
                "ascii", errors="replace"
            )
            result.append(
                {
                    "semantic": name,
                    "index": semantic_index,
                    "register": register,
                    "mask": mask,
                    "components": mask.bit_count(),
                    "componentType": {1: "uint", 2: "sint", 3: "float"}.get(
                        component_type, str(component_type)
                    ),
                }
            )
        return result
    raise ValueError(f"DXBC has no input-signature chunk: {path}")


def _vertex_semantics(signature: list[dict[str, Any]]) -> set[tuple[str, int]]:
    return {
        (row["semantic"].upper(), row["index"])
        for row in signature
        if row["semantic"].upper() not in SYSTEM_SEMANTICS
        and not row["semantic"].upper().startswith("SV_")
    }


def _metadata(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pair(root: Path, number: int) -> dict[str, Any]:
    vertex = root / f"{number:04d}_endfield_dxbc_0.dxbc"
    fragment = root / f"{number + 1:04d}_endfield_dxbc_1.dxbc"
    vertex_meta = root / f"{number:04d}_endfield_dxbc_0.dxbc.metadata.json"
    fragment_meta = root / f"{number + 1:04d}_endfield_dxbc_1.dxbc.metadata.json"
    if not (vertex.is_file() and fragment.is_file() and vertex_meta.is_file()):
        raise FileNotFoundError(f"incomplete D3D11 pair {number:04d}")
    metadata = _metadata(vertex_meta)
    fragment_metadata = _metadata(fragment_meta) if fragment_meta.is_file() else {}
    vertex_sig = _signature(vertex)
    fragment_sig = _signature(fragment)
    semantics = _vertex_semantics(vertex_sig)
    missing = sorted(AUTHORED_SEMANTICS ^ (AUTHORED_SEMANTICS & semantics))
    # A true fit requires every shader-fed vertex semantic to be present in
    # the authored stream.  System values (notably SV_InstanceID) are free.
    extra = sorted(semantics - AUTHORED_SEMANTICS)
    compatible = not missing and not extra
    debug = str(metadata.get("DebugName", ""))
    blob_match = re.search(r"/blob(\d+)/", debug)
    return {
        "sidecarIndex": number,
        "sourceBlobIndex": int(blob_match.group(1)) if blob_match else None,
        "vertex": {
            "file": vertex.name,
            "bytes": vertex.stat().st_size,
            "sha256": hashlib.sha256(vertex.read_bytes()).hexdigest(),
            "signature": vertex_sig,
            "debugName": debug,
        },
        "fragment": {
            "file": fragment.name,
            "bytes": fragment.stat().st_size,
            "sha256": hashlib.sha256(fragment.read_bytes()).hexdigest(),
            "signature": fragment_sig,
            "debugName": fragment_metadata.get("DebugName"),
        },
        "keywords": metadata.get("SourceCompiledKeywords") or [],
        "authoredStreamFit": {
            "compatible": compatible,
            "missing": [f"{name}{index}" for name, index in missing],
            "extra": [f"{name}{index}" for name, index in extra],
            "authoredStreamsNotConsumed": [f"{name}{index}" for name, index in missing],
            "shaderRequiredButNotAuthored": [f"{name}{index}" for name, index in extra],
            "systemValues": [
                row for row in vertex_sig if row["semantic"].upper().startswith("SV_")
            ],
        },
    }


def build_report(root: Path, target_keywords: Iterable[str] = M23_KEYWORDS) -> dict[str, Any]:
    target = tuple(target_keywords)
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for path in sorted(root.glob("*_endfield_dxbc_0.dxbc")):
        try:
            rows.append(_pair(root, int(path.name[:4])))
        except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
            failures.append(f"{path.name}: {exc}")
    if not root.is_dir():
        failures.append(f"variant root is missing: {root}")

    families: dict[tuple[Any, ...], dict[str, Any]] = {}
    family_rows: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(
            (
                item["semantic"],
                item["index"],
                item["components"],
                item["componentType"],
            )
            for item in row["vertex"]["signature"]
        )
        family_rows[key].append(row)
    for key, members in family_rows.items():
        families[key] = {
            "count": len(members),
            "sidecarIndices": [row["sidecarIndex"] for row in members],
            "vertexBytes": sorted({row["vertex"]["bytes"] for row in members}),
            "fragmentBytes": sorted({row["fragment"]["bytes"] for row in members}),
            "keywordsExamples": [row["keywords"] for row in members[:3]],
            "authoredStreamCompatibleCount": sum(
                row["authoredStreamFit"]["compatible"] for row in members
            ),
            "signature": [
                {
                    "semantic": semantic,
                    "index": index,
                    "components": components,
                    "componentType": component_type,
                }
                for semantic, index, components, component_type in key
            ],
        }
    target_set = set(target)
    target_rows = [
        row
        for row in rows
        if set(row["keywords"]) == target_set
        or (
            target_set <= set(row["keywords"])
            and set(row["keywords"]) - target_set == {"SRP_INSTANCING_ON"}
        )
    ]
    target_rows.sort(key=lambda row: row["sidecarIndex"])
    if len(rows) != EXPECTED_PAIR_COUNT:
        failures.append(
            f"D3D11 pair count drifted: expected={EXPECTED_PAIR_COUNT}, actual={len(rows)}")
    if len(families) != EXPECTED_FAMILY_COUNT:
        failures.append(
            f"signature family count drifted: expected={EXPECTED_FAMILY_COUNT}, actual={len(families)}")
    target_map = {row["sidecarIndex"]: row for row in target_rows}
    if sorted(target_map) != sorted(EXPECTED_TARGETS):
        failures.append(
            f"M23 target pair set drifted: expected={sorted(EXPECTED_TARGETS)}, actual={sorted(target_map)}")
    for sidecar, expected in EXPECTED_TARGETS.items():
        row = target_map.get(sidecar)
        if row is None:
            continue
        blob, vs_bytes, ps_bytes, vs_hash, ps_hash = expected
        actual = (row["sourceBlobIndex"], row["vertex"]["bytes"],
                  row["fragment"]["bytes"])
        if actual != (blob, vs_bytes, ps_bytes):
            failures.append(
                f"target {sidecar} blob/size drifted: expected={(blob, vs_bytes, ps_bytes)}, actual={actual}")
        if vs_hash and row["vertex"]["sha256"] != vs_hash:
            failures.append(f"target {sidecar} vertex hash drifted")
        if ps_hash and row["fragment"]["sha256"] != ps_hash:
            failures.append(f"target {sidecar} fragment hash drifted")
    compatible_count = sum(row["authoredStreamFit"]["compatible"] for row in rows)
    if compatible_count:
        failures.append(f"unexpected authored-stream-compatible VFXBaseV2 pairs: {compatible_count}")
    return {
        "schema": SCHEMA,
        "status": "pass" if not failures else "fail",
        "source": {"variantRoot": str(root), "targetKeywords": list(target)},
        "authoredParticleStreams": {
            "streams": [
                {"id": stream_id, **AUTHORED_STREAMS[stream_id]}
                for stream_id in (0, 1, 3, 4, 5, 34)
            ],
            "strideBytes": sum(item["bytes"] for item in AUTHORED_STREAMS.values()),
        },
        "summary": {
            "d3d11Pairs": len(rows),
            "signatureFamilies": len(families),
            "instancedPairs": sum("SRP_INSTANCING_ON" in row["keywords"] for row in rows),
            "authoredStreamCompatiblePairs": sum(
                row["authoredStreamFit"]["compatible"] for row in rows
            ),
            "targetPairs": len(target_rows),
            "targetCompatiblePairs": sum(
                row["authoredStreamFit"]["compatible"] for row in target_rows
            ),
            "failedPairs": len(failures),
        },
        "signatureFamilies": sorted(
            families.values(), key=lambda item: (-item["count"], item["signature"])
        ),
        "targetPairs": target_rows,
        "admission": {
            "exactM23Selection": "unique non-instanced exact keyword pair plus one SRP-instanced pair",
            "stride60Compatible": False,
            "reason": (
                "every recovered VFXBaseV2 D3D11 vertex signature requires "
                "BLENDWEIGHTS0 and BLENDINDICES0; neither is in authored streams "
                "[0,1,3,4,5,34]. The exact M23 pair additionally requires TANGENT0."
            ),
            "notVisualAdmission": True,
        },
        "failures": failures,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    report = build_report(args.variant_root)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
