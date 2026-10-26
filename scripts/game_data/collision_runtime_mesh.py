"""Decode pointer-bound Mesh physics caches from an admitted saved capture.

Uses one call/root at a time, a separately authenticated native layout, and an
exact CAB/PathID + raw/cooked hash join. Never stitches clipped arrays or epochs.
The report retains independent read times and auxiliary coverage gaps. Geometry
equivalence does not establish a PxShape attachment or a contact result.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data.collision_capture_inspect import _origin, _mesh_join, _floats, inspect
from scripts.game_data.collision_capture_memory import validate_archive
from scripts.game_data.collision_runtime_mesh_native import load_layout
from scripts.game_data.cooked_collision import read_triangle_mesh, write_obj
from scripts.game_data.corpus_common import atomic_write_text
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfield.collision-runtime-mesh-comparison.v1"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _le_pointer(text):
    raw = bytes.fromhex(text)
    _require(len(raw) == 8, "pointer width")
    return int.from_bytes(raw, "little")


class WindowGap(ValueError):
    pass


class WindowView:
    """Complete single-window reads with overlap checks in one sample only."""
    def __init__(self, windows, archive, *, call, root, role="sharedMesh"):
        self.windows = []
        self.reads = []
        for row in windows:
            if row["call"] != call or row["root"] != root or row["role"] != role:
                continue
            start, size = row["payloadOffset"], row["bytes"]
            raw = archive[start:start+size]
            _require(start >= 0 and len(raw) == size and _sha(raw) == row["sha256"], "window bytes/hash")
            self.windows.append((int(row["address"], 16), raw, row))

    def read(self, address, size, label):
        _require(0 < size <= 64*1024*1024 and 65536 <= address < 0x800000000000-size, "range bound:"+label)
        full = [(base, raw, row) for base, raw, row in self.windows if base <= address and address+size <= base+len(raw)]
        if not full:
            raise WindowGap(f"missing complete window:{label}:address={address:016x},bytes={size}")
        base, raw, chosen = min(full, key=lambda item: (item[2]["qpc"], item[2]["payloadOffset"]))
        result = raw[address-base:address-base+size]
        covering = []
        # Even a partial overlapping read can contradict this complete read.
        for other, data, row in self.windows:
            lo, hi = max(address, other), min(address+size, other+len(data))
            if lo < hi:
                if result[lo-address:hi-address] != data[lo-other:hi-other]:
                    raise WindowGap(f"conflicting captured windows:{label}:address={lo:016x},bytes={hi-lo}")
                covering.append(row["qpc"])
        self.reads.append(dict(field=label, address=f"{address:016x}", bytes=size, sha256=_sha(result),
                               selectedWindow=chosen["address"], qpc=chosen["qpc"], overlappingQpcRange=[min(covering), max(covering)]))
        return result

    def scalar(self, address, fmt, label):
        return struct.unpack("<"+fmt, self.read(address, struct.calcsize("<"+fmt), label))[0]


def decode_sample(view, native_root, player_base, contract, cooked, payload):
    """Core arrays fail closed; each optional auxiliary range has its own gap."""
    layout = contract["layout"]
    owner, triangle, tree = (layout[name] for name in ("mesh", "triangle", "tree"))
    _require(view.scalar(native_root, "Q", "mesh.vtable") == player_base+owner["vtableRva"], "Unity Mesh vtable")
    cache = view.scalar(native_root+owner["holderOffset"]+owner["heldTriangleOffset"], "Q", "mesh.heldTriangleMesh")
    _require(cache != 0, "Mesh has no held triangle cache")
    _require(view.scalar(cache, "Q", "cache.vtable") == player_base+triangle["vtableRva"], "PxBVH34TriangleMesh vtable")
    nv = view.scalar(cache+triangle["vertexCount"], "I", "cache.vertexCount")
    nt = view.scalar(cache+triangle["triangleCount"], "I", "cache.triangleCount")
    _require((nv, nt) == (len(cooked.geometry.vertices), len(cooked.geometry.triangles)),
             f"geometry counts:expected={len(cooked.geometry.vertices)}/{len(cooked.geometry.triangles)},actual={nv}/{nt}")
    flags = view.scalar(cache+triangle["flags"], "B", "cache.flags")
    width = 2 if flags & triangle["index16Mask"] else 4
    _require(width in contract["representation"]["triangleIndexWidths"], "unsupported native triangle width")
    vertex_ptr = view.scalar(cache+triangle["vertices"], "Q", "cache.vertices")
    triangle_ptr = view.scalar(cache+triangle["triangles"], "Q", "cache.triangles")
    vertices = view.read(vertex_ptr, nv*contract["representation"]["vertexStride"], "vertices")
    indices = view.read(triangle_ptr, nt*3*width, "triangles")
    spans = {span["field"]: payload[span["start"]:span["end"]] for span in cooked.spans}
    # Complete cooked reader accepts little-endian CPU BV4 only. Preserve floats
    # byte-for-byte rather than tolerating a numerical match or changed winding.
    _require(vertices == spans["mesh.vertices"], "vertex bytes differ from stored payload")
    flat = [value for tri in cooked.geometry.triangles for value in tri]
    decoded = struct.unpack("<"+str(nt*3)+("H" if width == 2 else "I"), indices)
    _require(list(decoded) == flat, "triangle indices/order differ from stored payload")
    result = dict(status="matched", concreteType=contract["typeName"]["ascii"], cacheAddress=f"{cache:016x}",
                  vertices=nv, triangles=nt, runtimeIndexWidth=width, storedIndexWidth=cooked.geometry.index_width,
                  geometrySha256=_sha(vertices+struct.pack("<"+str(len(flat))+"I", *decoded)),
                  runtimeBoundsCenter=list(struct.unpack("<3f", view.read(cache+triangle["boundsCenter"], 12, "bounds.center"))),
                  runtimeBoundsExtents=list(struct.unpack("<3f", view.read(cache+triangle["boundsExtents"], 12, "bounds.extents"))),
                  auxiliary=[], reads=view.reads)
    requests = [("edgeFlags", cache+triangle["edgeFlags"], bytes(cooked.metadata["edgeFlags"]))]
    if cooked.metadata["faceRemap"]:
        remap = cooked.metadata["faceRemap"]
        _require(contract["representation"]["faceRemapWidth"] == 4, "unsupported native face-remap width")
        requests.append(("faceRemap", cache+triangle["faceRemap"], struct.pack("<"+str(len(remap))+"I", *remap)))
    for label, pointer_field, expected in requests:
        if not expected:
            continue
        try:
            pointer = view.scalar(pointer_field, "Q", label+".pointer")
            raw = view.read(pointer, len(expected), label)
            result["auxiliary"].append(dict(field=label, status="matched" if raw == expected else "different", bytes=len(raw)))
        except (WindowGap, ValueError) as exc:
            result["auxiliary"].append(dict(field=label, status="unavailable", detail=str(exc)))
    try:
        tree_address = cache+triangle["treeOffset"]
        count = view.scalar(tree_address+tree["nodeCount"], "I", "bvh.nodeCount")
        pointer = view.scalar(tree_address+tree["nodes"], "Q", "bvh.nodes")
        expected = spans["bvh.slabs"]
        raw = view.read(pointer, len(expected), "bvh.storedExtentBytes")
        result["auxiliary"].append(dict(field="bvh.slabs", status="matched" if raw == expected and count == len(cooked.metadata["bvh"]["slots"]) else "different",
                                        bytes=len(raw), runtimeNodeCount=count, boundary=contract["representation"]["auxiliaryBoundary"]))
    except (WindowGap, ValueError) as exc:
        result["auxiliary"].append(dict(field="bvh.slabs", status="unavailable", detail=str(exc)))
    return result


def read_calls(root, profile):
    """Read paired declared events; immutable-session admission is owned above."""
    calls={}
    for line in (root/'events.jsonl').read_text('utf-8').splitlines():
        row=json.loads(line)
        if profile['schema'] in ('endfieldCapture.collisionBuild.v9','endfieldCapture.collisionBuild.v10','endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17'):
            from scripts.game_data.collision_capture_events import expand
            row=expand(row,profile['transport']['eventFormat'])
        if row['phase']==0:
            _require(row['call'] not in calls,'duplicate journal entry');calls[row['call']]=row
        else:
            _require(row['call'] in calls and 'returnRecord' not in calls[row['call']],'unpaired journal return')
            calls[row['call']]['returnRecord']=row
    return calls


def load_admission(root, *, reinspect=False, game_root=None, calls_out=None):
    """Reuse passed session admission only while its source bytes still agree."""
    report = inspect(root, game_root=game_root) if reinspect else json.loads((root/"collected/collision-inspection.json").read_text("utf-8"))
    _require(report.get("status") == "validated" and report.get("nativeGate") == "validated", "saved session was not admitted")
    _require(report.get("schema") in ("endfield.collision-capture-inspection.v6", "endfield.collision-capture-inspection.v7", "endfield.collision-capture-inspection.v8", "endfield.collision-capture-inspection.v9", "endfield.collision-capture-inspection.v10", "endfield.collision-capture-inspection.v11", "endfield.collision-capture-inspection.v12","endfield.collision-capture-inspection.v13","endfield.collision-capture-inspection.v14","endfield.collision-capture-inspection.v15",'endfield.collision-capture-inspection.v16','endfield.collision-capture-inspection.v17','endfield.collision-capture-inspection.v18') and Path(report["session"]).resolve() == root.resolve(), "saved admission schema/session")
    session = json.loads((root/"session.json").read_text("utf-8"))
    profile_path = root/"private/collision-build.json"
    _require(sha256_file(profile_path) == session["profileSha256"], "frozen profile changed")
    _require(sha256_file(root/"private/EndfieldCollisionCapture.dll") == session["runtimeSha256"], "staged runtime changed")
    profile = json.loads(profile_path.read_text("utf-8"))
    for source in profile["sources"]:
        leaf = source["archiveName"]
        _require(Path(leaf).name == leaf, "frozen source path")
        path = root/"static-sources"/leaf
        _require(path.stat().st_size == source["bytes"] and sha256_file(path) == source["sha256"].lower(), "frozen source changed:"+leaf)
    journal = root/"events.jsonl"
    _require(sha256_file(journal) == report["journalSha256"], "admitted journal changed")
    calls = read_calls(root,profile)
    receipt = json.loads((root/"receipt.json").read_text("utf-8"))
    for key in ("complete", "hooksInstalled", "quiescent", "writerOk"):
        _require(receipt[key] is True, "receipt completion:"+key)
    for key in ("dropped", "unreadable", "abandoned", "trackingOverflow", "activeCallbacks"):
        _require(receipt[key] == 0, "receipt loss:"+key)
    _require(receipt["calls"] == len(calls) and receipt["rows"] == report["rows"] == len(calls)*2, "admitted call census changed")
    for key in ("enableStatus", "disableStatus"):
        _require(receipt[key]["stage"] == 0 and receipt[key]["cleanupSucceeded"] is True and receipt[key]["pendingRecovery"] is False, "strict hook receipt")
    # Recheck cheap archive framing, every edge, timestamp and hash; reuse the
    # expensive already-passed managed method/ABI admission on identical inputs.
    memory = validate_archive(root/"native-memory.bin", receipt["nativeMemory"], profile["nativeMemory"], calls,
                              stage_contract=profile['stageCapture']['contract'] if profile['schema'] in ('endfieldCapture.collisionBuild.v10','endfieldCapture.collisionBuild.v11','endfieldCapture.collisionBuild.v12','endfieldCapture.collisionBuild.v13','endfieldCapture.collisionBuild.v14','endfieldCapture.collisionBuild.v15','endfieldCapture.collisionBuild.v16','endfieldCapture.collisionBuild.v17') else None,
                              detail_contract=profile.get('detailCapture',{}).get('contract'))
    _require(memory == report["nativeMemory"], "cached memory inspection differs")
    samples = [r for r in report["observations"] if r["kind"] in ("child_collider", "physics_collider") and r.get("meshPointer")]
    _require(len({r["call"] for r in samples}) == len(samples), "duplicate observed sample")
    eligible = {n for n, call in calls.items() if call["kind"] in (10, 13) and call["returnRecord"]["queryState"] == 1 and _le_pointer(call["returnRecord"]["mesh"])}
    _require(eligible == {r["call"] for r in samples}, "cached sample census differs")
    for sample in samples:
        raw = calls[sample["call"]]["returnRecord"]
        _require(sample["meshPointer"] == raw["mesh"] and sample["meshInstanceId"] == raw["meshId"] and
                 sample["colliderPointer"] == raw["args"][0] and sample["objectInstanceId"] == raw["objectId"] and
                 sample["worldMatrixColumnMajor"] == _floats(bytes.fromhex(raw["world"])), "cached sample values differ")
        _require(sample["enabled"] == bool(raw["enabled"]) and sample["convex"] == bool(raw["convex"]) and
                 sample["activeInHierarchy"] == bool(raw["active"]) and sample["rootGameObjectPointer"] == raw["args"][1] and
                 sample["gameObjectPointer"] == raw["go"] and sample["transformPointer"] == raw["transform"] and
                 sample["gameObjectInstanceId"] == raw["goId"], "cached sample state/root differs")
        expected_enrollment = _le_pointer(raw["args"][4]) if sample["kind"] == "physics_collider" else struct.unpack_from("<Q", bytes.fromhex(raw["after"]), 32)[0]
        _require(sample["enrollmentQpc"] == expected_enrollment, "cached enrollment time differs")
        origin = _origin(raw["meshOrigin"])
        _require(sample["meshProvenance"] == origin and sample["meshSourceJoin"] == _mesh_join(origin, profile), "cached source join differs")
        if sample["kind"] == "physics_collider":
            _require(sample["originChildCall"] == _le_pointer(raw["args"][2]) and sample["completedStepOrdinal"] == _le_pointer(raw["args"][3]), "cached retained link differs")
        else:
            _require(sample["retainedOriginCall"] == struct.unpack_from("<Q", bytes.fromhex(raw["after"]), 24)[0], "cached initial retained link differs")
        sample["worldMatrixBitsHex"] = raw["world"]
    if calls_out is not None:
        calls_out.update(calls)
    return report, profile, receipt, samples


def compare(root, raw_mesh_path, cooked_path, *, game_root=None, reinspect=False):
    result = dict(schema=SCHEMA, status="failed", session=str(root.resolve()), samples=[], diagnostics=[])
    try:
        root = root.resolve(strict=True)
        admission, profile, receipt, samples = load_admission(root, reinspect=reinspect, game_root=game_root)
        files = profile["files"]
        directory = game_root.parent if game_root and game_root.name == "Endfield_Data" else game_root
        paths = {name: directory/row["relativePath"] if directory else Path(row["path"]) for name, row in files.items()}
        contract, gate = load_layout(gameassembly=paths["gameAssembly"], metadata=paths["metadata"], unityplayer=paths["unityPlayer"])
        result["nativeGate"] = gate
        _require(contract is not None, "native layout:"+gate["status"]+":"+gate.get("detail", ""))
        for key, profile_key in (("gameAssemblySha256", "gameAssembly"), ("metadataSha256", "metadata"), ("unityPlayerSha256", "unityPlayer")):
            _require(contract["nativeInputs"][key].lower() == files[profile_key]["sha256"].lower(), "capture/native layout build differs")
        raw_mesh, payload = raw_mesh_path.read_bytes(), cooked_path.read_bytes()
        raw_sha, cooked_sha = _sha(raw_mesh), _sha(payload)
        _require(raw_mesh.count(payload) == 1, "cooked payload is not unique within selected raw Mesh")
        bindings = [r for r in profile["target"]["colliderBindings"] if r["meshRawSha256"] == raw_sha and
                    any(b["kind"] == "triangle" and b["sha256"] == cooked_sha for b in r["cookedBuffers"])]
        identities = {(b["mesh"]["sourceFile"].lower(), str(b["mesh"]["pathId"] & ((1<<64)-1))) for b in bindings}
        _require(len(identities) == 1, "raw/cooked hashes lack one frozen source identity")
        identity = next(iter(identities))
        cooked = read_triangle_mesh(payload)
        archive = (root/"native-memory.bin").read_bytes()
        _require(_sha(archive) == admission["nativeMemory"]["sha256"], "archive changed after admission")
        by_call = {r["call"]: r for r in samples}
        for sample in samples:
            origin = sample["meshProvenance"]
            source_mode = "direct_this_sample"
            if origin["status"] == "read_lock_busy" and sample["kind"] == "physics_collider":
                initial = by_call[sample["originChildCall"]]
                _require(initial["kind"] == "child_collider" and all(initial[k] == sample[k] for k in ("meshPointer", "meshInstanceId", "colliderPointer", "objectInstanceId", "enrollmentQpc", "rootGameObjectPointer", "gameObjectPointer", "transformPointer", "gameObjectInstanceId")), "retained source reuse identity differs")
                origin = initial["meshProvenance"]
                source_mode = "conditional_retained_identity_from_instantiation"
            if origin.get("status") != "mapped" or (origin.get("cab"), origin.get("pathId")) != identity:
                continue
            roots = [w for w in admission["nativeMemory"]["windows"] if w["call"] == sample["call"] and w["role"] == "sharedMesh" and w["depth"] == 0]
            row = dict(call=sample["call"], originChildCall=sample.get("originChildCall", sample["call"]), completedStepOrdinal=sample.get("completedStepOrdinal", 0),
                       sourceMode=source_mode, worldMatrixColumnMajor=sample["worldMatrixColumnMajor"], worldMatrixBitsHex=sample["worldMatrixBitsHex"], enabled=sample["enabled"], active=sample["activeInHierarchy"], convex=sample["convex"])
            view = None
            try:
                _require(len(roots) == 1, "missing/ambiguous native Mesh root")
                native_root = int(roots[0]["address"], 16)
                view = WindowView(admission["nativeMemory"]["windows"], archive, call=sample["call"], root=roots[0]["root"])
                row.update(decode_sample(view, native_root, _le_pointer(receipt["playerBase"]), contract, cooked, payload))
            except (ValueError, KeyError, TypeError, struct.error) as exc:
                row.update(status="unavailable" if isinstance(exc, WindowGap) else "rejected", detail=str(exc), reads=view.reads if view else [])
            result["samples"].append(row)
        matched = [s for s in result["samples"] if s["status"] == "matched"]
        _require(result["samples"], "no captured samples join the selected source")
        result.update(status="validated" if len(matched) == len(result["samples"]) else "partial", source=dict(cab=identity[0], pathId=identity[1], rawMeshSha256=raw_sha, cookedSha256=cooked_sha),
                      journalSha256=admission["journalSha256"], archiveSha256=admission["nativeMemory"]["sha256"], profileSha256=sha256_file(root/"private/collision-build.json"),
                      physicsCoverage=admission["physicsSnapshotCoverage"], sampleCoverage=dict(Counter(s["status"] for s in result["samples"])),
                      uniqueMatchedCaches=len({s["cacheAddress"] for s in matched}), uniqueMatchedGeometry=len({s["geometrySha256"] for s in matched}),
                      changedWorldMatrices=[dict(call=s["call"], originChildCall=s["originChildCall"], completedStepOrdinal=s["completedStepOrdinal"],
                                                 changedElements=[i for i in range(16) if by_call[s["originChildCall"]]["worldMatrixBitsHex"][i*8:i*8+8] != s["worldMatrixBitsHex"][i*8:i*8+8]])
                                            for s in result["samples"] if s["completedStepOrdinal"] and s["worldMatrixBitsHex"] != by_call[s["originChildCall"]]["worldMatrixBitsHex"]],
                      traversalLimits=admission["nativeMemory"]["samples"], evidenceBoundary=contract["evidenceBoundary"],
                      remainingGaps=["Separately timed reads; no atomic cache snapshot, allocation extents, PxShape ownership or contact results.", contract["representation"]["auxiliaryBoundary"]])
        _require(sha256_file(root/"events.jsonl") == result["journalSha256"] and sha256_file(root/"native-memory.bin") == result["archiveSha256"], "capture changed during comparison")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, struct.error) as exc:
        result.update(status="failed", samples=[], diagnostics=[dict(check="runtime_mesh_comparison", detail=str(exc)[:1600])])
    return result


def _output_path(path):
    resolved = path.resolve()
    _require(any(resolved.is_relative_to(REPO_ROOT/name) for name in ("reports", "scratch", "tmp")), "generated output must be under reports/, scratch/ or tmp/")
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--raw-mesh", type=Path, required=True)
    parser.add_argument("--cooked", type=Path, required=True)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--reinspect", action="store_true", help="rerun full admission instead of reusing unchanged admitted bytes")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--obj", type=Path, help="write source geometry only after every selected runtime cache comparison matches")
    args = parser.parse_args(argv)
    output = _output_path(args.output or args.session/"collected/runtime-mesh-comparison.json")
    obj = _output_path(args.obj) if args.obj else None
    report = compare(args.session, args.raw_mesh, args.cooked, game_root=args.game_root, reinspect=args.reinspect)
    if obj and report["status"] == "validated":
        payload = args.cooked.read_bytes()
        _require(_sha(payload) == report["source"]["cookedSha256"], "cooked file changed before OBJ publication")
        mesh = read_triangle_mesh(payload)
        write_obj(obj, mesh.geometry, complete=mesh)
        report["obj"] = dict(path=str(obj), sha256=sha256_file(obj), boundary="source-local collision surface, equal to all selected decoded runtime cache samples; no world placement or contact claim")
    atomic_write_text(output, json.dumps(report, indent=2)+"\n")
    print(json.dumps(dict(status=report["status"], samples=report.get("sampleCoverage", {}), diagnostics=report["diagnostics"], output=str(output))))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
