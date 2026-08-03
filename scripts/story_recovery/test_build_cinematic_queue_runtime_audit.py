from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_cinematic_queue_runtime_audit as audit  # noqa: E402


class CinematicQueueRuntimeAuditTests(unittest.TestCase):
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
            "bodyTargets": [{
                "type": "Fixture.Actions",
                "method": "PlayBrandNewByHandle",
                "methodIndex": 12,
                "token": "0x0600000c",
                "parameterDetails": [{"name": "handle", "typeName": handle_type}],
                "mappingStatus": "mapped",
                "methodPointerVa": "0x1000",
                "methodPointerRva": "0x1000",
                "fileOffset": "0x800",
            }],
            "directCallEdges": [{
                "caller": {"type": "Fixture.Actions", "method": "AddCinematicItem2Queue"},
                "callees": [{"type": "Fixture.Runtime", "method": "AddCinematicQueueItem"}],
                "offset": 8,
                "targetVa": "0x2000",
            }],
        }

        contract = audit.analyze_contract(catalog, body_map)

        self.assertEqual(["PlayBrandNewByHandle"], contract["nativeDispatcherMethods"])
        self.assertEqual(
            ["get_storyIdentity"],
            contract["payloadTypes"][0]["idGetters"],
        )


if __name__ == "__main__":
    unittest.main()
