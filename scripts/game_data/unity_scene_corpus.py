"""Fresh selected-Bundle scene bodies, collider backlinks and cooked Mesh joins.

Coverage is exported objects in the explicit physical CAB selection, not every
scene or live instance. External Mesh PPtrs require the referring export's
serialized external-table slot and a unique fresh physical target CAB.
The cooked-collision gate supplies the shared selected Unity/VFS authentication.
Mesh selectors require that object in the export. AssetBundle selectors with
PathID=0 select a physical Bundle span only; they assert no object identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from scripts.game_data.cooked_collision_corpus import (
    DEFAULT_CLI, _decoder_closure, _digest, _identity, _path_key,
    _selected_ledger, _selection_input, _verify_fingerprints, inspect_exports,
)
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.unity_scene import read_scene_object, scene_identity, trace_collider
from scripts.game_data.unity_asset_bundle import read_container_prefix
from scripts.repo_paths import REPO_ROOT

SCENE_TYPES = ("GameObject", "Transform", "MeshCollider", "MeshColliderEx", "AssetBundle")


def _pointer(document: dict) -> tuple[int, int]:
    return document["m_FileID"], document["m_PathID"]


def _external_mesh_target(identity: tuple, pointer: tuple, metadata: dict, sources: dict) -> tuple | None:
    """Resolve the exporter-observed external slot, never a bare PathID."""
    rows = [row for row in metadata.get("pptrReferences", []) if row.get("path") == "$.m_Mesh"]
    if len(rows) != 1:
        raise ValueError("external Mesh PPtr lacks one serialized external-table witness")
    row = rows[0]
    if (row.get("fileId"), row.get("pathId")) != pointer:
        raise ValueError("external Mesh witness differs from raw PPtr")
    cab = row.get("expectedTargetSourceFile")
    external_path = row.get("expectedTargetExternalPath", "")
    if not cab or external_path.replace("\\", "/").rsplit("/", 1)[-1] != cab:
        raise ValueError("external Mesh slot CAB/path witness differs")
    locations = {key[:3] for key in sources if key[2] == cab}
    if len(locations) > 1:
        raise ValueError(f"external Mesh target CAB has {len(locations)} physical locations")
    if not locations:
        return None
    target = (*next(iter(locations)), pointer[1] & ((1 << 64)-1))
    if row.get("resolutionStatus") == "resolved":
        observed = dict(sourceOriginalPath=row["targetSourceOriginalPath"],
                        sourceOffset=row["targetSourceOffset"], sourceFile=row["targetSourceFile"],
                        pathId=row["targetPathId"])
        if scene_identity(observed) != target:
            raise ValueError("resolved external Mesh identity differs from fresh target CAB")
    return target


def _check_typed(body: dict, document: dict, kind: str) -> None:
    """Independently decoded raw values must agree with the typed export."""
    if kind == "AssetBundle":
        typed = [dict(path=row["Key"], preloadIndex=row["Value"]["preloadIndex"],
                      preloadSize=row["Value"]["preloadSize"], asset=_pointer(row["Value"]["asset"]))
                 for row in document["m_Container"]]
        if (body["name"] != document["m_Name"] or body["preload"] != list(map(_pointer, document["m_PreloadTable"]))
                or body["containers"] != typed):
            raise ValueError("AssetBundle raw container/preload prefix differs from typed JSON")
        return
    if kind == "GameObject":
        if body["name"] != document["m_Name"] or body["components"] != list(map(_pointer, document["m_Components"])):
            raise ValueError("GameObject raw name/components differ from typed JSON")
        if "m_Layer" in document and body["layer"] != document["m_Layer"]:
            raise ValueError("GameObject raw layer differs from typed JSON")
        return
    if body["gameObject"] != _pointer(document["m_GameObject"]):
        raise ValueError(f"{kind} raw GameObject PPtr differs from typed JSON")
    if kind == "Transform":
        for field, name, axes in (("rotation", "m_LocalRotation", "XYZW"),
                                  ("position", "m_LocalPosition", "XYZ"), ("scale", "m_LocalScale", "XYZ")):
            # Newtonsoft writes the shortest float32 round-trip decimal.
            typed = tuple(struct.unpack("<f", struct.pack("<f", document[name][axis]))[0] for axis in axes)
            if typed != body[field]:
                raise ValueError(f"Transform raw {field} differs from typed JSON")
        if body["children"] != list(map(_pointer, document["m_Children"])) or body["father"] != _pointer(document["m_Father"]):
            raise ValueError("Transform raw parent/children differ from typed JSON")
    elif kind in ("MeshCollider", "BoxCollider"):
        fields = (("colliderOptions", "m_ColliderOptions"), ("tagConfig", "m_TagConfig"),
                  ("surfaceType", "m_SurfaceType"), ("isTrigger", "m_IsTrigger"),
                  ("enabled", "m_Enabled"), ("enableDither", "m_EnableDither"))
        if kind == "MeshCollider":
            fields += (("convex", "m_Convex"), ("cookingOptions", "m_CookingOptions"))
        for field, name in fields:
            if body[field] != document[name]:
                raise ValueError(f"{kind} raw {field} differs from typed JSON")
        if body["material"] != _pointer(document["m_Material"]):
            raise ValueError(f"{kind} raw material PPtr differs from typed JSON")
        if kind == "MeshCollider":
            if body["mesh"] != _pointer(document["m_Mesh"]):
                raise ValueError("MeshCollider raw Mesh PPtr differs from typed JSON")
        else:
            for field, name in (("size", "m_Size"), ("center", "m_Center")):
                typed = tuple(struct.unpack("<f", struct.pack("<f", document[name][axis]))[0] for axis in "xyz")
                if body[field] != typed:
                    raise ValueError(f"BoxCollider raw {field} differs from typed JSON")
    elif kind == "Rigidbody":
        for field, name in (("mass","m_Mass"),("drag","m_Drag"),("angularDrag","m_AngularDrag")):
            typed = struct.unpack('<f',struct.pack('<f',document[name]))[0]
            if body[field] != typed:
                raise ValueError(f"Rigidbody raw {field} differs from typed JSON")
        for field, name in (("useGravity","m_UseGravity"),("isKinematic","m_IsKinematic"),
                            ("interpolate","m_Interpolate"),("constraints","m_Constraints"),
                            ("collisionDetection","m_CollisionDetection")):
            if body[field] != document[name]:
                raise ValueError(f"Rigidbody raw {field} differs from typed JSON")


def inspect_scene_exports(json_root: Path, raw_root: Path, selection: list) -> dict:
    """Inspect already authenticated exports; this function is not a source gate."""
    wanted_cabs = {(_path_key(row["Source"]), row["Offset"]) for row in selection}
    wanted_meshes = {_identity(row["Source"], row["Offset"], row["PathID"]) for row in selection
                     if row["Type"] == "Mesh"}
    source_rows, bodies, bundles, metadata_rows, failures, seen_raw = {}, {}, {}, {}, [], set()
    for path in sorted(json_root.glob("*/*.json")):
        try:
            document = json.loads(path.read_text("utf-8-sig")); meta = document["$animestudio"]
            kind = meta["type"]
            if kind not in (*SCENE_TYPES, "Mesh") or path.parent.name != kind:
                raise ValueError(f"unexpected exported type/folder: {kind}/{path.parent.name}")
            raw_path = raw_root/kind/(path.stem+".dat"); raw = raw_path.read_bytes()
            seen_raw.add(raw_path.resolve())
            sha = hashlib.sha256(raw).hexdigest(); key = scene_identity(meta)
            if (len(raw) != meta["rawDataLength"] or len(raw) != meta["byteSize"]
                    or sha != meta["rawDataSha256"]):
                raise ValueError("raw object length/SHA256 differs from typed metadata")
            if (key[0], key[1]) not in wanted_cabs:
                raise ValueError("exported identity lies outside the selected physical CABs")
            if key in source_rows:
                raise ValueError("duplicate exported physical/CAB/PathID identity")
            source_rows[key] = dict(identity={name: meta[name] for name in (
                "sourceOriginalPath", "sourceOffset", "sourceFile", "pathId")},
                type=kind, name=meta["name"], jsonPath=str(path), rawPath=str(raw_path),
                rawSha256=sha, jsonSha256=_digest(path), byteSize=len(raw))
            metadata_rows[key] = meta
            if kind in ("Mesh", "MeshColliderEx"):
                continue  # Mesh has its own complete readers; Ex has no proved scene layout.
            if kind == "AssetBundle":
                body = read_container_prefix(raw); _check_typed(body, document, kind)
                bundles[key] = body
                continue
            body = read_scene_object(kind, raw)
            _check_typed(body, document, kind)
            bodies[key] = dict(body, kind=kind)
        except (ValueError, KeyError, TypeError, OSError, OverflowError, struct.error) as error:
            failures.append(dict(check="scene_body", source=str(path), detail=str(error)[:800]))
    actual_raw = {path.resolve() for path in raw_root.glob("*/*.dat")}
    if actual_raw != seen_raw:
        failures.append(dict(check="raw_json_coverage", expected=len(seen_raw), actual=len(actual_raw),
                             detail=f"first unmatched: {next(iter(sorted(actual_raw ^ seen_raw)), '')}"))
    meshes = inspect_exports(json_root/"Mesh", raw_root/"Mesh")
    failures.extend(dict(check="mesh_body", **failure) for failure in meshes["failures"])
    mesh_rows = {scene_identity(row["identity"]): row for row in meshes["objects"] if row.get("identity")}
    if not wanted_meshes.issubset({_identity(row["identity"]["sourceOriginalPath"],
            row["identity"]["sourceOffset"], row["identity"]["pathId"]) for row in mesh_rows.values()}):
        failures.append(dict(check="selected_mesh_coverage", detail="selected Mesh identities missing from fresh export"))
    prefab_roots = {}
    for key, bundle in bundles.items():
        for entry in bundle["containers"]:
            target = (*key[:3], entry["asset"][1] & ((1 << 64)-1))
            if (entry["asset"][0] == 0 and entry["asset"][1] and entry["path"].endswith(".prefab")
                    and bodies.get(target, {}).get("kind") == "GameObject"):
                prefab_roots.setdefault(target, []).append(dict(path=entry["path"], bundle=source_rows[key]))
    colliders = []
    for key, body in sorted(bodies.items()):
        if body["kind"] != "MeshCollider":
            continue
        row = dict(collider=source_rows[key], runtimePlacementStatus="unresolved")
        try:
            traced = trace_collider(key, bodies); row["trace"] = traced
            row["prefabAssets"] = prefab_roots.get(tuple(traced["chain"][-1]["gameObject"]), [])
            if traced["meshPointerStatus"] == "external_unresolved":
                target = _external_mesh_target(key, body["mesh"], metadata_rows[key], source_rows)
                if target is not None:
                    traced.update(mesh=target, meshPointerStatus="external_serialized_target")
            mesh = mesh_rows.get(traced["mesh"])
            if traced["meshPointerStatus"] not in ("local", "external_serialized_target"):
                row["status"] = "mesh_"+traced["meshPointerStatus"]
            elif mesh is None:
                row["status"] = "local_mesh_unavailable"
            elif mesh["status"] == "failed":
                row["status"] = "mesh_decode_failed"
            else:
                expected_kind = "convex" if body["convex"] else "triangle"
                row["mesh"] = {field: mesh[field] for field in (
                    "identity", "name", "rawSha256", "collisionOnly", "baked", "convex", "renderVertexCount")}
                row["geometry"] = [item for item in mesh["payloads"] if item["kind"] == expected_kind]
                row["status"] = "exact_serialized_collider_link" if row["geometry"] else "mesh_has_no_selected_cooked_buffer"
        except (ValueError, KeyError, TypeError) as error:
            row.update(status="hierarchy_unresolved", diagnostic=str(error)[:800])
        colliders.append(row)
    return dict(status="failed" if failures else "complete", failures=failures, colliders=colliders,
                counts=dict(objects=len(source_rows), sceneBodies=len(bodies), meshes=len(mesh_rows),
                            types=dict(Counter(row["type"] for row in source_rows.values())),
                            colliderStatuses=dict(Counter(row["status"] for row in colliders))),
                rawSources=[source_rows[key] for key in sorted(source_rows)],
                assetBundlePrefixes=[dict(source=source_rows[key], prefix=body) for key, body in sorted(bundles.items())],
                unsupportedSceneLayouts=[source_rows[key] for key in sorted(source_rows)
                                         if source_rows[key]["type"] == "MeshColliderEx"])


def audit_selection(*, selection_path: Path, summary_path: Path, ledger_path: Path,
                    expected_input_set: str, work_root: Path, cli: Path = DEFAULT_CLI,
                    reuse_path: Path | None = None, receipt_root: Path = REPO_ROOT) -> dict:
    selection = json.loads(selection_path.read_text("utf-8"))
    if (not isinstance(selection, list) or not selection
            or any(row.get("Type") not in ("Mesh", "AssetBundle") for row in selection)
            or any(row["Type"] == "AssetBundle" and row.get("PathID") != 0 for row in selection)
            or len({_identity(row["Source"], row["Offset"], row["PathID"]) for row in selection}) != len(selection)):
        raise ValueError("selection must contain unique Mesh identities or AssetBundle physical selectors with PathID=0")
    summary, provenance, files, chunks = _selected_ledger(summary_path, ledger_path, selection, expected_input_set)
    if _path_key(cli) not in {_path_key(row["path"]) for row in summary["buildFingerprints"]}:
        raise ValueError("selected scene exporter CLI is absent from the current VFS audit")
    selection_sha = _digest(selection_path); _verify_fingerprints(summary)
    closure = _decoder_closure(cli); physical_inputs = []
    for key, chunk in sorted(chunks.items()):
        path = Path(chunk["physicalChunkPath"]); stat = path.stat(); digest = _digest(path, "md5")
        if stat.st_size != chunk["actualPhysicalLength"] or digest != chunk["recomputedContentMd5"]:
            raise ValueError(f"selected physical chunk differs from current audit: {path}")
        physical_inputs.append(dict(path=str(path), length=stat.st_size, mtimeNs=stat.st_mtime_ns, md5=digest))
    previous = None
    if reuse_path is not None:
        previous = json.loads(reuse_path.read_text("utf-8"))
        def provenance_key(value):
            return {**value, **{field: _path_key(receipt_root / value[field])
                               for field in ("outerLedger", "outerSummaryPath")}}
        checks = (("schema", previous.get("schema"), "endfield.selected-unity-scene-corpus.v4"),
                  ("inputSetSha256", previous["inputSetSha256"], expected_input_set.upper()),
                  ("selection.sha256", previous["selection"]["sha256"], selection_sha),
                  ("selection.path", previous["selection"]["path"], str(selection_path.resolve())))
        for field, expected, actual in checks:
            if expected != actual:
                raise ValueError(f"scene reuse gate {field}: receipt={reuse_path}; expected={expected}; actual={actual}")
        old_provenance, new_provenance = provenance_key(previous["provenance"]), provenance_key(provenance)
        for field in sorted(set(old_provenance) | set(new_provenance)):
            if old_provenance.get(field) != new_provenance.get(field):
                raise ValueError(f"scene reuse gate provenance.{field}: receipt={reuse_path}; "
                                 f"expected={str(old_provenance.get(field))[:240]}; actual={str(new_provenance.get(field))[:240]}")
        if previous["extraction"]["decoderOutputClosure"] != closure:
            old = {row["path"]: row for row in previous["extraction"]["decoderOutputClosure"]}
            new = {row["path"]: row for row in closure}
            field = next((name for name in sorted(set(old) | set(new)) if old.get(name) != new.get(name)), "row order")
            raise ValueError(f"scene reuse gate exporter closure: receipt={reuse_path}; file={cli.parent/field}; "
                             f"expected={old.get(field)}; actual={new.get(field)}")
        old_physical = previous["extraction"]["physicalInputs"]
        if old_physical != physical_inputs:
            raise ValueError("saved scene extraction physical input snapshot differs")
        run_root = Path(previous["extraction"]["command"][2]).parent
    else:
        work_root.mkdir(parents=True, exist_ok=True)
        run_root = Path(tempfile.mkdtemp(prefix="scene-", dir=work_root))
    json_root, raw_root = run_root/"json", run_root/"raw"
    types = [*SCENE_TYPES, "Mesh"]
    command = [str(cli), str(_selection_input(selection)), str(json_root), "--game", "ArknightsEndfield",
               "--types", *types, "--export_type", "JSON", "--filter_data", str(selection_path.resolve()),
               "--secondary_export_type", "Raw", "--secondary_export_path", str(raw_root),
               "--secondary_types", *types, "--logger_flags", "Warning", "Error"]
    log_path = run_root/"export.log"
    if previous is not None:
        if (previous["extraction"]["command"] != command or previous["extraction"]["log"] != str(log_path)
                or _digest(log_path) != previous["extraction"]["logSha256"]):
            raise ValueError("saved scene extraction command/log differs")
    else:
        with log_path.open("wb") as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
        if completed.returncode:
            raise ValueError(f"AnimeStudio scene export returned {completed.returncode}; log={log_path}")
    if _digest(selection_path) != selection_sha or _decoder_closure(cli) != closure:
        raise ValueError("selection/exporter output closure changed during scene extraction")
    _verify_fingerprints(summary)
    for item in physical_inputs:
        stat = Path(item["path"]).stat()
        if (stat.st_size, stat.st_mtime_ns) != (item["length"], item["mtimeNs"]):
            raise ValueError(f"physical chunk changed during scene extraction: {item['path']}")
    report = inspect_scene_exports(json_root, raw_root, selection)
    if previous is not None and report["rawSources"] != previous["rawSources"]:
        raise ValueError("saved scene extraction object identities/raw hashes differ")
    _verify_fingerprints(summary)
    if _digest(selection_path) != selection_sha or _decoder_closure(cli) != closure:
        raise ValueError("selection/exporter output closure changed during scene inspection")
    for item in physical_inputs:
        stat = Path(item["path"]).stat()
        if (stat.st_size, stat.st_mtime_ns) != (item["length"], item["mtimeNs"]):
            raise ValueError(f"physical chunk changed during scene inspection: {item['path']}")
    # A silent per-asset omission is not evidence of absence. Retain the bounded
    # warning/error log and refuse to mark this exported census complete.
    if log_path.stat().st_size:
        report["failures"].append(dict(check="export_diagnostics", source=str(log_path),
                                       detail=log_path.read_text("utf-8", errors="replace")[:1200]))
        report["status"] = "failed"
    report.update(schema="endfield.selected-unity-scene-corpus.v4", inputSetSha256=expected_input_set.upper(),
                  provenance=provenance,
                  selection=dict(path=str(selection_path.resolve()), sha256=selection_sha,
                                 meshCount=sum(row["Type"] == "Mesh" for row in selection), cabCount=len(files)),
                  extraction=dict(command=command, log=str(log_path), logSha256=_digest(log_path),
                                  decoderOutputClosure=closure, physicalInputs=physical_inputs),
                  evidenceBoundary="Authenticated fresh exported scene bodies in selected physical Bundle CABs. Raw/typed values, local component backlinks and complete reciprocal TRS chains join current cooked Mesh buffers. External Mesh PPtrs require the exporter-observed referring external slot and a unique fresh physical target CAB. Export coverage is not an inner object-directory absence proof. Unavailable or ambiguous external targets, scene instantiation and runtime activation remain unresolved.")
    return report


def validate_receipt(report_path: Path, *, root: Path = REPO_ROOT) -> dict:
    """Recompute stored joins from a current saved extraction, without exporting.

    Derived collider/owner rows in the receipt are never trusted. The existing
    reuse gate authenticates the VFS, exporter, physical chunks and raw/typed
    census before rebuilding those rows. Snapshots also cover consumption by
    another publisher, so a changed input cannot leave a partial owner join.
    """
    original = report_path.read_bytes()
    saved = json.loads(original)
    if (saved.get("schema") != "endfield.selected-unity-scene-corpus.v4"
            or saved.get("status") != "complete" or saved.get("failures")):
        raise ValueError("scene receipt is not a complete v4 selected-corpus result")
    summary_path = Path(saved["provenance"]["outerSummaryPath"])
    ledger_path = root / saved["provenance"]["outerLedger"]
    selection_path = Path(saved["selection"]["path"])
    summary = json.loads(summary_path.read_text("utf-8"))
    cli = Path(saved["extraction"]["command"][0])
    paths = {report_path, summary_path, ledger_path, selection_path,
             Path(saved["extraction"]["log"])}
    paths.update(Path(row["path"]) for row in summary["sourceFingerprints"] + summary["buildFingerprints"])
    paths.update(Path(row["path"]) for row in saved["extraction"]["physicalInputs"])
    paths.update(path for path in cli.parent.rglob("*") if path.is_file())
    for row in saved["rawSources"]:
        paths.update(Path(row[field]) for field in ("jsonPath", "rawPath"))
    snapshots = {str(path): (path.stat().st_size, path.stat().st_mtime_ns) for path in paths}
    report = audit_selection(selection_path=selection_path, summary_path=summary_path,
                             ledger_path=ledger_path, expected_input_set=saved["inputSetSha256"],
                             work_root=report_path.parent, cli=cli, reuse_path=report_path, receipt_root=root)
    if report["status"] != "complete" or report["failures"]:
        raise ValueError(f"scene receipt reanalysis failed: {report['failures'][:3]}")
    if report_path.read_bytes() != original:
        raise ValueError("scene receipt changed during reanalysis")
    report["currentInputSnapshots"] = snapshots
    check_receipt_snapshot(report)
    return report


def check_receipt_snapshot(report: dict) -> None:
    """Guard the revalidated source set until its consumer finishes."""
    for filename, expected in report["currentInputSnapshots"].items():
        stat = Path(filename).stat()
        if (stat.st_size, stat.st_mtime_ns) != tuple(expected):
            raise ValueError(f"scene receipt input changed during consumption: {filename}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--outer-summary", type=Path, required=True)
    parser.add_argument("--outer-ledger", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--work-root", type=Path, default=REPO_ROOT/"tmp/animestudio/collision_ownership")
    parser.add_argument("--output-json", type=Path, default=REPO_ROOT/"reports/assets/collision_scene_current.json")
    parser.add_argument("--reuse-extraction", type=Path,
                        help="Reanalyse a saved scene-corpus extraction after revalidating its current source/CLI/raw receipt.")
    args = parser.parse_args(argv)
    destination = args.output_json
    try:
        report = audit_selection(selection_path=args.selection, summary_path=args.outer_summary,
                                 ledger_path=args.outer_ledger, expected_input_set=args.expected_input_set_sha256,
                                 work_root=args.work_root, cli=args.cli, reuse_path=args.reuse_extraction)
    except (ValueError, KeyError, TypeError, OSError) as error:
        report = dict(schema="endfield.selected-unity-scene-corpus.v4", status="failed",
                      failures=[dict(check="source_gate", detail=str(error)[:1200])])
        # Preserve the extraction receipt needed for a later authenticated
        # retry. A gate failure never replaces it with an unusable shell.
        if args.reuse_extraction is not None and destination.resolve() == args.reuse_extraction.resolve():
            destination = destination.with_name(destination.stem+".failed"+destination.suffix)
    atomic_write_text(destination, json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(dict(status=report["status"], counts=report.get("counts"),
                          failures=report["failures"][:3], report=str(destination)), ensure_ascii=False), flush=True)
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
