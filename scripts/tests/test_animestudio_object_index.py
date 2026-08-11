from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "animestudio_object_index", HERE.parent / "animestudio_object_index.py"
)
MERGER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MERGER)
SCHEMA_PATH = (
    HERE.parents[1]
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "Resources"
    / "ObjectIndexSchemaV1.json"
)


def identity(cab: str, source: str, offset: int, path_id: int) -> dict:
    return {
        "serializedFile": cab,
        "source": source,
        "sourceOffset": offset,
        "pathId": path_id,
    }


def schema(fields: list[str]) -> dict:
    schema_id = MERGER.schema_digest(fields)
    return {
        "recordType": "schema",
        "schemaVersion": 1,
        "schemaId": schema_id,
        "typeTreeSource": "serializedType",
        "fields": fields,
    }


def mono_script(source: str = "VFS/core.chk") -> dict:
    return {
        "recordType": "monoScript",
        "schemaVersion": 1,
        "object": identity("CAB-script", source, 44, -7),
        "className": "CutsceneRootComponent",
        "namespace": "Beyond.Gameplay.View",
        "assemblyName": "Gameplay.Beyond.dll",
    }


def object_row(schema_id: str, *, scalar: str = "cutscene_e11m1_dg011_2") -> dict:
    return {
        "recordType": "object",
        "schemaVersion": 1,
        "object": identity("CAB-owner", "VFS/owner.chk", 12, 90),
        "type": "MonoBehaviour",
        "classId": 114,
        "name": "CutsceneRootComponent",
        "container": "",
        "byteSize": 112,
        "decodeStatus": "decoded",
        "typeTreeSource": "serializedType",
        "schemaId": schema_id,
        "scalars": [["$._timelineName", "s", scalar]],
        "pptrs": [
            {
                "path": "$.m_Script",
                "fileId": 1,
                "pathId": -7,
                "status": "external_target_unavailable",
                "expected": {
                    "serializedFile": "CAB-script",
                    "externalPath": "archive:/CAB-script/CAB-script",
                    "externalGuid": "00000000-0000-0000-0000-000000000000",
                },
                "requiresGlobalUniquenessCheck": True,
                "resolutionBasis": "expected_external_identity",
            }
        ],
        "opaque": {"rawLength": 112, "rawSha256": "a" * 64, "error": None},
        "script": {"fileId": 1, "pathId": -7, "fullName": None, "assembly": None},
    }


def counts(rows: list[dict]) -> dict:
    objects = [row for row in rows if row["recordType"] == "object"]
    return {
        "objects": len(objects),
        "schemas": sum(row["recordType"] == "schema" for row in rows),
        "monoScripts": sum(row["recordType"] == "monoScript" for row in rows),
        "scalars": sum(len(row["scalars"]) for row in objects),
        "pptrs": sum(len(row["pptrs"]) for row in objects),
        "objectsWithTruncatedScalars": sum(
            row.get("scalarsTruncated") is True for row in objects
        ),
    }


def write_part(path: Path, rows: list[dict], *, complete: bool = True) -> None:
    summary = {
        "recordType": "summary",
        "schemaVersion": 1,
        "complete": complete,
        "counts": counts(rows),
        "errors": [],
    }
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows + [summary]),
        encoding="utf-8",
    )


def read_gzip_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


class MergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.schema = schema(["m_Script:PPtr<MonoScript>", "_timelineName:string"])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_cross_part_script_join_is_exact_and_enriched(self) -> None:
        owner = self.root / "owner.jsonl"
        scripts = self.root / "scripts.jsonl"
        write_part(owner, [self.schema, object_row(self.schema["schemaId"])])
        write_part(scripts, [mono_script()])

        summary = MERGER.merge_parts([owner, scripts], self.root / "out")
        objects = read_gzip_rows(self.root / "out" / "objects.jsonl.gz")
        merged = next(row for row in objects if row["recordType"] == "object")

        self.assertEqual(summary["externalResolutions"]["resolved"], 1)
        self.assertEqual(
            merged["pptrs"][0]["status"],
            MERGER.MERGED_RESOLUTION_STATUS,
        )
        self.assertEqual(
            merged["pptrs"][0]["resolutionBasis"],
            MERGER.MERGED_RESOLUTION_BASIS,
        )
        self.assertEqual(merged["pptrs"][0]["target"]["source"], "VFS/core.chk")
        self.assertEqual(
            merged["script"]["fullName"],
            "Beyond.Gameplay.View.CutsceneRootComponent",
        )
        self.assertEqual(merged["script"]["assembly"], "Gameplay.Beyond.dll")

    def test_merged_resolution_basis_is_in_published_schema(self) -> None:
        published = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        pptr_properties = published["$defs"]["pptr"]["properties"]

        self.assertIn(
            MERGER.MERGED_RESOLUTION_STATUS,
            pptr_properties["status"]["enum"],
        )
        self.assertIn(
            MERGER.MERGED_RESOLUTION_BASIS,
            pptr_properties["resolutionBasis"]["enum"],
        )

    def test_ambiguous_cab_pathid_never_joins(self) -> None:
        owner = self.root / "owner.jsonl"
        scripts = self.root / "scripts.jsonl"
        write_part(owner, [self.schema, object_row(self.schema["schemaId"])])
        write_part(scripts, [mono_script("VFS/a.chk"), mono_script("VFS/b.chk")])

        summary = MERGER.merge_parts([owner, scripts], self.root / "out")
        merged = next(
            row
            for row in read_gzip_rows(self.root / "out" / "objects.jsonl.gz")
            if row["recordType"] == "object"
        )

        self.assertEqual(summary["externalResolutions"]["ambiguous"], 1)
        self.assertEqual(merged["pptrs"][0]["status"], "ambiguous_external")
        self.assertNotIn("target", merged["pptrs"][0])

    def test_part_order_does_not_change_any_published_byte(self) -> None:
        owner = self.root / "owner.jsonl"
        scripts = self.root / "scripts.jsonl"
        write_part(owner, [self.schema, object_row(self.schema["schemaId"])])
        write_part(scripts, [mono_script()])

        MERGER.merge_parts([owner, scripts], self.root / "first", {"contract": 1})
        MERGER.merge_parts([scripts, owner], self.root / "second", {"contract": 1})

        for name in ("objects.jsonl.gz", "schemas.jsonl.gz", "summary.json"):
            self.assertEqual(
                (self.root / "first" / name).read_bytes(),
                (self.root / "second" / name).read_bytes(),
            )

    def test_component_scene_context_survives_the_fail_closed_merge(self) -> None:
        owner_row = object_row(self.schema["schemaId"])
        owner_row["sceneContext"] = {
            "gameObject": identity("CAB-owner", "VFS/owner.chk", 12, 91),
            "gameObjectName": "RadioTriggerZone",
            "transform": identity("CAB-owner", "VFS/owner.chk", 12, 92),
            "localPosition": {"x": 1.0, "y": 2.0, "z": 3.0},
            "worldPosition": {"x": 4.0, "y": 5.0, "z": 6.0},
            "worldPositionStatus": "exact_transform_hierarchy",
            "parentDepth": 2,
            "hierarchyPath": ["Level", "Triggers", "RadioTriggerZone"],
        }
        part = self.root / "scene-context.jsonl"
        write_part(part, [self.schema, owner_row])

        MERGER.merge_parts([part], self.root / "out")
        merged = next(
            row
            for row in read_gzip_rows(self.root / "out" / "objects.jsonl.gz")
            if row["recordType"] == "object"
        )

        self.assertEqual(merged["sceneContext"], owner_row["sceneContext"])

    def test_conflicting_duplicate_object_fails(self) -> None:
        first = self.root / "first.jsonl"
        second = self.root / "second.jsonl"
        write_part(first, [self.schema, object_row(self.schema["schemaId"], scalar="a")])
        write_part(second, [self.schema, object_row(self.schema["schemaId"], scalar="b")])

        with self.assertRaisesRegex(MERGER.MergeError, "conflicting duplicate"):
            MERGER.merge_parts([first, second], self.root / "out")

    def test_runtime_target_must_match_unique_global_candidate(self) -> None:
        owner_row = object_row(self.schema["schemaId"])
        owner_row["pptrs"][0]["status"] = "resolved"
        owner_row["pptrs"][0]["target"] = {
            **identity("CAB-script", "VFS/wrong.chk", 99, -7),
            "type": "MonoScript",
            "name": "CutsceneRootComponent",
        }
        owner = self.root / "owner.jsonl"
        scripts = self.root / "scripts.jsonl"
        write_part(owner, [self.schema, owner_row])
        write_part(scripts, [mono_script()])

        with self.assertRaisesRegex(MERGER.MergeError, "runtime external target conflicts"):
            MERGER.merge_parts([owner, scripts], self.root / "out")

    def test_incomplete_or_miscounted_part_fails(self) -> None:
        incomplete = self.root / "incomplete.jsonl"
        write_part(incomplete, [mono_script()], complete=False)
        with self.assertRaisesRegex(MERGER.MergeError, "not complete"):
            MERGER.merge_parts([incomplete], self.root / "out-incomplete")

        miscounted = self.root / "miscounted.jsonl"
        write_part(miscounted, [mono_script()])
        text = miscounted.read_text(encoding="utf-8").replace(
            '"monoScripts":1', '"monoScripts":2'
        )
        miscounted.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(MERGER.MergeError, "count mismatch"):
            MERGER.merge_parts([miscounted], self.root / "out-miscounted")

    def test_schema_hash_and_terminal_summary_are_enforced(self) -> None:
        bad_schema = dict(self.schema, schemaId="0" * 64)
        part = self.root / "bad-schema.jsonl"
        write_part(part, [bad_schema])
        with self.assertRaisesRegex(MERGER.MergeError, "schemaId hash mismatch"):
            MERGER.merge_parts([part], self.root / "out-schema")

        trailing = self.root / "trailing.jsonl"
        write_part(trailing, [mono_script()])
        with trailing.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(mono_script()) + "\n")
        with self.assertRaisesRegex(MERGER.MergeError, "after terminal summary"):
            MERGER.merge_parts([trailing], self.root / "out-trailing")


if __name__ == "__main__":
    unittest.main()
