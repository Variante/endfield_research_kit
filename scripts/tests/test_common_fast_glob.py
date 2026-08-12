from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
import tempfile
import time
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("common", HERE.parent / "common.py")
COMMON = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# Register before executing: dataclasses resolves annotations through
# sys.modules, so a path-loaded module must be findable under its own name.
sys.modules.setdefault(SPEC.name, COMMON)
SPEC.loader.exec_module(COMMON)


class FastGlobFilesTests(unittest.TestCase):
    def test_rel_path_preserves_lexical_inside_and_outside_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inside = root / "nested" / "fixture.json"
            outside = root.parent / "outside.json"

            self.assertEqual(
                "nested/fixture.json",
                COMMON.rel_path(inside, root),
            )
            self.assertEqual(
                outside.as_posix(),
                COMMON.rel_path(outside, root),
            )
            self.assertEqual(".", COMMON.rel_path(root, root))

    def test_selective_pattern_returns_only_files_in_stable_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "BeyondFMVPlayableAsset_p2.json").write_text("{}", encoding="utf-8")
            (root / "BeyondFMVPlayableAsset_p1.json").write_text("{}", encoding="utf-8")
            (root / "Other_p3.json").write_text("{}", encoding="utf-8")
            (root / "BeyondFMVPlayableAsset_dir.json").mkdir()

            matches = COMMON.fast_glob_files(
                root,
                "BeyondFMVPlayableAsset*.json",
            )

            self.assertEqual(
                [path.name for path in matches],
                [
                    "BeyondFMVPlayableAsset_p1.json",
                    "BeyondFMVPlayableAsset_p2.json",
                ],
            )

    def test_missing_directory_and_no_match_are_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(COMMON.fast_glob_files(root / "missing", "*.json"), [])
            self.assertEqual(COMMON.fast_glob_files(root, "none*.json"), [])

    def test_build_scoped_byte_cache_reads_immutable_input_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "fixture.bin"
            original_export_root = COMMON.EXPORT_ROOT
            try:
                COMMON.EXPORT_ROOT = root
                path.write_bytes(b"first")
                COMMON._read_bytes_cached_absolute.cache_clear()

                self.assertEqual(b"first", COMMON.read_bytes_cached(path))
                path.write_bytes(b"second")
                self.assertEqual(b"first", COMMON.read_bytes_cached(path))

                COMMON._read_bytes_cached_absolute.cache_clear()
                self.assertEqual(b"second", COMMON.read_bytes_cached(path))
            finally:
                COMMON.EXPORT_ROOT = original_export_root
                COMMON._read_bytes_cached_absolute.cache_clear()

    def test_write_text_if_changed_preserves_unchanged_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "nested" / "fixture.json"
            self.assertTrue(COMMON.write_text_if_changed(path, "{\"value\":1}\n"))
            self.assertEqual(
                b'{"value":1}' + os.linesep.encode("ascii"),
                path.read_bytes(),
            )
            first_stat = path.stat()
            time.sleep(0.01)

            self.assertFalse(COMMON.write_text_if_changed(path, "{\"value\":1}\n"))
            unchanged_stat = path.stat()
            self.assertEqual(first_stat.st_mtime_ns, unchanged_stat.st_mtime_ns)

            self.assertTrue(COMMON.write_text_if_changed(path, "{\"value\":2}"))
            self.assertEqual("{\"value\":2}", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
