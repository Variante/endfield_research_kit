from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_changed_game_data import (
    ChangedExportError,
    _load_index_rows,
    classify_changes,
    output_relative_path,
    publish_transaction,
    validate_audit_seed_summary,
)
from scripts.export_full_from_game import load_structured_incremental_manifest


def file_row(name: str, md5: str = "A" * 32, length: int = 4) -> dict:
    return {
        "logicalId": f"JsonData/{name}",
        "blockName": "JsonData",
        "blockTypeValue": 19,
        "virtualPath": name,
        "fileDataMd5DisplayHex": md5,
        "length": length,
        "encrypted": False,
    }


class ChangeClassificationTests(unittest.TestCase):
    def test_classifies_added_modified_deleted_and_unchanged(self) -> None:
        previous = [file_row("same"), file_row("changed"), file_row("gone")]
        current = [file_row("same"), file_row("changed", "B" * 32), file_row("new")]
        result = classify_changes(previous, current)
        self.assertEqual([row["virtualPath"] for row in result["added"]], ["new"])
        self.assertEqual([row["virtualPath"] for row in result["modified"]], ["changed"])
        self.assertEqual([row["virtualPath"] for row in result["deleted"]], ["gone"])
        self.assertEqual([row["virtualPath"] for row in result["unchanged"]], ["same"])

    def test_duplicate_logical_identity_fails_closed(self) -> None:
        with self.assertRaisesRegex(ChangedExportError, "duplicate baseline"):
            classify_changes([file_row("same"), file_row("same")], [])


class IndexAndPathTests(unittest.TestCase):
    def test_jsonl_index_requires_matching_terminal_summary(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "index.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "recordType": "file",
                        "logicalId": "JsonData/Data/A.bytes",
                        "blockName": "JsonData",
                        "fileBlockTypeValue": 19,
                        "fileName": "Data/A.bytes",
                        "fileDataMd5": "a" * 32,
                        "length": 7,
                        "encrypted": True,
                    }
                )
                + "\n"
                + json.dumps({"recordType": "summary", "fileCount": 1, "missingChunkCount": 0})
                + "\n",
                encoding="utf-8",
            )
            rows, _summary = _load_index_rows(path)
            self.assertEqual(rows[0]["fileDataMd5DisplayHex"], "A" * 32)
            self.assertTrue(rows[0]["encrypted"])

            path.write_text(path.read_text(encoding="utf-8").replace('"fileCount": 1', '"fileCount": 2'), encoding="utf-8")
            with self.assertRaisesRegex(ChangedExportError, "count mismatch"):
                _load_index_rows(path)

    def test_output_mapping_and_traversal_rejection(self) -> None:
        self.assertEqual(str(output_relative_path({"blockName": "Table", "virtualPath": "Data/Foo.bytes"})), "Table/Foo.json")
        self.assertEqual(str(output_relative_path({"blockName": "Video", "virtualPath": "Data/Foo.usm"})), "Data/Foo.mp4")
        for unsafe in ("../escape", "/absolute", "C:/absolute"):
            with self.subTest(unsafe=unsafe), self.assertRaises(ChangedExportError):
                output_relative_path({"blockName": "JsonData", "virtualPath": unsafe})


class PublicationTests(unittest.TestCase):
    def test_publish_replaces_and_retryable_delete_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            destination = root / "structured" / "Persistent" / "Data" / "A.bytes"
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"old")
            staged = root / "stage" / "A.bytes"
            staged.parent.mkdir()
            staged.write_bytes(b"new")
            publish_transaction(
                output_root=root,
                source="Persistent",
                staged={Path("Data/A.bytes"): staged},
                deleted=[file_row("Data/already-gone.bytes")],
                backup=root / "backup",
            )
            self.assertEqual(destination.read_bytes(), b"new")


class ProvenanceGateTests(unittest.TestCase):
    def test_audit_inventory_must_reconstruct_previous_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            persistent = root / "Persistent"
            persistent.mkdir()
            (persistent / "config.bin").write_bytes(b"abc")
            summary = root / "audit.json"
            summary.write_text(
                json.dumps(
                    {
                        "inputSetSha256": "seed",
                        "primaryAssets": str(persistent),
                        "sourceFingerprints": [{"role": "primary", "path": str(persistent / "VFS/a.blc"), "length": 10}],
                        "physicalChunkInventory": [{"role": "primary", "path": str(persistent / "VFS/a.chk"), "length": 20}],
                    }
                ),
                encoding="utf-8",
            )
            validate_audit_seed_summary(
                summary,
                ledger_input_set="seed",
                game_root=root,
                previous_source={"files": 3, "bytes": 33},
            )
            with self.assertRaisesRegex(ChangedExportError, "does not describe"):
                validate_audit_seed_summary(
                    summary,
                    ledger_input_set="seed",
                    game_root=root,
                    previous_source={"files": 3, "bytes": 29},
                )


class WrapperContractTests(unittest.TestCase):
    def test_changed_only_is_local_and_never_invokes_updates_builder(self) -> None:
        wrapper = (Path(__file__).resolve().parents[2] / "export.bat").read_text(encoding="utf-8")
        self.assertIn("--changed-only", wrapper)
        self.assertIn("export_changed_game_data.py prepare", wrapper)
        self.assertIn("export_changed_game_data.py finalize", wrapper)
        self.assertNotIn("python .\\scripts\\build_updates", wrapper.lower())

    def test_incremental_manifest_requires_exact_current_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            game = (root / "game").resolve()
            output = (root / "output").resolve()
            game.mkdir()
            output.mkdir()
            manifest = root / "manifest.json"
            source = {"files": 1, "bytes": 2, "fingerprint": "abc", "latest_mtime_ns": 3}
            manifest.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "complete": True,
                        "applied": True,
                        "updatesIntegration": "disabled",
                        "gameRoot": str(game),
                        "outputRoot": str(output),
                        "sourceFingerprints": {"Persistent": source},
                    }
                ),
                encoding="utf-8",
            )
            load_structured_incremental_manifest(
                manifest,
                game_root=game,
                output_root=output,
                selected_sources=("Persistent",),
                current_source_sizes={"Persistent": dict(source)},
            )
            changed = dict(source)
            changed["bytes"] = 9
            with self.assertRaisesRegex(ValueError, "source drift"):
                load_structured_incremental_manifest(
                    manifest,
                    game_root=game,
                    output_root=output,
                    selected_sources=("Persistent",),
                    current_source_sizes={"Persistent": changed},
                )


if __name__ == "__main__":
    unittest.main()
