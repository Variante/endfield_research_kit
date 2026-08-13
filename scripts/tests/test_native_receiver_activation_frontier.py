from __future__ import annotations

import unittest


from scripts.story_builder.native_receiver_activation_frontier import (
    classify_nominal_mission_host_comparisons,
    nominal_story_mission_candidates,
)


class NativeReceiverActivationFrontierTests(unittest.TestCase):
    def test_nominal_story_mission_candidate_stays_labeled(self) -> None:
        rows = nominal_story_mission_candidates(
            {
                "storyCoverage": {
                    "storyTriggerManifest": {
                        "black_testm1_1": {
                            "kind": "black",
                            "nominalMissionId": "testm1",
                        },
                        "black_unknown_1": {"kind": "black"},
                    }
                }
            },
            ["black_testm1_1", "black_unknown_1"],
        )
        self.assertEqual(rows, [{
            "storyKey": "black_testm1_1",
            "storyKind": "black",
            "nominalMissionId": "testm1",
        }])

    def test_validated_nominal_host_exclusion_is_exact_negative(self) -> None:
        self.assertEqual(
            classify_nominal_mission_host_comparisons([{
                "dictionaryValidated": True,
                "receiverScriptPresent": False,
            }]),
            "validated_nominal_mission_hosts_exclude_receiver_script",
        )

    def test_validated_membership_wins_over_exclusion(self) -> None:
        self.assertEqual(
            classify_nominal_mission_host_comparisons([
                {
                    "dictionaryValidated": True,
                    "receiverScriptPresent": False,
                },
                {
                    "dictionaryValidated": True,
                    "receiverScriptPresent": True,
                },
            ]),
            "nominal_mission_host_contains_receiver_script",
        )

    def test_unvalidated_host_fails_closed(self) -> None:
        self.assertEqual(
            classify_nominal_mission_host_comparisons([{
                "dictionaryValidated": False,
                "receiverScriptPresent": False,
            }]),
            "nominal_mission_host_dictionary_unresolved",
        )


if __name__ == "__main__":
    unittest.main()
