from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from build_endminf_external_pptr_closure import (  # noqa: E402
    TARGET_TYPES,
    build_report,
    main,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _stage(root: Path, *, serialized_file: str = "CAB-dependency", path_id: int = 77, pptr_path: str = "$.m_Materials[0]") -> Path:
    index = root / "stage" / "object_index.jsonl"
    index.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "recordType": "schema",
            "schemaVersion": 1,
            "schemaId": "fixture",
            "fields": [],
        },
        {
            "recordType": "object",
            "object": {
                "serializedFile": "CAB-root",
                "source": "VFS/ROOT/root.chk",
                "sourceOffset": 1,
                "pathId": 100,
            },
            "type": "ParticleSystemRenderer",
            "name": "root",
            "pptrs": [
                {
                    "path": pptr_path,
                    "fileId": 2,
                    "pathId": path_id,
                    "status": "external_target_unavailable",
                    "expected": {
                        "serializedFile": serialized_file,
                        "externalPath": f"archive:/{serialized_file}/{serialized_file}",
                        "externalGuid": "00000000-0000-0000-0000-000000000000",
                        "externalType": 0,
                    },
                }
            ],
        },
        {
            "recordType": "summary",
            "schemaVersion": 1,
            "complete": True,
            "counts": {
                "objects": 1,
                "schemas": 1,
                "monoScripts": 0,
                "scalars": 0,
                "pptrs": 1,
                "objectsWithTruncatedScalars": 0,
                "errors": 0,
                "suppressedErrors": 0,
            },
            "errors": [],
        },
    ]
    index.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    stage = root / "stage" / "external_ui_effect_stage.json"
    _write_json(
        stage,
        {
            "schema_version": 1,
            "character_id": "chr_0003_endminf",
            "actor_token": "endminf",
            "entry_count": 1,
            "container_count": 1,
            "object_index_paths": [str(index)],
            "expected_root_count": 1,
            "expected_clip_count": 0,
            "status": "ok",
            "validation": {
                "object_index_summaries": [
                    {
                        "recordType": "summary",
                        "complete": True,
                        "counts": {"errors": 0},
                        "errors": [],
                    }
                ],
                "root_clip_count": 1,
                "stage_fingerprint": "fixture-stage",
            },
        },
    )
    return stage


def _complete_target(root: Path, *, rows: list[dict]) -> Path:
    path = root / "complete.jsonl"
    output = list(rows)
    output.append(
        {
            "recordType": "summary",
            "schemaVersion": 1,
            "complete": True,
            "counts": {"errors": 0},
            "errors": [],
        }
    )
    path.write_text("\n".join(json.dumps(row) for row in output) + "\n", encoding="utf-8")
    return path


def _target_row(*, name: str = "M_exact", source: str = "VFS/AAAA/dep.chk", offset: int = 42, path_id: int = 77) -> dict:
    return {
        "recordType": "object",
        "object": {
            "serializedFile": "CAB-dependency",
            "source": source,
            "sourceOffset": offset,
            "pathId": path_id,
        },
        "type": "Material",
        "name": name,
    }


def _asset_map(root: Path, *, source: str = r"D:\Game\Endfield_Data\StreamingAssets\VFS\AAAA\dep.chk", path_id: int = 77, entry_type: str = "Material") -> Path:
    path = root / "map.json"
    _write_json(
        path,
        {
            "AssetEntries": [
                {
                    "Name": "M_exact",
                    "Container": "effects/prefabs/p_fxui_endminm003_overview_01.prefab",
                    "Source": source,
                    "PathID": path_id,
                    "Type": entry_type,
                    "Hash": "fixture",
                    "Offset": 42,
                }
            ]
        },
    )
    return path


def _dotnet_string(value: str) -> bytes:
    raw = value.encode("utf-8")
    size = len(raw)
    result = bytearray()
    while size >= 0x80:
        result.append((size & 0x7F) | 0x80)
        size >>= 7
    result.append(size)
    result.extend(raw)
    return bytes(result)


def _cab_map(root: Path) -> Path:
    path = root / "endfield_streamingassets_assets.bin"
    path.write_bytes(
        b"".join(
            [
                _dotnet_string(r"D:\Game\Endfield_Data\StreamingAssets"),
                struct.pack("<i", 1),
                _dotnet_string("CAB-dependency"),
                _dotnet_string(r"VFS\AAAA\dep.chk"),
                struct.pack("<q", 42),
                struct.pack("<i", 0),
            ]
        )
    )
    return path


class EndminfExternalPPtrClosureTests(unittest.TestCase):
    def test_exact_cab_pathid_source_offset_and_type_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = _stage(root)
            index = _complete_target(root, rows=[_target_row()])
            report = build_report(stage, object_indexes=[index], asset_maps=[_asset_map(root)])

            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["summary"]["resolvedCount"], 1)
            identity = report["identities"][0]
            self.assertEqual(identity["status"], "resolved")
            self.assertIn("asset_map_exact_source_offset_pathid", identity["resolutionBasis"])
            self.assertEqual(identity["extraction"]["Type"], "Material")
            self.assertEqual(identity["pathIdUnsigned"], 77)
            self.assertEqual(identity["pathIdHex"], "000000000000004D")
            self.assertEqual(set(report["extractionEntries"]), set(TARGET_TYPES))

    def test_conflicting_global_candidates_are_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = _stage(root)
            index = _complete_target(
                root,
                rows=[_target_row(name="M_one"), _target_row(name="M_two")],
            )
            report = build_report(stage, object_indexes=[index], asset_maps=[_asset_map(root)])

            self.assertEqual(report["status"], "incomplete_unresolved_dependencies")
            self.assertEqual(report["summary"]["ambiguousCount"], 1)
            self.assertEqual(report["identities"][0]["status"], "ambiguous")
            self.assertIsNone(report["identities"][0]["extraction"])

    def test_pathid_alone_or_wrong_source_never_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = _stage(root)
            wrong_map = _asset_map(root, source=r"D:\Game\Endfield_Data\StreamingAssets\VFS\BBBB\dep.chk")
            report = build_report(stage, asset_maps=[wrong_map])

            self.assertEqual(report["summary"]["unresolvedCount"], 1)
            self.assertEqual(report["identities"][0]["status"], "unresolved")
            self.assertEqual(report["identities"][0]["assetMapCandidates"], [])
            self.assertIsNone(report["identities"][0]["extraction"])

    def test_exported_json_metadata_proves_exact_target_and_assetmap_join(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = _stage(root)
            metadata = root / "json" / "M_exact.json"
            _write_json(
                metadata,
                {
                    "$animestudio": {
                        "pathId": 77,
                        "type": "Material",
                        "name": "M_exact",
                        "sourceFile": "CAB-dependency",
                        "sourceOriginalPath": r"D:\Game\Endfield_Data\StreamingAssets\VFS\AAAA\dep.chk",
                        "sourceOffset": 42,
                    },
                    "m_Name": "M_exact",
                },
            )
            report = build_report(stage, json_roots=[metadata], asset_maps=[_asset_map(root)])

            self.assertEqual(report["status"], "complete")
            self.assertIn("exported_json_metadata", report["identities"][0]["resolutionBasis"])
            self.assertEqual(report["identities"][0]["extraction"]["PathID"], 77)

    def test_cab_map_bridges_cab_to_exact_asset_map_source_offset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = _stage(root)
            report = build_report(stage, cab_maps=[_cab_map(root)], asset_maps=[_asset_map(root)])

            identity = report["identities"][0]
            self.assertEqual(identity["status"], "resolved")
            self.assertIn("cab_map_source_offset_to_cab", identity["resolutionBasis"])
            self.assertEqual(identity["cabMapCandidates"][0]["sourceOffset"], 42)
            self.assertEqual(identity["extraction"]["PathID"], 77)

    def test_check_mode_rejects_incomplete_without_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = _stage(root)
            output = root / "closure.json"
            code = main(["--stage", str(stage), "--output", str(output)])
            self.assertEqual(code, 2)
            code = main(["--stage", str(stage), "--output", str(output), "--allow-incomplete"])
            self.assertEqual(code, 0)
            code = main(
                ["--stage", str(stage), "--output", str(output), "--check", "--allow-incomplete"]
            )
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
