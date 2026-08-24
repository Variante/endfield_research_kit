#!/usr/bin/env python3
"""Fail-closed audit of the targeted HGRP/LitEffect raw subprogram export.

This is deliberately a narrow evidence verifier, not a general AnimeStudio
manifest reader.  It proves that one exact Shader object, exporter revision,
installed source CAB, sidecar manifest, and two Ruri outputs still describe
the same targeted run.  It never reads or publishes shader program bytes in
the durable evidence file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[2]
UNITY = REPO / "unity_endfield_graph_shader_lab"
DEFAULT_MANIFEST = (
    REPO
    / "scratch/animestudio/endminf_liteffect_shader/sidecars/Shader/"
    "HGRP_LitEffect_p5936F49FA93F14DD.shader.bytecode/manifest.json"
)
DEFAULT_RAW_EVIDENCE = (
    UNITY
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/"
    "Endminf/ExternalUiEffects/endminf_shader_raw_object_evidence.json"
)
DEFAULT_EVIDENCE = (
    UNITY
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/"
    "Endminf/ExternalUiEffects/endminf_liteffect_subprogram_evidence.json"
)
DEFAULT_CLI = (
    REPO
    / "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/"
    "AnimeStudio.CLI.exe"
)
DEFAULT_RURI = UNITY / "tools/bin/Release/net10.0/Ruri.ShaderDecompiler.Endfield.exe"

EXPECTED_SCHEMA = "animestudio.shader-subprogram.v1"
EXPECTED_SUBMODULE_COMMIT = "8ca2a2671d5d775e7f5db68a9c6d874165ecb5ee"
EXPECTED_CLI_SHA256 = "0af5f79d258580dd41466daefa5c0a7203f51c5ef35e982f54787f82bc1c2307"
EXPECTED_RURI_SHA256 = "d42aced865043a724bf9e7a2bd9e5dc379a056a9a2b70e99aff81c4e0b7f7b06"
EXPECTED_MANIFEST_SHA256 = "ad2bf8f1c7a78305ecb4d3f17702c07b36da018e2552b3ffced529fe1274ab99"

EXPECTED_SOURCE = {
    "path": r"D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\0CE8FA57\19F0903A12BA87C0D43E67E64889B525.chk",
    "size": 211831350,
    "sha256": "cbc87c7d8f41d90da25af7758cf77ced7321d19c52c067f6f77a75aa5dabc380",
}
EXPECTED_SHADER = {
    "cab": "CAB-2c811ef28608ab220ecdb5c4e0629d2d",
    "pathId": 6428594484694422749,
    "name": "HGRP/LitEffect",
}
EXPECTED_RAW_OBJECT = {
    "size": 1920196,
    "sha256": "0cf994a764694183b2c59eef25114f5d699315655e7467dd55cf378e676ee0eb",
    "sourceOffset": 40675344,
}
EXPECTED_COUNTS = {
    "entries": 2240,
    "encoding": {"DXBC": 680, "SMOL-V": 780, "SPIR-V": 780},
}
EXPECTED_RURI_OUTPUTS = {
    "parallax_hgbuffer_vertex.hlsl": {
        "size": 23831,
        "sha256": "766bb181381150caf1e732abb67e885e3388f6a589e8685cc82b8435dd689d9c",
        "markers": ("SV_Position",),
    },
    "parallax_hgbuffer_fragment.hlsl": {
        "size": 15426,
        "sha256": "7783cc2a916242f273853b115b2b4b67dfb8736940d86220d1cdf91dfe459744",
        "markers": ("SV_Target0", "SV_Target4", "frag_main"),
    },
}
EXPECTED_REPRESENTATIVES = {
    "vertex": {
        "fileName": "0114_endfield_dxbc_0.dxbc",
        "encoding": "DXBC",
        "stage": "vertex",
        "serializedStage": "vertex",
        "decodedStage": "vertex",
        "sourceOffset": 8244,
        "sourceSize": 7820,
        "rawSourceOffset": 8244,
        "rawSourceSize": 7820,
        "byteCount": 7820,
        "sha256": "b38d5e7661abdcb0d56a1c349eb673d205547fef5a30ba7d10befbe78b638253",
        "shaderLOD": 600,
        "subShaderIndex": 0,
        "passIndex": 0,
        "passName": "HGBuffer",
        "subProgramIndex": 19,
        "programBlobIndex": 207,
        "platform": "d3d11",
        "programType": "EndfieldD3D11",
        "programTypeValue": 33,
        "shaderHardwareTier": -1,
        "keywords": ["HG_ENABLE_MV", "_PARALLAX_MAP"],
        "localKeywords": [],
    },
    "fragment": {
        "fileName": "0115_endfield_dxbc_1.dxbc",
        "encoding": "DXBC",
        "stage": "fragment",
        "serializedStage": "vertex",
        "decodedStage": "fragment",
        "sourceOffset": 176,
        "sourceSize": 8068,
        "rawSourceOffset": 176,
        "rawSourceSize": 8068,
        "byteCount": 8068,
        "sha256": "b2248a1deb886a0e9226695d46e650756be932addd55a81d2b1114fdeb5f932a",
        "shaderLOD": 600,
        "subShaderIndex": 0,
        "passIndex": 0,
        "passName": "HGBuffer",
        "subProgramIndex": 19,
        "programBlobIndex": 207,
        "platform": "d3d11",
        "programType": "EndfieldD3D11",
        "programTypeValue": 33,
        "shaderHardwareTier": -1,
        "keywords": ["HG_ENABLE_MV", "_PARALLAX_MAP"],
        "localKeywords": [],
    },
}
EXPECTED_METADATA = {
    "0114_endfield_dxbc_0.dxbc.metadata.json": {
        "size": 31827,
        "sha256": "2866f1fd1cfd939d17cbf55c3a82b659c2edfe7da802f9e3f29a04f4c6344245",
        "decodedStage": "vertex",
    },
    "0115_endfield_dxbc_1.dxbc.metadata.json": {
        "size": 31829,
        "sha256": "5f0ef12fa6cbe19b16d51b7ff7a613c9007779ec2e27f3187eb25c14d421760d",
        "decodedStage": "fragment",
    },
}


class VerificationError(RuntimeError):
    """A required exact-evidence gate failed."""


def _fail(message: str) -> None:
    raise VerificationError(message)


def _hash_file(path: Path) -> str:
    if not path.is_file():
        _fail(f"missing file: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        _fail(f"cannot read {path}: {exc}")
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    if not path.is_file():
        _fail(f"missing JSON: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"invalid JSON {path}: {exc}")


def _require(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        _fail(f"{label}: expected {expected!r}, got {actual!r}")


def _require_keys(row: dict[str, Any], keys: Iterable[str], label: str) -> None:
    missing = [key for key in keys if key not in row]
    if missing:
        _fail(f"{label}: missing fields {', '.join(missing)}")


def _git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        _fail(f"git check failed: git {' '.join(args)} ({exc})")
    return completed.stdout.strip()


def _check_submodule(repo: Path) -> str:
    submodule = repo / "tools/AnimeStudio"
    commit = _git(submodule, "rev-parse", "HEAD")
    _require(commit, EXPECTED_SUBMODULE_COMMIT, "AnimeStudio submodule commit")
    dirty = _git(submodule, "status", "--porcelain")
    if dirty:
        _fail(f"AnimeStudio submodule is dirty: {dirty.splitlines()[0]}")
    return commit


def _check_cli(path: Path) -> dict[str, Any]:
    digest = _hash_file(path)
    _require(digest, EXPECTED_CLI_SHA256, "AnimeStudio.CLI SHA-256 (stale CLI)")
    return {"path": str(path), "size": path.stat().st_size, "sha256": digest}


def _check_ruri(path: Path) -> dict[str, Any]:
    digest = _hash_file(path)
    _require(digest, EXPECTED_RURI_SHA256, "Ruri executable SHA-256 (stale decompiler)")
    return {"path": str(path), "size": path.stat().st_size, "sha256": digest}


def _check_source(path_text: str) -> dict[str, Any]:
    _require(path_text, EXPECTED_SOURCE["path"], "shader source path")
    path = Path(path_text)
    if not path.is_file():
        _fail(f"missing installed shader source: {path}")
    size = path.stat().st_size
    _require(size, EXPECTED_SOURCE["size"], "shader source size (stale source)")
    digest = _hash_file(path)
    _require(digest, EXPECTED_SOURCE["sha256"], "shader source SHA-256 (stale source)")
    return {"path": path_text, "size": size, "sha256": digest}


def _check_raw_object(raw_evidence_path: Path, source_path: str) -> dict[str, Any]:
    data = _read_json(raw_evidence_path)
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        _fail("raw Shader evidence has no records list")
    matches = [
        row
        for row in records
        if isinstance(row, dict)
        and row.get("serializedFile") == EXPECTED_SHADER["cab"]
        and row.get("pathId") == EXPECTED_SHADER["pathId"]
        and row.get("targetName") == EXPECTED_SHADER["name"]
        and row.get("source") == source_path
        and row.get("sourceOffset") == EXPECTED_RAW_OBJECT["sourceOffset"]
    ]
    if len(matches) != 1:
        _fail("raw Shader evidence does not contain one exact LitEffect source record")
    row = matches[0]
    _require(row.get("targetType"), "Shader", "raw Shader target type")
    raw_object = row.get("rawObject")
    if not isinstance(raw_object, dict):
        _fail("raw Shader evidence has no rawObject record")
    _require(raw_object.get("size"), EXPECTED_RAW_OBJECT["size"], "raw Shader object size")
    _require(raw_object.get("sha256"), EXPECTED_RAW_OBJECT["sha256"], "raw Shader object SHA-256")
    return {
        "serializedFile": row["serializedFile"],
        "pathId": row["pathId"],
        "name": row["targetName"],
        "sourceOffset": row["sourceOffset"],
        "rawObject": {"size": raw_object["size"], "sha256": raw_object["sha256"]},
    }


def _validate_entry(row: dict[str, Any], sidecar_root: Path, index: int) -> dict[str, Any]:
    required = (
        "fileName", "encoding", "stage", "serializedStage", "decodedStage",
        "sourceOffset", "sourceSize", "rawSourceOffset", "rawSourceSize",
        "byteCount", "sha256", "shaderCab", "shaderPathId", "shaderName",
        "shaderSourceOriginalPath", "shaderLOD", "subShaderIndex", "passIndex",
        "passName", "subProgramIndex", "programBlobIndex", "platform",
        "programType", "programTypeValue", "shaderHardwareTier", "keywords",
        "localKeywords",
    )
    if not isinstance(row, dict):
        _fail(f"manifest entry {index}: row is not an object")
    _require_keys(row, required, f"manifest entry {index}")
    filename = row["fileName"]
    if not isinstance(filename, str) or not filename or Path(filename).name != filename:
        _fail(f"manifest entry {index}: sidecar fileName is not a safe basename")
    sidecar = sidecar_root / filename
    if not sidecar.is_file():
        _fail(f"manifest entry {index}: missing sidecar {sidecar}")
    for field in ("sourceOffset", "sourceSize", "rawSourceOffset", "rawSourceSize", "byteCount"):
        value = row[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            _fail(f"manifest entry {index}: invalid nonnegative integer {field}")
    if row["sourceSize"] <= 0:
        _fail(f"manifest entry {index}: sourceSize must be positive")
    _require(row["rawSourceOffset"], row["sourceOffset"], f"manifest entry {index} rawSourceOffset")
    _require(row["rawSourceSize"], row["sourceSize"], f"manifest entry {index} rawSourceSize")
    if row["sourceOffset"] > 0x7FFFFFFF - row["sourceSize"]:
        _fail(f"manifest entry {index}: source offset/size overflows the exporter int range")
    actual_size = sidecar.stat().st_size
    _require(actual_size, row["byteCount"], f"manifest entry {index} byteCount")
    digest = _hash_file(sidecar)
    _require(digest, row["sha256"], f"manifest entry {index} SHA-256")
    _require(row["shaderCab"], EXPECTED_SHADER["cab"], f"manifest entry {index} CAB")
    _require(row["shaderPathId"], EXPECTED_SHADER["pathId"], f"manifest entry {index} PathID")
    _require(row["shaderName"], EXPECTED_SHADER["name"], f"manifest entry {index} shader name")
    _require(row["shaderSourceOriginalPath"], EXPECTED_SOURCE["path"], f"manifest entry {index} source")
    return row


def _validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest_digest = _hash_file(manifest_path)
    _require(manifest_digest, EXPECTED_MANIFEST_SHA256, "manifest SHA-256 (stale manifest)")
    data = _read_json(manifest_path)
    if not isinstance(data, dict):
        _fail("shader manifest root is not an object")
    _require(data.get("schema"), EXPECTED_SCHEMA, "shader manifest schema")
    shader = data.get("shader")
    if not isinstance(shader, dict):
        _fail("shader manifest has no shader identity")
    for key, expected in EXPECTED_SHADER.items():
        _require(shader.get(key), expected, f"shader manifest {key}")
    source = _check_source(shader.get("sourceOriginalPath"))
    entries = data.get("entries")
    if not isinstance(entries, list):
        _fail("shader manifest has no entries list")
    _require(len(entries), EXPECTED_COUNTS["entries"], "shader manifest entry count")
    sidecar_root = manifest_path.parent
    seen: set[str] = set()
    encoding_counts: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(entries):
        row = _validate_entry(row, sidecar_root, index)
        if row["fileName"] in seen:
            _fail(f"duplicate manifest sidecar filename: {row['fileName']}")
        seen.add(row["fileName"])
        encoding_counts[row["encoding"]] = encoding_counts.get(row["encoding"], 0) + 1
        rows.append(row)
    _require(encoding_counts, EXPECTED_COUNTS["encoding"], "manifest encoding counts")
    return {
        "path": str(manifest_path),
        "sha256": manifest_digest,
        "schema": data["schema"],
        "shader": shader,
        "source": source,
        "entries": rows,
        "encodingCounts": encoding_counts,
    }


def _validate_target_variant(manifest: dict[str, Any], ruri_dir: Path) -> dict[str, Any]:
    rows = [
        row
        for row in manifest["entries"]
        if row.get("passName") == "HGBuffer"
        and row.get("platform") == "d3d11"
        and row.get("encoding") == "DXBC"
        and "_PARALLAX_MAP" in row.get("keywords", [])
    ]
    _require(len(rows), 84, "_PARALLAX_MAP HGBuffer D3D11 entry count")
    stages = {row.get("decodedStage") for row in rows}
    _require(stages, {"vertex", "fragment"}, "target decoded stages")
    for stage, expected in EXPECTED_REPRESENTATIVES.items():
        matches = [row for row in rows if row.get("decodedStage") == stage and row.get("subProgramIndex") == 19]
        if len(matches) != 1:
            _fail(f"target representative {stage}: expected one subProgramIndex 19 row")
        actual = matches[0]
        for key, value in expected.items():
            _require(actual.get(key), value, f"target representative {stage} {key}")

    metadata = []
    sidecar_root = Path(manifest["path"]).parent
    for filename, expected in EXPECTED_METADATA.items():
        path = sidecar_root / filename
        digest = _hash_file(path)
        _require(path.stat().st_size, expected["size"], f"metadata {filename} size")
        _require(digest, expected["sha256"], f"metadata {filename} SHA-256")
        data = _read_json(path)
        _require(
            data.get("SourceEndfieldParameterRecordParsed"),
            True,
            f"metadata {filename} Endfield parameter record",
        )
        _require(
            data.get("SourceEndfieldConstantBufferTableParsed"),
            True,
            f"metadata {filename} Endfield constant-buffer table",
        )
        _require(
            data.get("DecodedProgramStage"),
            expected["decodedStage"],
            f"metadata {filename} decoded stage",
        )
        metadata.append({
            "fileName": filename,
            "size": path.stat().st_size,
            "sha256": digest,
            "decodedStage": expected["decodedStage"],
            "endfieldConstantBufferTableParsed": True,
        })

    ruri = []
    for filename, expected in EXPECTED_RURI_OUTPUTS.items():
        path = ruri_dir / filename
        digest = _hash_file(path)
        _require(path.stat().st_size, expected["size"], f"Ruri output {filename} size")
        _require(digest, expected["sha256"], f"Ruri output {filename} SHA-256")
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in expected["markers"]:
            if marker not in text:
                _fail(f"Ruri output {filename}: missing marker {marker}")
        ruri.append({"fileName": filename, "size": path.stat().st_size, "sha256": digest})
    return {
        "entryCount": len(rows),
        "representatives": EXPECTED_REPRESENTATIVES,
        "metadata": metadata,
        "ruriOutputs": ruri,
    }


def _relative(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(path)


def _build_evidence(
    manifest: dict[str, Any],
    raw_object: dict[str, Any],
    submodule_commit: str,
    cli: dict[str, Any],
    ruri: dict[str, Any],
    target: dict[str, Any],
    manifest_path: Path,
    raw_evidence_path: Path,
    cli_path: Path,
    ruri_path: Path,
) -> dict[str, Any]:
    representatives = []
    for stage in ("vertex", "fragment"):
        row = target["representatives"][stage]
        representatives.append({
            "stage": stage,
            "fileName": row["fileName"],
            "sha256": row["sha256"],
            "byteCount": row["byteCount"],
            "sourceOffset": row["sourceOffset"],
            "sourceSize": row["sourceSize"],
            "passName": row["passName"],
            "passIndex": row["passIndex"],
            "subProgramIndex": row["subProgramIndex"],
            "programBlobIndex": row["programBlobIndex"],
            "keywords": row["keywords"],
            "serializedStage": row["serializedStage"],
            "decodedStage": row["decodedStage"],
        })
    return {
        "schema": "endfield.endminf-liteffect-subprogram-evidence.v1",
        "status": "verified",
        "scope": {
            "shader": EXPECTED_SHADER,
            "shaderLOD": 600,
            "target": "HGBuffer / d3d11 / _PARALLAX_MAP",
            "rawProgramBytes": "not embedded; sidecars remain disposable scratch output",
        },
        "source": manifest["source"],
        "rawObjectEvidence": {
            "path": _relative(raw_evidence_path, REPO),
            **raw_object,
        },
        "toolchain": {
            "animestudioSubmoduleCommit": submodule_commit,
            "cli": {"path": _relative(cli_path, REPO), "size": cli["size"], "sha256": cli["sha256"]},
            "ruri": {"path": _relative(ruri_path, REPO), "size": ruri["size"], "sha256": ruri["sha256"]},
        },
        "manifest": {
            "path": _relative(manifest_path, REPO),
            "schema": manifest["schema"],
            "size": manifest_path.stat().st_size,
            "sha256": manifest["sha256"],
            "entryCount": EXPECTED_COUNTS["entries"],
            "encodingCounts": manifest["encodingCounts"],
        },
        "target": {
            "entryCount": target["entryCount"],
            "representatives": representatives,
            "metadata": target["metadata"],
            "ruriOutputs": target["ruriOutputs"],
        },
        "evidenceBoundary": [
            "CAB/PathID/name and serialized Shader object identity are exact.",
            "Every exported sidecar length, SHA-256, source offset, and source size is checked.",
            "The selected vertex/fragment metadata sidecars are hash-pinned and must report a parsed Endfield constant-buffer table.",
            "serializedStage and decodedStage remain separate; no visual behavior is inferred.",
            "This JSON contains summaries and hashes only, never raw shader program bytes.",
        ],
    }


def _check_existing_evidence(path: Path, result: dict[str, Any]) -> None:
    if not path.is_file():
        return
    data = _read_json(path)
    if not isinstance(data, dict):
        _fail("durable LitEffect evidence is not an object")
    _require(data.get("schema"), "endfield.endminf-liteffect-subprogram-evidence.v1", "durable evidence schema")
    _require(data.get("status"), "verified", "durable evidence status")
    manifest = data.get("manifest")
    source = data.get("source")
    toolchain = data.get("toolchain")
    if not isinstance(manifest, dict) or not isinstance(source, dict) or not isinstance(toolchain, dict):
        _fail("durable LitEffect evidence is missing manifest/source/toolchain objects")
    _require(manifest.get("sha256"), result["manifest"]["sha256"], "durable evidence manifest hash")
    _require(source.get("sha256"), result["manifest"]["source"]["sha256"], "durable evidence source hash")
    _require(
        toolchain.get("animestudioSubmoduleCommit"),
        result["submoduleCommit"],
        "durable evidence AnimeStudio commit",
    )
    _require(manifest.get("entryCount"), EXPECTED_COUNTS["entries"], "durable evidence entry count")


def verify(
    manifest_path: Path = DEFAULT_MANIFEST,
    raw_evidence_path: Path = DEFAULT_RAW_EVIDENCE,
    cli_path: Path = DEFAULT_CLI,
    ruri_path: Path = DEFAULT_RURI,
    evidence_path: Path | None = DEFAULT_EVIDENCE,
    check_existing_evidence: bool = True,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    raw_evidence_path = raw_evidence_path.resolve()
    cli_path = cli_path.resolve()
    ruri_path = ruri_path.resolve()
    submodule_commit = _check_submodule(REPO)
    cli = _check_cli(cli_path)
    ruri = _check_ruri(ruri_path)
    manifest = _validate_manifest(manifest_path)
    raw_object = _check_raw_object(raw_evidence_path, manifest["source"]["path"])
    ruri_dir = manifest_path.parent / "ruri_final"
    target = _validate_target_variant(manifest, ruri_dir)
    result = {
        "manifest": manifest,
        "rawObject": raw_object,
        "submoduleCommit": submodule_commit,
        "cli": cli,
        "ruri": ruri,
        "target": target,
    }
    if evidence_path is not None and check_existing_evidence:
        _check_existing_evidence(evidence_path.resolve(), result)
    return result


def write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-evidence", type=Path, default=DEFAULT_RAW_EVIDENCE)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--ruri", type=Path, default=DEFAULT_RURI)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--write-evidence", action="store_true", help="write the durable summary after verification")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = verify(
            args.manifest,
            args.raw_evidence,
            args.cli,
            args.ruri,
            args.evidence,
            check_existing_evidence=not args.write_evidence,
        )
        if args.write_evidence:
            evidence = _build_evidence(
                result["manifest"],
                result["rawObject"],
                result["submoduleCommit"],
                result["cli"],
                result["ruri"],
                result["target"],
                args.manifest.resolve(),
                args.raw_evidence.resolve(),
                args.cli.resolve(),
                args.ruri.resolve(),
            )
            write_evidence(args.evidence.resolve(), evidence)
            _check_existing_evidence(args.evidence.resolve(), result)
        print(json.dumps({
            "status": "verified",
            "manifestEntries": len(result["manifest"]["entries"]),
            "targetEntries": result["target"]["entryCount"],
            "evidence": str(args.evidence.resolve()) if args.write_evidence else None,
        }, indent=2))
        return 0
    except VerificationError as exc:
        print(f"verify_endminf_liteffect_subprograms: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
