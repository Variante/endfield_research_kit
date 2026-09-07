import struct
import io
import json
from contextlib import redirect_stderr
import unittest
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
from scripts.game_data.il2cpp_context_audit import vfs_path_format_context
from scripts.game_data.il2cpp_context import literal_record
from scripts.game_data.il2cpp_context_audit import vfs_path_literals
from scripts.game_data.il2cpp_context_audit import vfs_format_item
from scripts.game_data.il2cpp_context_audit import vfs_string_carrier
from scripts.game_data.il2cpp_context_audit import vfs_root_resolver
from scripts.game_data.il2cpp_context_audit import unity_registration_forwarder
from scripts.game_data.il2cpp_context_audit import unity_registration_pair
from scripts.game_data.il2cpp_context_audit import unity_path_return
from scripts.game_data.il2cpp_context_audit import unity_conversion_exports
from scripts.game_data.il2cpp_context_audit import resolver_prefix_query
from scripts.game_data.il2cpp_context_audit import resolver_key_comparison
from scripts.game_data.il2cpp_context_audit import unity_module_lookup
from scripts.game_data.il2cpp_context_audit import unity_loader_input
from scripts.game_data.il2cpp_context_audit import unity_loader_conversion
from scripts.game_data.il2cpp_context_audit import nested_reader_context
from scripts.game_data.il2cpp_context_audit import list_formatter_candidate
from scripts.game_data.il2cpp_context_audit import list_element_dispatch
from scripts.game_data.il2cpp_context_audit import list_element_shared_context, list_element_null_probe
from scripts.game_data.il2cpp_context_audit import list_element_value_flow
from scripts.game_data.il2cpp_context_audit import adapter_conversion_context
from scripts.game_data.il2cpp_context_audit import element_provider_state_flow
from scripts.game_data.il2cpp_context_audit import buff_union_routes
from scripts.game_data.il2cpp_context_audit import buff_ifelse_forwarding
from scripts.game_data.il2cpp_context_audit import buff_ifelse_read_order
from scripts.game_data.il2cpp_context_audit import buff_sequence_read_order
from scripts.game_data.il2cpp_context_audit import buff_tag76_read_order
from unittest.mock import patch


class BuffTag76ReadOrderTests(unittest.TestCase):
    def setUp(self):
        self.base=0x180000000
        self.parts={self.base+at:bytes.fromhex(raw) for at,raw in (
            (0x3F7FD49,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
            (0x3F7FE00,'4080FE050F85635BFD00'),
            (0x3D9BB19,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
            (0x3D9BBD5,'4080FD030F85E0621701'),
            (0x2CA8729,'488B43504863388B733083EE040F885C8CE30148834350048343400483434404897330'),
            (0x2CA874C,'48634344488B4B18482BC8483BCF0F8C528CE30183FFFF743785FF7517'),
            (0x2CA8780,'4533C08BD7488BCB488B5C2430488B7424384883C4205FE974020000'),
            (0x2CA8A97,'4533C9448BC7488BD5488BCEE878F8FFFF488BE885FF7418'),
            (0x2CA8AAF,'8B73302BF70F88B0A4F70148017B50017B40017B44897330'))}
        for at,target in ((0x3F7FDB6,0x2CA8860),(0x3F7FE10,0x2CA88C0),
            (0x3F7FE39,0x2CA86B0),(0x3F7FE5A,0x2CA86B0),(0x3F7FE7B,0x2CA86B0),
            (0x3F7FEA3,0x381F8F0),(0x3D9BBE5,0x2CA8700),
            (0x3D9BC13,0x2CA88C0),(0x3D9BC37,0x2CA8700)):
            self.parts[self.base+at]=b'\xe8'+struct.pack('<i',target-at-5)
        self.parts[self.base+0x3F7FE96]=bytes.fromhex('488B15EB970B09')
        self.parts[self.base+0xD039688]=struct.pack('<Q',(6<<29)|(610878<<1)|1)
        self.parts[0x1000+610878*12]=struct.pack('<iii',428462,-1,62664)
        self.parts[0x18D2534A8]=struct.pack('<QQ',0x2000,0x3000)+bytes(16)
        self.parts[0x2000]=bytes.fromhex('91920000000000000000120000000000')
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=lambda va,n:self.parts[va])
        self.md=SimpleNamespace(methods=[None]*428463,types=list(range(37522)),
            type_full_name=lambda t:{37521:'System.Collections.Generic.List`1',177:'Beyond.Blackboard+BlackboardString'}[t])
        self.reg={'methodSpecs':'0x1000','methodSpecsCount':627868,'genericInstsCount':73902}
        self.arg=SimpleNamespace(raw_type_record_hex='A834258D010000000000150000000000',type_pointer_va=0x18C3B11D8)
        self.element=SimpleNamespace(raw_type_record_hex='B1000000000000000000120000000000')
        self.inst=SimpleNamespace(arguments=[self.arg],as_dict=lambda:{'index':62664})
        self.nested=SimpleNamespace(index=17007,arguments=[self.element],as_dict=lambda:{'index':17007})
        self.table=SimpleNamespace(resolve=lambda i:self.inst if i==62664 else None,
            resolve_pointer=lambda p:self.nested if p==0x3000 else None)

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return buff_tag76_read_order(self.pe,self.md,self.reg,self.table,{},[],source='fixture.dll')

    def test_order_context_and_encoding_boundary(self):
        row=self.decode()
        self.assertEqual(row['listCarrier']['baseDefinitionIndex'],37521)
        self.assertEqual(row['elementInstantiation']['index'],17007)
        self.assertEqual([r['targetRva'] for r in row['orderedCalls'][-3:]],[0x2CA8700,0x2CA88C0,0x2CA8700])
        self.assertIn('structural-only',row['boundary'])

    def test_truncated_trailing_and_mutated_windows_records(self):
        for va,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[va]=bad
                with self.subTest(va=va,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[va]=good

    def test_bad_count_wrong_element_and_ambiguous_pointer(self):
        self.reg['methodSpecsCount']=610878
        with self.assertRaises(ContextError):self.decode()
        self.reg['methodSpecsCount']=627868
        self.element.raw_type_record_hex='00'*16
        with self.assertRaises(ContextError):self.decode()
        self.element.raw_type_record_hex='B1000000000000000000120000000000'
        # The real registered-pointer join must reject duplicate matches;
        # its exact ambiguity diagnostics are covered by GenericInstantiation tests.
        def ambiguous(p):raise ContextError('fixture.dll',p,'unique pointer',[1,2])
        self.table.resolve_pointer=ambiguous
        with self.assertRaises(ContextError):self.decode()


class BuffSequenceReadOrderTests(unittest.TestCase):
    def setUp(self):
        self.base=0x180000000
        self.parts={self.base+at:bytes.fromhex(raw) for at,raw in (
            (0x39C6A69,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
            (0x39C6B06,'488B43500FB6308B7B3083EF017911BA01000000488BCBE81EB6100284C0750D48FF4350FF4340FF4344897B304080FEFF7516'),
            (0x39C6B82,'4080FE030F85DD030000'),
            (0x39C6BF8,'488B43508B28448B73304183EE047911BA04000000488BCBE82BB5100284C07511488343500483434004834344044489733048634344488B4B18482BC84863C5483BC80F8C78030000'),
            (0x39C6D4D,'488B4738488B4818E806D53DFF4C8BF085ED0F8EB6000000'),
            (0x39C6D98,'4D8B16488BD34863C6498BCE4883C0044D8B8A980100004C8D04C741FF9290010000FFC63BF57CB0EB59'),
            (0x39C6EA2,'488B43500FB6288B7B3083EF017911BA01000000488BCBE882B2100284C0750D48FF4350FF4340FF4344897B30'),
            (0x39C6EE5,'4084ED0F95C0884119'),
            (0x39C6F07,'488B43500FB6288B7B3083EF017911BA01000000488BCBE81DB2100284C0750D48FF4350FF4340FF4344897B30'),
            (0x39C6F47,'4084ED4C8B6C2428488B6C24680F95C04C8B742420884118'))}
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=lambda va,n:self.parts[va])

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return buff_sequence_read_order(self.pe,None,{},[],source='fixture.dll')

    def test_conditional_structure_retains_unknown_elements(self):
        self.assertIn('not serialized element width',self.decode()['boundary'])

    def test_truncated_trailing_and_mutated_windows(self):
        for va,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[va]=bad
                with self.subTest(va=va,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[va]=good


class BuffIfElseReadOrderTests(unittest.TestCase):
    def setUp(self):
        self.base=0x180000000
        self.parts={self.base+at:bytes.fromhex(raw) for at,raw in (
            (0x3773699,'4533C0488BD3488BCF488B5C24304883C4205FE9AF090000'),
            (0x3774093,'837B30010F8C089A6B01488B43500FB6288B733083EE010F880B9A6B0148FF4350FF4340FF43448973304080FDFF0F8482010000'),
            (0x37740FA,'4080FD080F85D1996B01'),
            (0x2CA88CF,'83793001488BD90F8CBCA5F701488B43500FB6308B7B3083EF010F88BCA5F70148FF4350FF4340FF4344897B30'),
            (0x2CA8901,'4084F6488B7424380F95C04883C4205FC3'),
            (0x2CA86BF,'83793004488BD90F8C9EA7F701488B43508B308B7B3083EF040F889FA7F70148834350048343400483434404897B30'))}
        for at,target in ((0x377410A,0x2CA88C0),(0x3774135,0x2CA86B0),(0x3774159,0x2CA86B0),
            (0x377417D,0x2CA86B0),(0x37741A1,0x2CA88C0),(0x37741CA,0x2DA5C90),
            (0x37741F3,0x2DA5C90),(0x377421C,0x2DA5C90)):
            self.parts[self.base+at]=b'\xe8'+struct.pack('<i',target-at-5)
        for at in (0x37741BD,0x37741E6,0x377420F):
            self.parts[self.base+at]=b'\x48\x8b\x15'+struct.pack('<i',0xCFF4E68-at-7)
        self.parts[self.base+0xCFF4E68]=struct.pack('<Q',(6<<29)|(619962<<1)|1)
        self.parts[0x1000+619962*12]=struct.pack('<iii',428464,-1,16408)
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=lambda va,n:self.parts[va])
        self.md=SimpleNamespace(methods=[None]*428465,types=[None]*9203,type_full_name=lambda t:'Beyond.Gameplay.Core.SequenceActionData')
        self.reg={'methodSpecs':'0x1000','methodSpecsCount':627868,'genericInstsCount':73902}
        self.arg=SimpleNamespace(raw_type_record_hex='F2230000000000000000120000000000')
        self.instance=SimpleNamespace(arguments=[self.arg],as_dict=lambda:{'index':16408})
        self.table=SimpleNamespace(resolve=lambda i:self.instance if i==16408 else None)

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return buff_ifelse_read_order(self.pe,self.md,self.reg,self.table,{},[],source='fixture.dll')

    def test_order_and_nested_widths_stay_unknown(self):
        row=self.decode()
        self.assertEqual([r['fastSerializedWidth'] for r in row['orderedCalls']],[1,4,4,4,1,None,None,None])
        self.assertEqual(len({r['cellVa'] for r in row['nestedOperands']}),1)

    def test_truncated_trailing_and_corrupted_evidence(self):
        for va,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[va]=bad
                with self.subTest(va=va,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[va]=good

    def test_wrong_nested_type_and_table_bounds(self):
        self.md.types=[]
        with self.assertRaises(ContextError):self.decode()
        self.md.types=[None]*9203
        self.arg.raw_type_record_hex='00'*16
        with self.assertRaises(ContextError):self.decode()
        self.arg.raw_type_record_hex='F2230000000000000000120000000000'
        self.reg['methodSpecsCount']=619962
        with self.assertRaises(ContextError):self.decode()


class BuffIfElseForwardingTests(unittest.TestCase):
    def setUp(self):
        self.base=0x180000000
        self.parts={self.base+at:bytes.fromhex(raw) for at,raw in (
            (0x30E2DC,'488B15D530DD0CE908165103'),
            (0xA1EA7C,'4C8B053D296C0CE974AC7C08'),
            (0x4E67AA1,'4C8B0518992708488BD3E8CC6FBBFB90E9345FAAFE'),
            (0x91E96FC,'48895C24084889742410574883EC204983783800498BD8488BFA488BF17508488BCBE86D58E6F64C8B4338488BD7488BCE4D8B00488B5C2430488B7424384883C4205FE93C6812F7'),
            (0x30FF80,'E90BFFA303'),
            (0x3D4FE90,'48895C24084889742410574883EC204983783800498BD8488BFA488BF17444488B0D3AF7390983B9E0000000007451488B4338488B08E8954305FF4885C07413B9050000004C8BCF4C8BC6488BD0E81DF42EFC488B5C2430488B7424384883C4205FC3488D0DF6F63909E861132FFC48837B380075A9488BCBE882F02FFCEB9FE8AB632DFCEBA8'))}
        for at,index,definition in ((0x30E2DC,614208,428462),(0xA1EA7C,618298,428461)):
            cell=self.base+at+7+struct.unpack_from('<i',self.parts[self.base+at],3)[0]
            self.parts[cell]=struct.pack('<Q',(6<<29)|(index<<1)|1)
            self.parts[0x1000+index*12]=struct.pack('<iii',definition,-1,24608)
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=lambda va,n:self.parts[va][:7] if n==7 else self.parts[va])
        self.md=SimpleNamespace(methods=[None]*428463)
        self.reg={'methodSpecs':'0x1000','methodSpecsCount':627868,'genericInstsCount':73902}
        self.argument=SimpleNamespace(raw_type_record_hex='233F0000000000000000120000000000')
        self.instance=SimpleNamespace(arguments=[self.argument],as_dict=lambda:{'index':24608})
        self.table=SimpleNamespace(resolve=lambda index:self.instance if index==24608 else None)

    def decode(self):
        return buff_ifelse_forwarding(self.pe,self.md,self.reg,self.table,source='fixture.dll')

    def test_distinct_contexts_shared_argument_and_no_eof_claim(self):
        row=self.decode()
        self.assertEqual([r['methodDefinition'] for r in row['contexts']],[428462,428461])
        self.assertIn('remain unresolved',row['boundary'])

    def test_truncated_trailing_and_corrupted_evidence(self):
        for va,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[va]=bad
                with self.subTest(va=va,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[va]=good

    def test_bounds_and_wrong_type_argument(self):
        self.reg['methodSpecsCount']=614208
        with self.assertRaises(ContextError):self.decode()
        self.reg['methodSpecsCount']=627868
        self.argument.raw_type_record_hex='00'*16
        with self.assertRaises(ContextError):self.decode()


class BuffUnionRouteTests(unittest.TestCase):
    def setUp(self):
        self.base=0x180000000
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x390D974,'488D5424384533C06689742438488BCFE8F7FEFFFF84C00F8422BD55010FB774243881FE9F0100000F87E0BC5501488D1557266FFC8B8CB2185391034803CAFFE1'),
            (0x390D8D2,'4080FEFA731C66418936B001'),
            (0x390D8F4,'754B837B30020F8C208A5501488B43500FB700664189068B7B3083EF020F881F8A550148834350028343400283434402897B30EBB3'),
            (0x390D941,'33C066418906EB95'),
            (0x4E66320,'4533C0BA02000000488BCBE82C2E8A0490E9CE75AAFE'),
            (0x4E696B3,'48893333D2E92543AAFE'),
            (0x417E68A,'488B0DE70FF20833D2E85872C2FE488BCF488BD8E87D4DE8FB4C8B0D9E87E70841B8C9000000488BD3488BCFE8B1EE18FC'),
            (0x417E4D1,'488B0D3018F20833D2E81174C2FE488BCF488BD8E8364FE8FB4C8B0D5789E70841B8C0000000488BD3488BCFE86AF018FC'),
            (0x390E160,'488B1529B57209488B0BE8B1566FFC488BCF4885C00F852F905501488B1576357D09E8690111FD488903488BD0E950F8FFFF'),
            (0x390DA8A,'488B15FF1B7909488B0BE8875D6FFC488BCF4885C00F85FC9F5501488B150C397D09E82B08A0FC488903488BD0E926FFFFFF'),
            (0x3910A00,'488B1509F37809488B0BE8112E6FFC488BCF4885C00F859B6F5501488B153E097D09E865DF10FD488903488BD0E9B0CFFFFF'),
            (0x39149EA,'488B150F5A7209488B0BE827EE6EFC488BCF4885C00F856B215501488B1554D17C09E8C39310FD488903488BD0E9C68FFFFF'),
            (0x390DCB0,'488B15B1936F09488B0BE8615B6FFC488BCF4885C00F8595A35501488B15E6307D09E8451011FD488903488BD0E900FDFFFF'),
            (0x390DC1A,'488B1527307309488B0BE8F75B6FFC488BCF4885C00F8571915501488B1514387D09E8130311FD488903488BD0E996FDFFFF'),
            (0x390DED6,'488B1563997009488B0BE83B596FFC488BCF4885C00F85F4A75501488B1588297D09E8CF1211FD488903488BD0E9DAFAFFFF'),
            (0x390DC4C,'488B15C5287909488B0BE8C55B6FFC488BCF4885C00F85539C5501488B15AA357D09E8050C11FD488903488BD0E964FDFFFF'),
            (0x390E354,'488B15E5C97209488B0BE8BD546FFC488BCF4885C00F85E38A5501488B1572317D09E881FC10FD488903488BD0E95CF6FFFF'),
            (0x390DA58,'488B1541B77809488B0BE8B95D6FFC488BCF4885C00F853B9A5501488B15A6357D09E86908A0FC488903488BD0E958FFFFFF'),
            (0x390E1C4,'488B159DC67209488B0BE84D566FFC488BCF4885C00F85888C5501488B1512337D09E8F9FD10FD488903488BD0E9ECF7FFFF'),
            (0x390E0FC,'488B158DC67209488B0BE815576FFC488BCF4885C00F85A48D5501488B158A337D09E839FF10FD488903488BD0E9B4F8FFFF'),
            (0x390DCE2,'488B15C7CD7209488B0BE82F5B6FFC488BCF4885C00F85F18D5501488B15943D7D09E8770011FD488903488BD0E9CEFCFFFF'),
            (0x390E994,'488B158DAB7209488B0BE87D4E6FFC488BCF4885C00F8525885501488B152A2D7D09E859F910FD488903488BD0E91CF0FFFF'),
            (0x390DA29,'488B15B0BF7809488B0BE8E85D6FFC488BCF4885C00F854C9E5501488B15F5377D09E8A408A0FC488903488BD0EB8A'),
            (0x390DDDC,'488B15B5BF7209488B0BE8355A6FFC488BCF4885C00F8531925501488B15DA377D09E89D0311FD488903488BD0E9D4FBFFFF'),
            (0x390E674,'488B1585277309488B0BE89D516FFC488BCF4885C00F855E8C5501488B15BA307D09E851FD10FD488903488BD0E93CF3FFFF'),
            (0x390E098,'488B1569C97209488B0BE879576FFC488BCF4885C00F85C98D5501488B150E347D09E86DFF10FD488903488BD0E918F9FFFF'),
            (0x390E0CA,'488B1597997809488B0BE847576FFC488BCF4885C00F8595825501488B15BC3C7D09E81FF710FD488903488BD0E9E6F8FFFF'),
            (0x390DB20,'488B1559227809488B0BE8F15C6FFC488BCF4885C00F851B9A5501488B155E357D09E87107A0FC488903488BD0E990FEFFFF'),
            (0x390D9B5,'488B1544AF7809488B0BE85C5E6FFC488BCF4885C00F858A9C5501488B1559377D09E83009A0FC488903488BD0488BCBE806CF72FC488B5C2430488B7424404883C4205FC3'),
            (0x390E44E,'488B1503B87209488B0BE8C3536FFC488BCF4885C00F85248B5501488B1598317D09E8E3FC10FD488903488BD0E962F5FFFF'),
            (0x390DDAA,'488B15179C7109488B0BE8675A6FFC488BCF4885C00F856EB25501488B151C277D09E8A31A11FD488903488BD0E906FCFFFF'),
            (0x390E9F8,'488B15C1AD7109488B0BE8194E6FFC488BCF4885C00F854AA45501488B15CE197D09E8D50C11FD488903488BD0E9B8EFFFFF'),
            (0x390EC1E,'488B1563AD7209488B0BE8F34B6FFC488BCF4885C00F856D845501488B15402A7D09E8DFF510FD488903488BD0E992EDFFFF'),
            (0x390E1F6,'488B15037E6F09488B0BE81B566FFC488BCF4885C00F850BA15501488B15882C7D09E8A30C11FD488903488BD0E9BAF7FFFF'),
            (0x390E4B2,'488B15CFA97809488B0BE85F536FFC488BCF4885C00F8535905501488B150C2C7D09E80B0111FD488903488BD0E9FEF4FFFF'),
            (0x390E804,'488B15D5766F09488B0BE80D506FFC488BCF4885C00F85E89A5501488B159A267D09E8650611FD488903488BD0E9ACF1FFFF'),
            (0x390DF9E,'488B15E32F7309488B0BE873586FFC488BCF4885C00F859D925501488B15E0367D09E8AF0311FD488903488BD0E912FAFFFF'),
            (0x390DF6C,'488B152D237909488B0BE8A5586FFC488BCF4885C00F855D995501488B156A337D09E8150911FD488903488BD0E944FAFFFF'),
            (0x390EB88,'488B1501227309488B0BE8894C6FFC488BCF4885C00F8535875501488B15B62B7D09E825F810FD488903488BD0E928EEFFFF'),
            (0x390E5DE,'488B15B38E7109488B0BE833526FFC488BCF4885C00F85A3AA5501488B15B01E7D09E8C31211FD488903488BD0E9D2F3FFFF'),
            (0x390E73C,'488B15DD277309488B0BE8D5506FFC488BCF4885C00F85EA8A5501488B15522F7D09E8F9FB10FD488903488BD0E974F2FFFF'),
            (0x390F4B6,'488B158BA47209488B0BE85B436FFC488BCF4885C00F85C07B5501488B15B0217D09E83BED10FD488903488BD0E9FAE4FFFF'),
            (0x390E8FE,'488B1543677009488B0BE8134F6FFC488BCF4885C00F8595A05501488B1500217D09E8B70A11FD488903488BD0E9B2F0FFFF'),
            (0x390E12E,'488B150B9F7109488B0BE8E3566FFC488BCF4885C00F8510AE5501488B15E8227D09E8A71611FD488903488BD0E982F8FFFF'),
            (0x390E4E4,'488B15F5B57209488B0BE82D536FFC488BCF4885C00F853E8B5501488B15C2307D09E8ADFC10FD488903488BD0E9CCF4FFFF'),
            (0x390F2C2,'488B1507AC7209488B0BE84F456FFC488BCF4885C00F8515795501488B1534287D09E857EB10FD488903488BD0E9EEE6FFFF'),
            (0x390EE44,'488B159D676F09488B0BE8CD496FFC488BCF4885C00F857E965501488B155A217D09E8F90111FD488903488BD0E96CEBFFFF'),
            (0x390E228,'488B1529A97809488B0BE8E9556FFC488BCF4885C00F8528935501488B15462E7D09E8010411FD488903488BD0E988F7FFFF'),
            (0x390E642,'488B15BF147909488B0BE8CF516FFC488BCF4885C00F85F0935501488B15AC2C7D09E89B0311FD488903488BD0E96EF3FFFF'),
            (0x390D9FA,'488B1587756F09488B0BE8175E6FFC488BCF4885C00F85F6AB5501488B15BC2D7D09E8DF08A0FC488903488BD0EBB9'),
            (0x390F25E,'488B152BA67709488B0BE8B3456FFC488BCF4885C00F85D7715501488B15A82B7D09E83FE610FD488903488BD0E952E7FFFF'),
            (0x390F2F4,'488B15551B7309488B0BE81D456FFC488BCF4885C00F851D7F5501488B15AA237D09E829F010FD488903488BD0E9BCE6FFFF'),
            (0x390E6D8,'488B1501237309488B0BE839516FFC488BCF4885C00F858D8C5501488B15DE307D09E8A1FD10FD488903488BD0E9D8F2FFFF'),
            (0x390F038,'488B1591AB7209488B0BE8D9476FFC488BCF4885C00F85217C5501488B15A62B7D09E841EE10FD488903488BD0E978E9FFFF'),
            (0x390F772,'488B1597AF7209488B0BE89F406FFC488BCF4885C00F8519775501488B151C1D7D09E8B7E810FD488903488BD0E93EE2FFFF'),
            (0x390EA5C,'488B151D107909488B0BE8B54D6FFC488BCF4885C00F85C18F5501488B15A2287D09E869FF10FD488903488BD0E954EFFFFF'),
            (0x390E70A,'488B156F577009488B0BE807516FFC488BCF4885C00F857CA45501488B15F4237D09E81F0E11FD488903488BD0E9A6F2FFFF'),
            (0x390DB52,'488B159FF27809488B0BE8BF5C6FFC488BCF4885C00F85B9A25501488B15FC307D09E8831011FD488903488BD0E95EFEFFFF'),
            (0x390E25A,'488B158F1E7909488B0BE8B7556FFC488BCF4885C00F8502975501488B154C307D09E86F0611FD488903488BD0E956F7FFFF'),
            (0x390F57E,'488B15CBA57209488B0BE893426FFC488BCF4885C00F85B97A5501488B1520207D09E81FEC10FD488903488BD0E932E4FFFF'),
            (0x390DB84,'488B15552E7809488B0BE88D5C6FFC488BCF4885C00F85158C5501488B157A3D7D09E889FF10FD488903488BD0E92CFEFFFF'),
            (0x390F9CA,'488B15DF837109488B0BE8473E6FFC488BCF4885C00F8578965501488B15DC0A7D09E8B3FE10FD488903488BD0E9E6DFFFFF'),
            (0x390ED7C,'488B15051F7309488B0BE8954A6FFC488BCF4885C00F85E9845501488B15DA297D09E80DF610FD488903488BD0E934ECFFFF'),
            (0x390E516,'488B15CB896F09488B0BE8FB526FFC488BCF4885C00F85D79A5501488B1598277D09E8AF0711FD488903488BD0E99AF4FFFF'),
            (0x390DEA4,'488B15F5C37209488B0BE86D596FFC488BCF4885C00F857A905501488B1582367D09E82D0211FD488903488BD0E90CFBFFFF'),
            (0x390F70E,'488B1593AA7809488B0BE803416FFC488BCF4885C00F8532745501488B1550247D09E887E610FD488903488BD0E9A2E2FFFF'),
            (0x390F86C,'488B1505367009488B0BE8A53F6FFC488BCF4885C00F854C945501488B1512137D09E87DFD10FD488903488BD0E944E1FFFF'),
            (0x390F5B0,'488B1579A27209488B0BE861426FFC488BCF4885C00F85727B5501488B1556207D09E8D1EC10FD488903488BD0E900E4FFFF'),
            (0x390E480,'488B15D1BF7209488B0BE891536FFC488BCF4885C00F854A8A5501488B15D6307D09E809FC10FD488903488BD0E930F5FFFF'),
            (0x390DE40,'488B1529C27209488B0BE8D1596FFC488BCF4885C00F853F8D5501488B15DE3C7D09E89DFF10FD488903488BD0E970FBFFFF'),
            (0x390E3EA,'488B153F217809488B0BE827546FFC488BCF4885C00F85EE835501488B15DC357D09E877F710FD488903488BD0E9C6F5FFFF'),
            (0x390F358,'488B15399B7809488B0BE8B9446FFC488BCF4885C00F857A815501488B15861D7D09E841F210FD488903488BD0E958E6FFFF'),
            (0x390FF10,'488B1551997209488B0BE801396FFC488BCF4885C00F8527725501488B15E6167D09E889E310FD488903488BD0E9A0DAFFFF'),
            (0x390EB24,'488B150DF37809488B0BE8ED4C6FFC488BCF4885C00F8548A55501488B1562197D09E8890D11FD488903488BD0E98CEEFFFF'),
            (0x390E322,'488B15E7A37109488B0BE8EF546FFC488BCF4885C00F85DDAB5501488B1524217D09E86B1411FD488903488BD0E98EF6FFFF'),
            (0x391035C,'488B153D077309488B0BE8B5346FFC488BCF4885C00F851E705501488B154A147D09E835E110FD488903488BD0E954D6FFFF'),
            (0x390EA2A,'488B15BF8E7109488B0BE8E74D6FFC488BCF4885C00F8596A65501488B15241B7D09E8D70E11FD488903488BD0E986EFFFFF'),
            (0x390FD1C,'488B155D5B7009488B0BE8F53A6FFC488BCF4885C00F85F58B5501488B15120C7D09E851F610FD488903488BD0E994DCFFFF'),
            (0x390E76E,'488B15BBF47809488B0BE8A3506FFC488BCF4885C00F85E5945501488B1548247D09E8CB0311FD488903488BD0E942F2FFFF'),
            (0x390EE76,'488B159BB37209488B0BE89B496FFC488BCF4885C00F8593805501488B15C0267D09E843F210FD488903488BD0E93AEBFFFF'),
            (0x390F54C,'488B1575637009488B0BE8C5426FFC488BCF4885C00F8511925501488B15A2137D09E801FD10FD488903488BD0E964E4FFFF'),
            (0x390DD46,'488B1543477809488B0BE8CB5A6FFC488BCF4885C00F857D895501488B15383B7D09E807FD10FD488903488BD0E96AFCFFFF'),
            (0x390EFA2,'488B1577AE7709488B0BE86F486FFC488BCF4885C00F853F745501488B15A42E7D09E89BE810FD488903488BD0E90EEAFFFF'),
            (0x390E610,'488B1549607009488B0BE801526FFC488BCF4885C00F8537A55501488B151E247D09E8DD0E11FD488903488BD0E9A0F3FFFF'),
            (0x390F1C8,'488B1529157909488B0BE849466FFC488BCF4885C00F85AC715501488B15A62B7D09E839E610FD488903488BD0E9E8E7FFFF'),
            (0x390FA2E,'488B151B0F7309488B0BE8E33D6FFC488BCF4885C00F8572735501488B15F0197D09E817E510FD488903488BD0E982DFFFFF'),
            (0x390EF70,'488B15A1B57209488B0BE8A1486FFC488BCF4885C00F856F7F5501488B15FE257D09E8F5F010FD488903488BD0E940EAFFFF'),
            (0x39105E6,'488B1523437009488B0BE82B326FFC488BCF4885C00F8572845501488B15C0037D09E853EE10FD488903488BD0E9CAD3FFFF'),
            (0x390F614,'488B1525157309488B0BE8FD416FFC488BCF4885C00F85FD7C5501488B15E2207D09E805EE10FD488903488BD0E99CE3FFFF'),
            (0x3910D84,'488B1565627109488B0BE88D2A6FFC488BCF4885C00F857B835501488B15A2F77C09E8B9EB10FD488903488BD0E92CCCFFFF'),
            (0x390F740,'488B1561AD7209488B0BE8D1406FFC488BCF4885C00F852A745501488B15EE237D09E885E610FD488903488BD0E970E2FFFF'),
            (0x390E002,'488B15B7A07809488B0BE80F586FFC488BCF4885C00F852C975501488B159C317D09E85F0711FD488903488BD0E9AEF9FFFF'),
            (0x390FEDE,'488B15E39F7209488B0BE833396FFC488BCF4885C00F8555705501488B1538167D09E80BE210FD488903488BD0E9D2DAFFFF'),
            (0x391000A,'488B158F4A7009488B0BE807386FFC488BCF4885C00F85638A5501488B15840A7D09E853F410FD488903488BD0E9A6D9FFFF'),
            (0x390EF0C,'488B1575A97809488B0BE805496FFC488BCF4885C00F855D855501488B1512217D09E82DF610FD488903488BD0E9A4EAFFFF'),
            (0x390FA60,'488B1559067909488B0BE8B13D6FFC488BCF4885C00F85D27E5501488B151E187D09E8A5EE10FD488903488BD0E950DFFFFF'),
            (0x390E386,'488B15DBB57709488B0BE88B546FFC488BCF4885C00F85C4805501488B15683A7D09E83BF510FD488903488BD0E92AF6FFFF'),
            (0x39107DA,'488B15EFFE7709488B0BE837306FFC488BCF4885C00F8552605501488B15AC117D09E8E7D310FD488903488BD0E9D6D1FFFF'),
            (0x390DAEE,'488B152B736F09488B0BE8235D6FFC488BCF4885C00F85AEAA5501488B15082D7D09E8AF07A0FC488903488BD0E9C2FEFFFF'),
            (0x39100A0,'488B1579267009488B0BE871376FFC488BCF4885C00F856C8C5501488B15A60A7D09E89DF510FD488903488BD0E910D9FFFF'),
            (0x39150C0,'488B1511F26F09488B0BE851E76EFC488BCF4885C00F85483A5501488B159EB97C09E8E5A310FD488903488BD0E9F088FFFF'),
            (0x390EEDA,'488B15B7537009488B0BE837496FFC488BCF4885C00F85439C5501488B157C1B7D09E8D70511FD488903488BD0E9D6EAFFFF'),
            (0x390ECB4,'488B1535A37809488B0BE85D4B6FFC488BCF4885C00F855D885501488B15F2237D09E82DF910FD488903488BD0E9FCECFFFF'),
            (0x390E89A,'488B15F78A7109488B0BE8774F6FFC488BCF4885C00F858FA85501488B156C1C7D09E8D31011FD488903488BD0E916F1FFFF'),
            (0x391038E,'488B15B3907809488B0BE883346FFC488BCF4885C00F851A715501488B15680C7D09E8DBE110FD488903488BD0E922D6FFFF'),
            (0x3915250,'488B1509207109488B0BE8C1E56EFC488BCF4885C00F85C43E5501488B15C6B27C09E805A710FD488903488BD0E96087FFFF'),
            (0x390F0CE,'488B15536E6F09488B0BE843476FFC488BCF4885C00F8509925501488B15B81D7D09E8BFFD10FD488903488BD0E9E2E8FFFF'),
            (0x390FF42,'488B15970B7309488B0BE8CF386FFC488BCF4885C00F85BA735501488B15CC177D09E8B3E410FD488903488BD0E96EDAFFFF'),
            (0x391508E,'488B1543F76F09488B0BE883E76EFC488BCF4885C00F85B5395501488B1528B97C09E893A310FD488903488BD0E92289FFFF'),
            (0x390F326,'488B15E3157309488B0BE8EB446FFC488BCF4885C00F8515805501488B15B0247D09E823F110FD488903488BD0E98AE6FFFF'),
            (0x39102C6,'488B155B9C7209488B0BE84B356FFC488BCF4885C00F85826C5501488B1548127D09E82FDE10FD488903488BD0E9EAD6FFFF'),
            (0x39102F8,'488B1501967209488B0BE819356FFC488BCF4885C00F85546D5501488B1596127D09E8BDDE10FD488903488BD0E9B8D6FFFF'),
            (0x3914B48,'488B15B94B7209488B0BE8C9EC6EFC488BCF4885C00F855C265501488B1586CB7C09E88D9710FD488903488BD0E9688EFFFF'),
            (0x390FB5A,'488B15875D7109488B0BE8B73C6FFC488BCF4885C00F85A5975501488B158C0B7D09E8C3FF10FD488903488BD0E956DEFFFF'),
            (0x3910712,'488B15BF507109488B0BE8FF306FFC488BCF4885C00F85D88B5501488B15E4FF7C09E8F3F310FD488903488BD0E99ED2FFFF'),
            (0x391505C,'488B15ED027009488B0BE8B5E76EFC488BCF4885C00F85D2395501488B156AB97C09E8ADA310FD488903488BD0E95489FFFF'),
            (0x390F89E,'488B152B597109488B0BE8733F6FFC488BCF4885C00F85B99A5501488B15200E7D09E8BB0211FD488903488BD0E912E1FFFF'),
            (0x3910B90,'488B1589427009488B0BE8812C6FFC488BCF4885C00F85EE7D5501488B1556FE7C09E849E810FD488903488BD0E920CEFFFF'),
            (0x390ED18,'488B1591817009488B0BE8F94A6FFC488BCF4885C00F85F1995501488B150E1B7D09E8D50411FD488903488BD0E998ECFFFF'),
            (0x3914A80,'488B15D1587209488B0BE891ED6EFC488BCF4885C00F8535245501488B15F6C97C09E8CD9510FD488903488BD0E9308FFFFF'),
            (0x390E2BE,'488B15637C7109488B0BE853556FFC488BCF4885C00F85AAAF5501488B1570237D09E8F31711FD488903488BD0E9F2F6FFFF'),
            (0x390DC7E,'488B15E3277809488B0BE8935B6FFC488BCF4885C00F85308C5501488B15C03D7D09E8AFFF10FD488903488BD0E932FDFFFF'),
            (0x3915124,'488B155D417109488B0BE8EDE66EFC488BCF4885C00F85873D5501488B154AB37C09E82DA610FD488903488BD0E98C88FFFF'),
            (0x390DD14,'488B15651E7809488B0BE8FD5A6FFC488BCF4885C00F85A28C5501488B15D23D7D09E89DFF10FD488903488BD0E99CFCFFFF'))}
        targets=[0]*416
        types=[None]*16728;self.ptrs={}
        for tag,target,index,definition,suffix,init in (
            (0xC9,0x390DA8A,106672,16163,'IfElseAction_IfElseActionData',0x417E68A),
            (0xC0,0x3910A00,106641,16145,'GainCostAction_Data',0x417E4D1),
            (0x40,0x39149EA,106441,16615,'CheckDamageTag_Data',None),
            (0x76,0x390E160,106507,16683,'Conditions_CheckSkillId_Data',None),
            (0xEC,0x390DCB0,106853,16241,'ModifyDynamicBlackboard_Data',None),
            (0x50,0x390DC1A,106467,16717,'CompareFloat_Data',None),
            (0x11F,0x390DED6,106969,16341,'RaiseTrainLevelEvent_Data',None),
            (0xB4,0x390DC4C,106625,16117,'FinishBuffAdvanced_Data',None),
            (0x56,0x390E354,106476,16593,'Conditions_CheckBuffIdInContext_Data',None),
            (0x92,0x390DA58,106537,16047,'CreateBuffAction_Data',None),
            (0x57,0x390E1C4,106475,16595,'Conditions_CheckBuffIdInContextAdvanced_Data',None),
            (0x5B,0x390E0FC,106480,16611,'Conditions_CheckDamageDecorateMask_Data',None),
            (0x3C,0x390DCE2,106437,16601,'CheckBuffStackNumAdvanced_Data',None),
            (0x78,0x390E994,106509,16687,'Conditions_CheckSkillType_Data',None),
            (0xB2,0x390DA29,106623,16111,'FindTargetAction_FindTargetActionData',None),
            (0x68,0x390DDDC,106493,16647,'Conditions_CheckMainCharacterCondition_Data',None),
            (0x81,0x390E674,106518,16707,'Conditions_CheckTimedMarkerCondition_Data',None),
            (0x58,0x390E098,106478,16599,'Conditions_CheckBuffStackNum_Data',None),
            (0x02,0x390E0CA,106256,16115,'AbilityActions_FinishBuffAction_Data',None),
            (0x9A,0x390DB20,106550,16063,'DamageAction_DamageActionData',None),
            (0xA2,0x390D9B5,106579,16079,'EffectAction_EffectActionData',None),
            (0x65,0x390E44E,106490,16641,'Conditions_CheckHp_Data',None),
            (0x169,0x390DDAA,107143,16485,'SpawnAbilityEntity_Data',None),
            (0x157,0x390E9F8,107097,16453,'SetSkillCdAtOnce_Data',None),
            (0x6E,0x390EC1E,106499,16665,'Conditions_CheckPoiseValue_Data',None),
            (0xFE,0x390E1F6,106901,16277,'ObtainCostAction_Data',None),
            (0x96,0x390E4B2,106541,16055,'CreateTimedMarker_Data',None),
            (0xFD,0x390E804,106885,16275,'NotNextCheckAction_Data',None),
            (0x7C,0x390DF9E,106513,16697,'Conditions_CheckTagMatch_Data',None),
            (0xB6,0x390DF6C,106627,16123,'FinishOwnerAction_Data',None),
            (0x80,0x390EB88,106517,16705,'Conditions_CheckTargetsEqual_Data',None),
            (0x16E,0x390E5DE,107148,16493,'SpellInflictionOnChar_Data',None),
            (0x7B,0x390E73C,106512,16695,'Conditions_CheckSuperArmor_Data',None),
            (0x6D,0x390F4B6,106498,16663,'Conditions_CheckPhysicalInflictionType_Data',None),
            (0x136,0x390E8FE,107005,16387,'SaveBuffStackNumAdvanced_Data',None),
            (0x163,0x390E12E,107114,16475,'SimpleCalcBBAction_Data',None),
            (0x69,0x390E4E4,106494,16653,'Conditions_CheckObjectTypeMatch_Data',None),
            (0x44,0x390F2C2,106445,16633,'CheckGlobalCDTimerAction_Data',None),
            (0x10F,0x390EE44,106926,16309,'PauseBuffTime_Data',None),
            (0x9B,0x390E228,106559,16065,'DebugPrintAction_Data',None),
            (0xC5,0x390E642,106660,16155,'HealAction_Data',None),
            (0x119,0x390D9FA,106941,16329,'PlaySoundAction_PlaySoundActionData',None),
            (0x0A,0x390F25E,106284,15903,'AddGlobalCDTimer_Data',None),
            (0x7A,0x390F2F4,106511,16691,'Conditions_CheckSpellInflictionType_Data',None),
            (0x88,0x390E6D8,106525,16725,'Conditions_Probablity_Data',None),
            (0x48,0x390F038,106449,16657,'CheckOriginSkillType_Data',None),
            (0x5A,0x390F772,106479,16609,'Conditions_CheckCustomAbilityEvent_Data',None),
            (0xC4,0x390EA5C,106651,16153,'GetTargetBuffBBAdvanced_Data',None),
            (0x145,0x390E70A,107077,16417,'SendBattleSignalToLevel_Data',None),
            (0xDE,0x390DB52,106784,16221,'LaunchProjectile_Data',None),
            (0xBD,0x390E25A,106633,16139,'ForEachAction_Data',None),
            (0x6A,0x390F57E,106495,16655,'Conditions_CheckObtainAtbType_Data',None),
            (0x24,0x390DB84,106353,15971,'CameraImpulseAction_CameraImpulseActionData',None),
            (0x16B,0x390F9CA,107145,16489,'SpawnInteractiveGoldCoin_Data',None),
            (0x7E,0x390ED7C,106515,16701,'Conditions_CheckTargetContains_Data',None),
            (0x35,0x390DD14,106376,16005,'CharHurtAnimAction_Data',None),
            (0xEA,0x390E516,106809,16237,'MergeTargetAction_Data',None),
            (0x61,0x390DEA4,106486,16629,'Conditions_CheckEntityNum_Data',None),
            (0x3F,0x390F70E,106440,16015,'CheckConsumeBuffLayer_Data',None),
            (0x14D,0x390F86C,107087,16433,'SetBuffDurationAction_Data',None),
            (0x73,0x390F5B0,106504,16675,'Conditions_CheckSkillCastId_Data',None),
            (0x5D,0x390E480,106483,16619,'Conditions_CheckDamageType_Data',None),
            (0x42,0x390DE40,106443,16623,'CheckDistanceCondition_Data',None),
            (0x27,0x390E3EA,106362,15977,'CastSkill_Data',None),
            (0x95,0x390F358,106540,16053,'CreateGlobalBuffAction_Data',None),
            (0x74,0x390FF10,106505,16677,'Conditions_CheckSkillDamageType_Data',None),
            (0x16D,0x390EB24,107149,16491,'SpellInfliction_Data',None),
            (0x160,0x390E322,107109,16469,'ShowHideActorAction_ShowHideActorData',None),
            (0x89,0x391035C,106526,16727,'Conditions_SaveHealValue_Data',None),
            (0x171,0x390EA2A,107157,16499,'StoreAttributeValue_Data',None),
            (0x132,0x390FD1C,107002,16379,'SaveAtbObtainValue_Data',None),
            (0xD4,0x390E76E,106768,16193,'InterruptAction_Data',None),
            (0x60,0x390EE76,106485,16627,'Conditions_CheckEnemyRank_Data',None),
            (0x126,0x390F54C,106982,16377,'RecoverFromPoiseBreak_Data',None),
            (0x1C,0x390DD46,106329,15939,'BlowOffCharacterAction_Data',None),
            (0x06,0x390EFA2,106277,15897,'AchieveSpecialGameEventAction_Data',None),
            (0x142,0x390E610,107018,16411,'SaveValueFromAIBlackboard_Data',None),
            (0x03,0x390F1C8,106257,16121,'AbilityActions_FinishGlobalBuffAction_Data',None),
            (0x51,0x390FA2E,106468,16719,'CompareString_Data',None),
            (0x5E,0x390EF70,106482,16621,'Conditions_CheckDamageTypeMask_Data',None),
            (0x13B,0x39105E6,107011,16397,'SaveDamageContext_Data',None),
            (0x84,0x390F614,106521,16713,'Conditions_CheckWeaponTypeCondition_Data',None),
            (0x174,0x3910D84,107160,16505,'StoreEntityProperty_Data',None),
            (0x41,0x390F740,106442,16617,'CheckDamageTransferredSource_Data',None),
            (0xA9,0x390E002,106594,16095,'EnemyHurtAnimAction_Data',None),
            (0x62,0x390FEDE,106487,16635,'Conditions_CheckHasDamageSkillCastId_Data',None),
            (0x13C,0x391000A,107012,16399,'SaveDamageSkillCastId_Data',None),
            (0x90,0x390EF0C,106534,16043,'CountShieldUIAction_Data',None),
            (0xBB,0x390FA60,106636,16135,'ForceTargetInFightAction_Data',None),
            (0x0B,0x390E386,106285,15905,'AddTagAction_Data',None),
            (0x2B,0x39107DA,106366,15985,'ChangeSeasonTowerEnergyAction_Data',None),
            (0x115,0x390DAEE,106937,16321,'PlayAnimationAction_PlayAnimationActionData',None),
            (0x151,0x39100A0,107091,16441,'SetHpFloor_Data',None),
            (0x13F,0x39150C0,107015,16405,'SaveShieldValueToBB_Data',None),
            (0x140,0x390EEDA,107016,16407,'SaveTargetDistanceAction_Data',None),
            (0x98,0x390ECB4,106543,16059,'CurveEvaluateFloat_Data',None),
            (0x176,0x390E89A,107166,16509,'SwitchAction_Data',None),
            (0x93,0x391038E,106538,16049,'CreateBuffAttachingSkill_Data',None),
            (0x175,0x3915250,107161,16507,'StoreSkillDamageType_Data',None),
            (0xFC,0x390F0CE,106886,16273,'NotifyCharPassiveUIAction_Data',None),
            (0x83,0x390FF42,106520,16711,'Conditions_CheckUsp_Data',None),
            (0x13A,0x391508E,107010,16395,'SaveCollectedBuffBbValue_Data',None),
            (0x86,0x390F326,106523,16721,'Conditions_ModifyCollectedBuffBbValue_Data',None),
            (0x63,0x39102C6,106488,16637,'Conditions_CheckHealTag_Data',None),
            (0x6B,0x39102F8,106496,16659,'Conditions_CheckOverHeal_Data',None),
            (0x77,0x3914B48,106508,16685,'Conditions_CheckSkillInterruptReason_Data',None),
            (0x188,0x390FB5A,107209,16545,'TriggerCustomAbilityEvent_Data',None),
            (0x187,0x3910712,107207,16543,'TriggerComboSkillAction_Data',None),
            (0x139,0x391505C,107009,16393,'SaveCharTypeId_Data',None),
            (0x18A,0x390F89E,107211,16549,'TriggerLiinoUIEvent_Data',None),
            (0x135,0x3910B90,107007,16385,'SaveBuffStackNum_Data',None),
            (0x122,0x390ED18,106976,16347,'ReadSkillSettingData_Data',None),
            (0x5C,0x3914A80,106481,16613,'Conditions_CheckDamageIgnoreImmuneLevel_Data',None),
            (0x183,0x390E2BE,107194,16535,'TimeDilationAction_Data',None),
            (0x2F,0x390DC7E,106371,15993,'ChannelingAction_Data',None),
            (0x15C,0x3915124,107102,16463,'ShakeCountShieldUIAction_Data',None)):
            targets[tag]=target;types[definition]='Beyond.MemoryPack.Beyond_Gameplay_Core_'+suffix+'ForMemoryPack'
            pointer=self.base+index*16
            self.parts[index*16]=struct.pack('<QII',definition,0x120000,0)
            self.ptrs[0x1000+index*8]=pointer
            for at,kind in ((target,1),)+(((init,2),) if init else ()):
                cell=at+7+struct.unpack_from('<i',self.parts[at],3)[0]
                self.parts[cell]=struct.pack('<Q',(kind<<29)|(index<<1)|1)
        self.parts[0x3915318]=struct.pack('<416I',*targets)
        def read(va,size):
            raw=self.parts[va-self.base]
            return raw[:7] if size==7 else raw
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=read,u64_at_va=lambda va:self.ptrs[va])
        self.md=SimpleNamespace(types=types,type_full_name=lambda t:t)
        self.reg={'types':'0x1000','typesCount':200000}

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return buff_union_routes(self.pe,self.md,self.reg,{},[],source='fixture.dll')

    def test_current_tag_routes_do_not_alias_old_names(self):
        row=self.decode();self.assertEqual([r['tag'] for r in row['rows']],[201,192,64,118,236,80,287,180,86,146,87,91,60,120,178,104,129,88,2,154,162,101,361,343,110,254,150,253,124,182,128,366,123,109,310,355,105,68,271,155,197,281,10,122,136,72,90,196,325,222,189,106,36,363,126,53,234,97,63,333,115,93,66,39,149,116,365,352,137,369,306,212,96,294,28,6,322,3,81,94,315,132,372,65,169,98,316,144,187,11,43,277,337,319,320,152,374,147,373,252,131,314,134,99,107,119,392,391,313,394,309,290,92,387,47,348])
        self.assertIn('IfElse',row['rows'][0]['wrapperName'])
        self.assertIn('GainCost',row['rows'][1]['wrapperName'])

    def test_truncated_trailing_corrupt_table_and_operands(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[at]=good

    def test_wrong_type_identity_and_registered_bounds(self):
        self.md.types[16163]=self.md.types[16145]
        with self.assertRaises(ContextError):self.decode()
        self.reg['typesCount']=106441
        with self.assertRaises(ContextError):self.decode()


class ElementProviderStateFlowTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0xF8040,'F68138010000017405488BC1EB05E9ED93F4FFC3'),
            (0x2DA427F,'488B5D38488B1B'),
            (0x2DA42B0,'B201488BCBE8462826FD4C8D6020'),
            (0x2DA439A,'488B4A10488B43704C8B34C8'),
            (0x2DA43E9,'498BCEE87F030000488BD8488B4538488B4008'),
            (0x2DA4412,'488BD0488B0BE833F425FD84C00F842AD0D401'),
            (0x2DA4592,'498B47704C8934F8'),
            (0x2DA482E,'488B80B8000000488B6818'),
            (0x2DA4970,'443B7B28754E488B75184C8B7310'),
            (0x2DA49A7,'33C948897C24204D8BCE4C8BC6488BD0E8745D29FD84C00F8516010000'),
            (0x2DA4ADA,'833D2BA70F0B00488B43184889442468'),
            (0x2DA4C7F,'4C8B0D52032A0A4C8BC3488BD7E80F44E000'),
            (0x2DA4C91,'488B442468'),
            (0x4AF1447,'4533F6E9652F2BFE'))}
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_state_lookup_and_distinct_return_context(self):
        row=element_provider_state_flow(self.pe,source='fixture.dll')
        self.assertEqual(len(row['windows']),14)
        self.assertIn('not a serialized reader',row['boundary'])
        self.assertIn('cannot be replaced by the fast-path identity',row['boundary'])

    def test_truncated_trailing_and_changed_state_offset_or_branch(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at,length=len(bad)),self.assertRaises(ContextError):
                    element_provider_state_flow(self.pe,source='fixture.dll')
            self.parts[at]=good


class AdapterConversionContextTests(unittest.TestCase):
    def setUp(self):
        self.parts={0x100:struct.pack('<QII',0x200,0x150000,0),
            0x200:struct.pack('<QQQQ',0x300,0x400,0,0),
            0x300:struct.pack('<QII',32173,0x120000,0),
            0x100000+173212*12:struct.pack('<iii',249850,12827,-1)}
        self.words={0x500:45287,0x504:173212}
        self.pe=SimpleNamespace(bytes_at_va=lambda va,size:self.parts[va],
            u32_at_va=lambda va:self.words[va],u64_at_va=lambda va:0x100)
        self.reg={'types':'0x200000','typesCount':50000,'methodSpecs':'0x100000',
            'methodSpecsCount':200000,'genericInstsCount':20000}
        self.entries=[{} for _ in range(13)]
        for rel,kind,ptr in ((8,2,0x500),(9,3,0x504)):
            self.entries[rel]={'relativeIndex':rel,'kindRaw':kind,'dataPointerVa':ptr,'entryVa':0x600+rel*16}
        self.inst=SimpleNamespace(index=12827,record_va=0x400,
            arguments=[SimpleNamespace(raw_type_record_hex='F2020000000000000000130000000000')],
            as_dict=lambda:{'index':12827})
        self.table=SimpleNamespace(resolve_pointer=lambda va:self.inst)
        buf=bytearray(0x3400)
        struct.pack_into('<II',buf,8+12*8,0x200,755*16)
        struct.pack_into('<II',buf,8+14*8,0x3200,16)
        struct.pack_into('<iihhHH',buf,0x200+754*16,0,0,0,0,0,0)
        struct.pack_into('<iiii',buf,0x3200,13633,1,0,754)
        types=[SimpleNamespace(generic_container_index=-1)]*32174
        types[13633]=SimpleNamespace(generic_container_index=0)
        types[32173]=SimpleNamespace(generic_container_index=-1,method_start=249850,method_count=1)
        self.method=SimpleNamespace(declaring_type=32173,slot=0,parameter_count=0,token=0x06001747,name_index=0)
        self.md=SimpleNamespace(buf=buf,types=types,methods=[None]*249850+[self.method],
            type_full_name=lambda t:'Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1',string=lambda i:'GetValue')

    def decode(self):
        return adapter_conversion_context(self.pe,self.md,self.reg,self.table,self.entries,source='fixture.dll')

    def test_reciprocal_ordinal_zero_interface_and_explicit_slot(self):
        row=self.decode()
        self.assertEqual((row['argumentOwner']['typeIndex'],row['argumentOwner']['ordinal']),(13633,0))
        self.assertEqual(row['methodSlot'],0)

    def test_truncated_trailing_and_malformed_carrier_or_spec(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[at]=good

    def test_wrong_context_owner_slot_and_bounds(self):
        self.method.slot=1
        with self.assertRaises(ContextError):self.decode()
        self.method.slot=0
        struct.pack_into('<i',self.md.buf,0x3200,13632)
        with self.assertRaises(ContextError):self.decode()
        struct.pack_into('<i',self.md.buf,0x3200,13633)
        self.reg['typesCount']=45287
        with self.assertRaises(ContextError):self.decode()


class ListElementValueFlowTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x3B13730,'48895C240848897424104C89442418574883EC20803D8143390A00498BF9488BF2488BD90F8489000000488B0D8FBE5D0983B9E0000000000F848D000000488B4F20E8C9485EFC488B88C0000000488B4920E8D90A29FF4885C07479B9050000004C8D4C24404C8BC3488BD0E85FBB52FC488B5C24404885DB7460488B4F20E88C485EFC488B88C0000000488B4940E87C485EFC33C94C8BC3488BD0E82F3058FC488B5C24308906488B7424384883C4205FC3488D0D06BE5D09E871DA52FCC605D642390A01E95FFFFFFFE8C02A51FCE969FFFFFFE80AACF9FCCC33C0EBC2'),
            (0x96800,'48895C240848896C24104889742418574883EC20498B38498BF00FB7E9488BDA488BCFE868E3F6FF440FB7873001000033C066413BC0731C488B97B00000000FB7C84803C948391CCA741A66FFC066413BC072EB440FB7C5488BD3488BCEE81DA3F7FFEB200FB7D0488B87B00000004803D28B44D00803C548984883C01448C1E0044803C74C8B00488BCE488B5008488B5C2430488B6C2438488B7424404883C4205F49FFE0'))}
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=self.read)

    def read(self,va,size):
        at=va-self.pe.image_base
        # Full-body requests expose truncated/trailing fixtures unchanged.
        if at in self.parts:return self.parts[at]
        for start,raw in self.parts.items():
            if start<=at<start+len(raw):return raw[at-start:at-start+size]
        raise ContextError('fixture.dll',at,'mapped range','missing')

    def test_initialized_object_slot_conversion_not_serialized_width(self):
        row=list_element_value_flow(self.pe,source='fixture.dll')
        self.assertEqual(row['outputByteLength'],4)
        self.assertEqual(len(row['bodies']),2)
        self.assertIn('initialized writable object slot',row['boundary'])
        self.assertIn('not proof of a serialized DWORD',row['boundary'])

    def test_truncated_trailing_and_corrupt_bodies(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at,length=len(bad)),self.assertRaises(ContextError):
                    list_element_value_flow(self.pe,source='fixture.dll')
            self.parts[at]=good

    def test_changed_record_offset_or_tail_call_fails_closed(self):
        at=0x96800;good=self.parts[at]
        for offset in (0x74,0x7D,0xA4):
            bad=bytearray(good);bad[offset]^=1;self.parts[at]=bytes(bad)
            with self.subTest(offset=offset),self.assertRaisesRegex(ContextError,'fixture.dll'):
                list_element_value_flow(self.pe,source='fixture.dll')
        self.parts[at]=good


class ListElementSharedContextTests(unittest.TestCase):
    def setUp(self):
        self.args=['A22D0000000000000000118000000000','068E00000000000000001C0000000000']
        self.specs=[(0,-1,-1)]*165249;self.specs[165248]=(102199,5059,-1)
        self.raw=struct.pack('<iiii',165248,0,0,-1)
        self.reg={'methodSpecsCount':len(self.specs),'genericMethodTableCount':1,'genericMethodTable':'0x1000'}
        self.code={'genericMethodPointersCount':1,'invokerPointersCount':1,'genericMethodPointers':'0x2000'}
        self.pe=SimpleNamespace(image_base=0x180000000,u64_at_va=lambda va:0x1840BB390)

    def decode(self):
        table=SimpleNamespace(resolve=lambda index:SimpleNamespace(record_va=0x3000,
            arguments=[SimpleNamespace(raw_type_record_hex=a) for a in self.args],as_dict=lambda:{'index':5059}))
        return list_element_shared_context(self.pe,table,self.reg,self.code,self.specs,self.raw,source='fixture.dll')

    def test_selected_shared_candidate_not_companion(self):
        row=self.decode()
        self.assertEqual(row['methodSpecIndices'],[165248])
        self.assertIn('shared-code candidate context',row['boundary'])

    def test_wrong_order_context_truncated_trailing_and_ambiguous(self):
        self.args.reverse()
        with self.assertRaises(ContextError):self.decode()
        self.args.reverse();good=self.raw
        for bad in (good[:-1],good+b'!',struct.pack('<iiii',165248,1,0,-1)):
            self.raw=bad
            with self.assertRaises(ContextError):self.decode()
        self.raw=good;self.specs[0]=self.specs[165248]
        with self.assertRaises(ContextError):self.decode()


class ListElementNullProbeTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x3EDF9A0,'40534883EC20488BD9C644243000E87D8EDCFE84C00F8537F8CC004883C4205BC3'),
            (0x4BAF1F2,'488D542430488BCBE861960FFEB001E9B50733FF'),
            (0x2CA8830,'40534883EC2083793001488BD90F8CBD8BE301488B43508038FF0F94C04883C4205BC3'),
            (0x2CA8860,'48895C24084889742410574883EC2083793001488BF2488BD90F8C958BE301488B43500FB608880E8B7B3083EF010F88938BE30148FF4350FF4340FF4344897B30803EFF488B5C2430488B7424380F95C04883C4205FC3'),
            (0x4AE1400,'4533C0BA01000000E84F7DC20490E930741CFE'),
            (0x4AE1414,'4533C0BA01000000E83B7DC20490E958741CFEBA01000000488BCBE80C0DFF0084C00F8565741CFEE953741CFE'))}
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_peek_marker_and_conditional_consumption(self):
        row=list_element_null_probe(self.pe,source='fixture.dll')
        self.assertEqual((row['markerByte'],row['fastConsumedBytesOnMatch']),(255,1))

    def test_truncated_trailing_corrupt_peek_branch_advance_or_boolean(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):list_element_null_probe(self.pe,source='fixture.dll')
            self.parts[at]=good


class ListElementDispatchTests(unittest.TestCase):
    def setUp(self):
        self.parts={0x98CD0:bytes.fromhex(
            '48895C2408488974241048897C241841564883EC20488B0A4D8BF1498BF0488BDAE89ABEF6FF488B3B488D0D90260204488B8790010000488BBF98010000483BC10F852B3D2600803DAFEDE00D000F84A1000000488B4720488B88C0000000488B11488BCEE8666CE40384C00F85F63C2600488B4720488B0D23D4000D488B98C000000083B9E000000000488B5B50747C33D2488BCBE885CBD0024885C0747733D2488BC8E876EDD00284C0756F488B4720488B88C0000000488B4958E89EEDD002488B4F204C8BC0498BD64C8B89C0000000488BCE4D8B4918E881A9A703488B5C2430488B742438488B7C24404883C420415EC3488D0DA4D3000DE88F84FAFFC605F5ECE00D01E947FFFFFFE8DED4F8FFE97AFFFFFFE82856A100CC33C0EBA1'),
            0x2FCA38:bytes.fromhex('33C0418906E96DC3D9FF4C8BCF4D8BC6488BD6488BCBFFD090E959C3D9FF'),
            0x98CF9:bytes.fromhex('488D0D90260204')}
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_fixed_pair_and_rip_derived_special_target(self):
        row=list_element_dispatch(self.pe,source='fixture.dll')
        self.assertEqual(row['targetPairOffsets'],[0x190,0x198])
        self.assertEqual(row['specializedTargetRva'],0x40BB390)
        self.assertIn('ordinary indirect CALL',row['boundary'])

    def test_truncated_trailing_changed_body_or_operand(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    list_element_dispatch(self.pe,source='fixture.dll')
            self.parts[at]=good


class ListFormatterCandidateTests(unittest.TestCase):
    def setUp(self):
        self.base=0x180000000
        self.parts={0x100:struct.pack('<QII',self.base+0x200,0x150000,0),
            0x200:struct.pack('<QQQQ',self.base+0x300,self.base+0x400,0,0),
            0x300:struct.pack('<QII',54057,0x120000,0)}
        for at,raw in ((0x3BA410E,'488B47508B30'),(0x3BA4120,'48834750048347400483474404895F30'),
            (0x3BA4130,'48634744488B4F18482BC84863C6483BC8'),(0x3BA4147,'83FEFF0F842F010000'),
            (0x3BA415F,'49833E00488B4520488B88C00000000F8518653201'),(0x3BA41C1,'85F60F881F653201'),
            (0x3BA4282,'49C70600000000'),(0x4ECA6AB,'FF431CC7431800000000E9799BCDFE'),
            (0x3BA4261,'85F67F4D'),(0x3BA42C3,'4C8D4C24584C8BC7498BD7E8FD494FFC'),
            (0x3BA4312,'41FFC4443BE60F8D47FFFFFFEB92')):self.parts[at]=bytes.fromhex(raw)
        self.pointers={self.base+0x10000+209879*8:self.base+0x100,self.base+0x20000:self.base+0x3BA40F0}
        def read(va,size):
            if va-self.base not in self.parts:raise ContextError('fixture.dll',va,'mapped raw range',size)
            return self.parts[va-self.base]
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=read,
                                u64_at_va=lambda va:self.pointers[va])
        self.reg={'typesCount':209880,'types':hex(self.base+0x10000),'methodSpecsCount':215462,
                  'genericMethodTableCount':1,'genericMethodTable':hex(self.base+0x30000)}
        self.code={'genericMethodPointersCount':1,'invokerPointersCount':1,'genericMethodPointers':hex(self.base+0x20000)}
        self.specs=[(0,-1,-1)]*215462;self.specs[215461]=(428795,816,-1)
        self.raw=struct.pack('<iiii',215461,0,0,-1)
        self.inst=SimpleNamespace(index=816,record_va=self.base+0x400,
            arguments=[SimpleNamespace(raw_type_record_hex='A22D0000000000000000118000000000')],as_dict=lambda:{'index':816})
        def resolve(pointer):
            if pointer!=self.base+0x400:raise ContextError('fixture',pointer,'registered pointer',pointer)
            return self.inst
        self.table=SimpleNamespace(resolve_pointer=resolve)
        self.md=SimpleNamespace(types=range(58110),methods={428795:SimpleNamespace(declaring_type=54057)})

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[{'token':0x060001C0}]):
            return list_formatter_candidate(self.pe,self.md,{},[],self.reg,self.code,self.table,self.specs,self.raw,source='fixture.dll')

    def test_candidate_and_nonuniform_negative_count_boundary(self):
        row=self.decode()
        self.assertEqual(row['methodSpecIndices'],[215461])
        self.assertEqual(row['codeCandidates'][0]['methodPointerVa'],self.base+0x3BA40F0)
        self.assertIn('does not universally reject',row['boundary'])
        self.assertIn('does not prove four serialized bytes',row['boundary'])

    def test_truncated_trailing_or_corrupt_carriers_and_windows(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):self.decode()
            self.parts[at]=good

    def test_bad_table_counts_indices_trailing_and_duplicate_candidates(self):
        good=self.raw
        for bad in (good[:-1],good+b'!',struct.pack('<iiii',215462,0,0,-1),struct.pack('<iiii',215461,1,0,-1)):
            self.raw=bad
            with self.assertRaises(ContextError):self.decode()
        self.raw=good+good;self.reg['genericMethodTableCount']=2
        with self.assertRaises(ContextError):self.decode()

    def test_wrong_context_or_additional_matching_spec(self):
        self.inst.index=817
        with self.assertRaises(ContextError):self.decode()
        self.inst.index=816;self.specs[0]=self.specs[215461]
        with self.assertRaises(ContextError):self.decode()


class NestedReaderContextTests(unittest.TestCase):
    def setUp(self):
        self.base=0x180000000;module=self.base+0x100
        self.modules={'MemoryPack.dll':module}
        self.words={module+8:678,module+0x40:120,module+0x50:691}
        self.qwords={module+16:self.base+0x2000,module+0x48:self.base+0x4000,module+0x58:self.base+0x5000}
        self.parts={self.base+0x2000:bytes(678*8)}
        ranges=bytearray(120*12)
        for i,(token,start,count) in enumerate(((0x06000073,36,1),(0x06000075,40,3),(0x0600002F,13,2))):
            struct.pack_into('<III',ranges,i*12,token,start,count)
        self.parts[self.base+0x4000]=bytes(ranges)
        self.reg={'methodSpecsCount':520000,'methodSpecs':hex(self.base+0x100000),
                  'genericInstsCount':60000,'typesCount':3000,'types':hex(self.base+0x200000)}
        for start,kind,index in ((36,3,517554),(40,3,516756),(13,1,2190)):
            payload=self.base+0x8000+start*4
            self.parts[self.base+0x5000+start*16]=struct.pack('<IIQ',kind,0,payload)
            self.parts[payload]=struct.pack('<I',index)
        self.parts[self.base+0x100000+517554*12]=struct.pack('<iii',428464,-1,54984)
        self.parts[self.base+0x100000+516756*12]=struct.pack('<iii',428394,-1,41928)
        self.parts[self.base+0x200000+2190*8]=struct.pack('<Q',self.base+0x9000)
        self.parts[self.base+0x9000]=struct.pack('<QII',2,0x1E0000,0)
        for at,raw in ((0x381F904,'488BDA4C8BF9'),(0x381F915,'488B4338488B18'),
                       (0x381F944,'488B4338488B30'),(0x381F956,'488B5E38488B1B'),
                       (0x381FB0D,'B9050000004C8D4C24204D8BC7488BD3E8DEF781FC')):
            self.parts[self.base+at]=bytes.fromhex(raw)
        self.args={54984:struct.pack('<QII',0,0x1E0000,0),41928:struct.pack('<QII',1,0x1E0000,0)}
        def resolve(index):
            return SimpleNamespace(record_va=0xA000,arguments=[SimpleNamespace(type_pointer_va=0xB000,
                raw_type_record_hex=self.args[index].hex().upper())],as_dict=lambda:{'index':index})
        self.table=SimpleNamespace(resolve=resolve)
        self.pe=SimpleNamespace(image_base=self.base,bytes_at_va=lambda va,size:self.parts[va],
                                u32_at_va=lambda va:self.words[va],u64_at_va=lambda va:self.qwords[va])
        self.buf=bytearray(0x300)
        struct.pack_into('<II',self.buf,8+12*8,0x200,48)
        struct.pack_into('<II',self.buf,8+14*8,0x240,48)
        methods=[SimpleNamespace(generic_container_index=-1)]*428465
        names={0:'MemoryPack.dll',1:'ReadPackable',2:'ReadValue',3:'GetFormatter'}
        for i,(definition,token) in enumerate(((428462,0x06000073),(428464,0x06000075),(428394,0x0600002F))):
            struct.pack_into('<iihhHH',self.buf,0x200+i*16,i,0,0,0,0,0)
            struct.pack_into('<iiii',self.buf,0x240+i*16,definition,1,1,i)
            methods[definition]=SimpleNamespace(generic_container_index=i,token=token,declaring_type=int(i==2),name_index=i+1)
        self.md=SimpleNamespace(buf=self.buf,methods=methods,
            types=['MemoryPack.MemoryPackReader','MemoryPack.MemoryPackFormatterProvider'],
            type_full_name=lambda name:name,string=lambda index:names[index],images=[SimpleNamespace(name_index=0)])

    def decode(self):
        return nested_reader_context(self.pe,self.md,self.modules,[0,0],self.reg,self.table,
                                     source='fixture.dll',metadata_source='fixture.dat')

    def test_distinct_reciprocal_parameters_and_module_slots(self):
        row=self.decode()
        self.assertEqual([r['moduleEntryIndex'] for r in row['rows']],[36,40,13])
        self.assertEqual([r['parameterOwner']['methodIndex'] for r in row['rows']],[428462,428464,428394])
        self.assertEqual([r['parameterOwner']['ordinal'] for r in row['rows']],[0,0,0])
        self.assertTrue(all(r['pointerVa']==0 for r in row['methods']))

    def test_same_ordinal_but_wrong_parameter_owner_is_rejected(self):
        self.args[54984]=self.args[41928]
        with self.assertRaises(ContextError):self.decode()

    def test_truncated_trailing_and_malformed_records_and_instructions(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                if at==self.base+0x2000 and bad==good:continue
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):self.decode()
            self.parts[at]=good

    def test_ambiguous_range_count_and_nonnull_generic_definition(self):
        at=self.base+0x4000;good=self.parts[at]
        for raw in (good[:36]+good[:12]+good[48:],good[:4]+struct.pack('<II',690,2)+good[12:]):
            self.parts[at]=raw
            with self.assertRaises(ContextError):self.decode()
        self.parts[at]=good
        pointers=bytearray(self.parts[self.base+0x2000]);struct.pack_into('<Q',pointers,(0x73-1)*8,self.base+0x1234)
        self.parts[self.base+0x2000]=bytes(pointers)
        with self.assertRaises(ContextError):self.decode()

    def test_out_of_bounds_spec_and_broken_reciprocal_container(self):
        self.reg['methodSpecsCount']=517554
        with self.assertRaises(ContextError):self.decode()
        self.reg['methodSpecsCount']=520000
        struct.pack_into('<i',self.buf,0x240,428464)
        with self.assertRaises(ContextError):self.decode()


class UnityLoaderConversionTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x22A130,
             '48895C241856415641574883EC30498BD8488BF24C8BF14885D20F84D20000004C8B014533FF44897C2428448BCE33D24C897C2420B9E9FD0000FF15A817630185C00F8EAA000000807B200148896C2450BD0C00000048897C24584863F80F85980000008BC5483BF8760B488BD7488BCBE8CA431A00807B2001746848897B10807B20017467488B036644893C78488BCB498B3EE8D7441A00807B2002488BE80F841C01CB00807B20017403488B1B896C2428448BCE4C8BC748895C242033D2B9E9FD0000FF151D176301488B7C2458488B6C2450488B5C24604883C430415F415E5EC3662BEF66896B18EB93488BC3EB97488BCBE896441A00EBD9488B4308E961FFFFFF'),
            (0x22A090,'48895C2408574883EC2080792002488BFA488BD90F842002CB00807B200174204C8B03488BCBE8E5451A00488B5C2430498D0C40488BC748890F4883C4205FC34C8BC3EBDE'),
            (0xEDA2CA,'E8D1434FFF488BD0E899424FFF90E9CDFD34FF'),
            (0xEDA2F2,'E8A9434FFF488BD0E871424FFF90E9D1FE34FF'),
            (0x3CE6A0,'807920017405488B4110C30FB75118B80C000000482BC2C3'),
            (0x2FE326,'E805BEF2FF488D9424A0000000488D4C2430E853BDF2FF'))}
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_arguments_and_two_byte_end_pointer(self):
        row=unity_loader_conversion(self.pe,source='fixture.UnityPlayer.dll')
        self.assertEqual((row['codePageArgument'],row['flagsArgument']),(65001,0))
        self.assertEqual(row['elementByteLength'],2)
        self.assertEqual(len(row['bodies']),5)

    def test_truncated_trailing_or_changed_count_result_and_end_pointer(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    unity_loader_conversion(self.pe,source='fixture.UnityPlayer.dll')
            self.parts[at]=good


class UnityLoaderInputTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x5579C0,'48895C2408574881EC800000008B0561504901488BF9488D4C243089442454BA10000000C644243000C644244818C644245001E868D0B1FF0F1005817732010F1100C6401000807C2450010F84150E9F00E91A0E9F00488D4C2430E8A06CDCFF'),
            (0xF48826,'C644244808E9E6F160FF'),
            (0x74A60,'405355564883EC4080792001488BF2488BD9BD180000000F85BE0000008BC5483BF07715807920010F85B6000000488BC34883C4405E5D5BC3'))}
        self.parts[0x187F180]=b'GameAssembly.dll'
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_inline_literal_and_loader_argument(self):
        row=unity_loader_input(self.pe,source='fixture.UnityPlayer.dll')
        self.assertEqual(row['requestedModuleName'],'GameAssembly.dll')
        self.assertEqual(row['requestByteLength'],16)
        self.assertEqual(row['loaderRva'],0x31E6C0)

    def test_truncated_trailing_or_changed_literal_tag_count_branch_and_call(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    unity_loader_input(self.pe,source='fixture.UnityPlayer.dll')
            self.parts[at]=good


class UnityModuleLookupTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x2FE290,
             '40564881EC80000000488BF1488B0D9DFDA5014885C90F847800C0004C8BC6488D542420E857010000488B0D80FDA5018B51084883C2084C6BC2074'
             'C03014C3B000F857100C00033C048899C24900000006689442430488BCEB80C000000C7442454010000006689442448C644245001E8EB68D7FF807E20017403488B0'
             'E48898C24A00000004C8D442430488D8C24A0000000488BD0E805BEF2FF488D9424A0000000488D4C2430E853BDF2FF0FB64C2450488B1880F9020F840A00C00080F'
             '901488D442430480F454424300F1F4000483BC374136683382F74064883C002EBEF66C7005C00EBF3807C2450010F84EEFFBF00488B4C2430FF1542D55501488BD84'
             '885C07443448B059B0A7A01488D4C24584889BC2498000000488BD6488B3D8CFCA501E837B29200488BD0488BCFE80C010000488D4C2458488918E83F65D7FF488BB'
             'C2498000000807C245000751B8B5424544C8D056F6D5601488B4C243041B90D020000E815AE2800488BC3488B9C24900000004881C4800000005EC3'),
            (0xEFE324,'4C8D05E55B2EFFBA20000000488D0D09FDE500E8C4ADD9FF488B0DFDFCE500E964FF3FFF488BD6E8800140FF488B00E9AE0040FF488B542440488D4C2430E809024DFF0FB64C2450E9DDFF3FFF488D4C2430E90D0040FF'),
            (0x31E670,'40574881EC90000000488BFA4885C9742E48899C24A0000000FF1561D25301488BD84885C00F84EB23BE00488BC3488B9C24A00000004881C4900000005FC333C0EBF3'),
            (0xF00A86,'FF15DCAE95008BD0488D4C2468E8881CE3FF807820017403488B004C8BC8488D153597BC004C8BC7488D4C2440E8887217FF488BC8488D159846960033C041B9FFFFFFFF8944243041B8E000000089442428C744242001000000E80BD541FF488D4C2440E8213E17FF488D4C2468E8173E17FF90E99CDB41FF'),
            (0x31E6C0,'4883EC28E8C7FBFDFF48890550659D014885C075054883C428C3'),
            (0x2FE388,'FF1542D55501'),(0x31E689,'FF1561D25301'),
            (0x22A16A,'FF15A8176301'),(0x22A1F5,'FF151D176301'))}
        self.parts.update({0x1C3624C:struct.pack('<IIIII',0x1C36648,0,0,0x1C38088,0x185B258),
                           0x1C38088:b'KERNEL32.dll\0',
                           0x1C36CC0:struct.pack('<Q',0x1C37618),
                           0x1C36CE0:struct.pack('<Q',0x1C375CE),
                           0x1C37618:b'\xf7\x03LoadLibraryW\0',
                           0x1C375CE:b'\xdd\x02GetProcAddress\0',
                           0x1C36D08:struct.pack('<Q',0x1C3756A),
                           0x1C3756A:b'\x23\x04MultiByteToWideChar\0'})
        self.header={0x3C:0x100,0x190:0x1C3624C,0x194:420}
        self.pe=SimpleNamespace(image_base=0x180000000,
            bytes_at_va=lambda va,size:self.parts[va-0x180000000],
            u32_at_file=lambda at:self.header[at])

    def test_selected_imports_and_handle_cache(self):
        row=unity_module_lookup(self.pe,source='fixture.UnityPlayer.dll')
        self.assertEqual([r['name'] for r in row['selectedImports']],
                         ['LoadLibraryW','GetProcAddress','MultiByteToWideChar','MultiByteToWideChar'])
        self.assertEqual(row['moduleHandleCacheRva'],0x1CF4C20)
        self.assertEqual(len(row['bodies']),5)

    def test_truncated_trailing_and_malformed_body_descriptor_thunk_or_name(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError) as raised:
                    unity_module_lookup(self.pe,source='fixture.UnityPlayer.dll')
                self.assertIn('fixture.UnityPlayer.dll',str(raised.exception))
            self.parts[at]=good

    def test_wrong_directory_offset_or_size(self):
        for at in (0x190,0x194):
            good=self.header[at]
            for bad in (0,good-1,good+1,0xFFFFFFFF):
                self.header[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    unity_module_lookup(self.pe,source='fixture.UnityPlayer.dll')
            self.header[at]=good


class ResolverKeyComparisonTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x2DF760,'482BD14983F808'),(0x2DF790,'8A013A0411750C'),
            (0x2DF79F,'4833C0C31BC083D8FFC3'),
            (0x2DF814,'488B0C0A480FC8480FC9483BC11BC083D8FFC3'),
            (0x1F21F,'4C8BC7483BF74C0F42C6E832052C00'),(0x1F29C,'483BFE7293'),
            (0x1F264,'4C8BC6483BDE4C0F42C3E8ED042C00'),(0x1F42E,'483BF30F8349FEFFFF'),
            (0x1F36F,'4C8BC7483BF74C0F42C6E8E2032C00'),
            (0x1F3D5,'483BFE72AA'),(0x1F43C,'483BF3738B'))}
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_complete_selected_windows(self):
        self.assertEqual(len(resolver_key_comparison(self.pe,source='fixture.dll')['windows']),11)

    def test_changed_truncated_trailing_compare_or_tie_break(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    resolver_key_comparison(self.pe,source='fixture.dll')
            self.parts[at]=good


class ResolverPrefixQueryTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x1F2D6,'BA28000000488BCBE85D052C00'),(0x1F2EC,'482BC34883F8FF'),
            (0x1F2F9,'4C8BC84533C0488D542440488D4C2420E892FDFFFF'),
            (0x1F30E,'488BD0488D4C2420E855460000'),
            (0x1F0BD,'4C3941100F828F7A2C00488B4110492BC0493BC14C0F42C8'),
            (0x1F0D5,'488379180F7603488B094A8D14014D8BC1488BCBE8E2570000'),
            (0x2399C,'0F10070F11030F104F100F114B10'),
            (0x24973,'4C8BC348894718488BD648895F10498BCEE897A32B00'))}
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_start_and_delimiter(self):
        row=resolver_prefix_query(self.pe,source='fixture.dll')
        self.assertEqual((row['queryStart'],row['delimiterByte']),(0,40))

    def test_bounds_call_and_move_windows_fail_closed(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    resolver_prefix_query(self.pe,source='fixture.dll')
            self.parts[at]=good


class UnityConversionExportsTests(unittest.TestCase):
    def setUp(self):
        self.ga={0xE177:bytes.fromhex('4C8BCA4C8902')};self.unity={}
        for at,hexraw,name_at,name,en,ns,os,fs,index,target in (
            (0x3205CD,'488B0D4C469D01488D150D6D6601E890E0FFFF488905D14A9D01',0x19872E8,
             'il2cpp_string_new_len',0xCF8DAF9,0xCF8BC5C,0xCF8C0EE,0xCF8B5E4,243,0x24AD0),
            (0x31FA06,'488B0D13529D01488D1544636601E857ECFFFF48890538519D01',0x1985D58,
             'il2cpp_gc_wbarrier_set_field',0xCF8D0D4,0xCF8BAD8,0xCF8C02C,0xCF8B460,146,0xE170)):
            literal=name.encode()+b'\0';self.unity[at]=bytes.fromhex(hexraw);self.unity[name_at]=literal
            self.ga.update({en:literal,ns:struct.pack('<I',en),os:struct.pack('<H',index),fs:struct.pack('<I',target)})
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.ga[va-0x180000000])
        self.up=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.unity[va-0x180000000])

    def decode(self):
        return unity_conversion_exports(self.pe,self.up,source='ga.dll',unity_source='unity.dll')

    def test_selected_export_targets(self):
        self.assertEqual([r['exportTargetRva'] for r in self.decode()['requests']],[0x24AD0,0xE170])

    def test_truncated_trailing_and_wrong_names_slots_and_abi(self):
        for parts in (self.ga,self.unity):
            for at,good in list(parts.items()):
                for bad in (good[:-1],good+b'!',bytes(len(good))):
                    parts[at]=bad
                    with self.subTest(at=at),self.assertRaises(ContextError):self.decode()
                parts[at]=good


class UnityPathReturnTests(unittest.TestCase):
    def setUp(self):
        self.parts={rva:bytes.fromhex(value) for rva,value in (
            (0x32BA24,'488D4C2420E822000000488BD0488D4C2460E88502FAFF'),
            (0x32BA3B,'488D4C2420E8CB8ED4FF488B442460'),
            (0x32BA63,'4C8D0596245401488BCB488D542420E819000000'),
            (0x2CBCC6,'488BD94C8BCA488BCAE81C8FDAFF'),
            (0x2CBCD4,'80792001751F448BC0488D4C2430498BD1E816000000'),
            (0x2CBCEA,'488B08488BC348890B'),(0x2CBCF9,'4D8B09EBDC'),
            (0x74BF0,'807920017405488B4110C3480FBE5118B818000000482BC2C3'),
            (0x2CBD06,'488B05AB93A2014C8BCA488BD9418BD0498BC9FFD0'),
            (0x2CBD1B,'4C8BC0488D54243033C9FF152D8EA201488B442430488903'))}
        self.parts[0x186DF00]=b'StreamingAssets\0'
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_return_and_representation(self):
        row=unity_path_return(self.pe,source='fixture.dll')
        self.assertEqual(row['representationTagOffset'],32)
        self.assertEqual(row['literal'],'StreamingAssets')

    def test_changed_truncated_or_trailing_windows(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    unity_path_return(self.pe,source='fixture.dll')
            self.parts[at]=good


class UnityRegistrationPairTests(unittest.TestCase):
    def setUp(self):
        base=0x180000000
        self.parts={0x3BF7C0:bytes.fromhex('48895C24084889742410574883EC2033FF488D352808C4FF8BDF660F1F440000488B943350D29D01488B8C33404E9E01E87BFAFFFFFFC7488D5B0881FF7E0F000072DD488B5C2430488B7424384883C4205FC3'),
            0x19DD250:struct.pack('<Q',base+0x32BA20)*0xF7E,
            0x19E4E40:struct.pack('<Q',base+0x19F1D50)*0xF7E,
            0x19F1D50:b'UnityEngine.Application::get_streamingAssetsPath\0',0x32BA20:b'!'}
        self.pe=SimpleNamespace(image_base=base,bytes_at_va=self.read)

    def read(self,va,size):
        if va-self.pe.image_base not in self.parts:
            raise ContextError('fixture.dll',va,'mapped target',va)
        raw=self.parts[va-self.pe.image_base]
        return raw[:1] if size==1 else raw

    def test_whole_slot_sweep_and_selected_pair(self):
        row=unity_registration_pair(self.pe,source='fixture.dll')
        self.assertEqual(row['summary']['success'],3966)
        self.assertEqual(row['selected']['index'],299)

    def test_truncated_trailing_changed_count_or_target(self):
        for at,good in list(self.parts.items()):
            if at==0x32BA20:continue
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    unity_registration_pair(self.pe,source='fixture.dll')
            self.parts[at]=good


class UnityRegistrationForwarderTests(unittest.TestCase):
    def setUp(self):
        self.parts={0x3BF270:bytes.fromhex('48895C241048896C2418564883EC2033DB488BF248391D85EC8A01488BE9762E48897C24308BFB488B0562EC8A01488BD6488BCDFF1407FFC3488D7F084863C3483B0559EC8A0172DE488B7C2430488BD6488BCD488B5C2438488B6C24404883C4205E48FF25E65C9301'),
            0x31E8F9:bytes.fromhex('488B0D20639D01488D15F1536601E864FDFFFF488905AD669D01'),
            0x3BF2D3:bytes.fromhex('48FF25E65C9301'),0x1983CF8:b'il2cpp_add_internal_call\0'}
        self.pe=SimpleNamespace(image_base=0x180000000,
            bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_full_forwarder_and_request(self):
        row=unity_registration_forwarder(self.pe,source='fixture.UnityPlayer.dll')
        self.assertEqual(row['requestedExport'],'il2cpp_add_internal_call')
        self.assertEqual(row['forwarderByteLength'],106)

    def test_bad_request_cache_and_terminator(self):
        for at in (0x31E8F9,0x3BF2D3,0x1983CF8):
            good=self.parts[at]
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    unity_registration_forwarder(self.pe,source='fixture.UnityPlayer.dll')
            self.parts[at]=good

    def test_missing_or_wrong_body_fails_closed(self):
        for raw in (b'',bytes(0x69),bytes(0x6A),bytes(0x6B)):
            pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:raw)
            with self.subTest(size=len(raw)),self.assertRaises(ContextError):
                unity_registration_forwarder(pe,source='fixture.UnityPlayer.dll')


class VfsRootResolverTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x2F46CD9,'E8325F9F00'),(0x2F46CE5,'488BD8'),
            (0x2F46CFD,'488B89B800000048895908'),(0x2F46CA7,'488B80B8000000488B4008'),
            (0x393CC14,'488B052D12570A4885C07407'),(0x393CC20,'4883C42848FFE0'),
            (0x393CC27,'488D0D1A7BEF06E87D256EFC'),(0x393CC3C,'4889050512570AEBDB'),
            (0x1F1DC,'4C8B2D7515E90D498B5D084D8BFD'),(0x1F293,'498B4740E957010000'),
            (0x1F2D6,'BA28000000488BCBE85D052C00'),(0x1F32A,'4C8B2D2714E90D498B5D084D8BFD'),
            (0x1F3CC,'4D3BFD751133DBEB11'),(0x1F3E2,'498B5F40'),(0x1F3F0,'488BC3'),
            (0x2E6B64,'48C7C0FFFFFFFFE97F87D3FF'),
            (0x2076F,'4889542410'),(0x2077D,'488BEC'),(0x207E6,'4C8B256BFFE80D'),
            (0x208BB,'488D1D96FEE80D'),(0x208CA,'B948000000E848301700'),
            (0x208DD,'0F1045D80F1140200F104DE80F114830'),
            (0x20924,'E837FCFFFF4C8BE8488B453849894540'),
            (0xF872C,'4889052580DB0D4889052680DB0D'),
            (0xF873F,'488900488940084889401066C7401801014889050180DB0D'),
            (0xCF8B1F0,'00000000FFFFFFFF0000000044C2F80C010000009E0100009E01000018B2F80C90B8F80C08BFF80C'),
            (0xCF8B914,'EFC4F80C'),(0xCF8BF4A,'2100'),
            (0xCF8B29C,'30050200'),(0x20530,'E92B020000'))}
        self.parts[0xCF8C4EF]=b'il2cpp_add_internal_call\0'
        self.parts[0xA834748]=b'UnityEngine.Application::get_streamingAssetsPath()\0'
        self.pe=SimpleNamespace(image_base=0x180000000,
            bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_static_requested_interface(self):
        row=vfs_root_resolver(self.pe,source='fixture.dll')
        self.assertEqual(row['requestedInterface'],'UnityEngine.Application::get_streamingAssetsPath()')

    def test_runtime_lookup_carrier_not_fixed_callee(self):
        row=vfs_root_resolver(self.pe,source='fixture.dll')
        self.assertEqual(row['candidateValueOffset'],64)
        self.assertNotEqual(row['lookupCarrierGlobalRva'],row['functionCacheRva'])

    def test_separate_writer_and_initializer(self):
        row=vfs_root_resolver(self.pe,source='fixture.dll')
        self.assertEqual(row['registrationWriterRva'],0x20760)
        self.assertEqual(row['sentinelInitializerRva'],0xF8718)

    def test_selected_export_to_tail_stub(self):
        row=vfs_root_resolver(self.pe,source='fixture.dll')
        self.assertEqual(row['selectedWriterExport'],
            {'name':'il2cpp_add_internal_call','ordinal':34,'stubRva':0x20530})

    def test_bad_target_name_terminator_and_window_lengths(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!',good[:-1]+bytes([good[-1]^1])):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    vfs_root_resolver(self.pe,source='fixture.dll')
            self.parts[at]=good


class VfsStringCarrierTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x2CB7624,'4C6341108BC2493BC07D0D4863C20FB7444114'),
            (0x24AD6,'448BC2488BD1488D4C2420E87A000000'),
            (0x24AE7,'488D4C242048837C243807480F474C24208B542430E86F0D0000'),
            (0x24BB2,'0FB60A80F980730C440FB6C141B901000000'),
            (0x24CC1,'0FB61E0FB60E80F9800F833C01000048FFC6'),
            (0x24CED,'488D480148894F10488BCF48837F18077603488B0F66891C416644896C4102'),
            (0x259DC,'897B10664489647B14'),
            (0x259FB,'4C8BC7488D4B144D03C0498BD6E813932B00'))}
        self.pe=SimpleNamespace(image_base=0x180000000,
            bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_reader_and_constructor_offsets(self):
        row=vfs_string_carrier(self.pe,source='fixture.dll')
        self.assertEqual((row['lengthOffset'],row['elementDataOffset'],row['elementByteLength']),(16,20,2))

    def test_truncated_and_trailing_windows(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!'):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    vfs_string_carrier(self.pe,source='fixture.dll')
            self.parts[at]=good

    def test_changed_bounds_width_and_copy_target_fail(self):
        for at in (0x2CB7624,0x24CED,0x259DC,0x259FB):
            good=self.parts[at];self.parts[at]=good[:-1]+bytes([good[-1]^1])
            with self.subTest(at=at),self.assertRaises(ContextError):
                vfs_string_carrier(self.pe,source='fixture.dll')
            self.parts[at]=good


class VfsFormatItemTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x2DF2D39,'488D4DC7448BC3488BD7'),(0x2DF2D48,'E8131700000F10008B7018'),
            (0x2DF4468,'418BD8488BFA488BF1'),(0x2DF447F,'FFC348636A10'),
            (0x2DF44AF,'0FB75442148D42D06683F809'),(0x2DF4515,'4183FE10'),
            (0x2DF4594,'44895E04FFC3'),(0x2DF45AC,'448936'),(0x2DF45B4,'44897E1C'),
            (0x2DF45BD,'895E180F114608'),
            (0x2DF4639,'488D4F1444895C242C4A8D0C61896C242848894C24200F28442420'),
            (0x4C5DC40,'4183FE100F8C906819FE'),(0x4C5DD0E,'41F7DF4533DB'))}
        self.pe=SimpleNamespace(image_base=0x180000000,
            bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def test_return_ranges_tile_exact_result(self):
        row=vfs_format_item(self.pe,source='fixture.dll')
        cursor=0
        for part in row['resultRanges']:
            self.assertEqual(part['offset'],cursor)
            cursor+=part['length']
        self.assertEqual(cursor,row['resultByteLength'])

    def test_truncated_and_trailing_instruction_windows(self):
        for at,good in list(self.parts.items()):
            for bad in (good[:-1],good+b'!'):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):
                    vfs_format_item(self.pe,source='fixture.dll')
            self.parts[at]=good

    def test_wrong_call_count_or_output_offset_fails(self):
        for at in (0x2DF2D48,0x2DF4515,0x2DF45BD,0x4C5DC40):
            good=self.parts[at];self.parts[at]=good[:-1]+bytes([good[-1]^1])
            with self.subTest(at=at),self.assertRaises(ContextError):
                vfs_format_item(self.pe,source='fixture.dll')
            self.parts[at]=good


class LiteralRecordTests(unittest.TestCase):
    def test_bounded_and_empty_interval(self):
        self.assertEqual(literal_record(struct.pack('<ii',3,2),5,source='meta',offset=8),(2,3))
        self.assertEqual(literal_record(struct.pack('<ii',0,5),5,source='meta',offset=8),(5,0))

    def test_truncated_trailing_negative_and_out_of_bounds(self):
        for raw in (b'',bytes(7),bytes(9),struct.pack('<ii',-1,0),struct.pack('<ii',1,-1),
                    struct.pack('<ii',6,0),struct.pack('<ii',1,5)):
            with self.subTest(raw=raw),self.assertRaises(ContextError):
                literal_record(raw,5,source='meta',offset=8)


class VfsPathLiteralTests(unittest.TestCase):
    def setUp(self):
        count=48958;pool_start=24+count*8
        self.buf=bytearray(pool_start)
        pool=bytearray()
        for index,value in ((48841,b'{0}/{1}/{2}'),(48957,b'{0}{1}{2}'),
                            (48832,b'{0}/{1}'),(48849,b'{0}/{1}{2}')):
            struct.pack_into('<ii',self.buf,24+index*8,len(value),len(pool));pool.extend(value)
        struct.pack_into('<iiii',self.buf,8,24,count*8,pool_start,len(pool))
        self.buf.extend(pool)
        self.parts={0x4139C:struct.pack('<I',0x41331),
                    0x41333:b'\xe8'+struct.pack('<i',0x2D8DE0-0x41333-5)}
        self.parts.update({at:bytes.fromhex(raw) for at,raw in (
            (0x41280,'8BC1C1E81D8BF1D1EE81E6FFFFFF0FFFC8'),
            (0x2D8E1D,'48635008486340104903D0'),(0x2D8E2F,'4903C04A634C0204428B14024803C8'))})
        for n,(rva,index) in enumerate(((0x2D7FAB2,48841),(0x2D7FB13,48957),(0x2D7FC9C,48832),
                                       (0x2D7DEEA,48841),(0x2D7E068,48849),(0x2D7E188,48832))):
            cell=0x1000+n*8
            self.parts[rva]=b'\x48\x8b\x05'+struct.pack('<i',cell-rva-7)
            self.parts[cell]=struct.pack('<Q',(5<<29)|(index<<1)|1)
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])

    def decode(self):
        return vfs_path_literals(self.pe,SimpleNamespace(buf=self.buf),source='fixture.dll',metadata_source='fixture.dat')

    def test_complete_row_sweep_and_four_literal_values(self):
        row=self.decode()
        self.assertEqual(row['literalSweep']['success'],48958)
        self.assertEqual(len({x['ascii'] for x in row['selected']}),4)

    def test_bad_header_pool_and_unselected_record_fail(self):
        good=self.buf[:]
        for offset,value in ((12,7),(16,0),(20,999999),(24,-1)):
            struct.pack_into('<i',self.buf,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ContextError):self.decode()
            self.buf=good[:]
        self.buf.pop()
        with self.assertRaises(ContextError):self.decode()

    def test_bad_switch_or_usage_is_not_a_literal(self):
        for at in (0x4139C,0x1000):
            good=self.parts[at]
            for bad in (good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at),self.assertRaises(ContextError):self.decode()
            self.parts[at]=good


class VfsPathFormatContextTests(unittest.TestCase):
    def setUp(self):
        self.parts={at:bytes.fromhex(raw) for at,raw in (
            (0x2D7E5E2,'488B050FC22E0A'),(0xD06A7F8,'5F2513C000000000'),
            (0x2D7E5E9,'4889442428'),(0x2DF2AC1,'4C8B757F488BFA4C8BE1'),
            (0x2DF2B28,'4863C30FB74C47146683F97B'),
            (0x2DF2D9E,'488B457F488B556F488B4038488B4808'),
            (0x2DF2E0C,'488B457F488B5567488B4038488B08'),
            (0x2DF2E94,'488B457F488B5577488B4038488B4810'),(0x2DF2D43,'45017C2408'),
            (0x2D72FAD,'4C8BFA418BF0418BD0488BD9'),
            (0x2D73006,'488B43208B088D04364863E84863C14C8D3447'),
            (0x2D73029,'4C8BC5498BD7498BCEFFD0'),(0x2D73065,'488B43208B0003F0'),
            (0x2D73097,'488B43208930'),(0x2D730CE,'488B43208B003B43287D38'),
            (0x2D73103,'488B43208B00489833C966890C47'))}
        self.spec_at=0x1000+627375*12
        self.parts[self.spec_at]=struct.pack('<iii',443949,-1,8335)
        self.pe=SimpleNamespace(image_base=0x180000000,bytes_at_va=lambda va,size:self.parts[va-0x180000000])
        self.reg={'methodSpecsCount':627868,'genericInstsCount':73902,'methodSpecs':'0x180001000'}
        self.instance=SimpleNamespace(arguments=[SimpleNamespace(raw_type_record_hex='C78C00000000000000000E0000000000') for _ in range(3)],as_dict=lambda:{'index':8335})
        self.table=SimpleNamespace(resolve=lambda index:self.instance)

    def decode(self):
        with patch('scripts.game_data.il2cpp_context_audit.module_methods',return_value=[]):
            return vfs_path_format_context(self.pe,SimpleNamespace(methods=range(500000)),{},[],self.reg,self.table,source='fixture.dll')

    def test_original_context_and_element_units(self):
        row=self.decode()
        self.assertEqual(row['methodSpecIndex'],627375)
        self.assertIn('not a byte length',row['boundary'])
        self.assertIn('only if the updated signed cursor is below capacity',row['boundary'])

    def test_all_selected_bytes_fail_closed(self):
        for at,good in list(self.parts.items()):
            for bad in (b'',good[:-1],good+b'!',bytes(len(good))):
                self.parts[at]=bad
                with self.subTest(at=at,length=len(bad)),self.assertRaises(ContextError):self.decode()
            self.parts[at]=good

    def test_wrong_context_or_argument_count(self):
        self.parts[self.spec_at]=struct.pack('<iii',443949,-1,5586)
        with self.assertRaises(ContextError):self.decode()
        self.parts[self.spec_at]=struct.pack('<iii',443949,-1,8335)
        self.instance.arguments.pop()
        with self.assertRaises(ContextError):self.decode()

    def test_shared_object_argument_cannot_replace_string(self):
        self.instance.arguments[1].raw_type_record_hex='068E00000000000000001C0000000000'
        with self.assertRaises(ContextError):self.decode()


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
        for tag in (1,2,3,5,6):
            with self.subTest(tag=tag):
                self.assertEqual(self.decode(struct.pack('<Q',(tag<<29)|7),tag=tag),3)

    def test_zero_and_maximum_legal_index(self):
        for tag in (1,2,3,5,6):
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
        for tag in (0,4,7,True):
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
