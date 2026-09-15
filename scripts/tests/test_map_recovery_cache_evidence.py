"""Content evidence for the map-recovery render caches.

The render cache used to be keyed on `size + mtime_ns`, so every
`export.bat --from-game` run - which rewrites every exported file whether or
not the game data changed - missed every scene.  These tests pin the two
properties that fixed it: evidence must survive an mtime-only rewrite, and it
must never survive a content change or go missing silently.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import map_recovery_cache_evidence as evidence


def write_asset_map(path: Path, entries: list[dict]) -> Path:
    path.write_text(
        json.dumps({"AssetEntries": entries}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def entry(name: str, path_id: int, object_type: str, object_hash: str | None) -> dict:
    row = {
        "Name": name,
        "Container": f"assets/{name.lower()}",
        "Source": "VFS/0CE8FA57/chunk.chk",
        "PathID": path_id,
        "Type": object_type,
        "Offset": 0,
    }
    if object_hash is not None:
        row["Hash"] = object_hash
    return row


def fresh_index(asset_map: Path) -> dict:
    """Rebuild the process-level memos so a rewritten asset map is re-read."""
    evidence.asset_map_sha256.cache_clear()
    evidence._OBJECT_INDEX_MEMO.clear()
    return evidence.load_object_hash_index(asset_map, asset_map.with_name("objects.json"))


class PathIdSuffixTests(unittest.TestCase):
    def test_the_exported_path_id_suffix_is_recovered(self):
        self.assertEqual(
            evidence.path_id_from_export_path(Path("S_prop_001_lod0_p748F5D331E277534.obj")),
            0x748F5D331E277534,
        )

    def test_a_name_that_itself_contains_p_keeps_only_the_trailing_id(self):
        self.assertEqual(
            evidence.path_id_from_export_path(Path("001_0_pA284B45FC95E4A3F.obj")),
            0xA284B45FC95E4A3F,
        )

    def test_a_file_without_an_exported_path_id_yields_none(self):
        self.assertIsNone(evidence.path_id_from_export_path(Path("renderers.jsonl")))

    def test_the_signed_asset_map_path_id_keys_on_its_unsigned_form(self):
        # AnimeStudio names exported files with the unsigned PathID while the
        # asset map publishes the signed int64. The exported export_full copy
        # of this entry really is `T_default_mro_MRO_pEEB1E5E9C92A208A.png`.
        self.assertEqual(evidence.path_id_key(-1246962829539794806), "EEB1E5E9C92A208A")


class ObjectHashIndexTests(unittest.TestCase):
    def test_renderer_consumed_types_are_indexed_by_unsigned_path_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset_map = write_asset_map(Path(tmp, "assets.json"), [
                entry("S_mesh", 0x11, "Mesh", "aaaa"),
                entry("T_tex", 0x22, "Texture2D", "bbbb"),
                entry("M_mat", 0x33, "Material", "cccc"),
                entry("anim", 0x44, "AnimationClip", "dddd"),
            ])
            index = fresh_index(asset_map)
            self.assertEqual(index["objects"], {
                "0000000000000011": "Mesh:aaaa",
                "0000000000000022": "Texture2D:bbbb",
                "0000000000000033": "Material:cccc",
            })

    def test_a_path_id_with_two_different_objects_is_ambiguous_not_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset_map = write_asset_map(Path(tmp, "assets.json"), [
                entry("T_a", 0x55, "Texture2D", "aaaa"),
                entry("T_b", 0x55, "Texture2D", "bbbb"),
            ])
            index = fresh_index(asset_map)
            self.assertNotIn("0000000000000055", index["objects"])
            self.assertIn("0000000000000055", index["ambiguous"])

    def test_the_same_object_listed_twice_stays_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset_map = write_asset_map(Path(tmp, "assets.json"), [
                entry("T_a", 0x66, "Texture2D", "aaaa"),
                entry("T_a", 0x66, "Texture2D", "aaaa"),
            ])
            self.assertEqual(fresh_index(asset_map)["objects"]["0000000000000066"], "Texture2D:aaaa")

    def test_an_entry_without_a_published_hash_is_never_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset_map = write_asset_map(Path(tmp, "assets.json"), [
                entry("S_mesh", 0x77, "Mesh", None),
            ])
            index = fresh_index(asset_map)
            self.assertEqual(index["objects"], {})
            self.assertIn("0000000000000077", index["ambiguous"])

    def test_an_mtime_only_rewrite_reuses_the_persisted_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset_map = write_asset_map(Path(tmp, "assets.json"), [
                entry("S_mesh", 0x11, "Mesh", "aaaa"),
            ])
            cache = Path(tmp, "objects.json")
            fresh_index(asset_map)
            built_at = cache.stat().st_mtime_ns
            os.utime(asset_map, None)
            evidence.asset_map_sha256.cache_clear()
            evidence._OBJECT_INDEX_MEMO.clear()
            evidence.load_object_hash_index(asset_map, cache)
            self.assertEqual(cache.stat().st_mtime_ns, built_at)

    def test_a_content_change_rebuilds_the_persisted_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset_map = Path(tmp, "assets.json")
            cache = Path(tmp, "objects.json")
            write_asset_map(asset_map, [entry("S_mesh", 0x11, "Mesh", "aaaa")])
            fresh_index(asset_map)
            write_asset_map(asset_map, [entry("S_mesh", 0x11, "Mesh", "zzzz")])
            evidence.asset_map_sha256.cache_clear()
            evidence._OBJECT_INDEX_MEMO.clear()
            rebuilt = evidence.load_object_hash_index(asset_map, cache)
            self.assertEqual(rebuilt["objects"]["0000000000000011"], "Mesh:zzzz")

    def test_a_missing_asset_map_publishes_its_unavailability(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = evidence.load_object_hash_index(Path(tmp, "absent.json"), Path(tmp, "objects.json"))
            self.assertEqual(index["objects"], {})
            self.assertEqual(index["unavailable"], "assetMapMissing")


class SourceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.asset_map = write_asset_map(self.tmp / "assets.json", [
            entry("S_mesh", 0x11, "Mesh", "aaaa"),
        ])
        self.index = fresh_index(self.asset_map)
        self.mesh = self.tmp / "S_mesh_p0000000000000011.obj"
        self.mesh.write_text("v 0 0 0\n", encoding="utf-8")

    def test_an_indexed_source_is_identified_by_its_asset_map_object_hash(self):
        record = evidence.source_evidence(self.mesh, self.index)
        self.assertEqual(record["evidence"], "assetMapObjectHash")
        self.assertEqual(record["object"], "Mesh:aaaa")
        self.assertNotIn("mtimeNs", record)

    def test_evidence_survives_an_mtime_only_rewrite(self):
        before = evidence.source_evidence(self.mesh, self.index)
        os.utime(self.mesh, (0, 0))
        evidence._CONTENT_SHA_MEMO.clear()
        self.assertEqual(evidence.source_evidence(self.mesh, self.index), before)

    def test_evidence_changes_when_the_exported_file_is_rewritten(self):
        before = evidence.source_evidence(self.mesh, self.index)
        with self.mesh.open("a", encoding="utf-8") as stream:
            stream.write("# appended\n")
        evidence._CONTENT_SHA_MEMO.clear()
        self.assertNotEqual(evidence.source_evidence(self.mesh, self.index), before)

    def test_an_unindexed_path_id_falls_back_to_content_sha256_and_says_so(self):
        stray = self.tmp / "S_other_p00000000000000FF.obj"
        stray.write_text("v 1 1 1\n", encoding="utf-8")
        record = evidence.source_evidence(stray, self.index)
        self.assertEqual(record["evidence"], "contentSha256")
        self.assertEqual(record["fallback"], "pathIdNotInAssetMap")
        self.assertEqual(len(record["sha256"]), 64)

    def test_an_ambiguous_path_id_falls_back_rather_than_guessing(self):
        asset_map = write_asset_map(self.tmp / "ambiguous.json", [
            entry("T_a", 0x99, "Texture2D", "aaaa"),
            entry("T_b", 0x99, "Texture2D", "bbbb"),
        ])
        index = fresh_index(asset_map)
        texture = self.tmp / "T_a_p0000000000000099.png"
        texture.write_bytes(b"\x89PNG\r\n\x1a\n")
        record = evidence.source_evidence(texture, index)
        self.assertEqual(record["fallback"], "ambiguousPathId")
        self.assertEqual(record["evidence"], "contentSha256")

    def test_a_file_without_a_path_id_falls_back_to_content_sha256(self):
        plain = self.tmp / "renderers.jsonl"
        plain.write_text("{}\n", encoding="utf-8")
        record = evidence.source_evidence(plain, self.index)
        self.assertEqual(record["fallback"], "noPathIdInFileName")

    def test_a_missing_source_is_recorded_as_missing_not_skipped(self):
        record = evidence.source_evidence(self.tmp / "absent_p0000000000000011.obj", self.index)
        self.assertEqual(record["evidence"], "missing")
        self.assertNotIn("object", record)

    def test_a_missing_source_and_a_present_one_never_share_evidence(self):
        present = evidence.source_evidence(self.mesh, self.index)
        self.mesh.unlink()
        self.assertNotEqual(evidence.source_evidence(self.mesh, self.index), present)

    def test_file_content_evidence_hashes_a_source_that_carries_no_path_id(self):
        sidecar = self.tmp / "renderers.jsonl"
        sidecar.write_text("{}\n", encoding="utf-8")
        record = evidence.file_content_evidence(sidecar)
        self.assertEqual(record["evidence"], "contentSha256")
        self.assertEqual(len(record["sha256"]), 64)
        self.assertEqual(
            evidence.file_content_evidence(self.tmp / "absent.jsonl")["evidence"], "missing"
        )

    def test_the_evidence_list_is_ordered_and_deduplicated(self):
        first = evidence.source_evidence_list([self.mesh, self.mesh], self.asset_map)
        self.assertEqual(len(first), 1)


class StreamingSidecarEvidenceTests(unittest.TestCase):
    def test_only_the_leading_source_block_of_a_sidecar_is_decoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            sidecar = Path(tmp, "scene.json")
            sidecar.write_text(json.dumps({
                "schemaVersion": 3,
                "levelId": "scene",
                "source": {
                    "cliSha256": "c" * 64,
                    "files": [
                        {"fileName": "InitChunkData_0_0_0_0.bytes", "packedSha256": "a" * 64},
                        {"fileName": "InitChunkData_1_0_0_0.bytes", "packedSha256": "b" * 64},
                    ],
                },
                # A large tail that must never be parsed.
                "instances": [{"id": index} for index in range(20000)],
            }), encoding="utf-8")
            block = evidence._sidecar_source_block(sidecar)
            self.assertEqual(block["cliSha256"], "c" * 64)
            self.assertEqual(len(block["files"]), 2)

    def test_a_sidecar_without_a_source_block_yields_no_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            sidecar = Path(tmp, "scene.json")
            sidecar.write_text(json.dumps({"levelId": "scene"}), encoding="utf-8")
            self.assertIsNone(evidence._sidecar_source_block(sidecar))

    def test_a_level_with_no_streaming_scene_says_so_instead_of_claiming_one(self):
        record = evidence.streaming_source_evidence("no_such_level_for_cache_evidence_tests")
        self.assertEqual(record["evidence"], "noStreamingScene")


class BindingRelationTests(unittest.TestCase):
    def test_paths_become_repo_relative_strings_in_a_stable_order(self):
        relations = evidence.binding_relations({
            "b": {"texturePath": ROOT / "export_full/tex.png", "slot": "_BaseMap"},
            "a": {"submeshBindings": [None, {"materialPath": ROOT / "export_full/mat.json"}]},
        })
        self.assertEqual([row[0] for row in relations], ["a", "b"])
        self.assertEqual(relations[1][1]["texturePath"], "export_full/tex.png")
        self.assertEqual(relations[0][1]["submeshBindings"][1]["materialPath"], "export_full/mat.json")

    def test_a_relation_change_is_visible(self):
        base = evidence.binding_relations({"a": {"texturePath": ROOT / "export_full/tex.png"}})
        moved = evidence.binding_relations({"a": {"texturePath": ROOT / "export_full/other.png"}})
        self.assertNotEqual(base, moved)

    def test_no_bindings_is_an_empty_relation_list(self):
        self.assertEqual(evidence.binding_relations(None), [])


if __name__ == "__main__":
    unittest.main()
