"""Join authenticated CompressData ordinals to exported BehaviourTree assets.

The native gate proves the field-to-archive route. This corpus gate checks the
current VFS archive, selected native build, exported Unity script identity and
export freshness before publishing source-CAB/PathID-to-ordinal ownership.
Export freshness may rely on the pre-provenance summary and is reported as
such; the join does not imply scene/enemy selection or live execution.

No decoded graph root carries an owner key, so ownership comes from the
exported side (contract ``extend_data_graph_owner.json``): each
``NodeCanvas.BehaviourTrees.BehaviourTree`` MonoBehaviour's
``_serializedGraphStringIndex`` names an archive ordinal. The gate checks the
MonoScript identity and object script pointer, source CAB and PathID, the
enabled compression flag, an empty inline graph, the document hash and full
ordinal coverage. Several distinct authored assets share an ordinal, so every
source-CAB/PathID-to-ordinal assignment is kept rather than forced
one-to-one. An inline ``CanvasGraph`` with compression disabled is excluded
despite its incidental index; index kind/range and script-pointer mutations
are rejected. Under the freshness guard this closes authored asset ownership
for the exported set, without independently authenticating each Unity
object's current installed bytes.

Pass ``--game-root`` (the installed ``Endfield_Data``) and the VFS audit's
``inputSetSha256``; the report is
``reports/animestudio/extend_data_graph_owner_latest.json``.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.extend_data_graph_owner_corpus")

import argparse
import copy
import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.extend_data_compress_corpus import (
    DEFAULT_CLI, audit as audit_compress,
)
from scripts.game_data.extend_data_graph_native import audit_extend_data_graph_native
from scripts.game_data.extraction.verify_export_freshness import (
    Requirements, build_report,
)
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.unity_store import UnityObjectRow, open_store
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "extend_data_graph_owner.json"
SCHEMA = "endfield.extend-data-graph-owner-contract.v1"
AUDIT_SCHEMA = "endfield.extend-data-graph-owner-corpus.v1"


class GraphOwnerError(ValueError):
    """A source, native, script, index or owner-identity check failed."""


def _require(ok: bool, detail: str) -> None:
    if not ok:
        raise GraphOwnerError(f"extend-data-graph-owner:{detail}")


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def _checked_document(store: Any, row: UnityObjectRow) -> dict[str, Any]:
    raw = store.read_bytes(row.type, row.name)
    _require(hashlib.sha256(raw).hexdigest().casefold() == row.sha256.casefold(),
             f"stored-document-sha256:{row.ref}")
    doc = json.loads(raw.decode("utf-8-sig"))
    _require(isinstance(doc, dict), f"document-root:{row.ref}")
    return doc


def _graph_row(
    row: UnityObjectRow, doc: dict[str, Any], contract: dict[str, Any],
    *, script_path_id: int, script_source_file: str, record_count: int,
) -> dict[str, Any]:
    fields = contract["fields"]
    label = row.ref
    header = doc.get("$animestudio")
    _require(isinstance(header, dict), f"header:{label}")
    _require(header.get("pathId") == row.path_id and header.get("sourceFile") == row.source_file,
             f"object-identity:{label}")
    _require(header.get("scriptPathId") == script_path_id and row.script_path_id == script_path_id,
             f"script-index:{label}")
    _require(isinstance(row.source_file, str) and bool(row.source_file)
             and type(row.path_id) is int, f"owner-key:{label}")
    pointer = doc.get(fields["scriptPointer"])
    _require(isinstance(pointer, dict)
             and pointer.get("m_PathID") == script_path_id,
             f"script-pointer:{label}")
    references_raw = header.get("pptrReferences")
    _require(isinstance(references_raw, list), f"script-references-kind:{label}")
    references = [ref for ref in references_raw
                  if isinstance(ref, dict) and ref.get("path") == fields["scriptReferencePath"]]
    _require(len(references) == 1
             and references[0].get("pathId") == script_path_id
             and references[0].get("expectedTargetSourceFile") == script_source_file,
             f"script-target:{label}")
    _require(doc.get("m_Name") == row.object_name, f"object-name:{label}")
    raw_object_sha = header.get("rawDataSha256")
    _require(isinstance(raw_object_sha, str)
             and re.fullmatch(r"[0-9a-fA-F]{64}", raw_object_sha) is not None,
             f"raw-object-sha256-kind:{label}")
    enabled = doc.get(fields["compressEnabled"])
    _require(type(enabled) is int and enabled in (0, contract["compressedFlagValue"]),
             f"compression-flag:{label}")
    index = doc.get(fields["archiveIndex"])
    _require(type(index) is int, f"archive-index-kind:{label}")
    inline = doc.get(fields["inlineGraph"])
    _require(isinstance(inline, str), f"inline-graph-kind:{label}")
    result = {
        "asset": row.ref, "objectName": row.object_name,
        "sourceFile": row.source_file, "pathId": row.path_id,
        "documentSha256": row.sha256.upper(),
        "rawObjectSha256": raw_object_sha.upper(),
    }
    if enabled != contract["compressedFlagValue"]:
        result.update(storage="inline", inlineLength=len(inline), incidentalIndex=index)
        return result
    _require(not contract["requireEmptyInlineGraphWhenCompressed"] or inline == "",
             f"compressed-inline-content:{label}")
    _require(0 <= index < record_count, f"archive-index-range:{label}:{index}")
    result.update(storage="compressed", ordinal=index)
    return result


def _mutation_negatives(
    row: UnityObjectRow, doc: dict[str, Any], contract: dict[str, Any],
    *, script_path_id: int, script_source_file: str, record_count: int,
) -> list[dict[str, str]]:
    cases = [
        ("out-of-range-index", lambda value: value.__setitem__(contract["fields"]["archiveIndex"], record_count),
         "archive-index-range"),
        ("string-index", lambda value: value.__setitem__(contract["fields"]["archiveIndex"], "0"),
         "archive-index-kind"),
        ("changed-script-pointer", lambda value: value[contract["fields"]["scriptPointer"]].__setitem__(
            "m_PathID", script_path_id + 1), "script-pointer"),
    ]
    rejected = []
    for name, mutate, expected in cases:
        changed = copy.deepcopy(doc)
        mutate(changed)
        try:
            _graph_row(row, changed, contract, script_path_id=script_path_id,
                       script_source_file=script_source_file, record_count=record_count)
        except GraphOwnerError as error:
            _require(expected in str(error), f"negative-wrong-rejection:{name}:{error}")
            rejected.append({"name": name, "status": "rejected", "detail": str(error)})
        else:
            raise GraphOwnerError(f"negative-accepted:{name}")
    return rejected


def audit(
    *, outer_summary: Path, outer_ledger: Path, expected_input_set_sha256: str,
    cli: Path, game_root: Path, export_root: Path, export_summary: Path,
    contract_path: Path = CONTRACT,
) -> dict[str, Any]:
    contract, contract_sha = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="extend-data-graph-owner",
        status="reviewed-structural-only",
    )
    compress = audit_compress(outer_summary, outer_ledger, expected_input_set_sha256, cli)
    _require(compress["status"] == "validated", "compress-corpus")
    _require(_same_path(compress["source"]["primaryAssets"], game_root / "Persistent")
             and _same_path(compress["source"]["fallbackAssets"], game_root / "StreamingAssets"),
             "outer-unity-root-selection")
    native = audit_extend_data_graph_native(
        gameassembly=game_root.parent / "GameAssembly.dll",
        metadata=game_root / "il2cpp_data/Metadata/global-metadata.dat",
    )
    _require(native["status"] == "validated", f"native-route:{native['status']}:{native['detail']}")
    freshness = build_report(
        game_root=game_root, output_root=export_root, summary_path=export_summary,
        sources=("StreamingAssets", "Persistent"),
        requirements=Requirements(unity=("MonoBehaviour", "MonoScript")),
    )
    _require(freshness.get("fresh") is True, f"unity-export-freshness:{freshness.get('error', 'stale')}")
    required = {item["kind"]: item for item in freshness.get("requiredOutputs", [])}
    for kind in ("game/Unity/MonoBehaviour", "game/Unity/MonoScript"):
        item = required.get(kind)
        _require(item is not None and item["fresh"] and item["partial"] is None,
                 f"unity-export-scope:{kind}")
    store = open_store(export_root)
    try:
        identity = contract["scriptIdentity"]
        candidates = []
        for row in store.rows("MonoScript"):
            if row.object_name != identity["className"]:
                continue
            doc = _checked_document(store, row)
            if (doc.get("m_ClassName"), doc.get("m_Namespace"), doc.get("m_AssemblyName")) == (
                identity["className"], identity["namespace"], identity["assemblyName"]
            ):
                candidates.append((row, doc))
        _require(len(candidates) == 1, f"script-identity-count:{len(candidates)}")
        script, script_doc = candidates[0]
        script_header = script_doc.get("$animestudio")
        _require(type(script.path_id) is int and isinstance(script.source_file, str)
                 and bool(script.source_file) and isinstance(script_header, dict)
                 and script_header.get("pathId") == script.path_id
                 and script_header.get("sourceFile") == script.source_file,
                 "script-owner-key")
        record_count = compress["framing"]["recordCount"]
        compressed: list[dict[str, Any]] = []
        inline: list[dict[str, Any]] = []
        owner_keys: set[tuple[str, int]] = set()
        sample: tuple[UnityObjectRow, dict[str, Any]] | None = None
        for row in store.iter_rows_by_script_path_id(script.path_id, "MonoBehaviour"):
            doc = _checked_document(store, row)
            item = _graph_row(row, doc, contract, script_path_id=script.path_id,
                              script_source_file=script.source_file, record_count=record_count)
            owner_key = (item["sourceFile"], item["pathId"])
            _require(owner_key not in owner_keys, f"duplicate-owner-key:{owner_key}")
            owner_keys.add(owner_key)
            if item["storage"] == "compressed":
                compressed.append(item)
                if sample is None:
                    sample = row, doc
            else:
                inline.append(item)
        _require(bool(compressed) and sample is not None, "no-compressed-graph-assets")
        groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in compressed:
            groups[row["ordinal"]].append(row)
        missing = sorted(set(range(record_count)) - set(groups))
        _require(not contract["requireFullOrdinalCoverage"] or not missing,
                 f"missing-archive-ordinals:{missing[:16]}")
        _require(contract["allowRepeatedOrdinals"] or all(len(group) == 1 for group in groups.values()),
                 "repeated-archive-ordinal")
        duplicates = [
            {"ordinal": index, "owners": [item["asset"] for item in group]}
            for index, group in sorted(groups.items()) if len(group) > 1
        ]
        negatives = _mutation_negatives(
            sample[0], sample[1], contract, script_path_id=script.path_id,
            script_source_file=script.source_file, record_count=record_count,
        )
    finally:
        store.close()
    return {
        "schema": AUDIT_SCHEMA, "status": "validated",
        "contractSha256": contract_sha,
        "source": {
            "inputSetSha256": compress["source"]["inputSetSha256"],
            "archiveSourceSha256": compress["framing"]["sourceSha256"],
            "nativeContractSha256": native["contractSha256"],
            "exportSummary": str(export_summary),
            "exportFreshnessProvenance": freshness.get("provenance"),
            "exportSourceFingerprints": {
                item["source"]: item["current"]["fingerprint"]
                for item in freshness.get("sources", [])
            },
        },
        "script": {
            "asset": script.ref, "sourceFile": script.source_file,
            "pathId": script.path_id, "documentSha256": script.sha256.upper(),
            "identity": identity,
        },
        "coverage": {
            "archiveRecordCount": record_count,
            "compressedGraphAssetCount": len(compressed),
            "uniqueOrdinals": len(groups),
            "inlineGraphAssetCount": len(inline),
            "missingOrdinals": missing,
            "duplicateOrdinalGroupCount": len(duplicates),
            "repeatedOwnerCount": len(compressed) - len(groups),
        },
        "duplicateOrdinals": duplicates,
        "compressedOwners": sorted(compressed, key=lambda item: (item["ordinal"], item["sourceFile"], item["pathId"])),
        "inlineAssets": inline,
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
                        default=REPO_ROOT / "reports/animestudio/extend_data_graph_owner_latest.json")
    args = parser.parse_args()
    try:
        report = audit(
            outer_summary=args.outer_summary, outer_ledger=args.outer_ledger,
            expected_input_set_sha256=args.expected_input_set_sha256, cli=args.cli,
            game_root=args.game_root, export_root=args.export_root,
            export_summary=args.export_summary, contract_path=args.contract,
        )
    except (GraphOwnerError, ValueError, RuntimeError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"ExtendData graph owner audit failed: {type(error).__name__}: {error}")
        return 2
    atomic_write_text(args.output, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    totals = report["coverage"]
    print(f"ExtendData graph owners validated: {totals['compressedGraphAssetCount']} assets / "
          f"{totals['uniqueOrdinals']} archive ordinals; report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
