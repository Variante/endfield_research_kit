import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import verify_endminf_fx_model_binding as verifier


class EndminfFxModelBindingTests(unittest.TestCase):
    def test_unity_crc32_matches_known_avatar_tos_entry(self):
        path = (
            "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/"
            "Bip001_Spine2/Bip001_Neck/Bip001_Head/lipLdn4Joint"
        )
        self.assertEqual(verifier.unity_crc32(path), 2464567722)

    def test_clip_hashes_require_exact_three_transform_bindings(self):
        value = {
            "m_ClipBindingConstant": {
                "genericBindings": [
                    {"path": path_hash, "attribute": attribute, "typeID": "Transform"}
                    for path_hash in verifier.EXPECTED_BINDING_HASHES
                    for attribute in (1, 2, 3)
                ]
            }
        }
        grouped = verifier.clip_binding_hashes(value)
        self.assertEqual(tuple(sorted(grouped)), verifier.EXPECTED_BINDING_HASHES)
        self.assertEqual(sum(len(rows) for rows in grouped.values()), 9)

    def test_clip_hashes_reject_binding_shape_mutation(self):
        for mutation in ("duplicate_attribute", "wrong_type"):
            with self.subTest(mutation=mutation):
                bindings = [
                    {"path": path_hash, "attribute": attribute, "typeID": "Transform"}
                    for path_hash in verifier.EXPECTED_BINDING_HASHES
                    for attribute in (1, 2, 3)
                ]
                if mutation == "duplicate_attribute":
                    bindings[2]["attribute"] = 2
                else:
                    bindings[2]["typeID"] = "Animator"
                with self.assertRaises(verifier.VerificationError):
                    verifier.clip_binding_hashes(
                        {"m_ClipBindingConstant": {"genericBindings": bindings}}
                    )

    def test_clip_hashes_reject_name_only_or_extra_path(self):
        value = {
            "m_ClipBindingConstant": {
                "genericBindings": [
                    {"path": path_hash, "attribute": 1, "typeID": "Transform"}
                    for path_hash in (*verifier.EXPECTED_BINDING_HASHES, 1234)
                    for _ in range(3)
                ]
            }
        }
        with self.assertRaisesRegex(verifier.VerificationError, "expected exactly"):
            verifier.clip_binding_hashes(value)

    def test_container_evidence_keeps_clip_only_identity(self):
        container = "assets/beyond/arts/effects/commonassets/arts/sk_model/sk_fx_endminf_01_ui.fbx"
        source = r"D:\game\FC.chk"
        identity = {
            "name": "A_actor_endminf_ui_overview_02",
            "type": "AnimationClip",
            "pathId": -7,
            "source": source,
            "sourceOffset": 99,
            "container": container,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "map.json"
            path.write_text(
                json.dumps(
                    {
                        "AssetEntries": [
                            {
                                "Name": identity["name"],
                                "Container": container,
                                "Source": source,
                                "PathID": -7,
                                "Type": "AnimationClip",
                                "Offset": 99,
                            },
                            {
                                "Name": "unrelated",
                                "Container": "assets/other.fbx",
                                "Source": source,
                                "PathID": -8,
                                "Type": "Mesh",
                                "Offset": 100,
                            },
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            evidence = verifier._container_evidence(path, identity)
        self.assertEqual(evidence["containerRowCount"], 1)
        self.assertEqual(evidence["containerModelRows"], 0)
        self.assertEqual(evidence["sourceOffsetModelRows"], 0)
        self.assertEqual(
            evidence["result"],
            "current_assetmap_container_scope_has_animation_clip_only_no_model_closure",
        )
        self.assertEqual(evidence["runtimeHierarchy"], "not_assessed")
        self.assertTrue(evidence["runtimeHierarchyNotNegated"])

    def test_avatar_tos_requires_crc32_key_match(self):
        path_hash = verifier.EXPECTED_BINDING_HASHES[0]
        authored = "Root/FX/target"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "avatar.json"
            path.write_text(json.dumps({"m_TOS": {str(path_hash): authored}}), encoding="utf-8")
            result = verifier._avatar_evidence(path, [path_hash])
        self.assertEqual(result["targetRows"][0]["keyPresent"], False)
        self.assertEqual(result["invalidKeyCount"], 1)
        self.assertEqual(result["result"], "all_target_hashes_absent_from_exact_avatar_tos")

    def test_source_provenance_rejects_snapshot_or_stage_hash_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.chk"
            source.write_bytes(b"exact-source")
            current = verifier._snapshot(source)
            identity = {"source": current["path"]}
            stamp = {
                "sourceFreshness": {
                    "status": "validated",
                    "current": dict(current),
                    "expected": dict(current),
                }
            }
            self.assertTrue(
                verifier._validate_source_provenance(
                    stamp, identity, dict(current), current
                )["sha256Validated"]
            )
            closure_mutation = dict(current)
            closure_mutation["bytes"] += 1
            with self.assertRaisesRegex(verifier.VerificationError, "expectedSourceSnapshot"):
                verifier._validate_source_provenance(
                    stamp, identity, closure_mutation, current
                )
            stage_mutation = json.loads(json.dumps(stamp))
            stage_mutation["sourceFreshness"]["current"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(verifier.VerificationError, "sha256"):
                verifier._validate_source_provenance(
                    stage_mutation, identity, dict(current), current
                )
            stage_mtime_mutation = json.loads(json.dumps(stamp))
            stage_mtime_mutation["sourceFreshness"]["expected"]["mtime_ns"] += 1
            with self.assertRaisesRegex(verifier.VerificationError, "sourceFreshness.expected"):
                verifier._validate_source_provenance(
                    stage_mtime_mutation, identity, dict(current), current
                )

    def test_stage_clip_rejects_name_mutation_without_animestudio_metadata(self):
        for wrong_key in ("m_Name", "Name"):
            with self.subTest(wrong_key=wrong_key), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "source.chk"
                source.write_bytes(b"source")
                source_snapshot = verifier._snapshot(source)
                identity = {
                    "name": "TargetClip",
                    "type": "AnimationClip",
                    "pathId": -7,
                    "pathIdHex": "FFFFFFFFFFFFFFF9",
                    "source": source_snapshot["path"],
                    "sourceOffset": 99,
                    "cab": "CAB-test",
                    "container": "assets/test.fbx",
                }
                stage = root / "stage"
                clip_dir = stage / "AnimationClip"
                clip_dir.mkdir(parents=True)
                (stage / ".character_import_stage.json").write_text(
                    json.dumps(
                        {
                            "status": "ok",
                            "identity": identity,
                            "sourceFreshness": {
                                "status": "validated",
                                "current": source_snapshot,
                                "expected": source_snapshot,
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                clip_path = clip_dir / "TargetClip_pFFFFFFFFFFFFFFF9.json"
                clip = {"m_Name": "TargetClip", "Name": "TargetClip"}
                clip[wrong_key] = "WrongClip"
                clip_path.write_text(json.dumps(clip), encoding="utf-8")
                with self.assertRaisesRegex(verifier.VerificationError, wrong_key):
                    verifier._stage_clip(
                        stage,
                        identity,
                        {
                            "bytes": source_snapshot["bytes"],
                            "mtime_ns": source_snapshot["mtime_ns"],
                        },
                    )

    def test_remap_gates_fail_closed_for_each_required_mapping_attack(self):
        hashes = verifier.EXPECTED_BINDING_HASHES
        paths = {path_hash: f"Root/FX/{path_hash}" for path_hash in hashes}
        manifest = {
            "targetRows": [
                {"pathHash": path_hash, "candidateCount": 1, "candidatePaths": [paths[path_hash]]}
                for path_hash in hashes
            ]
        }
        avatar = {
            "targetRows": [
                {
                    "pathHash": path_hash,
                    "keyPresent": True,
                    "algorithmMatches": True,
                    "candidateCount": 1,
                    "candidatePaths": [paths[path_hash]],
                }
                for path_hash in hashes
            ]
        }
        model = {"containerModelRows": 1, "sourceOffsetModelRows": 1}
        self.assertTrue(verifier._remap_gates(model, manifest, avatar, hashes)["allGatesPassed"])
        attacks = {
            "model_closure": (dict(model, containerModelRows=0), manifest, avatar),
            "manifest_non_unique": (
                model,
                {"targetRows": [dict(row) for row in manifest["targetRows"][:-1]]},
                avatar,
            ),
            "avatar_tos_missing": (
                model,
                manifest,
                {"targetRows": [dict(row) for row in avatar["targetRows"][:-1]]},
            ),
            "manifest_avatar_mismatch": (
                model,
                manifest,
                {
                    "targetRows": [
                        dict(row, candidatePaths=["Root/Other/path"])
                        if row["pathHash"] == hashes[0]
                        else dict(row)
                        for row in avatar["targetRows"]
                    ]
                },
            ),
        }
        for name, (mutated_model, mutated_manifest, mutated_avatar) in attacks.items():
            with self.subTest(attack=name):
                gates = verifier._remap_gates(
                    mutated_model, mutated_manifest, mutated_avatar, hashes
                )
                self.assertFalse(gates["allGatesPassed"])
                self.assertTrue(gates["missingGates"])


if __name__ == "__main__":
    unittest.main()
