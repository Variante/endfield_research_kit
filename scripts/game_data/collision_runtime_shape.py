"""Prove Collider -> PxShape -> source-bound triangle cache from saved windows.

No game attachment. Recompute the Mesh cache comparison and authenticate the
Collider/shape native consumers. Missing same-call shape windows preserve only
the observed Collider member, without borrowing later fields from another epoch.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data import collision_runtime_mesh as mesh
from scripts.game_data.collision_runtime_mesh_native import load_layout
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text

SCHEMA = "endfield.collision-runtime-shape-comparison.v1"
NATIVE_SCHEMA = "endfield.collision-runtime-shape-native-contract.v1"
CONTRACT = CONTRACTS_DIR / "collision_runtime_shape_native.json"


def decode_attachment(view, collider, player_base, contract, cache):
    """Read only authenticated native fields; withhold unavailable shape fields."""
    owner, shape, geometry = (contract["layout"][name] for name in ("collider", "shape", "geometry"))
    mesh._require(view.scalar(collider, "Q", "collider.vtable") == player_base+owner["vtableRva"], "MeshCollider vtable")
    pointer = view.scalar(collider+owner["shape"], "Q", "collider.currentShape")
    result = dict(status="no_shape" if not pointer else "shape_member_only", colliderAddress=f"{collider:016x}",
                  shapeAddress=f"{pointer:016x}", reads=view.reads)
    if not pointer:
        return result
    try:
        mesh._require(view.scalar(pointer, "Q", "shape.vtable") == player_base+shape["vtableRva"], "PxShape vtable")
        result.update(status="typed_shape", concreteType=contract["typeName"]["ascii"])
        # The native getter checks the inline type even on the buffered path.
        kind = view.scalar(pointer+shape["inlineGeometry"], "I", "shape.geometryType")
        mesh._require(kind == geometry["triangleType"], "shape is not triangle geometry")
        flags = view.scalar(pointer+shape["bufferFlags"], "B", "shape.bufferFlagsLowByte")
        address = pointer+shape["inlineGeometry"]
        buffered = bool(flags & shape["geometryBufferedMask"])
        if buffered:
            buffer = view.scalar(pointer+shape["bufferPointer"], "Q", "shape.bufferPointer")
            mesh._require(buffer != 0, "null buffered geometry")
            address = buffer+shape["bufferedGeometry"]
        mesh._require(view.scalar(address, "I", "geometry.selectedType") == geometry["triangleType"], "selected geometry type differs")
        held = view.scalar(address+geometry["triangleMesh"], "Q", "geometry.triangleMesh")
        mesh._require(held == cache, "shape triangle Mesh differs from same-call Mesh-held cache")
        result.update(status="attachment_matched", geometryType=kind, geometryBuffered=buffered,
                      cacheAddress=f"{held:016x}", geometryAddress=f"{address:016x}")
    except mesh.WindowGap as exc:
        result["detail"] = str(exc)
        return result
    # Actor association and flags are independent of the triangle-cache claim.
    auxiliary = []
    for label in ("actor", "flags"):
        try:
            if label == "actor":
                value = view.scalar(pointer+shape["actor"], "Q", "shape.actor")
                auxiliary.append(dict(field=label, status="observed", address=f"{value:016x}",
                                      boundary="direct: getActor association; scene membership/contact participation unresolved"))
            else:
                flags_address = pointer+shape["inlineFlags"]
                buffered_flags = bool(flags & shape["flagsBufferedMask"])
                if buffered_flags:
                    buffer = view.scalar(pointer+shape["bufferPointer"], "Q", "shape.flagsBufferPointer")
                    mesh._require(buffer != 0, "null buffered shape flags")
                    flags_address = buffer+shape["bufferedFlags"]
                value = view.scalar(flags_address, "B", "shape.flags")
                auxiliary.append(dict(field=label, status="observed", value=value, buffered=buffered_flags,
                                      namedBits={name: bool(value & bit) for name, bit in contract["representation"]["shapeFlags"].items()},
                                      boundary=contract["representation"]["flagBoundary"]))
        except (mesh.WindowGap, ValueError) as exc:
            auxiliary.append(dict(field=label, status="unavailable", detail=str(exc)))
    result["auxiliary"] = auxiliary
    return result


def compare(root, raw_mesh_path, cooked_path, *, game_root=None, reinspect=False):
    result = dict(schema=SCHEMA, status="failed", session=str(root.resolve()), samples=[], diagnostics=[])
    try:
        # Reuse session admission, but recompute geometry rather than trusting a
        # cached interpretation. Preserve every per-read time in the join.
        geometry = mesh.compare(root, raw_mesh_path, cooked_path, game_root=game_root, reinspect=reinspect)
        mesh._require(geometry["status"] in ("validated", "partial"), "Mesh comparison failed:"+repr(geometry["diagnostics"]))
        admission, profile, receipt, samples = mesh.load_admission(root, game_root=game_root)
        mesh._require(admission["journalSha256"] == geometry["journalSha256"] and
                      admission["nativeMemory"]["sha256"] == geometry["archiveSha256"] and
                      sha256_file(root/"private/collision-build.json") == geometry["profileSha256"], "capture changed between comparisons")
        files = profile["files"]
        directory = game_root.parent if game_root and game_root.name == "Endfield_Data" else game_root
        paths = {name: directory/row["relativePath"] if directory else Path(row["path"]) for name, row in files.items()}
        contract, gate = load_layout(gameassembly=paths["gameAssembly"], metadata=paths["metadata"], unityplayer=paths["unityPlayer"],
                                     contract_path=CONTRACT, schema=NATIVE_SCHEMA, validator="collision_runtime_shape_native")
        result["nativeGate"] = gate
        mesh._require(contract is not None, "shape native layout:"+gate["status"]+":"+gate.get("detail", ""))
        mesh._require(contract["nativeInputs"] == geometry["nativeGate"]["nativeInputs"], "shape/cache native build differs")
        archive = (root/"native-memory.bin").read_bytes()
        mesh._require(mesh._sha(archive) == geometry["archiveSha256"], "archive changed before shape reads")
        by_call = {s["call"]: s for s in samples}
        windows = admission["nativeMemory"]["windows"]
        for cache in geometry["samples"]:
            sample = by_call[cache["call"]]
            row = dict(call=cache["call"], originChildCall=cache["originChildCall"], completedStepOrdinal=cache["completedStepOrdinal"],
                       colliderPointer=sample["colliderPointer"], objectInstanceId=sample["objectInstanceId"],
                       meshPointer=sample["meshPointer"], meshInstanceId=sample["meshInstanceId"], sourceMode=cache["sourceMode"])
            view = None
            try:
                roots = [w for w in windows if w["call"] == sample["call"] and w["role"] == "collider" and w["depth"] == 0]
                mesh._require(len(roots) == 1, "missing/ambiguous native Collider root")
                row["colliderAddress"] = roots[0]["address"]
                view = mesh.WindowView(windows, archive, call=sample["call"], root=roots[0]["root"], role="collider")
                if cache["status"] != "matched":
                    detail = f"same-call cache comparison {cache['status']}:"+cache.get("detail", "unspecified")[:1000]
                    if cache["status"] == "unavailable":
                        raise mesh.WindowGap(detail)
                    raise ValueError(detail)
                row.update(decode_attachment(view, int(roots[0]["address"], 16), mesh._le_pointer(receipt["playerBase"]), contract, int(cache["cacheAddress"], 16)))
            except (ValueError, KeyError, TypeError, struct.error) as exc:
                row.update(status="unavailable" if isinstance(exc, mesh.WindowGap) else "rejected", detail=str(exc), reads=view.reads if view else [])
            # Same call links separately timed roots, never an atomic snapshot.
            row["cacheComparison"] = cache
            result["samples"].append(row)
        matched = [s for s in result["samples"] if s["status"] == "attachment_matched"]
        rejected = [s for s in result["samples"] if s["status"] in ("rejected", "no_shape")]
        mesh._require(result["samples"], "no source-bound samples")
        epochs = {str(epoch): dict(Counter(s["status"] for s in result["samples"] if s["completedStepOrdinal"] == epoch))
                  for epoch in sorted({s["completedStepOrdinal"] for s in result["samples"]})}
        stable = []
        for initial in [s for s in result["samples"] if s["completedStepOrdinal"] == 0]:
            related = [s for s in result["samples"] if s["originChildCall"] == initial["call"]]
            stable.append(dict(originChildCall=initial["call"], shapeAddress=initial.get("shapeAddress"),
                               sampledMemberUnchanged=all(s.get("shapeAddress") == initial.get("shapeAddress") and
                                                          s.get("colliderAddress") == initial.get("colliderAddress") for s in related),
                               calls=[s["call"] for s in related], boundary="conditional: sampled held members only; no continuous shape lifetime claim"))
        result.update(status="rejected" if rejected else "validated" if len(matched) == len(result["samples"]) else "partial",
                      source=geometry["source"], meshNativeGate=geometry["nativeGate"],
                      journalSha256=geometry["journalSha256"], archiveSha256=geometry["archiveSha256"], profileSha256=geometry["profileSha256"],
                      sampleCoverage=dict(Counter(s["status"] for s in result["samples"])), epochCoverage=epochs,
                      uniqueMatchedShapes=len({s["shapeAddress"] for s in matched}), uniqueMatchedCaches=len({s["cacheAddress"] for s in matched}),
                      sampledShapeMembers=stable, evidenceBoundary=contract["evidenceBoundary"],
                      remainingGaps=["Missing same-call shape fields stay unavailable; stable held pointers do not fill later geometry/flag observations.",
                                     "No atomic snapshot, continuous shape lifetime, actor scene membership, collision pair or contact result."])
        mesh._require(sha256_file(root/"events.jsonl") == result["journalSha256"] and
                      sha256_file(root/"native-memory.bin") == result["archiveSha256"] and
                      sha256_file(root/"private/collision-build.json") == result["profileSha256"], "capture changed during shape comparison")
        mesh._require(sha256_file(raw_mesh_path) == result["source"]["rawMeshSha256"] and
                      sha256_file(cooked_path) == result["source"]["cookedSha256"], "selected source changed during shape comparison")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, struct.error) as exc:
        result.update(status="failed", samples=[], diagnostics=[dict(check="runtime_shape_comparison", detail=str(exc)[:1600])])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--raw-mesh", type=Path, required=True)
    parser.add_argument("--cooked", type=Path, required=True)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--reinspect", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = mesh._output_path(args.output or args.session/"collected/runtime-shape-comparison.json")
    report = compare(args.session, args.raw_mesh, args.cooked, game_root=args.game_root, reinspect=args.reinspect)
    atomic_write_text(output, json.dumps(report, indent=2)+"\n")
    print(json.dumps(dict(status=report["status"], samples=report.get("sampleCoverage", {}), epochs=report.get("epochCoverage", {}),
                          diagnostics=report["diagnostics"], output=str(output))))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
