from __future__ import annotations

import sys
import subprocess
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


from scripts.animestudio import generate_dummydll


ROOT = Path(__file__).resolve().parents[2]


def load_generator():
    return generate_dummydll


def managed_stub() -> bytes:
    data = bytearray(512)
    data[:2] = b"MZ"
    data[128:132] = b"BSJB"
    return bytes(data)


class GenerateDummyDllTests(unittest.TestCase):
    def test_pins_cpp2il_endfield_release(self) -> None:
        generator = load_generator()
        self.assertEqual(
            "https://github.com/Variante/Cpp2IL-Endfield.git",
            generator.CPP2IL_REPOSITORY,
        )
        self.assertEqual("endfield-2022.0.7-v3", generator.CPP2IL_TAG)
        self.assertRegex(generator.CPP2IL_COMMIT, r"^[0-9a-f]{40}$")

    def test_direct_script_help_does_not_require_game_configuration(self) -> None:
        generator = load_generator()
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, str(Path(generator.__file__).resolve()), "--help"],
                cwd=temp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn("--status-only", result.stdout)

    def test_prepare_cpp2il_advances_only_clean_expected_origin(self) -> None:
        generator = load_generator()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "Cpp2IL-Endfield"
            (source / ".git").mkdir(parents=True)
            completed = [
                subprocess.CompletedProcess([], 0, generator.CPP2IL_REPOSITORY + "\n"),
                subprocess.CompletedProcess([], 0, ""),
                subprocess.CompletedProcess([], 0, generator.CPP2IL_COMMIT + "\n"),
                subprocess.CompletedProcess([], 0, ""),
            ]
            with (
                mock.patch.object(
                    generator, "cpp2il_source_commit", return_value="0" * 40
                ),
                mock.patch.object(
                    generator, "cpp2il_tracked_changes", return_value=""
                ),
                mock.patch.object(
                    generator, "run_command", side_effect=completed
                ) as run,
            ):
                self.assertTrue(generator.prepare_cpp2il(source, dry_run=False))

            commands = [call.args[0] for call in run.call_args_list]
            self.assertIn(
                ["git", "fetch", "--depth", "1", "origin", "tag", generator.CPP2IL_TAG],
                commands,
            )
            self.assertIn(
                ["git", "checkout", "--detach", generator.CPP2IL_COMMIT],
                commands,
            )

    def test_resolve_game_paths_accepts_data_root(self) -> None:
        generator = load_generator()
        with tempfile.TemporaryDirectory() as temp:
            install = Path(temp) / "Endfield Game"
            data = install / "Endfield_Data"
            metadata = data / "il2cpp_data" / "Metadata" / "global-metadata.dat"
            metadata.parent.mkdir(parents=True)
            metadata.write_bytes(b"metadata")
            (install / "GameAssembly.dll").write_bytes(b"gameassembly")
            (install / "Endfield.exe").write_bytes(b"exe")

            actual_install, actual_binary, actual_metadata, exe_name = generator.resolve_game_paths(data)

            self.assertEqual(install.resolve(), actual_install)
            self.assertEqual((install / "GameAssembly.dll").resolve(), actual_binary)
            self.assertEqual(metadata.resolve(), actual_metadata)
            self.assertEqual("Endfield", exe_name)

    def test_generation_manifest_records_bounded_cpp2il_coverage_gaps(self) -> None:
        generator = load_generator()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gameassembly = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            dll = root / "Assembly-CSharp.dll"
            gameassembly.write_bytes(b"game")
            metadata.write_bytes(b"metadata")
            dll.write_bytes(managed_stub())
            output = "\n".join(
                [
                    "\x1b[33mSkipping malformed image Bad.dll: first type is unavailable.",
                    "Skipped 7 malformed types in Gameplay.Beyond.dll.",
                    "Skipping malformed field default for Gameplay.Beyond.dll:Type.Field: ArgumentNullOrEmptyException.",
                    "Skipping malformed generic constraint for MemoryPack.Beyond.dll:Type.T: NullReferenceException.",
                ]
            )

            with mock.patch.object(
                generator, "cpp2il_source_commit", return_value=generator.CPP2IL_COMMIT
            ):
                manifest = generator.generation_manifest(
                    gameassembly=gameassembly,
                    metadata=metadata,
                    code_registration=1,
                    metadata_registration=2,
                    registration_summary={},
                    source=generator.DEFAULT_CPP2IL_SOURCE,
                    dlls=[dll],
                    cpp2il_output=output,
                    schema_identity_validation={
                        "status": "passed",
                        "expectedTypeCount": 1,
                        "exactIdentityCount": 1,
                    },
                )

            cpp2il = manifest["cpp2il"]
            self.assertEqual(generator.CPP2IL_REPOSITORY, cpp2il["repository"])
            self.assertEqual(generator.CPP2IL_TAG, cpp2il["tag"])
            self.assertEqual(generator.CPP2IL_COMMIT, cpp2il["commit"])
            self.assertEqual(1, cpp2il["skippedMalformedImageCount"])
            self.assertEqual(
                [{"name": "Bad.dll", "reason": "first type is unavailable."}],
                cpp2il["skippedMalformedImageDiagnostics"],
            )
            self.assertEqual(7, cpp2il["skippedMalformedTypeCount"])
            self.assertEqual(1, cpp2il["skippedMalformedFieldDefaultCount"])
            self.assertEqual(1, cpp2il["skippedMalformedGenericConstraintCount"])
            self.assertEqual(generator.sha256_file(Path(generator.__file__)), manifest["generatorSha256"])

    def test_publication_regressions_block_required_skips_and_size_collapse(self) -> None:
        generator = load_generator()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "DummyDll"
            output.mkdir()
            previous_files = [
                {"name": name, "bytes": 1000, "sha256": "old"}
                for name in sorted(generator.REQUIRED_ASSEMBLIES)
            ]
            (output / "generation.json").write_text(
                json.dumps(
                    {
                        "assemblies": {
                            "bytes": 3000,
                            "files": previous_files,
                        }
                    }
                ),
                encoding="utf-8",
            )
            next_manifest = {
                "cpp2il": {
                    "skippedMalformedImages": ["Assembly-CSharp.dll"],
                    "skippedMalformedTypeCount": 95,
                    "expectedTypeCount": 100,
                },
                "assemblies": {
                    "bytes": 300,
                    "files": [dict(row, bytes=100) for row in previous_files],
                },
            }

            regressions = generator.publication_regressions(output, next_manifest)

            self.assertTrue(any("required images skipped" in row for row in regressions))
            self.assertTrue(any("malformed type coverage collapsed" in row for row in regressions))
            self.assertTrue(any("total assembly bytes collapsed" in row for row in regressions))

    def test_current_output_status_verifies_files_and_rejects_degraded_coverage(self) -> None:
        generator = load_generator()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "DummyDll"
            output.mkdir()
            gameassembly = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            dll = output / "Assembly-CSharp.dll"
            gameassembly.write_bytes(b"game")
            metadata.write_bytes(b"metadata")
            dll.write_bytes(managed_stub())
            manifest = {
                "schema": 1,
                "generatorSha256": generator.sha256_file(Path(generator.__file__)),
                "game": {
                    "gameAssemblySha256": generator.sha256_file(gameassembly),
                    "metadataSha256": generator.sha256_file(metadata),
                },
                "cpp2il": {
                    "repository": generator.CPP2IL_REPOSITORY,
                    "tag": generator.CPP2IL_TAG,
                    "commit": generator.CPP2IL_COMMIT,
                    "skippedMalformedImageCount": 0,
                    "skippedMalformedImages": [],
                    "skippedMalformedTypeCount": 1,
                    "expectedTypeCount": 100,
                },
                "assemblies": {
                    "count": 1,
                    "bytes": dll.stat().st_size,
                    "files": [{
                        "name": dll.name,
                        "bytes": dll.stat().st_size,
                        "sha256": generator.sha256_file(dll),
                    }],
                },
                "schemaIdentityValidation": {
                    "status": "passed",
                    "expectedTypeCount": 1,
                    "exactIdentityCount": 1,
                },
            }
            (output / "generation.json").write_text(json.dumps(manifest), encoding="utf-8")

            self.assertEqual(
                "current",
                generator.current_output_status(output, gameassembly, metadata)[0],
            )
            manifest["cpp2il"]["commit"] = "0" * 40
            (output / "generation.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(
                "stale",
                generator.current_output_status(output, gameassembly, metadata)[0],
            )
            manifest["cpp2il"]["commit"] = generator.CPP2IL_COMMIT
            manifest["cpp2il"]["skippedMalformedTypeCount"] = 95
            (output / "generation.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(
                "degraded",
                generator.current_output_status(output, gameassembly, metadata)[0],
            )
            dll.write_bytes(managed_stub() + b"corrupt")
            self.assertEqual(
                "invalid",
                generator.current_output_status(output, gameassembly, metadata)[0],
            )

    def test_schema_identity_gate_requires_exact_assembly_token_and_name(self) -> None:
        generator = load_generator()
        expected = {
            ("gameplay.beyond.dll", 0x02000002): "Beyond.Outer+Inner",
            ("common.beyond.dll", 0x02000003): "Beyond.Value",
        }
        payload = {
            "schema": "animestudio.dummydll-index.v1",
            "complete": True,
            "invalidTypeCount": 0,
            "errors": [],
            "assemblies": [
                {
                    "module": "Gameplay.Beyond.dll",
                    "types": [
                        {
                            "token": "0x02000002",
                            "fullName": "Beyond.Outer+Inner",
                        }
                    ],
                },
                {
                    "module": "Common.Beyond.dll",
                    "types": [
                        {"token": "0x02000003", "fullName": "Beyond.Value"}
                    ],
                },
            ],
        }

        summary, failures = generator.compare_schema_identities(expected, payload)
        self.assertEqual([], failures)
        self.assertEqual("passed", summary["status"])
        self.assertEqual(2, summary["exactIdentityCount"])

        payload["assemblies"][0]["types"][0]["fullName"] = (
            "Beyond.Outer+Beyond.Inner"
        )
        summary, failures = generator.compare_schema_identities(expected, payload)
        self.assertEqual("failed", summary["status"])
        self.assertEqual(1, summary["mismatchedFullNameCount"])
        self.assertTrue(any("FullName values mismatch" in row for row in failures))

    def test_validate_generated_requires_exact_metadata_dll_set(self) -> None:
        generator = load_generator()
        names = set(generator.REQUIRED_ASSEMBLIES) | {"Extra.Schema.dll", "__Generated"}
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            for name in names:
                if name.endswith(".dll"):
                    (output / name).write_bytes(managed_stub())

            dlls = generator.validate_generated(output, names)
            self.assertEqual(len(names) - 1, len(dlls))

            (output / "Extra.Schema.dll").unlink()
            with self.assertRaises(SystemExit):
                generator.validate_generated(output, names)

    def test_publish_keeps_previous_set_when_replacing(self) -> None:
        generator = load_generator()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "DummyDll"
            output.mkdir()
            (output / "old.dll").write_bytes(managed_stub())
            raw = root / "raw"
            raw.mkdir()
            new_dll = raw / "new.dll"
            new_dll.write_bytes(managed_stub())

            backup = generator.publish(
                output,
                [new_dll],
                {"schema": 1},
                replace=True,
                stamp="fixture",
            )

            self.assertEqual(root / "DummyDll.previous-fixture", backup)
            self.assertTrue((output / "new.dll").is_file())
            self.assertTrue((output / "generation.json").is_file())
            self.assertTrue((backup / "old.dll").is_file())


if __name__ == "__main__":
    unittest.main()
