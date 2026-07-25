from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.timeline_action_evidence import iter_mono_dirs


class TimelineActionEvidencePathTests(unittest.TestCase):
    def test_exact_monobehaviour_root_does_not_recurse_again(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "MonoBehaviour"
            nested = root / "nested" / "MonoBehaviour"
            nested.mkdir(parents=True)

            self.assertEqual([root], iter_mono_dirs([root]))


if __name__ == "__main__":
    unittest.main()
