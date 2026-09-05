"""Exact-build, read-only generic-instantiation audit; JSON is emitted to stdout.

No runtime MethodInfo or serialized source cursor is inferred. Native tables
are referenced PE extents, not a claim to consume the entire PE to EOF.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp_context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.memorypack.skill_corpus import verify_current_report_inputs
from scripts.game_data.il2cpp_context import class_sharing_branch
from scripts.game_data.il2cpp_context import named_top_level_type
from scripts.game_data.il2cpp_context import object_type_comparison_key
from scripts.game_data.il2cpp_context import method_pointer_indices, generic_method_candidates
from scripts.game_data.il2cpp_context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp_context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer

ROOT = Path(__file__).resolve().parents[2]
GA_SHA = 'C24495E51B406F03B03890C4788EE618AE022C991405BE5D5B8B787CB775AE89'
MD_SHA = '0076743397ACADF03D3B0064343A963C7C88863B8160526D397E4B3EFB96F02E'
CORPUS_SHA = '3B2B96545D1A17FFA4F7770B2BA7AF6045E4BDE701465AD42E2AFB0FA6D05943'
CONSUMER_WINDOWS = (
    (0x2D36380, 0x2D36994, '85D41B9FE1654F6F92A646B7A964873F1F7FE0CD00D141C4F83008F8829E5030'),
    (0x3AF70, 0x3AFBF, '72BD36DFB1B0E26BACC5934A9DD0C0CE1F0DBC3B7D651C979A4D519F0898C5B3'),
    (0x3B188A0, 0x3B189ED, 'BBF441134BEE6360DE2E40A3EF134DB920D8DE9FED8231EEBF0602101B5E389D'),
    (0x3B677B0, 0x3B67D18, '57AD13123C926CC835193BAE0A9636F201B74EDF5D23F87121E7DA2D332555DB'),
    (0x970BFBC, 0x970BFF0, 'AB34067513E25C40E3C0BE6EAF9A085B4C48438CDB435512C1B2BF2AE24A34F3'),
    (0x9711078, 0x9711A57, 'CEA35CF8D73D0B319BD52DE7BA66202EB93CA5559EF0083F14EF01ED1D2D9963'),
    (0x970AD30, 0x970AE65, 'B1587FA587E6E160B00DEF0116FD0B7C1BEC5D7670AD8CA059E22489904F20EA'),
    (0x3B67E30, 0x3B67EC4, 'E20940F2F7B39A3BB1806DA04749C66E3B2CF514FF8CA0658B5F690C18EB0279'),
    (0x970C4A8, 0x970C672, 'EEFD3592C95C7366380F47A0890632F54ED8EC2B521D81014852BA045BFC610C'),
    (0x970BFF0, 0x970C1F5, 'AE39953E1E6D1C4C8531CE5206EA5DCE70CD82DBB8093111E669103CC2B80A7F'),
    (0x970915C, 0x9709454, 'AB0D5C7A12E463100AF920A8CB6A52001B52B15A51AB7EC11C1D006D04EC7363'),
    (0x5AD2140, 0x5AD227B, 'DF6D3A33414236CA22AD342A51DA9DF5B759B250EFB98B40BBD8816E6992C5E5'),
    (0x838223C, 0x8382292, '44086E7E4E68ABB7828C536B227D14046E427D6EA13E39C4396A66E0854F090D'),
    (0x837EC68, 0x837ED6A, '1FCA33902F53C293A266896CEDA59F4DE806A98E5B8FDF0A2F6FB10CA4ACD65D'),
    (0x8381FF0, 0x8382066, '7CD14312228390425009C7437524BCCAF7E52B39A40AB030D62AA197819998CF'),
    (0x83761A0, 0x837633C, '0178C8AB8E92ACFCBC58B294EC2800840F2EF46C86927FBFB5AB969AC9724DF9'),
    (0x8375FBC, 0x83761A0, 'EFA324973C53A29ED5926C04777AA94EF9E39DBB0CE12218B26E18E9BB97C41C'),
    (0x381F8F0, 0x381FDF6, '5917DCD09ACBA635492A0F3A751C3940EDEA02D5E0F38B977F3DADEFDC672279'),
    (0x37DF620, 0x37DF67D, '6901FC137F0D874FDFBDED47658B6B8BFA718E0BF2AE7EFD480EF8152DEEE72A'),
    (0x37DF680, 0x37DF77C, 'FBF5D3CF070494A3BE4FF265779AEEDE8B5CA95A2DE61EDFE215DB72640A1AA1'),
    (0x4E3B21E, 0x4E3B2B9, '4C1C33561E4C1011B637FF320D49C0DDF625396AEE89C8BB88414F9C97A048B5'),
    (0x8D20, 0x8F52, '48868BF56BEC2C84D6EEF44AE342E3CB5ABC1D54A62494733BE2703CA6A206B3'),
    (0x84B0, 0x8C74, 'A29F9BB8993244FF7D7571D39282EFA4A8B88736E71FAA18492B7AA4D90A706A'),
    (0xB010, 0xB995, '10231D49EEBCEAD16CF4142DF20F38407783C9D3DA55196125D305F23785D238'),
    (0x10000, 0x10019, 'AB93A915D9FB7495ADE419CB253425EEF1EED86E69495C824F19B157AD12C7F1'),
    (0xF4E0, 0xFF04, '0A71E5B9F7995F00CAF05B63F8FC5D3081CCD7614346A27057A329171072D89E'),
    (0x2DA8DA0, 0x2DA9898, 'C8A0697BE4093DAAA327F0D8202C33F900B6FB3857C270DFD6AD5F0E5386FFAF'),
    (0x2CC6B0, 0x2CC78C, '24344F6D00D7721765E78CF8141E2D1645B867A92FCBC657A54A7447C58303EC'),
    (0x2CC840, 0x2CC87C, '5E938881C79B911A1B1ACFE6BC3C4D3ABCC63D2552F05F0033FC67D0D49BEEF9'),
    (0x438F0, 0x43943, '33FF46D3B9C40354CAA46CC41E0F5174C2A87AAF69638F4A90B0E858F2DD56B1'),
    (0x9890, 0x9C67, '3764C631545FC23232AD4EBB109D0CC0415C1F5951531B840C207A4339749B34'),
    (0x13170, 0x134AF, '982687620B62840A318F9822B52C6F856D9FA5192337B1660007FD0306F52DD1'),
    (0x9C70, 0x9E6C, '0E56CE95E514F299C8F4D717C397811C7F1D16AC4E512C2955B23CCD05EA6F25'),
    (0x6A1E0, 0x6A39A, 'D9128C8BAB9B54797E0A0627E477F13A66063B5AB05932F0F9BB08475FE14E2B'),
    (0x2B2D70, 0x2B2E09, 'A9E38FAA7FB63E0C143C42798EB01AD09814F1639E04045E5EFDC776698B3080'),
    (0x69D60, 0x69D81, 'B585984BD43C174908671417D61F619A5BC3D0F083DF75AF691CF5EB218D4743'),
    (0x69D81, 0x69E9D, '8957659F01CF49BBFD5E7626A35F48B3E967880F6CEDF73B79C9AF5786E45276'),
    (0x69E9D, 0x69EAA, '05C4EF4266710A20641E22FDD6F964EE9C4A7ED76C4A98645B15F4D4780C4333'),
    (0x69EAA, 0x69F99, '98E219B3323AAF0B639E2B25E8AAB6AB135092CB0324F94C5F2F35299748ED86'),
    (0x4A560, 0x4A6A9, '5F21000E0A7DC7AD2B6AE4B29D79964839FEBBBD524762D6F8E4C0EA67618FE9'),
    (0x1C850, 0x1CCD6, 'E05B2B74811C4CCCCA4C95A3FACDFE804C037BB56FBBA41EB28EC1545265F70F'),
    (0x3CF20, 0x3D364, 'E1629CA701FE3C68029C4FA2207449CF615DC38E9EB43F4B3DFDA8319A41F48F'),
    (0x2C6C10, 0x2C6E20, 'D0C37020DB6E3FA5F5D8429326495F7C63157F0A731EE3DC070E1CB3F8BC05B4'),
    (0x2C7550, 0x2C75D3, 'CE47EA89E1466DA991434EB620A2DCFDF25D50F80A8D2A7A67CE87E70D73B13A'),
    (0x2DA4770, 0x2DA4842, 'E485B80DE7EB384A0656711FE57395E813FA3DA7981EED3171080ACCC0D40507'),
    (0x2DA4842, 0x2DA4CB6, 'B62863C4ECF8EED5095302277B77F5AF56FB6EEFD6BF69E53A249B99132231F7'),
    (0x2A5B3B0, 0x2B25E5F, 'FF4949FACDD976369EA9D9008FC74EAD1A384AA4F0A699585810DC65AEFB0B7B'),
    (0x38003F0, 0x380047D, 'A31994FE88EFC8CBC3666CEBCB71FDD8CA317233F38D1EF5727110E6879631B5'),
    (0xA790, 0xAE47, 'F9E448ECD6162E73ED4282F551F1F19A763854F6D99031A45EA61612AF292A09'),
    (0x9230, 0x962A, 'B11CC37279D6BD65872B4E6CC22339543A84B005FE4B65F424081417C0C57214'),
    (0x3850, 0x3995, '4C5BF32B3BDC82C200BC2D88CFD0698694249C52C68BE5B71E87CC596F713C23'),
    (0x281B0, 0x28367, '4A5FE0579AFAF220617B572015648A598472D8F86A163A8EBE9E4F06282C02CB'),
    (0x64EA0, 0x64FB9, '5432E86CB6E16C4659B2FAC1EDAD6F805331B1638BFF96C6103192AF46543F9E'),
    (0x37DE060, 0x37DE0BB, '0926899BA44C601CEBAC2B4E70580B397CDDAB4FC60060C1E8DC0EF99A2555FB'),
    (0x37DE9C5, 0x37DEB23, 'C6A761532672A5700D9FEEB980F66BAF88B6F1F2CEAC48688680CF4158C1F285'),
    (0x37DE884, 0x37DE9C5, '853722D03CBFE915CFB92DD372A7C85BE072576C8FEB4CB35912E766BBDE9BCA'),
    (0x41260, 0x4127B, 'DD4C21E4DCAA9ED293D62B4817726DDA64F2BCAFA8C2AFEFFF299EC039CE3F0B'),
    (0x4127B, 0x412D2, 'EC737048F208A7BF568C342D1630E506203A591F88E5497D2D93A9DD31B04D06'),
    (0x412D2, 0x412E0, '65F69D9450DCBB01DF08A592D62CFD560557C9B84E8662F49E421AEC07C15E91'),
    (0x2D8D10, 0x2D8D6A, '1D69558B9C9CBC2E7868E2A5895269966FB40E86B3E36B7B020BCC5C948ED5AC'),
    (0x2D8BF0, 0x2D8C12, '58AEECD1D6787DA519A37F3857FB40F3950BED75D3A9A0A6AEC81DEE32569AA4'),
    (0x2D8C12, 0x2D8C79, 'F1D27E8325CBBCF568E89D23C9280969ADAB6DEE2CEDE13E0FD1F1CBCB762470'),
    (0x2D8C79, 0x2D8C83, '087CD1A1ECF2C15B53BC8CA47F008DFACD7DB6E1579D1AD1C3A77D500224D68C'),
    (0x9630, 0x9850, 'F1F3F2471B2DDA9F3BC2E3505293D5658E04D9F25225CA8EF648EC4CC786388F'),
    (0x2C0E50, 0x2C0ED3, '16DD44242597B807F5729A2DD6AE5EF4BA7CB0B825BF9303F259407BB8A53A36'),
    (0x12BD0, 0x12C74, '90390C80AEFAF2A371E43E9491A557C87A6F168EFE73D8A7A089B7447C61EAAC'),
    (0x12CC0, 0x13169, 'BE122CAACEC77957916E5CC541FF0055ABFD9264303F7ACEB8BC48832933DCF3'),
    (0x2D7820, 0x2D7BBF, 'BFB975F36A64975240720253EB1391D00D2DFBD48317ED38291DAB6683EA00F0'),
    (0x9E70, 0xA500, '1B9824C30A36C141691EC195D8D3052B50A497722679DA9BAA2BC8194F68C19B'),
    (0x15C90, 0x16F71, 'EDCF30D6AEC6E2E98B7329DCA27C14DB36C754FADC8841648EDC02ADF5726023'),
)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def require(actual, expected, source, offset=0):
    if actual != expected:
        raise ContextError(str(source), offset, expected, actual)


def native_gate():
    gate = check_installed_native_inputs(GA_SHA, MD_SHA)
    require(gate.status, 'validated', 'selected native inputs: ' + gate.detail)
    return gate


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sweep(table):
    rows, failures = [], []
    for index in range(table.count):
        try:
            rows.append(table.resolve(index).as_dict())
        except ContextError as error:
            failures.append({'index': index, **error.diagnostics})
    return {'success': len(rows), 'failed': len(failures), 'unsupported': 0}, rows, failures


def validate_selected_method_spec(row, records, base, method_count, instantiation_count, *, source):
    """Verify emitted identity against raw records, independently of loop locals."""
    if not isinstance(row,dict) or len(records)%12:
        raise ContextError(source,base,'MethodSpec evidence object and exact record array',type(row).__name__)
    index=row.get('index')
    if type(index) is not int or not 0<=index<len(records)//12:
        raise ContextError(source,base,'bounded reported MethodSpec index',index)
    offset=base+index*12
    raw=records[index*12:(index+1)*12]
    definition,_,method_inst=method_spec_record(raw,method_count,instantiation_count,source=source,offset=offset)
    for key,expected in (('va',offset),('rawHex',raw.hex().upper()),('definition',definition)):
        if row.get(key)!=expected:
            raise ContextError(source,offset,f'reported {key} matches raw MethodSpec',
                               {'expected':expected,'actual':row.get(key)})
    inst=row.get('methodInstantiation')
    if not isinstance(inst,dict) or inst.get('index')!=method_inst:
        raise ContextError(source,offset+8,'reported method instantiation matches raw MethodSpec',
                           {'expected':method_inst,'actual':inst})


def serializer_return_consumers(pe, *, source):
    """Selected exact post-call windows, not exhaustive caller/EOF analysis."""
    edges=[]
    for rva,target in ((0x970BFE1,0x970C4A8),(0x97112AB,0x970C4A8),
                       (0x971179A,0x970C4A8),(0x97112BF,0x51D80)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'rawHex':raw.hex().upper(),'targetRva':target})
    windows=[]
    for rva,expected in ((0x970BFE6,'488B4424504883C448C3'),
                         (0x97112B0,'4C63C0B920000000448D49E1488BD7'),
                         (0x971179F,'488B742430488D8C24A0000000')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'edges':edges,'postCallWindows':windows,
            'level':'direct selected consumer dataflow',
            'objectReturnWrapper':{'rva':0x970BFBC,
                                   'boundary':'Copies entry RDX 16-byte input, supplies a zero-initialized output slot to the reader-owning entry, then overwrites RAX with that output slot and returns. The returned consumed count in EAX is discarded without comparison in this entire wrapper.'},
            'stateMachineCallsites':[
                {'rva':0x97112AB,'boundary':'Sign-extends returned consumed EAX into R8 and forwards it with ECX=0x20, R9D=1, RDX=the source object to another dispatcher. This is use of consumption, not an EOF comparison; the dispatched operation and source identity remain unresolved.'},
                {'rva':0x971179A,'boundary':'Loads the local output result into RSI and prepares cleanup, discarding returned consumed EAX. Buffer-fill counts and completion branches elsewhere in this owner do not themselves establish equality with this parser consumption.'}],
            'boundary':'No claim that these are all callers, that SkillData selects any of them, or that successful object return certifies EOF. Initial authenticated logical-file identity and the actual selected formatter remain missing.'}


def module_methods(pe, md, modules, image_owners, selections, *, source, expected_image='MemoryPack.dll'):
    """Join each selected definition through its own owner/image/token identity."""
    selected=[]
    pointer_tables={}
    for index,type_name,name,expected in selections:
        require(0<=index<len(md.methods),True,source,index)
        method=md.methods[index]
        require(0<=method.declaring_type<len(md.types),True,source,index)
        owner=md.types[method.declaring_type]
        require(md.type_full_name(owner),type_name,source,index)
        require(md.string(method.name_index),name,source,index)
        image_name=md.string(md.images[image_owners[method.declaring_type]].name_index)
        require(image_name,expected_image,source,index)
        module=modules[image_name]
        if module not in pointer_tables:
            count=pe.u32_at_va(module+8)
            require(count<=1_000_000,True,source,module+8)
            base=pe.u64_at_va(module+16)
            pointer_tables[module]=(base,pe.bytes_at_va(base,count*8))
        base,pointers=pointer_tables[module]
        row=method_token_pointer(method.token,pointers,source=source,offset=base)
        require(row['pointerVa'],0 if expected is None else pe.image_base+expected,source,row['slotVa'])
        selected.append(dict(row,methodIndex=index,declaringType=type_name,name=name,image=image_name,moduleVa=module))
    return selected


def reader_construction(pe, md, modules, image_owners, *, source):
    """Exact method-token identities plus independently reviewed native bodies."""
    selected=module_methods(pe,md,modules,image_owners,
        [(index,'MemoryPack.MemoryPackReader',name,rva) for index,name,rva in
         ((428422,'get_Consumed',0x4A46420),(428423,'get_Remaining',0x4A655D0),
          (428426,'.ctor',0x970AD30),(428427,'.ctor',0x3B67E30))],source=source)
    getters=[]
    for rva,hex_bytes in ((0x4A46420,'8B4144C3'),(0x4A655D0,'48635144488B4118482BC2C3')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        getters.append({'rva':rva,'rawHex':raw.hex().upper(),'rangeKind':'bounded explicit-return leaf; no pdata extent'})
    edges=[]
    for rva,target in ((0x970AE04,0x8381FF0),(0x970AE34,0x838223C),(0x970AE4C,0x3F779C0),
                       (0x970C5BB,0x3B67E30),(0x970C605,0x3F300),(0x970C0FD,0x970AD30)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'rawHex':raw.hex().upper(),'targetRva':target})
    return {'methods':selected,'getterLeaves':getters,'edges':edges,
            'level':'exact module/token identity; direct conditional native construction',
            'spanConstructor':{'rva':0x3B67E30,'inputWindowBytes':16,'stateWindowBytes':0x58,
                               'boundary':'RDX points to a 16-byte carrier copied to reader+0x20. Its signed dword+8 is stored at reader+0x30 and sign-extended into +0x18; +0x38 and both +0x40/+0x44 counters are cleared. Nonzero carrier length selects its pointer for +0x50; zero selects null. The first 24 state bytes come from static storage. Input validity and allocation bounds are not checked by this constructor.'},
            'sequenceConstructor':{'rva':0x970AD30,'inputWindowBytes':24,
                                   'boundary':'RDX points to a 24-byte endpoint descriptor. Equal endpoints use the static descriptor in reader+0; otherwise the input descriptor is copied. First-segment and length helpers still receive the original input, supplying +0x20/+0x30, total +0x18 and cursor +0x50. Both counters are cleared. Static descriptor contents and multi-segment ABI remain unresolved.'},
            'accessors':{'consumedOffset':0x44,'totalLengthOffset':0x18,
                         'boundary':'get_Consumed returns the dword at +0x44; get_Remaining returns qword+0x18 minus sign-extended dword+0x44. This independently names these state roles, not serialized field meanings.'},
            'caller':{'rva':0x970C4A8,'readerStackOffset':0x50,'returnedCounterStackOffset':0x94,
                      'boundary':'Copies the entry RDX 16-byte input, initializes a 0x58-byte stack reader, invokes the span constructor, dispatches with that reader, and returns its +0x44 counter after cleanup. The sequence caller similarly copies a constructed 0x58-byte state and returns +0x44. Neither reviewed owner compares that counter against original length. Caller selection for SkillData, initial file identity, and outer EOF enforcement remain unknown.'},
            'boundary':'A conditional source-length/consumed ABI exists, but no authenticated VFS allocation or observed SkillData invocation joins it. Do not prune terminal candidates.'}


def reader_cursor_consumers(pe, *, source):
    """Bound reviewed edges; caller authenticates complete selected native build."""
    edges=[]
    for rva,opcode,target in (
        (0x4E3B229,0xE8,0x970915C),(0x4E3B23C,0xE8,0x5AD2140),
        (0x5AD21C3,0xE8,0x838223C),(0x838228D,0xE9,0x83761A0),
        (0x5AD21F5,0xE8,0x837EC68),(0x5AD221C,0xE8,0x8381FF0),
        (0x8382045,0xE8,0x8375FBC),(0x5AD2236,0xE8,0x3F779C0),
        (0x9709289,0xE8,0x837EC68),(0x97092D8,0xE8,0x8381FF0),
        (0x9709421,0xE8,0x3F779C0),(0x381FAD4,0xE8,0x2DA4770),
        (0x381FB1D,0xE8,0x3F300)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        actual=relative_branch_target(raw,pe.image_base+rva,source=source)
        require(raw[0],opcode,source,rva)
        require(actual,pe.image_base+target,source,rva)
        edges.append({'instructionRva':rva,'instructionHex':raw.hex().upper(),'targetRva':target})
    # This leaf has no pdata row: certify only its two explicit return paths,
    # not a guessed function extent or the following aligned function.
    leaf=pe.bytes_at_va(pe.image_base+0x3F779C0,13)
    require(leaf,bytes.fromhex('837908007404488B01C333C0C3'),source,0x3F779C0)
    return {'edges':edges,'pointerLeaf':{'rva':0x3F779C0,'rawHex':leaf.hex().upper(),
                                       'rangeKind':'bounded instruction window; no pdata extent'},
            'level':'direct conditional native reader state transitions',
            'advance':{'rva':0x5AD2140,'normalReturn':True,'localCounterResetOffset':0x40,
                       'accumulatedCounterOffset':0x44,'cursorReplacementOffset':0x50,
                       'boundary':'The only normal return sets AL=1, resets +0x40, adds the signed-extended request via a 32-bit addition at +0x44, and replaces +0x30/+0x50 from helper outputs. Caller false-return fallback is not a second normal path in this pinned body. Helpers may throw; counter overflow and runtime descriptor validity are not certified.'},
            'ensure':{'rva':0x970915C,'sourceDescriptorPrefixBytes':24,
                      'boundary':'Uses +0x18 minus signed-extended +0x44 as a requested-length guard, resets +0x40 after a delegated 24-byte descriptor transformation, and selects an existing or copied segment before replacing +0x30/+0x50. The cursor can change allocations; a pointer delta is not an absolute source offset. The descriptor transform/copy/type-context helpers are not fully closed.'},
            'descriptorLength':{'rva':0x83761A0,'prefixBytes':24,
                                'boundary':'For equal endpoint objects at +0/+8, masks bit 31 from the +0x10/+0x14 words and returns end minus start. Unequal endpoints use type-context conversions and object +0x28 values; their ABI remains conditional, not a certified source length.'},
            'nestedRead':{'rva':0x381F8F0,'readerRegister':'R15',
                          'boundary':'Entry RCX is saved in R15 and passed to dispatch as R8; the local output is returned after formatter dispatch. This body is another provider/dispatch layer, not the list count or element consumer. Its cold cache paths, live MethodInfo and selected list formatter are unresolved.'},
            'boundary':'No authenticated logical-file allocation, initial descriptor, complete helper ABI, final cursor or EOF join. Keep both terminal candidates.'}


def wrapper_consumer(pe, md, reg, table, *, source):
    """Reviewed conditional wrapper path, not a source/EOF or dispatch receipt."""
    instruction=pe.bytes_at_va(pe.image_base+0x37DF6EC,7)
    require(instruction[:3],bytes.fromhex('488B15'),source,0x37DF6EC)
    cell=rip_qword_load_target(instruction,pe.image_base+0x37DF6EC,source=source)
    initializer=pe.bytes_at_va(pe.image_base+0x37DF752,7)
    require(initializer[:3],bytes.fromhex('488D0D'),source,0x37DF752)
    require(pe.image_base+0x37DF759+struct.unpack_from('<i',initializer,3)[0],cell,source,0x37DF752)
    records_base=int(reg['methodSpecs'],16)
    spec=usage_method_spec(pe.bytes_at_va(cell,8),pe.bytes_at_va(records_base,reg['methodSpecsCount']*12),
                          len(md.methods),reg['genericInstsCount'],source=source,
                          usage_offset=cell,records_offset=records_base)
    require((spec['index'],spec['definition'],spec['classInstantiationIndex'],spec['methodInstantiationIndex']),
            (610730,428462,-1,8486),source,spec['va'])
    inst=table.resolve(spec['methodInstantiationIndex'])
    require(len(inst.arguments),1,source,inst.record_va)
    arg=inst.arguments[0]
    raw=bytes.fromhex(arg.raw_type_record_hex)
    carrier_raw=pe.bytes_at_va(struct.unpack_from('<Q',raw)[0],32)
    base_raw=pe.bytes_at_va(struct.unpack_from('<Q',carrier_raw)[0],16)
    carrier=generic_type_carrier(raw,carrier_raw,base_raw,type_pointer=arg.type_pointer_va,
                                 type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],37521,source)
    require(md.type_full_name(md.types[37521]),'System.Collections.Generic.List`1',source)
    element_inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(element_inst.index,816,source,element_inst.record_va)
    require(len(element_inst.arguments),1,source,element_inst.record_va)
    require(element_inst.arguments[0].raw_type_record_hex,'A22D0000000000000000118000000000',source)
    call=pe.bytes_at_va(pe.image_base+0x37DF6F9,5)
    require(call[0],0xE8,source,0x37DF6F9)
    require(pe.image_base+0x37DF6FE+struct.unpack_from('<i',call,1)[0],pe.image_base+0x381F8F0,source,0x37DF6F9)
    return {'methodSpec':spec,'methodInstantiation':inst.as_dict(),
            'listCarrier':carrier,'elementInstantiation':element_inst.as_dict(),
            'formatterEntryRva':0x37DF620,'readerEntryRva':0x37DF680,'nestedCallRva':0x37DF6F9,
            'level':'direct conditional consumer; exact static usage/type relation',
            'boundary':'The formatter forwards its reader unchanged to the wrapper reader. The fast path consumes one byte using remaining+0x30, cursor+0x50 and counters+0x40/+0x44. Header 0xFF clears the output; non-null header 1 reaches the nested call with the same reader and the recorded List instantiation. Other headers reach a helper then INT3. Cold ensure/advance transitions are described separately in selectedReaderCursorConsumers; their descriptor helpers are not fully closed. No list element layout, actual provider selection, authenticated source allocation, source extent or final cursor is established.'}


def resource_carrier_consumers(pe, *, source):
    """Reviewed native carrier/state path, separate from actual resource selection."""
    edges=[]
    for rva,target in ((0x3B18966,0x3B677B0),(0x3B67C9C,0x2DA4260),
                       (0x3B67CBB,0x3F300),(0x3B67CD3,0x1F0450)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x3B188B5,'483972387508488BCAE8CD6653FC'),
        (0x3B1896B,'488B9C249800000048899C24A0000000'),
        (0x3B67CA6,'B9050000004C8B8C24080100004C8D442440488BD0'),
        (0x3B67CC0,'8B9C2484000000899C2410010000488D4C2430'),
        (0x3B67CEB,'8BC34881C4C0000000415F415E415D415C5F5E5BC3')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    switch=pe.bytes_at_va(pe.image_base+0x3B67D18,28)
    require(switch,struct.pack('<7I',0x3B67A26,0x3B67A35,0x3B67A44,0x3B67AA7,
                               0x3B67AB6,0x3B67A44,0x3B67B79),source,0x3B67D18)
    return {'edges':edges,'instructionWindows':windows,
            'switchData':{'rva':0x3B67D18,'rawHex':switch.hex().upper()},
            'level':'direct conditional native carrier/state consumption',
            'outer':{'rva':0x3B188A0,'inputCarrierBytes':16,
                     'boundary':'Null MethodInfo+0x38 invokes initialization; non-null skips it. Rebuilds a 16-byte local from input qword+0 and dword+8, with last dword zero. Supplies the local, output slot, zero R8 and context slot 0 to the inner entry. Returned EAX is discarded; the output slot is returned after cleanup. No EOF comparison in this wrapper.'},
            'inner':{'rva':0x3B677B0,'stateStackOffset':0x40,'counterOffset':0x44,
                     'boundary':'Inlines state construction: input carrier at state+0x20, dword length at +0x30, signed length at +0x18, zero +0x38/+0x40/+0x44, and pointer-or-null cursor at +0x50. State+0x48 comes from the thread-local storage/allocation path, not the plain constructor. Conditional non-null helper result reaches dispatch slot 5 with R8=&state and R9=output. Returns state dword+0x44 after cleanup, matching the independently identified consumed accessor offset. This is not a proof of helper success or input allocation validity.'},
            'boundary':'MethodSpec-based names and declared stream input are separately joined in selectedStreamSourceIdentity. Live contexts, complete upstream resource selection, path/hash, carrier allocation length and final authenticated-file cursor are not joined. The switch data is excluded from the code window. Both terminal layouts remain ambiguous.'}


def skill_resource_context(pe, md, modules, image_owners, table, reg, code,
                          spec_records, specs_raw, methods_raw, *, source):
    """Exact selected static relations; no live generic sharing or file receipt."""
    identity=named_top_level_type(md.buf,b'Gameplay.Beyond.dll',b'Beyond.Gameplay.Core',
                                 b'SkillData',source=source)
    require(identity['typeDefinitionIndex'],9060,source)
    inst=table.resolve(16656)
    require(len(inst.arguments),1,source,inst.record_va)
    raw=bytes.fromhex(inst.arguments[0].raw_type_record_hex)
    require(raw,bytes.fromhex('64230000000000000000120000000000'),source,inst.arguments[0].type_pointer_va)
    require(struct.unpack_from('<Q',raw)[0],identity['typeDefinitionIndex'],source)
    object_inst=table.resolve(75)
    require(len(object_inst.arguments),1,source,object_inst.record_va)
    require(object_inst.arguments[0].raw_type_record_hex,'068E00000000000000001C0000000000',source)
    identities=module_methods(pe,md,modules,image_owners,
        [(248580,'Beyond.Resource.ResourceManager','DeserializeFromJson',None),
         (248574,'Beyond.Resource.ResourceManager','DeserializeFromJsonAsyncByCoroutine',None)],
        source=source,expected_image='Common.Beyond.dll')
    for row,token in zip(identities,(0x06001251,0x0600124B)):
        require(row['token'],token,source,row['slotVa'])
    selected=[]
    for index,definition in ((621380,248580),(621385,248574)):
        require(spec_records[index],(definition,-1,inst.index),source,int(reg['methodSpecs'],16)+index*12)
        selected.append({'index':index,'definition':definition,'classInstantiationIndex':-1,
                         'methodInstantiationIndex':inst.index,'rawHex':specs_raw[index*12:(index+1)*12].hex().upper()})
    matching={i for i,(definition,_,_) in enumerate(spec_records) if definition in (248580,248574)}
    candidates=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),
        matching,code['genericMethodPointersCount'],code['invokerPointersCount'],
        source=source,offset=int(reg['genericMethodTable'],16))
    for row in candidates:
        method,invoker,_=row['indices']
        row['methodPointerVa']=pe.u64_at_va(int(code['genericMethodPointers'],16)+method*8)
        row['invokerPointerVa']=pe.u64_at_va(int(code['invokerPointers'],16)+invoker*8)
        require(row['methodPointerVa']!=0 and row['invokerPointerVa']!=0,True,source,row['va'])
    # Pins validate the current complete candidate set, without selecting a live one.
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in candidates],
            [(521437,pe.image_base+0x36A7AD0),(521443,pe.image_base+0x45BA810)],source)
    for index,definition in ((521437,248580),(521443,248574)):
        require(spec_records[index],(definition,-1,object_inst.index),source,int(reg['methodSpecs'],16)+index*12)
    return {'typeIdentity':identity,'methodIdentities':identities,'concreteInstantiation':inst.as_dict(),
            'objectInstantiation':object_inst.as_dict(),'concreteMethodSpecs':selected,
            'sameDefinitionMethodSpecs':[{'index':i,'indices':list(spec_records[i]),
                                         'rawHex':specs_raw[i*12:(i+1)*12].hex().upper()} for i in sorted(matching)],
            'codeCandidates':candidates,
            'tableFraming':{'records':reg['genericMethodTableCount'],'byteLength':len(methods_raw),
                             'sha256':hashlib.sha256(methods_raw).hexdigest().upper(),
                             'boundary':'All 16-byte records and MethodSpec keys bounded; only selected triples decoded. Other triples remain opaque.'},
            'level':'exact static type/MethodSpec/code-table relations',
            'boundary':'Core.SkillData, not the same-named AI nested type. Generic definition module slots are null; code candidates come from the separate generic method table. Same-definition Object MethodSpecs do not establish actual sharing selection, method invocation, resource path/hash, reader ABI, consumed length or EOF. Preserve both terminal candidates.'}


def stream_source_identity(pe,md,modules,image_owners,reg,code,spec_records,methods_raw,*,source):
    """Join selected generic bodies and declared stream slots, not live overrides."""
    identities=module_methods(pe,md,modules,image_owners,
        [(249865,'Beyond.MemoryPack.MemoryPackManager','DeSerialize',None),
         (249853,'Beyond.MemoryPack.MemoryPackManager','_DeSerialize',None),
         (248587,'Beyond.Resource.ResourceManager','_MemoryPackDeserializeFromJson',None)],
        source=source,expected_image='Common.Beyond.dll')
    identities+=module_methods(pe,md,modules,image_owners,
        [(428652,'MemoryPack.MemoryPackSerializer','Deserialize',None)],source=source)
    stream=named_top_level_type(md.buf,b'mscorlib.dll',b'System.IO',b'Stream',source=source)
    require(stream['typeDefinitionIndex'],37639,source)
    method=md.methods[249853]
    require((method.parameter_start,method.parameter_count),(237944,1),source)
    require(method.parameter_start<len(md.parameters),True,source)
    parameter=md.parameters[method.parameter_start]
    require(parameter.type_index,143204,source)
    require(parameter.type_index<reg['typesCount'],True,source)
    type_pointer=pe.u64_at_va(int(reg['types'],16)+parameter.type_index*8)
    type_raw=pe.bytes_at_va(type_pointer,16)
    require(type_raw,bytes.fromhex('07930000000000000000120000000000'),source,type_pointer)
    require(struct.unpack_from('<Q',type_raw)[0],stream['typeDefinitionIndex'],source,type_pointer)
    stream_methods=module_methods(pe,md,modules,image_owners,
        [(287486,'System.IO.Stream','get_Length',None),(287526,'System.IO.Stream','Read',0x2FC6D40)],
        source=source,expected_image='mscorlib.dll')
    for row,slot,return_index,raw_hex in zip(stream_methods,(11,35),(126199,126157),
        ('3C8D00000000000000000A8000000000','3B8D0000000000000000088000000000')):
        method=md.methods[row['methodIndex']]
        require((method.slot,method.return_type),(slot,return_index),source)
        require(return_index<reg['typesCount'],True,source)
        pointer=pe.u64_at_va(int(reg['types'],16)+return_index*8)
        raw=pe.bytes_at_va(pointer,16)
        require(raw,bytes.fromhex(raw_hex),source,pointer)
        row.update(virtualSlot=slot,returnTypeIndex=return_index,returnTypeRawHex=raw.hex().upper())
    expected=((517109,249865,0x3B188A0),(517125,249853,0x2D36380),
              (517721,428652,0x3B677B0),(521492,248587,0x3187EB0))
    definitions={definition for _,definition,_ in expected}
    matching={i for i,(definition,_,_) in enumerate(spec_records) if definition in definitions}
    rows=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),matching,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=source,
        offset=int(reg['genericMethodTable'],16))
    for row in rows:
        row['methodPointerVa']=pe.u64_at_va(int(code['genericMethodPointers'],16)+row['indices'][0]*8)
    require([(row['methodSpecIndex'],row['methodPointerVa']) for row in rows],
            [(index,pe.image_base+rva) for index,_,rva in expected],source)
    for index,definition,_ in expected:
        require(spec_records[index],(definition,-1,75),source,int(reg['methodSpecs'],16)+index*12)
    return {'methodIdentities':identities,'genericBodyCandidates':rows,'streamType':stream,
            'streamParameter':{'methodIndex':249853,'parameterIndex':237944,'typeIndex':parameter.type_index,
                               'typePointerVa':type_pointer,'typeRawHex':type_raw.hex().upper()},
            'declaredStreamMethods':stream_methods,
            'level':'exact static method/type/virtual-slot relation',
            'boundary':'Declared input is System.IO.Stream. Metadata virtual slots 11 and 35 name get_Length and Read, with signed 64-bit and 32-bit return records. This does not identify the concrete stream subclass or override, its successful initialization, bytes, position, full-read behavior or EOF. Shared Object method contexts do not prove actual SkillData invocation.'}


def stream_carrier_consumer(pe,*,source):
    """Exact reviewed calls and discarded read result; length is not a receipt."""
    edges=[]
    for rva,target in ((0x2D363DC,0x3AF70),(0x2D36425,0x3AF70),(0x2D36470,0x3AF70),
                       (0x2D365F1,0x3AF70),(0x2D36448,0x3150DD0),
                       (0x2D3659E,0x3B188A0),(0x2D36961,0x3B188A0)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x3AF78,'0FB7D9488BFA488B0AE80A9CFCFF488D431448C1E0044803074C8B00488B5008'),
        (0x2D36573,'FFD0488B0DAC6F2E0A'),
        (0x2D36924,'FF907003000048895D40448965488B452C'),
        (0x2D36442,'8BD0488D4D30'),
        (0x2D365F6,'4C8BE04C63C085C0'),
        (0x2D36526,'4585F60F884E040000'),
        (0x2D368E2,'4585E40F889F000000')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    for rva in (0x2D363D4,0x2D3641D,0x2D36468,0x2D365E9):
        require(pe.bytes_at_va(pe.image_base+rva,8),bytes.fromhex('B90B000000488BD6'),source,rva)
    switch=pe.bytes_at_va(pe.image_base+0x2D36994,56)
    require(switch,bytes.fromhex('C564D302CF64D302D664D302E264D302EC64D302D664D302F664D3029266D302A266D302B266D3021567D3022567D302B266D302E967D302'),source,0x2D36994)
    return {'edges':edges,'windows':windows,'switchData':{'rva':0x2D36994,'rawHex':switch.hex().upper()},
            'dispatcher':{'rva':0x3AF70,'slotBaseOffset':0x140,'slotStride':16,'inputSlotBits':16,
                          'boundary':'The reviewed entry computes class + (uint16(CX)+0x14)*16, loads pointer and companion. Its specialized branches and cold paths are not all closed; this is a slot-address connection, not a live override receipt.'},
            'level':'direct conditional native carrier construction and discarded read result',
            'boundary':'Both allocation branches perform one indirect call at class+0x370 with a 16-byte carrier, then call the joined manager carrier entry without testing returned EAX. Slot 35 is declared Stream.Read, not ReadExactly. The large branch obtains length separately for comparison, low-32-bit allocation request and low-32-bit carrier length; equality/stability is not checked. The small branch also narrows a fresh result before stack allocation. Later negative checks apply to the narrowed dword, not the original 64-bit result. No source position, complete-fill loop, short-read check, authenticated payload length or final parser EOF is established; allocation helpers and concrete overrides remain unresolved.'}


def audit():
    gate = native_gate()
    corpus_path = ROOT / 'reports/animestudio/skilldata_current_latest.json'
    require(sha(corpus_path), CORPUS_SHA, corpus_path)
    corpus = json.loads(corpus_path.read_text(encoding='utf-8'))
    verify_current_report_inputs(corpus)
    mapper_path = ROOT / 'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py'
    catalog_path = ROOT / 'tools/endfield-il2cpp/catalog_option_flow_metadata.py'
    sources = [Path(__file__), Path(__file__).with_name('il2cpp_context.py'),
               mapper_path, catalog_path, ROOT / 'scripts/common.py']
    source_hashes = {str(p): sha(p) for p in sources}
    mapper = load('context_audit_mapper', mapper_path)
    catalog = load('context_audit_catalog', catalog_path)
    pe = mapper.PeImage(gate.gameassembly)
    md = catalog.Metadata(gate.metadata)
    require(hashlib.sha256(pe.buf).hexdigest().upper(), GA_SHA, gate.gameassembly)
    require(hashlib.sha256(md.buf).hexdigest().upper(), MD_SHA, gate.metadata)
    candidates = mapper.find_code_registration_candidates(pe, {md.string(x.name_index) for x in md.images})
    require(candidates, [0x18A88E640], gate.gameassembly)
    image_owners = type_image_owners(md.buf, len(md.types), source=str(gate.metadata))
    require(pe.u32_at_va(candidates[0]+0x68), len(md.images), gate.gameassembly, candidates[0]+0x68)
    module_pointers = pe.bytes_at_va(pe.u64_at_va(candidates[0]+0x70), len(md.images)*8)
    module_rows = [(pe.c_string_at_va(pe.u64_at_va(pointer)), pointer)
                   for (pointer,) in struct.iter_unpack('<Q', module_pointers)]
    modules = match_image_modules([md.string(item.name_index) for item in md.images],
                                  module_rows, source=str(gate.gameassembly))
    image_rows = []
    module_rgctx_bytes = {}
    rgctx_inventory = []
    for item in md.images:
        name = md.string(item.name_index)
        if name not in modules:
            raise ContextError(str(gate.metadata), item.index, 'matching CodeGenModule name', name)
        image_rows.append({'imageIndex': item.index, 'name': name, 'typeStart': item.type_start,
                           'typeCount': item.type_count, 'moduleVa': modules[name]})
        entry_count=pe.u32_at_va(modules[name]+0x50)
        entry_base=pe.u64_at_va(modules[name]+0x58)
        require(entry_count<=1_000_000,True,gate.gameassembly,modules[name]+0x50)
        entry_bytes=pe.bytes_at_va(entry_base,entry_count*16) if entry_count else b''
        decoded_entries=rgctx_range_entries(entry_bytes,0,entry_count,source=str(gate.gameassembly),offset=entry_base)
        require(len(decoded_entries),entry_count,gate.gameassembly,entry_base)
        module_rgctx_bytes[name]=(entry_base,entry_bytes)
        rgctx_inventory.append({'imageIndex':item.index,'name':name,'entryBaseVa':entry_base,
                                'success':entry_count,'failed':0,'unsupported':0,
                                'sha256':hashlib.sha256(entry_bytes).hexdigest().upper()})
    registration = mapper.find_metadata_registration(pe, candidates[0])
    require(registration, 0x18A88E860, gate.gameassembly)
    for begin, end, expected in CONSUMER_WINDOWS:
        require(hashlib.sha256(pe.bytes_at_va(pe.image_base + begin, end-begin)).hexdigest().upper(),
                expected, gate.gameassembly, begin)
    for rva, prefix, expected in (
        (0x15E4C, '488D0D', candidates[0]),
        (0x15E68, '48890D', pe.image_base+0xDEB09B8),
        (0x12F74, '4C8B15', pe.image_base+0xDEB09B8),
        (0x2C7555, '4C8B1D', pe.image_base+0xDEB09B8),
        (0x37DEADB, '488D0D', pe.image_base+0xCFF4E48),
        (0x37DE8E9, '488B15', pe.image_base+0xCFF4E48),
    ):
        instruction = pe.bytes_at_va(pe.image_base+rva, 7)
        require(instruction[:3].hex().upper(), prefix, gate.gameassembly, rva)
        require(pe.image_base+rva+7+struct.unpack_from('<i', instruction, 3)[0], expected,
                gate.gameassembly, rva)
    reg = mapper.metadata_registration_summary(pe, registration)
    table = GenericInstantiationTable(pe.bytes_at_va, int(reg['genericInsts'], 16),
                                     reg['genericInstsCount'], source=str(gate.gameassembly))
    summary, rows, failures = sweep(table)
    # Explicit raw MethodSpec -> pointer-table join, not an observed invocation.
    spec_index = 516756
    if not 0 <= spec_index < reg['methodSpecsCount']:
        raise ContextError(str(gate.gameassembly), registration, 'bounded MethodSpec index', spec_index)
    spec_va = int(reg['methodSpecs'], 16) + spec_index * 12
    raw = pe.bytes_at_va(spec_va, 12)
    definition, class_inst, method_inst = struct.unpack('<iii', raw)
    require((definition, class_inst, method_inst), (428394, -1, 41928), gate.gameassembly, spec_va)
    selected = table.resolve(method_inst)
    require(len(selected.arguments), 1, gate.gameassembly, selected.record_va)
    type_raw = bytes.fromhex(selected.arguments[0].raw_type_record_hex)
    require(type_raw[10], 0x1E, gate.gameassembly, selected.arguments[0].type_pointer_va)
    owner = method_parameter_owner(md.buf, struct.unpack_from('<Q', type_raw)[0],
                                   [m.generic_container_index for m in md.methods], source=str(gate.metadata))
    require(owner['methodIndex'], 428464, gate.metadata, owner['containerOffset'])
    selected_method_spec={'index':spec_index,'va':spec_va,'rawHex':raw.hex().upper(),
                          'definition':definition,'methodInstantiation':selected.as_dict(),
                          'openMethodParameterOwner':owner}
    usage_va = pe.image_base+0xCFF4E48
    usage_raw = pe.bytes_at_va(usage_va, 8)
    call_index = method_spec_usage_index(usage_raw, reg['methodSpecsCount'],
                                         source=str(gate.gameassembly), offset=usage_va)
    require(call_index, 619889, gate.gameassembly, usage_va)
    # Tag 6 selects table index 5. The pinned branch forwards the original
    # encoding to 2D8D10, whose tag-6 path uses MethodSpec -> triple -> 8D20.
    require(pe.u32_at_va(pe.image_base+0x4138C+5*4), 0x412AC,
            gate.gameassembly, 0x4138C+5*4)
    if not 0 <= call_index < reg['methodSpecsCount']:
        raise ContextError(str(gate.gameassembly), registration, 'bounded call MethodSpec index', call_index)
    call_va = int(reg['methodSpecs'], 16) + call_index * 12
    call_raw = pe.bytes_at_va(call_va, 12)
    call_definition, call_class, call_method = struct.unpack('<iii', call_raw)
    require((call_definition, call_class, call_method), (owner['methodIndex'], -1, 14693),
            gate.gameassembly, call_va)
    call_inst = table.resolve(call_method)
    ordinal = owner['ordinal']
    if not 0 <= ordinal < len(call_inst.arguments):
        raise ContextError(str(gate.gameassembly), call_inst.record_va,
                           'ordinal within selected call instantiation', ordinal)
    argument = call_inst.arguments[ordinal]
    require(argument.raw_type_record_hex, 'B02D0000000000000000120000000000',
            gate.gameassembly, argument.type_pointer_va)
    module = modules['MemoryPack.dll']
    require(pe.u32_at_va(module+0x40), 120, gate.gameassembly, module+0x40)
    require(pe.u32_at_va(module+0x50), 691, gate.gameassembly, module+0x50)
    ranges_va = pe.u64_at_va(module+0x48)
    start, count = select_rgctx_range(pe.bytes_at_va(ranges_va,120*12),691,0x06000075,
                                      source=str(gate.gameassembly),offset=ranges_va)
    require((start,count),(40,3),gate.gameassembly,ranges_va)
    entry_va = pe.u64_at_va(module+0x58)+(start+1)*16
    entry_raw = pe.bytes_at_va(entry_va,16)
    require(struct.unpack_from('<I',entry_raw)[0],2,gate.gameassembly,entry_va)
    type_index = pe.u32_at_va(struct.unpack_from('<Q',entry_raw,8)[0])
    require(type_index,211958,gate.gameassembly,entry_va)
    require(type_index<reg['typesCount'],True,gate.gameassembly,entry_va)
    type_pointer = pe.u64_at_va(int(reg['types'],16)+type_index*8)
    formatter_type_raw = pe.bytes_at_va(type_pointer,16)
    carrier_raw = pe.bytes_at_va(struct.unpack_from('<Q',formatter_type_raw)[0],32)
    base_raw = pe.bytes_at_va(struct.unpack_from('<Q',carrier_raw)[0],16)
    formatter_carrier = generic_type_carrier(formatter_type_raw,carrier_raw,base_raw,
                                             type_pointer=type_pointer,type_count=len(md.types),source=str(gate.gameassembly))
    formatter_inst = table.resolve_pointer(formatter_carrier['classInstantiationPointerVa'])
    require(formatter_inst.index, selected.index, gate.gameassembly,formatter_inst.record_va)
    require(formatter_carrier['baseDefinitionIndex'],54005,gate.metadata)
    require(md.type_full_name(md.types[54005]),'MemoryPack.MemoryPackFormatter`1',gate.metadata)
    require(pe.u32_at_va(pe.image_base+0x9850+(0x15-0xF)*4),0x979D,gate.gameassembly,0x9850)
    # Static immediate-registration site: identity joins only, not live state.
    adapter_cells = []
    for rva, opcode, tag, expected_index in (
            (0x2B00F2B, '488B0D', 1, 205127),
            (0x2B00F4C, '488B15', 6, 559804),
            (0x2B00F60, '488B05', 2, 120613),
            (0xB2830, '488B15', 6, 559804)):
        instruction = pe.bytes_at_va(pe.image_base+rva, 7)
        require(instruction[:3], bytes.fromhex(opcode), gate.gameassembly, rva)
        cell = rip_qword_load_target(instruction,pe.image_base+rva,source=str(gate.gameassembly))
        cell_raw = pe.bytes_at_va(cell, 8)
        index = unresolved_usage_index(cell_raw, reg['methodSpecsCount'] if tag == 6 else reg['typesCount'],
                                       tag=tag, source=str(gate.gameassembly), offset=cell)
        require(index, expected_index, gate.gameassembly, cell)
        adapter_cells.append({'instructionRva':rva, 'instructionHex':instruction.hex().upper(),
                              'cellVa':cell, 'rawHex':cell_raw.hex().upper(), 'tag':tag, 'index':index})
    require(adapter_cells[1]['cellVa'], adapter_cells[3]['cellVa'], gate.gameassembly)
    adapter_pointer = pe.u64_at_va(int(reg['types'],16)+205127*8)
    adapter_raw = pe.bytes_at_va(adapter_pointer,16)
    adapter_carrier_raw = pe.bytes_at_va(struct.unpack_from('<Q',adapter_raw)[0],32)
    adapter_base_raw = pe.bytes_at_va(struct.unpack_from('<Q',adapter_carrier_raw)[0],16)
    adapter = generic_type_carrier(adapter_raw,adapter_carrier_raw,adapter_base_raw,
                                   type_pointer=adapter_pointer,type_count=len(md.types),source=str(gate.gameassembly))
    require(adapter['baseDefinitionIndex'],13633,gate.metadata)
    require(md.type_full_name(md.types[13633]),'Beyond.MemoryPack.GenericMemoryPackFormatter`2',gate.metadata)
    adapter_inst = table.resolve_pointer(adapter['classInstantiationPointerVa'])
    require(adapter_inst.index,38555,gate.gameassembly)
    require(len(adapter_inst.arguments),2,gate.gameassembly)
    adapter_module=modules['MemoryPack.Beyond.dll']
    require(image_owners[13633],1,gate.metadata)
    require(md.types[13633].token,0x0200000B,gate.metadata)
    require(pe.u32_at_va(adapter_module+0x40),5,gate.gameassembly,adapter_module+0x40)
    adapter_ranges=pe.u64_at_va(adapter_module+0x48)
    adapter_entry_base,adapter_entry_bytes=module_rgctx_bytes['MemoryPack.Beyond.dll']
    adapter_start,adapter_count=select_rgctx_range(pe.bytes_at_va(adapter_ranges,5*12),len(adapter_entry_bytes)//16,
                                                   md.types[13633].token,source=str(gate.gameassembly),offset=adapter_ranges)
    require((adapter_start,adapter_count),(4,13),gate.gameassembly,adapter_ranges)
    adapter_entries=rgctx_range_entries(adapter_entry_bytes,adapter_start,adapter_count,
                                        source=str(gate.gameassembly),offset=adapter_entry_base)
    type_slot=adapter_entries[10]
    require(pe.bytes_at_va(pe.image_base+0x2DA8E66,15),bytes.fromhex('488B4320488B98C0000000488B5B50'),
            gate.gameassembly,0x2DA8E66)
    require(type_slot['kindRaw'],1,gate.gameassembly,type_slot['entryVa'])
    slot_type_index=pe.u32_at_va(type_slot['dataPointerVa'])
    require(slot_type_index,10486,gate.gameassembly,type_slot['dataPointerVa'])
    require(slot_type_index<reg['typesCount'],True,gate.gameassembly,type_slot['dataPointerVa'])
    slot_type_pointer=pe.u64_at_va(int(reg['types'],16)+slot_type_index*8)
    slot_type_raw=pe.bytes_at_va(slot_type_pointer,16)
    require(slot_type_raw[10],0x13,gate.gameassembly,slot_type_pointer+10)
    slot_owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',slot_type_raw)[0],
                                    [t.generic_container_index for t in md.types],source=str(gate.metadata))
    require((slot_owner['typeIndex'],slot_owner['ordinal']),(13633,1),gate.metadata,slot_owner['containerOffset'])
    require(pe.u32_at_va(pe.image_base+0x9850+(0x13-0x0F)*4),0x9669,gate.gameassembly,0x9850)
    slot_argument=adapter_inst.arguments[slot_owner['ordinal']]
    nested_slots=[]
    for relative,expected_definition in ((3,102198),(4,428394),(11,277939)):
        entry=adapter_entries[relative]
        require(entry['kindRaw'],3,gate.gameassembly,entry['entryVa'])
        index=pe.u32_at_va(entry['dataPointerVa'])
        require(index<reg['methodSpecsCount'],True,gate.gameassembly,entry['dataPointerVa'])
        spec_va=int(reg['methodSpecs'],16)+index*12
        spec_raw=pe.bytes_at_va(spec_va,12)
        definition,ci,mi=method_spec_record(spec_raw,len(md.methods),reg['genericInstsCount'],
                                           source=str(gate.gameassembly),offset=spec_va)
        require(definition,expected_definition,gate.metadata)
        contexts=[]
        for kind,inst_index in (('class',ci),('method',mi)):
            inst=table.resolve(inst_index)
            arguments=[]
            for arg in inst.arguments:
                raw=bytes.fromhex(arg.raw_type_record_hex)
                require(raw[10],0x13,gate.gameassembly,arg.type_pointer_va+10)
                owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',raw)[0],
                                            [t.generic_container_index for t in md.types],source=str(gate.metadata))
                require(owner['typeIndex'],13633,gate.metadata,owner['containerOffset'])
                require(owner['ordinal']<len(adapter_inst.arguments),True,gate.metadata,owner['parameterOffset'])
                concrete=adapter_inst.arguments[owner['ordinal']]
                arguments.append({'rawHex':arg.raw_type_record_hex,'owner':owner,
                                  'conditionalArgumentRawHex':concrete.raw_type_record_hex})
            contexts.append({'kind':kind,'instantiationIndex':inst_index,'arguments':arguments})
        nested_slots.append({'relativeIndex':relative,'moduleEntryIndex':entry['moduleEntryIndex'],
                             'methodSpecIndex':index,'methodSpecRawHex':spec_raw.hex().upper(),
                             'definition':definition,'methodName':md.string(md.methods[definition].name_index),'contexts':contexts})
    require(pe.bytes_at_va(pe.image_base+0x8619,4),bytes.fromhex('48895F20'),gate.gameassembly,0x8619)
    require(pe.bytes_at_va(pe.image_base+0x873E,17),bytes.fromhex('4D8D442408498BD5488D4DD8E8D1470300'),
            gate.gameassembly,0x873E)
    require([a.raw_type_record_hex for a in adapter_inst.arguments],
            ['B02D0000000000000000120000000000','2D360000000000000000120000000000'],gate.gameassembly)
    require(md.type_full_name(md.types[13869]),'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack',gate.metadata)
    key_pointer = pe.u64_at_va(int(reg['types'],16)+120613*8)
    require(key_pointer,adapter_inst.arguments[0].type_pointer_va,gate.gameassembly)
    ctor_va = int(reg['methodSpecs'],16)+559804*12
    ctor_raw = pe.bytes_at_va(ctor_va,12)
    require(struct.unpack('<iii',ctor_raw),(102200,38555,-1),gate.gameassembly,ctor_va)
    require(md.methods[102200].declaring_type,13633,gate.metadata)
    require(md.string(md.methods[102200].name_index),'.ctor',gate.metadata)
    require(pe.bytes_at_va(pe.image_base+0x867C0,5),bytes.fromhex('E99BAAFBFF'),gate.gameassembly,0x867C0)
    require(pe.bytes_at_va(pe.image_base+0xB2837,5),bytes.fromhex('E9741DFD03'),gate.gameassembly,0xB2837)
    storage_references = []
    for rva in (0x3800409,0x2DA4806,0x2DA49F5,0x2DA4C42):
        instruction = pe.bytes_at_va(pe.image_base+rva,7)
        target = rip_qword_load_target(instruction,pe.image_base+rva,source=str(gate.gameassembly))
        require(target,pe.image_base+0xD0EF5F0,gate.gameassembly,rva)
        storage_references.append({'instructionRva':rva,'instructionHex':instruction.hex().upper(),'targetVa':target})
    storage_raw = pe.bytes_at_va(storage_references[0]['targetVa'],8)
    sharing_instruction = pe.bytes_at_va(pe.image_base+0x2C6DE0,7)
    sharing_global = class_sharing_branch(pe.bytes_at_va(pe.image_base+0x2C6CA9,10),pe.image_base+0x2C6CA9,
                                          sharing_instruction,pe.image_base+0x2C6DE0,
                                          pe.bytes_at_va(pe.image_base+0x2C6DE7,4),source=str(gate.gameassembly))
    require(sharing_global,pe.image_base+0xDE9F470,gate.gameassembly,0x2C6DE0)
    require([bytes.fromhex(a.raw_type_record_hex)[10] for a in adapter_inst.arguments],[0x12,0x12],gate.gameassembly)
    object_identity = named_top_level_type(md.buf,b'mscorlib.dll',b'System',b'Object',source=str(gate.metadata))
    require((object_identity['imageIndex'],object_identity['typeDefinitionIndex'],object_identity['byvalTypeIndex']),
            (6,36358,133396),gate.metadata,object_identity['typeDefinitionOffset'])
    require(object_identity['byvalTypeIndex']<reg['typesCount'],True,gate.metadata)
    object_pointer=pe.u64_at_va(int(reg['types'],16)+object_identity['byvalTypeIndex']*8)
    object_raw=pe.bytes_at_va(object_pointer,16)
    require(object_raw.hex().upper(),'068E00000000000000001C0000000000',gate.gameassembly,object_pointer)
    object_pair=table.resolve(1088)
    require([a.raw_type_record_hex for a in object_pair.arguments],[object_raw.hex().upper()]*2,gate.gameassembly)
    # The code window ends before this separately read switch-data entry.
    switch_entry=pe.image_base+0x2CC87C+(0x1C-0x0F)*4
    require(pe.u32_at_va(switch_entry),0x2CC840,gate.gameassembly,switch_entry)
    object_key=object_type_comparison_key(object_raw,source=str(gate.gameassembly),offset=object_pointer)
    require(summary['failed'],0,'complete generic-instantiation sweep before candidate enumeration')
    object_candidates=[]
    for row in rows:
        arguments=row['arguments']
        if len(arguments)!=2:
            continue
        raw_arguments=[bytes.fromhex(a['raw_type_record_hex']) for a in arguments]
        if any(raw[10]!=0x1C for raw in raw_arguments):
            continue
        keys=[object_type_comparison_key(raw,source=str(gate.gameassembly),offset=a['type_pointer_va'])
              for raw,a in zip(raw_arguments,arguments)]
        if keys==[object_key,object_key]:
            object_candidates.append(row['index'])
    require(md.methods[102199].declaring_type,13633,gate.metadata)
    require(md.string(md.methods[102199].name_index),'Deserialize',gate.metadata)
    specs_base=int(reg['methodSpecs'],16)
    specs_raw=pe.bytes_at_va(specs_base,reg['methodSpecsCount']*12)
    spec_records=[method_spec_record(specs_raw[index*12:(index+1)*12],len(md.methods),reg['genericInstsCount'],
                                     source=str(gate.gameassembly),offset=specs_base+index*12)
                  for index in range(reg['methodSpecsCount'])]
    validate_selected_method_spec(selected_method_spec,specs_raw,specs_base,len(md.methods),
                                   reg['genericInstsCount'],source=str(gate.gameassembly))
    shared_specs=[index for index,(definition,ci,mi) in enumerate(spec_records)
                  if definition==102199 and ci in object_candidates and mi==-1]
    code=mapper.code_registration_summary(pe,candidates[0])
    methods_base=int(reg['genericMethodTable'],16)
    methods_raw=pe.bytes_at_va(methods_base,reg['genericMethodTableCount']*16)
    shared_rows=[]
    for index,(spec_index,_,_,_) in enumerate(struct.iter_unpack('<iiii',methods_raw)):
        if spec_index not in shared_specs:
            continue
        triple_raw=methods_raw[index*16+4:index*16+16]
        method,invoker,adjustor=method_pointer_indices(triple_raw,code['genericMethodPointersCount'],
                                                       code['invokerPointersCount'],source=str(gate.gameassembly),
                                                       offset=methods_base+index*16+4)
        pointer=pe.u64_at_va(int(code['genericMethodPointers'],16)+method*8)
        invoker_pointer=pe.u64_at_va(int(code['invokerPointers'],16)+invoker*8)
        require(pointer!=0 and invoker_pointer!=0,True,gate.gameassembly,methods_base+index*16)
        shared_rows.append({'tableIndex':index,'methodSpecIndex':spec_index,
                            'indices':[method,invoker,adjustor],'indicesRawHex':triple_raw.hex().upper(),
                            'methodPointerVa':pointer,'invokerPointerVa':invoker_pointer})
    producer_names=[]
    for rva,prefix,expected in ((0x15F0D,'488D0D',b'mscorlib.dll'),
                               (0x15F3C,'4C8D05',b'Object'),(0x15F43,'488D15',b'System')):
        instruction=pe.bytes_at_va(pe.image_base+rva,7)
        require(instruction[:3],bytes.fromhex(prefix),gate.gameassembly,rva)
        pointer=pe.image_base+rva+7+struct.unpack_from('<i',instruction,3)[0]
        require(pe.bytes_at_va(pointer,len(expected)+1),expected+b'\0',gate.gameassembly,pointer)
        producer_names.append({'instructionRva':rva,'stringVa':pointer,'ascii':expected.decode('ascii')})
    require(pe.bytes_at_va(pe.image_base+0x15F4F,7),bytes.fromhex('4889051A95E80D'),gate.gameassembly,0x15F4F)
    # Independently connect the registration producer to the cache seeding loop.
    # These are reviewed instruction boundaries inside the pinned consumers.
    producer=pe.bytes_at_va(pe.image_base+0x15E5A,7)
    require(producer[:3],bytes.fromhex('488D05'),gate.gameassembly,0x15E5A)
    require(pe.image_base+0x15E61+struct.unpack_from('<i',producer,3)[0],registration,gate.gameassembly,0x15E5A)
    require(pe.bytes_at_va(pe.image_base+0x15E6F,7),bytes.fromhex('4889054AABE90D'),gate.gameassembly,0x15E6F)
    seed_global=rip_qword_load_target(pe.bytes_at_va(pe.image_base+0x12D70,7),pe.image_base+0x12D70,source=str(gate.gameassembly))
    require(seed_global,pe.image_base+0xDEB09C0,gate.gameassembly,0x12D70)
    cache_storage=[]
    for rva in (0x9D16,0x13248):
        target=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=str(gate.gameassembly))
        require(target,pe.image_base+0xDEB0568,gate.gameassembly,rva)
        cache_storage.append({'instructionRva':rva,'storageGlobalVa':target})
    return_evidence=serializer_return_consumers(pe,source=str(gate.gameassembly))
    return_evidence['methodIdentities']=module_methods(pe,md,modules,image_owners,
        [(428657,'MemoryPack.MemoryPackSerializer','Deserialize',0x970BFBC),
         (428658,'MemoryPack.MemoryPackSerializer','Deserialize',0x970C4A8),
         (428655,'MemoryPack.MemoryPackSerializer','Deserialize',0x970BFF0),
         (428667,'MemoryPack.MemoryPackSerializer+<DeserializeAsync>d__11','MoveNext',0x9711078)],
        source=str(gate.gameassembly))
    construction_evidence=reader_construction(pe,md,modules,image_owners,source=str(gate.gameassembly))
    cursor_evidence=reader_cursor_consumers(pe,source=str(gate.gameassembly))
    wrapper_evidence=wrapper_consumer(pe,md,reg,table,source=str(gate.gameassembly))
    resource_evidence=skill_resource_context(pe,md,modules,image_owners,table,reg,code,
        spec_records,specs_raw,methods_raw,source=str(gate.gameassembly))
    carrier_evidence=resource_carrier_consumers(pe,source=str(gate.gameassembly))
    stream_identity=stream_source_identity(pe,md,modules,image_owners,reg,code,spec_records,methods_raw,source=str(gate.gameassembly))
    stream_consumer=stream_carrier_consumer(pe,source=str(gate.gameassembly))
    native_gate()
    require(sha(corpus_path), CORPUS_SHA, corpus_path)
    verify_current_report_inputs(corpus)
    for path, expected in source_hashes.items():
        require(sha(path), expected, path)
    return {
        'schemaVersion': 1, 'status': 'failed' if failures else 'structural-only',
        'inputSetSha256': corpus['inputSetSha256'],
        'corpusReference': {'path': str(corpus_path), 'sha256': CORPUS_SHA,
                            'boundary': 'Authenticated corpus reference; this native audit does not restream VFS bytes.'},
        'nativeInputs': {'gameassembly': str(gate.gameassembly), 'gameassemblySha256': GA_SHA,
                         'metadata': str(gate.metadata), 'metadataSha256': MD_SHA},
        'sourceHashes': source_hashes, 'registration': reg,
        'methodSpecSweep':{'success':len(spec_records),'failed':0,'unsupported':0,
                           'sourceVa':specs_base,'byteLength':len(specs_raw),
                           'sha256':hashlib.sha256(specs_raw).hexdigest().upper(),
                           'boundary':'All referenced 12-byte MethodSpecs have bounded definition and class/method instantiation indices. This is not runtime inflation or whole-PE EOF.'},
        'selectedSerializerReturnConsumers':return_evidence,
        'selectedSkillResourceContext':resource_evidence,
        'selectedResourceCarrierConsumers':carrier_evidence,
        'selectedStreamSourceIdentity':stream_identity,
        'selectedStreamCarrierConsumer':stream_consumer,
        'selectedReaderConstruction':construction_evidence,
        'selectedReaderCursorConsumers':cursor_evidence,
        'selectedWrapperConsumer':wrapper_evidence,
        'selectedNestedAdapterSlots':{'rows':nested_slots,'level':'exact static MethodSpec/VAR relation',
                                      'boundary':'Relative slots 3, 4 and 11 independently join DeserializeNotNull<T0,T1>, GetFormatter<T1> and CreateInstance<T1>. Every VAR reciprocally belongs to the adapter type; conditional concrete arguments come from the separately authenticated immediate registration. Method names do not establish serialization order, actual nested dispatch or source cursor.'},
        'selectedMethodCompanionConstruction': {'lookupRva':0x8D20,'constructorRva':0x84B0,
                                                 'classStoreRva':0x8619,'methodPointerResolverCallRva':0x874A,
                                                 'classFieldOffset':0x20,'pointerFieldOffsets':[0,8,16],
                                                 'level':'direct conditional native construction path',
                                                 'boundary':'On the reviewed cache-miss construction path, the original definition class and class-instantiation feed the generic-class carrier lookup/construction, then the class pointer is stored at MethodInfo+0x20. The pointer resolver receives the original definition and context pair separately, writes a stack result, and its code/adjustor/invoker pointers are copied to MethodInfo+0/+8/+0x10. Normalizing arguments for a shared code lookup therefore does not itself replace the already stored original class pointer. This is not a live MethodInfo receipt, proof of cache contents, actual target invocation, source extent or EOF.'},
        'rgctxDefinitionSweep': {'images':rgctx_inventory,
                                  'summary':{'success':sum(x['success'] for x in rgctx_inventory),'failed':0,'unsupported':0},
                                  'boundary':'Exact referenced 16-byte definitions for every matched module; numeric kinds, padding and payload pointers are preserved, not resolved runtime slots or a partition of the PE.'},
        'selectedAdapterClassSlot': {'typeDefinition':13633,'token':md.types[13633].token,
                                     'rangeStart':adapter_start,'rangeCount':adapter_count,'entries':adapter_entries,
                                     'selectedRelativeIndex':10,'selectedModuleEntryIndex':type_slot['moduleEntryIndex'],
                                     'consumerRva':0x2DA8E66,'runtimeSlotByteOffset':0x50,
                                     'typeIndex':slot_type_index,'typePointerVa':slot_type_pointer,
                                     'typeRawHex':slot_type_raw.hex().upper(),'parameterOwner':slot_owner,
                                     'conditionalContextArgument':{'pointerVa':slot_argument.type_pointer_va,'rawHex':slot_argument.raw_type_record_hex},
                                     'level':'exact static slot/VAR identity; direct conditional class-context connection',
                                     'boundary':'The class initializer reads class+0x118 token and image+0x38 module, uses 12-byte token ranges and 16-byte definitions, emits eight-byte slots at class+0xC0, and supplies generic-carrier+8 context to substitution. Relative slot 10 is module entry 14, kind 1, a reciprocal ordinal-1 VAR of the adapter type. The VAR branch uses the class instantiation, whose second argument at the immediate registration is the wrapper type. This does not certify initialized class contents, actual method companion, formatter cache selection, source length or EOF.'},
        'selectedSharedMethodCandidates': {'definition':102199,'methodSpecIndices':shared_specs,
                                           'rows':shared_rows,'level':'exact static table relation; conditional index consumer',
                                           'boundary':'All matching MethodSpecs and generic-method table rows are preserved. The separately pinned index reader checks method/invoker indices, loads their pointer slots, and with adjustor -1 reuses the method pointer. Non-sentinel adjustors remain unsupported by this bounded decoder. This does not certify the runtime triple-map population, query success, target invocation, actual reader ABI, source length or final cursor.'},
        'selectedObjectComparison': {'key':object_key,'matchingRegisteredInstantiations':object_candidates,
                                     'switchEntryVa':switch_entry,'switchTargetRva':0x2CC840,
                                     'level':'direct conditional native equality/hash projection',
                                     'boundary':'For object-tag records the reviewed comparator checks the tag and bit 29 of the word at +8, then returns equal; the reviewed hash branch depends on those same two values. Record addresses and other bytes do not participate in this branch. The complete registered-instance sweep enumerates every matching two-argument candidate without selecting one. Even a singleton does not prove cache execution, returned interned pointer, method lookup success, active formatter or file cursor.'},
        'selectedInstantiationCacheSeed': {'registrationGlobalVa':seed_global,
                                          'seedCallRva':0x12D8B,'insertRva':0x13170,
                                          'lookupRva':0x9C70,'storageReferences':cache_storage,
                                          'level':'direct conditional native producer/consumer connection',
                                          'boundary':'The initializer stores the selected MetadataRegistration and calls the seed routine. Its normal loop reads count+0x10 and pointer-table+0x18, passes each eight-byte slot to insertion, and insertion dereferences that slot to a record pointer. Insertion and lookup access the identical cache storage global and compare argument counts plus native type comparisons. This establishes a static registration-to-cache seed path, not successful initialization, cold-path completion, actual cache contents, interned pointer selection or active formatter dispatch.'},
        'selectedObjectIdentity': {'metadata':object_identity,'producerNames':producer_names,
                                   'registeredTypePointerVa':object_pointer,'rawTypeHex':object_raw.hex().upper(),
                                   'objectPairInstantiation':object_pair.as_dict(),
                                   'level':'exact static identity; direct conditional producer/class-copy connection',
                                   'boundary':'The initializer supplies mscorlib.dll/System/Object to the lookup chain and stores its return in the sharing global. Name-cache construction uses metadata namespace/name and lookup compares both strings, not only hashes. The matched TypeDef reaches the class cache; the miss constructor copies the registered byval type record to class+0x20. This links the normal producer to System.Object record bytes and the static object/object candidate pair. Runtime image/name/class-cache population, initialization execution and interned pointer identity remain unobserved; no active Deserialize or file-cursor selection follows.'},
        'selectedSharingBranch': {'argumentTags':[0x12,0x12], 'normalizerRva':0x2C6C10,
                                  'canonicalCarrierGlobalVa':sharing_global,'carrierTypeOffset':0x20,
                                  'level':'direct conditional native branch; producer identity recorded separately',
                                  'boundary':'On an original-context lookup miss, the reviewed method-pointer resolver transforms class and method argument vectors and retries the triple lookup. Each non-null class-tag argument directly becomes the same global carrier+0x20, preserving vector order/count before interning. The normal producer links to System.Object bytes, but initialization execution, interned vector identity, lookup-table population, cold paths and actual invocation are not established; this does not select the object/object Deserialize candidate. The normalizer code ends before its separately located eight-dword switch table.'},
        'selectedProviderStorage': {'references':storage_references,'cellRawHex':storage_raw.hex().upper(),
                                    'level':'direct conditional consumer connection',
                                    'boundary':'Registration and GetFormatter read the identical RIP cell, then class+0xB8 and static-carrier+0x18. Direct lookup traverses that storage and returns a matched node+0x18 through the local result slot. A miss can invoke lazy callbacks, retry lookup, or construct and register other values. Static storage identity does not establish live contents, comparer results, initialization/replacement history or selected adapter dispatch.'},
        'selectedImmediateAdapter': {'cells':adapter_cells, 'typeCarrier':adapter,
                                    'argumentTypeNames':['Beyond.Gameplay.Core.GameplayTagList','Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack'],
                                    'classInstantiation':adapter_inst.as_dict(),
                                    'constructorMethodSpecVa':ctor_va,'constructorRawHex':ctor_raw.hex().upper(),
                                    'level':'exact static identity; direct conditional registration callsite',
                                    'boundary':'The type carrier and constructor share the ordered Core/ForMemoryPack instance, and the Core key uses the identical registered type pointer. The reviewed callsite passes the constructed-object stack slot and type-derived key to a registration function which forwards them to static-carrier+0x18 storage. This does not establish execution, allocation/constructor ABI completion, live cache selection, adapter Deserialize dispatch, source length or final cursor.'},
        'selectedFormatterTypeCarrier': {**formatter_carrier,'rgctxEntryVa':entry_va,
                                         'rgctxEntryRawHex':entry_raw.hex().upper(),
                                         'classInstantiationIndex':formatter_inst.index,
                                         'baseName':md.type_full_name(md.types[54005]),
                                         'boundary':'Exact static pointer/range/MVAR identity; the 32-byte carrier window is not a certified allocation extent and its last 16 bytes remain opaque. Native generic inflation iterates the class-inst arguments using the supplied context. This is the open formatter check type, not the active formatter object or proof that runtime inflation/caches executed.'},
        'selectedUsageCell': {'va': usage_va, 'rawHex': usage_raw.hex().upper(),
                              'methodSpecIndex': call_index, 'resolverSwitchEntryRva': 0x4138C+5*4,
                              'boundary': 'Direct static initialization mechanism: the guarded wrapper passes this cell address to the lazy resolver; tag 6 routes through MethodSpec/triple lookup and a non-null result is exchanged into the cell. The callsite reads the same cell. Initialization execution, cache history, active formatter and source cursor remain unobserved.'},
        'staticImageOwnership': {'typeCount': len(image_owners), 'images': image_rows,
                                 'selectedReadValueImage': image_owners[md.methods[428464].declaring_type],
                                 'registrationGlobalRva': 0xDEB09B8,
                                 'matchingRule': 'Native bytewise name matching continues after a match; duplicate names could overwrite a prior result. This gate requires unique module names before accepting a static join.',
                                 'boundary': 'Exact metadata type partition and unique module-name joins. Native normal-path directory stores and name comparisons are separately pinned; initialization execution, cold paths and live invocation remain unobserved.'},
        'consumerWindows': CONSUMER_WINDOWS, 'summary': summary,
        'selectedMethodSpec': selected_method_spec,
        'selectedCallMethodSpec': {'index': call_index, 'va': call_va, 'rawHex': call_raw.hex().upper(),
                                   'methodInstantiation': call_inst.as_dict()},
        'conditionalSubstitution': {
            'ordinal': ordinal, 'selectedRawArgument': argument.raw_type_record_hex,
            'level': 'exact static joins; conditional runtime application',
            'boundary': 'The open parameter belongs to the selected call definition and its ordinal indexes this registered argument. The native leaf applies that ordinal to its supplied live context. This report does not establish that the actual invocation supplies this context.'},
        'boundary': 'Pointer array -> 16-byte record -> argument pointer array -> raw 16-byte type records only. No live generic context, formatter, field order, source cursor or EOF claim.',
        'failures': failures, 'rows': rows,
    }


def main():
    try:
        report = audit()
    except (ContextError, OSError, ValueError) as error:
        print(json.dumps({'status': 'failed', 'diagnostic': getattr(error, 'diagnostics', getattr(error, 'diagnostic', str(error)))}), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
