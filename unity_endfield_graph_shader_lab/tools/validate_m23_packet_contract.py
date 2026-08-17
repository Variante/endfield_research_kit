#!/usr/bin/env python3
"""Validate the managed M23 packet census joined to the source oracle.

This is an evidence join, not a packet builder.  It accepts the three reports
produced by the Unity source-mesh oracle, the managed public-input census, and
the native exact-DXBC fixture.  A passing result means that the public rows
and source-mesh expansion refer to the same four particles and that the exact
shader fixture executed.  It deliberately requires every packed-row, draw-time
cb3, and visual-admission flag to remain false.

The reports contain bounded diagnostics rather than relying on an assertion
that stops at the first mismatch.  Checks are emitted in a stable order so a
changed source or stale report is actionable in CI and in a human review.
Only Python's standard library is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = "endfield.lizhiyan-m23-packet-contract-validator.v1"
CENSUS_SCHEMA = "endfield.lizhiyan-m23-managed-particle-packet-census.v1"
ORACLE_SCHEMA = "endfield.lizhiyan-m23-source-mesh-oracle.v1"
EXACT_SCHEMA = "endfield.original-m23-dxbc-exact.v3"

LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENSUS = LAB_ROOT / "scratch/character_recovery/lizhiyan_m23_packet_census/pts_40000.json"
DEFAULT_ORACLE = LAB_ROOT / "scratch/character_recovery/lizhiyan_m23_source_mesh_oracle/pts_40000.json"
DEFAULT_EXACT = LAB_ROOT / "tools/original_m23_dxbc_exact/build/m23_dxbc_validation.json"

EXPECTED_EFFECT_ROOT = "P_fxui_lizhiyan_overview_start_04_2"
EXPECTED_PREFAB = (
    "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/"
    "Effects/OverviewPeakParticles/"
    "P_fxui_lizhiyan_overview_start_04_2.prefab"
)
EXPECTED_PTS = 40000
EXPECTED_CLOCK_ORIGIN_PTS = 37967
EXPECTED_STREAM_IDS = [0, 1, 3, 4, 5, 34]
EXPECTED_RENDERERS = [
    {
        "hierarchy": EXPECTED_EFFECT_ROOT + "/xuanzhuan03",
        "particleSystemPathId": 2171212438583907872,
        "particleRendererPathId": 37981486576571936,
        "meshPathId": 5776537116290261507,
        "particleCount": 2,
        "sourceVertexCount": 388,
        "sourceIndexCount": 1728,
    },
    {
        "hierarchy": EXPECTED_EFFECT_ROOT + "/xuanzhuan03_02",
        "particleSystemPathId": 8324091109314139680,
        "particleRendererPathId": 5944045158489396768,
        "meshPathId": 987594971817297645,
        "particleCount": 2,
        "sourceVertexCount": 768,
        "sourceIndexCount": 1728,
    },
    {
        "hierarchy": EXPECTED_EFFECT_ROOT + "/xuanzhuan04",
        "particleSystemPathId": 8348750931752523296,
        "particleRendererPathId": 6551385765768926752,
        "meshPathId": 5776537116290261507,
        "particleCount": 0,
        "sourceVertexCount": 388,
        "sourceIndexCount": 1728,
    },
    {
        "hierarchy": EXPECTED_EFFECT_ROOT + "/xuanzhuan04_02",
        "particleSystemPathId": 4395430579353425440,
        "particleRendererPathId": -9496592748243424,
        "meshPathId": 987594971817297645,
        "particleCount": 0,
        "sourceVertexCount": 768,
        "sourceIndexCount": 1728,
    },
]
EXPECTED_PARTICLE_SEEDS = [3750955593, 3624193669]
EXPECTED_PUBLIC_ALPHAS = [51, 71]

# The oracle intentionally records compact SHA-256 digests instead of all
# BakeMesh COLOR0 bytes.  These hashes are the pinned source evidence for the
# two active renderer/material variants.  Their decoded alpha lanes are the
# proven [51, 70] sequence; the public Particle.GetCurrentColor sequence is
# [51, 71] and must not be copied into a packed row.
EXPECTED_BAKED_COLOR_SEGMENT_SHA256 = {
    EXPECTED_RENDERERS[0]["hierarchy"]: [
        "6E399B15EE55B578CA10687084E5702AB462AF875DCA7B15878E87B0900E6F29",
        "132B90A24362FC04094E297D80C5CFB9099B1A673C0EDD039A7ED02FED94C6A3",
    ],
    EXPECTED_RENDERERS[1]["hierarchy"]: [
        "E8A81CC6739C7949E5AF7776920CCEDE990C0C2D3FF1761B50A47E065BA3D81C",
        "8FBBC3244E36E2F79334D98239044C1A7CFF0B3B765C86CE791C574299D5E8FA",
    ],
}
EXPECTED_BAKED_COLOR_MESH_SHA256 = {
    EXPECTED_RENDERERS[0]["hierarchy"]:
        "D2CD0431F4C41C7FC9F48B384788204936DCA80C87E31B39A664AEBC15A069A8",
    EXPECTED_RENDERERS[1]["hierarchy"]:
        "5F836FB1C4A656FB690D8B2350D918A1489A7FD2E1D3FE8F7568B2EEEDEEAE15",
}

EXPECTED_PACKET_FIELDS = {
    "POSITION": (0, 3),
    "NORMAL": (12, 3),
    "TANGENT": (24, 4),
    "COLOR0": (40, 4),
    "TEXCOORD0": (56, 4),
    "TEXCOORD1": (72, 4),
    "TEXCOORD4": (88, 4),
    "BLENDWEIGHTS": (104, 4),
    "BLENDINDICES": (120, 4),
}


def _decode_repeated_white_alpha(digest: str, count: int) -> int | None:
    """Recover the constant alpha byte from an oracle HashColor32 segment."""

    if not isinstance(digest, str) or count < 0:
        return None
    target = digest.upper()
    prefix = struct.pack("<i", count)
    for alpha in range(256):
        payload = prefix + bytes((255, 255, 255, alpha)) * count
        if hashlib.sha256(payload).hexdigest().upper() == target:
            return alpha
    return None

EXPECTED_EXACT_FIELDS = {
    "vertex_sha256": "7d0a508f7b1e5c9aef0b89489feae97f8669a8cddaba1de0ccc0e26fd0eb2ca0",
    "pixel_sha256": "0ff508aa08112122c14a3ece17d12f15778eaf39ad0c639c946512dc996b6f83",
    "input_layout_creation_mask": "0x1",
    "vertex_buffer_creation_mask": "0x1",
    "vs_constant_buffer_creation_mask": "0x1f",
    "ps_constant_buffer_creation_mask": "0x1f",
    "shader_resource_creation_mask": "0x1f",
    "sampler_creation_mask": "0x1f",
    "state_creation_mask": "0x7",
    "vs_binding_mask": "0x1",
    "ps_binding_mask": "0x1",
    "input_binding_mask": "0x1",
    "vertex_buffer_binding_mask": "0x1",
    "vs_constant_buffer_binding_mask": "0x1f",
    "ps_constant_buffer_binding_mask": "0x1f",
    "shader_resource_binding_mask": "0x1f",
    "sampler_binding_mask": "0x1f",
    "state_binding_mask": "0x7",
    "vertex_shader_resource_creation_mask": "0x1",
    "vertex_shader_resource_binding_mask": "0x1",
    "render_target_binding_mask": "0x1",
    "topology_binding_mask": "0x1",
    "viewport_binding_mask": "0x1",
    "b4_high_semantics": "zero_or_sentinel_only_non_fidelity",
    "draw_issued": 1,
    "readback_finite": 1,
    "visual_fidelity_claim": 0,
}


class _Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(
        self,
        check_id: str,
        passed: bool,
        *,
        expected: Any = None,
        actual: Any = None,
        message: str = "",
    ) -> None:
        row: dict[str, Any] = {
            "id": check_id,
            "status": "pass" if passed else "fail",
        }
        if expected is not None:
            row["expected"] = expected
        if actual is not None:
            row["actual"] = actual
        if message:
            row["message"] = message
        self.rows.append(row)

    def equal(self, check_id: str, actual: Any, expected: Any, message: str = "") -> None:
        self.add(check_id, actual == expected, expected=expected, actual=actual, message=message)

    def true(self, check_id: str, actual: Any, message: str = "") -> None:
        self.add(check_id, actual is True, expected=True, actual=actual, message=message)

    def false(self, check_id: str, actual: Any, message: str = "") -> None:
        self.add(check_id, actual is False or actual == 0, expected=False, actual=actual, message=message)


def _get(document: Mapping[str, Any] | None, key: str, default: Any = None) -> Any:
    return document.get(key, default) if isinstance(document, Mapping) else default


def _renderer_map(document: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    rows = _get(document, "renderers", [])
    if not isinstance(rows, list):
        return {}
    return {
        row.get("hierarchy"): row
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("hierarchy"), str)
    }


def _check_header(checks: _Checks, document: Mapping[str, Any] | None, name: str, schema: str) -> None:
    checks.equal(f"{name}.schema", _get(document, "schema"), schema, f"{name} report schema drift")
    checks.equal(f"{name}.retailPts", _get(document, "retailPts"), EXPECTED_PTS,
                 f"{name} sample PTS does not identify the shared census sample")
    checks.equal(f"{name}.effectRoot", _get(document, "effectRoot"), EXPECTED_EFFECT_ROOT,
                 f"{name} effect root does not identify the shared prefab")
    checks.equal(f"{name}.prefab", _get(document, "prefab"), EXPECTED_PREFAB,
                 f"{name} prefab identity drifted")


def _check_census(census: Mapping[str, Any] | None, checks: _Checks) -> None:
    _check_header(checks, census, "census", CENSUS_SCHEMA)
    checks.equal("census.status", _get(census, "status"), "incomplete",
                 "managed census must remain an intentionally non-admitting incomplete report")
    checks.equal("census.packetStrideBytes", _get(census, "packetStrideBytes"), 136,
                 "M23 ISGN stride contract drifted")
    checks.true("census.publicInputCensusClosed", _get(census, "publicInputCensusClosed"))
    checks.false("census.sourceRendererSubmissionPath", _get(census, "sourceRendererSubmissionPath"))
    checks.false("census.candidatePacketAdmission", _get(census, "candidatePacketAdmission"))
    checks.false("census.exactPackedRowParity", _get(census, "exactPackedRowParity"))
    checks.false("census.drawTimeCb3Available", _get(census, "drawTimeCb3Available"))
    checks.false("census.visualAdmission", _get(census, "visualAdmission"))
    checks.true("census.nativePackedColorProducerProven", _get(census, "nativePackedColorProducerProven"))
    checks.equal("census.retailClockOriginPts", _get(census, "retailClockOriginPts"), EXPECTED_CLOCK_ORIGIN_PTS)
    checks.equal("census.activePacketFields", _packet_field_contract(census), EXPECTED_PACKET_FIELDS,
                 "136-byte field offsets/components drifted")

    rows = _get(census, "renderers", [])
    checks.equal("census.rendererCount", len(rows) if isinstance(rows, list) else None, 4,
                 "M23 census must contain exactly four authored renderers")
    renderers = _renderer_map(census)
    checks.equal("census.rendererHierarchies", sorted(renderers),
                 sorted(item["hierarchy"] for item in EXPECTED_RENDERERS))
    for expected in EXPECTED_RENDERERS:
        hierarchy = expected["hierarchy"]
        row = renderers.get(hierarchy)
        if row is None:
            checks.add(f"census.renderer.{hierarchy}.present", False, expected=True, actual=False,
                       message="missing renderer prevents a safe row join")
            continue
        for field, expected_value in (
            ("particleCount", expected["particleCount"]),
            ("totalSourceVertices", expected["sourceVertexCount"] * expected["particleCount"]),
            ("totalSourceIndices", expected["sourceIndexCount"] * expected["particleCount"]),
            ("activeVertexStreamIds", EXPECTED_STREAM_IDS),
            ("renderMode", "Mesh"),
            ("sourceRendererEnabled", True),
            ("candidateRowsBuilt", True),
            ("exactPackedRowsAvailable", False),
            ("drawTimeCb3Available", False),
        ):
            checks.equal(f"census.renderer.{hierarchy}.{field}", row.get(field), expected_value)
        mesh_ids = row.get("meshPathIds")
        checks.equal(f"census.renderer.{hierarchy}.meshPathIds", mesh_ids, [expected["meshPathId"]])
        particles = row.get("particles")
        expected_particles = expected["particleCount"]
        checks.equal(f"census.renderer.{hierarchy}.particleRows", len(particles) if isinstance(particles, list) else None,
                     expected_particles)
        if isinstance(particles, list):
            for particle in particles:
                vertices = particle.get("vertices") if isinstance(particle, Mapping) else None
                checks.true(
                    f"census.renderer.{hierarchy}.particle.{particle.get('particleIndex')}.candidateRows",
                    isinstance(vertices, list) and len(vertices) == expected["sourceVertexCount"],
                    "candidate vertices must cover the source mesh but remain non-admitting",
                )


def _packet_field_contract(document: Mapping[str, Any] | None) -> dict[str, tuple[Any, Any]]:
    fields = _get(document, "packetFields", [])
    result: dict[str, tuple[Any, Any]] = {}
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, Mapping) and isinstance(field.get("semantic"), str):
                result[field["semantic"]] = (field.get("offsetBytes"), field.get("componentCount"))
    return result


def _check_oracle(oracle: Mapping[str, Any] | None, census: Mapping[str, Any] | None, checks: _Checks) -> None:
    _check_header(checks, oracle, "oracle", ORACLE_SCHEMA)
    checks.equal("oracle.status", _get(oracle, "status"), "passed")
    checks.true("oracle.sourceContractPassed", _get(oracle, "sourceContractPassed"))
    checks.true("oracle.noDefaultsUsed", _get(oracle, "noDefaultsUsed"))
    checks.false("oracle.visualAdmission", _get(oracle, "visualAdmission"))
    checks.equal("oracle.retailClockOriginPts", _get(oracle, "retailClockOriginPts"), EXPECTED_CLOCK_ORIGIN_PTS)

    census_map = _renderer_map(census)
    oracle_map = _renderer_map(oracle)
    checks.equal("join.rendererHierarchies", sorted(oracle_map), sorted(census_map),
                 "census and source oracle renderer sets do not join")
    live_rows = 0
    expected_baked_alphas: list[int] = []
    actual_public_alphas: list[Any] = []
    actual_segment_hashes: list[str] = []
    for expected in EXPECTED_RENDERERS:
        hierarchy = expected["hierarchy"]
        row = oracle_map.get(hierarchy)
        census_row = census_map.get(hierarchy)
        if row is None:
            checks.add(f"oracle.renderer.{hierarchy}.present", False, expected=True, actual=False)
            continue
        for field in (
            "sourceGeometryClosed", "particleStateClosed", "custom1Closed", "segmentMappingClosed",
            "indexSequenceClosed", "localTrsClosed", "inverseTransposeNormalClosed", "stateResetClosed",
            "bakeMeshMutationClosed", "repeatClosed", "cameraInvarianceAuthoredGateClosed",
        ):
            checks.true(f"oracle.renderer.{hierarchy}.{field}", row.get(field),
                        "source oracle gate must close before joining a packet")
        if row.get("cameraInvarianceExpected"):
            checks.true(f"oracle.renderer.{hierarchy}.cameraInvarianceClosed", row.get("cameraInvarianceClosed"))
        checks.true(f"oracle.renderer.{hierarchy}.sourceRendererEnabled", row.get("sourceRendererEnabled"))
        checks.equal(f"oracle.renderer.{hierarchy}.particleCount", row.get("particleCount"), expected["particleCount"])
        particles = row.get("particles")
        expected_count = expected["particleCount"]
        checks.equal(f"oracle.renderer.{hierarchy}.particleRows", len(particles) if isinstance(particles, list) else None,
                     expected_count)
        source_meshes = row.get("sourceMeshes")
        if isinstance(source_meshes, list) and source_meshes:
            source_mesh = source_meshes[0]
            checks.equal(f"join.{hierarchy}.sourceMeshPathId", source_mesh.get("meshPathId"), expected["meshPathId"])
            checks.equal(f"join.{hierarchy}.sourceVertexCount", source_mesh.get("vertexCount"), expected["sourceVertexCount"])
            checks.equal(f"join.{hierarchy}.sourceIndexCount", source_mesh.get("indexCount"), expected["sourceIndexCount"])
            if isinstance(census_row, Mapping):
                census_meshes = census_row.get("sourceMeshes")
                if isinstance(census_meshes, list) and census_meshes:
                    checks.equal(f"join.{hierarchy}.sourceMeshName", census_meshes[0].get("name"), source_mesh.get("name"))
                    checks.equal(f"join.{hierarchy}.sourceMeshPathId.census", census_meshes[0].get("meshPathId"), source_mesh.get("meshPathId"))
                    checks.equal(f"join.{hierarchy}.sourceVertexCount.census", census_meshes[0].get("vertexCount"), source_mesh.get("vertexCount"))
        if not isinstance(particles, list):
            continue
        for particle in particles:
            live_rows += 1
            index = particle.get("particleIndex")
            checks.equal(f"oracle.renderer.{hierarchy}.particle.{index}.meshIndex", particle.get("meshIndex"), 0)
            checks.true(f"oracle.renderer.{hierarchy}.particle.{index}.bakedIndexRangeValid", particle.get("bakedIndexRangeValid"))
            checks.true(f"oracle.renderer.{hierarchy}.particle.{index}.bakedIndexSequenceValid", particle.get("bakedIndexSequenceValid"))
            checks.equal(f"oracle.renderer.{hierarchy}.particle.{index}.bakedVertexCount", particle.get("bakedVertexCount"), expected["sourceVertexCount"])
            color = particle.get("color") if isinstance(particle.get("color"), Mapping) else {}
            actual_public_alphas.append(color.get("a"))
            segment_hash = str(particle.get("bakedColorSegmentSha256", "")).upper()
            expected_baked_alphas.append(_decode_repeated_white_alpha(
                segment_hash, int(particle.get("bakedVertexCount") or 0)))
            actual_segment_hashes.append(segment_hash)
            expected_hashes = EXPECTED_BAKED_COLOR_SEGMENT_SHA256.get(hierarchy, [])
            expected_hash = expected_hashes[index] if isinstance(index, int) and 0 <= index < len(expected_hashes) else None
            checks.equal(f"color.{hierarchy}.particle.{index}.bakedColorSegmentSha256",
                         str(particle.get("bakedColorSegmentSha256", "")).upper(), expected_hash)
            if isinstance(census_row, Mapping):
                census_particles = census_row.get("particles")
                census_particle = next((value for value in census_particles or []
                                        if isinstance(value, Mapping) and value.get("particleIndex") == index), None)
                checks.equal(f"join.{hierarchy}.particle.{index}.randomSeed",
                             census_particle.get("randomSeed") if isinstance(census_particle, Mapping) else None,
                             particle.get("randomSeed"))
                census_color = census_particle.get("currentColor") if isinstance(census_particle, Mapping) else None
                checks.equal(f"join.{hierarchy}.particle.{index}.publicColor",
                             census_color, color)
        baked_mesh = row.get("bakedMesh")
        if expected["particleCount"]:
            expected_mesh_hash = EXPECTED_BAKED_COLOR_MESH_SHA256.get(hierarchy)
            checks.equal(f"color.{hierarchy}.bakedMesh.colors.sha256",
                         str((baked_mesh or {}).get("colors", {}).get("sha256", "")).upper()
                         if isinstance(baked_mesh, Mapping) else None,
                         expected_mesh_hash)
        elif isinstance(baked_mesh, Mapping):
            checks.equal(f"color.{hierarchy}.inactiveBakedColorCount",
                         (baked_mesh.get("colors") or {}).get("count"), 0)

    checks.equal("join.liveParticleRows", live_rows, 4,
                 "the shared PTS must contain two rows in each of the two active M23 renderers")
    checks.equal("color.publicAlphaSequence", actual_public_alphas,
                 EXPECTED_PUBLIC_ALPHAS + EXPECTED_PUBLIC_ALPHAS,
                 "public GetCurrentColor is a census value, not the packed COLOR0 producer")
    checks.equal("color.bakedAlphaSequence", expected_baked_alphas,
                 [51, 70, 51, 70],
                 "pinned BakeMesh COLOR0 alpha lanes are 51/70")
    checks.equal("color.bakedColorSegmentEvidenceCount", len(actual_segment_hashes), 4)


def _check_exact(exact: Mapping[str, Any] | None, checks: _Checks) -> None:
    checks.equal("exact.schema", _get(exact, "schema"), EXACT_SCHEMA, "exact bridge schema drifted")
    checks.equal("exact.mode", _get(exact, "mode"), "exact_pair")
    checks.equal("exact.status", _get(exact, "status"), "pass")
    for field, expected in EXPECTED_EXACT_FIELDS.items():
        checks.equal(f"exact.{field}", _get(exact, field), expected)
    for key in ("actor_particle_input", "actorParticleInput", "production_submission", "productionSubmission"):
        if key in (exact or {}):
            checks.false(f"exact.{key}", exact.get(key), "exact fixture must not claim live actor input")
    if isinstance(exact, Mapping) and "synthetic_grid" in exact:
        checks.true("exact.synthetic_grid", exact.get("synthetic_grid"),
                    "fixture provenance must remain explicit when present")


def validate_documents(
    census: Mapping[str, Any] | None,
    oracle: Mapping[str, Any] | None,
    exact: Mapping[str, Any] | None,
    *,
    input_paths: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a structured validation report; never silently admits on failure."""

    checks = _Checks()
    if census is None:
        checks.add("input.census.present", False, expected=True, actual=False, message="census JSON could not be loaded")
    if oracle is None:
        checks.add("input.oracle.present", False, expected=True, actual=False, message="oracle JSON could not be loaded")
    if exact is None:
        checks.add("input.exact.present", False, expected=True, actual=False, message="exact bridge JSON could not be loaded")
    _check_census(census, checks)
    _check_oracle(oracle, census, checks)
    _check_exact(exact, checks)
    failed = [row for row in checks.rows if row["status"] == "fail"]
    return {
        "schema": SCHEMA,
        "status": "pass" if not failed else "fail",
        "inputs": dict(input_paths or {}),
        "checks": checks.rows,
        "summary": {
            "passed": len(checks.rows) - len(failed),
            "failed": len(failed),
            "firstFailure": failed[0]["id"] if failed else None,
        },
        "admission": {
            "publicInputCensus": bool(_get(census, "publicInputCensusClosed")),
            "exactPackedRowParity": bool(_get(census, "exactPackedRowParity")),
            "drawTimeCb3Available": bool(_get(census, "drawTimeCb3Available")),
            "visualAdmission": bool(_get(census, "visualAdmission")) or bool(_get(oracle, "visualAdmission")),
            "visualFidelityClaim": _get(exact, "visual_fidelity_claim"),
            "claim": "source-input-join-only; packed-row and visual admission remain false",
        },
    }


def _load(path: Path, name: str) -> tuple[Mapping[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"{name}: {path}: {exc}"
    if not isinstance(value, Mapping):
        return None, f"{name}: {path}: top-level JSON value is not an object"
    return value, None


def build_report(census_path: Path, oracle_path: Path, exact_path: Path) -> dict[str, Any]:
    documents: dict[str, Mapping[str, Any] | None] = {}
    errors: list[str] = []
    for name, path in (("census", census_path), ("oracle", oracle_path), ("exact", exact_path)):
        documents[name], error = _load(path, name)
        if error:
            errors.append(error)
    report = validate_documents(
        documents["census"], documents["oracle"], documents["exact"],
        input_paths={"census": str(census_path), "oracle": str(oracle_path), "exact": str(exact_path)},
    )
    if errors:
        report["inputErrors"] = errors
        report["status"] = "fail"
        report["summary"]["failed"] += len(errors)
        if report["summary"]["firstFailure"] is None:
            report["summary"]["firstFailure"] = "input.census.present" if documents["census"] is None else (
                "input.oracle.present" if documents["oracle"] is None else "input.exact.present"
            )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=Path, default=DEFAULT_CENSUS)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--exact", type=Path, default=DEFAULT_EXACT)
    parser.add_argument("--output", type=Path, help="optional path for the structured report")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    report = build_report(args.census, args.oracle, args.exact)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
