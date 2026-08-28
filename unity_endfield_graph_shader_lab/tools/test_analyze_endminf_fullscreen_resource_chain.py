#!/usr/bin/env python3

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("analyze_endminf_fullscreen_resource_chain.py")
SPEC = importlib.util.spec_from_file_location("endminf_chain", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def resolver(ordinal, vs, ps, inputs=(), outputs=()):
    return {
        "fullscreenOrdinal": ordinal,
        "shaders": [
            {"stage": 0, "identityHash": vs},
            {"stage": 4, "identityHash": ps},
        ],
        "resourceChain": {
            "psInputs": [
                {"slot": slot, "objectId": object_id, "viewId": view_id}
                for slot, object_id, view_id in inputs
            ],
            "renderTargets": [
                {"slot": slot, "objectId": object_id, "viewId": view_id}
                for slot, object_id, view_id in outputs
            ],
        },
    }


class ResourceChainTests(unittest.TestCase):
    def write_session(self, root, resolvers):
        frame = root / "graphics" / "frames" / "100"
        frame.mkdir(parents=True)
        (frame / "metadata.json").write_text(json.dumps({
            "frame": 100,
            "captureIncomplete": False,
            "captureFailed": False,
            "fullscreenResolverRecordsTruncated": False,
            "fullscreenResolvers": resolvers,
        }), encoding="utf-8")

    def test_exact_object_identity_recovers_nearest_producer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_session(root, [
                resolver(20, 1, 2, outputs=((0, 100, 200),)),
                resolver(22, 3, 4, outputs=((0, 100, 201),)),
                resolver(23, MODULE.NORMAL_UBER_VS, MODULE.NORMAL_UBER_PS,
                         inputs=((0, 100, 300), (1, 999, 301)),
                         outputs=((0, 101, 400),)),
            ])
            result = MODULE.analyze(root)
            self.assertEqual(result["matchedEdgeCount"], 1)
            edge = result["samples"][0]["edges"][0]
            self.assertEqual(edge["producerOrdinal"], 22)
            self.assertEqual(edge["producerViewId"], 201)
            self.assertTrue(edge["exactObjectIdentityMatch"])

    def test_missing_resource_chain_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_session(root, [{
                "fullscreenOrdinal": 1,
                "shaders": [],
            }])
            with self.assertRaisesRegex(MODULE.AnalysisError, "lacks resourceChain"):
                MODULE.analyze(root)

    def test_truncated_resolver_census_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_session(root, [])
            path = root / "graphics" / "frames" / "100" / "metadata.json"
            metadata = json.loads(path.read_text(encoding="utf-8"))
            metadata["fullscreenResolverRecordsTruncated"] = True
            path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.AnalysisError, "census is truncated"):
                MODULE.analyze(root)


if __name__ == "__main__":
    unittest.main()
