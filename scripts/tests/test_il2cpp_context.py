import struct
import io
import json
from contextlib import redirect_stderr
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts.game_data.il2cpp_context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules
from scripts.game_data.il2cpp_context_audit import main, native_gate, sweep
from scripts.game_data.memorypack.skill_corpus import CensusGateError


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
