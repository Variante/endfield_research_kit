import struct
import io
import json
from contextlib import redirect_stderr
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts.game_data.il2cpp_context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range
from scripts.game_data.il2cpp_context_audit import main, native_gate, sweep, validate_selected_method_spec
from scripts.game_data.memorypack.skill_corpus import CensusGateError
from scripts.game_data.il2cpp_context import unresolved_usage_index, rip_qword_load_target
from scripts.game_data.il2cpp_context import class_sharing_branch
from scripts.game_data.il2cpp_context import named_top_level_type
from scripts.game_data.il2cpp_context import object_type_comparison_key
from scripts.game_data.il2cpp_context import method_pointer_indices
from scripts.game_data.il2cpp_context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp_context import method_spec_record, usage_method_spec


class UsageMethodSpecTests(unittest.TestCase):
    records=struct.pack('<iiiiii',0,-1,0,1,-1,1)
    usage=struct.pack('<Q', (6 << 29) | (1 << 1) | 1)

    def decode(self, usage=None, records=None, base=0x100):
        return usage_method_spec(self.usage if usage is None else usage,
                                 self.records if records is None else records,2,2,
                                 source='fixture.dll',usage_offset=0x80,records_offset=base)

    def test_exact_second_record(self):
        row=self.decode()
        self.assertEqual((row['index'],row['va'],row['definition'],row['methodInstantiationIndex']),
                         (1,0x10C,1,1))
        self.assertEqual(row['rawHex'],self.records[12:].hex().upper())

    def test_truncated_and_trailing(self):
        for records in (self.records[:-1],self.records+b'!',self.records[:12]):
            with self.assertRaises(ContextError): self.decode(records=records)
        for usage in (self.usage[:-1],self.usage+b'!'):
            with self.assertRaises(ContextError): self.decode(usage=usage)

    def test_bad_tag_or_index(self):
        for word in (0, (5<<29)|3, (6<<29)|5):
            with self.assertRaises(ContextError): self.decode(usage=struct.pack('<Q',word))

    def test_bad_record_count_or_offset(self):
        with self.assertRaises(ContextError) as caught:
            self.decode(records=self.records[:12]+struct.pack('<iii',1,-1,2))
        self.assertEqual(caught.exception.diagnostics['offset'],0x114)
        for base in (-1,True,(1<<64)-12):
            with self.assertRaises(ContextError): self.decode(base=base)


class MethodSpecRecordTests(unittest.TestCase):
    def decode(self, values=(1, -1, 0), **kwargs):
        return method_spec_record(struct.pack('<iii', *values), source='fixture.dll', offset=0x40,
                                  **{'method_count':2, 'instantiation_count':1, **kwargs})

    def test_normal_and_absent_contexts(self):
        self.assertEqual(self.decode(), (1, -1, 0))
        self.assertEqual(self.decode((0, -1, -1), instantiation_count=0), (0, -1, -1))

    def test_truncated_and_trailing(self):
        for length in (0, 11, 13):
            with self.assertRaises(ContextError):
                method_spec_record(bytes(length), 2, 1, source='fixture.dll')

    def test_malformed_indices(self):
        for values, relative in (((-1, -1, 0), 0), ((2, -1, 0), 0),
                                 ((1, -2, 0), 4), ((1, 1, 0), 4),
                                 ((1, -1, -2), 8), ((1, -1, 1), 8)):
            with self.subTest(values=values), self.assertRaises(ContextError) as caught:
                self.decode(values)
            self.assertEqual(caught.exception.diagnostics['offset'], 0x40+relative)

    def test_malformed_counts(self):
        for key in ('method_count', 'instantiation_count'):
            for count in (-1, True, 1_000_001):
                with self.subTest(key=key, count=count), self.assertRaises(ContextError):
                    self.decode(**{key:count})


class MethodSpecEvidenceTests(unittest.TestCase):
    records=struct.pack('<iiiiii',1,-1,0,2,-1,1)

    def row(self):
        return {'index':0,'va':0x100,'rawHex':self.records[:12].hex().upper(),
                'definition':1,'methodInstantiation':{'index':0}}

    def validate(self,row,records=None):
        validate_selected_method_spec(row,self.records if records is None else records,0x100,3,2,source='fixture.dll')

    def test_normal(self):
        self.validate(self.row())

    def test_later_loop_identity_overwrites_rejected(self):
        for key,value in (('index',1),('va',0x10C),('rawHex',self.records[12:].hex().upper()),
                          ('definition',2),('methodInstantiation',{'index':1})):
            row=self.row()
            row[key]=value
            with self.subTest(key=key),self.assertRaises(ContextError): self.validate(row)

    def test_malformed_evidence_and_record_tail(self):
        for row in (None,{},dict(self.row(),index=True),dict(self.row(),methodInstantiation=None)):
            with self.subTest(row=row),self.assertRaises(ContextError): self.validate(row)
        with self.assertRaises(ContextError): self.validate(self.row(),self.records+b'!')


class RgctxRangeEntriesTests(unittest.TestCase):
    raw = b''.join(struct.pack('<IIQ', i, 0xAABBCCDD, 0x100+i*8) for i in range(4))

    def decode(self, raw=None, start=2, count=2, offset=0x80):
        return rgctx_range_entries(self.raw if raw is None else raw, start, count,
                                   source='fixture.dll', offset=offset)

    def test_relative_and_module_indices_are_distinct(self):
        rows = self.decode()
        self.assertEqual([(r['relativeIndex'], r['moduleEntryIndex'], r['entryVa']) for r in rows],
                         [(0, 2, 0xA0), (1, 3, 0xB0)])
        self.assertEqual(rows[0]['opaquePaddingHex'], 'DDCCBBAA')
        self.assertEqual(rows[0]['dataPointerVa'], 0x110)

    def test_truncated_trailing_and_malformed_range(self):
        for raw in (self.raw[:-1], self.raw+b'!'):
            with self.assertRaises(ContextError): self.decode(raw)
        for start, count in ((-1, 1), (4, 1), (5, 0), (2, 3), (0, -1), (True, 1), (0, True)):
            with self.subTest(start=start, count=count), self.assertRaises(ContextError):
                self.decode(start=start, count=count)

    def test_empty_range_and_unknown_kind_preserved(self):
        self.assertEqual(self.decode(start=4, count=0), [])
        raw = struct.pack('<IIQ', 0xFFFFFFFF, 7, 0)
        self.assertEqual(self.decode(raw, start=0, count=1)[0]['kindRaw'], 0xFFFFFFFF)

    def test_address_bounds(self):
        for offset in (-1, True, (1 << 64)-63):
            with self.assertRaises(ContextError): self.decode(offset=offset)


class TypeParameterOwnerTests(unittest.TestCase):
    def fixture(self):
        raw = bytearray(0x300)
        struct.pack_into('<II', raw, 8+12*8, 0x200, 32)
        struct.pack_into('<II', raw, 8+14*8, 0x240, 16)
        for ordinal in range(2):
            struct.pack_into('<iihhHH', raw, 0x200+ordinal*16, 0, 0, -1, 0, ordinal, 0)
        struct.pack_into('<iiii', raw, 0x240, 0, 2, 0, 0)
        return raw

    def decode(self, raw, owners=None):
        return type_parameter_owner(raw, 1, [0] if owners is None else owners, source='fixture.dat')

    def test_normal_second_type_parameter(self):
        row = self.decode(self.fixture())
        self.assertEqual((row['typeIndex'], row['ordinal']), (0, 1))
        self.assertNotIn('methodIndex', row)

    def test_truncation_and_section_tail(self):
        raw = self.fixture()
        for changed in (raw[:0x7F], raw[:0x24F]):
            with self.assertRaises(ContextError): self.decode(changed)
        struct.pack_into('<I', raw, 8+12*8+4, 33)
        with self.assertRaises(ContextError): self.decode(raw)

    def test_wrong_kind_ordinal_count_and_reverse_owner(self):
        for offset, value in ((0x248, 1), (0x21C, 0), (0x244, 1), (0x240, 1), (0x210, 1)):
            raw = self.fixture()
            struct.pack_into('<i', raw, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ContextError): self.decode(raw)
        with self.assertRaises(ContextError): self.decode(self.fixture(), owners=[1])


class MethodPointerIndicesTests(unittest.TestCase):
    raw = struct.pack('<iii', 1, 2, -1)

    def decode(self, raw, method_count=2, invoker_count=3):
        return method_pointer_indices(raw, method_count, invoker_count,
                                      source='fixture.dll', offset=0x80)

    def test_normal_no_adjustor(self):
        self.assertEqual(self.decode(self.raw), (1, 2, -1))

    def test_truncated_and_trailing(self):
        for raw in (b'', self.raw[:-1], self.raw + b'\0'):
            with self.subTest(length=len(raw)), self.assertRaises(ContextError):
                self.decode(raw)

    def test_malformed_indices_and_unsupported_adjustors(self):
        for values, relative in (((-1, 2, -1), 0), ((2, 2, -1), 0),
                                 ((1, -1, -1), 4), ((1, 3, -1), 4),
                                 ((1, 2, -2), 8), ((1, 2, 0), 8)):
            with self.subTest(values=values), self.assertRaises(ContextError) as caught:
                self.decode(struct.pack('<iii', *values))
            self.assertEqual(caught.exception.diagnostics['offset'], 0x80 + relative)

    def test_malformed_counts(self):
        for count in (-1, True, 1_000_001):
            for key in ('method_count', 'invoker_count'):
                with self.subTest(key=key, count=count), self.assertRaises(ContextError):
                    self.decode(self.raw, **{key: count})


class ObjectTypeComparisonKeyTests(unittest.TestCase):
    raw = bytes.fromhex('068E00000000000000001C0000000000')

    def decode(self, raw):
        return object_type_comparison_key(raw, source='fixture.dll', offset=0x80)

    def test_normal_and_comparison_flag(self):
        self.assertEqual(self.decode(self.raw), (0x1C, 0))
        changed = bytearray(self.raw)
        changed[11] |= 0x20
        self.assertEqual(self.decode(changed), (0x1C, 1))

    def test_ignored_bytes_do_not_become_identity(self):
        for bit in range(128):
            if bit // 8 == 10 or bit == 11 * 8 + 5:
                continue
            changed = bytearray(self.raw)
            changed[bit // 8] ^= 1 << (bit % 8)
            with self.subTest(bit=bit):
                self.assertEqual(self.decode(changed), self.decode(self.raw))

    def test_truncated_and_trailing_rejected(self):
        for changed in (b'', self.raw[:-1], self.raw + b'\0'):
            with self.subTest(length=len(changed)), self.assertRaises(ContextError) as caught:
                self.decode(changed)
            self.assertEqual(caught.exception.diagnostics['offset'], 0x80)

    def test_other_tags_fail_closed(self):
        for tag in range(256):
            if tag == 0x1C:
                continue
            changed = bytearray(self.raw)
            changed[10] = tag
            with self.subTest(tag=tag), self.assertRaises(ContextError) as caught:
                self.decode(changed)
            self.assertEqual(caught.exception.diagnostics['offset'], 0x8A)


class NamedTopLevelTypeTests(unittest.TestCase):
    def fixture(self, duplicate=False):
        count=2 if duplicate else 1
        raw=bytearray(0x300)
        struct.pack_into('<II',raw,0x18,0xB0,10)
        raw[0xB0:0xBA]=b'I\0NS\0Type\0'
        struct.pack_into('<II',raw,0xA0,0x100,92*count)
        struct.pack_into('<II',raw,0xA8,0x200,40)
        struct.pack_into('<iiii',raw,0x200,0,0,0,count)
        for i in range(count):
            struct.pack_into('<iiii',raw,0x100+i*92,5,2,3,-1)
        return raw

    def decode(self, raw):
        return named_top_level_type(bytes(raw),b'I',b'NS',b'Type',source='fixture.dat')

    def test_normal_exact_reference(self):
        result=self.decode(self.fixture())
        self.assertEqual((result['imageIndex'],result['typeDefinitionIndex'],result['byvalTypeIndex']),(0,0,3))

    def test_truncated_and_bad_section_count(self):
        raw=self.fixture()
        for changed in (raw[:0xAF],raw[:0x220]):
            with self.assertRaises(ContextError):
                self.decode(changed)
        struct.pack_into('<I',raw,0xA4,93)
        with self.assertRaises(ContextError):
            self.decode(raw)

    def test_unterminated_and_out_of_bounds_string(self):
        for field,value in ((0x100,10),(0x1C,9)):
            raw=self.fixture()
            struct.pack_into('<i',raw,field,value)
            with self.assertRaises(ContextError):
                  self.decode(raw)

    def test_ambiguity_nested_and_exported_rejected(self):
        with self.assertRaises(ContextError):
            self.decode(self.fixture(duplicate=True))
        for field,value in ((0x10C,0),(0x214,1)):
            raw=self.fixture()
            struct.pack_into('<i',raw,field,value)
            with self.assertRaises(ContextError):
                self.decode(raw)

    def test_image_section_trailing_and_out_of_bounds_rejected(self):
        for field, value in ((0xAC, 41), (0xA8, 0x2FF)):
            with self.subTest(field=field, value=value):
                raw = self.fixture()
                struct.pack_into('<I', raw, field, value)
                with self.assertRaises(ContextError) as caught:
                    self.decode(raw)
                self.assertEqual(caught.exception.diagnostics['source'], 'fixture.dat')

    def test_negative_byval_index_rejected(self):
        raw = self.fixture()
        struct.pack_into('<i', raw, 0x108, -1)
        with self.assertRaises(ContextError):
            self.decode(raw)

    def test_overlapping_sections_rejected(self):
        raw=self.fixture()
        struct.pack_into('<I',raw,0x18,0x100)
        with self.assertRaises(ContextError) as caught:
            self.decode(raw)
        self.assertEqual(caught.exception.diagnostics['expected'],'disjoint string/type/image sections')


class ClassSharingBranchTests(unittest.TestCase):
    compare=bytes.fromhex('80790A120F84')+struct.pack('<i',0xF6)
    load=bytes.fromhex('488B1D')+struct.pack('<i',0xF9)
    advance=bytes.fromhex('4883C320')

    def decode(self, compare=None, load=None, advance=None):
        return class_sharing_branch(self.compare if compare is None else compare,0x100,
                                    self.load if load is None else load,0x200,
                                    self.advance if advance is None else advance,source='fixture.dll')

    def test_normal_anonymous_global(self):
        self.assertEqual(self.decode(),0x300)

    def test_truncated_and_trailing(self):
        for key,raw in (('compare',self.compare),('load',self.load),('advance',self.advance)):
            for changed in (raw[:-1],raw+b'\0'):
                with self.subTest(key=key,changed=changed),self.assertRaises(ContextError):
                    self.decode(**{key:changed})

    def test_malformed_offset_and_other_type_tag(self):
        for raw in (self.compare[:6]+struct.pack('<i',0xF5),self.compare[:3]+b'\x11'+self.compare[4:]):
            with self.subTest(raw=raw),self.assertRaises(ContextError):
                self.decode(compare=raw)
        with self.assertRaises(ContextError):
            self.decode(advance=bytes.fromhex('4883C310'))


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
