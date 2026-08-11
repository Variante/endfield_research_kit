import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("verify_overlay_runtime_inputs.py")
SPEC = importlib.util.spec_from_file_location("verify_overlay_runtime_inputs", SCRIPT)
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

    def test_leaves_missing_path_unchanged_for_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            configured = Path(directory) / "Endfield_Data"
            self.assertEqual(MODULE.resolve_game_root(configured), configured)


if __name__ == "__main__":
    unittest.main()
