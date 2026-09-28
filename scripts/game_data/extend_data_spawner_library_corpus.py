"""Audit authored SpawnerConfig monster-action keys against their enemy library.

Every reported row is backed by an exact sequential MemoryPack decode and by
the current VFS ledger's logical-file length and MD5. This proves the authored
action-to-library relation, not live monster selection or protocol template ID.

The gate requires current JsonData export freshness, rechecks every
SpawnerConfig logical file against the VFS ledger (exact path, length and
plaintext MD5), and decodes the wave, group and action maps sequentially to
physical EOF. Every decoded ``SpawnMonsterFromTemplateV2.libraryKey`` selects
exactly one ``enemyLibrary[].key`` in the same file, yielding that action's
authored ``enemyId`` and optional ``overrideAIConfig``; other action union
tags keep the reader's bounded status. Every distinct authored ``enemyId`` is
an ``EnemyTable`` key, and some are in the graph-linked AI subset: an authored
key join only. In the current corpus, items selected by monster actions carry
positive ``bornTemplateId`` strings that differ from the item's ``enemyId``,
and every stored ``bornBehaviorData`` is null. Neither these bytes nor the
source graph's authored spawner-enemy rule converts an item to
``SCENE_MONSTER.commonInfo.templateid`` or selects an ``EnemyInfo``/
``EntityNode``; the missing witness is the producer or consumer that carries
one stored entry's ID into a selected protocol message or entity-data node.

The selected native fallback branch that reads those born fields is checked by
``extend_data_spawner_library_native``. Pass ``--game-root`` and the VFS
audit's ``inputSetSha256``; the default report is
``reports/animestudio/extend_data_spawner_library_latest.json``.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.extend_data_spawner_library_corpus")

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.extend_data_spawner_library_native import audit_extend_data_spawner_library_native
from scripts.game_data.extraction.verify_export_freshness import Requirements, build_report
from scripts.game_data.memorypack.corpus_gate import _read_outer_and_ledger, family_rows
from scripts.game_data.spawner_binary import (
    decode_spawner_named_prefix, decode_spawner_wave_map_sequential,
)
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.extend-data-spawner-library-corpus.v2"
PREFIX = "Data/Json/SpawnerConfig/"
PATH_PATTERN = re.compile(r"Data/Json/SpawnerConfig/(?:[^/]+/)*[^/]+\.json")


class SpawnerLibraryCorpusError(ValueError):
    """A current SpawnerConfig source or action-to-library join did not close."""


def _require(ok: bool, detail: str) -> None:
    if not ok:
        raise SpawnerLibraryCorpusError(f"extend-data-spawner-library:{detail}")


def _export_path(export_root: Path, virtual_path: str) -> Path:
    parts = PurePosixPath(virtual_path).parts
    _require(len(parts) >= 4 and parts[:3] == ("Data", "Json", "SpawnerConfig")
             and all(part not in ("", ".", "..") for part in parts),
             f"unsafe-virtual-path:{virtual_path}")
    root = (export_root / "game/Json/SpawnerConfig").resolve()
    candidate = root.joinpath(*parts[3:]).resolve()
    _require(candidate.is_relative_to(root), f"export-path-escape:{virtual_path}")
    return candidate


def _selected_library_item(
    by_key: dict[str, dict[str, Any]], action: dict[str, Any], *, source: str,
) -> dict[str, Any]:
    key = action.get("libraryKey")
    _require(isinstance(key, str) and bool(key) and key in by_key,
             f"action-library-key:{source}:{action.get('actionId')}:{key!r}")
    item = by_key[key]
    _require(isinstance(item.get("enemyId"), str) and bool(item["enemyId"]),
             f"action-enemy-id:{source}:{action.get('actionId')}:{key!r}")
    return item


def _check_born_fields(items: list[dict[str, Any]], *, source: str) -> None:
    for item in items:
        index = item["index"]
        template = item.get("bornTemplateId")
        behavior = item.get("bornBehaviorData")
        _require(isinstance(template, str),
                 f"born-template-type:{source}:{index}:{type(template).__name__}")
        _require(behavior is None,
                 f"born-behavior-not-null:{source}:{index}:{type(behavior).__name__}")


def audit(
    *, outer_summary: Path, outer_ledger: Path, expected_input_set_sha256: str,
    game_root: Path, export_root: Path, export_summary: Path,
) -> dict[str, Any]:
    native = audit_extend_data_spawner_library_native(
        gameassembly=game_root.parent / "GameAssembly.dll",
        metadata=game_root / "il2cpp_data/Metadata/global-metadata.dat",
    )
    _require(native["status"] == "validated",
             f"native:{native['status']}:{native['detail']}")
    freshness = build_report(
        game_root=game_root, output_root=export_root, summary_path=export_summary,
        sources=("StreamingAssets", "Persistent"),
        requirements=Requirements(structured=("json-data",)),
    )
    _require(freshness.get("fresh") is True, "export-freshness")
    required = {item["kind"]: item for item in freshness.get("requiredOutputs", [])}
    json_output = required.get("game/Json")
    _require(json_output is not None and json_output["fresh"] and json_output["partial"] is None,
             "export-json-scope")

    outer, _header, file_rows, provenance = _read_outer_and_ledger(
        outer_summary, outer_ledger,
        expected_input_set_sha256=expected_input_set_sha256,
    )
    rows = family_rows(
        file_rows, expected_input=expected_input_set_sha256.upper(),
        prefix=PREFIX, pattern=PATH_PATTERN, label="SpawnerConfig",
    )
    root = export_root / "game/Json/SpawnerConfig"
    actual_files = {p.resolve() for p in root.rglob("*.json")}
    expected_files = {_export_path(export_root, row["virtualPath"]) for row in rows}
    _require(actual_files == expected_files,
             f"export-file-set:{len(actual_files)}:{len(expected_files)}")

    counts: Counter[str] = Counter({
        "enemyLibraryItemsWithBornBehaviorData": 0,
        "enemyLibraryBornTemplateIdEqualsEnemyId": 0,
        "monsterActionsWithBornBehaviorData": 0,
    })
    joins: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for row in rows:
        virtual_path = row["virtualPath"]
        path = _export_path(export_root, virtual_path)
        data = path.read_bytes()
        digest = hashlib.md5(data).hexdigest().upper()
        _require(len(data) == row["length"]
                 and digest == str(row["recomputedFileDataMd5"]).upper(),
                 f"logical-bytes:{virtual_path}:{len(data)}/{row['length']}:{digest}/{row['recomputedFileDataMd5']}")
        try:
            prefix = decode_spawner_named_prefix(data)
            waves = decode_spawner_wave_map_sequential(
                data, wave_map_offset=prefix["waveMapOffset"],
            )
        except (ValueError, RuntimeError) as error:
            raise SpawnerLibraryCorpusError(f"decode:{virtual_path}:{error}") from error
        items = prefix["enemyLibrary"]
        by_key = {item["key"]: item for item in items}
        _require(len(by_key) == len(items) and all(by_key),
                 f"library-key-uniqueness:{virtual_path}")
        _check_born_fields(items, source=virtual_path)
        file_join_count = 0
        for wave in waves["waves"]:
            for group in wave["groupMap"]:
                for action in group["actionMap"]:
                    tag = action["unionTag"]
                    counts[f"actionTag{tag}"] += 1
                    if tag != 5:
                        continue
                    item = _selected_library_item(by_key, action, source=virtual_path)
                    joins.append({
                        "sourceFile": virtual_path,
                        "configId": prefix["configId"],
                        "waveId": wave["waveId"],
                        "groupId": group["groupId"],
                        "actionId": action["actionId"],
                        "actionMapKey": action["mapKey"],
                        "libraryKey": action["libraryKey"],
                        "enemyLibraryIndex": item["index"],
                        "enemyId": item["enemyId"],
                        "overrideAIConfig": item["overrideAIConfig"],
                        "bornTemplateId": item["bornTemplateId"],
                        "bornBehaviorData": item["bornBehaviorData"],
                    })
                    file_join_count += 1
                    counts["monsterActionsWithBornTemplateId"] += bool(item["bornTemplateId"])
        counts["files"] += 1
        counts["enemyLibraryItems"] += len(items)
        counts["enemyLibraryItemsWithBornTemplateId"] += sum(bool(item["bornTemplateId"]) for item in items)
        counts["enemyLibraryBornTemplateIdEqualsEnemyId"] += sum(
            bool(item["bornTemplateId"]) and item["bornTemplateId"] == item["enemyId"]
            for item in items
        )
        counts["monsterActionsJoined"] += file_join_count
        files.append({
            "sourceFile": virtual_path, "logicalSha256": hashlib.sha256(data).hexdigest().upper(),
            "enemyLibraryCount": len(items), "waveCount": waves["waveCount"],
            "monsterActionsJoined": file_join_count,
            "schemaStatus": waves["schemaStatus"],
        })

    _require(counts["monsterActionsJoined"] > 0, "no-monster-actions")
    return {
        "schema": SCHEMA, "status": "validated",
        "source": {
            "inputSetSha256": outer["inputSetSha256"],
            "outer": provenance["outer"], "ledger": provenance["ledger"],
            "sourceFingerprints": provenance["sourceFingerprints"],
            "exportSummary": str(export_summary),
            "exportFreshnessProvenance": freshness.get("provenance"),
            "nativeContractSha256": native["contractSha256"],
        },
        "counts": dict(sorted(counts.items())),
        "files": files,
        "actionLibraryJoins": joins,
        "evidenceBoundary": {
            "exact": "Current VFS ledger logical files match exported bytes; exact current SpawnerConfig prefix and sequential wave/action decoder consume each file to EOF. Every decoded tag-5 action libraryKey matches one enemyLibrary.key in the same file. Each item has a parsed bornTemplateId and null bornBehaviorData on this corpus.",
            "conditional": "Selected native AI initialization can read a chosen item's bornTemplateId and bornBehaviorData on its fallback branch; this report does not select a live action or monster message.",
            "unresolved": "Other action union tags retain their reader boundary. The join does not show that enemyLibrary.enemyId equals SCENE_MONSTER.commonInfo.templateid for a live entity.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path,
                        default=REPO_ROOT / "reports/animestudio/vfs_understanding_latest.json")
    parser.add_argument("--outer-ledger", type=Path,
                        default=REPO_ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz")
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, default=REPO_ROOT / "export_full")
    parser.add_argument("--export-summary", type=Path,
                        default=REPO_ROOT / "reports/export/export_full_summary.json")
    parser.add_argument("--output", type=Path,
                        default=REPO_ROOT / "reports/animestudio/extend_data_spawner_library_latest.json")
    args = parser.parse_args()
    try:
        report = audit(
            outer_summary=args.outer_summary, outer_ledger=args.outer_ledger,
            expected_input_set_sha256=args.expected_input_set_sha256,
            game_root=args.game_root, export_root=args.export_root,
            export_summary=args.export_summary,
        )
    except (ValueError, RuntimeError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print(f"ExtendData spawner library audit failed: {type(error).__name__}: {error}")
        return 2
    atomic_write_text(args.output, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"Spawner library validated: {report['counts']['files']} files, "
          f"{report['counts']['monsterActionsJoined']} authored monster-action joins; "
          f"report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
