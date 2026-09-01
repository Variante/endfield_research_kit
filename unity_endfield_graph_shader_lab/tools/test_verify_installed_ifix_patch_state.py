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

    def test_loader_native_map_stale_build_reports_failure(self) -> None:
        report = {
            "source_build": {
                "game_assembly": {
                    "path_at_recovery": "C:/fixture/GameAssembly.dll",
                    "sha256": "a" * 64,
                },
                "global_metadata": {
                    "path_at_recovery": "C:/fixture/global-metadata.dat",
                    "sha256": "b" * 64,
                },
            }
        }
        catalog = {
            "metadata": {
                "path": "C:/fixture/global-metadata.dat",
                "sha256": "b" * 64,
            }
        }
        native_map = {
            "metadata": {
                "metadataPath": "C:/fixture/global-metadata.dat",
                "metadataSha256": "b" * 64,
                "gameAssembly": "C:/fixture/GameAssembly.dll",
                "gameAssemblySha256": "c" * 64,
            }
        }
        with self.assertRaisesRegex(SystemExit, "native map native-build provenance"):
            verifier.check_loader_build_provenance(report, catalog, native_map)


if __name__ == "__main__":
    unittest.main()
