"""Assemble admitted cooked surfaces using stored Unity Transform chains.

This is a projection of selected MeshColliders, including inactive/disabled
definitions. It includes the root's stored TRS, not any live grid/parent matrix.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile

from scripts.common import rel_path
from scripts.game_data.cooked_collision import read_triangle_mesh
from scripts.game_data.cooked_convex import read_convex_mesh
from scripts.game_data.cooked_collision_corpus import receipt_payloads
from scripts.webui.assets.collision_runtime import object_key, variant_key

SCHEMA = "endfield.assets-collision-prefabs.v2"
SOURCE = "CollisionPrefab"
BOUNDARY = ("Selected stored MeshColliders and separately admitted BoxColliders, including disabled/inactive definitions. "
            "Coordinates compose the root and descendant stored TRS. Primitive and custom "
            "colliders other than the admitted boxes, unselected bodies, live grid/parent transforms, activation and world "
            "placement are not reconstructed.")


def transform_surface(vertices, faces, matrix):
    """Apply a finite row-major affine matrix, keeping reflected faces outward."""
    if (len(matrix) != 16 or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in matrix)
            or list(matrix[12:]) != [0, 0, 0, 1]):
        raise ValueError("stored collider Transform chain is not a finite affine matrix")
    a, b, c, _, d, e, f, _, g, h, i, *_ = matrix
    determinant = a * (e*i-f*h) - b * (d*i-f*g) + c * (d*h-e*g)
    if not math.isfinite(determinant) or determinant == 0:
        raise ValueError("stored collider Transform chain is singular")
    transformed = [tuple(sum(matrix[r*4+k]*vertex[k] for k in range(3)) + matrix[r*4+3]
                         for r in range(3)) for vertex in vertices]
    if any(not math.isfinite(value) for vertex in transformed for value in vertex):
        raise ValueError("stored collider Transform chain produced non-finite vertices")
    return transformed, [tuple(reversed(face)) if determinant < 0 else tuple(face) for face in faces]


def _root_key(trace):
    root = trace["chain"][-1]["gameObject"]
    return object_key(dict(sourceOriginalPath=root[0], sourceOffset=root[1], sourceFile=root[2], pathId=root[3]))


def box_surface(size, center):
    """Draw full stored box dimensions around its collider-local center."""
    if (len(size) != 3 or len(center) != 3 or any(not math.isfinite(v) for v in (*size, *center))
            or any(v <= 0 for v in size)):
        raise ValueError('stored box size/center is invalid')
    vertices = [tuple(center[k]+sign[k]*size[k]/2 for k in range(3)) for sign in
                ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    return vertices, ((0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5))


def publish_prefabs(entries: list[dict], reports: list[dict], corpus: dict, *, root: Path, asset_dir: Path,
                    box_report: dict | None = None) -> dict:
    """Stage assemblies from freshly admitted scene and cooked-Mesh receipts."""
    variants = {variant_key(e["cl"]): e for e in entries if "cl" in e}
    if len(variants) != sum("cl" in e for e in entries):
        raise ValueError("duplicate collision variant in prefab assembly")
    mesh_sources = {object_key(row["identity"]): row for row in corpus["objects"]}
    groups, decoded, observations = {}, {}, {}
    for report in reports:
        if report.get("status") != "complete" or report.get("failures"):
            raise ValueError("prefab assembly scene receipt did not validate")
        for row in report["colliders"]:
            if not row.get("prefabAssets"):
                continue
            trace = row["trace"]
            root_key = _root_key(trace)
            owner_key = object_key(row["collider"]["identity"])
            paths = sorted(set(p["path"] for p in row["prefabAssets"]))
            observation = (root_key, paths, row["collider"]["rawSha256"], trace, row["status"],
                           row.get("mesh"), row.get("geometry"))
            if owner_key in observations:
                if observations[owner_key] != observation:
                    raise ValueError("conflicting stored prefab collider observations")
                continue
            observations[owner_key] = observation
            group = groups.setdefault(root_key, dict(paths=set(), parts=[], missing=0))
            group["paths"].update(paths)
            if row["status"] != "exact_serialized_collider_link":
                group["missing"] += 1
                continue
            if len(row["geometry"]) != 1:
                raise ValueError("prefab collider does not select one cooked buffer")
            item = row["geometry"][0]
            key = (*object_key(row["mesh"]["identity"]), item["kind"], row["mesh"]["rawSha256"], item["sha256"])
            entry = variants.get(key)
            if entry is None:
                group["missing"] += 1
                continue
            if not any(object_key(owner["identity"]) == owner_key and set(paths).issubset(owner["prefabPaths"])
                       for owner in entry["cl"].get("authored", {}).get("owners", [])):
                raise ValueError("prefab assembly differs from admitted stored owner")
            if key not in decoded:
                source = mesh_sources.get(key[:4])
                if source is None or source["rawSha256"] != key[-2]:
                    raise ValueError("prefab assembly lacks admitted physical Mesh source")
                found = None
                for kind, payload, actual in receipt_payloads(source):
                    if kind != item["kind"]:
                        continue
                    if any(actual.get(field) != item.get(field) for field in
                           ("kind", "offset", "byteCount", "sha256", "vertexCount", "triangleCount", "polygonCount")):
                        raise ValueError("prefab assembly cooked buffer differs from admitted source")
                    mesh = read_triangle_mesh(payload) if kind == "triangle" else read_convex_mesh(payload)
                    vertices, faces = ((mesh.geometry.vertices, mesh.geometry.triangles) if kind == "triangle"
                                       else (mesh.vertices, mesh.polygons))
                    if (mesh.metadata["bytesConsumed"] != len(payload)
                            or len(vertices) != entry["cl"]["vertexCount"] or len(faces) != entry["cl"]["faceCount"]):
                        raise ValueError("prefab assembly decoded geometry dimensions differ")
                    found = (vertices, faces)
                if found is None:
                    raise ValueError("prefab assembly selected buffer is unavailable")
                decoded[key] = found
            vertices, faces = transform_surface(*decoded[key], trace["composedLocalMatrix"])
            group["parts"].append(dict(key=key, owner=owner_key, kind='mesh', vertices=vertices, faces=faces,
                                       enabled=trace["enabled"], active=all(n["active"] for n in trace["chain"])))
    unlinked_boxes, box_observations = 0, {}
    if box_report is not None:
        if (box_report.get('schema') != 'endfield.selected-unity-box-corpus.v1'
                or box_report.get('status') != 'complete' or box_report.get('failures')):
            raise ValueError('prefab assembly BoxCollider receipt did not validate')
        for row in box_report['boxes']:
            if row['status'] != 'exact_stored_box_link':
                raise ValueError('prefab assembly BoxCollider link is unresolved')
            trace = row['trace']; owner_key = object_key(row['collider']['identity'])
            if owner_key in observations:
                raise ValueError('one physical object cannot be a MeshCollider and a BoxCollider')
            if owner_key in box_observations:
                if box_observations[owner_key] != row:
                    raise ValueError('conflicting stored BoxCollider observations')
                continue
            box_observations[owner_key] = row
            root_key = _root_key(trace); group = groups.get(root_key)
            if group is None or not row['prefabPaths']:
                unlinked_boxes += 1
                continue
            if not set(row['prefabPaths']).issubset(group['paths']):
                raise ValueError('BoxCollider prefab paths differ from admitted assembly root')
            vertices, faces = transform_surface(*box_surface(trace['size'], trace['center']), trace['composedLocalMatrix'])
            identity = row['collider']['identity']
            public = dict(identity={**identity, 'pathId':str(owner_key[1]), 'sourceOffset':str(identity['sourceOffset'])},
                          rawSha256=row['collider']['rawSha256'], size=trace['size'], center=trace['center'],
                          enabled=trace['enabled'], isTrigger=trace['isTrigger'],
                          hierarchy=[dict(name=n['name'],active=n['active']) for n in reversed(trace['chain'])])
            group['parts'].append(dict(key=None, owner=owner_key, kind='box', vertices=vertices, faces=faces,
                                       enabled=trace['enabled'], active=all(n['active'] for n in trace['chain']), public=public))
    destination = asset_dir.resolve() / "collision_prefabs"
    destination.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="selection-", dir=destination))
    links, descriptors = defaultdict(list), []
    try:
        for root_key, group in sorted(groups.items()):
            if not group["parts"]:
                continue
            name = hashlib.sha256(json.dumps(root_key, separators=(",", ":")).encode("utf-8")).hexdigest() + ".obj"
            output = stage / name
            offset, face_count = 0, 0
            with output.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write("# " + BOUNDARY + "\n")
                for part in sorted(group["parts"], key=lambda p: p["owner"]):
                    stream.write(f"# enabled={part['enabled']} hierarchyActive={part['active']}\n")
                    stream.write(f"o {part['kind']}_collider_{part['owner'][0]}_{part['owner'][1]:016X}\n")
                    for vertex in part["vertices"]:
                        stream.write("v " + " ".join(format(value, ".17g") for value in vertex) + "\n")
                    for face in part["faces"]:
                        stream.write("f " + " ".join(str(index+offset+1) for index in face) + "\n")
                    offset += len(part["vertices"]); face_count += len(part["faces"])
            descriptor = dict(schema=SCHEMA, prefabPaths=sorted(group["paths"]),
                rootIdentity=dict(sourceOriginalPath=root_key[2], sourceOffset=str(root_key[3]),
                                  sourceFile=root_key[0], pathId=str(root_key[1])),
                rel=f"{SOURCE}/{name}", sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                colliderCount=len(group["parts"]), selectedMissingCount=group["missing"],
                meshColliderCount=sum(p['kind']=='mesh' for p in group['parts']),
                boxColliderCount=sum(p['kind']=='box' for p in group['parts']),
                boxParts=[p['public'] for p in group['parts'] if p['kind']=='box'],
                storedDisabledCount=sum(not p["enabled"] for p in group["parts"]),
                storedInactiveCount=sum(not p["active"] for p in group["parts"]),
                vertexCount=offset, faceCount=face_count)
            descriptors.append(descriptor)
            for key in {part["key"] for part in group["parts"] if part['key'] is not None}:
                links[key].append(descriptor)
        for entry in entries:
            if "cl" in entry:
                entry["cl"].pop("prefabs", None)
        for key, rows in links.items():
            variants[key]["cl"]["prefabs"] = dict(schema=SCHEMA, assemblies=rows)
        return dict(schema=SCHEMA, status="validated", sourceRoot=rel_path(stage, root),
                    counts=dict(assemblies=len(descriptors), linkedVariants=len(links),
                                colliderParts=sum(d["colliderCount"] for d in descriptors),
                                boxColliderParts=sum(d['boxColliderCount'] for d in descriptors), unlinkedBoxColliders=unlinked_boxes,
                                selectedMissing=sum(d["selectedMissingCount"] for d in descriptors)),
                    evidenceBoundary=BOUNDARY)
    except BaseException:
        # Only the exact mkdtemp directory below this owned output is removed.
        shutil.rmtree(stage)
        raise
