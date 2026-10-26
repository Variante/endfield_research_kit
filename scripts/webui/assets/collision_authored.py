"""Publish exact stored collider/prefab owners beside collision previews.

These are authored components and reciprocal Transform chains. They do not
identify a live instance, prove activation, or change mesh-local previews.
Saved scene reports supply input paths only; their joins are recomputed.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.common import rel_path, write_json
from scripts.game_data import unity_scene_corpus
from scripts.game_data import unity_box_corpus
from scripts.game_data import unity_render_corpus
from scripts.game_data import unity_source_directory_corpus,unity_render_resources
from scripts.webui.assets import collision_render_assets
from scripts.webui.assets.collision_renderers import project_renderers, SCHEMA as RENDER_SCHEMA
from scripts.game_data.unity_scene_meshes import join_mesh_receipt, SCHEMA as JOIN_SCHEMA
from scripts.game_data.cooked_collision_corpus import check_receipt_snapshot, validate_receipt
from scripts.webui.assets.collision_runtime import object_key, variant_key
from scripts.webui.assets.collision_models import apply_model_sources, SCHEMA as MODEL_SCHEMA
from scripts.webui.assets.collision_prefabs import publish_prefabs, SCHEMA as PREFAB_SCHEMA, SOURCE as PREFAB_SOURCE

SELECTION_SCHEMA = "endfield.assets-collision-authored-selection.v5"
PROJECTION_SCHEMA = "endfield.assets-collision-authored.v1"


def _public_identity(identity: dict) -> dict:
    object_key(identity)
    return {**identity, "pathId": str(identity["pathId"]), "sourceOffset": str(identity["sourceOffset"])}


def project_owners(entries: list[dict], reports: list[dict]) -> dict:
    """Stage exact physical Mesh/hash/kind joins from freshly admitted reports."""
    variants = {}
    for entry in entries:
        if "cl" in entry:
            key = variant_key(entry["cl"])
            if key in variants:
                raise ValueError("duplicate physical collision variant in Assets")
            variants[key] = entry
    groups, owners, statuses = {}, {}, Counter()
    unmatched = set()
    for report in reports:
        if (report.get("schema") not in ("endfield.selected-unity-scene-corpus.v4", JOIN_SCHEMA)
                or report.get("status") != "complete" or report.get("failures")):
            raise ValueError("authored scene audit did not validate")
        for row in report["colliders"]:
            collider_key = object_key(row["collider"]["identity"])
            # Deduplicate overlapping selections without hiding a conflicting
            # observation of one physical stored component.
            if collider_key in owners:
                if owners[collider_key] != row:
                    # Extraction paths can differ, but proved semantic fields
                    # and raw hashes must agree for the same stored component.
                    previous = owners[collider_key]
                    fields = ("status", "trace", "mesh", "geometry")
                    if (previous["collider"]["rawSha256"] != row["collider"]["rawSha256"]
                            or any(previous.get(f) != row.get(f) for f in fields)
                            or [p["path"] for p in previous.get("prefabAssets", [])]
                            != [p["path"] for p in row.get("prefabAssets", [])]):
                        raise ValueError("conflicting stored collider observations")
                continue
            owners[collider_key] = row
            statuses[row["status"]] += 1
            if row["status"] != "exact_serialized_collider_link":
                continue
            mesh, trace = row["mesh"], row["trace"]
            mesh_key = object_key(mesh["identity"])
            target = trace["mesh"]
            if (target is None or mesh_key != object_key(dict(sourceOriginalPath=target[0],
                    sourceOffset=target[1], sourceFile=target[2], pathId=target[3]))
                    or trace["meshPointerStatus"] not in ("local", "external_serialized_target")):
                raise ValueError("authored collider Mesh target differs from physical source")
            if len(row["geometry"]) != 1:
                raise ValueError("authored collider must select exactly one cooked buffer")
            geometry = row["geometry"][0]
            kind = "convex" if trace["convex"] else "triangle"
            if geometry["kind"] != kind:
                raise ValueError("authored collider convex flag differs from cooked buffer kind")
            key = (*mesh_key, kind, mesh["rawSha256"], geometry["sha256"])
            if key not in variants:
                unmatched.add(collider_key)
                continue
            collision = variants[key]["cl"]
            if (collision["vertexCount"] != geometry["vertexCount"]
                    or collision["faceCount"] != geometry.get("triangleCount", geometry.get("polygonCount"))
                    or collision["bufferBytes"] != geometry["byteCount"]):
                raise ValueError("authored collider/Assets geometry dimensions differ")
            owner = dict(identity=_public_identity(row["collider"]["identity"]),
                         rawSha256=row["collider"]["rawSha256"],
                         prefabPaths=sorted(set(p["path"] for p in row.get("prefabAssets", []))),
                         hierarchy=[dict(name=node["name"], active=node["active"])
                                    for node in reversed(trace["chain"])],
                         enabled=trace["enabled"], meshPointerStatus=trace["meshPointerStatus"])
            groups.setdefault(key, []).append(owner)
    # All joins have succeeded before any prior claim is replaced.
    for entry in entries:
        if "cl" in entry:
            entry["cl"].pop("authored", None)
    for key, rows in groups.items():
        variants[key]["cl"]["authored"] = dict(schema=PROJECTION_SCHEMA, owners=rows)
    return dict(schema=PROJECTION_SCHEMA, status="validated", counts=dict(
        linkedVariants=len(groups), linkedColliders=sum(map(len, groups.values())),
        prefabLinkedVariants=sum(any(r["prefabPaths"] for r in rows) for rows in groups.values()),
        unmatchedColliders=len(unmatched), colliderStatuses=dict(statuses)),
        evidenceBoundary="Exact stored MeshCollider pointers, convex selection, reciprocal hierarchy and AssetBundle prefab roots. Stored enabled/active flags describe authored configuration; live instantiation, activation, world placement and solver use remain unresolved. Previews stay in mesh local coordinates.")


def apply_authored_publication(payload: dict, *, root: Path, selection_path: Path,
                              corpus_path: Path, receipts: list[Path] | None = None,
                              summary_path: Path | None = None, model_receipt: Path | None = None,
                              game_root: Path | None = None, asset_dir: Path | None = None,
                              box_receipt: Path | None = None, render_receipt: Path | None = None,
                              render_resource_receipts: list[Path] | None = None) -> dict:
    """Refresh owner metadata without extracting or changing stored geometry."""
    for entry in payload["entries"]:
        if "cl" in entry:
            entry["cl"].pop("authored", None)
            entry["cl"].pop("models", None)
            entry["cl"].pop("prefabs", None)
            entry["cl"].pop("renderers", None)
    payload.setdefault("sourceRoots", {}).pop(PREFAB_SOURCE, None)
    payload['sourceRoots'].pop(collision_render_assets.SOURCE,None)
    evidence = dict(schema=PROJECTION_SCHEMA, status="missing",
                    diagnostic="No selected authored collision scene receipt.")
    try:
        selection_bytes = None
        if receipts is not None:
            if not selection_path.resolve().is_relative_to((root / "reports").resolve()):
                raise ValueError("generated authored selections must stay under reports/")
            selection = dict(schema=SELECTION_SCHEMA, receipts=[rel_path(p.resolve(), root) for p in receipts])
            if model_receipt is not None:
                selection["modelReceipt"] = rel_path(model_receipt.resolve(), root)
            if box_receipt is not None:
                selection['boxReceipt'] = rel_path(box_receipt.resolve(), root)
            if render_receipt is not None:
                selection['renderReceipt'] = rel_path(render_receipt.resolve(), root)
            if render_resource_receipts is not None:
                selection['renderResourceReceipts']=[rel_path(p.resolve(),root) for p in render_resource_receipts]
        elif selection_path.is_file():
            selection_bytes = selection_path.read_bytes()
            selection = json.loads(selection_bytes)
        else:
            payload.setdefault("collision", {})["authored"] = evidence
            return evidence
        if (model_receipt is not None or box_receipt is not None or render_receipt is not None or render_resource_receipts is not None) and receipts is None:
            raise ValueError("select scene receipts alongside a new Model, BoxCollider or render component receipt")
        if selection.get("schema") != SELECTION_SCHEMA:
            raise ValueError("unsupported authored collision selection schema")
        paths = selection["receipts"]
        if not isinstance(paths, list) or not 1 <= len(paths) <= 8 or any(not isinstance(p, str) or not p for p in paths):
            raise ValueError("authored selection needs one to eight scene receipts")
        corpus_bytes = corpus_path.read_bytes()
        corpus = validate_receipt(corpus_path, summary_path=summary_path)
        if payload.get("collision", {}).get("receiptSha256") != hashlib.sha256(corpus_bytes).hexdigest():
            raise ValueError("Assets collision geometry publication differs from selected corpus")
        admitted = {(*object_key(row["identity"]), item["kind"], row["rawSha256"], item["sha256"]): item
                    for row in corpus["objects"] for item in row["payloads"]}
        for entry in payload["entries"]:
            if "cl" not in entry:
                continue
            collision = entry["cl"]
            geometry = admitted.get(variant_key(collision))
            if (geometry is None or geometry["vertexCount"] != collision["vertexCount"]
                    or geometry.get("triangleCount", geometry.get("polygonCount")) != collision["faceCount"]
                    or geometry["byteCount"] != collision["bufferBytes"]):
                raise ValueError("Assets collision variant differs from current corpus")
        reports = [unity_scene_corpus.validate_receipt(path, root=root)
                   for path in dict.fromkeys((root / p).resolve() for p in paths)]
        if any(r["inputSetSha256"] != corpus["inputSetSha256"] for r in reports):
            raise ValueError("authored scene and collision corpus input sets differ")
        joined_reports = [join_mesh_receipt(report, corpus) for report in reports]
        if selection_bytes is not None and selection_path.read_bytes() != selection_bytes:
            raise ValueError("authored selection changed during publication")
        if corpus_path.read_bytes() != corpus_bytes:
            raise ValueError("collision corpus receipt changed during authored publication")
        check_receipt_snapshot(corpus)
        for report in reports:
            unity_scene_corpus.check_receipt_snapshot(report)
        evidence = project_owners(payload["entries"], joined_reports)
        evidence["sourceJoins"] = [dict(counts=report["counts"], sourceScopes=report["sourceScopes"])
                                   for report in joined_reports]
        model_path = selection.get("modelReceipt")
        model_evidence = dict(schema=MODEL_SCHEMA, status="missing")
        if model_path is not None:
            try:
                if not isinstance(model_path, str) or not model_path:
                    raise ValueError("invalid selected Model receipt path")
                model_evidence = apply_model_sources(payload["entries"], receipt_path=root / model_path,
                    scenes=reports, joined_scenes=joined_reports, root=root, game_root=game_root,
                    export_root=root / payload["root"] if payload.get("root") else None)
            except (ValueError, KeyError, TypeError, OSError, OverflowError, RuntimeError) as error:
                for entry in payload["entries"]:
                    if "cl" in entry:
                        entry["cl"].pop("models", None)
                model_evidence = dict(schema=MODEL_SCHEMA, status="unavailable", diagnostic=str(error)[:1200])
        evidence["models"] = model_evidence
        box_path = selection.get('boxReceipt'); box_report = None
        box_evidence = dict(schema=unity_box_corpus.SCHEMA, status='missing')
        if box_path is not None:
            try:
                if not isinstance(box_path, str) or not box_path:
                    raise ValueError('invalid selected BoxCollider receipt path')
                candidate = root/box_path
                box_source = json.loads(candidate.read_bytes())['sceneReceipt']
                base = next((r for r in reports if box_source in r['currentInputSnapshots']), None)
                if base is None:
                    raise ValueError('BoxCollider receipt needs its admitted base scene selection')
                box_report = unity_box_corpus.validate_receipt(candidate, base)
                box_evidence = dict(schema=unity_box_corpus.SCHEMA, status='validated', counts=box_report['counts'])
            except (ValueError, KeyError, TypeError, OSError, OverflowError) as error:
                box_evidence = dict(schema=unity_box_corpus.SCHEMA, status='unavailable', diagnostic=str(error)[:1200])
        evidence['boxes'] = box_evidence
        try:
            prefab_evidence = publish_prefabs(payload["entries"], joined_reports, corpus,
                root=root, asset_dir=asset_dir or root / "webui/data/assets", box_report=box_report)
            if box_report is not None:
                try:
                    unity_scene_corpus.check_receipt_snapshot(box_report)
                except (ValueError, OSError) as error:
                    evidence['boxes'] = dict(schema=unity_box_corpus.SCHEMA, status='unavailable', diagnostic=str(error)[:1200])
                    raise
        except (ValueError, KeyError, TypeError, OSError, OverflowError) as error:
            for entry in payload['entries']:
                if 'cl' in entry:
                    entry['cl'].pop('prefabs', None)
            prefab_evidence = dict(schema=PREFAB_SCHEMA, status="unavailable", diagnostic=str(error)[:1200])
        evidence["prefabs"] = {k: v for k, v in prefab_evidence.items() if k != "sourceRoot"}
        render_path=selection.get('renderReceipt')
        render_evidence=dict(schema=RENDER_SCHEMA,status='missing')
        if render_path is not None:
            try:
                if not isinstance(render_path,str) or not render_path:
                    raise ValueError('invalid selected render component receipt path')
                candidate=root/render_path
                base_path=json.loads(candidate.read_bytes())['sceneReceipt']
                base=next((r for r in reports if base_path in r['currentInputSnapshots']),None)
                if base is None:raise ValueError('renderer receipt needs its admitted base scene selection')
                render_report=unity_render_corpus.validate_receipt(candidate,base)
                render_evidence=project_renderers(payload['entries'],joined_reports,render_report)
                unity_scene_corpus.check_receipt_snapshot(render_report)
                resource_paths=selection.get('renderResourceReceipts')
                if resource_paths is not None:
                    try:
                        if (not isinstance(resource_paths,list) or not 1<=len(resource_paths)<=8
                                or any(not isinstance(p,str) or not p for p in resource_paths)):
                            raise ValueError('render resource selection needs one to eight directory receipts')
                        source_reports=[];bodies={}
                        for p in resource_paths:
                            admitted,decoded=unity_source_directory_corpus.validate_receipt((root/p).resolve(),base,root=root)
                            source_reports.append(admitted)
                            for key,body in decoded.items():
                                if key in bodies and bodies[key]!=body:raise ValueError('conflicting decoded render resource bodies')
                                bodies[key]=body
                        resource_join=unity_render_resources.join_resources(base,render_report,source_reports,bodies)
                        resource_evidence,assemblies=collision_render_assets.publish(resource_join,bodies,root=root,asset_dir=asset_dir or root/'webui/data/assets',cli=Path(base['extraction']['command'][0]))
                        projected=project_renderers(payload['entries'],joined_reports,resource_join,assemblies=assemblies)
                        for admitted in source_reports:unity_scene_corpus.check_receipt_snapshot(admitted)
                        unity_scene_corpus.check_receipt_snapshot(render_report)
                        render_evidence=projected;render_evidence['resources']=resource_evidence
                        payload['sourceRoots'][collision_render_assets.SOURCE]=resource_evidence['sourceRoot']
                    except (ValueError,KeyError,TypeError,OSError,OverflowError) as error:
                        render_evidence=project_renderers(payload['entries'],joined_reports,render_report)
                        render_evidence['resources']=dict(status='unavailable',diagnostic=str(error)[:1200])
                        payload['sourceRoots'].pop(collision_render_assets.SOURCE,None)
            except (ValueError,KeyError,TypeError,OSError,OverflowError) as error:
                for entry in payload['entries']:
                    if 'cl' in entry:entry['cl'].pop('renderers',None)
                render_evidence=dict(schema=RENDER_SCHEMA,status='unavailable',diagnostic=str(error)[:1200])
        evidence['renderers']=render_evidence
        check_receipt_snapshot(corpus)
        for report in reports:
            unity_scene_corpus.check_receipt_snapshot(report)
        if prefab_evidence["status"] == "validated":
            payload["sourceRoots"][PREFAB_SOURCE] = prefab_evidence["sourceRoot"]
        if receipts is not None:
            write_json(selection_path, selection)
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as error:
        for entry in payload["entries"]:
            if "cl" in entry:
                entry["cl"].pop("authored", None)
                entry["cl"].pop("models", None)
                entry["cl"].pop("prefabs", None)
                entry["cl"].pop("renderers", None)
        payload["sourceRoots"].pop(PREFAB_SOURCE, None)
        payload['sourceRoots'].pop(collision_render_assets.SOURCE,None)
        evidence = dict(schema=PROJECTION_SCHEMA, status="unavailable", diagnostic=str(error)[:1200])
    payload.setdefault("collision", {})["authored"] = evidence
    return evidence
