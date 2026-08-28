import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
RUNTIMES = (
    "EndfieldRecoveredEndminfM18PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfM21PeakExactRuntime.cs",
    "EndfieldRecoveredEndminfM28PeakExactRuntime.cs",
)


class EndminfPeakExactCaptureWindowContractTests(unittest.TestCase):
    def test_single_frame_packets_are_not_replayed_across_adjacent_ticks(self) -> None:
        for name in RUNTIMES:
            with self.subTest(runtime=name):
                source = (RUNTIME_ROOT / name).read_text(encoding="utf-8")
                self.assertRegex(
                    source,
                    r"HalfWindowSeconds\s*=\s*1\.0f\s*/\s*120\.0f;",
                )
                self.assertIn("Mathf.Abs(", source)
                self.assertIn("<=\n                HalfWindowSeconds", source)

        uber = (RUNTIME_ROOT / "EndfieldRecoveredEndminfUberExactRuntime.cs").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            uber,
            r"HalfWindowSeconds\s*=\s*1\.0f\s*/\s*120\.0f;",
        )
        self.assertIn("if (!IsCapturedPhase(hasPost, post))", uber)
        self.assertIn("post.mode == 6", uber)
        self.assertIn("Mathf.Abs(post.elapsed - CapturePhaseSeconds)", uber)

    def test_inactive_exact_paths_restore_the_authored_renderer(self) -> None:
        for name in RUNTIMES[:2]:
            with self.subTest(runtime=name):
                source = (RUNTIME_ROOT / name).read_text(encoding="utf-8")
                self.assertIn("renderer.enabled = !active", source)

        m28 = (RUNTIME_ROOT / RUNTIMES[2]).read_text(encoding="utf-8")
        prepare = m28.index("internal bool PrepareBeforeCulling")
        restore = m28.index("RestoreSourceRenderers();", prepare)
        active = m28.index("active = !float.IsNaN", restore)
        suppress = m28.index("SuppressSourceRenderers();", active)
        self.assertLess(restore, active)
        self.assertLess(active, suppress)


if __name__ == "__main__":
    unittest.main()
