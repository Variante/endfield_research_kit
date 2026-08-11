from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "animestudio" / "generate_dummydll.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("endfield_dummydll_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load generator: {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def managed_stub() -> bytes:
    data = bytearray(512)
    data[:2] = b"MZ"
    data[128:132] = b"BSJB"
    return bytes(data)


class GenerateDummyDllTests(unittest.TestCase):
    def test_patch_guards_malformed_value_type_field_defaults(self) -> None:
        generator = load_generator()
        patch_text = generator.CPP2IL_PATCH.read_text(encoding="utf-8")

        self.assertIn("ValidateConstantTypeReference(fieldTypeRef)", patch_text)
        self.assertIn("Skipping malformed field default", patch_text)
        self.assertIn("fieldDefinition.Attributes &= ~FieldAttributes.HasDefault", patch_text)
        self.assertIn("Skipping malformed generic constraint", patch_text)
        self.assertIn("module.ImportReference(constraintType)", patch_text)

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

            manifest = generator.generation_manifest(
                gameassembly=gameassembly,
                metadata=metadata,
                code_registration=1,
                metadata_registration=2,
                registration_summary={},
                source=generator.DEFAULT_CPP2IL_SOURCE,
                dlls=[dll],
                cpp2il_output=output,
            )

            cpp2il = manifest["cpp2il"]
            self.assertEqual(1, cpp2il["skippedMalformedImageCount"])
            self.assertEqual(7, cpp2il["skippedMalformedTypeCount"])
            self.assertEqual(1, cpp2il["skippedMalformedFieldDefaultCount"])
            self.assertEqual(1, cpp2il["skippedMalformedGenericConstraintCount"])

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
