import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "audit_catalog_coverage",
    ROOT / "tools/endfield-il2cpp/audit_catalog_coverage.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CatalogCoverageTests(unittest.TestCase):
    def make_fixture(self, base: Path, *, summary_complete=True, catalog_hash="a" * 64):
        catalog_path = base / "catalog.json"
        dummy_root = base / "DummyDll"
        dummy_root.mkdir()
        dll_path = dummy_root / "Game.dll"
        dll_path.write_bytes(b"managed-placeholder")
        dll_hash = MODULE.sha256_file(dll_path)
        generation = {
            "schema": 1,
            "game": {
                "metadataSha256": catalog_hash,
                "gameAssemblySha256": "b" * 64,
            },
            "cpp2il": {
                "skippedMalformedImageCount": 0,
                "skippedMalformedImages": [],
                "skippedMalformedTypeCount": 1,
            },
            "assemblies": {
                "count": 1,
                "bytes": dll_path.stat().st_size,
                "files": [{
                    "name": "Game.dll",
                    "bytes": dll_path.stat().st_size,
                    "sha256": dll_hash,
                }],
            },
        }
        self.write_json(dummy_root / "generation.json", generation)
        dummy_index_path = base / "dummy_types.json"
        dummy_index = {
            "schema": MODULE.DUMMY_INDEX_SCHEMA,
            "complete": True,
            "assemblyCount": 1,
            "typeCount": 1,
            "assemblies": [{
                "path": "Game.dll",
                "module": "Game.dll",
                "bytes": dll_path.stat().st_size,
                "sha256": dll_hash,
                "typeCount": 1,
                "types": [{
                    "fullName": "Demo.Present",
                    "namespace": "Demo",
                    "name": "Present",
                    "token": "0x02000001",
                }],
            }],
            "errors": [],
        }
        self.write_json(dummy_index_path, dummy_index)
        catalog = {
            "schema": MODULE.CATALOG_SCHEMA,
            "status": "complete_with_unresolved",
            "source": {
                "metadataSha256": catalog_hash,
                "gameAssemblySha256": "b" * 64,
            },
            "coverage": {"malformedTypes": 0},
            "types": [
                {
                    "index": 0,
                    "image": "Game.dll",
                    "fullName": "Demo.Present",
                    "token": "0x02000001",
                },
                {
                    "index": 1,
                    "image": "Game.dll",
                    "fullName": "Demo.Missing",
                    "token": "0x02000002",
                },
            ],
        }
        self.write_json(catalog_path, catalog)

        object_root = base / "object_index"
        object_root.mkdir()
        rows = [
            {
                "recordType": "monoScript",
                "assemblyName": "Game.dll",
                "namespace": "Demo",
                "className": "Present",
                "object": {"pathId": 10},
            },
            {
                "recordType": "object",
                "type": "MonoBehaviour",
                "name": "present",
                "decodeStatus": "decoded",
                "typeTreeSource": "scriptType",
                "script": {"assembly": "Game.dll", "fullName": "Demo.Present"},
                "object": {"pathId": 1},
            },
            {
                "recordType": "object",
                "type": "MonoBehaviour",
                "name": "missing",
                "decodeStatus": "partial",
                "script": {"assembly": "Game", "fullName": "Demo.Missing"},
                "object": {"pathId": 2},
            },
            {
                "recordType": "object",
                "type": "MonoBehaviour",
                "name": "unknown",
                "decodeStatus": "partial",
                "object": {"pathId": 3},
            },
        ]
        objects_path = object_root / "objects.jsonl.gz"
        with gzip.open(objects_path, "wt", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")
        schemas_path = object_root / "schemas.jsonl.gz"
        with gzip.open(schemas_path, "wt", encoding="utf-8") as stream:
            stream.write("{}\n")
        fingerprint = MODULE.stable_hash([{
            "path": "Game.dll",
            "bytes": dll_path.stat().st_size,
            "sha256": dll_hash,
        }])
        summary = {
            "schemaVersion": 1,
            "complete": summary_complete,
            "errors": [],
            "counts": {"objects": len(rows) - 1, "monoScripts": 1},
            "outputs": {
                "objects": {
                    "path": objects_path.name,
                    "bytes": objects_path.stat().st_size,
                    "sha256": MODULE.sha256_file(objects_path),
                },
                "schemas": {
                    "path": schemas_path.name,
                    "bytes": schemas_path.stat().st_size,
                    "sha256": MODULE.sha256_file(schemas_path),
                },
            },
            "stageSignature": {
                "payload": {
                    "source": "Fixture",
                    "cli": {"dummyDlls": {"fingerprint": fingerprint}},
                },
            },
        }
        self.write_json(object_root / "summary.json", summary)
        return catalog_path, dummy_root, dummy_index_path, object_root

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_exact_type_and_monobehaviour_joins(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog, dummy_root, dummy_index, object_root = self.make_fixture(Path(directory))
            report = MODULE.build_report(
                catalog,
                dummy_root,
                dummy_root / "generation.json",
                dummy_index,
                [object_root],
            )
            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["coverage"]["catalogTypesInDummyDll"], 1)
            self.assertEqual(report["coverage"]["catalogTypesInTokenConsistentDummyDll"], 1)
            self.assertEqual(report["coverage"]["catalogTypesMissingDummyDll"], 1)
            accepted = report["objectIndexes"]["accepted"][0]
            self.assertEqual(accepted["monoBehaviourRows"], 3)
            self.assertEqual(accepted["distinctReferencedMonoScripts"], 2)
            self.assertEqual(accepted["monoScripts"]["rows"], 1)
            self.assertEqual(accepted["monoScripts"]["catalogYesDummyYes"], 1)
            self.assertEqual(accepted["joinScripts"]["catalogYesDummyYes"], 1)
            self.assertEqual(accepted["joinScripts"]["catalogYesDummyNo"], 1)
            self.assertEqual(accepted["joinInstances"]["missing_script_identity"], 1)
            markdown = MODULE.render_markdown(report)
            self.assertIn("Immediate schema-recovery candidates", markdown)
            self.assertIn("Game::Demo.Missing", markdown)

    def test_incomplete_index_is_rejected_without_consuming_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog, dummy_root, dummy_index, object_root = self.make_fixture(
                Path(directory), summary_complete=False
            )
            report = MODULE.build_report(
                catalog,
                dummy_root,
                dummy_root / "generation.json",
                dummy_index,
                [object_root],
            )
            self.assertEqual(report["status"], "failed_evidence")
            self.assertEqual(report["objectIndexes"]["accepted"], [])
            self.assertIn("incomplete", report["objectIndexes"]["rejected"][0]["reason"])

    def test_native_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog, dummy_root, dummy_index, object_root = self.make_fixture(Path(directory))
            catalog_data = json.loads(catalog.read_text(encoding="utf-8"))
            catalog_data["source"]["metadataSha256"] = "c" * 64
            self.write_json(catalog, catalog_data)
            with self.assertRaisesRegex(MODULE.AuditError, "native hashes differ"):
                MODULE.build_report(
                    catalog,
                    dummy_root,
                    dummy_root / "generation.json",
                    dummy_index,
                    [object_root],
                )

    def test_name_only_dummydll_match_is_not_schema_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog, dummy_root, dummy_index, object_root = self.make_fixture(Path(directory))
            inventory = json.loads(dummy_index.read_text(encoding="utf-8"))
            inventory["assemblies"][0]["types"][0]["token"] = "0x02000002"
            self.write_json(dummy_index, inventory)
            report = MODULE.build_report(
                catalog,
                dummy_root,
                dummy_root / "generation.json",
                dummy_index,
                [object_root],
            )
            self.assertEqual(report["coverage"]["catalogTypesInDummyDll"], 1)
            self.assertEqual(report["coverage"]["catalogTypesInTokenConsistentDummyDll"], 0)
            self.assertEqual(report["coverage"]["dummyDllTokenNameMismatchDefinitions"], 1)
            self.assertEqual(
                report["objectIndexes"]["accepted"][0]["joinScripts"]["catalogYesDummyYes"],
                0,
            )

    def test_object_output_hash_mismatch_rejects_index(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog, dummy_root, dummy_index, object_root = self.make_fixture(Path(directory))
            with (object_root / "objects.jsonl.gz").open("ab") as stream:
                stream.write(b"changed")
            report = MODULE.build_report(
                catalog,
                dummy_root,
                dummy_root / "generation.json",
                dummy_index,
                [object_root],
            )
            self.assertEqual(report["status"], "failed_evidence")
            self.assertIn("hash/size mismatch", report["objectIndexes"]["rejected"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
