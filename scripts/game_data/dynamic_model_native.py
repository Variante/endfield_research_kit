"""Authenticate and decode stored DynamicStreaming Model records.

The reviewed generated layout closes every byte of the inline Model struct.
Current VFS bytes and a native-gated BundleManifest join its PathHash to authored
asset paths. These are stored placements, not instantiated Unity transforms.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.bundle_cab_dependency_corpus import _manifest_dependency_lists
from scripts.game_data.bundle_manifest import parse_decompressed_bundle_manifest
from scripts.game_data.bundle_manifest_native import audit_bundle_manifest_native
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.dynamic_main_native import validate_native_layout as validate_main_layout
from scripts.game_data.dynamic_scalar_components_native import (
    _builder_struct_declarations, _decode_record, _flat_fields,
    _float32_getter_offset, _gaps, _getter_offset, _nested_getter_offset,
    _relative_call_target, _validate_carriers,
)
from scripts.game_data.dynamic_stream_area_corpus import DEFAULT_CLI, MAIN_NAME_RE, load_current_inputs
from scripts.game_data.dynamic_streaming import _bounded_vector, _field_span, _root_layout, _table_layout, parse_dynamic_file
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.unity_scene_corpus import audit_selection as audit_scene_selection
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR/"dynamic_model_native.json"
SCHEMA = "endfield.dynamic-model-native-contract.v1"
AUDIT_SCHEMA = "endfield.dynamic-model-corpus.v2"


def join_model_colliders(models: list[dict], scene: dict, source_bundles: dict) -> dict:
    """Join authored path, selected logical Bundle and declared prefab root."""
    by_path = defaultdict(list)
    for collider in scene["colliders"]:
        if collider["status"] != "exact_serialized_collider_link":
            continue
        for prefab in collider["prefabAssets"]:
            identity = prefab["bundle"]["identity"]
            key = (identity["sourceOriginalPath"].replace("\\", "/").casefold(), identity["sourceOffset"])
            bundle = source_bundles.get(key)
            if bundle is None:
                raise ValueError(f"model-collider: selected prefab Bundle lacks active logical identity: {key}")
            by_path[prefab["path"], bundle].append(collider)
    matched, edges, convex = 0, 0, 0
    for model in models:
        model["colliderBindings"] = []
        if model["pathStatus"] != "unique_authored_path":
            continue
        asset = model["assets"][0]
        for collider in by_path.get((asset["path"], asset["bundle"]), []):
            model["colliderBindings"].append(dict(collider=collider["collider"]["identity"],
                mesh=collider["mesh"]["identity"], meshRawSha256=collider["mesh"]["rawSha256"],
                prefabRoot=collider["trace"]["chain"][-1]["gameObject"],
                composedPrefabLocalMatrix=collider["trace"]["composedLocalMatrix"],
                convex=collider["trace"]["convex"],
                cookedBuffers=[dict(kind=b["kind"], sha256=b["sha256"]) for b in collider["geometry"]],
                placementStatus="stored_model_and_prefab_local_only"))
            edges += 1; convex += int(collider["trace"]["convex"])
        matched += bool(model["colliderBindings"])
    return dict(modelsWithSelectedColliders=matched, modelColliderEdges=edges, convexEdges=convex)


def validate_native_layout(gameassembly: Path, metadata: Path) -> tuple:
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic-model", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["metadataSha256"],
                                         gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        raise ValueError(f"dynamic-model:installed_native_inputs:{gate.status}:{gate.detail}")
    main, main_digest, native = validate_main_layout(gameassembly, metadata)
    if native != inputs:
        raise ValueError("dynamic-model: main/model contracts select different native inputs")
    image = open_native_image(gameassembly, metadata)
    methods, bodies = {}, {}
    for row in contract["methods"]:
        index = row["index"]
        if index in methods or not 0 < row["bodyExtent"] <= 4096:
            raise ValueError("dynamic-model: duplicate method or invalid body extent")
        image.validate_method_row([index, row["type"], row["method"], row["rva"]], label="dynamic-model")
        method = image.metadata.methods[index]
        parameters = list(image.metadata.parameters_for(method))
        if ([image.metadata.metadata_type_name(p.type_index) for p in parameters] != row["parameters"]
                or [image.metadata.string(p.name_index) for p in parameters] != row["parameterNames"]
                or image.metadata.metadata_type_name(method.return_type) != row["returnType"]):
            raise ValueError(f"dynamic-model:{row['type']}.{row['method']}: metadata signature differs")
        raw = image.pe.bytes_at_va(image.pe.image_base+row["rva"], row["bodyExtent"])
        if hashlib.sha256(raw).hexdigest().upper() != row["bodySha256"]:
            raise ValueError(f"dynamic-model:{row['type']}.{row['method']}: body SHA256 differs")
        for probe in row.get("probes", []):
            at, expected = probe["offset"], bytes.fromhex(probe["bytes"])
            if at < 0 or not expected or raw[at:at+len(expected)] != expected:
                raise ValueError(f"dynamic-model:{row['method']}: builder witness differs at {at}")
        methods[index], bodies[index] = row, raw
    layout = contract["layout"]
    records = {row["type"]: row for row in layout["records"]}
    if len(records) != len(layout["records"]):
        raise ValueError("dynamic-model: duplicate record type")
    carriers = _validate_carriers(layout, image)
    used = set()
    for record in records.values():
        if _gaps(record, inline_types=records):
            raise ValueError(f"dynamic-model:{record['name']}: stored layout contains undeclared gaps")
        for field in record["fields"]:
            index = field["getterMethodIndex"]; method = methods[index]; raw = bodies[index]
            if (method["type"], method["method"], method["returnType"], method["parameters"]) != (
                    record["type"], "get_"+field["name"], field["type"], []):
                raise ValueError(f"dynamic-model:{record['name']}.{field['name']}: getter binding differs")
            kind = field["getterKind"]; label = record["name"]+"."+field["name"]
            if kind == "scalar":
                actual = _getter_offset(raw, label)
            elif kind == "float32":
                actual = _float32_getter_offset(raw, label)
            elif kind in ("initialize", "forward"):
                actual = _nested_getter_offset(raw, label, kind)
                if _relative_call_target(raw, method["rva"], field["carrierCallOffset"], label) != carriers[kind]["rva"]:
                    raise ValueError(f"dynamic-model:{label}: carrier initializer call differs")
            else:
                raise ValueError(f"dynamic-model:{label}: unsupported getter kind {kind}")
            if actual != field["offset"]:
                raise ValueError(f"dynamic-model:{label}: offset expected={field['offset']} actual={actual}")
            used.add(index)
        builder = methods[record["builderMethodIndex"]]; raw = bodies[builder["index"]]
        flattened = list(_flat_fields(record, records))
        if (builder["type"] != record["type"] or builder["method"] != "Create"+record["type"].rsplit(".", 1)[-1]
                or builder["parameters"] != ["Google.FlatBuffers.FlatBufferBuilder", *(f["type"] for f in flattened)]
                or [n.casefold() for n in builder["parameterNames"][1:]] != [f["name"].replace(".", "_").casefold() for f in flattened]):
            raise ValueError(f"dynamic-model:{record['name']}: builder flattened fields differ")
        declarations = _builder_struct_declarations(raw)
        if not declarations or declarations[0][1:] != (record["alignment"], record["width"]):
            raise ValueError(f"dynamic-model:{record['name']}: first struct Prep width/alignment differs")
        used.add(builder["index"])
    model = records[layout["modelType"]]
    vector = next(v for v in main["vectors"] if v["fieldIndex"] == model["gridFieldIndex"])
    if (vector["name"], vector["elementType"], vector["elementWidth"], vector["elementAlignment"]) != (
            model["name"], model["type"], model["width"], model["alignment"]) or used != set(methods):
        raise ValueError("dynamic-model: Model vector or native method coverage differs")
    return layout, main, dict(modelContractSha256=digest, mainContractSha256=main_digest), native


def decode_models(data: bytes, layout: dict, main: dict, *, source: str) -> list[dict]:
    """Decode a native-validated layout; source authentication belongs to audit."""
    widths = {v["fieldIndex"]: v["elementWidth"] for v in main["vectors"]}
    parse_dynamic_file("main", data, main_vector_widths=widths)
    records = {r["type"]: r for r in layout["records"]}; model = records[layout["modelType"]]
    root = _root_layout(data); body, count, _ = _bounded_vector(data, root, 3, 4)
    out = []
    for grid in range(count):
        slot = body+grid*4; table = _table_layout(data, slot+struct.unpack_from("<I", data, slot)[0])
        uid = _field_span(data, table, 0, 4)
        if uid is None:
            raise ValueError(f"{source}: grid[{grid}] lacks UniqueId")
        start, n, _ = _bounded_vector(data, table, model["gridFieldIndex"], model["width"])
        for ordinal in range(n):
            offset = start+ordinal*model["width"]
            values, gap = _decode_record(data, offset, model, source, inline_types=records)
            if gap:
                raise ValueError(f"{source}: grid[{grid}] Model[{ordinal}] undeclared bytes")
            specials = []
            for field in _flat_fields(model, records):
                if field["type"] != "System.Single":
                    continue
                value = struct.unpack_from("<f", data, offset+field["offset"])[0]
                if math.isfinite(value):
                    continue
                bits = struct.unpack_from("<I", data, offset+field["offset"])[0]
                special = dict(float32BitsHex=f"{bits:08X}",
                               special="nan" if math.isnan(value) else "negativeInfinity" if value < 0 else "positiveInfinity")
                target = values; names = field["name"].split(".")
                for name in names[:-1]:
                    target = target[name]
                target[names[-1]] = special
                specials.append(field["name"])
            out.append(dict(gridOrdinal=grid, uniqueId=struct.unpack_from("<I", data, uid)[0],
                            ordinal=ordinal, byteOffset=offset, values=values, float32SpecialFields=specials))
    return out


def manifest_assets(raw: bytes) -> dict[int, list[dict]]:
    """Read native-validated AssetInfo rows; preserve hash collisions explicitly."""
    import brotli  # Existing manifest reader dependency; no new package is installed.
    decoded = brotli.decompress(raw); parsed = parse_decompressed_bundle_manifest(decoded)
    names, _, _ = _manifest_dependency_lists(raw); table = parsed.tables[0]
    value_start = table.offset+table.row_count*8  # Hash slots precede 24-byte AssetInfo values.
    payload = memoryview(decoded)[parsed.variable_region.payload_offset:parsed.variable_region.footer_offset]
    result = defaultdict(list)
    for ordinal in range(table.row_count):
        key, path_offset, bundle_index, size, reserved = struct.unpack_from("<Q4I", decoded, value_start+ordinal*24)
        if not 0 <= bundle_index < len(names) or path_offset > len(payload)-4:
            raise ValueError(f"manifest AssetInfo[{ordinal}]: path or Bundle index out of bounds")
        length = struct.unpack_from("<I", payload, path_offset)[0]
        if length > len(payload)-path_offset-4:
            raise ValueError(f"manifest AssetInfo[{ordinal}]: compressed path exceeds payload")
        try:
            path = brotli.decompress(payload[path_offset+4:path_offset+4+length]).decode("utf-16-le", errors="strict")
        except (brotli.error, UnicodeError) as error:
            raise ValueError(f"manifest AssetInfo[{ordinal}]: compressed UTF16 path differs: {error}") from error
        row = dict(path=path, bundle=names[bundle_index], bundleIndex=bundle_index, assetSize=size)
        if row not in result[key]:
            result[key].append(row)
    return dict(result)


def audit(*, gameassembly: Path, metadata: Path, input_root: Path, manifest: Path,
          outer_path: Path, ledger_path: Path, expected_input_set: str, cli: Path = DEFAULT_CLI,
          scene_receipt: Path | None = None) -> dict:
    layout, main, contracts, native = validate_native_layout(gameassembly, metadata)
    outer, sources, provenance = load_current_inputs(outer_path, ledger_path, cli, expected_input_set,
                                                    file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes")
    manifest_native = audit_bundle_manifest_native(manifest=manifest, gameassembly=gameassembly, metadata=metadata)
    if manifest_native["status"] != "validated":
        raise ValueError(f"dynamic-model:manifest-native:{manifest_native['status']}:{manifest_native['detail']}")
    manifest_raw = manifest.read_bytes(); manifest_rows, source_bundles = [], {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if (row.get("recordType") == "file" and row.get("fileName") == "Data/Bundles/Windows/manifest.hgmmap"
                    and row.get("status") == "verified" and row.get("boundaryStatus") == "boundary_verified"):
                manifest_rows.append(row)
            if (row.get("recordType") == "file" and row.get("blockName") in ("Bundle", "InitBundle")
                    and row.get("status") == "verified" and row.get("boundaryStatus") == "boundary_verified"):
                key = (row["physicalChunkPath"].replace("\\", "/").casefold(), row["offset"])
                if key in source_bundles:
                    raise ValueError(f"dynamic-model: duplicate active Bundle source {key}")
                source_bundles[key] = row["fileName"]
    if (len(manifest_rows) != 1 or manifest_rows[0]["length"] != len(manifest_raw)
            or manifest_rows[0]["recomputedFileDataMd5"].upper() != hashlib.md5(manifest_raw).hexdigest().upper()):
        raise ValueError("dynamic-model: current manifest VFS length/MD5 join differs")
    assets = manifest_assets(manifest_raw); rows, receipts, counts = [], [], Counter()
    prefix = "Data/DynamicStreaming/"
    for source in sources:
        if not source["path"].startswith(prefix):
            raise ValueError(f"dynamic-model: invalid source prefix {source['path']}")
        relative = Path(source["path"][len(prefix):])
        if relative.is_absolute() or ".." in relative.parts or ":" in str(relative):
            raise ValueError(f"dynamic-model: invalid source path {source['path']}")
        path = input_root/relative; data = path.read_bytes(); md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != source["declaredBytes"] or md5 != source["fileDataMd5"]:
            raise ValueError(f"dynamic-model:{path}: source length/MD5 expected={source['declaredBytes']}/{source['fileDataMd5']} actual={len(data)}/{md5}")
        decoded = decode_models(data, layout, main, source=source["path"])
        receipts.append(dict(path=str(path), virtualPath=source["path"], sha256=hashlib.sha256(data).hexdigest().upper(), md5=md5, models=len(decoded)))
        for row in decoded:
            row["source"] = source["path"]; key = row["values"]["PathHash"] & ((1 << 64)-1)
            row["pathHashHex"] = f"{key:016X}"; row["assets"] = assets.get(key, [])
            row["pathStatus"] = "unique_authored_path" if len(row["assets"]) == 1 else "ambiguous" if row["assets"] else "unresolved"
            counts[row["pathStatus"]] += 1; rows.append(row)
    scene_join = None
    if scene_receipt is not None:
        saved = json.loads(scene_receipt.read_text("utf-8"))
        scene = audit_scene_selection(selection_path=Path(saved["selection"]["path"]), summary_path=outer_path,
            ledger_path=ledger_path, expected_input_set=expected_input_set, cli=cli,
            work_root=REPO_ROOT/"tmp/animestudio/collision_ownership", reuse_path=scene_receipt)
        if scene["status"] != "complete":
            raise ValueError(f"dynamic-model: selected scene receipt failed: {scene['failures'][:3]}")
        scene_join = dict(receipt=str(scene_receipt), sha256=sha256_file(scene_receipt),
                          **join_model_colliders(rows, scene, source_bundles))
    return dict(schema=AUDIT_SCHEMA, status="validated", nativeInputs=native, contracts=contracts,
                inputSetSha256=outer["inputSetSha256"], provenance=provenance,
                manifest=dict(path=str(manifest), sha256=sha256_file(manifest), native=manifest_native),
                counts=dict(files=len(receipts), models=len(rows), pathStatuses=dict(counts)), files=receipts, models=rows,
                sceneJoin=scene_join,
                evidenceBoundary="Exact stored Model fields and authenticated PathHash-to-manifest asset rows. Rotation remains its stored three-axis representation. Authored asset/bundle identity does not prove prefab root identity, selected grid matrix, live instantiation, animation or collider activation.")


def validate_receipt(receipt_path: Path, *, gameassembly: Path, metadata: Path,
                     outer_path: Path, ledger_path: Path, cli: Path = DEFAULT_CLI,
                     root: Path = REPO_ROOT) -> dict:
    """Recompute Model values/path joins from an admitted saved source set.

    Saved derived models and collider bindings are not proof. This API checks
    their source paths/hashes, then repeats the maintained native/source audit
    without streaming or exporting. Equivalent absolute/relative source paths
    identify one input root; different roots or selections remain failures.
    """
    original = receipt_path.read_bytes(); saved = json.loads(original)
    if saved.get("schema") != AUDIT_SCHEMA or saved.get("status") != "validated" or saved.get("failures"):
        raise ValueError("model receipt is not a validated v2 source corpus")
    for field, path in (("outerReportSha256", outer_path), ("ledgerSha256", ledger_path)):
        actual = sha256_file(path).upper(); expected = saved["provenance"][field].upper()
        if actual != expected:
            raise ValueError(f"model receipt {field}: source={path}; expected={expected}; actual={actual}")
    manifest = root / saved["manifest"]["path"]
    if sha256_file(manifest).upper() != saved["manifest"]["sha256"].upper():
        raise ValueError(f"model receipt manifest SHA256 differs: {manifest}")
    roots, expected_files = set(), {}
    prefix = "Data/DynamicStreaming/"
    for row in saved["files"]:
        virtual = row["virtualPath"]
        if not virtual.startswith(prefix):
            raise ValueError(f"model receipt source prefix differs: {virtual}")
        relative = Path(virtual[len(prefix):])
        if relative.is_absolute() or ".." in relative.parts or ":" in str(relative):
            raise ValueError(f"model receipt unsafe virtual path: {virtual}")
        path = (root / row["path"]).resolve(); base = path
        for _ in relative.parts:
            base = base.parent
        if (base / relative).resolve() != path or virtual in expected_files:
            raise ValueError(f"model receipt duplicate or incompatible physical path: {virtual}")
        roots.add(base); expected_files[virtual] = {**row, "path": str(path)}
    if len(roots) != 1:
        raise ValueError(f"model receipt needs one source root; actual={len(roots)}")
    outer = json.loads(outer_path.read_bytes())
    paths = {receipt_path, outer_path, ledger_path, manifest, gameassembly, metadata, gameassembly.parent / "UnityPlayer.dll"}
    paths.update(root / row["path"] for row in saved["files"])
    paths.update(Path(row["path"]) for row in outer["sourceFingerprints"] + outer["buildFingerprints"])
    snapshots = {str(path): (path.stat().st_size, path.stat().st_mtime_ns) for path in paths}
    current = audit(gameassembly=gameassembly, metadata=metadata, input_root=next(iter(roots)),
                    manifest=manifest, outer_path=outer_path, ledger_path=ledger_path,
                    expected_input_set=saved["inputSetSha256"], cli=cli)
    if current.get("schema") != AUDIT_SCHEMA or current.get("status") != "validated" or current.get("failures"):
        raise ValueError("model source reanalysis did not validate")
    actual_files = {row["virtualPath"]: {**row, "path": str(Path(row["path"]).resolve())} for row in current["files"]}
    if current["nativeInputs"] != saved["nativeInputs"]:
        for field in sorted(set(current["nativeInputs"]) | set(saved["nativeInputs"])):
            if current["nativeInputs"].get(field) != saved["nativeInputs"].get(field):
                raise ValueError(f"model receipt native gate {field}: source={gameassembly}; "
                                 f"expected={saved['nativeInputs'].get(field)}; actual={current['nativeInputs'].get(field)}")
    for virtual in sorted(set(expected_files) | set(actual_files)):
        expected, actual = expected_files.get(virtual), actual_files.get(virtual)
        if expected == actual:
            continue
        field = next((key for key in sorted(set(expected or {}) | set(actual or {}))
                      if (expected or {}).get(key) != (actual or {}).get(key)), "presence")
        raise ValueError(f"model receipt source gate {field}: source={virtual}; "
                         f"expected={str((expected or {}).get(field))[:240]}; actual={str((actual or {}).get(field))[:240]}")
    if receipt_path.read_bytes() != original:
        raise ValueError("model receipt changed during source reanalysis")
    current["currentInputSnapshots"] = snapshots
    check_receipt_snapshot(current)
    return current


def check_receipt_snapshot(report: dict) -> None:
    for filename, expected in report["currentInputSnapshots"].items():
        stat = Path(filename).stat()
        if (stat.st_size, stat.st_mtime_ns) != tuple(expected):
            raise ValueError(f"model receipt input changed during consumption: {filename}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("gameassembly", "metadata", "input-root", "manifest", "outer-report", "ledger"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--scene-receipt", type=Path,
                        help="Revalidate a selected scene extraction and join declared prefab roots to stored models.")
    parser.add_argument("--output", type=Path, default=REPO_ROOT/"reports/animestudio/dynamic_model_current_latest.json")
    args = parser.parse_args(argv)
    try:
        report = audit(gameassembly=args.gameassembly, metadata=args.metadata, input_root=args.input_root,
                       manifest=args.manifest, outer_path=args.outer_report, ledger_path=args.ledger,
                       expected_input_set=args.expected_input_set_sha256, scene_receipt=args.scene_receipt)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError, struct.error) as error:
        report = dict(schema=AUDIT_SCHEMA, status="failed", failures=[dict(check="model_native_or_source_gate", detail=str(error)[:1600])])
    destination = args.output if report["status"] == "validated" else args.output.with_name(args.output.stem+".failed"+args.output.suffix)
    atomic_write_text(destination, json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    print(json.dumps(dict(status=report["status"], counts=report.get("counts"), failures=report.get("failures", []), report=str(destination))), flush=True)
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
