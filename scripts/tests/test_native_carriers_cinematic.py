from __future__ import annotations

import unittest

from scripts.story_recovery.native_carriers import cinematic_queue as audit


class CinematicQueueRuntimeAuditTests(unittest.TestCase):
    def test_missing_enqueue_sink_names_failed_gate(self):
        with self.assertRaisesRegex(
            RuntimeError,
            r"validator=cinematic_queue_runtime failed: gate=enqueue_sink .*actual=0",
        ):
            audit.discover_enqueue_family(
                "Fixture.Runtime.QueueDataBase",
                "Fixture.Runtime+QueueHandle",
                [],
            )

    def test_structural_contract_discovers_new_payloads_without_name_allowlist(self):
        handle_type = "Fixture.Runtime+QueueHandle"
        catalog = {"matchedTypes": [
            {
                "fullName": "Fixture.Runtime.QueueDataBase",
                "token": "0x02000001",
                "fields": [{"name": "cinematicId"}],
                "methods": [{"name": "get_queueItemType"}],
            },
            {
                "fullName": handle_type,
                "token": "0x02000002",
                "fields": [{"name": "m_finished"}, {"name": "id"}, {"name": "data"}],
                "methods": [{"name": "Finish"}],
            },
            {
                "fullName": "Fixture.Runtime.BrandNewPayload",
                "token": "0x02000003",
                "fields": [{"name": "extra"}],
                "methods": [
                    {"name": "get_queueItemType"},
                    {"name": "get_storyIdentity", "returnTypeName": "System.String"},
                ],
            },
        ]}
        body_map = {
            "bodyTargets": [
                {
                    "type": "Fixture.Actions",
                    "method": "PlayBrandNewByHandle",
                    "methodIndex": 12,
                    "token": "0x0600000c",
                    "parameterDetails": [{"name": "handle", "typeName": handle_type}],
                    "mappingStatus": "mapped",
                    "methodPointerVa": "0x1000",
                    "methodPointerRva": "0x1000",
                    "fileOffset": "0x800",
                },
                {
                    "type": "Fixture.Runtime",
                    "method": "Enqueue",
                    "methodIndex": 13,
                    "token": "0x0600000d",
                    "parameterDetails": [{
                        "name": "item",
                        "typeName": "Fixture.Runtime.QueueDataBase",
                    }],
                    "mappingStatus": "mapped",
                    "methodPointerVa": "0x2000",
                    "directCalls": [],
                },
                {
                    "type": "Fixture.Actions",
                    "method": "ProduceBrandNew",
                    "methodIndex": 14,
                    "token": "0x0600000e",
                    "parameterDetails": [{"name": "storyIdentity", "typeName": "System.String"}],
                    "mappingStatus": "mapped",
                    "methodPointerVa": "0x3000",
                    "directCalls": [{
                        "offset": 8,
                        "targetVa": "0x2000",
                        "resolved": [{"type": "Fixture.Runtime", "method": "Enqueue"}],
                    }],
                },
            ],
        }
        action_rows = [{
            "type": "Fixture.Actions.BrandNewAction",
            "method": "Execute",
            "slot": 15,
            "token": "0x0600000f",
            "methodPointerVa": "0x4000",
            "typeFields": [{"name": "_storyIdentity"}],
            "directCalls": [{
                "offset": 12,
                "targetVa": "0x3000",
                "resolved": [{"type": "Fixture.Actions", "method": "ProduceBrandNew"}],
            }],
        }]

        contract = audit.analyze_contract(catalog, body_map, action_rows)

        self.assertEqual(["PlayBrandNewByHandle"], contract["nativeDispatcherMethods"])
        self.assertEqual(
            ["get_storyIdentity"],
            contract["payloadTypes"][0]["idGetters"],
        )
        self.assertEqual(["ProduceBrandNew"], [
            row["method"] for row in contract["nativeProducers"]
        ])
        self.assertEqual(
            "BrandNewAction",
            contract["actionProducerRoutes"][0]["actionType"],
        )


if __name__ == "__main__":
    unittest.main()
