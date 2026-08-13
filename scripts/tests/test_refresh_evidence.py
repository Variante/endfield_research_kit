from __future__ import annotations

import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.story_builder import refresh_evidence


class RefreshEvidenceTests(unittest.TestCase):
    def test_steps_use_importable_modules_not_script_paths(self) -> None:
        self.assertEqual(
            [step.module for step in refresh_evidence.STEPS],
            [
                "scripts.story_builder.dialog_registry",
                "scripts.story_builder.video_bindings",
                "scripts.story_builder.source_links",
                "scripts.story_builder.spaceship_story_content",
            ],
        )
        self.assertTrue(
            all("/" not in step.module and "\\" not in step.module for step in refresh_evidence.STEPS)
        )

    def test_run_step_invokes_python_module_from_repo_root(self) -> None:
        step = refresh_evidence.EvidenceStep("fixture", "scripts.fixture", ("--quiet",))
        completed = subprocess.CompletedProcess([], 0, "done", "")
        with patch.object(refresh_evidence.subprocess, "run", return_value=completed) as run:
            result = refresh_evidence.run_step(step)

        self.assertEqual(result.returncode, 0)
        run.assert_called_once_with(
            [sys.executable, "-m", "scripts.fixture", "--quiet"],
            cwd=refresh_evidence.ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


if __name__ == "__main__":
    unittest.main()
