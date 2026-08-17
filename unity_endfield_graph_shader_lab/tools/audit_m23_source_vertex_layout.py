#!/usr/bin/env python3
"""Audit the source M23 mesh/particle streams against the exact 0138 IA ABI.

This audit deliberately separates three things that are easy to conflate:
the text OBJ payload, the authored ParticleSystemRenderer stream tuple, and
the exact shader input declaration.  A pass proves the first two produce the
captured 60-byte stock stream and therefore cannot be cited as the missing
136-byte fork/HG producer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "endfield.lizhiyan-m23-source-vertex-layout-audit.v1"
LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_MESH_ROOT = (
    REPO_ROOT / "scratch/animestudio/lizhiyan_peak_particles/dependency_convert/Mesh"
)
DEFAULT_RENDERER_ROOT = (
    REPO_ROOT / "scratch/animestudio/lizhiyan_peak_particles/prefab_json/ParticleSystemRenderer"
)

EXPECTED_MESHES = {
    "S_fx_lzy_xishou_01_p502A61E6E0572203.obj": (388, 388, 388, 576),
    "S_fx_lzy_xishou_01_p0DB4A464F521C6ED.obj": (768, 768, 768, 576),
    "S_fx_lzy_yuanzhu_01_p5B10FDB82FE687DA.obj": (268, 268, 268, 396),
}
EXPECTED_RENDERERS = {
    -9496592748243424: 987594971817297645,
    37981486576571936: 5776537116290261507,
    5944045158489396768: 987594971817297645,
    6551385765768926752: 5776537116290261507,
}
EXPECTED_STREAMS = [0, 1, 3, 4, 5, 34]
STREAMS = {
    0: ("Position", 12),
    1: ("Normal", 12),
    3: ("Color32", 4),
    4: ("UV", 8),
    5: ("UV2", 8),
    34: ("Custom1XYZW", 16),
}
EXACT_FIELDS = [
    ("POSITION", 12), ("NORMAL", 12), ("TANGENT", 16),
    ("COLOR0", 16), ("TEXCOORD0", 16), ("TEXCOORD1", 16),
    ("TEXCOORD4", 16), ("BLENDWEIGHTS", 16), ("BLENDINDICES", 16),
]


def _obj_counts(path: Path) -> dict[str, Any]:
    counts = {"v": 0, "vt": 0, "vn": 0, "f": 0, "g": 0}
    other_tags: set[str] = set()
    with path.open("r", encoding="utf-8-sig", errors="strict") as source:
        for line in source:
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            tag = stripped.split(None, 1)[0]
            if tag in counts:
                counts[tag] += 1
            else:
                other_tags.add(tag)
    return {"path": str(path), "counts": counts, "otherTags": sorted(other_tags)}


def _renderer(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    meta = data.get("$animestudio") or {}
    return {
        "path": str(path),
        "pathId": meta.get("pathId"),
        "streams": data.get("m_VertexStreams"),
        "useCustomVertexStreams": data.get("m_UseCustomVertexStreams"),
        "enableGPUInstancing": data.get("m_EnableGPUInstancing"),
        "enableHGGPUInstancing": data.get("m_EnableHGGPUInstancing"),
        "meshPathId": (data.get("m_Mesh") or {}).get("m_PathID"),
        "renderMode": data.get("m_RenderMode"),
    }


def build_report(mesh_root: Path, renderer_root: Path) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []

    def check(check_id: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            failures.append({"id": check_id, "expected": expected, "actual": actual})

    meshes = []
    for name, expected in EXPECTED_MESHES.items():
        path = mesh_root / name
        if not path.is_file():
            failures.append({"id": f"mesh.{name}.present", "expected": True, "actual": False})
            continue
        row = _obj_counts(path)
        meshes.append(row)
        actual = row["counts"]
        check(f"mesh.{name}.v_vt_vn_f",
              [actual["v"], actual["vt"], actual["vn"], actual["f"]], list(expected))
        check(f"mesh.{name}.otherTags", row["otherTags"], [])

    renderers = []
    for path in sorted(renderer_root.glob("*.json")):
        row = _renderer(path)
        if row["pathId"] not in EXPECTED_RENDERERS:
            continue
        renderers.append(row)
        rid = row["pathId"]
        check(f"renderer.{rid}.streams", row["streams"], EXPECTED_STREAMS)
        check(f"renderer.{rid}.customStreams", row["useCustomVertexStreams"], True)
        check(f"renderer.{rid}.renderMode", row["renderMode"], 4)
        check(f"renderer.{rid}.mesh", row["meshPathId"], EXPECTED_RENDERERS[rid])
        check(f"renderer.{rid}.hgInstancing", row["enableHGGPUInstancing"], False)
    check("renderer.identities", sorted(row["pathId"] for row in renderers),
          sorted(EXPECTED_RENDERERS))

    authored_stride = sum(STREAMS[value][1] for value in EXPECTED_STREAMS)
    exact_stride = sum(width for _, width in EXACT_FIELDS)
    check("stride.authored", authored_stride, 60)
    check("stride.exact", exact_stride, 136)
    check("stride.layoutsDiffer", authored_stride != exact_stride, True)

    return {
        "schema": SCHEMA,
        "status": "pass" if not failures else "fail",
        "inputs": {"meshRoot": str(mesh_root), "rendererRoot": str(renderer_root)},
        "meshes": meshes,
        "renderers": renderers,
        "authoredParticleLayout": {
            "streams": [{"id": value, "semantic": STREAMS[value][0],
                         "bytes": STREAMS[value][1]} for value in EXPECTED_STREAMS],
            "strideBytes": authored_stride,
        },
        "exact0138Layout": {
            "fields": [{"semantic": name, "bytes": width} for name, width in EXACT_FIELDS],
            "strideBytes": exact_stride,
        },
        "admission": {
            "sourceMeshIs136ByteProducer": False,
            "authoredParticleStreamIs136ByteProducer": False,
            "forkHgProducerResolved": False,
            "claim": "source OBJ and authored stock particle stream are excluded as the exact 136-byte producer",
        },
        "summary": {"failed": len(failures),
                    "firstFailure": failures[0]["id"] if failures else None},
        "failures": failures,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-root", type=Path, default=DEFAULT_MESH_ROOT)
    parser.add_argument("--renderer-root", type=Path, default=DEFAULT_RENDERER_ROOT)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    report = build_report(args.mesh_root, args.renderer_root)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
