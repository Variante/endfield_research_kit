"""Audit a selected set of Unity Mesh JSON/raw exports and cooked collision data.

Selection is explicit (AnimeStudio --filter_data JSON), never inferred from a
name. A current VFS audit gates the selected CAB identities. Raw object hashes
and typed cooked-buffer hashes must agree before a format reader is called.
The selection defines coverage; this does not claim every installed Mesh was
selected, or assign scene transforms, materials or runtime collider ownership.
"""
from __future__ import annotations
from scripts.source_paths import configured_animestudio_cli
from scripts.source_paths import ExportLayout

from collections import Counter
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
from functools import lru_cache

from scripts.game_data.unity_evidence_store import (
    evidence_path, evidence_roots, native_store_args, snapshot_path, storage_receipt, validate_storage,
)
from scripts.game_data.cooked_collision import read_triangle_mesh
from scripts.game_data.cooked_convex import read_convex_mesh
from scripts.game_data.corpus_common import atomic_write_text, validate_provenance
from scripts.repo_paths import REPO_ROOT

DEFAULT_CLI = configured_animestudio_cli()
DEFAULT_EVIDENCE_ROOT = ExportLayout.configured().evidence_dir / 'assets/collision_evidence'


def _guard_evidence_root(path: Path, evidence_root: Path | None = None) -> None:
    """Published receipts must survive cleanup of disposable extraction inputs."""
    reports = (evidence_root or ExportLayout.configured().evidence_dir).resolve()
    resolved = path.resolve()
    if reports not in resolved.parents:
        raise ValueError("Collision evidence directory must be under the selected export/meta/evidence/: " + str(path))


def _retain_input(source: Path, destination: Path) -> str:
    """Keep the exact audited bytes, refusing a source changed during copying."""
    expected = _digest(source)
    shutil.copyfile(source, destination)
    if _digest(destination) != expected or _digest(source) != expected:
        raise ValueError(f"Collision evidence input changed while retaining it: {source}")
    return expected


@lru_cache(maxsize=4096)
def _path_key(path: str | Path) -> str:
    return Path(path).resolve().as_posix().casefold()


def _identity(source: str, offset: int, path_id: int) -> tuple:
    if not isinstance(offset,int) or offset < 0 or not isinstance(path_id,int):
        raise ValueError(f"invalid selected Mesh offset/PathID: {offset}/{path_id}")
    return _path_key(source),offset,path_id & 0xffffffffffffffff


def _digest(path: Path, algorithm: str = "sha256") -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source,algorithm).hexdigest().upper()


def _selection_input(selection: list) -> Path:
    # filter_data reads explicit physical chunks, possibly in either audited
    # layer. Metadata priority must not hide fallback chunks from Unity loading.
    return Path(os.path.commonpath([str(Path(row["Source"]).resolve().parent) for row in selection]))


def _verify_fingerprints(summary: dict) -> None:
    for row in summary["sourceFingerprints"]+summary["buildFingerprints"]:
        path = Path(row["path"])
        if path.stat().st_size != row["length"] or _digest(path) != row["sha256"]:
            raise ValueError(f"audited input changed: {path}")


def _decoder_closure(cli: Path) -> list[dict]:
    return [dict(path=p.relative_to(cli.parent).as_posix(), length=p.stat().st_size, sha256=_digest(p))
            for p in sorted(cli.parent.rglob("*")) if p.is_file()]


def _selected_ledger(summary_path: Path, ledger_path: Path, selection: list, expected: str) -> tuple:
    if not re.fullmatch(r"[0-9a-fA-F]{64}",expected):
        raise ValueError("expected inputSetSha256 must be 64 hexadecimal characters")
    expected = expected.upper()
    summary = json.loads(summary_path.read_text("utf-8"))
    wanted = {(_path_key(row["Source"]),row["Offset"]) for row in selection}
    chunks_wanted = {p for p,_ in wanted}
    headers, files, chunks = [], {}, {}
    with gzip.open(ledger_path,"rt",encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            # An overlay ledger retains replaced fallback declarations beside
            # the active metadata view. They never admit a selected file or
            # duplicate the active physical chunk's authentication record.
            if row.get("status") == "shadowed_fallback" and row.get("boundaryStatus") == "shadowed":
                continue
            if row.get("recordType") == "audit_header":
                headers.append(row)
            elif row.get("recordType") == "file" and row.get("physicalChunkPath"):
                key = (_path_key(row["physicalChunkPath"]),row["offset"])
                if key in wanted:
                    if key in files:
                        raise ValueError(f"duplicate selected VFS file identity: {key}")
                    files[key] = row
            elif row.get("recordType") == "chunk" and row.get("physicalChunkPath"):
                key = _path_key(row["physicalChunkPath"])
                if key in chunks_wanted:
                    if key in chunks:
                        raise ValueError(f"duplicate selected VFS chunk identity: {key}")
                    chunks[key] = row
    if len(headers) != 1:
        raise ValueError(f"expected one VFS ledger header; got {len(headers)}")
    failures, provenance = validate_provenance(summary,headers[0],ledger_path,expected)
    if failures:
        raise ValueError(f"VFS provenance checks failed: {failures[:4]}")
    if set(files) != wanted or set(chunks) != chunks_wanted:
        raise ValueError(f"selection not covered by ledger: files={len(files)}/{len(wanted)}, chunks={len(chunks)}/{len(chunks_wanted)}")
    for row in list(files.values())+list(chunks.values()):
        if (row.get("inputSetSha256") != expected or row.get("status") != "verified"
                or row.get("boundaryStatus") != "boundary_verified"
                or row.get("blockName") not in ("Bundle","InitBundle")):
            raise ValueError(f"selected VFS Bundle is not authenticated: {row.get('physicalChunkPath')}:{row.get('offset')}")
    provenance["auditBlocks"] = [row["blockName"] for row in summary["blocks"]]
    provenance["outerSummaryPath"] = str(summary_path.resolve())
    return summary,provenance,files,chunks


def _join_selection(report: dict, selection: list) -> None:
    wanted = {_identity(r["Source"],r["Offset"],r["PathID"]):r for r in selection}
    if len(wanted) != len(selection) or not wanted:
        raise ValueError("Mesh selection is empty or has duplicate serialized identities")
    seen = set()
    for row in report["objects"]:
        identity = row.get("identity")
        if not identity:
            raise ValueError(f"typed export has no serialized identity: {row['jsonPath']}")
        key = _identity(identity["sourceOriginalPath"],identity["sourceOffset"],identity["pathId"])
        if key not in wanted or key in seen:
            raise ValueError(f"unexpected/duplicate exported Mesh identity: {key}")
        seen.add(key)
        row["container"] = wanted[key].get("Container")  # Catalog label only.
    if seen != set(wanted):
        missing = sorted(set(wanted)-seen)
        raise ValueError(f"Mesh extraction coverage differs from selection: {len(seen)}/{len(wanted)}, first missing={missing[0]}")


def audit_selection(*, selection_path: Path, summary_path: Path, ledger_path: Path,
                    expected_input_set: str, work_root: Path, cli: Path = DEFAULT_CLI,
                    evidence_root: Path | None = None) -> dict:
    """Authenticate inputs, run a fresh typed/raw export, check identity coverage."""
    _guard_evidence_root(work_root, evidence_root)
    work_root.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="collision-", dir=work_root)).resolve()
    inputs = run_root / "inputs"
    inputs.mkdir()
    retained = {}
    for source, name in ((selection_path, "selection.json"), (summary_path, "vfs_audit.json"),
                         (ledger_path, "vfs_ledger.jsonl.gz")):
        destination = inputs / name
        retained[destination] = _retain_input(source, destination)
    selection_path, summary_path, ledger_path = (
        inputs / "selection.json", inputs / "vfs_audit.json", inputs / "vfs_ledger.jsonl.gz"
    )
    # Validate and invoke the exporter using retained inputs. Original paths may
    # be temporary; no published dependency or command points back to them.
    selection = json.loads(selection_path.read_text("utf-8"))
    if not isinstance(selection,list) or not selection or any(row.get("Type") != "Mesh" for row in selection):
        raise ValueError("selection must be a non-empty AnimeStudio Mesh filter array")
    # Reject duplicates before launching the exporter.
    if len({_identity(r["Source"],r["Offset"],r["PathID"]) for r in selection}) != len(selection):
        raise ValueError("selection has duplicate Mesh identities")
    selection_sha = _digest(selection_path)
    summary,provenance,files,chunks = _selected_ledger(summary_path,ledger_path,selection,expected_input_set)
    if _path_key(cli) not in {_path_key(r["path"]) for r in summary["buildFingerprints"]}:
        raise ValueError(f"exporter CLI has no fingerprint in the selected audit: {cli}")
    _verify_fingerprints(summary)
    decoder = _decoder_closure(cli)
    physical_inputs = []
    for key,row in sorted(chunks.items()):
        path = Path(row["physicalChunkPath"]); stat = path.stat(); digest = _digest(path,"md5")
        if stat.st_size != row["actualPhysicalLength"] or digest != row["recomputedContentMd5"]:
            raise ValueError(f"selected physical chunk differs from current audit: {path}")
        physical_inputs.append(dict(path=str(path),length=stat.st_size,mtimeNs=stat.st_mtime_ns,md5=digest))
    json_root,raw_root = run_root/"json",run_root/"raw"
    command = [str(cli),str(_selection_input(selection)),str(json_root),"--game","ArknightsEndfield",
               "--types","Mesh","--names","^$","--export_type","JSON","--filter_data",str(selection_path.resolve()),
               "--secondary_export_type","Raw","--secondary_export_path",str(raw_root),"--secondary_types","Mesh", *native_store_args(run_root)]
    with (run_root/"export.log").open("wb") as log:
        completed = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=False)
    if completed.returncode:
        raise ValueError(f"AnimeStudio selected Mesh export returned {completed.returncode}; log={run_root/'export.log'}")
    if _digest(selection_path) != selection_sha or _decoder_closure(cli) != decoder:
        raise ValueError("selection/exporter output closure changed during extraction")
    _verify_fingerprints(summary)
    for row in physical_inputs:
        stat = Path(row["path"]).stat()
        if stat.st_size != row["length"] or stat.st_mtime_ns != row["mtimeNs"]:
            raise ValueError(f"selected physical chunk changed during extraction: {row['path']}")
    json_root, raw_root = evidence_roots(run_root, stored=True)
    report = inspect_exports(json_root/"Mesh", raw_root/"Mesh")
    if {str(p) for p in raw_root.rglob("*.dat")} != {r["rawPath"] for r in report["objects"]}:
        raise ValueError("Collision raw/typed object census differs")
    _join_selection(report,selection)
    for path, expected in retained.items():
        if _digest(path) != expected:
            raise ValueError(f"retained Collision evidence changed during extraction: {path}")
    report.update(schema="endfield.cooked-collision-selected-corpus.v3", inputSetSha256=expected_input_set.upper(),
                  provenance=provenance, selection=dict(path=str(selection_path),sha256=selection_sha,meshCount=len(selection),cabCount=len(files)),
                  extraction=dict(command=command,log=str(run_root/"export.log"),logSha256=_digest(run_root/"export.log"),
                                  decoderOutputClosure=decoder,physicalInputs=physical_inputs, storage=storage_receipt(run_root)),
                  evidenceBoundary="Exact cooked-buffer length/SHA256 joins to fresh Unity raw objects, under a selected current VFS Bundle audit and unchanged exporter/input snapshots. Format readers reach payload EOF. Coverage is the explicit Mesh identity selection; render attributes, scene transforms and collider ownership are separate joins.")
    return report


def extract_payload(raw: bytes, info: dict, kind: str) -> tuple[int, bytes]:
    """Join one typed buffer to a length-prefixed raw object range by SHA256."""
    size = info["ByteCount"]
    if not isinstance(size, int) or size <= 0:
        raise ValueError(f"{kind}: non-positive typed ByteCount {size}")
    magic = b"MESH" if kind == "triangle" else b"CVXM"
    matches = []
    for endian_byte in (0, 1):
        header = b"NXS" + bytes([endian_byte]) + magic
        start = raw.find(header)
        while start != -1:
            if (start >= 4 and start+size <= len(raw)
                    and struct.unpack_from("<i", raw, start-4)[0] == size):
                payload = raw[start:start+size]
                if hashlib.sha256(payload).hexdigest().lower() == str(info.get("Sha256", "")).lower():
                    matches.append((start, payload))
            start = raw.find(header, start+1)
    if len(matches) != 1:
        raise ValueError(f"{kind}: expected one raw length/SHA256 match; got {len(matches)}")
    if matches[0][1][:16].hex().upper() != info.get("HeaderHex"):
        raise ValueError(f"{kind}: typed header differs from raw payload")
    return matches[0]


def validate_receipt(report_path: Path, *, summary_path: Path | None = None) -> dict:
    """Admit a saved extraction for another consumer while its inputs are current.

    This does not run AnimeStudio again. It authenticates the audited ledger,
    selected physical chunks, exporter closure, extraction command and coverage.
    Consumers must additionally rejoin each typed/raw buffer with
    ``receipt_payloads`` and run the complete format reader before using it.
    """
    try:
        return _validate_receipt(report_path, summary_path=summary_path)
    except FileNotFoundError as error:
        raise ValueError(
            f"Collision receipt {report_path}: required evidence file is missing: {error.filename}. "
            "Run export.bat assets to regenerate legacy receipts automatically; "
            "new runs retain selection, VFS audit and Mesh JSON/raw evidence inside the selected export/meta/evidence/assets/collision_evidence/. "
            "export.bat assets automatically prepares missing or stale static collision evidence; "
            "an empty replacement file cannot satisfy its hash checks."
        ) from error


def _validate_receipt(report_path: Path, *, summary_path: Path | None = None) -> dict:
    report = json.loads(report_path.read_text("utf-8"))
    if (report.get("schema") not in ("endfield.cooked-collision-selected-corpus.v1", "endfield.cooked-collision-selected-corpus.v2", "endfield.cooked-collision-selected-corpus.v3")
            or report.get("status") != "complete" or report.get("failures")):
        raise ValueError("collision receipt is not a complete selected-corpus result")
    selection_info = report["selection"]
    selection_path = Path(selection_info["path"])
    if _digest(selection_path) != selection_info["sha256"]:
        raise ValueError(f"collision selection SHA256 differs: {selection_path}")
    selection = json.loads(selection_path.read_text("utf-8"))
    if not selection or any(row.get("Type") != "Mesh" for row in selection):
        raise ValueError("collision selection is not a non-empty Mesh array")
    provenance = report["provenance"]
    summary_path = summary_path or Path(provenance["outerSummaryPath"])
    summary, current, files, chunks = _selected_ledger(
        summary_path, Path(provenance["outerLedger"]), selection, report["inputSetSha256"])
    for field in ("inputSetSha256", "outerLedgerSha256", "primaryAssets", "fallbackAssets", "auditBlocks"):
        if current[field] != provenance[field]:
            raise ValueError(f"collision receipt provenance differs: {field}")
    input_paths = {Path(row["path"]) for row in summary["sourceFingerprints"] + summary["buildFingerprints"]}
    input_paths.update(Path(row["physicalChunkPath"]) for row in chunks.values())
    input_paths.update((report_path, summary_path, selection_path, Path(provenance["outerLedger"])))
    snapshots = {str(path): (path.stat().st_size, path.stat().st_mtime_ns) for path in input_paths}
    _verify_fingerprints(summary)
    extraction = report["extraction"]
    command = extraction["command"]
    # Bind the raw/JSON paths and selection to the command that made them.
    stored = report["schema"].endswith(".v3")
    if len(command) != (23 if stored else 19):
        raise ValueError("collision receipt extraction command has an unexpected shape")
    cli, primary, json_root = map(Path, command[:3])
    raw_root = Path(command[16])
    expected = [str(cli), str(primary), str(json_root), "--game", "ArknightsEndfield",
                "--types", "Mesh", "--names", "^$", "--export_type", "JSON", "--filter_data",
                str(selection_path.resolve()), "--secondary_export_type", "Raw", "--secondary_export_path",
                str(raw_root), "--secondary_types", "Mesh"]
    if stored:
        expected.extend(native_store_args(json_root.parent))
        validate_storage(json_root.parent, extraction)
        store = json_root.parent / "objects.sqlite"
        snapshots[str(store)] = (store.stat().st_size, store.stat().st_mtime_ns)
    expected_input = _selection_input(selection) if not report["schema"].endswith(".v1") else Path(summary["primaryAssets"])
    if command[3:] != expected[3:] or _path_key(primary) != _path_key(expected_input):
        raise ValueError("collision receipt command does not match the audited Mesh selection")
    if _path_key(cli) not in {_path_key(row["path"]) for row in summary["buildFingerprints"]}:
        raise ValueError("collision receipt CLI is absent from the VFS audit")
    if _decoder_closure(cli) != extraction["decoderOutputClosure"]:
        raise ValueError("collision receipt exporter output closure differs")
    for path in cli.parent.rglob("*"):
        if path.is_file():
            snapshots[str(path)] = (path.stat().st_size, path.stat().st_mtime_ns)
    if _digest(Path(extraction["log"])) != extraction["logSha256"]:
        raise ValueError("collision extraction log SHA256 differs")
    physical = {_path_key(row["path"]): row for row in extraction["physicalInputs"]}
    if set(physical) != set(chunks) or len(physical) != len(extraction["physicalInputs"]):
        raise ValueError("collision receipt physical chunk coverage differs")
    for key, chunk in chunks.items():
        row = physical[key]
        path = Path(row["path"])
        if (path.stat().st_size != row["length"] or row["length"] != chunk["actualPhysicalLength"]
                or row["md5"] != chunk["recomputedContentMd5"] or _digest(path, "md5") != row["md5"]):
            raise ValueError(f"collision receipt physical chunk changed: {path}")
    if (report["selectedCount"] != len(selection) or selection_info["meshCount"] != len(selection)
            or selection_info["cabCount"] != len(files) or len(report["objects"]) != len(selection)):
        raise ValueError("collision receipt selection counts differ")
    _join_selection(report, selection)
    counts = Counter(row["status"] for row in report["objects"])
    if dict(counts) != report["counts"] or set(counts) - {"decoded", "noCookedData"}:
        raise ValueError("collision receipt object statuses/counts differ")
    if stored:
        json_root, raw_root = evidence_roots(json_root.parent, stored=True)
        for root, field, pattern in ((json_root, "jsonPath", "*.json"), (raw_root, "rawPath", "*.dat")):
            if {str(p) for p in (root/"Mesh").glob(pattern)} != {r[field] for r in report["objects"]}:
                raise ValueError("collision database object census differs")
    for row in report["objects"]:
        if (evidence_path(row["jsonPath"]).resolve().parent != (json_root/"Mesh").resolve()
                or evidence_path(row["rawPath"]).resolve().parent != (raw_root/"Mesh").resolve()):
            raise ValueError(f"collision receipt object lies outside extraction roots: {row['name']}")
        for field in ("jsonPath", "rawPath"):
            path = snapshot_path(row[field])
            if str(path) not in snapshots:
                stat = path.stat()
                snapshots[str(path)] = (stat.st_size, stat.st_mtime_ns)
    report["currentInputSnapshots"] = snapshots
    check_receipt_snapshot(report)
    return report


def check_receipt_snapshot(report: dict) -> None:
    """Reject an input replaced while a saved receipt is being consumed."""
    for filename, expected in report["currentInputSnapshots"].items():
        stat = Path(filename).stat()
        if (stat.st_size, stat.st_mtime_ns) != tuple(expected):
            raise ValueError(f"collision receipt input changed during consumption: {filename}")


def receipt_payloads(row: dict):
    """Yield hash-joined buffers, refusing edited typed JSON or raw objects."""
    typed = evidence_path(row["jsonPath"]).read_bytes()
    if row.get("jsonSha256") and hashlib.sha256(typed).hexdigest() != row["jsonSha256"].lower():
        raise ValueError("collision typed JSON SHA256 differs")
    data = json.loads(typed.decode("utf-8-sig"))
    identity = data["$animestudio"]
    if ({key: identity[key] for key in row["identity"]} != row["identity"]
            or data["m_Name"] != row["name"]
            or data["m_CollisionMeshOnly"] != row["collisionOnly"]
            or data["m_CollisionMeshBaked"] != row["baked"]
            or data["m_CollisionMeshConvex"] != row["convex"]
            or data["m_VertexCount"] != row["renderVertexCount"]):
        raise ValueError(f"collision typed identity/flags differ: {row['jsonPath']}")
    raw = evidence_path(row["rawPath"]).read_bytes()
    if (len(raw) != identity["rawDataLength"]
            or hashlib.sha256(raw).hexdigest() != identity["rawDataSha256"]
            or identity["rawDataSha256"] != row["rawSha256"]):
        raise ValueError(f"collision raw object length/SHA256 differs: {row['rawPath']}")
    recorded = {item["kind"]: item for item in row["payloads"]}
    if len(recorded) != len(row["payloads"]):
        raise ValueError("collision receipt has duplicate payload kinds")
    actual = set()
    for kind, field in (("triangle", "TriangleCollision"), ("convex", "ConvexCollision")):
        info = data[field]
        if info["ByteCount"] == 0:
            if info.get("Sha256") is not None or info.get("HeaderHex") != "":
                raise ValueError(f"{field}: empty buffer has a digest/header")
            continue
        actual.add(kind)
        offset, payload = extract_payload(raw, info, kind)
        item = recorded.get(kind)
        if (not item or item["offset"] != offset or item["byteCount"] != len(payload)
                or str(item["sha256"]).lower() != hashlib.sha256(payload).hexdigest()):
            raise ValueError(f"{kind}: collision receipt buffer boundary/SHA256 differs")
        yield kind, payload, item
    if actual != set(recorded) or bool(actual) != (row["status"] == "decoded"):
        raise ValueError("collision receipt cooked-buffer coverage differs")


def inspect_exports(json_root: Path, raw_root: Path, *, payload_root: Path | None = None,
                    export_pairs=None) -> dict:
    results, failures, groups = [], [], Counter()
    pairs = export_pairs if export_pairs is not None else (
        (source, raw_root / (source.stem+".dat"))
        for source in sorted(json_root.glob("*.json"), key=lambda p: p.name))
    for source, raw_path in pairs:
        row = {"jsonPath": str(source), "rawPath": str(raw_path)}
        try:
            typed = source.read_bytes()
            data = json.loads(typed.decode("utf-8-sig"))
            identity = data["$animestudio"]
            row.update(identity={k: identity[k] for k in ("pathId", "sourceFile", "sourceOriginalPath", "sourceOffset")},
                       name=data["m_Name"], jsonSha256=hashlib.sha256(typed).hexdigest(), rawSha256=identity["rawDataSha256"],
                       collisionOnly=data["m_CollisionMeshOnly"], baked=data["m_CollisionMeshBaked"],
                       convex=data["m_CollisionMeshConvex"], renderVertexCount=data["m_VertexCount"])
            raw = evidence_path(row["rawPath"]).read_bytes()
            if len(raw) != identity["rawDataLength"] or hashlib.sha256(raw).hexdigest() != identity["rawDataSha256"]:
                raise ValueError("raw object length/SHA256 differs from typed export identity")
            cooked = []
            for kind, field in (("triangle", "TriangleCollision"), ("convex", "ConvexCollision")):
                info = data[field]
                if info["ByteCount"] == 0:
                    if info.get("Sha256") is not None or info.get("HeaderHex") != "":
                        raise ValueError(f"{field}: empty buffer has a digest/header")
                    continue
                offset, payload = extract_payload(raw, info, kind)
                item = dict(kind=kind, offset=offset, byteCount=len(payload), sha256=info["Sha256"])
                if payload_root:
                    payload_root.mkdir(parents=True, exist_ok=True)
                    dest = payload_root/(source.stem+f".{kind}.bin")
                    dest.write_bytes(payload); item["payloadPath"] = str(dest)
                if kind == "triangle":
                    mesh = read_triangle_mesh(payload)
                    item.update(vertexCount=len(mesh.geometry.vertices), triangleCount=len(mesh.geometry.triangles),
                                flags=mesh.geometry.flags, midphase=mesh.geometry.midphase,
                                indexWidth=mesh.geometry.index_width, bvhSlots=len(mesh.metadata["bvh"]["slots"]),
                                bvhQuantized=mesh.metadata["bvh"]["quantized"],
                                minimumZeroClampCount=len(mesh.metadata["bvh"]["minimumZeroClamps"]),
                                edgeFlagValues=sorted(set(mesh.metadata["edgeFlags"])))
                else:
                    mesh = read_convex_mesh(payload)
                    item.update(vertexCount=len(mesh.vertices), polygonCount=len(mesh.polygons),
                                gpuEdges=bool(mesh.metadata["gpuEdges"]),
                                gaussMap=mesh.metadata["gaussMap"] is not None,
                                planeResidualMax=max(mesh.metadata["planeVertexResiduals"]),
                                volume=mesh.metadata["volume"])
                item.update(bytesConsumed=mesh.metadata["bytesConsumed"], spans=mesh.spans)
                cooked.append(item)
            row["payloads"] = cooked
            row["status"] = "decoded" if cooked else "noCookedData"
            groups[row["status"]] += 1
        except (ValueError, KeyError, TypeError, OSError, struct.error) as error:
            row.update(status="failed", diagnostic=str(error))
            groups["failed"] += 1
            failures.append({"source": str(source), "diagnostic": str(error)})
        results.append(row)
    return dict(status="complete" if not failures else "failed", selectedCount=len(results),
                counts=dict(groups), failures=failures, objects=results)


def _guard_generated(path: Path) -> None:
    resolved = path.resolve()
    if not any(base.resolve() in resolved.parents for base in (ExportLayout.configured().evidence_dir,)):
        raise ValueError(f"corpus publication must be inside the selected export/meta/evidence/: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection",type=Path,required=True,help="explicit AnimeStudio Mesh --filter_data JSON")
    parser.add_argument("--outer-summary",type=Path,required=True)
    parser.add_argument("--outer-ledger",type=Path,required=True)
    parser.add_argument("--expected-input-set-sha256",required=True)
    parser.add_argument("--cli",type=Path,default=DEFAULT_CLI)
    parser.add_argument("--work-root",type=Path,default=DEFAULT_EVIDENCE_ROOT,
                        help="retained evidence directory inside the selected export/meta/evidence/")
    parser.add_argument("--output-json",type=Path,default=ExportLayout.configured().evidence_dir / 'assets/cooked_collision_current_latest.json')
    args = parser.parse_args()
    try:
        _guard_generated(args.output_json); _guard_evidence_root(args.work_root)
        if _path_key(args.output_json) in {_path_key(p) for p in (args.selection,args.outer_summary,args.outer_ledger,args.cli)}:
            raise ValueError("output report must differ from input files")
    except ValueError as error:
        print(json.dumps(dict(validator="cooked_collision_selected_corpus",status="failed",check="output boundary",diagnostic=str(error))))
        return 1
    try:
        report = audit_selection(selection_path=args.selection,summary_path=args.outer_summary,ledger_path=args.outer_ledger,
                                 expected_input_set=args.expected_input_set_sha256,cli=args.cli,work_root=args.work_root)
    except (ValueError,KeyError,TypeError,OSError,struct.error) as error:
        report = dict(schema="endfield.cooked-collision-selected-corpus.v2",status="failed",
                      inputSetSha256=args.expected_input_set_sha256.upper(),
                      failures=[dict(validator="cooked_collision_selected_corpus",check="input/extraction gate",diagnostic=str(error))])
    # A failed refresh must not replace the last complete publication.
    output = args.output_json if report["status"] == "complete" else args.output_json.with_name(
        args.output_json.stem + ".failed" + args.output_json.suffix)
    atomic_write_text(output,json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(validator="cooked_collision_selected_corpus",status=report["status"],
                          selectedCount=report.get("selectedCount"),counts=report.get("counts"),
                          failureCount=len(report["failures"]),firstFailures=report["failures"][:5],
                          report=str(output)),ensure_ascii=False))
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
