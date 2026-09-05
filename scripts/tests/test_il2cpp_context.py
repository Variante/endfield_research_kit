import struct
import io
import json
from contextlib import redirect_stderr
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts.game_data.il2cpp_context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range
from scripts.game_data.il2cpp_context_audit import main, native_gate, sweep, validate_selected_method_spec, reader_cursor_consumers, reader_construction, serializer_return_consumers, skill_resource_context
from scripts.game_data.memorypack.skill_corpus import CensusGateError
from scripts.game_data.il2cpp_context import unresolved_usage_index, rip_qword_load_target
from scripts.game_data.il2cpp_context import class_sharing_branch
from scripts.game_data.il2cpp_context import named_top_level_type
from scripts.game_data.il2cpp_context import object_type_comparison_key
from scripts.game_data.il2cpp_context import method_pointer_indices
from scripts.game_data.il2cpp_context import generic_method_candidates
from scripts.game_data.il2cpp_context_audit import resource_carrier_consumers, module_methods, stream_carrier_consumer, stream_source_identity
from scripts.game_data.il2cpp_context_audit import vfs_stream_identity, vfs_stream_consumer
from scripts.game_data.il2cpp_context_audit import file_stream_open, vfs_descriptor_path, vfs_descriptor_producer, vfs_bytebuf_consumer, vfs_block_cursor
from scripts.game_data.il2cpp_context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp_context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.il2cpp_context_audit import vfs_block_transform
from scripts.game_data.il2cpp_context_audit import vfs_block_file_source
from scripts.game_data.il2cpp_context_audit import native_file_read
from scripts.game_data.il2cpp_context_audit import vfs_path_carrier


class VfsPathCarrierTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in (
            (0x318BFFA,0x2D7F770),(0x318C12E,0x2D7AE60),
            (0x2D7F7CB,0x2D7F920),(0x2D7AEC6,0x2D7DBF0),
            (0x2D7FB68,0x2D7FE70),(0x2D7FD10,0x2D7FE70),
            (0x2D7DF60,0x2F46C10),(0x2D7E0CC,0x2F46C10),(0x2D7E210,0x2F46C10),
            (0x318C03E,0x2D7E480),(0x318C15D,0x2D7E480),
            (0x2D7E601,0x2DF2AA0),(0x2D7E636,0x2D72FA0))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x2D7F7D3,'0F10000F1048100F11030F114B10'),(0x2D7AECE,'0F10000F1048100F11030F114B10'),
            (0x2D7FB6D,'4889442438'),(0x2D7FBCF,'4889742440'),(0x2D7FC2F,'4C897C2448'),
            (0x2D7FD15,'4889442438'),(0x2D7FD70,'4C897C2440'),(0x2D7FDE3,'498BC6410F1106410F114E10'),
            (0x2D7DF65,'488945C8'),(0x2D7DFBF,'4C8975D0'),(0x2D7E00F,'488975D8'),
            (0x2D7E215,'488945C8'),(0x2D7E26F,'488975D0'),(0x2D7E2D9,'410F1107410F114F10'),
            (0x2D7E58A,'488B7E08'),(0x2D7E5A4,'4C8B7610'),(0x2D7E5B7,'4C8B3E488B7618'),
            (0x2D7E5EE,'48897424204D8BCE4C8BC7498BD7488D4C2438'),
            (0x2D7E61E,'488D5020'),(0x2D7E62B,'4533C9448B442440488BCB'))})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return vfs_path_carrier(self.pe,None,{},[],source='fixture.dll')

    def test_four_slots_without_root_semantics(self):
        row=self.decode()
        self.assertEqual(row['carrierByteLength'],32)
        self.assertIn('leaves +0x18 zero',row['boundary'])
        self.assertIn('do not establish formatting syntax',row['boundary'])

    def test_truncated_trailing_and_mutated_evidence(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good

    def test_swapped_getter_fails(self):
        rva=0x2D7FB68
        self.parts[rva]=b'\xe8'+struct.pack('<i',0x2F46C10-rva-5)
        with self.assertRaises(ContextError) as caught:self.decode()
        self.assertIn('fixture.dll',str(caught.exception))


class NativeFileReadTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',0x3AFCB00-rva-5) for rva in (0x2FCA582,0x2FCA69D)}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x2FCA4BD,'85ED0F8826AACF0185DB0F88BAA9CF01418B46183BE80F8F55A9CF012BC33BE80F8FF2A8CF01'),
            (0x2FCA508,'412BFF3BDF7F028BFB'),(0x2FCA576,'448BC8498BCF4533C0498BD5'),
            (0x2FCA68C,'448BCB4889442420448BC5498BD6498BCF'),
            (0x2FCA6BC,'83F8FF0F848CA6CF014863C348014668E90DFFFFFF'),(0x2FCA5DE,'03DF8BC3'),
            (0x3AFCB1D,'418BD94963F04C8BF24533E4'),(0x3AFCB7A,'4C8B7810'),
            (0x3AFCB93,'488BBC24B00000004489278D041E413B46180F87AE000000'),
            (0x3AFCBAB,'488D56204903D644896424344C896424204C8D4C2434448BC3498BCF'),
            (0x3AFCBCD,'85C07508'),(0x3AFCBD7,'89078B5C2434'),
            (0x3AFCBF5,'B8FFFFFFFF833F000F45D8895C2438'),(0x3AFCC3C,'8BC3'))})
        self.header={0x3C:0x100,0x100+24+120:0xCF8EBC0,0x100+24+124:220}
        self.parts[0xCF8EBC0]=struct.pack('<IIIII',0xCF8ECE8,0,0,0xCF8FE50,0xA82F048)
        self.parts[0xCF8FE50]=b'KERNEL32.dll\0'
        for rva,index,name_rva,hint,name in ((0x3AFCBC7,78,0xCF8FC30,0x4A9,b'ReadFile'),
                                            (0x3AFCBD1,4,0xCF8F668,0x28D,b'GetLastError')):
            self.parts[rva]=b'\xff\x15'+struct.pack('<i',0xA82F048+index*8-rva-6)
            self.parts[0xCF8ECE8+index*8]=struct.pack('<Q',name_rva)
            self.parts[name_rva]=struct.pack('<H',hint)+name+b'\0'
        self.pe=SimpleNamespace(image_base=0x180000000,u32_at_file=lambda at:self.header[at],
            bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return native_file_read(self.pe,None,{},[],source='fixture.dll')

    def test_static_import_names_and_distinct_count_carrier(self):
        row=self.decode()
        self.assertEqual([x['name'] for x in row['selectedImports']],['ReadFile','GetLastError'])
        self.assertIn('does not derive the count from the API boolean',row['boundary'])
        self.assertIn('live IAT contents',row['boundary'])

    def test_all_selected_bytes_fail_closed(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good

    def test_malformed_directory_rva_or_length(self):
        for at in (0x100+24+120,0x100+24+124):
            good=self.header[at];self.header[at]=good+1
            with self.subTest(at=at),self.assertRaises(ContextError):self.decode()
            self.header[at]=good

    def test_ordinal_thunk_rejected(self):
        self.parts[0xCF8EF58]=struct.pack('<Q',(1<<63)|0x4A9)
        with self.assertRaises(ContextError) as caught:self.decode()
        self.assertIn('fixture.dll',str(caught.exception))


class VfsBlockFileSourceTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in (
            (0x318BC48,0x318BE20),(0x318BD63,0x318BE20),
            (0x318BC60,0x318BFA0),(0x318BD8F,0x318C0C0),
            (0x318BC8A,0x318B640),(0x318BDA9,0x318B640),
            (0x318C060,0x2D71FA0),(0x318C17E,0x2D71FA0),
            (0x318C06A,0x318C220),(0x318C188,0x318C220),
            (0x318C2BE,0x2DF9D00),(0x318C2F3,0x3AF70))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x318BC81,'4533C0488BD3488BC8'),(0x318BDA0,'4533C0488BD3488BC8'),
            (0x318C065,'33D2488BC8'),(0x318C06F,'488BF8'),(0x318C07D,'488BC7'),
            (0x318C183,'33D2488BC8'),(0x318C18D,'488BF8'),(0x318C19B,'488BC7'),
            (0x318C26A,'4533F6'),(0x318C2EE,'B90B000000'),
            (0x318C2F8,'488BF8483DFFFFFF7F0F8FB20000004885C00F8483000000'),
            (0x318C310,'8BD0'),(0x318C31E,'4C8BF885FF7E4D'),
            (0x318C341,'4C8B9060030000488B80680300004889442420448BCF458BC6498BD7488BCE41FFD2'),
            (0x318C363,'85C00F84AF0000004403F02BF8EBAF'),
            (0x318C372,'4C89BC24A0000000'),(0x318C3FB,'498BC7'))})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])
        self.method=SimpleNamespace(slot=34,parameter_count=3)

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return vfs_block_file_source(self.pe,SimpleNamespace(methods={287719:self.method}),{},[],source='fixture.dll')

    def test_read_loop_does_not_certify_eof(self):
        row=self.decode()
        self.assertEqual(row['readSlot'],34)
        self.assertIn('adds EAX to offset and subtracts EAX',row['boundary'])
        self.assertIn('full-fill reasoning requires the Read override contract',row['boundary'])

    def test_truncated_trailing_mutated_instruction_fails(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good

    def test_wrong_slot_or_parameter_count_fails(self):
        for field,bad,good in (('slot',35,34),('parameter_count',2,3)):
            setattr(self.method,field,bad)
            with self.subTest(field=field),self.assertRaises(ContextError):self.decode()
            setattr(self.method,field,good)


class VfsBlockTransformTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in (
            (0x318B91E,0x507D3C4),(0x507D3DE,0x2C97EF0),
            (0x318B93D,0x33AF150),(0x2C97FE6,0x2C97A90))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x318B66A,'488BF1'),
            (0x318B8FE,'488B82B8000000448B80E4000000448B4E18452BC848897C2420488BD6488BCB'),
            (0x318B92A,'488B88B80000004533C08B91E4000000488BCE'),
            (0x318B942,'488BF8488BC7'),
            (0x507D3C4,'4883EC4848C74424300000000044894C24284C8BCA4489442420'),
            (0x2C97EFD,'448B642478498BE9458BE84C8BFA488BF14585E40F8EBD000000'),
            (0x2C97F42,'448B742470438D0426413B41180F8FA082E401438D04043942180F8CFE81E401'),
            (0x2C97F62,'418BF8452BF0'),(0x2C97F70,'0FB65E3080E33F7468'),
            (0x2C97F79,'418D043E3B4518736B4C8B46284D85C07468440FB6CB453B48187358413B7F187352'),
            (0x2C97F9B,'418D043EFEC34863C84863C7FFC70FB654292043325401204288543820'),
            (0x2C97FB8,'8BC7412BC5885E30413BC47CAB'),
            (0x318B8F7,'488B1512E1F209'),(0x318B923,'488B05E6E0F209'))})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return vfs_block_transform(self.pe,None,{},[],source='fixture.dll')

    def test_aliasing_is_not_cipher_or_eof_proof(self):
        row=self.decode()
        self.assertEqual(len(row['edges']),4)
        self.assertEqual(len({x['cellVa'] for x in row['staticStorage']}),1)
        self.assertIn('identical input/output array pointers',row['boundary'])
        self.assertIn('Nonpositive count returns without validation',row['boundary'])
        self.assertIn('neither a complete decryption algorithm nor EOF',row['boundary'])

    def test_all_evidence_rejects_truncated_trailing_or_mutated_bytes(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good

    def test_different_static_cell_fails_with_source_and_offset(self):
        good=self.parts[0x318B923]
        self.parts[0x318B923]=good[:3]+struct.pack('<i',struct.unpack('<i',good[3:])[0]+8)
        with self.assertRaises(ContextError) as caught:self.decode()
        diagnostic=str(caught.exception)
        self.assertIn('fixture.dll',diagnostic)
        self.assertIn('expected',diagnostic)


class VfsBlockCursorTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in (
            (0x33AF224,0x449AEB0),(0x33AF346,0x2D76170),(0x2D76351,0x2D76D10),
            (0x4D86E74,0x2D76630),(0x33AF1C4,0x2D767D0),(0x33AF1E8,0x2FE7660))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x449AEE1,'C744243400000000897C24304889742438'),
            (0x449AEF7,'0F10442430488B742468488BC30F1103'),
            (0x33AF21A,'488D4DB0458BC6488BD6'),(0x33AF33C,'4C8D45A08BD6488D4DC0'),
            (0x2D7634C,'4C8BC68BD5'),
            (0x2D76356,'0F10000F1048100F11030F114B104883C3204883EF0175C2'),
            (0x2D76249,'4C63F0'),(0x2D76286,'498BDE48C1E305'),(0x2D76326,'4585F67E43'),
            (0x33AF1A6,'8B5E18412BDE83EB0485DB0F8EEE7C9D01'),
            (0x33AF1ED,'3BF80F858A7C9D01'),
            (0x33AF3B0,'8B40182B45A085C0410F4EC685C07E0A837F48030F84A47A9D01'),
            (0x4D86E79,'90E94B8562FE'),(0x33AF3CA,'488BC7'))})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return vfs_block_cursor(self.pe,None,{},[],source='fixture.dll')

    def test_same_carrier_is_not_eof(self):
        row=self.decode()
        self.assertIn('same mutable carrier',row['boundary'])
        self.assertIn('No final equality check follows',row['boundary'])
        self.assertIn('before its positive-count loop',row['boundary'])

    def test_truncated_trailing_and_mutated_evidence(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good

    def test_wrong_version_condition_fails_with_diagnostic(self):
        raw=bytearray(self.parts[0x33AF3B0]);raw[19]=4;self.parts[0x33AF3B0]=bytes(raw)
        with self.assertRaises(ContextError) as caught:self.decode()
        self.assertIn('fixture.dll',str(caught.exception))


class VfsByteBufConsumerTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in (
            (0x2D76F35,0x2D78240),(0x2D76FAD,0x2D78240),(0x2D76FC2,0x2D78240),
            (0x2D770CB,0x2D79390),(0x2D77847,0x3E1DF70),(0x2D778B2,0x3820080))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x2D76EB9,'66C1E108660BCA6683C1020FBFC10103'),
            (0x2D76F2A,'4533C941B0018BD6488BCF'),(0x2D76F3A,'830308'),
            (0x2D76FB2,'8D5608488945F74533C941B001488BCF'),
            (0x2D76FC7,'488945FF0F2875F7830310'),
            (0x2D770B1,'488D55F7488BCF660F7F75F7'),(0x2D770F4,'8B7C0838897D0F'),
            (0x2D776FE,'0F1045070F104D170F11000F114810'),
            (0x2D78298,'8D47073B43180F8D02010000'),(0x2D783A6,'33C0EBC3'),
            (0x2D782B1,'4084F60F84877ED701'),(0x100,'7FDF0000000000000000112000000000'))})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000],
                                u64_at_va=lambda va:0x180000100)
        self.parameter=SimpleNamespace(type_index=93608)
        self.parameters=[None]*235375+[self.parameter]
        self.count=200000

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]), \
             patch('scripts.game_data.il2cpp_context_audit.named_top_level_type',return_value={'typeDefinitionIndex':57215}):
            return vfs_bytebuf_consumer(self.pe,SimpleNamespace(buf=b'',parameters=self.parameters,
                methods={247366:SimpleNamespace(parameter_start=235374,parameter_count=2)}),{},[],
                {'typesCount':self.count,'types':'0x100000'},source='fixture.dll')

    def test_short_read_zero_and_cursor_advance_remain_distinct(self):
        row=self.decode()
        self.assertIn('returns zero normally; callers still advance',row['boundary'])
        self.assertIn('sign-extended',row['boundary'])
        self.assertIn('not a fail-closed source-range validator',row['boundary'])

    def test_wrong_parameter_and_truncated_parameter_table(self):
        self.parameter.type_index=93609
        with self.assertRaises(ContextError):self.decode()
        self.parameter.type_index=93608
        self.parameters.pop()
        with self.assertRaises(ContextError):self.decode()

    def test_bad_registered_type_count(self):
        self.count=93608
        with self.assertRaises(ContextError):self.decode()

    def test_truncated_trailing_and_mutated_evidence(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good


class VfsDescriptorProducerTests(unittest.TestCase):
    def setUp(self):
        self.base=0x180000000
        self.parts={}
        for ordinal,(rva,index,definition,ci) in enumerate(((0x2D752A2,55461,286427,3297),
            (0x2D756A4,70920,286427,4291),(0x2D75759,70927,286407,4291),(0x2D757D4,55468,286407,3297))):
            cell=0x100+ordinal*8
            self.parts[rva]=bytes.fromhex('488B2D')+struct.pack('<i',cell-rva-7)
            self.parts[cell]=struct.pack('<Q',(6<<29)|(index<<1)|1)
            self.parts[0x100000+index*12]=struct.pack('<iii',definition,ci,-1)
        for rva in (0x2D7527E,0x2D75689,0x2D757B9):
            self.parts[rva]=bytes.fromhex('488B05')+struct.pack('<i',0xD072F48-rva-7)
        for rva,target in ((0x2D756EB,0x2D79390),(0x2D757B4,0x3E1DF70),(0x2D75825,0x3820080)):
            self.parts[rva]=b'\xe8'+struct.pack('<i',target-rva-5)
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x2D756F0,'85C0783D'),(0x2D75701,'3B41180F83FC010000489848C1E0058B5C0838895E08'),
            (0x2D75763,'8B5A202B5A28'),(0x2D7578A,'41B1010F104500448BC3498BCE'),
            (0x2D75801,'0F10450041B101498BCE'),(0x2D7581E,'8BD34889442420'),
            (0x2D7582A,'E9E5FEFFFF'),(0x2D756AB,'488B4720488B88C0000000488B81B0000000'),
            (0x2D75769,'488B4720488B88C0000000488B81C0000000'))})
        a='3B8D0000000000000000088000000000';b='7EDF0000000000000000118000000000'
        self.args={3297:[a,b],4291:[b,a]}
        self.reg={'methodSpecsCount':80000,'methodSpecs':hex(self.base+0x100000),'genericInstsCount':5000}
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=lambda va,size:self.parts[va-self.base])

    def decode(self):
        def resolve(index):
            return SimpleNamespace(arguments=[SimpleNamespace(raw_type_record_hex=x) for x in self.args[index]],
                                   as_dict=lambda:{'index':index})
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]), \
             patch('scripts.game_data.il2cpp_context_audit.named_top_level_type',return_value={'typeDefinitionIndex':0xDF7E}):
            return vfs_descriptor_producer(self.pe,SimpleNamespace(buf=b'',methods=range(300000)),{},[],
                self.reg,SimpleNamespace(resolve=resolve),source='fixture.dll')

    def test_original_method_context_and_reversed_arguments(self):
        row=self.decode()
        self.assertEqual([x['methodSpecIndex'] for x in row['methodUsages']],[55461,70920,70927,55468])
        self.assertIn('not FindEntry/TryInsert',row['boundary'])
        self.assertIn('return values are not checked',row['boundary'])

    def test_argument_order_must_not_be_inferred_from_same_set(self):
        self.args[4291].reverse()
        with self.assertRaises(ContextError):self.decode()

    def test_bad_usage_count_and_method_spec_extent(self):
        self.reg['methodSpecsCount']=55461
        with self.assertRaises(ContextError):self.decode()

    def test_corrupt_truncated_and_trailing_evidence(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good


class VfsDescriptorPathTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in
            ((0x2D7A52D,0x2D7A040),(0x2D7A53A,0x2D75510),
             (0x2D7A13E,0x2D751D0),(0x2D752DE,0x3820560),(0x4C48A6A,0x6DBEEC0))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x2D7557F,'8B4318C1E80A'),(0x2D7A546,'0FB6F0'),(0x2D7A56C,'440FB6C6'),
            (0x2D7A0DE,'F64718020F871810ED01'),(0x2D7A134,'4533C0488D4D20488BD7'),
            (0x2D75260,'837F08000F8CD837ED01'),(0x2D75285,'448B7708488B88B8000000488B5908'),
            (0x2D752CA,'418BD6488BCB'),(0x2D752E8,'85C00F885237ED01'),
            (0x2D752F0,'488B4B184885C90F849E0000003B41180F838F000000'),
            (0x2D75306,'489848C1E0050F10440830'),(0x2D7531E,'0F1106'),
            (0x4C48A6F,'0F57C0E99AC812FE'))})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return vfs_descriptor_path(self.pe,None,{},[],source='fixture.dll')

    def test_mode_projection_and_indirect_record(self):
        row=self.decode()
        self.assertEqual(row['mode']['effectiveBitRangeInclusive'],[10,17])
        self.assertEqual(row['lookup']['descriptorKeyOffset'],8)
        self.assertEqual(row['lookup']['resultBytes'],16)
        self.assertIn('does not read an inline',row['boundary'])

    def test_negative_lookup_can_return_zero_not_proven_throw(self):
        row=self.decode()
        self.assertIn('if that call returns normally',row['boundary'])
        self.assertIn('not a proven throwing rejection',row['boundary'])

    def test_truncated_trailing_and_malformed_evidence(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good

    def test_bound_check_polarity_and_stride_cannot_change(self):
        for rva,index in ((0x2D75260,5),(0x2D752F0,17),(0x2D75306,5)):
            original=self.parts[rva]
            changed=bytearray(original);changed[index]^=1;self.parts[rva]=bytes(changed)
            with self.assertRaises(ContextError) as caught:self.decode()
            self.assertIn('fixture.dll',str(caught.exception))
            self.parts[rva]=original


class FileStreamOpenTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in
            ((0x2D7A716,0x2D7ACD0),(0x2D7A975,0x5BBB52C),
             (0x2D7ADD5,0x2DF9D00),(0x5BBB607,0x30A4310),(0x5BBB61E,0x51D80))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x2D7A549,'8B6B10'),(0x2D7A68C,'4080FF010F84C60200004080FF027423'),
            (0x2D7ACEB,'4963F8'),(0x5BBB547,'4963F8'),(0x2D7ADDA,'85FF7425'),(0x5BBB60C,'85FF7E14'),
            (0x2D7ADE9,'498B8140030000488BD74D8B89480300004533C0488BCBFFD0'),
            (0x5BBB610,'4C8BC7B9200000004533C9488BD3'),
            (0x51DA9,'4C8D4B14448BC749C1E104488BD64D030E498BCE498B014D8B4908'))})
        for rva in (0x2D7AD7F,0x5BBB5C0):self.parts[rva]=bytes.fromhex('488B0D')+struct.pack('<i',0x300-rva-7)
        self.parts[0x300]=struct.pack('<Q',(1<<29)|(119269<<1)|1)
        self.parts[0x400]=bytes.fromhex('10930000000000000000120000000000')
        self.parts[0x2D7ACA8]=bytes.fromhex('D0A9D702DFA9D702EEA9D70251AAD70260AAD702EEA9D70219ABD702')
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000],
                                u64_at_va=lambda va:0x180000400)
        self.seek=SimpleNamespace(slot=32)

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]), \
             patch('scripts.game_data.il2cpp_context_audit.named_top_level_type',return_value={'typeDefinitionIndex':37648,'byvalTypeIndex':119269}):
            return file_stream_open(self.pe,SimpleNamespace(buf=b'',types={37648:SimpleNamespace(parent_index=143204)},
                methods={287727:self.seek}),{},[],{'typesCount':200000,'types':'0x100000'},source='fixture.dll')

    def test_distinct_signed_offset_predicates(self):
        result=self.decode()
        self.assertEqual(len(result['allocations']),2)
        self.assertIn('positive offsets',result['boundary'])
        self.assertIn('any nonzero offset',result['boundary'])

    def test_wrong_seek_slot(self):
        self.seek.slot=33
        with self.assertRaises(ContextError):self.decode()

    def test_corrupt_truncated_and_trailing_evidence(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[rva]=good


class VfsStreamIdentityTests(unittest.TestCase):
    def setUp(self):
        self.parts={0x180000300:struct.pack('<Q',(1<<29)|(147393<<1)|1),
                    0x200:bytes.fromhex('07930000000000000000120000000000'),
                    0x400:bytes.fromhex('987C0000000000000000120000000000'),
                    0x182D7A588:bytes.fromhex('488B0D')+struct.pack('<i',0x300-0x2D7A58F)}
        self.pointers={0x100000+143204*8:0x200,0x100000+147393*8:0x400}
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va],u64_at_va=self.pointers.__getitem__)
        self.parent=SimpleNamespace(parent_index=143204)
        self.methods={i:SimpleNamespace(slot=s) for i,s in ((247486,35),(247495,11),(247496,12))}

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]), \
             patch('scripts.game_data.il2cpp_context_audit.named_top_level_type',return_value={'typeDefinitionIndex':31896,'byvalTypeIndex':147393}):
            return vfs_stream_identity(self.pe,SimpleNamespace(buf=b'',types={31896:self.parent},methods=self.methods),
                {},[],{'typesCount':200000,'types':'0x100000'},source='fixture.dll')

    def test_normal_allocation_is_not_runtime_receipt(self):
        result=self.decode()
        self.assertEqual(result['allocationCellVa'],0x180000300)
        self.assertIn('not successful execution',result['boundary'])

    def test_wrong_parent_and_override_slot(self):
        self.parent.parent_index=1
        with self.assertRaises(ContextError):self.decode()
        self.parent.parent_index=143204
        self.methods[247486].slot=34
        with self.assertRaises(ContextError):self.decode()

    def test_bad_allocation_usage_or_type_record(self):
        for key in (0x180000300,0x400):
            original=self.parts[key]
            for bad in (b'',original[:-1],original+b'!',bytes(len(original))):
                self.parts[key]=bad
                with self.subTest(key=key,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[key]=original


class VfsStreamConsumerTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in
            ((0x2D7A580,0x2D7A640),(0x2D7A5A0,0x26060),(0x2D7A5DF,0x2D076C0),
             (0x2D06BCA,0x3AF70),(0x3DBBE03,0x3AF70),(0x2D06C24,0x508E0),
             (0x4C36099,0x3A8ADF0),(0x2D06CDE,0x2C97740))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x2D0770C,'410F1006488D4F4848895F48410F104E100F1147280F114F38'),
            (0x4A49105,'8B433C4883C4205BC3'),(0x3DBBE08,'8B4B38482BC14883C4205BC3'),
            (0x2D06BC2,'B90C000000488BD3'),(0x3DBBDF5,'488B53484885D27433B90C000000'),
            (0x2D06C15,'B9230000004C8D4424300F29442430'),
            (0x50906,'498B80700300004D8B80780300000F29442420FFD0'),
            (0x2D06C29,'8BF83B46080F87DCF4F201'),(0x2D06CE3,'8BC7488B7C2468488B5C24704883C4505EC3'))})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_descriptor_offsets_and_non_full_read(self):
        result=vfs_stream_consumer(self.pe,source='fixture.dll')
        self.assertEqual(result['descriptorStateOffset']+result['length']['descriptorOffset'],result['length']['stateOffset'])
        self.assertIn('without a full-fill loop',result['read']['boundary'])

    def test_mutated_truncated_and_trailing_windows(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):vfs_stream_consumer(self.pe,source='fixture.dll')
            self.parts[rva]=good


class StreamSourceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.methods={249853:SimpleNamespace(parameter_start=237944,parameter_count=1),
            287486:SimpleNamespace(slot=11,return_type=126199),287526:SimpleNamespace(slot=35,return_type=126157)}
        self.parameters=[None]*237945
        self.parameters[-1]=SimpleNamespace(type_index=143204)
        self.records=[(0,-1,-1)]*521493
        expected=((517109,249865,0x3B188A0),(517125,249853,0x2D36380),
                  (517721,428652,0x3B677B0),(521492,248587,0x3187EB0))
        self.pointers={0x100000+143204*8:0x200,0x100000+126199*8:0x300,0x100000+126157*8:0x400}
        self.raw_types={0x200:bytes.fromhex('07930000000000000000120000000000'),
            0x300:bytes.fromhex('3C8D00000000000000000A8000000000'),
            0x400:bytes.fromhex('3B8D0000000000000000088000000000')}
        self.raw=b''
        for i,(spec,definition,rva) in enumerate(expected):
            self.records[spec]=(definition,-1,75)
            self.raw+=struct.pack('<4i',spec,i,i,-1)
            self.pointers[0x500+i*8]=0x180000000+rva
        self.pe=SimpleNamespace(image_base=0x180000000,u64_at_va=self.pointers.__getitem__,
                                bytes_at_va=lambda va,size:self.raw_types[va])
        self.reg={'types':'0x100000','typesCount':200000,'genericMethodTable':'0x200000',
                   'genericMethodTableCount':4,'methodSpecs':'0x300000'}
        self.code={'genericMethodPointers':'0x500','genericMethodPointersCount':4,'invokerPointersCount':4}

    def decode(self):
        def identities(pe,md,modules,owners,selections,**kwargs):return [{'methodIndex':x[0]} for x in selections]
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',side_effect=identities), \
             patch('scripts.game_data.il2cpp_context_audit.named_top_level_type',return_value={'typeDefinitionIndex':37639}):
            return stream_source_identity(self.pe,SimpleNamespace(buf=b'',methods=self.methods,parameters=self.parameters),
                {},[],self.reg,self.code,self.records,self.raw,source='fixture.dll')

    def test_stream_slots_and_generic_bodies(self):
        result=self.decode()
        self.assertEqual([x['virtualSlot'] for x in result['declaredStreamMethods']],[11,35])
        self.assertEqual(len(result['genericBodyCandidates']),4)
        self.assertIn('concrete stream subclass',result['boundary'])

    def test_wrong_virtual_slot_or_return_record(self):
        self.methods[287526].slot=36
        with self.assertRaises(ContextError):self.decode()
        self.methods[287526].slot=35
        self.raw_types[0x400]=self.raw_types[0x300]
        with self.assertRaises(ContextError):self.decode()

    def test_wrong_parameter_type_and_truncation(self):
        self.parameters[-1].type_index=143205
        with self.assertRaises(ContextError):self.decode()
        self.parameters[-1].type_index=143204
        self.raw_types[0x200]=self.raw_types[0x200][:-1]
        with self.assertRaises(ContextError):self.decode()

    def test_wrong_shared_context(self):
        self.records[517125]=(249853,-1,16656)
        with self.assertRaises(ContextError):self.decode()


class StreamCarrierConsumerTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in
            ((0x2D363DC,0x3AF70),(0x2D36425,0x3AF70),(0x2D36470,0x3AF70),
             (0x2D365F1,0x3AF70),(0x2D36448,0x3150DD0),(0x2D3659E,0x3B188A0),(0x2D36961,0x3B188A0))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x3AF78,'0FB7D9488BFA488B0AE80A9CFCFF488D431448C1E0044803074C8B00488B5008'),
            (0x2D36573,'FFD0488B0DAC6F2E0A'),(0x2D36924,'FF907003000048895D40448965488B452C'),
            (0x2D36442,'8BD0488D4D30'),(0x2D365F6,'4C8BE04C63C085C0'),
            (0x2D36526,'4585F60F884E040000'),(0x2D368E2,'4585E40F889F000000'))})
        for rva in (0x2D363D4,0x2D3641D,0x2D36468,0x2D365E9):self.parts[rva]=bytes.fromhex('B90B000000488BD6')
        self.parts[0x2D36994]=bytes.fromhex('C564D302CF64D302D664D302E264D302EC64D302D664D302F664D3029266D302A266D302B266D3021567D3022567D302B266D302E967D302')
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_virtual_slot_address_and_discarded_read_result(self):
        result=stream_carrier_consumer(self.pe,source='fixture.dll')
        self.assertEqual(result['dispatcher']['slotBaseOffset']+35*16,0x370)
        self.assertIn('without testing returned EAX',result['boundary'])

    def test_mutated_truncated_and_trailing_windows(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):
                    stream_carrier_consumer(self.pe,source='fixture.dll')
            self.parts[rva]=good


class ModuleMethodsTests(unittest.TestCase):
    def setUp(self):
        self.pointer=0
        self.method=SimpleNamespace(declaring_type=0,name_index='DeserializeFromJson',token=0x06000001)
        self.md=SimpleNamespace(methods=[self.method],types=['Beyond.Resource.ResourceManager'],
            images=[SimpleNamespace(name_index='Common.Beyond.dll')],string=lambda x:x,type_full_name=lambda x:x)
        self.pe=SimpleNamespace(image_base=0x180000000,u32_at_va=lambda va:1,u64_at_va=lambda va:0x200,
                                bytes_at_va=lambda va,size:struct.pack('<Q',self.pointer))

    def decode(self):
        return module_methods(self.pe,self.md,{'Common.Beyond.dll':0x100},[0],
            [(0,'Beyond.Resource.ResourceManager','DeserializeFromJson',None)],
            source='fixture.dll',expected_image='Common.Beyond.dll')

    def test_generic_definition_null_slot_preserved(self):
        self.assertEqual(self.decode()[0]['pointerVa'],0)

    def test_wrong_slot_or_image_rejected(self):
        self.pointer=0x180000100
        with self.assertRaises(ContextError):self.decode()
        self.pointer=0
        self.md.images[0].name_index='Wrong.dll'
        with self.assertRaises(ContextError):self.decode()

    def test_token_not_global_index(self):
        self.method.token=0x06000002
        with self.assertRaises(ContextError):self.decode()


class ResourceCarrierConsumerTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in
                    ((0x3B18966,0x3B677B0),(0x3B67C9C,0x2DA4260),
                     (0x3B67CBB,0x3F300),(0x3B67CD3,0x1F0450))}
        self.parts.update({rva:bytes.fromhex(raw) for rva,raw in (
            (0x3B188B5,'483972387508488BCAE8CD6653FC'),
            (0x3B1896B,'488B9C249800000048899C24A0000000'),
            (0x3B67CA6,'B9050000004C8B8C24080100004C8D442440488BD0'),
            (0x3B67CC0,'8B9C2484000000899C2410010000488D4C2430'),
            (0x3B67CEB,'8BC34881C4C0000000415F415E415D415C5F5E5BC3'))})
        self.parts[0x3B67D18]=struct.pack('<7I',0x3B67A26,0x3B67A35,0x3B67A44,0x3B67AA7,
                                        0x3B67AB6,0x3B67A44,0x3B67B79)
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_conditional_carrier_not_eof(self):
        result=resource_carrier_consumers(self.pe,source='fixture.dll')
        self.assertEqual(len(result['edges']),4)
        self.assertEqual(result['inner']['counterOffset'],0x44)
        self.assertIn('EAX is discarded',result['outer']['boundary'])

    def test_negative_instruction_and_switch_windows(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):
                    resource_carrier_consumers(self.pe,source='fixture.dll')
            self.parts[rva]=good

    def test_initialization_branch_polarity(self):
        self.parts[0x3B188B5]=bytes.fromhex('483972387408488BCAE8CD6653FC')
        with self.assertRaises(ContextError) as caught:resource_carrier_consumers(self.pe,source='fixture.dll')
        self.assertEqual(caught.exception.diagnostics['offset'],0x3B188B5)


class GenericMethodCandidateTests(unittest.TestCase):
    def decode(self,raw=None,count=2,specs=None):
        if raw is None:raw=struct.pack('<8i',1,2,3,-1,0,99,99,99)
        return generic_method_candidates(raw,count,4,{1} if specs is None else specs,
                                         5,6,source='fixture.dll',offset=0x100)

    def test_normal_and_opaque_nonselected_triple(self):
        rows=self.decode()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['indices'],[2,3,-1])
        self.assertEqual(rows[0]['va'],0x100)

    def test_truncated_and_trailing(self):
        raw=struct.pack('<8i',1,2,3,-1,0,99,99,99)
        for bad in (raw[:-1],raw+b'!'):
            with self.subTest(length=len(bad)),self.assertRaises(ContextError):self.decode(bad)

    def test_bad_counts_and_selection(self):
        for count in (-1,True,1_000_001,1):
            with self.subTest(count=count),self.assertRaises(ContextError):self.decode(count=count)
        for selected in ({-1},{4},{True}):
            with self.subTest(selected=selected),self.assertRaises(ContextError):self.decode(specs=selected)

    def test_unselected_key_still_bounded(self):
        with self.assertRaises(ContextError) as caught:
            self.decode(struct.pack('<8i',1,2,3,-1,4,0,0,-1))
        self.assertEqual(caught.exception.diagnostics['offset'],0x110)

    def test_bad_selected_triples_report_exact_field(self):
        for triple,offset in (((-1,3,-1),0x104),((5,3,-1),0x104),
                              ((2,6,-1),0x108),((2,3,0),0x10C)):
            with self.subTest(triple=triple),self.assertRaises(ContextError) as caught:
                self.decode(struct.pack('<4i',1,*triple),count=1)
            self.assertEqual(caught.exception.diagnostics['offset'],offset)

    def test_multiple_candidates_preserved(self):
        raw=struct.pack('<8i',1,2,3,-1,1,4,5,-1)
        self.assertEqual([r['tableIndex'] for r in self.decode(raw)],[0,1])
        self.assertEqual(self.decode(raw,specs={3}),[])

    def test_overflowing_address(self):
        with self.assertRaises(ContextError):
            generic_method_candidates(bytes(16),1,1,set(),1,1,source='fixture',offset=(1<<64)-8)


class SkillResourceContextTests(unittest.TestCase):
    def setUp(self):
        self.specs=[(0,-1,-1)]*621386
        for i,row in ((621380,(248580,-1,16656)),(621385,(248574,-1,16656)),
                      (521437,(248580,-1,75)),(521443,(248574,-1,75))):self.specs[i]=row
        self.raw_specs=b''.join(struct.pack('<3i',*row) for row in self.specs)
        def instance(index,raw):
            obj=SimpleNamespace(index=index,record_va=0x900,arguments=[SimpleNamespace(
                raw_type_record_hex=raw,type_pointer_va=0xA00)])
            obj.as_dict=lambda:{'index':index}
            return obj
        self.instances={16656:instance(16656,'64230000000000000000120000000000'),
                        75:instance(75,'068E00000000000000001C0000000000')}
        self.raw=struct.pack('<8i',521437,0,0,-1,521443,1,1,-1)
        self.pointers={0x300:0x1836A7AD0,0x308:0x1845BA810,0x400:0x180000100,0x408:0x180000200}
        self.pe=SimpleNamespace(image_base=0x180000000,u64_at_va=self.pointers.__getitem__)
        self.reg={'methodSpecs':'0x1000','genericMethodTable':'0x2000','genericMethodTableCount':2}
        self.code={'genericMethodPointersCount':2,'invokerPointersCount':2,
                   'genericMethodPointers':'0x300','invokerPointers':'0x400'}

    def run_probe(self):
        with patch('scripts.game_data.il2cpp_context_audit.named_top_level_type',return_value={'typeDefinitionIndex':9060}), \
             patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[
                 {'token':0x06001251,'slotVa':0},{'token':0x0600124B,'slotVa':8}]):
            return skill_resource_context(self.pe,SimpleNamespace(buf=b''),{},[],
                SimpleNamespace(resolve=self.instances.__getitem__),self.reg,self.code,
                self.specs,self.raw_specs,self.raw,source='fixture.dll')

    def test_static_candidates_not_selected_dispatch(self):
        result=self.run_probe()
        self.assertEqual(len(result['codeCandidates']),2)
        self.assertIn('Preserve both terminal candidates',result['boundary'])

    def test_wrong_same_named_type(self):
        self.instances[16656].arguments[0].raw_type_record_hex='8C1F0000000000000000120000000000'
        with self.assertRaises(ContextError):self.run_probe()

    def test_wrong_concrete_method_context(self):
        self.specs[621380]=(248580,-1,75)
        with self.assertRaises(ContextError):self.run_probe()

    def test_null_or_wrong_code_pointer(self):
        for pointer in (0,0x180000100):
            self.pointers[0x300]=pointer
            with self.subTest(pointer=pointer),self.assertRaises(ContextError):self.run_probe()

    def test_unexpected_extra_candidate_not_silently_selected(self):
        self.raw+=self.raw[:16]
        self.reg['genericMethodTableCount']=3
        with self.assertRaises(ContextError):self.run_probe()


class SerializerReturnConsumerTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:b'\xe8'+struct.pack('<i',target-rva-5) for rva,target in
                    ((0x970BFE1,0x970C4A8),(0x97112AB,0x970C4A8),(0x971179A,0x970C4A8),(0x97112BF,0x51D80))}
        self.parts.update({0x970BFE6:bytes.fromhex('488B4424504883C448C3'),
                           0x97112B0:bytes.fromhex('4C63C0B920000000448D49E1488BD7'),
                           0x971179F:bytes.fromhex('488B742430488D8C24A0000000')})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_selected_edges_and_non_eof_boundary(self):
        result=serializer_return_consumers(self.pe,source='fixture.dll')
        self.assertEqual(len(result['edges']),4)
        self.assertEqual(len(result['postCallWindows']),3)
        self.assertIn('discarded without comparison',result['objectReturnWrapper']['boundary'])

    def test_mutated_truncated_and_trailing_windows(self):
        for rva,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=bad
                with self.subTest(rva=rva,length=len(bad)),self.assertRaises(ContextError):
                    serializer_return_consumers(self.pe,source='fixture.dll')
            self.parts[rva]=good

    def test_target_change_reports_instruction_offset(self):
        self.parts[0x970BFE1]=b'\xe8'+struct.pack('<i',0)
        with self.assertRaises(ContextError) as caught:serializer_return_consumers(self.pe,source='fixture.dll')
        self.assertEqual(caught.exception.diagnostics['offset'],0x970BFE1)


class ReaderConstructionTests(unittest.TestCase):
    def setUp(self):
        methods=[None]*428428
        pointers=bytearray(80*8)
        for index,name,token,rva in ((428422,'get_Consumed',0x0600004B,0x4A46420),
                                      (428423,'get_Remaining',0x0600004C,0x4A655D0),
                                      (428426,'.ctor',0x0600004F,0x970AD30),
                                      (428427,'.ctor',0x06000050,0x3B67E30)):
            methods[index]=SimpleNamespace(declaring_type=0,name_index=name,token=token)
            struct.pack_into('<Q',pointers,((token&0xFFFFFF)-1)*8,0x180000000+rva)
        self.parts={0x200:bytes(pointers),0x180000000+0x4A46420:bytes.fromhex('8B4144C3'),
                    0x180000000+0x4A655D0:bytes.fromhex('48635144488B4118482BC2C3')}
        for rva,target in ((0x970AE04,0x8381FF0),(0x970AE34,0x838223C),(0x970AE4C,0x3F779C0),
                           (0x970C5BB,0x3B67E30),(0x970C605,0x3F300),(0x970C0FD,0x970AD30)):
            self.parts[0x180000000+rva]=b'\xe8'+struct.pack('<i',target-rva-5)
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va],
                                u32_at_va=lambda va:80,u64_at_va=lambda va:0x200)
        self.md=SimpleNamespace(methods=methods,types=[object()],images=[SimpleNamespace(name_index='MemoryPack.dll')],
                                string=lambda value:value,type_full_name=lambda value:'MemoryPack.MemoryPackReader')

    def decode(self):
        return reader_construction(self.pe,self.md,{'MemoryPack.dll':0x100},[0],source='fixture.dll')

    def test_identity_and_conditional_boundary(self):
        row=self.decode()
        self.assertEqual([r['slot'] for r in row['methods']],[74,75,78,79])
        self.assertEqual(row['accessors']['consumedOffset'],0x44)
        self.assertIn('Do not prune',row['boundary'])

    def test_wrong_image_or_method_identity(self):
        self.md.images[0].name_index='Unrelated.dll'
        with self.assertRaises(ContextError):self.decode()
        self.md.images[0].name_index='MemoryPack.dll'
        self.md.methods[428422].token=0x0600004C
        with self.assertRaises(ContextError):self.decode()

    def test_bad_pointer_or_leaf(self):
        good=self.parts[0x200]
        self.parts[0x200]=bytes(len(good))
        with self.assertRaises(ContextError):self.decode()
        self.parts[0x200]=good
        key=0x180000000+0x4A46420
        for raw in (b'',bytes.fromhex('8B4140C3'),bytes.fromhex('8B4144C390')):
            self.parts[key]=raw
            with self.assertRaises(ContextError):self.decode()


class MethodTokenPointerTests(unittest.TestCase):
    def decode(self,token=0x06000002,pointers=None,offset=0x100):
        return method_token_pointer(token,struct.pack('<QQ',0x300,0x200) if pointers is None else pointers,
                                     source='fixture.dll',offset=offset)

    def test_rid_not_address_or_global_order(self):
        row=self.decode()
        self.assertEqual((row['slot'],row['slotVa'],row['pointerVa']),(1,0x108,0x200))
        self.assertEqual(self.decode(0x06000001,bytes(8))['pointerVa'],0)

    def test_truncated_trailing_out_of_range(self):
        for pointers in (b'',bytes(7),bytes(8),bytes(15),bytes(17)):
            with self.assertRaises(ContextError):self.decode(pointers=pointers)

    def test_bad_tokens_and_extent(self):
        for token in (True,-1,0x06000000,0x02000001,0x06000003,0x106000001):
            with self.assertRaises(ContextError):self.decode(token=token)
        for offset in (-1,True,(1<<64)-8):
            with self.assertRaises(ContextError):self.decode(offset=offset)


class ReaderCursorConsumerTests(unittest.TestCase):
    def setUp(self):
        pairs=((0x4E3B229,0x970915C),(0x4E3B23C,0x5AD2140),(0x5AD21C3,0x838223C),
               (0x838228D,0x83761A0),(0x5AD21F5,0x837EC68),(0x5AD221C,0x8381FF0),
               (0x8382045,0x8375FBC),(0x5AD2236,0x3F779C0),(0x9709289,0x837EC68),
               (0x97092D8,0x8381FF0),(0x9709421,0x3F779C0),(0x381FAD4,0x2DA4770),
               (0x381FB1D,0x3F300))
        self.parts={rva:bytes([0xE9 if rva==0x838228D else 0xE8])+struct.pack('<i',target-rva-5)
                    for rva,target in pairs}
        self.parts[0x3F779C0]=bytes.fromhex('837908007404488B01C333C0C3')
        self.pe=SimpleNamespace(image_base=0x180000000,
                                bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_expected_edges_and_evidence_boundary(self):
        row=reader_cursor_consumers(self.pe,source='fixture.dll')
        self.assertEqual(len(row['edges']),13)
        self.assertTrue(row['advance']['normalReturn'])
        self.assertIn('Keep both terminal candidates',row['boundary'])

    def test_mutated_target_and_opcode(self):
        for raw in (b'\xe8\0\0\0\0', b'\xe9'+self.parts[0x4E3B229][1:]):
            self.parts[0x4E3B229]=raw
            with self.assertRaises(ContextError): reader_cursor_consumers(self.pe,source='fixture.dll')

    def test_truncated_trailing_and_leaf_mutation(self):
        for rva in (0x4E3B229,0x3F779C0):
            good=self.parts[rva]
            for raw in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[rva]=raw
                with self.assertRaises(ContextError): reader_cursor_consumers(self.pe,source='fixture.dll')
            self.parts[rva]=good


class RelativeBranchTests(unittest.TestCase):
    def test_forward_call_backward_jump(self):
        for opcode, displacement in ((0xE8,127),(0xE9,-127)):
            self.assertEqual(relative_branch_target(bytes([opcode])+struct.pack('<i',displacement),
                                                    0x100,source='fixture.dll'),0x105+displacement)

    def test_truncated_trailing_and_indirect(self):
        for raw in (b'', b'\xe8\0\0\0', b'\xe8\0\0\0\0!', b'\xff\0\0\0\0'):
            with self.assertRaises(ContextError): relative_branch_target(raw,0x100,source='fixture.dll')

    def test_address_and_target_bounds(self):
        for address in (-1,True,1<<64,(1<<64)-4):
            with self.assertRaises(ContextError): relative_branch_target(b'\xe8\0\0\0\0',address,source='fixture.dll')
        for address,displacement in ((0,-6),((1<<64)-5,1)):
            with self.assertRaises(ContextError) as caught:
                relative_branch_target(b'\xe9'+struct.pack('<i',displacement),address,source='fixture.dll')
            self.assertEqual(caught.exception.diagnostics['offset'],address)


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
