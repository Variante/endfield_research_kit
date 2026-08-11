import unittest
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("verify_installed_ifix_patch_state.py")
SPEC = importlib.util.spec_from_file_location("verify_installed_ifix_patch_state", SCRIPT)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class InstalledIfixVerifierTests(unittest.TestCase):
    def test_refresh_metadata_accepts_matching_patch_sha(self) -> None:
        report = {
            "refresh": {
                "tool": "refresh_installed_ifix_patch_state.py",
                "source_patch_sha256": "a" * 64,
            }
        }
        verifier.check_refresh_metadata(report, {"sha256": "a" * 64})

    def test_refresh_metadata_reports_expected_and_actual_sha(self) -> None:
        report = {
            "refresh": {
                "tool": "refresh_installed_ifix_patch_state.py",
                "source_patch_sha256": "b" * 64,
            }
        }
        with self.assertRaisesRegex(
            SystemExit,
            r"IFix report refresh patch SHA mismatch: expected='a{64}' actual='b{64}'",
        ):
            verifier.check_refresh_metadata(report, {"sha256": "a" * 64})


if __name__ == "__main__":
    unittest.main()
