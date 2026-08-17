#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_m23_source_vertex_layout.py")
SPEC = importlib.util.spec_from_file_location("audit_m23_source_vertex_layout", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class M23SourceVertexLayoutAuditTests(unittest.TestCase):
    def test_current_sources_exclude_136_byte_producer(self) -> None:
        report = M.build_report(M.DEFAULT_MESH_ROOT, M.DEFAULT_RENDERER_ROOT)
        self.assertEqual(report["status"], "pass", report["failures"])
        self.assertEqual(report["authoredParticleLayout"]["strideBytes"], 60)
        self.assertEqual(report["exact0138Layout"]["strideBytes"], 136)
        self.assertFalse(report["admission"]["sourceMeshIs136ByteProducer"])
        self.assertFalse(report["admission"]["forkHgProducerResolved"])

    def test_missing_mesh_is_actionable_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = M.build_report(Path(temporary), M.DEFAULT_RENDERER_ROOT)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["firstFailure"],
                         "mesh.S_fx_lzy_xishou_01_p502A61E6E0572203.obj.present")

    def test_renderer_stream_drift_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = next(path for path in M.DEFAULT_RENDERER_ROOT.glob("*.json")
                          if json.loads(path.read_text(encoding="utf-8-sig"))["$animestudio"]["pathId"]
                          in M.EXPECTED_RENDERERS)
            data = json.loads(source.read_text(encoding="utf-8-sig"))
            data["m_VertexStreams"] = [0]
            (root / source.name).write_text(json.dumps(data), encoding="utf-8")
            report = M.build_report(M.DEFAULT_MESH_ROOT, root)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(row["id"].endswith(".streams") for row in report["failures"]))


if __name__ == "__main__":
    unittest.main()
