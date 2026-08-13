from __future__ import annotations

import unittest

from scripts.story_builder.dialog_tree_routes import (
    DIALOG_TREE_RUNTIME_DEFAULTS,
    recover_dialog_tree_option_routes,
)


def node(node_id: str, node_type: str) -> dict:
    return {"$id": node_id, "$type": f"Beyond.Gameplay.{node_type}"}


def option_node(options: list[dict], *, has_extra: bool = False) -> dict:
    return {
        "$id": "option",
        "$type": "Beyond.Gameplay.DialogTreeOptionNode",
        "_normalOptions": options,
        "_hasExOption": has_extra,
    }


def connection(target: str) -> dict:
    return {
        "_sourceNode": {"$ref": "option"},
        "_targetNode": {"$ref": target},
    }


class DialogTreeOptionRouteTests(unittest.TestCase):
    def test_omitted_index_uses_only_validated_managed_default(self) -> None:
        nodes = [
            option_node([{"_optionId": "option_a"}]),
            node("target", "DialogTreeFinishNode"),
        ]
        without_contract = recover_dialog_tree_option_routes(
            nodes, [connection("target")]
        )
        self.assertEqual(
            without_contract["nodes"][0]["routes"][0]["status"], "rejected"
        )

        validated = recover_dialog_tree_option_routes(
            nodes,
            [connection("target")],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )
        route = validated["nodes"][0]["routes"][0]
        self.assertEqual(route["status"], "validated")
        self.assertEqual(route["connectionIndex"], 0)
        self.assertEqual(route["connectionIndexSource"], "runtime_default")

    def test_explicit_index_selects_physical_edge_not_option_ordinal(self) -> None:
        recovered = recover_dialog_tree_option_routes(
            [
                option_node(
                    [
                        {"_optionId": "option_a", "index": 2},
                        {"_optionId": "option_b", "index": 0},
                    ],
                    has_extra=True,
                ),
                node("first", "DialogTreeFinishNode"),
                node("extra", "DialogTreeExOptionNode"),
                node("third", "DialogTreeFinishNode"),
            ],
            [connection("first"), connection("extra"), connection("third")],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )
        routes = recovered["nodes"][0]["routes"]
        self.assertEqual(
            [(route["optionId"], route["targetNodeId"]) for route in routes],
            [("option_a", "third"), ("option_b", "first")],
        )
        self.assertEqual(recovered["counts"]["extraOptionNodes"], 1)
        self.assertEqual(recovered["counts"]["connectionCountMismatchNodes"], 1)

    def test_out_of_range_index_is_retained_as_bounded_diagnostic(self) -> None:
        recovered = recover_dialog_tree_option_routes(
            [
                option_node(
                    [
                        {"_optionId": "option_a", "index": 0},
                        {"_optionId": "option_b", "index": 1},
                    ]
                ),
                node("only", "DialogTreeFinishNode"),
            ],
            [connection("only")],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )
        routes = recovered["nodes"][0]["routes"]
        self.assertEqual(routes[0]["status"], "validated")
        self.assertEqual(routes[1]["status"], "rejected")
        self.assertEqual(
            routes[1]["issue"]["gate"], "normalOptionConnectionIndexBounds"
        )
        self.assertEqual(
            routes[1]["issue"]["expected"], {"minimum": 0, "maximumExclusive": 1}
        )
        self.assertEqual(
            routes[1]["failureClass"],
            "serialized_connection_index_out_of_bounds",
        )
        self.assertEqual(
            recovered["nodes"][0]["routingClass"],
            "linked_option_node_with_partial_index_coverage",
        )
        self.assertEqual(recovered["nodes"][0]["nodeOrdinal"], 0)
        self.assertEqual(
            recovered["counts"]["linkedOptionNodesWithPartialIndexCoverage"],
            1,
        )
        self.assertEqual(
            recovered["counts"]["serializedConnectionIndexesOutOfBounds"], 1
        )

    def test_linked_option_node_without_edges_is_not_treated_as_terminal(self) -> None:
        recovered = recover_dialog_tree_option_routes(
            [option_node([{"_optionId": "option_a", "index": 0}])],
            [],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )
        node_row = recovered["nodes"][0]
        route = node_row["routes"][0]
        self.assertEqual(
            node_row["routingClass"],
            "linked_option_node_without_outgoing_connections",
        )
        self.assertEqual(node_row["incomingConnectionCount"], 0)
        self.assertEqual(
            route["failureClass"],
            "linked_option_node_without_outgoing_connections",
        )
        self.assertEqual(
            recovered["counts"]["linkedOptionNodesWithoutOutgoingConnections"],
            1,
        )
        self.assertEqual(
            recovered["counts"]["linkedNormalOptionsWithoutOutgoingConnections"],
            1,
        )

    def test_shared_physical_edge_requires_both_authored_indexes(self) -> None:
        recovered = recover_dialog_tree_option_routes(
            [
                option_node(
                    [
                        {"_optionId": "option_a", "index": 0},
                        {"_optionId": "option_b", "index": 0},
                    ]
                ),
                node("shared", "DialogTreeFinishNode"),
            ],
            [connection("shared")],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )
        self.assertEqual(
            [route["targetNodeId"] for route in recovered["nodes"][0]["routes"]],
            ["shared", "shared"],
        )

    def test_option_node_without_graph_identity_is_counted_and_rejected(self) -> None:
        invalid_option_node = option_node([{"_optionId": "option_a", "index": 0}])
        invalid_option_node.pop("$id")
        recovered = recover_dialog_tree_option_routes(
            [invalid_option_node, node("target", "DialogTreeFinishNode")],
            [],
            runtime_defaults=DIALOG_TREE_RUNTIME_DEFAULTS,
        )
        self.assertEqual(recovered["counts"]["authoredOptionNodes"], 1)
        self.assertEqual(recovered["counts"]["unrecoverableOptionNodes"], 1)
        self.assertEqual(
            recovered["counts"]["unreferencedOptionDefinitionNodes"], 1
        )
        self.assertEqual(
            recovered["counts"]["unreferencedOptionDefinitionRoutes"], 1
        )
        self.assertEqual(recovered["counts"]["rejectedNormalOptionRoutes"], 1)
        self.assertEqual(
            recovered["nodes"][0]["routingClass"],
            "unreferenced_option_definition",
        )
        route = recovered["nodes"][0]["routes"][0]
        self.assertEqual(route["status"], "rejected")
        self.assertEqual(route["failureClass"], "unreferenced_option_definition")
        self.assertEqual(route["issue"]["gate"], "nodeIdentity")


if __name__ == "__main__":
    unittest.main()
