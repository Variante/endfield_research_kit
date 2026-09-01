import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "verify_charinfo_presentation_recovery.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_charinfo_presentation_recovery",
    MODULE_PATH,
)
subject = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(subject)


class CharInfoPresentationRecoveryVerifierTests(unittest.TestCase):
    def test_current_source_background_renderer_contract_passes(self) -> None:
        subject.verify_implementation()

    def test_missing_contract_token_reports_path_and_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "presentation.cs"
            path.write_text("current contract", encoding="utf-8")
            with self.assertRaisesRegex(
                AssertionError,
                r"presentation\.cs: missing required token 'expected contract'",
            ):
                subject.require_tokens(path, ["expected contract"])


if __name__ == "__main__":
    unittest.main()
