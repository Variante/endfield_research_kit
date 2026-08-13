from __future__ import annotations

import contextlib
import io
import unittest

from scripts.story_builder import build


class StoryBuildCliTests(unittest.TestCase):
    def test_default_arguments_are_owned_by_build_module(self) -> None:
        args = build.parse_args([])
        self.assertEqual(args.default_language, "CN")
        self.assertEqual(args.timeline_recovery, "auto")
        self.assertFalse(hasattr(args, "skip_audio_link"))

    def test_removed_audio_relink_flag_is_rejected(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                build.parse_args(["--skip-audio-link"])


if __name__ == "__main__":
    unittest.main()
