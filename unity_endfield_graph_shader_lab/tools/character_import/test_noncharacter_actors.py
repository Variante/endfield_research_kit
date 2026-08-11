#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_import.noncharacter_actors import (  # noqa: E402
    DEFAULT_NONCHARACTER_CATALOG_ROOT,
    DEFAULT_NONHUMAN_DEPENDENCY_GUIDANCE,
    NPC_ARCHETYPE_CONTAINERS,
    build_extraction_plan,
    build_noncharacter_actor_catalog,
    write_noncharacter_catalogs,
)
from character_import import noncharacter_actors as noncharacter_module  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def container(group: str, stable_id: str) -> str:
    return (
        "assets/beyond/dynamicassets/gameplay/actors/postmodels/"
        f"{group}/{stable_id}_postmodel.prefab"
    )


def entry(
    group: str,
    stable_id: str,
    path_id: int,
    *,
    asset_type: str = "Animator",
    name: str | None = None,
) -> dict:
    source_container = (
        NPC_ARCHETYPE_CONTAINERS[stable_id]
        if group == "npc_archetypes"
        else container(group, stable_id)
    )
    return {
        "Name": name or stable_id + "_postmodel",
        "Container": source_container,
        "Source": str(Path(tempfile.gettempdir()) / f"source_{path_id}.chk"),
        "PathID": path_id,
        "Type": asset_type,
        "Hash": f"hash{path_id}",
        "Offset": abs(path_id) * 10,
    }


class NoncharacterActorCatalogTests(unittest.TestCase):
    def make_maps(self, root: Path, *, missing_animator: bool = False) -> list[Path]:
        streaming = root / "StreamingAssets" / "maps" / "assets.json"
        persistent = root / "Persistent" / "maps" / "assets.json"
        rows = [
            entry("enemies", "eny_0001_alpha", 1),
            entry("enemies", "eny_0001_alpha", 2, asset_type="Mesh"),
            entry("enemies", "eny_0001_alpha_death", 3),
            # A suffix alone is not enough to invent an alias relationship.
            entry("enemies", "eny_0002_orphan_death", 4),
            # Ability Animator names need not equal the prefab root.
            entry(
                "abilityentities",
                "abilityentity_interact_bomb",
                5,
                name="P_interactive_bombthrow01_01",
            ),
        ]
        rows.extend(
            entry(
                "npc_archetypes",
                stable_id,
                100 + index,
                name="P_" + stable_id[2:],
            )
            for index, stable_id in enumerate(NPC_ARCHETYPE_CONTAINERS)
        )
        if missing_animator:
            rows.append(
                entry(
                    "enemies",
                    "eny_0003_noanimator",
                    6,
                    asset_type="MonoBehaviour",
                )
            )
        write_json(streaming, {"GameType": "ArknightsEndfield", "AssetEntries": rows})
        write_json(persistent, {"GameType": "ArknightsEndfield", "AssetEntries": []})
        return [streaming, persistent]

    def test_original_container_rule_excludes_only_proven_base_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = build_noncharacter_actor_catalog(
                self.make_maps(root),
                work_root=root / "work",
            )

            self.assertEqual(catalog["canonical_group_counts"]["enemies"], 2)
            self.assertEqual(catalog["canonical_group_counts"]["abilityentities"], 1)
            self.assertEqual(catalog["canonical_group_counts"]["npc_archetypes"], 8)
            self.assertEqual(catalog["excluded_variant_count"], 1)
            self.assertEqual(
                [actor["stable_actor_id"] for actor in catalog["actors"]],
                [
                    "eny_0001_alpha",
                    "eny_0002_orphan_death",
                    "abilityentity_interact_bomb",
                    *list(NPC_ARCHETYPE_CONTAINERS),
                ],
            )
            variant = catalog["excluded_variants"][0]
            self.assertEqual(variant["variant_actor_id"], "eny_0001_alpha_death")
            self.assertEqual(variant["duplicate_of_identity"], "eny_0001_alpha")

    def test_capabilities_are_generic_fail_closed_without_humanoid_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = build_noncharacter_actor_catalog(
                self.make_maps(root),
                work_root=root / "work",
            )
            for actor in catalog["actors"]:
                capabilities = actor["capabilities"]
                self.assertTrue(capabilities["generic_hierarchy_extraction_supported"])
                self.assertTrue(capabilities["non_humanoid_safe_import"])
                self.assertFalse(capabilities["humanoid_avatar_proven"])
                self.assertFalse(
                    capabilities["extended_humanoid_101_slot_layout_proven"]
                )
                self.assertFalse(capabilities["humanoid_muscle_decode_enabled"])
                self.assertFalse(capabilities["resident_character_lineup_member"])

    def test_non_animator_container_is_excluded_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = build_noncharacter_actor_catalog(
                self.make_maps(root, missing_animator=True),
                work_root=root / "work",
            )
            self.assertEqual(catalog["excluded_no_animator_container_count"], 1)
            excluded = catalog["excluded_no_animator_containers"][0]
            self.assertEqual(excluded["stable_source_root"], "eny_0003_noanimator")

    def test_batch_plan_rejects_variants_and_unknown_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = build_noncharacter_actor_catalog(
                self.make_maps(root),
                work_root=root / "work",
            )
            with self.assertRaisesRegex(ValueError, "excluded variant"):
                build_extraction_plan(
                    catalog,
                    selected_actor_ids={"eny_0001_alpha_death"},
                )
            with self.assertRaisesRegex(ValueError, "unknown canonical"):
                build_extraction_plan(catalog, selected_actor_ids={"eny_9999_missing"})

    def test_group_catalog_contract_and_batch_order_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work_root = root / "work"
            catalog = build_noncharacter_actor_catalog(
                self.make_maps(root),
                work_root=work_root,
            )
            selected = {"eny_0001_alpha", "abilityentity_interact_bomb"}
            plan = build_extraction_plan(
                catalog,
                work_root=work_root,
                selected_actor_ids=selected,
                batch_size=1,
            )
            output_root = root / "catalogs"
            outputs = write_noncharacter_catalogs(
                catalog,
                plan,
                catalog_root=output_root,
            )
            first_bytes = {key: path.read_bytes() for key, path in outputs.items()}
            write_noncharacter_catalogs(catalog, plan, catalog_root=output_root)
            self.assertEqual(
                first_bytes,
                {key: path.read_bytes() for key, path in outputs.items()},
            )
            self.assertEqual(outputs["enemies"].name, "enemy_actor_model_catalog.json")
            self.assertEqual(
                outputs["abilityentities"].name,
                "ability_prop_actor_model_catalog.json",
            )
            self.assertEqual(
                outputs["npc_archetypes"].name,
                "ambient_npc_archetype_actor_model_catalog.json",
            )
            enemy_catalog = json.loads(outputs["enemies"].read_text(encoding="utf-8"))
            self.assertIn("actors", enemy_catalog)
            required = {
                "stable_actor_id",
                "root_name",
                "display_name",
                "postmodel_root",
                "postmodel_family",
                "source_classification",
                "canonical",
                "import_enabled",
                "selected_this_run",
                "manifest_asset_path",
                "prefab_asset_path",
            }
            for actor in enemy_catalog["actors"]:
                self.assertTrue(required <= set(actor))
                self.assertIn("/Generated/Actors/Enemies/", actor["manifest_asset_path"])
            selected_row = next(
                actor
                for actor in enemy_catalog["actors"]
                if actor["stable_actor_id"] == "eny_0001_alpha"
            )
            unselected_row = next(
                actor
                for actor in enemy_catalog["actors"]
                if actor["stable_actor_id"] == "eny_0002_orphan_death"
            )
            self.assertTrue(selected_row["selected_this_run"])
            self.assertIn("gallery_batch", selected_row)
            self.assertFalse(unselected_row["selected_this_run"])
            self.assertNotIn("gallery_batch", unselected_row)
            self.assertEqual(plan["selected_actor_count"], 2)
            self.assertEqual(plan["batch_count"], 2)

    def test_default_catalog_destination_matches_unity_contract(self) -> None:
        self.assertEqual(
            DEFAULT_NONCHARACTER_CATALOG_ROOT.as_posix().split("/")[-3:],
            ["Generated", "Actors", "Catalog"],
        )

    def test_cli_catalog_smoke_uses_catalog_and_plan_signatures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = {
                "canonical_group_counts": {
                    "enemies": 1,
                    "abilityentities": 1,
                    "npc_archetypes": 1,
                },
                "excluded_variant_count": 0,
            }
            plan = {"selected_actor_count": 3, "batch_count": 1}
            outputs = {
                "catalog": root / "catalog.json",
                "extraction_plan": root / "plan.json",
            }
            with (
                mock.patch.object(
                    noncharacter_module,
                    "build_noncharacter_actor_catalog",
                    autospec=True,
                    return_value=catalog,
                ) as build_catalog,
                mock.patch.object(
                    noncharacter_module,
                    "build_extraction_plan",
                    autospec=True,
                    return_value=plan,
                ) as build_plan,
                mock.patch.object(
                    noncharacter_module,
                    "write_noncharacter_catalogs",
                    autospec=True,
                    return_value=outputs,
                ),
            ):
                result = noncharacter_module.main(
                    [
                        "--work-root",
                        str(root / "work"),
                        "--catalog-root",
                        str(root / "catalogs"),
                    ]
                )
            self.assertEqual(result, 0)
            build_catalog.assert_called_once()
            build_plan.assert_called_once()


class InstalledNoncharacterActorSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from character_import.catalog import DEFAULT_ASSET_MAPS

        if not all(path.is_file() for path in DEFAULT_ASSET_MAPS):
            raise unittest.SkipTest("installed-game AssetMaps are unavailable")
        cls.catalog = build_noncharacter_actor_catalog(
            DEFAULT_ASSET_MAPS,
            dependency_guidance=(
                DEFAULT_NONHUMAN_DEPENDENCY_GUIDANCE
                if DEFAULT_NONHUMAN_DEPENDENCY_GUIDANCE.is_file()
                else None
            ),
        )

    def test_current_original_data_exact_counts(self) -> None:
        self.assertEqual(self.catalog["canonical_actor_count"], 131)
        self.assertEqual(
            self.catalog["canonical_group_counts"],
            {"enemies": 94, "abilityentities": 29, "npc_archetypes": 8},
        )
        self.assertEqual(self.catalog["excluded_variant_count"], 10)
        self.assertEqual(
            self.catalog["excluded_variant_kind_counts"],
            {
                "enemy_chrdg_variant": 1,
                "enemy_death_variant": 2,
                "enemy_race_variant": 6,
                "enemy_soldier_variant": 1,
            },
        )

    def test_current_multi_animator_containers_are_not_collapsed(self) -> None:
        by_id = {actor["stable_actor_id"]: actor for actor in self.catalog["actors"]}
        self.assertEqual(by_id["eny_0125_fdcentur"]["animator_count"], 2)
        self.assertEqual(
            by_id["abilityentity_eny_0081_ruanyi_skill011"]["animator_count"],
            3,
        )
        self.assertEqual(
            sum(actor["animator_count"] for actor in self.catalog["actors"]),
            136,
        )

    def test_current_asset_map_hashes_pin_the_source_boundary(self) -> None:
        hashes = [row["sha256"] for row in self.catalog["asset_maps"]]
        self.assertEqual(
            hashes,
            [
                "148415835F911FC94A634925C50C2D8B9A1CD4F5F141412F956CBB143805B6F3",
                "A6EAF031E7808DE8380AF7095A00CE02153F4C2FD2D7D723AF3CD72517AB3152",
            ],
        )

    def test_source_proven_zero_visible_renderer_contract(self) -> None:
        if self.catalog.get("dependency_guidance") is None:
            self.skipTest("source-derived dependency guidance is unavailable")
        by_id = {actor["stable_actor_id"]: actor for actor in self.catalog["actors"]}
        zero_ids = {
            stable_id
            for stable_id, actor in by_id.items()
            if actor["source_proven_zero_renderer"]
        }
        self.assertEqual(
            zero_ids,
            {
                "abilityentity_eny_klcommon_mech",
                "abilityentity_interact_bomb",
                "p_actor_gentlemannpc_01",
            },
        )
        bomb = by_id["abilityentity_interact_bomb"]
        self.assertEqual(bomb["render_class"], "particle_only")
        self.assertEqual(bomb["baseline_renderer_count"], 0)
        self.assertEqual(bomb["source_particle_system_count"], 9)
        self.assertEqual(
            bomb["renderer_exclusion_reason_counts"],
            {"particle_system_separate_runtime": 9},
        )
        gentleman = by_id["p_actor_gentlemannpc_01"]
        self.assertEqual(gentleman["baseline_renderer_count"], 0)
        self.assertEqual(
            gentleman["renderer_exclusion_reason_counts"],
            {"default_hg_runtime_material_placeholder": 15},
        )

    def test_nefarcore_external_geometry_and_builtin_cube_baselines(self) -> None:
        if self.catalog.get("dependency_guidance") is None:
            self.skipTest("source-derived dependency guidance is unavailable")
        by_id = {actor["stable_actor_id"]: actor for actor in self.catalog["actors"]}
        nefarcore = by_id["eny_0115_nefarcore"]
        self.assertEqual(nefarcore["declared_baseline_renderer_count"], 1)
        self.assertEqual(nefarcore["baseline_renderer_count"], 0)
        self.assertTrue(nefarcore["source_proven_external_geometry"])
        self.assertFalse(nefarcore["source_proven_zero_renderer"])
        self.assertEqual(
            nefarcore["external_geometry_reason"],
            "no_serialized_mesh_dependency",
        )
        hsrogue = by_id["abilityentity_eny_0085_hsrogue"]
        self.assertEqual(hsrogue["baseline_renderer_count"], 1)
        self.assertFalse(hsrogue["source_proven_external_geometry"])

    def test_generated_texture_plan_and_catalog_publication_are_exact(self) -> None:
        catalog_root = DEFAULT_NONCHARACTER_CATALOG_ROOT
        plan_path = catalog_root / "noncharacter_actor_extraction_plan.json"
        if not plan_path.is_file():
            self.skipTest("generated installed-source extraction plan is unavailable")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(plan["selected_actor_count"], 131)
        self.assertEqual(plan["selected_animator_entry_count"], 133)
        self.assertEqual(plan["source_job_count"], 131)
        self.assertEqual(plan["batch_count"], 7)
        self.assertEqual(
            plan["default_gallery_batch_sizes"],
            {"enemies": 24, "abilityentities": 16, "npc_archetypes": 16},
        )
        self.assertEqual(
            {
                group: [
                    batch["job_count"]
                    for batch in plan["batches"]
                    if batch["source_group"] == group
                ]
                for group in ("enemies", "abilityentities", "npc_archetypes")
            },
            {
                "enemies": [24, 24, 24, 22],
                "abilityentities": [16, 13],
                "npc_archetypes": [8],
            },
        )
        self.assertEqual(plan["dependency_job_count"], 49)
        self.assertEqual(
            sum(
                job["entry_count"]
                for job in plan["dependency_jobs"]
                if job["asset_type"] == "Mesh"
            ),
            371,
        )
        self.assertEqual(
            sum(
                job["entry_count"]
                for job in plan["dependency_jobs"]
                if job["asset_type"] == "Material"
            ),
            329,
        )
        self.assertEqual(plan["unresolved_baseline_dependency_count"], 1)
        self.assertEqual(plan["material_texture_binding_count"], 1471)
        self.assertEqual(plan["unresolved_texture_binding_count"], 0)
        enemy_bindings = [
            binding
            for binding in plan["material_texture_bindings"]
            if "eny_0007_mimicw" in binding.get("actor_ids", [])
        ]
        self.assertTrue(enemy_bindings)
        self.assertTrue(all(binding["file"] for binding in enemy_bindings))
        self.assertTrue(all(Path(binding["file"]).is_file() for binding in enemy_bindings))

        for filename in (
            "enemy_actor_model_catalog.json",
            "ability_prop_actor_model_catalog.json",
            "ambient_npc_archetype_actor_model_catalog.json",
        ):
            payload = json.loads((catalog_root / filename).read_text(encoding="utf-8"))
            enabled_count = sum(bool(actor["import_enabled"]) for actor in payload["actors"])
            self.assertIn(enabled_count, {0, len(payload["actors"])})

        group_baselines = {
            group: sum(
                actor["baseline_renderer_count"]
                for actor in self.catalog["actors"]
                if actor["source_classification"] == group
            )
            for group in ("enemy", "prop_only", "npc_source_archetype")
        }
        self.assertEqual(
            group_baselines,
            {"enemy": 290, "prop_only": 99, "npc_source_archetype": 56},
        )


if __name__ == "__main__":
    unittest.main()
