import base64
import hashlib
import json
import struct
import tempfile
from types import SimpleNamespace
import unittest
import importlib.util
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("refresh_installed_ifix_patch_state.py")
SPEC = importlib.util.spec_from_file_location("refresh_installed_ifix_patch_state", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
discover_patch_layout = MODULE.discover_patch_layout
find_bridge_offset = MODULE.find_bridge_offset


def encode_string(value: str) -> bytes:
    payload = value.encode("utf-8")
    length = len(payload)
    out = bytearray()
    while length >= 0x80:
        out.append((length & 0x7F) | 0x80)
        length >>= 7
    out.append(length)
    out.extend(payload)
    return bytes(out)


def synthetic_patch() -> bytes:
    data = bytearray(b"\x00" * 0x88)
    data.extend(encode_string("IFix.ILFixInterfaceBridge, Gameplay.Beyond"))
    types = ["Beyond.Test.Actor, Gameplay.Beyond", "System.Int32"]
    data.extend(struct.pack("<i", len(types)))
    for value in types:
        data.extend(encode_string(value))
    data.extend(struct.pack("<i", 1))
    data.extend(b"\x00")
    data.extend(struct.pack("<i", 0))
    data.extend(encode_string("Tick"))
    data.extend(struct.pack("<i", 1))
    data.extend(struct.pack("<i", 1))
    data.extend(struct.pack("<i", 7))
    data.extend(struct.pack("<i", 0))
    return bytes(data)


class RefreshIfixPatchTests(unittest.TestCase):
    def test_discovers_bridge_and_unique_target_table(self) -> None:
        payload = synthetic_patch()
        self.assertEqual(find_bridge_offset(payload), 0x88)
        targets, layout = discover_patch_layout(payload)
        self.assertEqual(layout["target_count"], 1)
        self.assertEqual(layout["terminal_int32"], 0)
        self.assertEqual(targets[0]["type"], "Beyond.Test.Actor")
        self.assertEqual(targets[0]["parameters"], ["System.Int32"])
        self.assertEqual(targets[0]["implementation_index"], 7)

    def test_rejects_payload_without_a_self_terminating_target_table(self) -> None:
        payload = synthetic_patch()[:-4] + struct.pack("<i", 1)
        with self.assertRaises(ValueError):
            discover_patch_layout(payload)

    def test_animestudio_targeted_index_and_stream_are_joined_exactly(self) -> None:
        patch = synthetic_patch()
        actual_md5 = hashlib.md5(patch).hexdigest().upper()
        vfs_md5 = bytes.fromhex(actual_md5)[::-1].hex().upper()
        index = {
            "blocks": [{
                "name": "IFixPatchOut",
                "chunks": [{"absolutePath": "C:/fixture/chunk.chk"}],
            }],
            "files": [{
                "fileName": MODULE.PATCH_NAME,
                "fileDataMd5": vfs_md5,
                "length": len(patch),
            }],
        }

        with tempfile.TemporaryDirectory() as folder:
            index_path = Path(folder) / "index.json"

            def run(args: list[str]) -> SimpleNamespace:
                if args[0] == "vfs-index":
                    index_path.write_text(json.dumps(index), encoding="utf-8")
                    return SimpleNamespace(stdout="", stderr="", returncode=0)
                row = {
                    "fileName": MODULE.PATCH_NAME,
                    "dataBase64": base64.b64encode(patch).decode("ascii"),
                }
                return SimpleNamespace(
                    stdout=json.dumps(row) + "\nStreamed 1 files\n",
                    stderr="",
                    returncode=0,
                )

            with mock.patch.object(MODULE, "_run_animestudio", side_effect=run):
                _, _, _, observed = MODULE._extract_current_ifix(
                    Path("C:/fixture/Persistent"),
                    Path("C:/fixture/StreamingAssets"),
                    index_path,
                )
        self.assertEqual(observed, patch)

    def test_animestudio_stream_md5_mismatch_fails_closed(self) -> None:
        patch = synthetic_patch()
        index = {
            "blocks": [{
                "name": "IFixPatchOut",
                "chunks": [{"absolutePath": "C:/fixture/chunk.chk"}],
            }],
            "files": [{
                "fileName": MODULE.PATCH_NAME,
                "fileDataMd5": "00" * 16,
                "length": len(patch),
            }],
        }
        with tempfile.TemporaryDirectory() as folder:
            index_path = Path(folder) / "index.json"

            def run(args: list[str]) -> SimpleNamespace:
                if args[0] == "vfs-index":
                    index_path.write_text(json.dumps(index), encoding="utf-8")
                    return SimpleNamespace(stdout="", stderr="", returncode=0)
                row = {
                    "fileName": MODULE.PATCH_NAME,
                    "dataBase64": base64.b64encode(patch).decode("ascii"),
                }
                return SimpleNamespace(
                    stdout=json.dumps(row), stderr="", returncode=0
                )

            with mock.patch.object(MODULE, "_run_animestudio", side_effect=run):
                with self.assertRaisesRegex(ValueError, "MD5 mismatch"):
                    MODULE._extract_current_ifix(
                        Path("C:/fixture/Persistent"),
                        Path("C:/fixture/StreamingAssets"),
                        index_path,
                    )

    def test_loader_metadata_catalog_stale_build_fails_closed(self) -> None:
        payload = {
            "metadata": {
                "path": "C:/fixture/global-metadata.dat",
                "sha256": "b" * 64,
            }
        }
        with self.assertRaisesRegex(ValueError, "native-build provenance"):
            MODULE.validate_loader_artifact_provenance(
                "metadata_catalog",
                payload,
                Path("C:/fixture/GameAssembly.dll"),
                "a" * 64,
                Path("C:/fixture/global-metadata.dat"),
                "c" * 64,
            )

    def test_loader_native_map_stale_gameassembly_fails_closed(self) -> None:
        payload = {
            "metadata": {
                "metadataPath": "C:/fixture/global-metadata.dat",
                "metadataSha256": "c" * 64,
                "gameAssembly": "C:/fixture/GameAssembly.dll",
                "gameAssemblySha256": "b" * 64,
            }
        }
        with self.assertRaisesRegex(ValueError, "native-build provenance"):
            MODULE.validate_loader_artifact_provenance(
                "native_map",
                payload,
                Path("C:/fixture/GameAssembly.dll"),
                "a" * 64,
                Path("C:/fixture/global-metadata.dat"),
                "c" * 64,
            )


if __name__ == "__main__":
    unittest.main()
