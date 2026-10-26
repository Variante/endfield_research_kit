"""Publish separate collision previews from an authenticated selected corpus.

The raw-format readers own decoding. This module owns the Assets projection:
local-coordinate OBJ files, exact serialized identity and a default-hidden tag.
It never replaces render Mesh exports or adds name-based material bindings.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from scripts.common import rel_path
from scripts.game_data.cooked_collision import read_triangle_mesh, write_obj
from scripts.game_data.cooked_convex import read_convex_mesh, write_convex_obj
from scripts.game_data.cooked_collision_corpus import check_receipt_snapshot, receipt_payloads, validate_receipt


COLLISION_SOURCE = "Collision"


def publish_collision_previews(receipt_path: Path, *, root: Path, asset_dir: Path,
                               summary_path: Path | None = None) -> dict:
    """Stage the full admitted selection before returning any index entries.

    Missing optional evidence produces no collision rows. A failed current gate
    or object check also produces none, with a bounded diagnostic; callers must
    publish that state instead of retaining rows from a previous build.
    """
    if not receipt_path.is_file():
        return {"status": "missing", "entries": [], "diagnostic": "No selected collision corpus receipt."}
    stage = None
    try:
        receipt_bytes = receipt_path.read_bytes()
        receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
        report = validate_receipt(receipt_path, summary_path=summary_path)
        output_root = asset_dir.resolve() / "collision"
        output_root.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix="selection-", dir=output_root))
        entries, counts = [], Counter()
        for row in report["objects"]:
            identity = row["identity"]
            # The file name includes physical identity, so equal names/PathIDs
            # in distinct CABs cannot overwrite or form misleading variants.
            physical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
            key = hashlib.sha256(physical.encode("utf-8")).hexdigest()[:24]
            pid = f"{identity['pathId'] & ((1 << 64) - 1):016X}"
            name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", row["name"]).strip(" .")[:120] or "Mesh"
            for kind, payload, item in receipt_payloads(row):
                filename = f"{key}_{name}_p{pid}.obj"
                destination = stage / kind / filename
                if kind == "triangle":
                    mesh = read_triangle_mesh(payload)
                    vertices, faces = len(mesh.geometry.vertices), len(mesh.geometry.triangles)
                    write_obj(destination, mesh.geometry, complete=mesh)
                else:
                    mesh = read_convex_mesh(payload)
                    vertices, faces = len(mesh.vertices), len(mesh.polygons)
                    write_convex_obj(destination, mesh)
                if (vertices != item["vertexCount"] or faces != item.get("triangleCount", item.get("polygonCount"))
                        or mesh.metadata["bytesConsumed"] != len(payload)):
                    raise ValueError(f"decoded collision geometry differs from receipt: {row['name']} / {kind}")
                obj = destination.read_bytes()
                entries.append({
                    "k": "model", "r": f"{COLLISION_SOURCE}/{kind}/{filename}", "n": row["name"],
                    "s": len(obj), "pid": pid, "h": hashlib.sha256(obj).hexdigest(),
                    "c": row.get("container") or "", "cl": {
                        "kind": kind, "key": f"{key}:{kind}", "vertexCount": vertices, "faceCount": faces,
                        "identity": {**identity, "pathId": str(identity["pathId"]),
                                     "sourceOffset": str(identity["sourceOffset"])},
                        "bufferSha256": item["sha256"], "bufferBytes": item["byteCount"],
                        "rawSha256": row["rawSha256"], "collisionOnly": row["collisionOnly"],
                        "baked": row["baked"], "convex": row["convex"],
                    },
                })
                counts[kind] += 1
        if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != receipt_sha:
            raise ValueError("collision receipt changed during publication")
        check_receipt_snapshot(report)
        # A changing export selection never silently leaves old rows current.
        expected = sum(len(row["payloads"]) for row in report["objects"])
        if len(entries) != expected:
            raise ValueError(f"collision geometry coverage differs: {len(entries)}/{expected}")
        return {"status": "validated", "entries": entries, "sourceRoot": rel_path(stage, root),
                "receiptSha256": receipt_sha, "inputSetSha256": report["inputSetSha256"],
                "selectedCount": report["selectedCount"], "noCookedData": report["counts"].get("noCookedData", 0),
                "counts": dict(counts), "scope": {
                    "primaryAssets": report["provenance"]["primaryAssets"],
                    "fallbackAssets": report["provenance"]["fallbackAssets"],
                    "auditBlocks": report["provenance"]["auditBlocks"],
                }, "coordinates": "Unity mesh local coordinates and original cooked winding; no scene transform.",
                "evidenceBoundary": "Exact stored collision geometry for the selected serialized identities. Sampled runtime evidence, when admitted, is published separately; previews have no scene transform."}
    except (ValueError, KeyError, TypeError, OSError) as error:
        if stage is not None:
            # mkdtemp returned this directory directly below the owned root.
            if stage.resolve().parent != (asset_dir.resolve()/"collision"):
                raise RuntimeError("collision staging directory escaped its output root") from error
            shutil.rmtree(stage)
        return {"status": "unavailable", "entries": [], "diagnostic": str(error)[:1200]}


def add_collision_publication(payload: dict, publication: dict) -> None:
    """Extend only the broad Assets index; geometry has its own source root."""
    payload["collision"] = {key: value for key, value in publication.items() if key not in ("entries", "sourceRoot")}
    entries = publication["entries"]
    if not entries:
        return
    payload["entries"] = [*payload["entries"], *entries]
    payload["sourceRoots"][COLLISION_SOURCE] = publication["sourceRoot"]
    payload["counts"]["total"] += len(entries)
    payload["counts"]["model"] += len(entries)
