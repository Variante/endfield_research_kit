import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class WebUiOptionOverrideFilterTests(unittest.TestCase):
    def test_override_tag_does_not_replace_generated_option_issue(self) -> None:
        app = (ROOT / "webui" / "app.js").read_text(encoding="utf-8")
        labels = (ROOT / "webui" / "app_labels.js").read_text(encoding="utf-8")

        keep_issue = app.index("issues.push(code);", app.index("function applyOptionOverrideFlagsToEntries"))
        classify_coverage = app.index(
            "if (optionRecoveryIssueIsCovered(entry, overrideScene, code))",
            keep_issue,
        )
        self.assertLess(keep_issue, classify_coverage)
        self.assertIn('if (hasCoveredOptionRecoveryIssue) issues.push("overrided");', app)
        self.assertIn('"overrided",\n  "notOverrided",', labels)
        self.assertIn('storyIssueOverrided: "Option manually overridden"', labels)
        self.assertIn(
            'storyIssueOverrided: "\\u9009\\u9879\\u5df2\\u624b\\u52a8\\u8986\\u76d6"',
            labels,
        )


if __name__ == "__main__":
    unittest.main()
