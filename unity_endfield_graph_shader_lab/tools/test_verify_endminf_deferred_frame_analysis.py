import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_endminf_deferred_frame_analysis.py")
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_deferred_frame_analysis", MODULE_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EndminfDeferredFrameAnalysisTests(unittest.TestCase):
    def test_uses_unseeded_fnv1(self):
        self.assertEqual(MODULE.fnv1_64(b""), "0000000000000000")
        self.assertEqual(MODULE.fnv1_64(b"a"), "0000000000000061")
        self.assertEqual(MODULE.fnv1_64(b"ab"), "000061000000a4b1")

    def test_parses_texture_descriptor(self):
        descriptor = MODULE.parse_descriptor(
            'type=Texture2D width=3840 height=2160 format="R11G11B10_FLOAT" '
            'bind_flags="shader_resource render_target"'
        )
        self.assertEqual(descriptor["width"], 3840)
        self.assertEqual(descriptor["height"], 2160)
        self.assertEqual(descriptor["format"], "R11G11B10_FLOAT")
        self.assertEqual(descriptor["bind_flags"], "shader_resource render_target")

    def test_reports_missing_exact_draw(self):
        with tempfile.TemporaryDirectory() as temp:
            frame = Path(temp)
            (frame / "log.txt").write_text("", encoding="utf-8")
            report, failures = MODULE.audit_capture(frame)
        self.assertEqual(report["exactDraws"], [])
        self.assertTrue(any("exact_draw_count" in failure for failure in failures))

    def test_extracts_all_resource_slots(self):
        lines = [
            "000074 PSSetShaderResources(StartSlot:0, NumViews:28, ppShaderResourceViews:x)",
            *(f"       {slot}: view=x resource=y hash={slot:08x}" for slot in range(28)),
        ]
        resources = MODULE._draw_resource_hashes(lines, "000074")
        self.assertEqual(len(resources), 28)
        self.assertEqual(resources["t0"], "00000000")
        self.assertEqual(resources["t27"], "0000001b")

    def test_liteffect_instanced_parallax_draws_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as temp:
            frame = Path(temp) / "FrameAnalysis-2026-08-24-182646"
            frame.mkdir()
            (frame / "log.txt").write_text("", encoding="utf-8")
            for binding in ("ib=aaaa", "ps-t0=bbbb", "o0=cccc"):
                (frame / (
                    "000047-" + binding + "-vs=" + MODULE.LITEFFECT_VS_HASH +
                    "-ps=" + MODULE.LITEFFECT_PS_HASH + ".dsc"
                )).write_text("", encoding="utf-8")
            report, failures = MODULE.audit_capture(frame)
        self.assertEqual(report["litEffectInstancedParallaxDraws"], [47])
        self.assertTrue(any("liteffect_instanced_parallax_draws" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
