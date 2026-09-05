import struct
import io
import json
from contextlib import redirect_stderr
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts.game_data.il2cpp_context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range
from scripts.game_data.il2cpp_context_audit import main, native_gate, sweep
from scripts.game_data.memorypack.skill_corpus import CensusGateError
from scripts.game_data.il2cpp_context import unresolved_usage_index, rip_qword_load_target


class RipQwordLoadTests(unittest.TestCase):
    def decode(self, raw, address=0x100):
        return rip_qword_load_target(raw,address,source='fixture.dll')

    def test_registers_and_signed_displacement(self):
        for rex in (0x48,0x4C):
            for register in range(8):
                for displacement in (-0x100,0,0x1234):
                    raw=bytes((rex,0x8B,5|(register<<3)))+struct.pack('<i',displacement)
                    self.assertEqual(self.decode(raw),0x107+displacement)

    def test_truncated_trailing_and_wrong_instruction(self):
        for raw in (b'',bytes(6),bytes(8),bytes.fromhex('488D0500000000'),
                    bytes.fromhex('488B4500000000'),bytes.fromhex('498B0500000000')):
            with self.subTest(raw=raw),self.assertRaises(ContextError):
                self.decode(raw)

    def test_address_and_target_boundaries(self):
        raw=bytes.fromhex('488B0500000000')
        for address in (-1,True,(1<<64)-7):
            with self.subTest(address=address),self.assertRaises(ContextError):
                self.decode(raw,address)
        for address,displacement in ((0,-8),((1<<64)-8,1)):
            with self.subTest(address=address),self.assertRaises(ContextError) as caught:
                self.decode(raw[:3]+struct.pack('<i',displacement),address)
            self.assertEqual(caught.exception.diagnostics['expected'],'bounded eight-byte target address')


class UnresolvedUsageTests(unittest.TestCase):
    def decode(self, raw, count=4, tag=2):
        return unresolved_usage_index(raw,count,tag=tag,source='fixture.dll',offset=0x30)

    def test_each_supported_tag_exact_index(self):
        for tag in (1,2,3,6):
            with self.subTest(tag=tag):
                self.assertEqual(self.decode(struct.pack('<Q',(tag<<29)|7),tag=tag),3)

    def test_zero_and_maximum_legal_index(self):
        for tag in (1,2,3,6):
            with self.subTest(tag=tag):
                self.assertEqual(self.decode(struct.pack('<Q',(tag<<29)|1),count=1,tag=tag),0)
                self.assertEqual(self.decode(struct.pack('<Q',(tag<<29)|(999_999<<1)|1),
                                             count=1_000_000,tag=tag),999_999)
        with self.assertRaises(ContextError) as caught:
            self.decode(struct.pack('<Q',0x40000001),count=0)
        self.assertEqual(caught.exception.diagnostics,{
            'source':'fixture.dll','offset':0x30,'expected':'usage target index in [0,0)','actual':0})

    def test_truncated_and_trailing(self):
        for size in (0,7,9):
            with self.subTest(size=size), self.assertRaises(ContextError):
                self.decode(bytes(size))

    def test_wrong_tag_live_pointer_and_index_bound(self):
        for word in (0x60000001,0x40000000,0x180000001,0x40000009):
            with self.subTest(word=word), self.assertRaises(ContextError) as caught:
                self.decode(struct.pack('<Q',word))
            self.assertEqual(caught.exception.diagnostics['offset'],0x30)

    def test_count_and_tag_fail_closed(self):
        for count in (-1,True,1_000_001):
            with self.subTest(count=count), self.assertRaises(ContextError):
                self.decode(struct.pack('<Q',0x40000001),count=count)
        for tag in (0,4,5,7,True):
            with self.subTest(tag=tag), self.assertRaises(ContextError):
                self.decode(struct.pack('<Q',0x40000001),tag=tag)


class GenericInstantiationTests(unittest.TestCase):
    def setUp(self):
        self.blocks = {0x100: struct.pack('<QQ', 0x200, 0x220),
                       0x200: struct.pack('<IIQ', 2, 0xDEADBEEF, 0x300),
                       0x220: struct.pack('<IIQ', 0, 0, 0),
                       0x300: struct.pack('<QQ', 0x400, 0x420),
                       0x400: bytes(range(16)), 0x420: bytes(range(16, 32))}
        self.reads = []

    def read(self, va, size):
        self.reads.append((va, size))
        if va not in self.blocks:
            raise ValueError('unbacked fixture address')
        return self.blocks[va][:size]

    def table(self, **kw):
        return GenericInstantiationTable(self.read, 0x100, 2, source='fixture.dll', **kw)

    def test_normal_preserves_order_padding_and_empty(self):
        table = self.table()
        row = table.resolve(0)
        self.assertEqual(row.record_va, 0x200)
        self.assertEqual(row.padding_hex, 'EFBEADDE')
        self.assertEqual([a.type_pointer_va for a in row.arguments], [0x400, 0x420])
        self.assertEqual(table.resolve(1).arguments, ())
        self.assertEqual(table.resolve(-1).record_va, None)

    def test_inline_decoy_is_not_a_record(self):
        # At index 1, the wrong index*16 reader sees a plausible decoy.
        self.blocks[0x110] = struct.pack('<IIQ', 1, 0, 0x300)
        self.assertEqual(struct.unpack('<IIQ', self.read(0x110, 16))[0], 1)
        self.assertEqual(self.table().resolve(1).arguments, ())
        self.assertNotIn((0x110, 16), self.reads[1:])

    def test_pointer_join_unique_and_ambiguous(self):
        self.assertEqual(self.table().resolve_pointer(0x220).index, 1)
        self.blocks[0x100] = struct.pack('<QQ', 0x200, 0x200)
        with self.assertRaises(ContextError) as caught:
            self.table().resolve_pointer(0x200)
        self.assertEqual(caught.exception.diagnostics['actual']['candidateIndices'], [0, 1])

    def test_pointer_join_missing_or_null(self):
        for pointer in (0, -1, True, 0x999):
            with self.subTest(pointer=pointer), self.assertRaises(ContextError):
                self.table().resolve_pointer(pointer)

    def test_every_truncated_range_fails(self):
        for address in (0x100, 0x200, 0x300, 0x400):
            with self.subTest(address=address):
                original = self.blocks[address]
                self.blocks[address] = original[:-1]
                with self.assertRaises(ContextError) as caught:
                    self.table().resolve(0)
                self.assertEqual(caught.exception.diagnostics['offset'], address)
                self.assertEqual(caught.exception.diagnostics['source'], 'fixture.dll')
                self.blocks[address] = original

    def test_count_checked_before_vector_read(self):
        self.blocks[0x200] = struct.pack('<IIQ', 65, 0, 0x300)
        with self.assertRaises(ContextError):
            self.table().resolve(0)
        self.assertNotIn((0x300, 520), self.reads)

    def test_invalid_indices(self):
        for index in (-2, 2, True, 0.0):
            with self.subTest(index=index), self.assertRaises(ContextError):
                self.table().resolve(index)

    def test_null_record_vector_and_type(self):
        for address, replacement in ((0x100, bytes(16)),
                                     (0x200, struct.pack('<IIQ', 1, 0, 0)),
                                     (0x300, bytes(16))):
            original = self.blocks[address]
            with self.subTest(address=address):
                self.blocks[address] = replacement
                with self.assertRaises(ContextError):
                    self.table().resolve(0)
            self.blocks[address] = original

    def test_invalid_table_inputs(self):
        for va, count in ((None, 2), (-1, 2), (0, 2), ((1 << 64)-4, 2),
                          (0x100, -1), (0x100, 1_000_001), (0x100, True)):
            with self.subTest(va=va, count=count), self.assertRaises(ContextError):
                GenericInstantiationTable(self.read, va, count, source='fixture')

    def test_external_bytes_not_implicitly_consumed(self):
        # These are referenced records in a PE, not a whole-file grammar.
        self.blocks[0x200] += b'trailing unrelated PE bytes'
        self.assertEqual(len(self.table().resolve(0).arguments), 2)
        self.assertIn((0x200, 16), self.reads)

    def test_sweep_keeps_independent_failures(self):
        self.blocks[0x200] = b''
        summary, rows, errors = sweep(self.table())
        self.assertEqual(summary, {'success': 1, 'failed': 1, 'unsupported': 0})
        self.assertEqual(rows[0]['index'], 1)
        self.assertEqual(errors[0]['index'], 0)

    def test_native_missing_and_mismatch_stop(self):
        for status in ('missing', 'mismatched'):
            with self.subTest(status=status), patch('scripts.game_data.il2cpp_context_audit.check_installed_native_inputs',
                    return_value=SimpleNamespace(status=status, detail='fixture')):
                with self.assertRaises(ContextError):
                    native_gate()

    def test_corpus_drift_diagnostic_stays_structured(self):
        error = CensusGateError('fingerprint-sha256-mismatch', source='tool.dll', expected='old', actual='new')
        stderr = io.StringIO()
        with patch('scripts.game_data.il2cpp_context_audit.audit', side_effect=error), redirect_stderr(stderr):
            self.assertEqual(main(), 1)
        self.assertEqual(json.loads(stderr.getvalue())['diagnostic'], error.diagnostic)


class ParameterOwnerTests(unittest.TestCase):
    def setUp(self):
        self.buf = bytearray(0x300)
        struct.pack_into('<II', self.buf, 8+12*8, 0x200, 16)
        struct.pack_into('<II', self.buf, 8+14*8, 0x220, 16)
        struct.pack_into('<iihhHH', self.buf, 0x200, 0, 0, 0, 0, 0, 0)
        struct.pack_into('<iiii', self.buf, 0x220, 0, 1, 1, 0)

    def resolve(self, index=0, methods=None):
        return method_parameter_owner(bytes(self.buf), index, [0] if methods is None else methods, source='metadata.dat')

    def test_normal(self):
        self.assertEqual(self.resolve()['methodIndex'], 0)

    def test_header_and_section_truncation(self):
        for end in (0, 120, 0x22F):
            with self.subTest(end=end), self.assertRaises(ContextError):
                method_parameter_owner(bytes(self.buf[:end]), 0, [0], source='fixture')

    def test_malformed_section(self):
        for size in (15, 0xFFFFFFFF):
            struct.pack_into('<I', self.buf, 8+12*8+4, size)
            with self.assertRaises(ContextError):
                self.resolve()

    def test_section_overlap(self):
        struct.pack_into('<I', self.buf, 8+14*8, 0x200)
        with self.assertRaises(ContextError):
            self.resolve()

    def test_invalid_parameter_and_reverse_method(self):
        for index in (-1, 1, True):
            with self.assertRaises(ContextError):
                self.resolve(index)
        with self.assertRaises(ContextError):
            self.resolve(methods=[1])

    def test_container_kind_range_ordinal_and_owner(self):
        for offset, value in ((0x200, 1), (0x20C, 1), (0x220, -1),
                              (0x224, -1), (0x228, 0), (0x22C, 1)):
            with self.subTest(offset=offset):
                original = self.buf[offset:offset+4]
                struct.pack_into('<i', self.buf, offset, value)
                with self.assertRaises(ContextError):
                    self.resolve()
                self.buf[offset:offset+4] = original


class GenericCarrierTests(unittest.TestCase):
    def test_token_range_normal_and_negative(self):
        raw = struct.pack('<III', 0x6000075, 1, 2)
        def parse(data, total=3):
            return select_rgctx_range(data,total,0x6000075,source='fixture',offset=0x80)
        self.assertEqual(parse(raw), (1,2))
        for bad in (b'',raw[:-1],raw+b'!',raw+raw,struct.pack('<III',1,0,1),struct.pack('<III',1,3,1)):
            with self.subTest(raw=bad), self.assertRaises(ContextError):
                parse(bad)
        with self.assertRaises(ContextError):
            parse(raw,2)

    def setUp(self):
        self.parts = [struct.pack('<QHBBI',0x200,0,0x15,0,0),
                      struct.pack('<QQ',0x300,0x400)+bytes(range(16)),
                      struct.pack('<QHBBI',2,0,0x12,0,0)]

    def parse(self, count=3):
        return generic_type_carrier(*self.parts, type_pointer=0x100, type_count=count, source='fixture')

    def test_normal_and_opaque_tail(self):
        row = self.parse()
        self.assertEqual(row['baseDefinitionIndex'], 2)
        self.assertEqual(row['classInstantiationPointerVa'], 0x400)
        self.assertEqual(row['opaqueCarrierTailHex'], bytes(range(16)).hex().upper())

    def test_truncated_and_trailing_ranges(self):
        for index in range(3):
            good = self.parts[index]
            for bad in (good[:-1], good+b'!'):
                self.parts[index] = bad
                with self.assertRaises(ContextError):
                    self.parse()
            self.parts[index] = good

    def test_invalid_count_definition_tags_and_null_pointers(self):
        for count in (2, -1, 1_000_001, True):
            with self.assertRaises(ContextError):
                self.parse(count)
        for part, offset, size in ((0,0,8),(1,0,8),(1,8,8),(0,10,1),(2,10,1)):
            good = self.parts[part]
            self.parts[part] = good[:offset]+bytes(size)+good[offset+size:]
            with self.assertRaises(ContextError):
                self.parse()
            self.parts[part] = good


class UsageCellTests(unittest.TestCase):
    def decode(self, raw, count=7):
        return method_spec_usage_index(raw, count, source='fixture', offset=0x20)

    def test_normal(self):
        self.assertEqual(self.decode(struct.pack('<Q', 0xC000000D)), 6)

    def test_truncated_and_trailing(self):
        for length in (0, 7, 9):
            with self.subTest(length=length), self.assertRaises(ContextError):
                self.decode(bytes(length))

    def test_wrong_tag_live_pointer_and_upper_bits(self):
        for word in (0x6000000D, 0xC000000C, 0x180000000, 0x1C000000D):
            with self.subTest(word=word), self.assertRaises(ContextError):
                self.decode(struct.pack('<Q', word))

    def test_bad_count_and_out_of_range(self):
        for count in (0, 6, -1, 1_000_001, True):
            with self.subTest(count=count), self.assertRaises(ContextError):
                self.decode(struct.pack('<Q', 0xC000000D), count)


class ImageOwnerTests(unittest.TestCase):
    def test_module_names_match_by_identity_not_order(self):
        self.assertEqual(match_image_modules(['A','B'], [('B',0x200),('A',0x100)], source='fixture'), {'A':0x100,'B':0x200})

    def test_duplicate_module_name_is_ambiguous(self):
        with self.assertRaises(ContextError) as caught:
            match_image_modules(['A','B'], [('A',0x100),('A',0x200)], source='fixture')
        self.assertEqual(caught.exception.diagnostics['actual']['candidatePointers'], [0x100,0x200])

    def test_missing_extra_and_duplicate_images_rejected(self):
        for images, modules in ((['A'], [('B',0x100)]), (['A','A'], [('A',0x100)]), (['A'], [('A',0)])):
            with self.subTest(images=images), self.assertRaises(ContextError):
                match_image_modules(images, modules, source='fixture')

    def fixture(self, intervals):
        data = bytearray(0xB0 + len(intervals)*40)
        struct.pack_into('<II', data, 0xA8, 0xB0, len(intervals)*40)
        for index, (start, count) in enumerate(intervals):
            struct.pack_into('<iI', data, 0xB0 + index*40 + 8, start, count)
        return bytes(data)

    def test_normal(self):
        self.assertEqual(type_image_owners(self.fixture([(0,2),(-1,0),(2,1)]), 3, source='fixture'), [0,0,2])

    def test_overlap_is_ambiguous(self):
        with self.assertRaises(ContextError) as caught:
            type_image_owners(self.fixture([(0,2),(1,2)]), 3, source='fixture')
        self.assertEqual(caught.exception.diagnostics['actual']['candidateImages'], [0,1])

    def test_hole_and_bad_count(self):
        for intervals in ([(0,1),(2,1)], [(0,4)], [(-1,1)], [(0,0xFFFFFFFF)]):
            with self.subTest(intervals=intervals), self.assertRaises(ContextError):
                type_image_owners(self.fixture(intervals), 3, source='fixture')

    def test_truncated_and_misaligned_section(self):
        good = self.fixture([(0,3)])
        for data in (good[:12], good[:-1], good[:0xAC]+struct.pack('<I',39)+good[0xB0:]):
            with self.assertRaises(ContextError):
                type_image_owners(data, 3, source='fixture')

    def test_unrelated_tail_not_consumed(self):
        self.assertEqual(type_image_owners(self.fixture([(0,3)])+b'tail', 3, source='fixture'), [0,0,0])


if __name__ == '__main__':
    unittest.main()
