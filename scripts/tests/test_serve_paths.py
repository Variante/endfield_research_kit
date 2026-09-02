from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import serve


class ServePathTests(unittest.TestCase):
    def test_export_roots_use_optional_paths_bat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "endfield_paths.bat").write_text(
                '@echo off\n'
                'set "ENDFIELD_PREVIOUS_EXPORT_ROOT=old_export"\n'
                'set "ENDFIELD_EXPORT_ROOT=current_export"\n',
                encoding="utf-8",
            )
            with (
                mock.patch.object(serve, "PROJECT_ROOT", root),
                mock.patch.object(serve, "WEBUI_ROOT", root / "webui"),
                mock.patch.dict(
                    os.environ,
                    {
                        "WEBUI_PREVIOUS_EXPORT_ROOT": "",
                        "ENDFIELD_PREVIOUS_EXPORT_ROOT": "",
                        "ENDFIELD_EXPORT_ROOT": "",
                    },
                ),
            ):
                self.assertEqual(serve.resolve_export_full_root(), root / "current_export")
                self.assertEqual(serve.resolve_previous_export_root(), root / "old_export")

    def test_environment_overrides_paths_bat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "endfield_paths.bat").write_text(
                'set "ENDFIELD_PREVIOUS_EXPORT_ROOT=batch_old"\n'
                'set "ENDFIELD_EXPORT_ROOT=batch_current"\n',
                encoding="utf-8",
            )
            with (
                mock.patch.object(serve, "PROJECT_ROOT", root),
                mock.patch.object(serve, "WEBUI_ROOT", root / "webui"),
                mock.patch.dict(
                    os.environ,
                    {
                        "WEBUI_PREVIOUS_EXPORT_ROOT": "webui_old",
                        "ENDFIELD_PREVIOUS_EXPORT_ROOT": "env_old",
                        "ENDFIELD_EXPORT_ROOT": "env_current",
                    },
                ),
            ):
                self.assertEqual(serve.resolve_export_full_root(), root / "env_current")
                self.assertEqual(serve.resolve_previous_export_root(), root / "webui_old")

    def test_previous_root_falls_back_to_updates_feed_without_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            feed = root / "webui" / "data" / "updates" / "latest.json"
            feed.parent.mkdir(parents=True)
            feed.write_text(
                json.dumps({"previousSourceRoot": "feed_old"}), encoding="utf-8"
            )
            with (
                mock.patch.object(serve, "PROJECT_ROOT", root),
                mock.patch.object(serve, "WEBUI_ROOT", root / "webui"),
                mock.patch.dict(
                    os.environ,
                    {
                        "WEBUI_PREVIOUS_EXPORT_ROOT": "",
                        "ENDFIELD_PREVIOUS_EXPORT_ROOT": "",
                    },
                ),
            ):
                self.assertEqual(serve.resolve_previous_export_root(), root / "feed_old")


if __name__ == "__main__":
    unittest.main()
