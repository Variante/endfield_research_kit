import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_taau_history_contract.py")
SPEC = importlib.util.spec_from_file_location("audit_taau_history_contract", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ResolveGameRootTests(unittest.TestCase):
    def test_accepts_install_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "GameAssembly.dll").touch()
            self.assertEqual(MODULE.resolve_game_root(root), root)

    def test_normalizes_endfield_data_child(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "Endfield_Data"
            data.mkdir()
            (root / "GameAssembly.dll").touch()
            self.assertEqual(MODULE.resolve_game_root(data), root)


class ContractProbeTests(unittest.TestCase):
    def test_order_probe_accepts_source_order(self) -> None:
        MODULE.require_order("Dilation MaskDilation Resolve", ("Dilation", "MaskDilation", "Resolve"), "passes")

    def test_order_probe_reports_missing_or_reordered_token(self) -> None:
        with self.assertRaisesRegex(AssertionError, "passes: missing ordered 'MaskDilation'"):
            MODULE.require_order("Dilation Resolve", ("Dilation", "MaskDilation", "Resolve"), "passes")

    def test_current_installed_contract_builds(self) -> None:
        audit = MODULE.build_audit()
        self.assertEqual(audit["schema"], "endfield.taau-history-contract.v1")
        self.assertEqual(audit["status"], "source_closed_live_handles_open")
        self.assertEqual(audit["contract"]["passOrder"], ["Dilation", "MaskDilation", "Resolve"])
        self.assertIn("Live TextureHandle identities", audit["contract"]["boundary"])
        self.assertEqual(audit["sceneHistory"]["writeback"]["preserveName"], "historySceneColor")


if __name__ == "__main__":
    unittest.main()
