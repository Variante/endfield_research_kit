from __future__ import annotations

import unittest

from scripts.story_builder.dialog_tree_routes import (
    DIALOG_TREE_RUNTIME_DEFAULTS,
    recover_dialog_tree_finish_endpoints,
)


def node(node_id: str | None, node_type: str, **fields) -> dict:
    row = {"$type": f"Beyond.Gameplay.{node_type}, Gameplay.Beyond", **fields}
    if node_id is not None:
        row["$id"] = node_id
    return row


def connection(source_id: str, target_id: str) -> dict:
    return {
        "$type": "Beyond.Gameplay.DialogTreeConnection, Gameplay.Beyond",
        "_sourceNode": {"$ref": source_id},
        "_targetNode": {"$ref": target_id},
    }


class DialogTreeFinishEndpointTests(unittest.TestCase):
    def test_recovers_prime_reachable_explicit_and_default_finish_ids(self) -> None:
        recovered = recover_dialog_tree_finish_endpoints(
            [
                node("start", "DialogTreeCinematicNode"),
                node("explicit", "DialogTreeFinishNode", finishId=3),
                node("default", "DialogTreeFinishNode"),
            ],
            [connection("start", "explicit"), connection("start", "default")],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )

        self.assertEqual(recovered["primeNodeId"], "start")
        self.assertEqual(recovered["counts"]["validatedFinishEndpoints"], 2)
        self.assertEqual(recovered["counts"]["explicitFinishIds"], 1)
        self.assertEqual(recovered["counts"]["runtimeDefaultFinishIds"], 1)
        self.assertEqual(
            [
                (row["finishId"], row["finishIdSource"], row["nodePath"])
                for row in recovered["endpoints"]
            ],
            [
                (3, "serialized_explicit", ["start", "explicit"]),
                (0, "runtime_default", ["start", "default"]),
            ],
        )

    def test_detached_finish_node_fails_closed(self) -> None:
        recovered = recover_dialog_tree_finish_endpoints(
            [
                node("start", "DialogTreeTrunkNode"),
                node("finish", "DialogTreeFinishNode", finishId=1),
            ],
            [],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )

        endpoint = recovered["endpoints"][0]
        self.assertEqual(endpoint["status"], "rejected")
        self.assertEqual(
            endpoint["failureClass"],
            "finish_node_not_reachable_from_prime",
        )
        self.assertEqual(
            endpoint["issue"]["gate"], "finishPrimeReachability"
        )
        self.assertEqual(recovered["counts"]["unreachableFinishNodes"], 1)

    def test_unreferenced_finish_definition_is_retained_as_diagnostic(self) -> None:
        recovered = recover_dialog_tree_finish_endpoints(
            [
                node("start", "DialogTreeTrunkNode"),
                node(None, "DialogTreeFinishNode", finishId=1),
            ],
            [],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )

        endpoint = recovered["endpoints"][0]
        self.assertEqual(endpoint["status"], "rejected")
        self.assertEqual(
            endpoint["failureClass"], "unreferenced_finish_definition"
        )
        self.assertEqual(
            recovered["counts"]["unreferencedFinishDefinitions"], 1
        )

    def test_invalid_finish_id_is_not_replaced_by_runtime_default(self) -> None:
        recovered = recover_dialog_tree_finish_endpoints(
            [
                node("start", "DialogTreeTrunkNode"),
                node("finish", "DialogTreeFinishNode", finishId=True),
            ],
            [connection("start", "finish")],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )

        endpoint = recovered["endpoints"][0]
        self.assertEqual(endpoint["status"], "rejected")
        self.assertEqual(
            endpoint["failureClass"], "invalid_serialized_finish_id"
        )
        self.assertEqual(
            endpoint["issue"]["actual"], "invalid_serialized_value"
        )

    def test_invalid_connection_reference_invalidates_endpoint_path(self) -> None:
        recovered = recover_dialog_tree_finish_endpoints(
            [
                node("start", "DialogTreeTrunkNode"),
                node("finish", "DialogTreeFinishNode", finishId=1),
            ],
            [connection("missing", "finish")],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )

        endpoint = recovered["endpoints"][0]
        self.assertEqual(endpoint["status"], "rejected")
        self.assertEqual(
            endpoint["failureClass"], "invalid_finish_connection_graph"
        )
        self.assertTrue(
            any(issue["gate"] == "connectionReference" for issue in recovered["issues"])
        )


if __name__ == "__main__":
    unittest.main()
