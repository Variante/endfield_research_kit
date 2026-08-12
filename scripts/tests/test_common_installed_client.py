"""Resolving the installed client, and gating a step on its build."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("common", HERE.parent / "common.py")
COMMON = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# Register before executing: dataclasses resolves annotations through
# sys.modules, so a path-loaded module must be findable under its own name.
sys.modules.setdefault(SPEC.name, COMMON)
SPEC.loader.exec_module(COMMON)


class InstalledClientTestCase(unittest.TestCase):
    """Isolates the resolver from whatever client this machine has installed."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.summary = self.root / "export_full_summary.json"
        self.builtin_default = self.root / "builtin" / "Endfield_Data"
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop("ENDFIELD_GAME_ROOT", None)
        os.environ.pop(COMMON.REQUIRE_NATIVE_EVIDENCE_ENV, None)
        # ROOT drives the endfield_paths.bat lookup, which no test has unless
        # it calls configure_paths_bat().
        self.enterContext(mock.patch.object(COMMON, "ROOT", self.root))
        self.enterContext(
            mock.patch.object(
                COMMON, "DEFAULT_INSTALLED_GAME_DATA_ROOT", self.builtin_default
            )
        )

    def install(self, name: str, *, gameassembly: bytes = b"pinned build") -> Path:
        """Create a client layout under ``name`` and return its Endfield_Data."""
        data_root = self.root / name / "Endfield_Data"
        metadata = data_root / COMMON.GLOBAL_METADATA_REL
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_bytes(b"metadata")
        (data_root.parent / "GameAssembly.dll").write_bytes(gameassembly)
        return data_root

    def configure_summary(self, data_root: Path) -> None:
        self.summary.write_text(
            json.dumps({"game_root": str(data_root)}), encoding="utf-8"
        )

    def configure_paths_bat(self, data_root: Path) -> None:
        (self.root / "endfield_paths.bat").write_text(
            f'set "ENDFIELD_GAME_ROOT={data_root}"\n', encoding="utf-8"
        )


class ResolutionTests(InstalledClientTestCase):
    def test_deliberate_configuration_outranks_the_recorded_export(self) -> None:
        env = self.install("env")
        configured = self.install("configured")
        exported = self.install("exported")
        os.environ["ENDFIELD_GAME_ROOT"] = str(env)
        self.configure_paths_bat(configured)
        self.configure_summary(exported)

        self.assertEqual(
            [env, configured, exported, self.builtin_default],
            COMMON.installed_game_data_root_candidates(self.summary),
        )

    def test_the_first_candidate_that_exists_wins(self) -> None:
        exported = self.install("exported")
        os.environ["ENDFIELD_GAME_ROOT"] = str(self.root / "moved" / "Endfield_Data")
        self.configure_summary(exported)

        self.assertEqual(
            exported, COMMON.resolve_installed_game_data_root(self.summary)
        )

    def test_native_input_names_come_from_the_resolved_root(self) -> None:
        installed = self.install("installed")
        os.environ["ENDFIELD_GAME_ROOT"] = str(installed)

        self.assertEqual(
            (
                installed.parent / "GameAssembly.dll",
                installed / COMMON.GLOBAL_METADATA_REL,
            ),
            COMMON.resolve_installed_native_inputs(self.summary),
        )

    def test_no_install_anywhere_reports_the_top_candidate_to_fix(self) -> None:
        missing = self.root / "moved" / "Endfield_Data"
        os.environ["ENDFIELD_GAME_ROOT"] = str(missing)

        gameassembly, metadata = COMMON.resolve_installed_native_inputs(self.summary)
        self.assertEqual(missing.parent / "GameAssembly.dll", gameassembly)
        self.assertEqual(missing / COMMON.GLOBAL_METADATA_REL, metadata)

    def test_the_same_root_is_listed_once(self) -> None:
        shared = self.install("shared")
        os.environ["ENDFIELD_GAME_ROOT"] = f"{shared}\\"
        self.configure_summary(shared)

        candidates = COMMON.installed_game_data_root_candidates(self.summary)
        self.assertEqual([shared, self.builtin_default], candidates)


class NativeEvidenceGateTests(InstalledClientTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.installed = self.install("installed")
        self.gameassembly = self.installed.parent / "GameAssembly.dll"
        self.metadata = self.installed / COMMON.GLOBAL_METADATA_REL
        self.gameassembly_sha256 = hashlib.sha256(b"pinned build").hexdigest()
        self.metadata_sha256 = hashlib.sha256(b"metadata").hexdigest()
        self.absent = self.root / "absent.bin"
        os.environ["ENDFIELD_GAME_ROOT"] = str(self.installed)

    def check(self, **kwargs) -> COMMON.InstalledNativeInputs:
        return COMMON.check_installed_native_inputs(
            export_summary_path=self.summary, **kwargs
        )

    def test_the_pinned_build_validates_and_reports_its_digests(self) -> None:
        result = self.check(
            expected_gameassembly_sha256=self.gameassembly_sha256.upper(),
            expected_metadata_sha256=self.metadata_sha256,
        )
        self.assertTrue(result.validated)
        self.assertEqual(self.gameassembly, result.gameassembly)
        self.assertEqual(self.gameassembly_sha256, result.gameassembly_sha256)
        self.assertEqual(self.metadata_sha256, result.metadata_sha256)
        self.assertEqual("", result.detail)

    def test_an_absent_file_is_missing_and_names_the_path_to_fix(self) -> None:
        result = self.check(gameassembly=self.absent)
        self.assertEqual(COMMON.NATIVE_EVIDENCE_MISSING, result.status)
        self.assertFalse(result.validated)
        self.assertEqual("", result.gameassembly_sha256)
        self.assertIn(str(self.absent), result.detail)
        self.assertIn("ENDFIELD_GAME_ROOT", result.detail)

    def test_another_build_is_mismatched_and_names_both_builds(self) -> None:
        result = self.check(expected_gameassembly_sha256="0" * 64)
        self.assertEqual(COMMON.NATIVE_EVIDENCE_MISMATCHED, result.status)
        self.assertFalse(result.validated)
        self.assertIn(self.gameassembly_sha256[:12], result.detail)
        self.assertIn("000000000000", result.detail)
        self.assertIs(
            result, COMMON.NativeEvidenceUnavailable(result).result
        )

    def test_metadata_is_read_only_when_the_step_needs_it(self) -> None:
        binary_only = self.check(metadata=self.absent, require_metadata=False)
        self.assertTrue(binary_only.validated)
        self.assertEqual("", binary_only.metadata_sha256)

        # Pinning the metadata hash implies reading it, or an unread file would
        # look like a drifted one.
        pinned = self.check(
            metadata=self.absent,
            expected_metadata_sha256=self.metadata_sha256,
            require_metadata=False,
        )
        self.assertEqual(COMMON.NATIVE_EVIDENCE_MISSING, pinned.status)

    def test_the_message_says_skipped_unless_the_step_is_required(self) -> None:
        missing = self.check(gameassembly=self.absent)
        self.assertTrue(
            COMMON.native_evidence_skip_message("probe", missing).startswith(
                "[probe] skipped: "
            )
        )
        self.assertTrue(
            COMMON.native_evidence_skip_message(
                "probe", missing, required=True
            ).startswith("[probe] failed: ")
        )
        self.assertIn(
            "different build",
            COMMON.native_evidence_skip_message(
                "probe", self.check(expected_gameassembly_sha256="0" * 64)
            ),
        )

    def test_only_a_truthy_environment_value_demands_native_evidence(self) -> None:
        for value, required in (
            (None, False),
            ("", False),
            ("0", False),
            ("false", False),
            ("off", False),
            ("1", True),
            ("yes", True),
        ):
            with self.subTest(value=value):
                if value is None:
                    os.environ.pop(COMMON.REQUIRE_NATIVE_EVIDENCE_ENV, None)
                else:
                    os.environ[COMMON.REQUIRE_NATIVE_EVIDENCE_ENV] = value
                self.assertEqual(required, COMMON.native_evidence_required())


if __name__ == "__main__":
    unittest.main()
