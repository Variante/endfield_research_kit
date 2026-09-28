"""Gate authored EnemyAIConfigData-to-CompressData graph references.

The route is AssetBundle container path/PathID -> AI-config aiBB pointer ->
blackboard graph-mode RID -> exact managed-reference canvasGraph pointer ->
BehaviourTree asset -> authenticated archive ordinal. The selected native
synchronous path reads EnemyTable.aiTemplateId and forms an AIConfig asset
path; each reported Table-to-config match must also have that path.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.extend_data_graph_ai_corpus")

import argparse
import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.extend_data_compress_corpus import DEFAULT_CLI
from scripts.game_data.extend_data_graph_ai_native import audit_extend_data_graph_ai_native
from scripts.game_data.extend_data_graph_owner_corpus import (
    _checked_document, audit as audit_owner,
)
from scripts.game_data.extraction.verify_export_freshness import Requirements, build_report
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.unity_store import UnityObjectRow, open_store
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "extend_data_graph_ai.json"
SCHEMA = "endfield.extend-data-graph-ai-contract.v3"
AUDIT_SCHEMA = "endfield.extend-data-graph-ai-corpus.v3"


class GraphAiError(ValueError):
    """A stored keyed graph relation is absent, malformed, or stale."""


def _require(ok: bool, detail: str) -> None:
    if not ok:
        raise GraphAiError(f"extend-data-graph-ai:{detail}")


def _checked_native_asset_path(
    ai_key: str, stored_path: str, *, prefix: str, pattern: str,
) -> str:
    """Require a stored AssetBundle path to equal the native-formatted key path."""
    _require(isinstance(ai_key, str) and bool(ai_key)
             and isinstance(stored_path, str) and bool(stored_path),
             "native-ai-path-input")
    expected = pattern.format(prefix, ai_key)
    _require(stored_path.casefold() == expected.casefold(),
             f"native-ai-path:{ai_key}:{stored_path!r}:{expected!r}")
    return expected


def _checked_enemy_row_identity(enemy_key: str, row: dict[str, Any]) -> None:
    _require(isinstance(enemy_key, str) and isinstance(row, dict)
             and row.get("enemyId") == enemy_key,
             f"enemy-row-identity:{enemy_key}")


def _identity(store: Any, identity: dict[str, str]) -> UnityObjectRow:
    found = []
    for row in store.rows_by_object_name("MonoScript", identity["className"]):
        doc = _checked_document(store, row)
        if (doc.get("m_ClassName"), doc.get("m_Namespace"), doc.get("m_AssemblyName")) == (
            identity["className"], identity["namespace"], identity["assemblyName"]
        ):
            header = doc.get("$animestudio")
            _require(isinstance(header, dict)
                     and header.get("sourceFile") == row.source_file
                     and header.get("pathId") == row.path_id,
                     f"script-owner:{row.ref}")
            found.append(row)
    _require(len(found) == 1, f"script-identity:{identity['className']}:{len(found)}")
    return found[0]


def _scripted_document(store: Any, row: UnityObjectRow, script: UnityObjectRow) -> dict[str, Any]:
    doc = _checked_document(store, row)
    header = doc.get("$animestudio")
    label = row.ref
    _require(isinstance(header, dict)
             and header.get("sourceFile") == row.source_file
             and header.get("pathId") == row.path_id
             and header.get("scriptPathId") == script.path_id
             and row.script_path_id == script.path_id
             and doc.get("m_Name") == row.object_name,
             f"scripted-identity:{label}")
    pointer = doc.get("m_Script")
    _require(isinstance(pointer, dict)
             and pointer.get("m_PathID") == script.path_id,
             f"script-pointer:{label}")
    references = header.get("pptrReferences")
    _require(isinstance(references, list), f"script-references:{label}")
    matched = [ref for ref in references if isinstance(ref, dict)
               and ref.get("path") == "$.m_Script"]
    _require(len(matched) == 1 and matched[0].get("pathId") == script.path_id
             and matched[0].get("expectedTargetSourceFile") == script.source_file,
             f"script-target:{label}")
    return doc


def _pointer_reference(
    doc: dict[str, Any], path: str, pointer: dict[str, Any],
    source_file: str, *, nullable: bool,
) -> dict[str, Any]:
    header = doc["$animestudio"]
    refs = header.get("pptrReferences")
    _require(isinstance(refs, list), f"pptr-reference-list:{path}")
    matched = [ref for ref in refs if isinstance(ref, dict) and ref.get("path") == path]
    _require(len(matched) == 1, f"pptr-reference-count:{path}:{len(matched)}")
    ref = matched[0]
    path_id = pointer.get("m_PathID")
    _require(type(pointer.get("m_FileID")) is int and pointer["m_FileID"] == 0
             and type(path_id) is int and (nullable or path_id != 0)
             and ref.get("fileId") == 0 and ref.get("pathId") == path_id,
             f"pptr-value:{path}")
    if path_id == 0:
        _require(ref.get("resolutionStatus") == "null", f"pptr-null:{path}")
    else:
        _require(ref.get("expectedTargetSourceFile") == source_file
                 and ref.get("targetSourceFile") == source_file
                 and ref.get("targetPathId") == path_id
                 and ref.get("targetType") == "MonoBehaviour"
                 and ref.get("resolutionStatus") == "resolved",
                 f"pptr-target:{path}:{path_id}")
    return ref


def _bundle_paths(store: Any, source_file: str) -> tuple[UnityObjectRow, dict[int, str]]:
    rows = list(store.iter_rows_by_source_file(source_file, "AssetBundle"))
    _require(len(rows) == 1, f"bundle-count:{source_file}:{len(rows)}")
    row = rows[0]
    doc = _checked_document(store, row)
    header = doc.get("$animestudio")
    _require(isinstance(header, dict)
             and header.get("sourceFile") == source_file
             and header.get("pathId") == row.path_id
             and header.get("typeTreeSource") == "serializedType",
             f"bundle-identity:{row.ref}")
    container = doc.get("m_Container")
    _require(isinstance(container, list) and bool(container), f"bundle-container:{row.ref}")
    by_id: dict[int, str] = {}
    paths: set[str] = set()
    for index, entry in enumerate(container):
        label = f"{row.ref}:m_Container[{index}]"
        _require(isinstance(entry, dict) and set(entry) == {"Key", "Value"},
                 f"bundle-entry:{label}")
        path = entry["Key"]
        info = entry["Value"]
        _require(isinstance(path, str) and bool(path) and path not in paths
                 and isinstance(info, dict) and isinstance(info.get("asset"), dict),
                 f"bundle-key-value:{label}")
        pointer = info["asset"]
        path_id = pointer.get("m_PathID")
        _require(type(pointer.get("m_FileID")) is int and pointer["m_FileID"] == 0
                 and type(path_id) is int and path_id != 0 and path_id not in by_id,
                 f"bundle-pointer:{label}")
        paths.add(path)
        by_id[path_id] = path
    return row, by_id


def _graph_modes(
    blackboard: dict[str, Any], source_file: str,
    owners: dict[tuple[str, int], dict[str, Any]],
    allowed_types: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], int]:
    label = blackboard["$animestudio"].get("name", "blackboard")
    graph = blackboard.get("graph")
    references = blackboard.get("references")
    _require(isinstance(graph, dict) and set(graph) == {"_keyData", "_valueData"}
             and isinstance(graph["_keyData"], list)
             and isinstance(graph["_valueData"], list)
             and len(graph["_keyData"]) == len(graph["_valueData"]),
             f"blackboard-graph-shape:{label}")
    _require(isinstance(references, dict)
             and isinstance(references.get("RefIds"), list),
             f"blackboard-references:{label}")
    ref_ids = references["RefIds"]
    _require("count" not in references or references["count"] == len(ref_ids),
             f"blackboard-reference-count:{label}")
    by_rid: dict[int, tuple[int, dict[str, Any]]] = {}
    for index, ref in enumerate(ref_ids):
        _require(isinstance(ref, dict) and type(ref.get("rid")) is int
                 and ref["rid"] not in by_rid,
                 f"blackboard-reference-rid:{label}:{index}")
        by_rid[ref["rid"]] = index, ref
    modes: list[dict[str, Any]] = []
    other = 0
    for index, (key, value) in enumerate(zip(graph["_keyData"], graph["_valueData"])):
        _require(isinstance(key, dict) and set(key) == {"tag"}
                 and isinstance(key["tag"], dict)
                 and set(key["tag"]) == {"tagId"}
                 and type(key["tag"]["tagId"]) is int
                 and isinstance(value, dict) and set(value) == {"graph"}
                 and isinstance(value["graph"], dict)
                 and set(value["graph"]) == {"rid"}
                 and type(value["graph"]["rid"]) is int,
                 f"blackboard-mode-envelope:{label}:{index}")
        rid = value["graph"]["rid"]
        _require(rid in by_rid, f"blackboard-mode-rid:{label}:{index}:{rid}")
        ref_index, ref = by_rid[rid]
        data = ref.get("data")
        if not isinstance(data, dict) or "canvasGraph" not in data:
            other += 1
            continue
        _require(ref.get("type") in allowed_types
                 and data.get("$decoded") is True
                 and data.get("exactTypeTreeDecoded") is True
                 and data.get("observedPayloadStatus") == "all serialized managed-reference TypeTree fields consumed",
                 f"canvas-graph-type-tree:{label}:{ref_index}")
        pointer = data["canvasGraph"]
        _require(isinstance(pointer, dict), f"canvas-graph-pointer:{label}:{ref_index}")
        path = f"$.references.RefIds[{ref_index}].data.canvasGraph"
        _pointer_reference(blackboard, path, pointer, source_file, nullable=True)
        path_id = pointer["m_PathID"]
        owner = owners.get((source_file, path_id)) if path_id else None
        _require(path_id == 0 or owner is not None,
                 f"canvas-graph-owner:{label}:{ref_index}:{path_id}")
        modes.append({
            "modeIndex": index, "modeTagId": key["tag"]["tagId"],
            "managedReferenceIndex": ref_index, "managedReferenceRid": rid,
            "managedReferenceType": ref["type"],
            "canvasGraphPathId": path_id,
            "graphAsset": owner["asset"] if owner else None,
            "ordinal": owner["ordinal"] if owner else None,
        })
    return modes, other


def _mutation_negatives(
    blackboard: dict[str, Any], source_file: str,
    owners: dict[tuple[str, int], dict[str, Any]],
    allowed_types: list[dict[str, str]], modes: list[dict[str, Any]],
) -> list[dict[str, str]]:
    sample = next(mode for mode in modes if mode["ordinal"] is not None)
    mode_index = sample["modeIndex"]
    ref_index = sample["managedReferenceIndex"]
    unknown_rid = max(ref["rid"] for ref in blackboard["references"]["RefIds"]) + 1
    cases = [
        ("changed-mode-rid", lambda doc: doc["graph"]["_valueData"][mode_index]["graph"].__setitem__(
            "rid", unknown_rid), "blackboard-mode-rid"),
        ("changed-canvas-graph-pointer", lambda doc: doc["references"]["RefIds"][ref_index]["data"]["canvasGraph"].__setitem__(
            "m_PathID", sample["canvasGraphPathId"] + 1), "pptr-value"),
        ("unverified-managed-reference", lambda doc: doc["references"]["RefIds"][ref_index]["data"].__setitem__(
            "exactTypeTreeDecoded", False), "canvas-graph-type-tree"),
    ]
    rejected = []
    for name, mutate, expected in cases:
        changed = copy.deepcopy(blackboard)
        mutate(changed)
        try:
            _graph_modes(changed, source_file, owners, allowed_types)
        except GraphAiError as error:
            _require(expected in str(error), f"negative-wrong-rejection:{name}:{error}")
            rejected.append({"name": name, "status": "rejected", "detail": str(error)})
        else:
            raise GraphAiError(f"negative-accepted:{name}")
    return rejected


def audit(
    *, outer_summary: Path, outer_ledger: Path, expected_input_set_sha256: str,
    cli: Path, game_root: Path, export_root: Path, export_summary: Path,
    contract_path: Path = CONTRACT,
) -> dict[str, Any]:
    contract, contract_sha = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="extend-data-graph-ai",
        status="reviewed-structural-only",
    )
    _require(contract.get("requireNativeAiConfigPathForMatchedEnemyRows") is True,
             "native-ai-path-contract")
    _require(contract.get("requireEnemyRowIdentityKey") is True,
             "enemy-row-identity-contract")
    native_ai = audit_extend_data_graph_ai_native(
        gameassembly=game_root.parent / "GameAssembly.dll",
        metadata=game_root / "il2cpp_data/Metadata/global-metadata.dat",
    )
    _require(native_ai["status"] == "validated",
             f"native-ai-route:{native_ai['status']}:{native_ai['detail']}")
    native_path = native_ai["route"]
    owner = audit_owner(
        outer_summary=outer_summary, outer_ledger=outer_ledger,
        expected_input_set_sha256=expected_input_set_sha256, cli=cli,
        game_root=game_root, export_root=export_root,
        export_summary=export_summary,
    )
    _require(owner["status"] == "validated", "owner-corpus")
    freshness = build_report(
        game_root=game_root, output_root=export_root, summary_path=export_summary,
        sources=("StreamingAssets", "Persistent"),
        requirements=Requirements(
            structured=("table",), unity=("AssetBundle", "MonoBehaviour", "MonoScript")
        ),
    )
    _require(freshness.get("fresh") is True, "export-freshness")
    required = {item["kind"]: item for item in freshness.get("requiredOutputs", [])}
    for kind in ("game/Table", "game/Unity/AssetBundle", "game/Unity/MonoBehaviour", "game/Unity/MonoScript"):
        item = required.get(kind)
        _require(item is not None and item["fresh"] and item["partial"] is None,
                 f"export-scope:{kind}")
    owner_by_key = {(item["sourceFile"], item["pathId"]): item
                    for item in owner["compressedOwners"]}
    source_cabs = sorted({item["sourceFile"] for item in owner["compressedOwners"]})
    store = open_store(export_root)
    try:
        config_script = _identity(store, contract["scriptIdentities"]["aiConfig"])
        blackboard_script = _identity(store, contract["scriptIdentities"]["blackboard"])
        paths_by_cab: dict[str, dict[int, str]] = {}
        bundles: list[dict[str, Any]] = []
        for cab in source_cabs:
            bundle, paths = _bundle_paths(store, cab)
            paths_by_cab[cab] = paths
            bundles.append({"sourceFile": cab, "asset": bundle.ref,
                            "documentSha256": bundle.sha256.upper(),
                            "containerCount": len(paths)})
        graph_assets = []
        for item in owner["compressedOwners"]:
            path = paths_by_cab[item["sourceFile"]].get(item["pathId"])
            _require(path is not None or not contract["requireAllCompressedOwnersInBundleContainer"],
                     f"graph-container-path:{item['asset']}")
            graph_assets.append({**item, "assetPath": path})
        config_rows = list(store.iter_rows_by_script_path_id(config_script.path_id, "MonoBehaviour"))
        _require(all(row.source_file in paths_by_cab for row in config_rows),
                 "ai-config-outside-graph-source-cabs")
        configs: list[dict[str, Any]] = []
        config_by_name: dict[str, dict[str, Any]] = {}
        blackboard_cache: dict[tuple[str, int], tuple[UnityObjectRow, dict[str, Any]]] = {}
        mode_totals: Counter[str] = Counter()
        negative_sample: tuple[dict[str, Any], str, list[dict[str, Any]]] | None = None
        for row in config_rows:
            doc = _scripted_document(store, row, config_script)
            cab = row.source_file
            _require(type(row.path_id) is int and row.path_id in paths_by_cab[cab],
                     f"ai-config-container-path:{row.ref}")
            _require(isinstance(row.object_name, str) and bool(row.object_name)
                     and row.object_name not in config_by_name,
                     f"ai-config-name-key:{row.ref}")
            pointer = doc.get("aiBB")
            _require(isinstance(pointer, dict), f"ai-blackboard-pointer:{row.ref}")
            _pointer_reference(doc, "$.aiBB", pointer, cab, nullable=False)
            bb_key = (cab, pointer["m_PathID"])
            if bb_key not in blackboard_cache:
                bb_rows = [candidate for candidate in store.rows_by_path_id(pointer["m_PathID"], cab)
                           if candidate.type == "MonoBehaviour"]
                _require(len(bb_rows) == 1, f"ai-blackboard-target:{row.ref}:{len(bb_rows)}")
                bb_row = bb_rows[0]
                blackboard_cache[bb_key] = bb_row, _scripted_document(store, bb_row, blackboard_script)
            bb_row, bb_doc = blackboard_cache[bb_key]
            modes, other_count = _graph_modes(
                bb_doc, cab, owner_by_key, contract["canvasGraphReferenceTypes"]
            )
            mode_totals["modesWithoutExactCanvasGraph"] += other_count
            mode_totals["canvasGraphModes"] += len(modes)
            mode_totals["nonNullCanvasGraphModes"] += sum(mode["ordinal"] is not None for mode in modes)
            if negative_sample is None and any(mode["ordinal"] is not None for mode in modes):
                negative_sample = bb_doc, cab, modes
            config = {
                "asset": row.ref, "sourceFile": cab, "pathId": row.path_id,
                "assetPath": paths_by_cab[cab][row.path_id],
                "nameKey": row.object_name, "documentSha256": row.sha256.upper(),
                "blackboardAsset": bb_row.ref,
                "blackboardPathId": bb_row.path_id,
                "blackboardDocumentSha256": bb_row.sha256.upper(),
                "graphModes": modes,
            }
            configs.append(config)
            config_by_name[row.object_name] = config
        _require(negative_sample is not None, "no-checked-ai-graph-mode")
        negatives = _mutation_negatives(
            negative_sample[0], negative_sample[1], owner_by_key,
            contract["canvasGraphReferenceTypes"], negative_sample[2],
        )
    finally:
        store.close()
    table_path = export_root / "game/Table/EnemyTable.json"
    table_raw = table_path.read_bytes()
    table_sha = hashlib.sha256(table_raw).hexdigest().upper()
    table = json.loads(table_raw.decode("utf-8-sig"))
    _require(isinstance(table, dict), "enemy-table-root")
    enemies: list[dict[str, Any]] = []
    unresolved_table_ids: Counter[str] = Counter()
    native_path_matches = 0
    negative_native_path: tuple[str, str] | None = None
    negative_enemy_row: tuple[str, dict[str, Any]] | None = None
    for enemy_key, row in table.items():
        _checked_enemy_row_identity(enemy_key, row)
        if negative_enemy_row is None:
            negative_enemy_row = enemy_key, row
        ai_key = row.get("aiTemplateId")
        _require(isinstance(ai_key, str), f"enemy-ai-key-kind:{enemy_key}")
        if not ai_key:
            continue
        config = config_by_name.get(ai_key)
        if config is None:
            unresolved_table_ids[ai_key] += 1
            continue
        selected_path = _checked_native_asset_path(
            ai_key, config["assetPath"],
            prefix=native_path["assetPathPrefix"], pattern=native_path["assetPathFormat"],
        )
        native_path_matches += 1
        if negative_native_path is None:
            negative_native_path = ai_key, config["assetPath"]
        linked = [mode for mode in config["graphModes"] if mode["ordinal"] is not None]
        if linked:
            enemies.append({
                "enemyId": row.get("enemyId"), "enemyRowKey": enemy_key,
                "aiTemplateId": ai_key, "aiConfigAsset": config["asset"],
                "nativeAiConfigAssetPath": selected_path,
                "aiConfigSourceFile": config["sourceFile"],
                "aiConfigPathId": config["pathId"],
                "graphModes": linked,
            })
    _require(native_path_matches > 0 and negative_native_path is not None,
             "no-native-ai-path-matches")
    try:
        _checked_native_asset_path(
            negative_native_path[0], negative_native_path[1] + ".changed",
            prefix=native_path["assetPathPrefix"], pattern=native_path["assetPathFormat"],
        )
    except GraphAiError as error:
        negatives.append({"name": "changed-ai-config-container-path",
                          "status": "rejected", "detail": str(error)})
    else:
        raise GraphAiError("negative-accepted:changed-ai-config-container-path")
    _require(negative_enemy_row is not None, "empty-enemy-table")
    changed_enemy_row = dict(negative_enemy_row[1], enemyId=negative_enemy_row[0] + ".changed")
    try:
        _checked_enemy_row_identity(negative_enemy_row[0], changed_enemy_row)
    except GraphAiError as error:
        negatives.append({"name": "changed-enemy-row-identity",
                          "status": "rejected", "detail": str(error)})
    else:
        raise GraphAiError("negative-accepted:changed-enemy-row-identity")
    return {
        "schema": AUDIT_SCHEMA, "status": "validated",
        "contractSha256": contract_sha,
        "source": {
            "inputSetSha256": owner["source"]["inputSetSha256"],
            "archiveSourceSha256": owner["source"]["archiveSourceSha256"],
            "ownerContractSha256": owner["contractSha256"],
            "nativeContractSha256": owner["source"]["nativeContractSha256"],
            "nativeAiContractSha256": native_ai["contractSha256"],
            "exportSummary": str(export_summary),
            "exportFreshnessProvenance": freshness.get("provenance"),
            "exportSourceFingerprints": {
                item["source"]: item["current"]["fingerprint"]
                for item in freshness.get("sources", [])
            },
            "enemyTable": str(table_path),
            "enemyTableSha256": table_sha,
        },
        "coverage": {
            "enemyRowsWithExactIdentityKey": len(table),
            "compressedGraphAssetCount": len(graph_assets),
            "graphAssetPathsResolved": sum(item["assetPath"] is not None for item in graph_assets),
            "aiConfigCountInOwnerCabs": len(configs),
            "distinctBlackboards": len(blackboard_cache),
            "aiConfigsWithNonNullCanvasGraph": sum(any(mode["ordinal"] is not None for mode in cfg["graphModes"]) for cfg in configs),
            "canvasGraphModes": mode_totals["canvasGraphModes"],
            "nonNullCanvasGraphModes": mode_totals["nonNullCanvasGraphModes"],
            "nullCanvasGraphModes": mode_totals["canvasGraphModes"] - mode_totals["nonNullCanvasGraphModes"],
            "modesWithoutExactCanvasGraph": mode_totals["modesWithoutExactCanvasGraph"],
            "enemyRowsWithExactAiNameAndGraph": len(enemies),
            "enemyRowsWithNativeAiConfigPath": native_path_matches,
            "enemyRowsWithNativeAiConfigPathAndGraph": len(enemies),
            "unmatchedNonemptyEnemyAiKeys": sum(unresolved_table_ids.values()),
        },
        "bundles": bundles,
        "graphAssets": graph_assets,
        "aiConfigs": configs,
        "enemyRows": enemies,
        "unmatchedEnemyAiKeys": dict(sorted(unresolved_table_ids.items())),
        "mutationNegatives": negatives,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path,
                        default=REPO_ROOT / "reports/animestudio/vfs_understanding_latest.json")
    parser.add_argument("--outer-ledger", type=Path,
                        default=REPO_ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz")
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, default=REPO_ROOT / "export_full")
    parser.add_argument("--export-summary", type=Path,
                        default=REPO_ROOT / "reports/export/export_full_summary.json")
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--output", type=Path,
                        default=REPO_ROOT / "reports/animestudio/extend_data_graph_ai_latest.json")
    args = parser.parse_args()
    try:
        report = audit(
            outer_summary=args.outer_summary, outer_ledger=args.outer_ledger,
            expected_input_set_sha256=args.expected_input_set_sha256,
            cli=args.cli, game_root=args.game_root, export_root=args.export_root,
            export_summary=args.export_summary, contract_path=args.contract,
        )
    except (GraphAiError, ValueError, RuntimeError, KeyError, TypeError, OSError,
            json.JSONDecodeError) as error:
        print(f"ExtendData graph AI audit failed: {type(error).__name__}: {error}")
        return 2
    atomic_write_text(args.output, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    coverage = report["coverage"]
    print(f"ExtendData graph AI validated: {coverage['graphAssetPathsResolved']} graph paths, "
          f"{coverage['nonNullCanvasGraphModes']} AI graph modes, "
          f"{coverage['enemyRowsWithNativeAiConfigPathAndGraph']} native-path enemy rows with graphs; "
          f"report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
