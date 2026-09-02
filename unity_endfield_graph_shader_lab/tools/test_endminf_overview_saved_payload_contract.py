#!/usr/bin/env python3
"""Source contract for Endminf's post-save native particle verification."""

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfOverviewEffectImporter.cs"
)
ANIMATION_IMPORTER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfEffectAnimationImporter.cs"
)
STAGE = ROOT / (
    "scratch/character_recovery/endminf_external_fx_rig/"
    "exact_four_root_stage"
)
ANIMATION_ROOT = ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/"
    "Effects/Overview/Animation"
)
ANIMATION_CONTRACT = ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "endminf_effect_animation_source_curve_contract.json"
)
ANIMATION_BUILDER = ROOT / (
    "tools/build_endminf_effect_animation_semantic_contract.py"
)
LOD_ACTIVATION_RUNTIME = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Animation/"
    "EndfieldRecoveredEffectLodActivation.cs"
)
LOD_ACTIVATION_CONTRACT = ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "endminf_effect_lod_activation_contract.json"
)
SPAWNER = ROOT / (
    "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredCharEffectSpawner.cs"
)
PATH_ID_MASK = (1 << 64) - 1


def stage_path_id(path: Path) -> int:
    return int(path.stem.rsplit("_p", 1)[1], 16)


def pptr_path_id(value: object) -> int:
    if not isinstance(value, dict):
        return 0
    for key in ("m_PathID", "pathID", "PathID"):
        if key in value:
            return int(value[key]) & PATH_ID_MASK
    return 0


def load_stage_type(type_name: str) -> dict[int, dict]:
    return {
        stage_path_id(path): json.loads(path.read_text(encoding="utf-8"))
        for path in (STAGE / type_name).glob("*.json")
    }


class EndminfOverviewSavedPayloadContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = IMPORTER.read_text(encoding="utf-8")

    def test_saved_payload_gate_runs_after_effect_animation_rebuild(self) -> None:
        build = self.source.index("public static void BuildAndValidate()")
        animation = self.source.index(
            "EndfieldEndminfEffectAnimationImporter.BuildAndValidate();", build
        )
        validate = self.source.index(
            "ValidateGenerated(gos, transforms, systems, renderers, forceFields,",
            animation,
        )
        self.assertLess(animation, validate)

    def test_saved_gate_identity_joins_all_game_objects_and_transforms(self) -> None:
        start = self.source.index(
            "private static void VerifySavedHierarchySourcePayloads("
        )
        end = self.source.index(
            "private static void VerifySavedSourcePayloads(", start
        )
        body = self.source[start:end]
        for token in (
            "gameObjects.TryGetValue(",
            "row.gameObjectPathId",
            "transforms.TryGetValue(",
            "row.transformPathId",
            'L.PPtrId(sourceTransform["m_GameObject"])',
            'sourceTransform["m_Father"]',
            'L.Str(sourceGameObject, "m_Name")',
            'L.Int(sourceGameObject, "m_Layer")',
            'L.Vector3Value(sourceTransform["m_LocalPosition"])',
            'L.QuaternionValue(sourceTransform["m_LocalRotation"])',
            'L.Vector3Value(sourceTransform["m_LocalScale"])',
        ):
            self.assertIn(token, body)
        self.assertIn(
            "consumedGameObjects.Count == gameObjects.Count", self.source
        )
        self.assertIn(
            "consumedTransforms.Count == transforms.Count", self.source
        )

    def test_source_child_graph_and_crystal_owner_order_are_exact(self) -> None:
        transforms = load_stage_type("Transform")
        renderers = load_stage_type("ParticleSystemRenderer")
        self.assertEqual(len(transforms), 101)

        referenced_children: set[int] = set()
        root_count = 0
        for parent_path_id, transform in transforms.items():
            parent = pptr_path_id(transform["m_Father"])
            if parent == 0:
                root_count += 1
            child_path_ids = [
                pptr_path_id(value) for value in transform["m_Children"]
            ]
            self.assertEqual(len(child_path_ids), len(set(child_path_ids)))
            for child_path_id in child_path_ids:
                self.assertNotIn(child_path_id, referenced_children)
                referenced_children.add(child_path_id)
                self.assertIn(child_path_id, transforms)
                self.assertEqual(
                    pptr_path_id(transforms[child_path_id]["m_Father"]),
                    parent_path_id,
                )
        self.assertEqual(root_count, 4)
        self.assertEqual(len(referenced_children), 97)

        game_object_to_transform = {
            pptr_path_id(row["m_GameObject"]): path_id
            for path_id, row in transforms.items()
        }
        target_materials = {
            "M13": 0x57A25F1386F7012F,
            "M14": 0xF6DCA5E6B2122169,
            "M21": 0x8EE22B791F9A2753,
            "M29": 0x7BCC4552203800A8,
            "M30": 0x5FE318FDDD817ADA,
        }
        owners: dict[str, int] = {}
        for owner, material_path_id in target_materials.items():
            matches = []
            for renderer in renderers.values():
                materials = [
                    pptr_path_id(value)
                    for value in renderer["m_Materials"]
                ]
                if material_path_id in materials:
                    matches.append(game_object_to_transform[
                        pptr_path_id(renderer["m_GameObject"])
                    ])
            self.assertEqual(len(matches), 1, owner)
            owners[owner] = matches[0]

        overview02_parent = pptr_path_id(
            transforms[owners["M13"]]["m_Father"]
        )
        self.assertEqual(
            overview02_parent,
            pptr_path_id(transforms[owners["M14"]]["m_Father"]),
        )
        self.assertEqual(
            overview02_parent,
            pptr_path_id(transforms[owners["M21"]]["m_Father"]),
        )
        overview02_children = [
            pptr_path_id(value)
            for value in transforms[overview02_parent]["m_Children"]
        ]
        self.assertEqual(
            [overview02_children.index(owners[name])
             for name in ("M13", "M14", "M21")],
            [2, 3, 10],
        )

        overview04_parent = pptr_path_id(
            transforms[owners["M29"]]["m_Father"]
        )
        self.assertEqual(
            overview04_parent,
            pptr_path_id(transforms[owners["M30"]]["m_Father"]),
        )
        overview04_children = [
            pptr_path_id(value)
            for value in transforms[overview04_parent]["m_Children"]
        ]
        self.assertEqual(
            [overview04_children.index(owners[name])
             for name in ("M29", "M30")],
            [0, 1],
        )

    def test_importer_applies_and_revalidates_every_ordered_child(self) -> None:
        build = self.source.index("public static void BuildAndValidate()")
        validate_graph = self.source.index(
            "ValidateExactSourceChildGraph(transforms);", build
        )
        validate_owners = self.source.index(
            "ValidateExactCrystalOwnerSourceOrder(transforms);", validate_graph
        )
        construct = self.source.index("var obj = new GameObject", validate_owners)
        apply_order = self.source.index(
            "ApplyExactSourceChildOrder(generated, transforms);", construct
        )
        marker_order = self.source.index(
            "GetComponentsInChildren<ParticleSystemRenderer>(true)", apply_order
        )
        self.assertLess(validate_graph, validate_owners)
        self.assertLess(validate_owners, construct)
        self.assertLess(construct, apply_order)
        self.assertLess(apply_order, marker_order)

        for token in (
            "transforms.Count == 101",
            'pair.Value["m_Children"]',
            "referencedChildren.Count == transforms.Count - rootCount",
            "child.transform.SetSiblingIndex(index);",
            "generated.childCount == sourceChildPathIds.Length",
            "childRow.generatedTransform.GetSiblingIndex() == index",
            "generated.GetChild(index) == childRow.generatedTransform",
            "expected M13 < M14 < M21",
            "expected M29 < M30",
        ):
            self.assertIn(token, self.source)

    def test_saved_gate_identity_joins_source_rows_to_direct_components(self) -> None:
        start = self.source.index("private static void VerifySavedSourcePayloads(")
        end = self.source.index("private static bool ValidateMoveWithTransform(", start)
        body = self.source[start:end]
        for token in (
            "systems.TryGetValue(",
            "node.particleSystemPathId",
            "renderers.TryGetValue(",
            "node.particleRendererPathId",
            'L.PPtrId(sourceSystem["m_GameObject"])',
            'L.PPtrId(sourceRenderer["m_GameObject"])',
            "node.generatedParticleSystem",
            "node.generatedRenderer",
            "VerifyFullParticlePayload(",
            "VerifyFullRendererPayload(",
        ):
            self.assertIn(token, body)

    def test_six_stone_force_fields_are_exact_and_fail_closed(self) -> None:
        systems = load_stage_type("ParticleSystem")
        force_fields = load_stage_type("ParticleSystemForceField")
        game_objects = load_stage_type("GameObject")
        transforms = load_stage_type("Transform")
        game_object_to_transform = {
            pptr_path_id(row["m_GameObject"]): path_id
            for path_id, row in transforms.items()
        }
        game_object_names = {
            path_id: row["m_Name"] for path_id, row in game_objects.items()
        }

        influenced_systems = []
        referenced_force_fields = []
        for row in systems.values():
            external = row["ExternalForcesModule"]
            influences = [
                pptr_path_id(value)
                for value in external["influenceList"]
            ]
            if not influences:
                continue
            influenced_systems.append(row)
            self.assertTrue(external["enabled"])
            self.assertEqual(len(influences), 1)
            referenced_force_fields.extend(influences)
            pptr_rows = row["$animestudio"]["pptrReferences"]
            source_reference = next(
                item for item in pptr_rows
                if item["path"] ==
                    "$.ExternalForcesModule.influenceList[0]"
            )
            self.assertEqual(source_reference["resolutionStatus"], "resolved")
            self.assertEqual(
                source_reference["targetType"],
                "ParticleSystemForceField",
            )
            self.assertEqual(
                pptr_path_id({"m_PathID": source_reference["targetPathId"]}),
                influences[0],
            )

        self.assertEqual(len(influenced_systems), 6)
        self.assertEqual(len(set(referenced_force_fields)), 6)
        self.assertEqual(set(referenced_force_fields), set(force_fields))
        for path_id, row in force_fields.items():
            self.assertEqual(row["$animestudio"]["type"],
                             "ParticleSystemForceField")
            self.assertEqual(row["$animestudio"]["classId"], 330)
            self.assertEqual(row["m_Enabled"], 1)
            game_object_path_id = pptr_path_id(row["m_GameObject"])
            self.assertIn(game_object_path_id, game_object_to_transform)
            self.assertRegex(game_object_names[game_object_path_id],
                             r"^suikuai \([3-6]\)$")

        for token in (
            'LoadType(stage, "ParticleSystemForceField")',
            "forceFields.Count == 6",
            "forceFieldHost.AddComponent<ParticleSystemForceField>()",
            'external.Remove("influenceList")',
            "generatedExternal.RemoveAllInfluences();",
            "generatedExternal.AddInfluence(forceField);",
            "generatedExternal.GetInfluence(index) == expected",
            "consumedForceFields.Count == forceFields.Count",
        ):
            self.assertIn(token, self.source)

    def test_safe_payload_helpers_are_shared_by_import_and_saved_gate(self) -> None:
        self.assertGreaterEqual(self.source.count("BuildSafeParticlePayload("), 3)
        self.assertGreaterEqual(self.source.count("BuildSafeRendererPayload("), 3)
        self.assertGreaterEqual(self.source.count("VerifyFullParticlePayload("), 3)
        self.assertGreaterEqual(self.source.count("VerifyFullRendererPayload("), 3)

    def test_renderer_excludes_only_intentional_dependency_overrides(self) -> None:
        safe_start = self.source.index(
            "private static Dictionary<string, object> BuildSafeRendererPayload("
        )
        verify_start = self.source.index(
            "private static void VerifyFullRendererPayload(", safe_start
        )
        safe_body = self.source[safe_start:verify_start]
        self.assertIn('safeRenderer.Remove("m_Materials")', safe_body)
        self.assertIn('key.StartsWith(\n                    "m_Mesh"', safe_body)
        self.assertNotIn('safeRenderer.Remove("m_Enabled")', safe_body)

        saved_start = verify_start
        saved_end = self.source.index("private static void ValidateGenerated(", saved_start)
        saved_body = self.source[saved_start:saved_end]
        self.assertEqual(saved_body.count('expected.Remove("m_Enabled")'), 1)
        self.assertNotIn('expected.Remove("m_RenderMode")', saved_body)

    def test_renderer_sorting_fudge_alias_is_explicit_and_complete(self) -> None:
        rows = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (STAGE / "ParticleSystemRenderer").glob("*.json")
        ]
        self.assertEqual(len(rows), 70)
        self.assertTrue(all(
            float(row["m_RendererSortingFudge"]) ==
            float(row["m_SortingFudge"])
            for row in rows
        ))
        self.assertEqual(
            sum(float(row["m_SortingFudge"]) == 4.0 for row in rows), 3
        )
        self.assertIn(
            'safeRenderer.Remove("m_RendererSortingFudge")', self.source
        )
        self.assertIn(
            'safeRenderer["m_SortingFudge"] = unitySortingFudge;', self.source
        )

    def test_runtime_does_not_replace_source_billboard_size_with_fitted_clamp(self) -> None:
        spawner = SPAWNER.read_text(encoding="utf-8")
        self.assertNotIn("ApplyEndminfBillboardClampCompatibility", spawner)
        self.assertNotIn("renderer.maxParticleSize = 10f", spawner)
        self.assertNotIn("renderer.maxParticleSize <= 0.5001f", spawner)

    def test_effect_animation_source_and_semantic_contract_are_pinned(self) -> None:
        animation_source = ANIMATION_IMPORTER.read_text(encoding="utf-8")
        builder_source = ANIMATION_BUILDER.read_text(encoding="utf-8")
        contract_bytes = ANIMATION_CONTRACT.read_bytes()
        contract = json.loads(contract_bytes)
        expected = {
            "A_actor_endminf_ui_overview_02_p910F78E15CD34301.json":
                "22c191d15ea18dc2d890b9c6e4411e8e2985c6ea5fd6db96263b499e3d86a70d",
            "A_fx_endminf_ui_overview_04_pDB8EF20719226683.json":
                "220ae359098e5a843afdced4680265e3eead2aba79b926988c5ba46ae6d42e6f",
        }
        self.assertEqual(
            contract["schema"],
            "endfield.endminf-effect-animation-source-curves.v2",
        )
        self.assertEqual(
            contract["status"],
            "source_derived_rebuildable_curve_contract",
        )
        self.assertEqual(
            {row["sourceFile"]: row["sourceSha256"]
             for row in contract["clips"]},
            expected,
        )
        self.assertEqual(
            sum(row["bindingCount"] for row in contract["clips"]),
            58,
        )
        self.assertEqual(
            sum(curve["keyCount"]
                for clip in contract["clips"] for curve in clip["curves"]),
            17_984,
        )
        canonical_contract_bytes = contract_bytes.replace(
            b"\r\n", b"\n"
        ).replace(b"\r", b"\n")
        contract_digest = hashlib.sha256(canonical_contract_bytes).hexdigest()
        self.assertIn(f'"{contract_digest}"', animation_source)
        for source_file, digest in expected.items():
            self.assertIn(f'"{source_file}"', animation_source)
            self.assertIn(f'"{digest}"', animation_source)
            self.assertIn(f'"{source_file}"', builder_source)
            self.assertIn(f'"{digest}"', builder_source)
        self.assertNotIn("ExactStageRelative", animation_source)
        self.assertNotIn("scratch/character_recovery", animation_source)
        self.assertNotIn("ValidateExactAnimationEvidence", animation_source)
        for token in (
            "endminf_effect_animation_source_curve_contract.json",
            "BuildOrReplaceClip(",
            "AssetDatabase.CreateAsset(clip, assetPath)",
            "AnimationUtility.SetEditorCurve(",
            "AnimationUtility.SetObjectReferenceCurve(clip, binding, null)",
            "AnimationUtility.SetKeyLeftTangentMode(",
            "AnimationUtility.SetKeyRightTangentMode(",
            "ValidateSemanticClip(",
            "AnimationUtility.GetCurveBindings(clip)",
            "AnimationUtility.GetEditorCurve(",
            "HashCurveTimeValues(curve)",
            "HashKeyPayload(",
            "ValidateExactKeyPayload(",
            '.Replace("\\r\\n", "\\n")',
            "Encoding.UTF8.GetBytes(canonicalText)",
        ):
            self.assertIn(token, animation_source)
        self.assertIn('"--check-contract"', builder_source)
        self.assertIn('"--check-generated"', builder_source)

    def test_shape_texture_boundary_does_not_claim_native_bc7_identity(self) -> None:
        self.assertIn(
            "hash-pinned decoded PNG content plus", self.source
        )
        self.assertIn(
            "does not claim native BC7 bytes or platform compression identity",
            self.source,
        )

    def test_lod_activation_uses_normal_creation_masks_and_source_active_bits(self) -> None:
        runtime = LOD_ACTIVATION_RUNTIME.read_text(encoding="utf-8")
        contract_bytes = LOD_ACTIVATION_CONTRACT.read_bytes().replace(
            b"\r\n", b"\n"
        ).replace(b"\r", b"\n")
        contract = json.loads(contract_bytes)
        contract_sha256 = hashlib.sha256(contract_bytes).hexdigest()
        self.assertIn(f'"{contract_sha256}"', self.source)
        self.assertEqual(
            contract["runtimeDefaults"],
            {
                "qualitySettingLodLevel": 8,
                "qualityNormalizationDomain": [1, 2, 4, 8],
                "targetLayers": 1,
            },
        )
        self.assertEqual(len(contract["rows"]), 101)
        self.assertTrue(all(row["authoredInitialActive"] for row in contract["rows"]))
        native = contract["nativeEvidence"]
        self.assertEqual(len(native["methodIdentities"]), 18)
        self.assertTrue(native["normalCreationRouteDirectCallerExcluded"])
        self.assertEqual(len(native["setAllTargetLayersCallerOwners"]), 2)
        self.assertEqual(len(native["byteGates"]), 10)
        self.assertTrue(native["recordedInstalledIfixNonreplacement"])
        self.assertIn("NormalCreationQualitySettingLodLevel = 8", runtime)
        self.assertIn("NormalCreationTargetLayers = 1", runtime)
        self.assertIn("row.authoredInitialActive &&", runtime)
        self.assertNotIn("showSettingLodLevel", runtime)
        self.assertNotIn("showTargetLayers", runtime)

    def test_lod_importer_configures_before_onenable(self) -> None:
        preflight = self.source.index("LoadAuthoredInitialActive(repo, gos);")
        first_asset_mutation = self.source.index("L.EnsureFolder(GeneratedRoot);")
        self.assertLess(preflight, first_asset_mutation)
        construct = self.source.index("var obj = new GameObject")
        inactive = self.source.index("obj.SetActive(false);", construct)
        attach = self.source.index("AttachExactLodActivation(", inactive)
        last_component_payload = self.source.index(
            "marker.particleNodes = markerNodes.ToArray();", inactive
        )
        self.assertLess(inactive, attach)
        self.assertLess(last_component_payload, attach)
        self.assertNotIn("obj.SetActive(true);", self.source)
        lod = self.source.index(
            "var activation = root.AddComponent<EndfieldRecoveredEffectLodActivation>();"
        )
        disabled = self.source.index("activation.enabled = false;", lod)
        rows = self.source.index("activation.rows = rows.ToArray();", disabled)
        apply = self.source.index("activation.ApplyBeforePlay();", rows)
        enabled = self.source.index("activation.enabled = true;", apply)
        self.assertLess(disabled, rows)
        self.assertLess(rows, apply)
        self.assertLess(apply, enabled)
        self.assertNotIn("activation.showSettingLodLevel", self.source)
        self.assertNotIn("activation.showTargetLayers", self.source)


if __name__ == "__main__":
    unittest.main()
