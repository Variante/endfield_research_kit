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
from scripts.game_data.il2cpp_context import method_pointer_indices
from scripts.game_data.il2cpp_context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp_context import method_spec_record, usage_method_spec

ROOT = Path(__file__).resolve().parents[2]
GA_SHA = 'C24495E51B406F03B03890C4788EE618AE022C991405BE5D5B8B787CB775AE89'
MD_SHA = '0076743397ACADF03D3B0064343A963C7C88863B8160526D397E4B3EFB96F02E'
CORPUS_SHA = '3B2B96545D1A17FFA4F7770B2BA7AF6045E4BDE701465AD42E2AFB0FA6D05943'
CONSUMER_WINDOWS = (
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
            'boundary':'The formatter forwards its reader unchanged to the wrapper reader. The fast path consumes one byte using remaining+0x30, cursor+0x50 and counters+0x40/+0x44. Header 0xFF clears the output; non-null header 1 reaches the nested call with the same reader and the recorded List instantiation. Other headers reach a helper then INT3. Cold ensure/advance delegates remain opaque; their return branches rejoin the reviewed header path. No list element layout, actual provider selection, authenticated source allocation, source extent or final cursor is established.'}


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
    wrapper_evidence=wrapper_consumer(pe,md,reg,table,source=str(gate.gameassembly))
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
