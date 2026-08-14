from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = (
    "benchmark_export.py",
    "verify_export_freshness.py",
)


class RootScriptImportIdentityTests(unittest.TestCase):
    def test_identity_imports_do_not_catch_internal_missing_modules(self) -> None:
        for name in SCRIPTS:
            path = ROOT / "scripts" / name
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            broad_handlers = [
                handler
                for node in tree.body
                if isinstance(node, ast.Try)
                for handler in node.handlers
                if isinstance(handler.type, ast.Name)
                and handler.type.id in {"ImportError", "ModuleNotFoundError"}
            ]
            self.assertEqual(broad_handlers, [], name)

    def test_direct_and_module_help_identities(self) -> None:
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        for name in SCRIPTS:
            module = f"scripts.{Path(name).stem}"
            commands = (
                [sys.executable, str(ROOT / "scripts" / name), "--help"],
                [sys.executable, "-m", module, "--help"],
            )
            for command in commands:
                result = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
