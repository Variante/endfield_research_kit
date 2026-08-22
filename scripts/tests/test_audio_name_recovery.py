import unittest
from unittest import mock

from scripts.audio_semantics import event_projection, identifiers, name_recovery


def inventory(*names_or_hashes) -> list[dict]:
    rows = []
    for value in names_or_hashes:
        event_hash = (
            value
            if isinstance(value, int)
            else identifiers.audio_hash_generator_compute(value)
        )
        rows.append({"eventHash": event_hash & 0xFFFFFFFF})
    return rows


class AudioHashContractTests(unittest.TestCase):
    def test_module_hash_matches_audio_hash_generator(self):
        for value in ("au_eny_0094_hsfly_skill03_charge", "Au_UI_Button_Close", ""):
            self.assertEqual(
                name_recovery._hash_units(name_recovery._code_units(value)),
                identifiers.audio_hash_generator_compute(value),
            )


class GrammarTests(unittest.TestCase):
    def test_grammar_splits_every_boundary_after_the_family(self):
        grammar = name_recovery.build_grammar(["au_eny_0094_hsfly_charge"])
        self.assertEqual(
            sorted(grammar),
            [("au_eny", 2), ("au_eny", 3), ("au_eny", 4)],
        )
        heads, tails = grammar[("au_eny", 3)]
        self.assertEqual(list(heads.values()), ["au_eny_0094"])
        self.assertEqual(list(tails.values()), ["hsfly_charge"])

    def test_grammar_skips_names_too_short_to_template(self):
        self.assertEqual(name_recovery.build_grammar(["au_eny", "au__x"]), {})

    def test_grammar_keeps_first_observed_casing(self):
        grammar = name_recovery.build_grammar(["Au_UI_Button_Close", "au_ui_Button_Open"])
        heads, tails = grammar[("au_ui", 3)]
        self.assertEqual(list(heads.values()), ["Au_UI_Button"])
        self.assertEqual(sorted(tails.values()), ["Close", "Open"])


class RecoveryTests(unittest.TestCase):
    def test_recovers_clustered_sibling_names(self):
        known = [
            "au_actor_aurora_ui_overview_to_weapon",
            "au_actor_aurora_ui_weapon_to_overview",
            "au_actor_avywen_ui_open_panel",
            "au_actor_azrila_ui_open_panel",
        ]
        targets = [
            "au_actor_avywen_ui_overview_to_weapon",
            "au_actor_avywen_ui_weapon_to_overview",
            "au_actor_azrila_ui_overview_to_weapon",
            "au_actor_azrila_ui_weapon_to_overview",
        ]
        result = name_recovery.recover_event_names(known, inventory(*known, *targets))

        self.assertEqual(result["status"], "complete")
        self.assertEqual(sorted(row["name"] for row in result["entries"]), sorted(targets))
        row = next(
            entry for entry in result["entries"] if entry["name"] == targets[0]
        )
        self.assertEqual(row["eventHash"], identifiers.audio_hash_generator_compute(targets[0]))
        self.assertEqual(row["eventHashHex"], f"0x{row['eventHash']:08x}")
        self.assertEqual(row["namingFamily"], "au_actor")
        self.assertEqual(row["corroboration"], name_recovery.PROMOTED_CORROBORATION)
        self.assertEqual(row["evidence"], name_recovery.NAME_EVIDENCE)
        self.assertGreaterEqual(row["headSiblingCount"], name_recovery.MIN_SIBLING_CLUSTER)
        self.assertGreaterEqual(row["tailSiblingCount"], name_recovery.MIN_SIBLING_CLUSTER)

    def test_a_lone_recovery_has_nothing_to_corroborate_it(self):
        known = [
            "au_actor_aurora_ui_overview_to_weapon",
            "au_actor_aurora_ui_weapon_to_overview",
            "au_actor_avywen_ui_overview_to_weapon",
        ]
        target = "au_actor_avywen_ui_weapon_to_overview"
        result = name_recovery.recover_event_names(known, inventory(*known, target))

        self.assertEqual(result["entries"], [])
        self.assertEqual([row["name"] for row in result["isolatedEntries"]], [target])

    def test_isolated_preimage_is_reported_but_never_promoted(self):
        known = ["au_int_belt_start_loop", "au_int_door_stop_loop"]
        target = "au_int_door_start_loop"
        result = name_recovery.recover_event_names(known, inventory(*known, target))

        self.assertEqual(result["entries"], [])
        self.assertEqual([row["name"] for row in result["isolatedEntries"]], [target])
        self.assertEqual(
            result["isolatedEntries"][0]["corroboration"],
            name_recovery.ISOLATED_CORROBORATION,
        )
        self.assertEqual(result["isolatedCount"], 1)
        self.assertEqual(result["promotedCount"], 0)

    def test_already_named_events_are_never_counted_as_recoveries(self):
        known = [
            "au_actor_aurora_ui_overview_to_weapon",
            "au_actor_aurora_ui_weapon_to_overview",
            "au_actor_avywen_ui_overview_to_weapon",
            "au_actor_avywen_ui_weapon_to_overview",
        ]
        result = name_recovery.recover_event_names(known, inventory(*known))

        self.assertEqual(result["targetHashCount"], 0)
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["entries"], [])

    def test_explicitly_resolved_hashes_are_excluded_from_targets(self):
        known = [
            "au_actor_aurora_ui_overview_to_weapon",
            "au_actor_aurora_ui_weapon_to_overview",
            "au_actor_avywen_ui_overview_to_weapon",
        ]
        target = "au_actor_avywen_ui_weapon_to_overview"
        target_hash = identifiers.audio_hash_generator_compute(target)
        result = name_recovery.recover_event_names(
            known,
            inventory(*known, target),
            named_event_hashes=[target_hash],
        )

        self.assertEqual(result["targetHashCount"], 0)
        self.assertEqual(result["entries"], [])

    def test_two_spellings_for_one_hash_are_dropped(self):
        # A real 32-bit collision presents as one target hash with two distinct
        # generated spellings; neither may be chosen.
        promoted, isolated, _ = name_recovery._corroborate({
            0x1234ABCD: {"au_x_aaa_bbb": "au_x_aaa_bbb", "au_x_ccc_ddd": "au_x_ccc_ddd"},
        })
        self.assertEqual(promoted, {})
        self.assertEqual(isolated, {})

    def test_ambiguous_hashes_are_counted_in_the_summary(self):
        known = ["au_x_aaa_bbb", "au_x_ccc_ddd"]
        with mock.patch.object(
            name_recovery,
            "_corroborate",
            lambda matches: ({}, {}, {}),
        ):
            result = name_recovery.recover_event_names(
                known,
                inventory("au_x_aaa_ddd", "au_x_ccc_bbb"),
            )
        self.assertEqual(result["matchCount"], 2)
        self.assertEqual(result["ambiguousHashCount"], 2)
        self.assertEqual(result["entries"], [])

    def test_statistics_are_reported(self):
        known = [
            "au_actor_aurora_ui_overview_to_weapon",
            "au_actor_aurora_ui_weapon_to_overview",
            "au_actor_avywen_ui_overview_to_weapon",
        ]
        target = "au_actor_avywen_ui_weapon_to_overview"
        result = name_recovery.recover_event_names(known, inventory(*known, target))

        self.assertEqual(result["schemaVersion"], name_recovery.SCHEMA_VERSION)
        self.assertGreater(result["candidateCount"], 0)
        self.assertGreaterEqual(result["passes"], 1)
        self.assertGreaterEqual(result["expectedCoincidentalPreimages"], 0.0)
        self.assertIn("does not prove a caller", result["evidenceBoundary"])

    def test_degrades_without_a_seed_grammar(self):
        result = name_recovery.recover_event_names([], inventory("au_x_y_z"))
        self.assertEqual(result["status"], "degraded")
        self.assertIn("grammar", result["reason"])


class ProjectionWiringTests(unittest.TestCase):
    def test_recovered_names_are_published_as_exact_event_aliases(self):
        alias = {
            "eventHash": 0x1234ABCD,
            "name": "au_actor_avywen_battle_dead",
            "corroboration": name_recovery.PROMOTED_CORROBORATION,
            "evidence": name_recovery.NAME_EVIDENCE,
        }
        aliases = event_projection.exact_wwise_event_aliases({
            "grammarRecoveredWwiseEventNames": [alias],
        })
        self.assertEqual([row["name"] for row in aliases], [alias["name"]])

    def test_a_conflicting_name_from_another_source_drops_the_hash(self):
        aliases = event_projection.exact_wwise_event_aliases({
            "voiceTableWwiseEventAliases": [
                {"eventHash": 0x1234ABCD, "name": "vo_narrating_real_name"},
            ],
            "grammarRecoveredWwiseEventNames": [
                {
                    "eventHash": 0x1234ABCD,
                    "name": "au_actor_avywen_battle_dead",
                    "corroboration": name_recovery.PROMOTED_CORROBORATION,
                },
            ],
        })
        self.assertEqual(aliases, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
