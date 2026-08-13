from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULES = (
    "context",
    "envtalk_attachment",
    "lua_consumer_references",
    "mission_dependency_graph",
    "node_attachment",
)


class StoryBuilderImportIdentityTests(unittest.TestCase):
    def test_common_imports_do_not_catch_internal_missing_modules(self):
        for name in MODULES:
            path = ROOT / "scripts" / "story_builder" / f"{name}.py"
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            broad_handlers = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.ExceptHandler)
                and isinstance(node.type, ast.Name)
                and node.type.id == "ModuleNotFoundError"
            ]
            self.assertEqual(broad_handlers, [], name)

    def test_both_supported_package_identities_select_the_matching_common(self):
        module_list = ",".join(repr(name) for name in MODULES)
        probe = (
            "import importlib; "
            f"names=({module_list},); "
            "mods=[importlib.import_module(PREFIX+n) for n in names]; "
            "assert all(m.__package__ == PACKAGE for m in mods); "
            "print(PACKAGE)"
        )
        cases = (
            ("scripts.story_builder.", "scripts.story_builder", None),
            ("story_builder.", "story_builder", str(ROOT / "scripts")),
        )
        for prefix, package, pythonpath in cases:
            env = os.environ.copy()
            if pythonpath is None:
                env.pop("PYTHONPATH", None)
            else:
                env["PYTHONPATH"] = pythonpath
            command = f"PREFIX={prefix!r}; PACKAGE={package!r}; {probe}"
            result = subprocess.run(
                [sys.executable, "-c", command],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), package)


if __name__ == "__main__":
    unittest.main()
