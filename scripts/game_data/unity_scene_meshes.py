"""Compose admitted scene references with a separately admitted Mesh corpus.

No extraction runs. A referring raw Mesh PPtr and its serialized external slot
must select one physical CAB in the combined source set. Complete raw/cooked
checks precede ownership; names, preloads and bare PathIDs never select a Mesh.
The result has its own schema because its Mesh scope extends the scene census.


Evidence and admission boundary
-------------------------------
Exact raw/cooked target checks require both selections from the same current
input set. The referring PPtr, exact external slot and unique physical CAB are
mandatory; missing or ambiguous targets stay unresolved. This extends only
the Mesh join, not scene-body census. Stored assemblies keep each collider as
a separate part and compose root and descendant TRS under a physical root;
disabled definitions are included, while unadmitted primitive/custom bodies
and live physics remain outside scope.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.game_data.cooked_collision import read_triangle_mesh
from scripts.game_data.cooked_convex import read_convex_mesh
from scripts.game_data.cooked_collision_corpus import check_receipt_snapshot as check_mesh_snapshot, receipt_payloads
from scripts.game_data.unity_scene import read_scene_object, scene_identity
from scripts.game_data.unity_scene_corpus import check_receipt_snapshot, _check_typed, _external_mesh_target

SCHEMA = "endfield.stored-collider-mesh-joins.v1"


def join_mesh_receipt(scene: dict, meshes: dict) -> dict:
    """Compose current receipt admissions while retaining both source scopes."""
    if (scene.get("schema") != "endfield.selected-unity-scene-corpus.v4"
            or meshes.get("schema") not in ("endfield.cooked-collision-selected-corpus.v1",
                                           "endfield.cooked-collision-selected-corpus.v2")
            or scene.get("status") != "complete" or meshes.get("status") != "complete"
            or scene.get("failures") or meshes.get("failures")
            or scene["inputSetSha256"] != meshes["inputSetSha256"]):
        raise ValueError("scene/Mesh receipt schemas, admission or current input sets differ")
    check_receipt_snapshot(scene)
    check_mesh_snapshot(meshes)
    targets = {scene_identity(row["identity"]): row for row in meshes["objects"]}
    if len(targets) != len(meshes["objects"]):
        raise ValueError("Mesh receipt has duplicate physical identities")
    sources = {scene_identity(row["identity"]): row for row in scene["rawSources"]}
    for key, mesh in targets.items():
        source = sources.get(key)
        if source is not None and (source["type"] != "Mesh" or source["rawSha256"] != mesh["rawSha256"]):
            raise ValueError(f"scene/Mesh receipts disagree on physical object: {mesh['identity']}")
    sources.update(targets)
    checked, joined, counts = {}, [], Counter()
    for source_row in scene["colliders"]:
        if source_row["status"] != "mesh_external_unresolved":
            joined.append(source_row)
            continue
        collider = source_row["collider"]
        key = scene_identity(collider["identity"])
        raw = Path(collider["rawPath"]).read_bytes()
        typed = Path(collider["jsonPath"]).read_bytes()
        if (len(raw) != collider["byteSize"] or hashlib.sha256(raw).hexdigest() != collider["rawSha256"]
                or hashlib.sha256(typed).hexdigest().upper() != collider["jsonSha256"]):
            raise ValueError(f"referring MeshCollider bytes changed: {collider['jsonPath']}")
        document = json.loads(typed.decode("utf-8-sig"))
        if scene_identity(document["$animestudio"]) != key:
            raise ValueError(f"referring MeshCollider identity changed: {collider['jsonPath']}")
        body = read_scene_object("MeshCollider", raw)
        _check_typed(body, document, "MeshCollider")
        row = dict(source_row)
        try:
            target = _external_mesh_target(key, body["mesh"], document["$animestudio"], sources)
        except ValueError as error:
            row["diagnostic"] = str(error)[:800]
            counts["externalUnresolved"] += 1
            joined.append(row)
            continue
        mesh = targets.get(target)
        if mesh is None:
            counts["externalUnresolved"] += 1
            joined.append(row)
            continue
        if target not in checked:
            geometry = []
            for kind, payload, item in receipt_payloads(mesh):
                if kind == "triangle":
                    decoded = read_triangle_mesh(payload)
                    vertices, faces = len(decoded.geometry.vertices), len(decoded.geometry.triangles)
                else:
                    decoded = read_convex_mesh(payload)
                    vertices, faces = len(decoded.vertices), len(decoded.polygons)
                if (vertices != item["vertexCount"]
                        or faces != item.get("triangleCount", item.get("polygonCount"))
                        or decoded.metadata["bytesConsumed"] != len(payload)):
                    raise ValueError(f"external Mesh complete geometry differs: {mesh['jsonPath']}")
                geometry.append(item)
            checked[target] = geometry
        kind = "convex" if body["convex"] else "triangle"
        row["trace"] = dict(row["trace"], mesh=target, meshPointerStatus="external_serialized_target")
        row["mesh"] = {field: mesh[field] for field in (
            "identity", "name", "rawSha256", "collisionOnly", "baked", "convex", "renderVertexCount")}
        row["geometry"] = [item for item in checked[target] if item["kind"] == kind]
        row["status"] = "exact_serialized_collider_link" if row["geometry"] else "mesh_has_no_selected_cooked_buffer"
        counts["externalResolved"] += 1
        joined.append(row)
    check_receipt_snapshot(scene)
    check_mesh_snapshot(meshes)
    return dict(schema=SCHEMA, status="complete", failures=[], inputSetSha256=scene["inputSetSha256"],
                colliders=joined, counts=dict(counts),
                sourceScopes=dict(sceneSelection=scene["selection"], meshSelection=meshes["selection"]),
                evidenceBoundary="Exact stored external Mesh pointer/slot and unique physical CAB across two current admitted source selections; complete cooked geometry and existing reciprocal prefab hierarchy. Scene-body coverage is unchanged. Runtime instances, activation, world placement and solver use remain unresolved.")
