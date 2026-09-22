"""MemoryPack reader and BuffData consumer validations.

Moved verbatim out of ``context_audit``; that module owns the audit
contract and the report it assembles.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from scripts.game_data.il2cpp.context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.il2cpp.context import named_top_level_type
from scripts.game_data.il2cpp.context import method_pointer_indices, generic_method_candidates
from scripts.game_data.il2cpp.context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp.context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.il2cpp.context_audit_common import CONSUMER_WINDOWS, require, sha


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


def buff_tag76_read_order(pe,md,reg,table,modules,image_owners,*,source):
    """Current anonymous tag-76 profile; no live list formatter or field names."""
    wrapper='Beyond.MemoryPack.Beyond_Gameplay_Core_Conditions_CheckSkillId_DataForMemoryPack'
    element='Beyond.MemoryPack.Beyond_Blackboard_BlackboardStringForMemoryPack'
    methods=module_methods(pe,md,modules,image_owners,
        [(124595,wrapper,'Deserialize',0x3F7FD80),
         (124596,wrapper+'+Beyond_Gameplay_Core_Conditions_CheckSkillId_DataForMemoryPackFormatter','Deserialize',0x3F7FD20),
         (162686,element,'Deserialize',0x3D9BB50),
         (162687,element+'+Beyond_Blackboard_BlackboardStringForMemoryPackFormatter','Deserialize',0x3D9BAF0)],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in (
        (0x3F7FD49,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
        (0x3F7FE00,'4080FE050F85635BFD00'),
        (0x3D9BB19,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
        (0x3D9BBD5,'4080FD030F85E0621701'),
        (0x2CA8729,'488B43504863388B733083EE040F885C8CE30148834350048343400483434404897330'),
        (0x2CA874C,'48634344488B4B18482BC8483BCF0F8C528CE30183FFFF743785FF7517'),
        (0x2CA8780,'4533C08BD7488BCB488B5C2430488B7424384883C4205FE974020000'),
        (0x2CA8A97,'4533C9448BC7488BD5488BCEE878F8FFFF488BE885FF7418'),
        (0x2CA8AAF,'8B73302BF70F88B0A4F70148017B50017B40017B44897330')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    calls=[]
    for at,target in ((0x3F7FDB6,0x2CA8860),(0x3F7FE10,0x2CA88C0),
        (0x3F7FE39,0x2CA86B0),(0x3F7FE5A,0x2CA86B0),(0x3F7FE7B,0x2CA86B0),
        (0x3F7FEA3,0x381F8F0),(0x3D9BBE5,0x2CA8700),
        (0x3D9BC13,0x2CA88C0),(0x3D9BC37,0x2CA8700)):
        raw=pe.bytes_at_va(pe.image_base+at,5);require(raw[:1],b'\xe8',source,at)
        require(relative_branch_target(raw,pe.image_base+at,source=source),pe.image_base+target,source,at)
        calls.append({'rva':at,'targetRva':target})
    at=pe.image_base+0x3F7FE96
    cell=rip_qword_load_target(pe.bytes_at_va(at,7),at,source=source)
    require(cell,pe.image_base+0xD039688,source,at)
    usage=pe.bytes_at_va(cell,8)
    require(method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell),610878,source,cell)
    va=int(reg['methodSpecs'],16)+610878*12;raw=pe.bytes_at_va(va,12)
    require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),(428462,-1,62664),source,va)
    instance=table.resolve(62664)
    require(len(instance.arguments),1,source)
    arg=instance.arguments[0];tr=bytes.fromhex(arg.raw_type_record_hex)
    require(tr,bytes.fromhex('A834258D010000000000150000000000'),source)
    cp=struct.unpack_from('<Q',tr)[0];cr=pe.bytes_at_va(cp,32)
    require(len(cr),32,source,cp)
    bp=struct.unpack_from('<Q',cr)[0]
    require(bp!=0,True,source,cp)
    carrier=generic_type_carrier(tr,cr,pe.bytes_at_va(bp,16),type_pointer=arg.type_pointer_va,type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],37521,source,bp)
    require(md.type_full_name(md.types[37521]),'System.Collections.Generic.List`1',source)
    nested=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(nested.index,17007,source)
    require([a.raw_type_record_hex for a in nested.arguments],['B1000000000000000000120000000000'],source)
    require(md.type_full_name(md.types[177]),'Beyond.Blackboard+BlackboardString',source)
    return {'methods':methods,'windows':windows,'orderedCalls':calls,
        'nestedUsageCellVa':cell,'nestedUsageRawHex':usage.hex().upper(),
        'nestedMethodSpecIndex':610878,'nestedMethodSpecRawHex':raw.hex().upper(),
        'methodInstantiation':instance.as_dict(),'listCarrier':carrier,'elementInstantiation':nested.as_dict(),
        'level':'direct conditional consumer order; exact static nested type identity',
        'boundary':'Tag 76 routes to the current wrapper in selectedBuffUnionRoutes. Its member-five path reads one nonzero-normalized byte and three DWORDs before ReadPackable with List<BlackboardString>. The independently joined element reader takes member three, length-prefixed bytes, one normalized byte, then length-prefixed bytes. The length helper reads a signed DWORD: -1 returns null, zero takes an empty path, and positive length is forwarded unchanged to the byte consumer, which advances source/counters by that length after its decoder call. Payload bytes remain anonymous: encoding/cache contents, complete decoder parity, negative values below -1, live list formatter, concrete source carrier and final cursor/EOF are not proven. The maintained finite list profile is structural-only; neither managed names nor output-slot widths establish serialized order or gameplay meaning.'}


def buff_action_read_order(pe,md,reg,table,modules,image_owners,*,source,contract_path):
    """Selected action profile under audit()'s explicit native hash gate."""
    path=Path(contract_path)
    contract=json.loads(path.read_bytes())
    require(contract['schemaVersion'],1,path)
    methods=module_methods(pe,md,modules,image_owners,contract['methods'],
        source=source,expected_image='MemoryPack.Beyond.dll')
    for group in contract.get('methodGroups',[]):
        methods.extend(module_methods(pe,md,modules,image_owners,group['methods'],
            source=source,expected_image=group['image']))
    for row in contract['codeWindows']+contract.get('dataWindows',[]):
        start,end=row['startRva'],row['endRva']
        require(0<=start<end,True,path,start)
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        require(hashlib.sha256(raw).hexdigest().upper(),row['sha256'],source,start)
    for row in contract['nestedContexts']:
        at=pe.image_base+row['instructionRva']
        ins=pe.bytes_at_va(at,7)
        require(ins,bytes.fromhex(row['instructionHex']),source,at)
        cell=rip_qword_load_target(ins,at,source=source)
        require(cell,row['cellVa'],source,at)
        usage=pe.bytes_at_va(cell,8)
        require(usage,bytes.fromhex(row['usageRawHex']),source,cell)
        index=method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell)
        require(index,row['methodSpecIndex'],source,cell)
        va=int(reg['methodSpecs'],16)+index*12
        spec=method_spec_record(pe.bytes_at_va(va,12),len(md.methods),reg['genericInstsCount'],source=source,offset=va)
        require(spec,tuple(row['methodSpec']),source,va)
        instance=table.resolve(spec[2])
        require([a.raw_type_record_hex for a in instance.arguments],[row['argumentRawHex']],source,va)
        argument=bytes.fromhex(row['argumentRawHex'])
        if row.get('generic') is not None:
            require(argument[10],0x15,source,va)
            cp=struct.unpack_from('<Q',argument)[0]
            cr=pe.bytes_at_va(cp,32)
            require(cr,bytes.fromhex(row['generic']['carrierRawHex']),source,cp)
            bp=struct.unpack_from('<Q',cr)[0];br=pe.bytes_at_va(bp,16)
            require(br,bytes.fromhex(row['generic']['baseRawHex']),source,bp)
            carrier=generic_type_carrier(argument,cr,br,type_pointer=instance.arguments[0].type_pointer_va,
                type_count=len(md.types),source=source)
            require(carrier['baseDefinitionIndex'],row['typeDefinition'],source,bp)
            nested=table.resolve_pointer(carrier['classInstantiationPointerVa'])
            require(nested.index,row['generic']['elementInstantiationIndex'],source,cp)
            require([a.raw_type_record_hex for a in nested.arguments],row['generic']['elementArguments'],source,cp)
        else:
            kind=row.get('typeKind',0x12)
            require(kind in (0x11,0x12),True,path,va)
            require(argument[10],kind,source,va)
            require(struct.unpack_from('<Q',argument)[0],row['typeDefinition'],source,va)
        require(0<=row['typeDefinition']<len(md.types),True,source,va)
        require(md.type_full_name(md.types[row['typeDefinition']]),row['typeName'],source,va)
    verified_source_read_calls = verify_contract_source_read_calls(
        pe, contract, source=source)
    return {'contractPath':str(path),'contractSha256':sha(path),'methods':methods,
        'codeWindows':contract['codeWindows'],'dataWindows':contract.get('dataWindows',[]),'nestedContexts':contract['nestedContexts'],
        'anonymousReadOrder':contract['anonymousReadOrder'],
        'verifiedSourceReadCallSites':verified_source_read_calls,
        'level':'direct selected consumer order; exact static nested type joins; structural-only parser profile',
        'boundary':contract['boundary']}


def verify_contract_source_read_calls(pe, contract, *, source):
    """Verify contract-pinned direct source-reader calls against the selected PE."""
    rows = contract.get('sourceReadCallSites', [])
    if not isinstance(rows, list):
        raise ContextError(source, 0, 'sourceReadCallSites array', rows)
    if not rows:
        return []
    read_orders = contract.get('anonymousReadOrder')
    if not isinstance(read_orders, dict) or len(read_orders) != 1:
        raise ContextError(source, 0, 'one root member read-order for source callsites',
                           read_orders)
    root_key, root_order = next(iter(read_orders.items()))
    if not isinstance(root_order, list) or not re.search(r'member\d+$', root_key):
        raise ContextError(source, 0, 'root member-count key and read-order array',
                           [root_key, root_order])
    verified = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ContextError(source, index, f'source read callsite {index} object', row)
        member_index = row.get('memberIndex')
        read_type = row.get('readType')
        instruction_rva = row.get('callInstructionRva')
        target_rva = row.get('targetRva')
        if (type(member_index) is not int or not 0 <= member_index < len(root_order) or
                type(instruction_rva) is not int or type(target_rva) is not int or
                not isinstance(read_type, str)):
            raise ContextError(source, index,
                               f'source read callsite {index} bounded member/RVA fields', row)
        require(root_order[member_index], read_type, source, instruction_rva)
        if instruction_rva in seen:
            raise ContextError(source, instruction_rva,
                               'unique source read call instruction RVA', instruction_rva)
        seen.add(instruction_rva)
        raw = pe.bytes_at_va(pe.image_base + instruction_rva, 5)
        require(raw[:1], b'\xE8', source, instruction_rva)
        target = relative_branch_target(raw, pe.image_base + instruction_rva, source=source)
        require(target, pe.image_base + target_rva, source, instruction_rva)
        verified.append({
            'rootReadOrderKey': root_key,
            'memberIndex': member_index,
            'readType': read_type,
            'callInstructionRva': instruction_rva,
            'instructionByteLength': len(raw),
            'rawHex': raw.hex().upper(),
            'targetRva': target - pe.image_base,
            'classification': 'exact-build direct E8 source-reader call',
        })
    return verified


def buff_sequence_read_order(pe,md,modules,image_owners,*,source):
    """Selected member-three sequence: count, indirect elements, two bytes."""
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_SequenceActionDataForMemoryPack'
    methods=module_methods(pe,md,modules,image_owners,
        [(104346,name,'Deserialize',0x39C6AA0),
         (104347,name+'+Beyond_Gameplay_Core_SequenceActionDataForMemoryPackFormatter','Deserialize',0x39C6A40)],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in (
        (0x39C6A69,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
        (0x39C6B06,'488B43500FB6308B7B3083EF017911BA01000000488BCBE81EB6100284C0750D48FF4350FF4340FF4344897B304080FEFF7516'),
        (0x39C6B82,'4080FE030F85DD030000'),
        (0x39C6BF8,'488B43508B28448B73304183EE047911BA04000000488BCBE82BB5100284C07511488343500483434004834344044489733048634344488B4B18482BC84863C5483BC80F8C78030000'),
        (0x39C6D4D,'488B4738488B4818E806D53DFF4C8BF085ED0F8EB6000000'),
        (0x39C6D98,'4D8B16488BD34863C6498BCE4883C0044D8B8A980100004C8D04C741FF9290010000FFC63BF57CB0EB59'),
        (0x39C6EA2,'488B43500FB6288B7B3083EF017911BA01000000488BCBE882B2100284C0750D48FF4350FF4340FF4344897B30'),
        (0x39C6EE5,'4084ED0F95C0884119'),
        (0x39C6F07,'488B43500FB6288B7B3083EF017911BA01000000488BCBE81DB2100284C0750D48FF4350FF4340FF4344897B30'),
        (0x39C6F47,'4084ED4C8B6C2428488B6C24680F95C04C8B742420884118')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    root_methods=[row for row in methods if row.get('methodIndex')==104346]
    require(len(root_methods),1,source,0x39C6AA0)
    require(root_methods[0].get('pointerVa')-pe.image_base,0x39C6AA0,source,0x39C6AA0)
    root_windows=[(start,end,digest) for start,end,digest in CONSUMER_WINDOWS
                  if start==0x39C6AA0]
    require(root_windows,[(0x39C6AA0,0x39C6FA7,
                           '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90')],
            source,0x39C6AA0)
    root_start,root_end,root_sha=root_windows[0]
    return {'methods':methods,'windows':windows,
        'rootCodeWindow':{'startRva':root_start,'endRva':root_end,'sha256':root_sha},
        'level':'direct conditional selected-consumer structure',
        'boundary':'Header FF clears the output; header 3 takes a signed DWORD count after the one-byte header. The fast count path compares total-minus-consumed with the count, not count times an element width. Count -1 skips elements; zero uses a separate empty-array helper. Positive counts call a provider-selected class+0x190 target with the same reader, an eight-byte array output slot and class+0x198 companion. Output-slot width is not serialized element width. Then two bytes are consumed and nonzero-normalized, writing object offsets 0x19 then 0x18. No semantic field names, live provider identity, negative-count allocation behavior, nested extent, authenticated source cursor or EOF are promoted. Maintained framing rejects counts below -1 conservatively.'}


def buff_ifelse_read_order(pe,md,reg,table,modules,image_owners,*,source):
    """Selected reader's member-eight fast path; no live dispatch or EOF claim."""
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_IfElseAction_IfElseActionDataForMemoryPack'
    methods=module_methods(pe,md,modules,image_owners,
        [(120613,name,'Deserialize',0x3774060),
         (120614,name+'+Beyond_Gameplay_Core_IfElseAction_IfElseActionDataForMemoryPackFormatter','Deserialize',0x3773670)],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in (
        (0x3773699,'4533C0488BD3488BCF488B5C24304883C4205FE9AF090000'),
        (0x3774093,'837B30010F8C089A6B01488B43500FB6288B733083EE010F880B9A6B0148FF4350FF4340FF43448973304080FDFF0F8482010000'),
        (0x37740FA,'4080FD080F85D1996B01'),
        (0x2CA88CF,'83793001488BD90F8CBCA5F701488B43500FB6308B7B3083EF010F88BCA5F70148FF4350FF4340FF4344897B30'),
        (0x2CA8901,'4084F6488B7424380F95C04883C4205FC3'),
        (0x2CA86BF,'83793004488BD90F8C9EA7F701488B43508B308B7B3083EF040F889FA7F70148834350048343400483434404897B30')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    calls=[]
    for at,target,width in ((0x377410A,0x2CA88C0,1),(0x3774135,0x2CA86B0,4),
        (0x3774159,0x2CA86B0,4),(0x377417D,0x2CA86B0,4),(0x37741A1,0x2CA88C0,1),
        (0x37741CA,0x2DA5C90,None),(0x37741F3,0x2DA5C90,None),(0x377421C,0x2DA5C90,None)):
        raw=pe.bytes_at_va(pe.image_base+at,5);require(raw[:1],b'\xe8',source,at)
        require(relative_branch_target(raw,pe.image_base+at,source=source),pe.image_base+target,source,at)
        calls.append({'rva':at,'targetRva':target,'fastSerializedWidth':width})
    operands=[]
    for at in (0x37741BD,0x37741E6,0x377420F):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+at,7),pe.image_base+at,source=source)
        require(cell,pe.image_base+0xCFF4E68,source,at)
        raw=pe.bytes_at_va(cell,8)
        require(method_spec_usage_index(raw,reg['methodSpecsCount'],source=source,offset=cell),619962,source,cell)
        operands.append({'rva':at,'cellVa':cell,'usageRawHex':raw.hex().upper()})
    va=int(reg['methodSpecs'],16)+619962*12;raw=pe.bytes_at_va(va,12)
    require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
            (428464,-1,16408),source,va)
    instance=table.resolve(16408)
    require([a.raw_type_record_hex for a in instance.arguments],['F2230000000000000000120000000000'],source)
    require(9202<len(md.types),True,source)
    require(md.type_full_name(md.types[9202]),'Beyond.Gameplay.Core.SequenceActionData',source)
    root_windows=[(start,end,digest) for start,end,digest in CONSUMER_WINDOWS
                  if start==0x3774060]
    require(root_windows,[(0x3774060,0x37742A8,
                           'AC1FF978FEF71639E74980B43AE00D9746518A9DD94B41772F2867963A596ED8')],
            source,0x3774060)
    root_start,root_end,root_sha=root_windows[0]
    return {'methods':methods,'windows':windows,'orderedCalls':calls,'nestedOperands':operands,
        'nestedMethodSpecIndex':619962,'nestedMethodSpecRawHex':raw.hex().upper(),
        'nestedTypeDefinition':9202,
        'nestedTypeName':'Beyond.Gameplay.Core.SequenceActionData',
        'nestedInstantiation':instance.as_dict(),
        'rootCodeWindow':{'startRva':root_start,'endRva':root_end,
                          'sha256':root_sha},
        'level':'direct selected-consumer order and fast widths; exact nested static type argument',
        'boundary':'The token/module-joined formatter forwards RDX reader and R8 output to the static reader. After a one-byte member header, its header-eight branch passes the same reader to byte/nonzero normalization, three raw DWORD reads, a second byte/nonzero normalization, then three nested helper calls. The fast scalar prefix is 14 bytes after the header; no signedness or gameplay names are assigned. All three nested callsites use one MethodSpec with SequenceActionData as its type argument, not a proven live formatter. Header FF, reused-object preprocessing, allocation/init, other header values and segment-replacement paths are outside this fast-path claim. No nested serialized widths, complete record extent, concrete source cursor or EOF are established.'}


def buff_ifelse_forwarding(pe,md,reg,table,*,source):
    """Exact thunk contexts and conditional reuse flow, not nested field grammar."""
    windows=[]
    for at,expected in (
        (0x30E2DC,'488B15D530DD0CE908165103'),
        (0xA1EA7C,'4C8B053D296C0CE974AC7C08'),
        (0x4E67AA1,'4C8B0518992708488BD3E8CC6FBBFB90E9345FAAFE'),
        (0x91E96FC,'48895C24084889742410574883EC204983783800498BD8488BFA488BF17508488BCBE86D58E6F64C8B4338488BD7488BCE4D8B00488B5C2430488B7424384883C4205FE93C6812F7'),
        (0x30FF80,'E90BFFA303'),
        (0x3D4FE90,'48895C24084889742410574883EC204983783800498BD8488BFA488BF17444488B0D3AF7390983B9E0000000007451488B4338488B08E8954305FF4885C07413B9050000004C8BCF4C8BC6488BD0E81DF42EFC488B5C2430488B7424384883C4205FC3488D0DF6F63909E861132FFC48837B380075A9488BCBE882F02FFCEB9FE8AB632DFCEBA8')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    rows=[]
    for at,index,definition,target in ((0x30E2DC,614208,428462,0x381F8F0),
                                     (0xA1EA7C,618298,428461,0x91E96FC)):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+at,7),pe.image_base+at,source=source)
        usage=pe.bytes_at_va(cell,8)
        require(method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell),index,source,cell)
        va=int(reg['methodSpecs'],16)+index*12;raw=pe.bytes_at_va(va,12)
        require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
                (definition,-1,24608),source,va)
        rows.append({'thunkRva':at,'tailTargetRva':target,'usageCellVa':cell,'usageRawHex':usage.hex().upper(),
                     'methodSpecIndex':index,'methodSpecRawHex':raw.hex().upper(),'methodDefinition':definition})
    instance=table.resolve(24608)
    require([a.raw_type_record_hex for a in instance.arguments],['233F0000000000000000120000000000'],source)
    return {'windows':windows,'contexts':rows,'methodInstantiation':instance.as_dict(),
        'level':'direct conditional register flow; exact static MethodSpec/type argument identity',
        'boundary':'Both C9 branch thunks replace the callsite companion before tail transfer. Their different MethodSpecs have the same single IfElse wrapper argument, independently identified in selectedBuffUnionRoutes. Creation preserves RCX reader and replaces RDX; its target body is not promoted here. Reuse preserves RCX reader and RDX output-slot address, replaces R8, ensures companion+0x38 and forwards its first slot through a tail thunk. The next body takes that companion first slot to the separately reviewed provider, then, only for a non-null result, passes selector 5, provider object, unchanged reader and output slot to 0x3F300. These bodies do not directly read serialized fields. Live provider/formatter and concrete nested consumer ABI remain unresolved; no record length, field order, authenticated source cursor or EOF follows.'}


def buff_union_routes(pe,md,reg,modules,image_owners,*,source):
    """Selected current tag routes, not a replacement serialization schema."""
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack+Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPackFormatter'
    methods=module_methods(pe,md,modules,image_owners,[(107657,name,'Deserialize',0x390D950),
        (107659,name,'.cctor',0x417AC00)],source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in (
        (0x3910618,'488B1589297009'),
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
        (0x3910D20,'488B15A1CA7809488B0BE8F12A6FFC488BCF4885C00F8537835501488B153EC9'),
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
        (0x3910D52,'488B1517677109488B0BE8BF2A6FFC488BCF4885C00F8544835501488B151CF87C09E87FEB10FD488903488BD0E95ECCFFFF'),
        (0x390E2F0,'488B15D9FA7809488B0BE821556FFC488BCF4885C00F85DC805501488B155E3B7D09E841F510FD488903488BD0E9C0F6FFFF'),
        (0x391083E,'488B1593987809488B0BE8D32F6FFC488BCF4885C00F853D625501488B1560127D09E8DFD410FD488903488BD0E972D1FFFF'),
        (0x390FE7A,'488B155F9E7809488B0BE897396FFC488BCF4885C00F85BD6E5501488B152C1D7D09E853E010FD488903488BD0E936DBFFFF'),
        (0x391006E,'488B15D3327009488B0BE8A3376FFC488BCF4885C00F85898C5501488B15E00A7D09E8C3F510FD488903488BD0E942D9FFFF'),
        (0x390F1FA,'488B153F947809488B0BE817466FFC488BCF4885C00F850A855501488B15C41F7D09E837F510FD488903488BD0E9B6E7FFFF'),
        (0x390EBEC,'488B153D2C7809488B0BE8254C6FFC488BCF4885C00F8523AA5501488B152A177D09E81D1111FD488903488BD0E9C4EDFFFF'),
        (0x390E3B8,'488B15712A7809488B0BE859546FFC488BCF4885C00F8553805501488B15663A7D09E8C1F410FD488903488BD0E9F8F5FFFF'),
        (0x390E57A,'488B158F927009488B0BE897526FFC488BCF4885C00F8565A15501488B15DC227D09E8370C11FD488903488BD0E936F4FFFF'),
        (0x39103F2,'488B150F847809488B0BE81F346FFC488BCF4885C00F85E0715501488B154C0D7D09E88BE210FD488903488BD0E9BED5FFFF'),
        (0x390EB56,'488B153B387809488B0BE8BB4C6FFC488BCF4885C00F85587B5501488B15302D7D09E8EBEE10FD488903488BD0E95AEEFFFF'),
        (0x391032A,'488B1577067309488B0BE8E7346FFC488BCF4885C00F8526705501488B15A4147D09E82BE110FD488903488BD0E986D6FFFF'),
        (0x390EFD4,'488B15B51E7309488B0BE83D486FFC488BCF4885C00F85E17D5501488B1532247D09E895EF10FD488903488BD0E9DCE9FFFF'),
        (0x3910938,'488B15E18D7809488B0BE8D92E6FFC488BCF4885C00F85D96A5501488B150E077D09E8C5DB10FD488903488BD0E978D0FFFF'),
        (0x3910B2C,'488B15CD697009488B0BE8E52C6FFC488BCF4885C00F851C7C5501488B15D2FD7C09E809E710FD488903488BD0E984CEFFFF'),
        (0x3910AFA,'488B151F687009488B0BE8172D6FFC488BCF4885C00F85397C5501488B1514FE7C09E823E710FD488903488BD0E9B6CEFFFF'),
        (0x3910C26,'488B15B3257009488B0BE8EB2B6FFC488BCF4885C00F85BC805501488B1540FF7C09E8E7E910FD488903488BD0E98ACDFFFF'),
        (0x3914B16,'488B15D34C7209488B0BE8FBEC6EFC488BCF4885C00F85B4255501488B1518CB7C09E82F9710FD488903488BD0E99A8EFFFF'),
        (0x3914AE4,'488B15A54C7209488B0BE82DED6EFC488BCF4885C00F85D1255501488B1552CB7C09E8559710FD488903488BD0E9CC8EFFFF'),
        (0x390DF08,'488B1519AD7109488B0BE809596FFC488BCF4885C00F8564AF5501488B1596247D09E8011811FD488903488BD0E9A8FAFFFF'),
        (0x390E5AC,'488B15DD447809488B0BE865526FFC488BCF4885C00F853D805501488B1532337D09E811F410FD488903488BD0E904F4FFFF'),
        (0x390ECE6,'488B15E37D7109488B0BE82B4B6FFC488BCF4885C00F859BA45501488B1500197D09E8B70C11FD488903488BD0E9CAECFFFF'),
        (0x390E9C6,'488B15C3137909488B0BE84B4E6FFC488BCF4885C00F85EA8F5501488B1560297D09E8C3FF10FD488903488BD0E9EAEFFFFF'),
        (0x390EAC0,'488B1589706F09488B0BE8514D6FFC488BCF4885C00F8580985501488B158E237D09E8210411FD488903488BD0E9F0EEFFFF'),
        (0x390E034,'488B157D1B7909488B0BE8DD576FFC488BCF4885C00F85289A5501488B1592337D09E8E50911FD488903488BD0E97CF9FFFF'),
        (0x390ED4A,'488B15BFE87809488B0BE8C74A6FFC488BCF4885C00F8586A85501488B157CE97809E8EFE210FD488903488BD0E966ECFFFF'),
        (0x390EEA8,'488B1579767009488B0BE869496FFC488BCF4885C00F85DF985501488B15261A7D09E8D50311FD488903488BD0E908EBFFFF'),
        (0x390F3BC,'488B15358C7109488B0BE855446FFC488BCF4885C00F85979B5501488B1532117D09E8550411FD488903488BD0E9F4E5FFFF'),
        (0x390F22C,'488B15DDFD7809488B0BE8E5456FFC488BCF4885C00F8590895501488B1552217D09E84DF810FD488903488BD0E984E7FFFF'),
        (0x390F006,'488B151B7C7009488B0BE80B486FFC488BCF4885C00F85EE975501488B1598187D09E8BF0211FD488903488BD0E9AAE9FFFF'),
        (0x390F290,'488B15390F7809488B0BE881456FFC488BCF4885C00F85B1755501488B15EE267D09E83DE910FD488903488BD0E920E7FFFF'),
        (0x390F678,'488B15C97D7009488B0BE899416FFC488BCF4885C00F85FA905501488B1566127D09E8EDFB10FD488903488BD0E938E3FFFF'),
        (0x390F420,'488B1551E37809488B0BE8F1436FFC488BCF4885C00F8538835501488B15A6E17809E84DDB10FD488903488BD0E990E5FFFF'),
        (0x390DE0E,'488B15838A6F09488B0BE8035A6FFC488BCF4885C00F8593A35501488B15F02F7D09E8CB0F11FD488903488BD0E9A2FBFFFF'),
        (0x390E868,'488B15F1797109488B0BE8A94F6FFC488BCF4885C00F856DA95501488B153E1D7D09E8951111FD488903488BD0E948F1FFFF'),
        (0x390F3EE,'488B15D3627109488B0BE823446FFC488BCF4885C00F85E79E5501488B1518127D09E8FF0611FD488903488BD0E9C2E5FFFF'),
        (0x390F38A,'488B1567107909488B0BE887446FFC488BCF4885C00F857E855501488B150C1F7D09E857F510FD488903488BD0E926E6FFFF'),
        (0x390F998,'488B15216E6F09488B0BE8793E6FFC488BCF4885C00F85DF875501488B1586147D09E811F410FD488903488BD0E918E0FFFF'),
        (0x390F83A,'488B15DF617009488B0BE8D73F6FFC488BCF4885C00F85EC905501488B15E4107D09E84BFB10FD488903488BD0E976E1FFFF'),
        (0x390F4E8,'488B1589427009488B0BE829436FFC488BCF4885C00F8563975501488B15BE157D09E8C50011FD488903488BD0E9C8E4FFFF'),
        (0x390F6AA,'488B1537E17809488B0BE867416FFC488BCF4885C00F8516985501488B1574DF7809E847D910FD488903488BD0E906E3FFFF'),
        (0x390DF3A,'488B1587BE7809488B0BE8D7586FFC488BCF4885C00F85A68A5501488B15943B7D09E89BFD10FD488903488BD0E976FAFFFF'),
        (0x390F808,'488B1529707009488B0BE809406FFC488BCF4885C00F85D78F5501488B15A6107D09E8A5FA10FD488903488BD0E9A8E1FFFF'),
        (0x390DABC,'488B15E5617009488B0BE8555D6FFC488BCF4885C00F85B5B05501488B1552307D09E8ED07A0FC488903488BD0E9F4FEFFFF'),
        (0x390E192,'488B1537AF7109488B0BE87F566FFC488BCF4885C00F8504AD5501488B15F4217D09E89B1511FD488903488BD0E91EF8FFFF'),
        (0x390F06A,'488B157FAE7709488B0BE8A7476FFC488BCF4885C00F858C735501488B15CC2D7D09E8EBE710FD488903488BD0E946E9FFFF'),
        (0x390FD4E,'488B159B557109488B0BE8C33A6FFC488BCF4885C00F851E965501488B1560097D09E823FE10FD488903488BD0E962DCFFFF'),
        (0x390FD80,'488B1599D87809488B0BE8913A6FFC488BCF4885C00F8565985501488B1526D97809E8D1D210FD488903488BD0E930DCFFFF'),
        (0x390DBB6,'488B153BBF7809488B0BE85B5C6FFC488BCF4885C00F85D9975501488B15E83B7D09E8E70811FD488903488BD0E9FAFDFFFF'),
        (0x391003C,'488B159D387009488B0BE8D5376FFC488BCF4885C00F85248C5501488B157A0A7D09E859F510FD488903488BD0E974D9FFFF'),
        (0x39100D2,'488B15D7D67809488B0BE83F376FFC488BCF4885C00F85D98E5501488B159CD57809E82BCF10FD488903488BD0E9DED8FFFF'),
        (0x390F100,'488B15B9877109488B0BE811476FFC488BCF4885C00F85D59F5501488B153E147D09E8190811FD488903488BD0E9B0E8FFFF'),
        (0x390FE16,'488B159B077809488B0BE8FB396FFC488BCF4885C00F85D7695501488B15A01B7D09E863DD10FD488903488BD0E99ADBFFFF'),
        (0x390FFA6,'488B154B5C6F09488B0BE86B386FFC488BCF4885C00F85AF835501488B15980E7D09E853EF10FD488903488BD0E90ADAFFFF'),
        (0x3910136,'488B15E3537109488B0BE8DB366FFC488BCF4885C00F85A3925501488B1550057D09E877FA10FD488903488BD0E97AD8FFFF'),
        (0x390FAF6,'488B157BF57809488B0BE81B3D6FFC488BCF4885C00F85B1805501488B1598187D09E86BEF10FD488903488BD0E9BADEFFFF'),
        (0x390FDE4,'488B15D52E7809488B0BE82D3A6FFC488BCF4885C00F851A685501488B15E21A7D09E8FDDB10FD488903488BD0E9CCDBFFFF'),
        (0x390F09C,'488B15DD8B7809488B0BE875476FFC488BCF4885C00F8514875501488B15CA207D09E819F710FD488903488BD0E914E9FFFF'),
        (0x390DE72,'488B151FCF7209488B0BE89F596FFC488BCF4885C00F85C3B65501488B15E4247D09E8371E11FD488903488BD0E93EFBFFFF'),
        (0x3910744,'488B1515AB7209488B0BE8CD306FFC488BCF4885C00F85DC8D5501488B1522FC7C09E84DF510FD488903488BD0E96CD2FFFF'),
        (0x390FBF0,'488B1511957809488B0BE8213C6FFC488BCF4885C00F858E785501488B1526147D09E855E910FD488903488BD0E9C0DDFFFF'),
        (0x390F9FC,'488B15D5677109488B0BE8153E6FFC488BCF4885C00F8581985501488B15220C7D09E8CD0011FD488903488BD0E9B4DFFFFF'),
        (0x390FCB8,'488B1519D17809488B0BE8593B6FFC488BCF4885C00F8568815501488B158E0F7D09E829EF10FD488903488BD0E9F8DCFFFF'),
        (0x39101FE,'488B15931A7809488B0BE813366FFC488BCF4885C00F8504655501488B1548177D09E8A3D810FD488903488BD0E9B2D7FFFF'),
        (0x3910488,'488B15F1FD7809488B0BE889336FFC488BCF4885C00F8556745501488B15460E7D09E805E410FD488903488BD0E928D5FFFF'),
        (0x39104EC,'488B155D666F09488B0BE825336FFC488BCF4885C00F85DB7B5501488B156A087D09E869E810FD488903488BD0E9C4D4FFFF'),
        (0x3910294,'488B15CDA97209488B0BE87D356FFC488BCF4885C00F858E6B5501488B1552127D09E81DDD10FD488903488BD0E91CD7FFFF'),
        (0x390EDE0,'488B1589B47809488B0BE8314A6FFC488BCF4885C00F85EB7B5501488B15FE2C7D09E8DDEE10FD488903488BD0E9D0EBFFFF'),
        (0x3910230,'488B15711C7809488B0BE8E1356FFC488BCF4885C00F85E7645501488B15E6167D09E8B9D810FD488903488BD0E980D7FFFF'),
        (0x3910424,'488B15C57B7809488B0BE8ED336FFC488BCF4885C00F85F5725501488B158A0D7D09E825E310FD488903488BD0E98CD5FFFF'),
        (0x390E6A6,'488B151B307809488B0BE86B516FFC488BCF4885C00F85DE805501488B1560327D09E85BF410FD488903488BD0E90AF3FFFF'),
        (0x390EA8E,'488B159B907109488B0BE8834D6FFC488BCF4885C00F859FA55501488B15281A7D09E8D70D11FD488903488BD0E922EFFFFF'),
        (0x390F966,'488B15C3A07209488B0BE8AB3E6FFC488BCF4885C00F853A775501488B15E81C7D09E8AFE810FD488903488BD0E94AE0FFFF'),
        (0x3910CEE,'488B15337D7109488B0BE8232B6FFC488BCF4885C00F8526825501488B1540F77C09E8C3EA10FD488903488BD0E9C2CCFFFF'),
        (0x390E066,'488B151B6D6F09488B0BE8AB576FFC488BCF4885C00F85F7A55501488B1528287D09E8F71011FD488903488BD0E94AF9FFFF'),
        (0x390E836,'488B15C3AD7809488B0BE8DB4F6FFC488BCF4885C00F85B18B5501488B15402F7D09E8A3FC10FD488903488BD0E97AF1FFFF'),
        (0x390E930,'488B15A9AF7809488B0BE8E14E6FFC488BCF4885C00F8531845501488B15262B7D09E8CDF510FD488903488BD0E980F0FFFF'),
        (0x390DD14,'488B15651E7809488B0BE8FD5A6FFC488BCF4885C00F85A28C5501488B15D23D7D09E89DFF10FD488903488BD0E99CFCFFFF')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    table_va=pe.image_base+0x3915318;raw=pe.bytes_at_va(table_va,416*4)
    require(len(raw),416*4,source,table_va)
    targets=[r[0] for r in struct.iter_unpack('<I',raw)]
    rows=[]
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
        (0x85,0x3910906,106522,16715,'Conditions_CompareDeckAttr_Data',None),
        (0x174,0x3910D84,107160,16505,'StoreEntityProperty_Data',None),
        (0x41,0x390F740,106442,16617,'CheckDamageTransferredSource_Data',None),
        (0xA9,0x390E002,106594,16095,'EnemyHurtAnimAction_Data',None),
        (0x62,0x390FEDE,106487,16635,'Conditions_CheckHasDamageSkillCastId_Data',None),
        (0x13C,0x391000A,107012,16399,'SaveDamageSkillCastId_Data',None),
        (0x90,0x390EF0C,106534,16043,'CountShieldUIAction_Data',None),
        (0xBB,0x390FA60,106636,16135,'ForceTargetInFightAction_Data',None),
        (0x0B,0x390E386,106285,15905,'AddTagAction_Data',None),
        (0x0C,0x390FDB2,106286,15907,'AddTagToEntities_Data',None),
        (0x26,0x3910776,106361,15975,'CastPlungingAttack_Data',None),
        (0x10C,0x39105B4,106924,16303,'PatrolTeleport_Data',None),
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
        (0x15C,0x3915124,107102,16463,'ShakeCountShieldUIAction_Data',None),
        (0x16F,0x3910D52,107150,16495,'SpendAtbAction_Data',None),
        (0x05,0x390E2F0,106259,16195,'AbilityActions_InterruptCurSkillAction_Data',None),
        (0x3A,0x391083E,106435,16013,'CheckBuffEnhanceChangedLayer_Data',None),
        (0x4C,0x390FE7A,106455,16023,'ClearProjectileAction_Data',None),
        (0x150,0x391006E,107090,16439,'SetGeneralAbilityCd_Data',None),
        (0xA7,0x390F1FA,106586,16091,'EnablePartsAction_Data',None),
        (0x19E,0x390EBEC,107707,15957,'AddCameraControlStateAction_AddCameraControlStateActionData',None),
        (0x08,0x390E3B8,106281,15959,'AddDynamicCcsAction_AddDynamicCcsActionData',None),
        (0x120,0x390E57A,106970,16343,'RandomAction_Data',None),
        (0x9F,0x39103F2,106567,16073,'DispelAction_Data',None),
        (0x1B,0x390EB56,106327,15937,'BlowOffAction_Data',None),
        (0x87,0x391032A,106524,16723,'Conditions_OrConditionAction_Data',None),
        (0x52,0x390EFD4,106469,16693,'Condition_CheckSquadInFight_Data',None),
        (0x8E,0x3910938,106532,16039,'CostAtbRefreshLongestSkillCd_Data',None),
        (0x125,0x3910B2C,106981,16353,'RecoverDashEnergy_Data',None),
        (0x124,0x3910AFA,106980,16351,'RecordBattleDetails_Data',None),
        (0x14F,0x3910C26,107089,16437,'SetFirstDashParam_Data',None),
        (0x71,0x3914B16,106502,16671,'Conditions_CheckProjectileInPerfectDodgeCd_Data',None),
        (0x70,0x3914AE4,106501,16669,'Conditions_CheckProjectileIgnoreImmuneLevel_Data',None),
        (0x159,0x390DF08,107099,16457,'SetSuperArmorAction_Data',None),
        (0x16,0x390E5AC,106311,15927,'AuraAction_Data',None),
        (0x178,0x390ECE6,107170,16513,'SwitchModeAction_Data',None),
        (0xC1,0x390E9C6,106648,16147,'GetAITransDataAction_Data',None),
        (0x101,0x390EAC0,106904,16283,'OnSpellAbnormalStartFinish_Data',None),
        (0xC7,0x390E034,106665,16159,'HitStopAction_Data',None),
        (0x19B,0x390ED4A,107236,16215,'VulnerableAction_Data',None),
        (0x128,0x390EEA8,106984,16357,'RecoverPoiseAction_Data',None),
        (0x164,0x390F3BC,107119,16477,'SkillAffixAction_Data',None),
        (0xCF,0x390F22C,106675,16175,'IgniteBuffTextAction_Data',None),
        (0x12B,0x390F006,106988,16363,'RefreshBuffAttrModifierValue_Data',None),
        (0x2C,0x390F290,106367,15987,'ChangeSkillAction_Data',None),
        (0x127,0x390F678,106983,16355,'RecoverLockOnEndIfNoLockAction_Data',None),
        (0xAB,0x390F420,106601,16217,'EnhancedAction_Data',None),
        (0xF6,0x390DE0E,106865,16261,'MoveToAction_Data',None),
        (0x17C,0x390E868,107184,16521,'TeleportAction_Data',None),
        (0x186,0x390F3EE,107206,16541,'TriggerCharSpellInflictionEvent_Data',None),
        (0xB9,0x390F38A,106634,16129,'ForceHideHeadBarAction_Data',None),
        (0xF4,0x390F998,106863,16257,'MoveGaitAction_Data',None),
        (0x133,0x390F83A,107003,16381,'SaveBuffLifeTime_Data',None),
        (0x14A,0x390F4E8,107085,16427,'SetAnimatorParamAction_Data',None),
        (0x15D,0x390F6AA,107103,16213,'ShelterAction_Data',None),
        (0x37,0x390DF3A,106426,16009,'CharWeaponVisibleAction_CharWeaponVisibleActionData',None),
        (0x12A,0x390F808,106987,16361,'RefrainObtainUsp_Data',None),
        (0x144,0x390DABC,107076,16415,'SelfRotateAction_Data',None),
        (0x15B,0x390E192,107101,16461,'SetWeaknessAction_Data',None),
        (7,0x390F06A,106280,15899,'AddAIMarkerAction_Data',None),
        (395,0x390FD4E,107216,16551,'TriggerSpellBurstEventAction_Data',None),
        (412,0x390FD80,107242,16207,'WeakAction_Data',None),
        (138,0x390DBB6,106527,16031,'ContinuousFindTargetAction_Data',None),
        (331,0x391003C,107084,16429,'SetAnimTimeScaleAction_Data',None),
        (358,0x39100D2,107124,16209,'SlowAction_Data',None),
        (370,0x390F100,107158,16501,'StoreBuffCount_Data',None),
        (40,0x390FE16,106363,15979,'ChangeGeneralAbilityButton_Data',None),
        (258,0x390FFA6,106905,16285,'OnSpellInflictionStart_Data',None),
        (398,0x3910136,107220,16557,'TyphoeaArcheryChipDataAction_Data',None),
        (206,0x390FAF6,106674,16173,'IgniteAction_Data',None),
        (23,0x390FDE4,106319,15929,'BindBountyEnemyAction_Data',None),
        (173,0x390F09C,106609,16101,'EventListenerAction_Data',None),
        (408,0x390DE72,107233,16577,'VoiceTriggerAction_VoiceTriggerActionData',None),
        (407,0x3910744,107232,16575,'VoiceInterruptAction_VoiceInterruptActionData',None),
        (145,0x390FBF0,106535,16045,'CreateAdditionalBattleShape_Data',None),
        (388,0x390F9FC,107197,16537,'TogglableAction_Data',None),
        (223,0x390FCB8,106786,16223,'LaunchUpwardAction_Data',None),
        (31,0x39101FE,106332,15945,'BombTouchLayerAction_Data',None),
        (183,0x3910488,106629,16125,'FlowTextAction_Data',None),
        (240,0x39104EC,106858,16249,'ModifyResilienceDecreaseFactor_Data',None),
        (85,0x3910294,106474,16591,'Conditions_CheckBuffFromSource_Data',None),
        (54,0x390EDE0,106425,16007,'CharWeaponAnimationAction_CharWeaponAnimationActionData',None),
        (32,0x3910230,106337,15949,'BreakoutAction_Data',None),
        (168,0x3910424,106589,16093,'EnableSpecialAim_Data',None),
        (35,0x390E6A6,106338,15955,'BroadcastAlertToCharactersAction_BroadcastAlertToCharactersActionData',None),
        (362,0x390EA8E,107144,16487,'SpawnEnemyAction_Data',None),
        (111,0x390F966,106500,16667,'Conditions_CheckProfession_Data',None),
        (353,0x3910CEE,107110,16471,'ShowSquadTipsAction_Data',None),
        (284,0x390E066,106956,16335,'PullAction_Data',None),
        (140,0x390E836,106530,16035,'ConvertToTargetContext_Data',None),
        (78,0x390E930,106459,16027,'ComboCacheAction_Data',None),
        (148,0x391096A,106539,16051,'CreateDynamicBattleShape_Data',None),
        (188,0x39109CE,106637,16137,'ForceTriggerWeakness_Data',None),
        (344,0x3910C8A,107098,16455,'SetStrafeModeAction_Data',None),
        (346,0x3910CBC,107100,16459,'SetWaterDroneItemModePersistLiquidIdAction_Data',None),
        (364,0x3910D20,107147,16211,'SpeedupAction_Data',None),
        (377,0x3910104,107177,16515,'TagQueryListenerAction_Data',None),
        (402,0x3910DB6,107225,16565,'TyphoeaIsInShootingRangeAction_Data',None),
        (334,0x3910618,107088,16435,'SetDamageTagImmuneRule_Data',None),
        (224,0x390E7D2,106794,15961,'LockCameraAimAction_LockCameraAimActionData',None),
        (13,0x3910168,106291,15909,'AirborneAction_AirborneActionData',None),
        (0xD5,0x4E67C83,106689,16187,'IntResourceHpCheckAction_Data',None),
        (0xD6,0x4E67CC6,106690,16189,'IntResourceOnHpZeroAction_Data',None)):
        require(targets[tag],target,source,table_va+tag*4)
        operands=[]
        for at,usage_tag in ((target,1),)+(((init,2),) if init is not None else ()):
            ins=pe.bytes_at_va(pe.image_base+at,7)
            require(len(ins),7,source,pe.image_base+at)
            cell=pe.image_base+at+7+struct.unpack_from('<i',ins,3)[0]
            usage=pe.bytes_at_va(cell,8)
            found=unresolved_usage_index(usage,reg['typesCount'],tag=usage_tag,source=source,offset=cell)
            require(found,index,source,cell)
            pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
            record=pe.bytes_at_va(pointer,16);require(len(record),16,source,pointer)
            require(record[10],0x12,source,pointer+10)
            require(struct.unpack_from('<Q',record)[0],definition,source,pointer)
            require(definition<len(md.types),True,source,pointer)
            namespace='View' if tag==0x19E else 'Core'
            expected_name='Beyond.MemoryPack.Beyond_Gameplay_'+namespace+'_'+suffix+'ForMemoryPack'
            require(md.type_full_name(md.types[definition]),expected_name,source,pointer)
            operands.append({'instructionRva':at,'cellVa':cell,'usageRawHex':usage.hex().upper(),
                'usageTag':usage_tag,'registeredTypeIndex':index,'typePointerVa':pointer,'typeRawHex':record.hex().upper()})
        if len(operands)==2:require(operands[0]['typePointerVa'],operands[1]['typePointerVa'],source)
        rows.append({'tag':tag,'switchTargetRva':target,'typeDefinition':definition,'wrapperName':expected_name,'operands':operands})
    return {'methods':methods,'windows':windows,'switchTableRva':0x3915318,'switchEntryCount':416,
        'switchTableSha256':hashlib.sha256(raw).hexdigest().upper(),'rows':rows,
        'level':'direct current native tag-to-wrapper routing; exact metadata identity',
        'boundary':'The token/module-joined reader calls the bounded tag helper then uses its ushort output in an unsigned <=0x19F switch. The helper fast path consumes one byte and directly returns tags below 0xFA. FA consumes two more bytes as a little-endian ushort with no lower-value restriction; its short-input path calls an external refill helper, not an in-body zero-result failure. FB..FF return false with zero tag output, skipping the AL=1 instruction; the dispatcher false path clears its output. The maintained finite parser retains FF null and leaves FB..FE unsupported. Segment replacement is not certified. Selected table entries reach exact type-usage operands, including current union364 to SpeedupAction. For C9 and C0, separate cctor callsites pass those literal tags alongside a helper result derived from the same registered type pointer (usage kind two versus branch kind one). Current C9 describes the IfElse wrapper; C0 describes GainCost, contradicting the legacy Buff reader C0 name. Tag 40 describes CheckDamageTag. This is not a blanket tag renumbering rule or proof of nested fields, actual object allocation, formatter execution, record extent or EOF. Do not alias C9 to the legacy C0 parser or promote existing labels for current bytes without the concrete nested consumer ABI.'}


def element_provider_state_flow(pe,*,source):
    """Selected state-dependent lookup path; enclosing bodies are gated by audit."""
    windows=[]
    for at,expected in (
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
        (0x4AF1447,'4533F6E9652F2BFE')):
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    return {'windows':windows,'level':'direct conditional state/return flow',
        'boundary':'The short class helper returns its input unchanged when bit zero at +0x138 is set; otherwise it tail-jumps to initialization, whose return cannot be replaced by the fast-path identity. The provider receives a companion, not a serialized reader. Companion method-context slot zero feeds a helper and its result+0x20 becomes a lookup key. A successful first-table lookup uses a 24-byte row index to load a qword carrier from a separate vector; a miss may construct and insert a carrier. A null context element can instead forward a null carrier to the next helper. That helper consults static-carrier+0x18 state, compares a hash and invokes a separate equality target before returning a matched node+0x18 value. Miss branches include conditional helper calls, allocations and publication through another helper; they are not equivalent to selecting the static registered candidate. The common return comes from the writable local slot. The caller checks the returned object against companion method-context slot one before returning it or entering an error path. These branches establish state dependence, not cache contents, helper success, concrete formatter identity, execution, serialized bytes or EOF. Hash/equality algorithms, all initialization and generation helper implementations, and live mutation ordering remain unresolved.'}


def adapter_conversion_context(pe,md,reg,table,entries,*,source):
    """Static interface carrier and slot identity; not a live conversion target."""
    require(len(entries),13,source)
    entry=entries[8]
    require((entry['relativeIndex'],entry['kindRaw']),(8,2),source,entry['entryVa'])
    index=pe.u32_at_va(entry['dataPointerVa'])
    require(index,45287,source,entry['dataPointerVa'])
    require(index<reg['typesCount'],True,source,entry['dataPointerVa'])
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    require(pointer!=0,True,source)
    raw=pe.bytes_at_va(pointer,16);require(len(raw),16,source,pointer)
    require(raw[10],0x15,source,pointer+10)
    cp=struct.unpack_from('<Q',raw)[0];require(cp!=0,True,source,pointer)
    cr=pe.bytes_at_va(cp,32);require(len(cr),32,source,cp)
    bp=struct.unpack_from('<Q',cr)[0];require(bp!=0,True,source,cp)
    carrier=generic_type_carrier(raw,cr,pe.bytes_at_va(bp,16),type_pointer=pointer,
        type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],32173,source,bp)
    interface=md.types[32173]
    require(md.type_full_name(interface),'Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1',source)
    inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(inst.index,12827,source,inst.record_va)
    require(len(inst.arguments),1,source,inst.record_va)
    arg=bytes.fromhex(inst.arguments[0].raw_type_record_hex)
    require(arg,bytes.fromhex('F2020000000000000000130000000000'),source,inst.record_va)
    owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',arg)[0],
        [t.generic_container_index for t in md.types],source=source)
    require((owner['typeIndex'],owner['ordinal']),(13633,0),source,owner['containerOffset'])
    method_entry=entries[9]
    require((method_entry['relativeIndex'],method_entry['kindRaw']),(9,3),source,method_entry['entryVa'])
    spec=pe.u32_at_va(method_entry['dataPointerVa'])
    require(spec,173212,source,method_entry['dataPointerVa'])
    require(spec<reg['methodSpecsCount'],True,source,method_entry['dataPointerVa'])
    spec_va=int(reg['methodSpecs'],16)+spec*12
    spec_raw=pe.bytes_at_va(spec_va,12)
    definition,ci,mi=method_spec_record(spec_raw,len(md.methods),reg['genericInstsCount'],source=source,offset=spec_va)
    require((definition,ci,mi),(249850,inst.index,-1),source,spec_va)
    require((interface.method_start,interface.method_count),(definition,1),source)
    method=md.methods[definition]
    require((method.declaring_type,method.slot,method.parameter_count,method.token),
        (32173,0,0,0x06001747),source)
    require(md.string(method.name_index),'GetValue',source)
    return {'carrier':carrier,'interfaceEntry':entry,'methodEntry':method_entry,
        'instantiation':inst.as_dict(),'argumentOwner':owner,'methodSpecIndex':spec,
        'methodSpecRawHex':spec_raw.hex().upper(),'methodDefinition':definition,'methodSlot':method.slot,
        'level':'exact static carrier/VAR/MethodSpec and metadata slot identity',
        'boundary':'Adapter relative class slot eight describes IMemoryPackDeSerializeWrapper with the reciprocal adapter ordinal-zero VAR. Slot nine describes GetValue with the identical class-instantiation index; its independently decoded metadata slot is zero and it has no explicit parameters. This distinguishes the conversion interface argument T0 from the existing slot-four formatter query for T1; it does not by itself decode the method return type or implementation. The native helper requests interface slot zero, but does not read RGCTX slot nine directly. The static relationship does not prove inflated interface pointers, a live implementation, method body semantics, serialized order, source consumption or EOF. Do not substitute the shared-code Object candidate for the original companion context.'}


def list_element_value_flow(pe,*,source):
    """Ref-object dispatch followed by object conversion; not a DWORD byte read."""
    windows=[]
    for at,expected in (
        (0x3B1373A,'4C89442418'),(0x3B1374B,'498BF9488BF2488BD9'),
        (0x3B1376E,'488B4F20E8C9485EFC488B88C0000000488B4920E8D90A29FF'),
        (0x3B1378C,'B9050000004C8D4C24404C8BC3488BD0E85FBB52FC'),
        (0x3B137A1,'488B5C24404885DB7460'),
        (0x3B137AB,'488B4F20E88C485EFC488B88C0000000488B4940E87C485EFC'),
        (0x3B137C4,'33C94C8BC3488BD0E82F3058FC'),(0x3B137D6,'8906'),(0x3B1380B,'33C0EBC2'),
        (0x96814,'498B38498BF00FB7E9488BDA'),
        (0x96828,'440FB7873001000033C066413BC0731C'),
        (0x96838,'488B97B00000000FB7C84803C948391CCA741A'),
        (0x96865,'0FB7D0488B87B00000004803D28B44D00803C548984883C01448C1E0044803C7'),
        (0x96885,'4C8B00488BCE488B5008'),(0x968A3,'49FFE0')):
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    bodies=[]
    for start,end,expected in (
        (0x3B13730,0x3B1380F,'8F484C44B26A8E791ED7FA7470F1ACEA2C46391E6869DE64D9B206FC6ECB05C7'),
        (0x96800,0x968A6,'C9595BDA4FE4DBC11FC0B54731878C8F1305752C0DE7BA35104FE8DC134F8743')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper();require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    return {'windows':windows,'bodies':bodies,'outputByteLength':4,
            'level':'direct conditional ref-object/output and interface-dispatch flow',
            'boundary':'The non-FF helper retains reader RCX, output RDX and companion R9, and saves incoming R8 in the stack qword later passed by address to formatter dispatch. Companion-derived class slots supply the provider query and conversion interface carrier. Dispatch receives the original reader plus that initialized writable object slot. A null resulting object yields EAX=0; otherwise the conversion helper receives slot number zero, a separately derived interface carrier and the resulting object. Its hit path compares exact pointers in 16-byte class interface records, adds the requested ushort slot to a record DWORD offset, sign-extends the 32-bit sum and addresses a target/companion pair at class+(sum+0x14)*16. Its miss path delegates pair resolution to another helper. The common path tail-jumps with RCX=object and RDX=the loaded companion; it does not pass the original reader to this conversion target. The outer helper writes returned EAX to its four-byte output. That width is therefore a converted result width, not proof of a serialized DWORD load or four-byte cursor advance. Pair bounds, interface/class initialization, provider and conversion identities, actual target selection, delegated byte consumption and EOF remain unresolved.'}


def list_element_shared_context(pe,table,reg,code,spec_records,methods_raw,*,source):
    """Selected code-context candidate; never overwrite a live companion context."""
    inst=table.resolve(5059)
    require([a.raw_type_record_hex for a in inst.arguments],
            ['A22D0000000000000000118000000000','068E00000000000000001C0000000000'],source,inst.record_va)
    require(len(spec_records),reg['methodSpecsCount'],source)
    selected={i for i,row in enumerate(spec_records) if row==(102199,5059,-1)}
    require(sorted(selected),[165248],source)
    rows=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),selected,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=source,
        offset=int(reg['genericMethodTable'],16))
    for row in rows:
        slot=int(code['genericMethodPointers'],16)+row['indices'][0]*8
        row['methodPointerSlotVa']=slot;row['methodPointerVa']=pe.u64_at_va(slot)
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in rows],[(165248,pe.image_base+0x40BB390)],source)
    return {'classInstantiation':inst.as_dict(),'methodDefinition':102199,'methodSpecIndices':sorted(selected),
            'codeCandidates':rows,'level':'exact selected static MethodSpec/code-context relation',
            'boundary':'The selected MethodSpec of the previously module/token-joined GenericMemoryPackFormatter Deserialize definition has ordered GameplayTag-record and Object-record arguments and no method instantiation. Its bounded generic-method table entry joins the dispatcher comparison target. This is a shared-code candidate context, not the actual object class or loaded companion context. The companion class supplies the specialized branch RGCTX slots independently; substituting the shared Object argument into that context is invalid without separate evidence. Actual provider selection, companion inflation, element payload and EOF remain unresolved.'}


def list_element_null_probe(pe,*,source):
    """Conditional FF peek and one-byte consumption, not a terminal grammar."""
    windows=[]
    for at,rawhex in (
        (0x3EDF9A0,'40534883EC20488BD9C644243000E87D8EDCFE84C00F8537F8CC004883C4205BC3'),
        (0x4BAF1F2,'488D542430488BCBE861960FFEB001E9B50733FF'),
        (0x2CA8830,'40534883EC2083793001488BD90F8CBD8BE301488B43508038FF0F94C04883C4205BC3'),
        (0x2CA8860,'48895C24084889742410574883EC2083793001488BF2488BD90F8C958BE301488B43500FB608880E8B7B3083EF010F88938BE30148FF4350FF4340FF4344897B30803EFF488B5C2430488B7424380F95C04883C4205FC3'),
        (0x4AE1400,'4533C0BA01000000E84F7DC20490E930741CFE'),
        (0x4AE1414,'4533C0BA01000000E83B7DC20490E958741CFEBA01000000488BCBE80C0DFF0084C00F8565741CFEE953741CFE')):
        raw=bytes.fromhex(rawhex)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'byteLength':len(raw),'rawHex':rawhex,'sha256':hashlib.sha256(raw).hexdigest().upper()})
    return {'windows':windows,'markerByte':255,'fastConsumedBytesOnMatch':1,
            'level':'direct conditional marker-peek and consumed-counter flow',
            'boundary':'The selected helper calls a peek routine that ensures one readable byte if needed, compares cursor[0] with 0xFF and returns the comparison without directly advancing cursor or counters. A false result returns immediately. A true result calls a byte consumer with the same reader and a local byte output, then returns true regardless of that consumer AL result. The consumer copies one byte out; its fast path advances cursor, local and consumed counters by one and decrements remaining by one. It returns byte!=0xFF, so the wrapper does not simply forward that boolean. Cold paths use the already reviewed ensure/advance routines; ensure may replace the segment, so absence of fast pointer increment does not imply unchanged allocation. The dispatcher true branch clears its DWORD output. This conditional FF handling does not identify a serialized union, prove the non-FF element width, guarantee source validity, or establish source/terminal/EOF consumption. The shared target identity does not prove this branch executes.'}


def list_element_dispatch(pe,*,source):
    """Object-selected target/companion ABI, not a selected element reader."""
    bodies=[]
    for start,end,expected in (
        (0x98CD0,0x98DF1,'1BF6036D17FE88296002DAF06C93284CA14CA2C7117C2E89240F7FAF2D1D61FE'),
        (0x2FCA38,0x2FCA56,'F223AF3B187BBB846AD744B4553E69B70D6BBBB616C49CB208C55A3CB2E3D9B9')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    # Decode the actual RIP operand rather than infer a target from nearby names.
    at=0x98CF9;raw=pe.bytes_at_va(pe.image_base+at,7)
    require(raw[:3],bytes.fromhex('488D0D'),source,at)
    require(len(raw),7,source,at)
    target=at+7+struct.unpack_from('<i',raw,3)[0]
    require(target,0x40BB390,source,at)
    return {'bodies':bodies,'targetPairOffsets':[0x190,0x198],'specializedTargetRva':target,
            'fallbackCallRva':0x2FCA4E,'level':'direct conditional object-target/companion ABI',
            'boundary':'Entry RDX is retained as the formatter object, R8 as the reader and R9 as the output pointer; incoming RCX is overwritten by the object class before the initialization helper call. The class is then reloaded and its +0x190 target and +0x198 companion are loaded as a pair. If the target differs from the exact RIP-derived comparison address, the cold branch performs an ordinary indirect CALL with RCX=object, RDX=reader, R8=output and R9=the loaded companion, then rejoins cleanup. It is not a tail jump, nor a companion inferred from declaration order. The equal-target path instead reads the loaded companion class RGCTX slots and calls another helper with the retained reader. A nonzero AL clears the output DWORD; the other path eventually forwards the retained reader/output, a helper-derived value and class slot three to another reader helper. These distinct branches do not certify which target the live object selects. Class initialization, actual target/companion identity and inflation, all delegated read widths/cursor changes and final EOF remain unresolved. No constant element byte width or terminal-candidate elimination follows.'}


def list_formatter_candidate(pe,md,modules,image_owners,reg,code,table,spec_records,methods_raw,*,source):
    """Concrete registered candidate, separate from active provider dispatch."""
    identities=module_methods(pe,md,modules,image_owners,
        [(428795,'MemoryPack.Formatters.ListFormatter`1','Deserialize',None)],source=source)
    require(identities[0]['token'],0x060001C0,source)
    index=209879
    require(index<reg['typesCount'],True,source)
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    require(pointer!=0,True,source,int(reg['types'],16)+index*8)
    raw=pe.bytes_at_va(pointer,16);require(len(raw),16,source,pointer)
    require(raw[10],0x15,source,pointer)
    carrier_pointer=struct.unpack_from('<Q',raw)[0]
    require(carrier_pointer!=0,True,source,pointer)
    carrier_raw=pe.bytes_at_va(carrier_pointer,32);require(len(carrier_raw),32,source,carrier_pointer)
    base_pointer=struct.unpack_from('<Q',carrier_raw)[0]
    require(base_pointer!=0,True,source,carrier_pointer)
    base_raw=pe.bytes_at_va(base_pointer,16)
    carrier=generic_type_carrier(raw,carrier_raw,base_raw,type_pointer=pointer,type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],54057,source,base_pointer)
    require(md.methods[428795].declaring_type,54057,source)
    inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(inst.index,816,source,inst.record_va)
    require(len(inst.arguments),1,source,inst.record_va)
    require(inst.arguments[0].raw_type_record_hex,'A22D0000000000000000118000000000',source,inst.record_va)
    # spec_records is the already bounded complete MethodSpec inventory from audit().
    require(len(spec_records),reg['methodSpecsCount'],source)
    selected={i for i,row in enumerate(spec_records) if row==(428795,816,-1)}
    require(sorted(selected),[215461],source)
    candidates=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),selected,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=source,
        offset=int(reg['genericMethodTable'],16))
    for row in candidates:
        slot=int(code['genericMethodPointers'],16)+row['indices'][0]*8
        row['methodPointerSlotVa']=slot;row['methodPointerVa']=pe.u64_at_va(slot)
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in candidates],
            [(215461,pe.image_base+0x3BA40F0)],source)
    windows=[]
    for at,expected in ((0x3BA410E,'488B47508B30'),
        (0x3BA4120,'48834750048347400483474404895F30'),
        (0x3BA4130,'48634744488B4F18482BC84863C6483BC8'),
        (0x3BA4141,'0F8CB4653201'),
        (0x3BA4147,'83FEFF0F842F010000'),(0x3BA415F,'49833E00488B4520488B88C00000000F8518653201'),
        (0x3BA41C1,'85F60F881F653201'),(0x3BA4282,'49C70600000000'),
        (0x4ECA6FB,'33D28BCEE8900A8404CCCC'),
        (0x4ECA6AB,'FF431CC7431800000000E9799BCDFE'),
        (0x3BA4261,'85F67F4D'),(0x3BA42C3,'4C8D4C24584C8BC7498BD7E8FD494FFC'),
        (0x3BA4312,'41FFC4443BE60F8D47FFFFFFEB92')):
        chunk=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(chunk)),chunk,source,at)
        windows.append({'rva':at,'rawHex':expected})
    range_failure_branch_rva=0x3BA4141
    range_failure_branch_raw=pe.bytes_at_va(pe.image_base+range_failure_branch_rva,6)
    require(range_failure_branch_raw,bytes.fromhex('0F8CB4653201'),source,
            range_failure_branch_rva)
    range_failure_target_rva=(range_failure_branch_rva+6+
                              struct.unpack_from('<i',range_failure_branch_raw,2)[0])
    require(range_failure_target_rva,0x4ECA6FB,source,range_failure_branch_rva)
    return {'methodIdentities':identities,'registeredTypeIndex':index,'typeCarrier':carrier,
            'classInstantiation':inst.as_dict(),'methodSpecIndices':sorted(selected),'codeCandidates':candidates,
            'windows':windows,'level':'exact static candidate identity; direct conditional header and loop flow',
            'fastHeaderGuard':{
                'countWidthBytes':4,
                'signedCount':True,
                'remainingBytesComparedToCount':True,
                'comparisonRva':0x3BA4130,
                'comparisonRawHex':'48634744488B4F18482BC84863C6483BC8',
                'rangeFailureCondition':'remaining < signed count',
                'rangeFailureBranchRva':range_failure_branch_rva,
                'rangeFailureBranchRawHex':range_failure_branch_raw.hex().upper(),
                'rangeFailureTargetRva':range_failure_target_rva,
                'rangeFailureBodyRawHex':'33D28BCEE8900A8404CCCC',
                'boundary':'The four-byte signed count is compared with remaining bytes after the header. A signed remaining<count branch reaches a helper call followed by INT3 if the helper returns; it does not enter the normal positive-element loop.',
            },
            'boundary':'The registered ListFormatter type and Deserialize MethodSpec share the same one-argument instantiation as the previously joined List carrier. The complete selected MethodSpec/code-table join yields one static code candidate, not proof of provider selection. This body receives the reader in RDX, output-slot pointer in R8 and companion in R9. Its fast header path reads a signed DWORD, advances cursor and both counters by four, and compares total-minus-consumed with the sign-extended count without multiplying by an element width. Header -1 clears the output. With a null output, other negative counts reach a helper followed by INT3; with an existing output, the reviewed reuse branch instead increments object+0x1C, clears object+0x18 and reaches a loop guarded by count>0. Thus this body does not universally reject all counts below -1. Each positive iteration passes the same reader and a zeroed four-byte output slot to element dispatch, then forwards the output word to another helper and increments its loop index. A four-byte output slot does not prove four serialized bytes per element. Cold header paths call the separately reviewed ensure/advance helpers. Element formatter identity, helper effects, successful allocation/reuse, actual MethodInfo/provider selection, authenticated source span and final cursor/EOF remain unresolved. Keep both terminal grammars.'}


def nested_reader_context(pe, md, modules, image_owners, reg, table, *, source, metadata_source):
    """Slot-zero context chain: reciprocal parameters, never live substitution."""
    methods=module_methods(pe,md,modules,image_owners,
        [(428462,'MemoryPack.MemoryPackReader','ReadPackable',None),
         (428464,'MemoryPack.MemoryPackReader','ReadValue',None),
         (428394,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',None)],source=source,
        expected_image='MemoryPack.dll')
    module=modules['MemoryPack.dll']
    require(pe.u32_at_va(module+0x40),120,source,module+0x40)
    require(pe.u32_at_va(module+0x50),691,source,module+0x50)
    range_va=pe.u64_at_va(module+0x48);entry_va=pe.u64_at_va(module+0x58)
    ranges=pe.bytes_at_va(range_va,120*12)
    require(len(ranges),120*12,source,range_va)
    containers=[m.generic_container_index for m in md.methods]
    rows=[]
    for definition,token,start,count,kind,index,next_definition,inst_index in (
        (428462,0x06000073,36,1,3,517554,428464,54984),
        (428464,0x06000075,40,3,3,516756,428394,41928),
        (428394,0x0600002F,13,2,1,2190,None,None)):
        require(md.methods[definition].token,token,metadata_source,definition)
        require(select_rgctx_range(ranges,691,token,source=source,offset=range_va),(start,count),source,range_va)
        at=entry_va+start*16;raw=pe.bytes_at_va(at,16)
        require(len(raw),16,source,at)
        require(struct.unpack_from('<I',raw)[0],kind,source,at)
        payload=struct.unpack_from('<Q',raw,8)[0]
        encoded=pe.bytes_at_va(payload,4)
        require(encoded,struct.pack('<I',index),source,payload)
        row={'methodDefinition':definition,'token':token,'relativeSlot':0,'moduleEntryIndex':start,
             'entryVa':at,'entryRawHex':raw.hex().upper(),'index':index,'kind':kind}
        if kind==3:
            require(index<reg['methodSpecsCount'],True,source,payload)
            spec_at=int(reg['methodSpecs'],16)+index*12
            spec=pe.bytes_at_va(spec_at,12)
            parsed=method_spec_record(spec,len(md.methods),reg['genericInstsCount'],source=source,offset=spec_at)
            require(parsed,(next_definition,-1,inst_index),source,spec_at)
            inst=table.resolve(inst_index)
            require(len(inst.arguments),1,source,inst.record_va)
            argument=inst.arguments[0];type_at=argument.type_pointer_va
            type_raw=bytes.fromhex(argument.raw_type_record_hex)
            row.update({'methodSpecVa':spec_at,'methodSpecRawHex':spec.hex().upper(),
                        'nextMethodDefinition':next_definition,'methodInstantiation':inst.as_dict()})
        else:
            require(index<reg['typesCount'],True,source,payload)
            slot=int(reg['types'],16)+index*8
            pointer=pe.bytes_at_va(slot,8)
            require(len(pointer),8,source,slot)
            type_at=struct.unpack('<Q',pointer)[0]
            require(type_at!=0,True,source,slot)
            type_raw=pe.bytes_at_va(type_at,16)
        require(len(type_raw),16,source,type_at)
        require(type_raw[10],0x1E,source,type_at)
        owner=method_parameter_owner(md.buf,struct.unpack_from('<Q',type_raw)[0],containers,source=metadata_source)
        require((owner['methodIndex'],owner['ordinal']),(definition,0),metadata_source,owner['containerOffset'])
        row.update({'typePointerVa':type_at,'typeRawHex':type_raw.hex().upper(),'parameterOwner':owner})
        rows.append(row)
    windows=[]
    for at,expected in ((0x381F904,'488BDA4C8BF9'),(0x381F915,'488B4338488B18'),
                        (0x381F944,'488B4338488B30'),(0x381F956,'488B5E38488B1B'),
                        (0x381FB0D,'B9050000004C8D4C24204D8BC7488BD3E8DEF781FC')):
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    return {'methods':methods,'rows':rows,'windows':windows,
            'level':'exact static token/MethodSpec/MVAR joins; direct conditional nested context reads',
            'boundary':'The selected nested body retains its incoming reader and follows MethodInfo+0x38 slot zero three times before deriving a provider key. The corresponding independently image/token-joined ranges identify ReadPackable to ReadValue, ReadValue to GetFormatter, then the GetFormatter MVAR type. Each method edge has one open method argument whose reciprocal owner is the preceding method and whose ordinal is zero; the final type is a distinct ordinal-zero parameter owned by GetFormatter itself. These are three different parameter records, not interchangeable raw identities. Conditional on ordinary context inflation from the previously authenticated ReadPackable<List<...>> call, this chain carries that same concrete argument through the intermediate contexts. All three generic definition ordinary-pointer slots are null; static ranges do not select a shared body. The body passes the retained reader and separate output slot to dispatch, but actual initialized MethodInfos, substitution, provider key/cache contents, list formatter, source length and final cursor remain unobserved. No list framing, element meaning or terminal uniqueness follows.'}


def wrapper_consumer(pe, md, modules, image_owners, reg, table, *, source):
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
    wrapper_methods=module_methods(pe,md,modules,image_owners,
        [(104357,'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack','Deserialize',0x37DF680),
         (104358,'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack+Beyond_Gameplay_Core_GameplayTagListForMemoryPackFormatter','Deserialize',0x37DF620)],
        source=source,expected_image='MemoryPack.Beyond.dll')
    code_windows=[]
    for rva,expected,role in (
        (0x37DF6A8,'837B3001','compare remaining bytes to one-byte wrapper header'),
        (0x37DF6B2,'488B43500FB630','read one wrapper header byte from reader cursor'),
        (0x37DF6C5,'48FF4350FF4340FF4344897B30','advance cursor and consumed counters by one byte'),
        (0x37DF6D2,'4080FEFF745649833E000F846CBB65014080FE010F8595BB6501',
         'accept null header 0xFF or non-null member-count header 1'),
    ):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        code_windows.append({'rva':rva,'rawHex':raw.hex().upper(),'role':role})
    return {'methodSpec':spec,'methodInstantiation':inst.as_dict(),
            'listCarrier':carrier,'elementInstantiation':element_inst.as_dict(),
            'methodIdentities':wrapper_methods,'headerCodeWindows':code_windows,
            'wrapperFraming':{
                'headerByteWidth':1,'acceptedNonNullHeaderByte':1,'nullHeaderByte':0xFF,
                'remainingOffset':0x30,'cursorOffset':0x50,
                'consumedCounterOffsets':[0x40,0x44],
                'nestedCallRva':0x37DF6F9,
                'boundary':'The reviewed reader consumes exactly one header byte before the nested List<GameplayTag> read. Header 0xFF takes the null path; non-null header 1 reaches the nested read; other values leave the supported path. This is static wrapper code, not proof that the runtime provider selects it for the current file.',
            },
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
