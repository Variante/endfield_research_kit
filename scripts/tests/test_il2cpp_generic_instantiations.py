from __future__ import annotations

import importlib.util
import struct
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"

IMAGE_BASE = 0x180000000


def load_helper():
    spec = importlib.util.spec_from_file_location("endfield_il2cpp_generic_index", HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeImage:
    """Flat synthetic image where RVA equals file offset.

    Only the PeImage surface used by the registration/index helpers is provided.
    """

    def __init__(self, size: int = 0x4000) -> None:
        self.buf = bytearray(size)
        self.image_base = IMAGE_BASE
        self.sections = [
            {
                "name": ".text",
                "virtualAddress": 0,
                "virtualSize": size,
                "rawPointer": 0,
                "rawSize": size,
            }
        ]

    def write(self, va: int, data: bytes) -> None:
        offset = va - self.image_base
        self.buf[offset: offset + len(data)] = data

    def write_u32(self, va: int, value: int) -> None:
        self.write(va, struct.pack("<I", value))

    def write_u64(self, va: int, value: int) -> None:
        self.write(va, struct.pack("<Q", value))

    def file_offset_for_va(self, va: int):
        rva = va - self.image_base
        if 0 <= rva < len(self.buf):
            return rva, ".text", rva
        return None, "", rva

    def u32_at_va(self, va: int) -> int:
        offset, _, _ = self.file_offset_for_va(va)
        if offset is None:
            raise ValueError(f"VA outside image: 0x{va:x}")
        return struct.unpack_from("<I", self.buf, offset)[0]

    def u64_at_va(self, va: int) -> int:
        offset, _, _ = self.file_offset_for_va(va)
        if offset is None:
            raise ValueError(f"VA outside image: 0x{va:x}")
        return struct.unpack_from("<Q", self.buf, offset)[0]


def fake_metadata(names: dict[int, tuple[str, str]]):
    """Build a metadata stub whose method_signature() output is predictable."""
    methods = []
    for index in range(max(names) + 1 if names else 0):
        type_name, method_name = names.get(index, ("T", "M"))
        methods.append(
            types.SimpleNamespace(
                declaring_type=index, name_index=index, token=0x06000000 + index,
                _type_name=type_name, _method_name=method_name,
            )
        )
    md = types.SimpleNamespace(methods=methods, types=methods)
    md.string = lambda index: methods[index]._method_name
    md.type_full_name = lambda type_def: type_def._type_name
    return md


class MetadataRegistrationTests(unittest.TestCase):
    def test_summary_reads_count_pointer_pairs(self) -> None:
        helper = load_helper()
        image = FakeImage()
        base = IMAGE_BASE + 0x100
        for index, name in enumerate(helper.METADATA_REGISTRATION_FIELDS):
            image.write_u32(base + index * 0x10, index + 1)
            image.write_u64(base + index * 0x10 + 8, IMAGE_BASE + 0x800 + index)
        summary = helper.metadata_registration_summary(image, base)

        self.assertEqual(f"0x{base:x}", summary["va"])
        self.assertEqual(1, summary["genericClassesCount"])
        self.assertEqual(5, summary["methodSpecsCount"])
        self.assertEqual(hex(IMAGE_BASE + 0x804), summary["methodSpecs"])

    def test_plausible_rejects_pointer_outside_image(self) -> None:
        helper = load_helper()
        image = FakeImage()
        base = IMAGE_BASE + 0x100
        for index in range(len(helper.METADATA_REGISTRATION_FIELDS)):
            image.write_u64(base + index * 0x10 + 8, IMAGE_BASE + 0x800)
        self.assertTrue(helper.metadata_registration_is_plausible(image, base))

        image.write_u64(base + 8, 0xDEADBEEFDEADBEEF)
        self.assertFalse(helper.metadata_registration_is_plausible(image, base))

    def test_zero_pointers_do_not_reject_a_candidate(self) -> None:
        # metadataUsages is legitimately null on this build.
        helper = load_helper()
        image = FakeImage()
        base = IMAGE_BASE + 0x100
        for index in range(len(helper.METADATA_REGISTRATION_FIELDS)):
            image.write_u64(base + index * 0x10 + 8, IMAGE_BASE + 0x800)
        image.write_u64(base + 7 * 0x10 + 8, 0)
        self.assertTrue(helper.metadata_registration_is_plausible(image, base))

    def test_find_metadata_registration_uses_neighbouring_lea(self) -> None:
        helper = load_helper()
        image = FakeImage()
        code_reg = IMAGE_BASE + 0x1000
        meta_reg = IMAGE_BASE + 0x1100
        for index in range(len(helper.METADATA_REGISTRATION_FIELDS)):
            image.write_u64(meta_reg + index * 0x10 + 8, IMAGE_BASE + 0x800)

        def lea(site: int, target: int, reg: int) -> None:
            disp = target - (site + 7)
            image.write(site, bytes([0x48, 0x8D, 0x05 | (reg << 3)]) + struct.pack("<i", disp))

        lea(IMAGE_BASE + 0x200, code_reg, 1)   # lea rcx, CodeRegistration
        lea(IMAGE_BASE + 0x210, meta_reg, 2)   # lea rdx, MetadataRegistration

        self.assertEqual(meta_reg, helper.find_metadata_registration(image, code_reg))

    def test_find_metadata_registration_returns_none_without_anchor(self) -> None:
        helper = load_helper()
        image = FakeImage()
        self.assertIsNone(helper.find_metadata_registration(image, IMAGE_BASE + 0x1000))


class GenericMethodIndexTests(unittest.TestCase):
    def _build(self, helper, image, *, slot: int, spec_index: int, method_definition: int,
               entry_va: int):
        code_reg = IMAGE_BASE + 0x1000
        meta_reg = IMAGE_BASE + 0x1100
        pointer_table = IMAGE_BASE + 0x1200
        generic_table = IMAGE_BASE + 0x1400
        spec_table = IMAGE_BASE + 0x1600

        # CodeRegistration.genericMethodPointers count/pointer at +0x10/+0x18.
        image.write_u32(code_reg + 0x10, slot + 1)
        image.write_u64(code_reg + 0x18, pointer_table)
        image.write_u64(pointer_table + slot * 8, entry_va)

        # MetadataRegistration genericMethodTable (index 2) and methodSpecs (index 4).
        image.write_u32(meta_reg + 2 * 0x10, 1)
        image.write_u64(meta_reg + 2 * 0x10 + 8, generic_table)
        image.write_u32(meta_reg + 4 * 0x10, spec_index + 1)
        image.write_u64(meta_reg + 4 * 0x10 + 8, spec_table)

        image.write(generic_table, struct.pack("<iiii", spec_index, slot, 0, 0))
        image.write(spec_table + spec_index * helper.METHOD_SPEC_STRIDE,
                    struct.pack("<iii", method_definition, 7, -1))
        return code_reg, meta_reg

    def test_index_names_open_generic_definition(self) -> None:
        helper = load_helper()
        image = FakeImage()
        entry_va = IMAGE_BASE + 0x2000
        code_reg, meta_reg = self._build(
            helper, image, slot=3, spec_index=2, method_definition=1, entry_va=entry_va
        )
        md = fake_metadata({0: ("Beyond.Other", "Nope"), 1: ("Beyond.KeyGenerator`2", "GetKey")})

        index = helper.build_generic_method_index(image, md, code_reg, meta_reg)

        self.assertIn(entry_va, index)
        row = index[entry_va][0]
        self.assertEqual("Beyond.KeyGenerator`2", row["type"])
        self.assertEqual("GetKey", row["method"])
        self.assertTrue(row["genericInstantiation"])
        self.assertEqual(3, row["genericMethodPointerSlot"])
        self.assertEqual(2, row["methodSpecIndex"])

    def test_null_entry_pointer_is_skipped(self) -> None:
        helper = load_helper()
        image = FakeImage()
        code_reg, meta_reg = self._build(
            helper, image, slot=3, spec_index=2, method_definition=1, entry_va=0
        )
        md = fake_metadata({1: ("Beyond.KeyGenerator`2", "GetKey")})

        self.assertEqual({}, helper.build_generic_method_index(image, md, code_reg, meta_reg))

    def test_out_of_range_method_definition_is_skipped(self) -> None:
        helper = load_helper()
        image = FakeImage()
        entry_va = IMAGE_BASE + 0x2000
        code_reg, meta_reg = self._build(
            helper, image, slot=3, spec_index=2, method_definition=99, entry_va=entry_va
        )
        md = fake_metadata({1: ("Beyond.KeyGenerator`2", "GetKey")})

        self.assertEqual({}, helper.build_generic_method_index(image, md, code_reg, meta_reg))


if __name__ == "__main__":
    unittest.main()
