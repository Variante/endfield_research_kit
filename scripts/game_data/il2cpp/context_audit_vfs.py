"""Stream, VFS and UnityPlayer consumer validations.

Moved verbatim out of ``context_audit``; that module owns the audit
contract and the report it assembles.

Pinned values.  Every build-locked value these validations check or report --
GameAssembly and UnityPlayer RVAs, instruction windows and body hashes, import
descriptors and name thunks, export slots, metadata indices and literal-pool
rows -- lives in ``contracts/il2cpp_context_audit_native.json`` under
``pins``, one section per report key (``selectedVfsRootResolver`` for
:func:`vfs_root_resolver`), bound as ``pins`` at the top of each function.
PE header offsets, structure offsets, virtual-slot numbers and the UTF-8 code
page stay here because they do not change with a client build.
"""
from __future__ import annotations

import hashlib
import struct
from scripts.game_data.il2cpp.context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.il2cpp.context import named_top_level_type
from scripts.game_data.il2cpp.context import method_pointer_indices, generic_method_candidates
from scripts.game_data.il2cpp.context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.il2cpp.context import literal_record
from scripts.game_data.il2cpp.context_audit_common import AUDIT_PINS, require
from scripts.game_data.il2cpp.context_audit_memorypack import module_methods


def stream_source_identity(pe,md,modules,image_owners,reg,code,spec_records,methods_raw,*,source):
    """Join selected generic bodies and declared stream slots, not live overrides."""
    pins=AUDIT_PINS['selectedStreamSourceIdentity']
    identities=module_methods(pe,md,modules,image_owners,
        pins['managerMethods'],
        source=source,expected_image='Common.Beyond.dll')
    identities+=module_methods(pe,md,modules,image_owners,
        pins['serializerMethods'],source=source)
    stream=named_top_level_type(md.buf,b'mscorlib.dll',b'System.IO',b'Stream',source=source)
    require(stream['typeDefinitionIndex'],pins['streamTypeDefinition'],source)
    method=md.methods[pins['managerMethods'][1][0]]
    require((method.parameter_start,method.parameter_count),(pins['streamParameterIndex'],1),source)
    require(method.parameter_start<len(md.parameters),True,source)
    parameter=md.parameters[method.parameter_start]
    require(parameter.type_index,pins['streamTypeIndex'],source)
    require(parameter.type_index<reg['typesCount'],True,source)
    type_pointer=pe.u64_at_va(int(reg['types'],16)+parameter.type_index*8)
    type_raw=pe.bytes_at_va(type_pointer,16)
    require(type_raw,bytes.fromhex(pins['streamTypeRawHex']),source,type_pointer)
    require(struct.unpack_from('<Q',type_raw)[0],stream['typeDefinitionIndex'],source,type_pointer)
    stream_methods=module_methods(pe,md,modules,image_owners,
        pins['streamMethods'],
        source=source,expected_image='mscorlib.dll')
    for row,slot,return_index,raw_hex in zip(stream_methods,(11,35),pins['returnTypeIndices'],
        pins['returnTypeRawHex']):
        method=md.methods[row['methodIndex']]
        require((method.slot,method.return_type),(slot,return_index),source)
        require(return_index<reg['typesCount'],True,source)
        pointer=pe.u64_at_va(int(reg['types'],16)+return_index*8)
        raw=pe.bytes_at_va(pointer,16)
        require(raw,bytes.fromhex(raw_hex),source,pointer)
        row.update(virtualSlot=slot,returnTypeIndex=return_index,returnTypeRawHex=raw.hex().upper())
    expected=pins['genericBodies']
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
        require(spec_records[index],(definition,-1,(AUDIT_PINS['selectedSkillResourceContext']['objectInstantiation'])),source,int(reg['methodSpecs'],16)+index*12)
    return {'methodIdentities':identities,'genericBodyCandidates':rows,'streamType':stream,
            'streamParameter':{'methodIndex':pins['managerMethods'][1][0],'parameterIndex':pins['streamParameterIndex'],'typeIndex':parameter.type_index,
                               'typePointerVa':type_pointer,'typeRawHex':type_raw.hex().upper()},
            'declaredStreamMethods':stream_methods,
            'level':'exact static method/type/virtual-slot relation',
            'boundary':'Declared input is System.IO.Stream. Metadata virtual slots 11 and 35 name get_Length and Read, with signed 64-bit and 32-bit return records. This does not identify the concrete stream subclass or override, its successful initialization, bytes, position, full-read behavior or EOF. Shared Object method contexts do not prove actual SkillData invocation.'}


def stream_carrier_consumer(pe,*,source):
    """Exact reviewed calls and discarded read result; length is not a receipt."""
    pins=AUDIT_PINS['selectedStreamCarrierConsumer']
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    for rva in pins['companionLoads']:
        require(pe.bytes_at_va(pe.image_base+rva,8),bytes.fromhex(pins['companionLoadHex']),source,rva)
    expected_switch=bytes.fromhex(pins['switchDataHex'])
    switch=pe.bytes_at_va(pe.image_base+pins['switchDataRva'],len(expected_switch))
    require(switch,expected_switch,source,pins['switchDataRva'])
    return {'edges':edges,'windows':windows,'switchData':{'rva':pins['switchDataRva'],'rawHex':switch.hex().upper()},
            'dispatcher':{'rva':pins['dispatcherRva'],'slotBaseOffset':0x140,'slotStride':16,'inputSlotBits':16,
                          'boundary':'The reviewed entry computes class + (uint16(CX)+0x14)*16, loads pointer and companion. Its specialized branches and cold paths are not all closed; this is a slot-address connection, not a live override receipt.'},
            'level':'direct conditional native carrier construction and discarded read result',
            'boundary':'Both allocation branches perform one indirect call at class+0x370 with a 16-byte carrier, then call the joined manager carrier entry without testing returned EAX. Slot 35 is declared Stream.Read, not ReadExactly. The large branch obtains length separately for comparison, low-32-bit allocation request and low-32-bit carrier length; equality/stability is not checked. The small branch also narrows a fresh result before stack allocation. Later negative checks apply to the narrowed dword, not the original 64-bit result. No source position, complete-fill loop, short-read check, authenticated payload length or final parser EOF is established; allocation helpers and concrete overrides remain unresolved.'}


def vfs_stream_identity(pe,md,modules,image_owners,reg,*,source):
    """Normal allocation candidate plus independent token/parent/slot identities."""
    pins=AUDIT_PINS['selectedVfsStreamIdentity']
    identity=named_top_level_type(md.buf,b'Common.Beyond.dll',b'Beyond.VFS',b'VFSFileReadStream',source=source)
    require((identity['typeDefinitionIndex'],identity['byvalTypeIndex']),(pins['vfsReadStreamDefinition'],pins['vfsReadStreamTypeIndex']),source)
    require(md.types[pins['vfsReadStreamDefinition']].parent_index,pins['streamTypeIndex'],source)
    require(pins['streamTypeIndex']<reg['typesCount'],True,source)
    parent_pointer=pe.u64_at_va(int(reg['types'],16)+pins['streamTypeIndex']*8)
    parent_raw=pe.bytes_at_va(parent_pointer,16)
    require(parent_raw,bytes.fromhex(pins['streamTypeRawHex']),source,parent_pointer)
    cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+pins['allocationLoadRva'],7),pe.image_base+pins['allocationLoadRva'],source=source)
    raw=pe.bytes_at_va(cell,8)
    index=unresolved_usage_index(raw,reg['typesCount'],tag=1,source=source,offset=cell)
    require(index,identity['byvalTypeIndex'],source,cell)
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    type_raw=pe.bytes_at_va(pointer,16)
    require(type_raw,bytes.fromhex(pins['allocationTypeRawHex']),source,pointer)
    methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],
        source=source,expected_image='Common.Beyond.dll')
    for index,slot in pins['virtualSlots']:
        require(md.methods[index].slot,slot,source,index)
    return {'typeIdentity':identity,'parentTypePointerVa':parent_pointer,'parentTypeRawHex':parent_raw.hex().upper(),
            'allocationCellVa':cell,'allocationCellRawHex':raw.hex().upper(),
            'allocationTypePointerVa':pointer,'allocationTypeRawHex':type_raw.hex().upper(),'methods':methods,
            'level':'exact static type/parent/token/slot relation; conditional allocation connection',
            'boundary':'The allocation callsite loads a type usage for VFSFileReadStream and passes the returned object plus the same 32-byte descriptor and inner stream to its token-joined constructor. Metadata parent points to the separately joined Stream record. This identifies the normal construction path, not successful execution, resolved live type usage, replacement callbacks, selected source file or authenticated bytes.'}


def vfs_stream_consumer(pe,*,source):
    """Descriptor-to-state and nested stream relations on reviewed normal paths."""
    pins=AUDIT_PINS['selectedVfsStreamConsumer']
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'edges':edges,'windows':windows,'level':'direct conditional native descriptor/state/return connection',
            'descriptorBytes':32,'descriptorStateOffset':0x28,'innerStreamOffset':0x48,
            'length':{'stateOffset':0x3C,'descriptorOffset':0x14,
                      'boundary':'The normal getter zero-extends this dword into RAX. It is copied from the constructor descriptor, not queried from physical-file EOF.'},
            'position':{'baseStateOffset':0x38,'descriptorOffset':0x10,
                        'boundary':'The normal getter calls slot 12 on the inner stream and subtracts the zero-extended descriptor dword. No initial inner position or seek execution is established.'},
            'read':{'boundary':'Normal Read subtracts logical Position from the zero-extended length word and uses the low 32 bits of a positive difference, otherwise zero; its signed request comparison does not certify arbitrary 64-bit ranges. An oversized request goes through a carrier-slicing helper whose full ABI remains open. The specialized inner dispatcher ignores entry ECX, copies the 16-byte input and calls fixed class+0x370 (slot 35) once, returning its EAX. Read unsigned-checks that count does not exceed the resulting request, optionally passes exactly the returned prefix to another stateful helper, and returns that count without a full-fill loop. The concrete inner override and optional transform remain unresolved.'},
            'boundary':'All statements are conditional on the reviewed no-replacement paths. Callback overrides, inner stream construction/seek, allocation extents, descriptor-to-current-VFS identity/hash and source/EOF receipt remain unresolved. Logical position arithmetic is not physical-file ownership or proof of byte equality.'}


def file_stream_open(pe,md,modules,image_owners,reg,*,source):
    """Selected normal file-stream creation/seek paths; no path or EOF receipt."""
    pins=AUDIT_PINS['selectedFileStreamOpen']
    identity=named_top_level_type(md.buf,b'mscorlib.dll',b'System.IO',b'FileStream',source=source)
    require((identity['typeDefinitionIndex'],identity['byvalTypeIndex']),(pins['fileStreamDefinition'],pins['fileStreamTypeIndex']),source)
    require(md.types[pins['fileStreamDefinition']].parent_index,pins['streamTypeIndex'],source)
    allocations=[]
    for rva in pins['allocationLoads']:
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        raw=pe.bytes_at_va(cell,8)
        index=unresolved_usage_index(raw,reg['typesCount'],tag=1,source=source,offset=cell)
        require(index,identity['byvalTypeIndex'],source,cell)
        pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
        type_raw=pe.bytes_at_va(pointer,16)
        require(type_raw,bytes.fromhex(pins['fileStreamTypeRawHex']),source,pointer)
        allocations.append({'rva':rva,'cellVa':cell,'cellRawHex':raw.hex().upper(),
                             'typePointerVa':pointer,'typeRawHex':type_raw.hex().upper()})
    require(allocations[0]['cellVa'],allocations[1]['cellVa'],source)
    methods=module_methods(pe,md,modules,image_owners,
        pins['helperMethods'],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        pins['fileStreamMethods'],source=source,expected_image='mscorlib.dll')
    require(md.methods[pins['fileStreamMethods'][2][0]].slot,32,source,pins['fileStreamMethods'][2][0])
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    expected_switch=bytes.fromhex(pins['switchDataHex'])
    switch=pe.bytes_at_va(pe.image_base+pins['switchDataRva'],len(expected_switch))
    require(switch,expected_switch,source,pins['switchDataRva'])
    return {'typeIdentity':identity,'allocations':allocations,'methodIdentities':methods,'edges':edges,
            'windows':windows,'switchData':{'rva':pins['switchDataRva'],'rawHex':switch.hex().upper()},
            'level':'exact static allocation/method identity; direct conditional initial seek',
            'boundary':'Normal mode 1 and mode 2 select distinct token-joined helpers and FileStream constructors. The descriptor dword+0x10 reaches their offset argument and is sign-extended from int32. Mode 1 seeks only for positive offsets; mode 2 seeks for any nonzero offset. Both use declared FileStream.Seek slot 32 with numeric origin 0 and discard its return; the general dispatcher uses the low 16-bit slot number and preserves the supplied offset/origin. Normal return gives the constructed stream, not proof of a successful physical path/hash match or actual initial position. Root selection, path construction, FileStream constructor/Seek internals, replacement callbacks and authenticated logical-file bytes remain unresolved. Switch data is not code.'}


def vfs_descriptor_path(pe,md,modules,image_owners,*,source):
    """Normal descriptor lookup and mode projection, not a serialized BLC join."""
    pins=AUDIT_PINS['selectedVfsDescriptorPath']
    methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],
        source=source,expected_image='Common.Beyond.dll')
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methodIdentities':methods,'edges':edges,'windows':windows,
            'mode':{'descriptorOffset':0x18,'loadBytes':4,'rightShift':10,'callerMask':255,
                    'effectiveBitRangeInclusive':[10,17]},
            'lookup':{'descriptorKeyOffset':8,'containerArrayOffset':0x18,
                      'arrayCountOffset':0x18,'indexedStride':32,'indexedReadBias':0x30,'resultBytes':16},
            'level':'direct conditional native lookup and bit projection; exact static method identity',
            'boundary':'On the no-replacement path, the mode getter logically shifts descriptor dword+0x18 by 10; its caller passes only AL, hence bits 10..17. With descriptor byte+0x18 bit 1 clear, the relative-path routine calls the token-joined chunk-name getter with a separate 16-byte output buffer. A nonnegative descriptor dword+8 is passed to a lookup on static-carrier+8. A nonnegative result is checked against the count at array carrier+0x18, then 16 bytes are copied from array+0x30+result*32. A negative key or lookup result diverts to a helper call; if that call returns normally, the branch zeroes XMM0 and rejoins the same 16-byte output copy. It is not a proven throwing rejection or an authenticated missing-chunk receipt. The normal lookup does not read an inline descriptor-leading hash. Method names do not prove these bytes equal the authenticated BLC chunk MD5. Complete lookup implementation, container population/producer, negative-path helper effects, alternate bit-1 path, path encoding/root selection and replacement callbacks remain unresolved; no current logical-file or EOF receipt follows.'}


def vfs_descriptor_producer(pe,md,modules,image_owners,reg,table,*,source):
    """Paired storage and original MethodInfo class contexts, not live contents."""
    pins=AUDIT_PINS['selectedVfsDescriptorProducer']
    methods=module_methods(pe,md,modules,image_owners,
        pins['descriptorMethods'],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        pins['dictionaryMethods'],
        source=source,expected_image='mscorlib.dll')
    value=named_top_level_type(md.buf,b'Beyond.Byte.dll',b'Beyond.Byte',b'UInt128',source=source)
    require(value['typeDefinitionIndex'],pins['uint128Definition'],source)
    int_raw=pins['int32RawType']
    value_raw=pins['uint128RawType']
    instances=[]
    for index,expected in ((pins['intToValueInstance'],[int_raw,value_raw]),(pins['valueToIntInstance'],[value_raw,int_raw])):
        instance=table.resolve(index)
        require([a.raw_type_record_hex for a in instance.arguments],expected,source)
        instances.append(instance.as_dict())
    usage=[]
    for rva,index,definition,ci in pins['methodUsages']:
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        raw=pe.bytes_at_va(cell,8)
        actual=unresolved_usage_index(raw,reg['methodSpecsCount'],tag=6,source=source,offset=cell)
        require(actual,index,source,cell)
        va=int(reg['methodSpecs'],16)+actual*12
        spec=pe.bytes_at_va(va,12)
        require(method_spec_record(spec,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
                (definition,ci,-1),source,va)
        usage.append({'rva':rva,'cellVa':cell,'rawHex':raw.hex().upper(),
                      'methodSpecIndex':actual,'methodSpecRawHex':spec.hex().upper()})
    storage=[]
    for rva in pins['storageLoads']:
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        require(cell,pe.image_base+pins['storageCellRva'],source,rva)
        storage.append({'rva':rva,'cellVa':cell})
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'valueType':value,'instances':instances,'methodUsages':usage,
            'storageReferences':storage,'edges':edges,'windows':windows,
            'level':'exact static ordered instances and MethodSpec usages; direct conditional producer flow',
            'boundary':'The source usage cells name TryGetValue/set_Item, not FindEntry/TryInsert simply because the inlined call targets look like those helpers. Their MethodInfo+0x20 supplies the original Dictionary class before class RGCTX slots are loaded. Registered arguments are Int32/UInt128 and the exact reverse order. The setter probes static-carrier+0x10 using the incoming 16 bytes; a nonnegative result is bounds-checked and its indexed dword copied to descriptor+8. On a miss it computes dword+0x20 minus dword+0x28, supplies the same integer and 16-byte value in reverse orders to two helpers with numeric behavior 1, then stores that integer to descriptor+8. The second helper uses static-carrier+8, the same storage selected by the getter. Helper return values are not checked. Complete insertion/comparer/collision semantics, initialization, replacement paths, other mutations and actual reciprocal contents are unproved. UInt128 identity is not BLC MD5 provenance; serialized source/carrier/cursor and EOF remain unresolved.'}


def vfs_bytebuf_consumer(pe,md,modules,image_owners,reg,*,source):
    """Conditional serialized-input cursor path; native permissiveness is not validation."""
    pins=AUDIT_PINS['selectedVfsByteBufConsumer']
    methods=module_methods(pe,md,modules,image_owners,
        pins['descriptorMethods'],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        pins['byteHelperMethods'],source=source,expected_image='Beyond.Byte.dll')
    identity=named_top_level_type(md.buf,b'Beyond.Byte.dll',b'Beyond.Byte',b'ByteBufStream',source=source)
    require(identity['typeDefinitionIndex'],pins['byteBufStreamDefinition'],source)
    method=md.methods[pins['descriptorMethods'][0][0]]
    require((method.parameter_start,method.parameter_count),(pins['readFromByteBufParameterStart'],2),source)
    require((pins['readFromByteBufParameterStart']+2)<=len(md.parameters),True,source)
    require(md.parameters[(pins['readFromByteBufParameterStart']+1)].type_index,pins['byteBufParameterTypeIndex'],source)
    require(pins['byteBufParameterTypeIndex']<reg['typesCount'],True,source)
    pointer=pe.u64_at_va(int(reg['types'],16)+pins['byteBufParameterTypeIndex']*8)
    type_raw=pe.bytes_at_va(pointer,16)
    require(type_raw,bytes.fromhex(pins['byteBufParameterRawType']),source,pointer)
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'sourceType':identity,'parameterTypePointerVa':pointer,
            'parameterTypeRawHex':type_raw.hex().upper(),'edges':edges,'windows':windows,
            'level':'exact static source-type identity; direct conditional cursor/value path',
            'boundary':'The selected source parameter joins ByteBufStream. On the reviewed no-replacement path R8 supplies a mutable carrier with cursor dword+0 and array object+8. Two initial bytes are assembled little-endian, incremented by 2 in 16 bits, then sign-extended before adding to the cursor. After an eight-byte helper call and cursor advance, two further helper calls at cursor and cursor+8 form the 16-byte container lookup input; the cursor advances 16. The same paired insertion targets are used on lookup miss, and the resulting integer enters the returned 32-byte descriptor. ReadULong with the supplied nonzero flag assembles eight bytes little-endian after per-byte index checks, but signed int32(offset+7) >= array count returns zero normally; callers still advance their cursor. Overflow and alternate flag/replacement paths are not generalized. This is not a fail-closed source-range validator or proof that returned zeros came from file bytes. Later skips, narrowed values, version/flag branches and cursor save/restore require their own closure. The array origin, authenticated BLC identity, complete carrier allocation, initial/final cursor and logical-file EOF remain unproved.'}


def vfs_block_cursor(pe,md,modules,image_owners,*,source):
    """Array -> shared cursor -> nested records; distinguish checksum and EOF."""
    pins=AUDIT_PINS['selectedVfsBlockCursor']
    methods=module_methods(pe,md,modules,image_owners,
        pins['blockMethods'],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        pins['byteBufMethods'],source=source,expected_image='Beyond.Byte.dll')
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,
            'level':'exact static identities; direct conditional shared-cursor and return paths',
            'boundary':'The normal main-info entry passes its input array and supplied start index to CreateFromByte, which constructs 16 bytes: cursor dword, zero dword, original array pointer. Main, chunk and file readers share that same mutable carrier. Chunk processing sign-extends a ReadInt result and requests count*32 bytes before its positive-count loop; each file result is copied as 32 bytes. Allocation-helper behavior and negative-count rejection are not proved by this loop. Before parsing, main compares two helper results using array length minus start minus four and the selected tail position; helper algorithms and authenticated array provenance remain open. After the chunk loop, the normal remaining calculation clamps nonpositive array-length-minus-cursor to zero. Positive remaining with stored version 3 causes one ReadInt call, whose result is discarded before returning the object; other versions can return with positive remaining. No final equality check follows this extra read. This is not an EOF validator, even if the earlier comparison succeeds. Replacement callbacks, helper internals, upstream decryption/file identity, full record grammar and final source receipt remain unresolved.'}


def vfs_block_transform(pe,md,modules,image_owners,*,source):
    """Reviewed normal-path array aliasing, not a complete cipher implementation."""
    pins=AUDIT_PINS['selectedVfsBlockTransform']
    methods=module_methods(pe,md,modules,image_owners,
        pins['blockMethods'],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        pins['cipherMethods'],
        source=source,expected_image='Common.Beyond.XXEnc.dll')
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    storage=[]
    for rva in pins['storageLoads']:
        raw=pe.bytes_at_va(pe.image_base+rva,7)
        cell=rip_qword_load_target(raw,pe.image_base+rva,source=source)
        require(cell,pe.image_base+pins['storageCellRva'],source,rva)
        storage.append({'rva':rva,'cellVa':cell,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'staticStorage':storage,
            'level':'exact static identities; direct conditional in-place byte transform',
            'boundary':'On the reviewed non-replacement path, the entry retains its original array in RSI. It passes that array, static-carrier+0xE4 as offset and signed 32-bit array-length-minus-offset as count to TransformBytes. The wrapper forwards identical input/output array pointers and identical input/output offsets to WorkBytes. A positive-count normal loop reads one input byte, XORs it with a byte from state+0x28 array, and writes the same output index; its state byte counter is masked with 63 and zero invokes a separate block helper. Nonpositive count returns without validation. Initial length sums use signed 32-bit arithmetic; per-byte array indices also have unsigned bounds checks. This is not a reusable fail-closed range parser. After the transform returns, the same original array reaches the already pinned main-info reader, with a fresh +0xE4 load from the same static storage cell. No equality check proves the two runtime offset loads stayed identical. Static values, key/span and constructor ABI, state initialization/block generation, exceptional and replacement behavior, cipher parity with the maintained decoder, physical-file identity and actual execution remain unresolved. This establishes neither a complete decryption algorithm nor EOF consumption.'}


def vfs_block_file_source(pe,md,modules,image_owners,*,source):
    """File-read return carrier and loop; actual paths and Read override stay open."""
    pins=AUDIT_PINS['selectedVfsBlockFileSource']
    methods=module_methods(pe,md,modules,image_owners,
        pins['blockMethods'],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        pins['fileMethods'],source=source,expected_image='mscorlib.dll')
    require(md.methods[pins['fileMethods'][1][0]].slot,34,source,pins['fileMethods'][1][0])
    require(md.methods[pins['fileMethods'][1][0]].parameter_count,3,source,pins['fileMethods'][1][0])
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'readSlot':34,
            'level':'exact static identities; direct conditional read-loop and return-array chain',
            'boundary':'Both reviewed block constructors pass the returned array of their respective file helper directly to DecryptCreateBlockGroupInfo, after nonnull/nonempty checks. On the normal successful helper paths, a path-carrier conversion result is passed to System.IO.File.ReadAllBytes, whose returned array is preserved across cleanup and returned unchanged. The actual root strings, relative path construction, path-carrier conversion, selection/fallback and authenticated on-disk file/hash remain unresolved. ReadAllBytes calls a FileStream constructor and dispatches Length via numeric slot 11. Its positive signed length branch rejects values above INT32_MAX, requests an array of the narrowed length, and loops while signed remaining is positive. Each call uses class+0x360 and companion+0x368 (slot 34, not the previously reviewed slot 35), passes array/accumulated offset/remaining, then adds EAX to offset and subtracts EAX from remaining. Zero EAX branches to error helpers rather than the normal loop return. There is no local negative/oversized returned-count rejection or final equality check; full-fill reasoning requires the Read override contract. The registered FileStream Read definition independently declares slot 34 and three parameters, but concrete live dispatch, constructor/override internals, zero-length alternate helper, allocation/error/cleanup behavior and actual file execution are not proved. A length-based read loop is not a source-hash receipt or a serialized-reader EOF check.'}


def native_file_read(pe,md,modules,image_owners,*,source):
    """Static import/argument/count connection; no live OS or handle receipt."""
    pins=AUDIT_PINS['selectedNativeFileRead']
    methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],source=source,expected_image='mscorlib.dll')
    edges=[]
    for rva in pins['monoReadCalls']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+pins['methods'][1][3],source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':pins['methods'][1][3],'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    # This selected-build witness authenticates the header directory reference,
    # first descriptor and two exact name thunks. Other imports stay opaque.
    optional=pe.u32_at_file(0x3C)+24
    require(pe.u32_at_file(optional+120),pins['importDirectoryRva'],source,optional+120)
    require(pe.u32_at_file(optional+124),pins['importDirectorySize'],source,optional+124)
    require(pe.bytes_at_va(pe.image_base+pins['importDirectoryRva'],20),
            struct.pack('<IIIII',pins['importLookupRva'],0,0,pins['kernel32NameRva'],pins['importAddressRva']),source,pins['importDirectoryRva'])
    require(pe.bytes_at_va(pe.image_base+pins['kernel32NameRva'],13),b'KERNEL32.dll\0',source,pins['kernel32NameRva'])
    imports=[]
    # Rows: [call RVA, import index, name RVA, hint, imported name].
    for rva,index,name_rva,hint,import_name in pins['imports']:
        name=import_name.encode('ascii')
        raw=pe.bytes_at_va(pe.image_base+rva,6)
        require(len(raw),6,source,rva)
        require(raw[:2],b'\xff\x15',source,rva)
        slot=rva+6+struct.unpack_from('<i',raw,2)[0]
        require(slot,pins['importAddressRva']+index*8,source,rva)
        lookup=pins['importLookupRva']+index*8
        require(pe.bytes_at_va(pe.image_base+lookup,8),struct.pack('<Q',name_rva),source,lookup)
        require(pe.bytes_at_va(pe.image_base+name_rva,len(name)+3),struct.pack('<H',hint)+name+b'\0',source,name_rva)
        imports.append({'callRva':rva,'iatSlotRva':slot,'lookupSlotRva':lookup,
                        'nameRva':name_rva,'name':name.decode('ascii'),'dll':'KERNEL32.dll'})
    return {'methods':methods,'edges':edges,'windows':windows,'selectedImports':imports,
            'level':'exact static import/identity joins; direct conditional buffer and returned-count flow',
            'boundary':'The reviewed FileStream array overload checks negative offset/count and offset against array length minus count before its normal buffered path. Buffered and direct reads call the same MonoIO helper. That helper extracts a handle carrier at +0x10, compares the 32-bit offset-plus-count against array length, then passes handle, array+0x20+sign-extended offset, count, address of a zeroed out DWORD and a zero fifth argument to the static ReadFile import slot. A zero API return calls the static GetLastError slot and stores its result through the supplied error pointer. The helper returns the out DWORD when that error word is zero, otherwise -1; it does not derive the count from the API boolean return. The direct FileStream branch records that count, tests its error and -1 paths, updates state position and adds already-buffered bytes for its normal return. This distinguishes API boolean, out-byte count, error and accumulated read count. Only two name thunks and their descriptor are joined, not the entire import directory; live IAT contents, imported function behavior, handle provenance, full buffered-state invariants, alternate async/error/cleanup paths and runtime execution remain unresolved. No authenticated-file receipt, unconditional full-read guarantee or serialized EOF follows.'}


def vfs_path_carrier(pe,md,modules,image_owners,*,source):
    """Four-slot path carrier construction/consumption, not concrete root identity."""
    pins=AUDIT_PINS['selectedVfsPathCarrier']
    methods=module_methods(pe,md,modules,image_owners,
        pins['pathMethods'],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        pins['appendMethods'],
        source=source,expected_image='Unsafe.VFS.dll')
    edges=[]
    for rva,target in pins['edges']:
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'carrierByteLength':32,
            'level':'exact static identities; direct conditional four-slot carrier flow',
            'boundary':'The file-helper checks call two distinct builders and copy both 16-byte halves of their results into the caller-supplied 32-byte carrier. On the non-replacement builder paths, slot +0 comes from branch-selected static storage and slot +8 from the respective path getter. Nonempty first input normally fills +0x10 with that input and +0x18 with the second candidate; the empty/null first-input branch instead fills +0x10 with the second candidate and leaves +0x18 zero. Streaming can transform the second candidate before these stores; its helper behavior and predicate semantics remain unresolved. AppendPathInfo receives that carrier, skips work when slot +0 is null/empty, substitutes a shared static value for null slots +8/+0x10/+0x18, and forwards +0,+8,+0x10,+0x18 in that order to another helper with a separate stack companion. Its resulting temporary array+0x20 and temporary DWORD length are passed to the append consumer. The copy width and argument order do not establish formatting syntax, separators, string contents, final output length, concrete root, overlay selection or file/hash identity. Static values, getter initialization, formatting/append ABI and helper internals, replacements and runtime execution remain unresolved.'}


def vfs_path_format_context(pe,md,modules,image_owners,reg,table,*,source):
    """Original generic arguments and append units, not complete format grammar."""
    pins=AUDIT_PINS['selectedVfsPathFormatContext']
    methods=module_methods(pe,md,modules,image_owners,
        pins['methods'],source=source,expected_image='ZString.dll')
    rva=pins['usageLoadRva']
    cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
    require(cell,pe.image_base+pins['usageCellRva'],source,rva)
    raw=pe.bytes_at_va(cell,8)
    index=unresolved_usage_index(raw,reg['methodSpecsCount'],tag=6,source=source,offset=cell)
    require(index,pins['methodSpecIndex'],source,cell)
    va=int(reg['methodSpecs'],16)+index*12
    spec=pe.bytes_at_va(va,12)
    require(method_spec_record(spec,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
            tuple(pins['appendFormatMethodSpec']),source,va)
    instance=table.resolve(pins['appendFormatMethodSpec'][2])
    require([a.raw_type_record_hex for a in instance.arguments],
            pins['stringArgumentRawTypes']*3,source)
    windows=[]
    for at,hex_bytes in pins['windows']:
        chunk=pe.bytes_at_va(pe.image_base+at,len(bytes.fromhex(hex_bytes)))
        require(chunk,bytes.fromhex(hex_bytes),source,at)
        windows.append({'rva':at,'rawHex':chunk.hex().upper()})
    return {'methods':methods,'usageCellVa':cell,'usageRawHex':raw.hex().upper(),
            'methodSpecIndex':index,'methodSpecRawHex':spec.hex().upper(),
            'methodInstantiation':instance.as_dict(),'windows':windows,
            'level':'exact static original MethodSpec; direct conditional 16-bit-unit consumption',
            'boundary':'The AppendPathInfo call supplies an original AppendFormat MethodSpec with three ordered string-tag arguments, stored as its stack companion. Do not replace that context with arguments inferred from the shared code body. The reviewed body reads the companion at its sixth ABI position; numeric selector branches use the first/second/third value alongside companion+0x38 slots 0/8/16. Actual RGCTX inflation and nested formatter execution are not established. Input scanning reads 16-bit elements at string+0x14+index*2; literal copying advances the temporary cursor by element count. The downstream UnSafeString.Append receives pointer and count, calls a capacity helper, computes signed-extended 32-bit count*2 for an indirect copy target, and advances its stored cursor by the original count. A zero 16-bit terminator is written only if the updated signed cursor is below capacity. Hence the forwarded count is a two-byte-unit count on this path, not a byte length or an unconditional terminator guarantee. Capacity/copy resolver internals, replacement paths, complete format grammar, actual generic dispatch, output validity/length, concrete path and source identity remain unresolved.'}


def resolver_key_comparison(pe,*,source):
    """Bounded-prefix lexicographic comparison and caller length tie-breaks."""
    pins=AUDIT_PINS['selectedResolverKeyComparison']
    windows=[]
    for at,expected in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+at,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,at)
        windows.append({'rva':at,'rawHex':raw.hex().upper()})
    return {'windows':windows,'level':'direct conditional byte-order comparison',
            'boundary':'The complete comparator consumes the supplied byte count using alignment bytes, bounded qword groups and remaining bytes. Equal prefixes return zero. Byte mismatches return -1/+1 using unsigned comparison flags; qword mismatches byte-swap both operands before the same unsigned ordering, preserving first-byte lexicographic order. The resolver supplies the smaller key/query byte length, then uses length comparisons to order equal prefixes, for both original and transformed queries. Hence a matching prefix alone is not key equality. No character decoding, case folding or locale comparison occurs in this reviewed helper. Its count is not an independent allocation bound; valid pointer extents and string construction/copy, tree invariants, actual keys and execution remain prerequisites. This does not establish a live lookup result, formatter selection or file identity.'}


def resolver_prefix_query(pe,*,source):
    """Conditional prefix extent, not live key equality or lookup success."""
    pins=AUDIT_PINS['selectedResolverPrefixQuery']
    windows=[]
    for at,expected in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+at,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,at)
        windows.append({'rva':at,'rawHex':raw.hex().upper()})
    return {'windows':windows,'queryStart':0,'delimiterByte':40,
            'level':'direct conditional prefix-range construction',
            'boundary':'After a successful delimiter search the resolver subtracts the query data pointer from the result, supplies that difference as requested length and supplies start zero to the subrange helper. The helper unsigned-checks start<=length, clamps requested length to length-start, selects inline or pointer bytes by capacity>15 and forwards source+start with the bounded count to a constructor. Its result is moved as two 16-byte halves into the second query carrier. For a valid successful search of the first left parenthesis this requests exactly the bytes before that delimiter, excluding parentheses and their suffix; it does not simply remove two final bytes. The reviewed search uses scalar and SIMD matching; no arbitrary no-match return guarantee is promoted from undefined BSF-zero destination contents. Allocation/copy/comparison helper semantics, malformed carriers, actual cache/tree contents and successful lookup remain unresolved. This conditional extent does not establish live equivalence between the requested and registered names.'}


def unity_loader_conversion(pe,*,source):
    """Selected conversion counts and end pointer; no successful API receipt."""
    pins=AUDIT_PINS['selectedUnityLoaderConversion']
    bodies=[]
    for start,end,expected in pins['bodies']:
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    caller=bytes.fromhex(pins['callerHex'])
    require(pe.bytes_at_va(pe.image_base+pins['callerRva'],len(caller)),caller,source,pins['callerRva'])
    return {'bodies':bodies,'callerRva':pins['callerRva'],'callerRawHex':caller.hex().upper(),
            'codePageArgument':65001,'flagsArgument':0,'elementByteLength':2,
            'level':'direct conditional count, terminator and end-pointer flow',
            'boundary':'The converter receives a pointer-to-input-pointer, a 64-bit input count and an output representation. With nonzero count its first selected MultiByteToWideChar import call receives ECX=65001, EDX=0, R8=input data, R9D=low DWORD input count, a null output and zero output count. A nonpositive EAX goes to an unreviewed reset helper. A positive EAX is sign-extended and used for capacity selection, stored length (or inline 12-length WORD encoding), and a zero WORD at data+2*length before a second import call. The second call uses the same input bytes/count and a helper-derived output data/count; its EAX survives the epilogue but the module caller does not inspect it before calling the end-pointer helper. That helper selects inline/pointer data and writes data+2*representationLength into its output slot. Its length leaf returns QWORD +0x10 unless tag BYTE +0x20=1, when it returns 12-zero-extended WORD +0x18; it preserves the R8 data register used by the end-pointer caller. Tag-two cold branches call a capacity helper before rejoining. Capacity allocation, reset and tag mutation remain unresolved, so neither output bounds nor conversion success is asserted. Representation length and the subsequent slash-loop end are not validated against the second API return. This is not Unicode parity, an OS binding receipt, a loaded-image hash or a SkillData final cursor.'}


def unity_loader_input(pe,*,source):
    """Exact selected caller's fixed inline request, not loaded image identity."""
    pins=AUDIT_PINS['selectedUnityLoaderInput']
    windows=[]
    # These are selected path windows, not whole-function coverage. The helper's
    # other branches cannot be selected by this caller's explicit tag=1/count=16.
    for start,end,expected in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        windows.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    literal=b'GameAssembly.dll'
    require(pe.bytes_at_va(pe.image_base+pins['literalRva'],16),literal,source,pins['literalRva'])
    return {'windows':windows,'literalRva':pins['literalRva'],'requestedModuleName':literal.decode('ascii'),
            'requestByteLength':16,'loaderCallRva':pins['loaderCallRva'],'loaderRva':pins['loaderRva'],
            'level':'direct selected caller inline-byte construction and argument flow',
            'boundary':'The caller initializes a stack representation with tag BYTE +0x20=1, then calls a helper with count 16. On these explicit inputs the reviewed helper path compares count against 24 and returns the original representation address without mutating it or invoking other callees. The caller copies the exact 16-byte GameAssembly.dll literal to that address and writes a separate zero byte at +16. Its tag-one cold branch sets BYTE +0x18=8, rejoins the hot path and passes the same representation address in RCX to the reviewed module loader. The previously verified length helper therefore computes 24-8=16 on this carrier. Other capacity/helper branches and the caller after the loader call are outside this claim. This proves a static basename request, not actual invocation, conversion correctness, the selected module-cache entry, Windows search-path resolution, loaded absolute path or loaded image hash. It cannot certify a current GameAssembly binding or any SkillData source/cursor.'}


def unity_module_lookup(pe,*,source):
    """Selected loader/lookup control flow and import identities, not live bindings."""
    pins=AUDIT_PINS['selectedUnityModuleLookup']
    bodies=[]
    # Include split hot fragments and their explicit cold branch destinations.
    # Callees are not included in these extents or implicitly given semantics.
    for start,end,expected in pins['bodies']:
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    optional=pe.u32_at_file(0x3C)+24
    require(pe.u32_at_file(optional+120),pins['importDirectoryRva'],source,optional+120)
    require(pe.u32_at_file(optional+124),pins['importDirectorySize'],source,optional+124)
    require(pe.bytes_at_va(pe.image_base+pins['importDirectoryRva'],20),
            struct.pack('<IIIII',pins['importLookupRva'],0,0,pins['kernel32NameRva'],pins['importAddressRva']),source,pins['importDirectoryRva'])
    require(pe.bytes_at_va(pe.image_base+pins['kernel32NameRva'],13),b'KERNEL32.dll\0',source,pins['kernel32NameRva'])
    imports=[]
    # Rows: [call RVA, import index, name RVA, hint, imported name].
    for at,index,name_rva,hint,import_name in pins['imports']:
        name=import_name.encode('ascii')
        raw=pe.bytes_at_va(pe.image_base+at,6)
        require(len(raw),6,source,at)
        require(raw[:2],b'\xff\x15',source,at)
        slot=at+6+struct.unpack_from('<i',raw,2)[0]
        require(slot,pins['importAddressRva']+index*8,source,at)
        lookup=pins['importLookupRva']+index*8
        require(pe.bytes_at_va(pe.image_base+lookup,8),struct.pack('<Q',name_rva),source,lookup)
        require(pe.bytes_at_va(pe.image_base+name_rva,len(name)+3),
                struct.pack('<H',hint)+name+b'\0',source,name_rva)
        imports.append({'callRva':at,'iatSlotRva':slot,'lookupSlotRva':lookup,
                        'nameRva':name_rva,'name':name.decode('ascii'),'dll':'KERNEL32.dll'})
    return {'bodies':bodies,'selectedImports':imports,'moduleHandleCacheRva':pins['moduleHandleCacheRva'],
            'level':'exact selected import identities; direct conditional handle and lookup-result flow',
            'boundary':'The loader entry forwards its incoming RCX to a module helper, stores the returned RAX in the shared module-handle cache and exits on zero before the export-request body. The helper has a runtime-cache branch that returns a qword supplied by another helper. Its other branch extracts input representation data/length, invokes conversion helpers, iterates two-byte elements up to a helper-supplied end pointer replacing 0x2F with 0x5C, selects inline or pointer storage and passes it as RCX to the selected static LoadLibraryW import slot. The imported return is preserved, optionally stored through a cache helper, and returned after cleanup. The export lookup helper preserves incoming module/name arguments for the selected GetProcAddress import, returns its nonzero result, or returns zero for a null module. On a zero imported result its cold branch calls diagnostic/cleanup helpers and rejoins the return of the saved zero, conditional on those calls returning normally. Only the first import descriptor and three selected name thunks are joined, including both conversion calls to MultiByteToWideChar, not complete import-table coverage or live IAT contents. Cache lookup/insertion and string conversion helper semantics, end-pointer validity, actual input module path, loaded image identity, successful binding and execution remain unresolved. No authenticated SkillData source, final cursor or terminal uniqueness follows.'}


def unity_conversion_exports(pe,unity,*,source,unity_source):
    """Two selected export chains and conditional output-slot write ABI."""
    pins=AUDIT_PINS['selectedUnityConversionExports']
    requests=[]
    for at,rawhex,name_at,name,export_name_at,name_slot,ordinal_slot,function_slot,index,target in pins['requests']:
        raw=bytes.fromhex(rawhex);literal=name.encode('ascii')+b'\0'
        require(unity.bytes_at_va(unity.image_base+at,len(raw)),raw,unity_source,at)
        require(unity.bytes_at_va(unity.image_base+name_at,len(literal)),literal,unity_source,name_at)
        for slot,expected in ((name_slot,struct.pack('<I',export_name_at)),
                              (ordinal_slot,struct.pack('<H',index)),(function_slot,struct.pack('<I',target))):
            require(pe.bytes_at_va(pe.image_base+slot,len(expected)),expected,source,slot)
        require(pe.bytes_at_va(pe.image_base+export_name_at,len(literal)),literal,source,export_name_at)
        requests.append({'name':name,'loaderRva':at,'rawHex':rawhex,'exportTargetRva':target,'ordinal':index+1})
    require(pe.bytes_at_va(pe.image_base+pins['barrierStoreRva'],6),bytes.fromhex(pins['barrierStoreHex']),source,pins['barrierStoreRva'])
    return {'requests':requests,'level':'exact selected export identities; direct conditional output-slot store',
            'boundary':'Unity requests string_new_len into the first conversion cache and gc_wbarrier_set_field into the second. Selected GameAssembly export name/ordinal/function slots join the former to the previously reviewed byte-to-string constructor, and the latter to a leaf that writes R8 into [RDX] before optional atomic bitmap marking. The caller passes the first result in R8 and its separate output slot in RDX, then reads that slot. Conditional on these dynamic bindings and successful calls, the returned qword is the first constructor result, not a second newly constructed object. The barrier marking branch and constructor internal allocation helpers are not a live GC receipt. Loader module identity, actual cache bindings, lifecycle, input validity, query normalization and concrete directory remain unresolved. Only selected export chains are joined, not full export coverage.'}


def unity_path_return(pe,*,source):
    """Selected return-slot and string representation, not runtime path value."""
    pins=AUDIT_PINS['selectedUnityPathReturn']
    windows=[]
    for rva,expected in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    literal=b'StreamingAssets\0'
    require(pe.bytes_at_va(pe.image_base+pins['literalRva'],len(literal)),literal,source,pins['literalRva'])
    return {'windows':windows,'literal':'StreamingAssets','representationTagOffset':32,
            'level':'direct conditional return-slot flow',
            'boundary':'The selected registered target builds a temporary representation, passes it to a converter with a separate output slot, cleans up the temporary and returns that output qword. A nested builder supplies the exact StreamingAssets literal to another helper, not proof of concatenation semantics or root value. The converter length helper returns QWORD +0x10 unless BYTE +0x20 equals one; on that branch it returns 24 minus sign-extended BYTE +0x18. The same tag chooses inline representation versus the pointer at +0. Only the low DWORD length reaches the next helper. That helper calls a dynamic function with data pointer and length, then forwards its result to a second dynamic function with a separate output slot and returns the slot qword. These calls are not yet verified managed-string constructors. Dynamic targets, allocation/cleanup and joining helpers, underlying path initialization, tag validity and actual execution remain unresolved; no authenticated file or runtime directory is asserted.'}


def unity_registration_pair(pe,*,source):
    """Shared native loop index proves static pairing, not active registration."""
    pins=AUDIT_PINS['selectedUnityRegistrationPair']
    body=pe.bytes_at_va(pe.image_base+pins['loopRva'],pins['loopByteLength'])
    require(hashlib.sha256(body).hexdigest().upper(),
            pins['loopSha256'],source,pins['loopRva'])
    count=pins['registrationCount'];values_rva=pins['valuesRva'];names_rva=pins['namesRva']
    values_raw=pe.bytes_at_va(pe.image_base+values_rva,count*8)
    names_raw=pe.bytes_at_va(pe.image_base+names_rva,count*8)
    require(len(values_raw),count*8,source,values_rva)
    require(len(names_raw),count*8,source,names_rva)
    rows=[]
    for i,((value,),(name,)) in enumerate(zip(struct.iter_unpack('<Q',values_raw),struct.iter_unpack('<Q',names_raw))):
        # Addressability only: not complete name strings or function bodies.
        require(len(pe.bytes_at_va(value,1)),1,source,values_rva+i*8)
        require(len(pe.bytes_at_va(name,1)),1,source,names_rva+i*8)
        rows.append({'index':i,'nameVa':name,'valueVa':value})
    selected=rows[pins['selectedIndex']]
    require(selected['nameVa'],pe.image_base+pins['selectedNameRva'],source,names_rva+pins['selectedIndex']*8)
    require(selected['valueVa'],pe.image_base+pins['selectedValueRva'],source,values_rva+pins['selectedIndex']*8)
    literal=b'UnityEngine.Application::get_streamingAssetsPath\0'
    require(pe.bytes_at_va(selected['nameVa'],len(literal)),literal,source,pins['selectedNameRva'])
    return {'loopRva':pins['loopRva'],'loopSha256':hashlib.sha256(body).hexdigest().upper(),
            'namesRva':names_rva,'valuesRva':values_rva,'slotByteLength':8,
            'summary':{'success':count,'failed':0,'unsupported':0},'rows':rows,
            'selected':dict(selected,name=literal[:-1].decode('ascii')),
            'level':'direct static name/value argument pairing',
            'boundary':'The complete loop starts at index zero, derives image base with RIP-relative LEA, loads RDX and RCX from separate arrays using the same byte offset, calls the reviewed forwarder and advances by eight until 0xF7E entries. Both complete pointer vectors are bounded and every target is checked for one-byte addressability only; this is not complete string/body decoding. Entry 299 independently pairs the selected interface name with RVA 0x32BA20. The registered name lacks the parentheses in the resolver request, so matching still depends on the unclosed query helper path. Loop invocation, callback effects, dynamic export resolution, tree insertion, duplicate registrations and the selected target body/return ABI remain unresolved. No current directory or authenticated-file identity is inferred.'}


def unity_registration_forwarder(pe,*,source):
    """Selected dynamic export request and forwarding, not live binding."""
    pins=AUDIT_PINS['selectedUnityRegistrationForwarder']
    raw=pe.bytes_at_va(pe.image_base+pins['forwarderRva'],pins['forwarderByteLength'])
    require(hashlib.sha256(raw).hexdigest().upper(),
            pins['forwarderSha256'],source,pins['forwarderRva'])
    windows=[]
    for rva,value in pins['windows']:
        chunk=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(value)))
        require(chunk,bytes.fromhex(value),source,rva)
        windows.append({'rva':rva,'rawHex':chunk.hex().upper()})
    name=b'il2cpp_add_internal_call\0'
    require(pe.bytes_at_va(pe.image_base+pins['exportNameRva'],len(name)),name,source,pins['exportNameRva'])
    return {'windows':windows,'forwarderRva':pins['forwarderRva'],'forwarderByteLength':len(raw),
            'forwarderSha256':hashlib.sha256(raw).hexdigest().upper(),
            'requestedExport':name[:-1].decode('ascii'),'functionCacheRva':pins['functionCacheRva'],
            'level':'exact static request; direct conditional two-argument forwarding',
            'boundary':'A selected loader window supplies a module-handle carrier and the NUL-terminated export name to a dynamic lookup helper, then stores its result in the function cache. The full reviewed forwarding function preserves the two entry arguments, passes them to each selected callback in a separately stored pointer array when its count is positive, then tail-jumps through that same function cache with the original arguments. The zero-callback branch reaches the same tail jump. This connects requested export name to a conditional cache consumer, not the actual module handle, resolved function identity, successful initialization or runtime execution. Callback identities/state, lookup helper cold paths, registration callers and concrete interface-name/function-value pairs remain unresolved. The nearby interface-name pointer array is only a lead and is not joined by position or matching counts.'}


def vfs_root_resolver(pe,*,source):
    """Static requested interface and conditional cache flow, not actual root."""
    pins=AUDIT_PINS['selectedVfsRootResolver']
    windows=[]
    for rva,expected in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    name=b'UnityEngine.Application::get_streamingAssetsPath()\0'
    require(pe.bytes_at_va(pe.image_base+pins['nameRva'],len(name)),name,source,pins['nameRva'])
    export_name=b'il2cpp_add_internal_call\0'
    require(pe.bytes_at_va(pe.image_base+pins['exportNameRva'],len(export_name)),export_name,source,pins['exportNameRva'])
    return {'windows':windows,'requestedInterface':name[:-1].decode('ascii'),
            'nameRva':pins['nameRva'],'functionCacheRva':pins['functionCacheRva'],
            'lookupCarrierGlobalRva':pins['lookupCarrierGlobalRva'],'candidateValueOffset':64,
            'registrationWriterRva':pins['registrationWriterRva'],'sentinelInitializerRva':pins['sentinelInitializerRva'],
            'selectedWriterExport':{'name':export_name[:-1].decode('ascii'),
                                    'ordinal':pins['writerExportOrdinal'],'stubRva':pins['writerExportStubRva']},
            'level':'exact static resolver name; direct conditional cache flow',
            'boundary':'The normal non-replacement streaming-path getter initialization branch calls the wrapper, preserves RAX in RBX and stores it in static carrier+8; the normal return reads that slot. The wrapper loads a cached function pointer and tail-jumps to it when nonnull. On cache miss it passes the exact NUL-terminated interface name to the resolver, checks the result, stores that result in the same function-pointer cell and tail-jumps. The requested name is not a verified resolved function identity, ABI or actual directory. The resolver loads a runtime tree carrier from a static global, follows child pointers using comparison helper results and returns candidate node+0x40 after its first lookup. If that lookup chooses the sentinel, it constructs a second query through helpers (including a search passed byte 0x28) and traverses the same carrier again; a final sentinel yields zero, otherwise node+0x40 supplies the result. The independently reviewed writer scans the first argument to a NUL byte, prepares a 32-byte key carrier and searches the same global tree. Its insertion path requests 0x48 bytes, copies the key carrier into node+0x20 and calls an insertion helper; both existing-candidate and returned-node paths store the original second argument into node+0x40. A separate initializer zeroes two global slots, requests 0x48 bytes, writes self pointers at node+0/+8/+0x10 and marker WORD 0x0101 at +0x18, then stores that pointer in the lookup global. Neither function being present proves initialization, insertion success or actual selected name/value pairs. The selected PE export header, name-pointer slot, ordinal-index slot and function slot independently join il2cpp_add_internal_call (ordinal 34) to a five-byte tail-jump stub into this writer, preserving incoming arguments. Only this selected export chain is certified, not complete export-table coverage; the stub is not assigned to the preceding pdata entry. Export callers and their actual name/value arguments, insertion/allocator internals, string construction/comparison/search/subrange helper semantics and live contents, replacement/cold failure paths, class initialization, comparison predicate semantics, live cache contents and the final path/file/hash connection remain unresolved.'}


def vfs_string_carrier(pe,*,source):
    """Conditional literal conversion and character-reader carrier connection."""
    pins=AUDIT_PINS['selectedVfsStringCarrier']
    windows=[]
    for rva,expected in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'windows':windows,'lengthOffset':16,'elementDataOffset':20,'elementByteLength':2,
            'level':'direct conditional native carrier flow; ASCII widening branch',
            'boundary':'The format-item comma helper zero-extends the input DWORD index before comparing it with sign-extended carrier length at +0x10; for nonnegative length this rejects negative indices as well as indices at or above length. The accepted path returns the zero-extended WORD at carrier+0x14+index*2. Literal construction forwards its input pointer and zero-extended DWORD byte count into a temporary 32-byte conversion carrier. On the reviewed ASCII branch each byte below 0x80 becomes one 16-bit element, the temporary element count advances by one, and a following zero WORD is written. The wrapper chooses inline versus pointer storage by capacity>7 and forwards the low DWORD element count. The next helper writes result+0x10 length and a zero WORD at result+0x14+count*2 on its nonempty allocation path, then calls the copy helper with destination result+0x14, original element pointer and count*2. These offsets independently agree with the format-item reader. Allocation/capacity/copy helpers, empty singleton contents, non-ASCII cold/error branches, cache initialization and actual execution remain unresolved; this is not complete Unicode conversion parity or proof of a runtime output path.'}


def vfs_format_item(pe,*,source):
    """Local format-item return ABI; not whole-format or serialized EOF."""
    pins=AUDIT_PINS['selectedVfsFormatItem']
    windows=[]
    for rva,expected in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'windows':windows,'resultByteLength':32,
            'resultRanges':[
                {'offset':0,'length':4,'role':'numeric selector'},
                {'offset':4,'length':4,'role':'zero'},
                {'offset':8,'length':16,'role':'zero or bounded colon-span pointer/count/padding'},
                {'offset':24,'length':4,'role':'index after closing brace'},
                {'offset':28,'length':4,'role':'zero or comma-derived signed numeric value'}],
            'level':'direct conditional native return ABI',
            'boundary':'The caller supplies RCX result storage, RDX format carrier and R8D opening-brace index; the helper returns the same storage in RAX. Main and separate cold fragments were reviewed together. Reads use carrier+0x14 and two-byte indices, with length at +0x10. The numeric selector is decimal accumulated and must be below 16 before proceeding. Normal return writes all 32 result bytes: selector, zero padding, a zero span or nonempty colon-span pointer with count and zero padding, index one past the closing brace, and a comma-derived numeric value (zero when absent). The nonempty span excludes colon and closing brace and checks start/count against carrier length. The caller copies both 16-byte halves and reads result+0x18; this is a local item cursor, not whole-format EOF. The character helper is separately joined in selectedVfsStringCarrier; error helper behavior, arbitrary-input validity, string-construction ABI, nested generic formatting and actual execution remain unresolved. No full grammar emulator or runtime output path is asserted.'}


def vfs_path_literals(pe,md,*,source,metadata_source):
    """Exact literal pool intervals plus selected native tag-5 consumers."""
    pins=AUDIT_PINS['selectedVfsPathLiterals']
    require(len(md.buf)>=24,True,metadata_source,0)
    row_start,row_size,pool_start,pool_size=struct.unpack_from('<iiii',md.buf,8)
    if not (row_start>=24 and row_size>=0 and row_size%8==0 and row_start<=len(md.buf)
            and row_size<=len(md.buf)-row_start):
        raise ContextError(metadata_source,8,'bounded eight-byte literal row table after header',
                           {'start':row_start,'size':row_size,'fileLength':len(md.buf)})
    if not (pool_start>=row_start+row_size and pool_size>=0 and pool_start<=len(md.buf)
            and pool_size<=len(md.buf)-pool_start):
        raise ContextError(metadata_source,16,'bounded literal pool after row table',
                           {'start':pool_start,'size':pool_size,'rowEnd':row_start+row_size,'fileLength':len(md.buf)})
    count=row_size//8
    require(count<=1_000_000,True,metadata_source,8)
    rows=[literal_record(md.buf[at:at+8],pool_size,source=metadata_source,offset=at)
          for at in range(row_start,row_start+row_size,8)]
    require(pe.bytes_at_va(pe.image_base+pins['literalSwitchEntryRva'],4),struct.pack('<I',pins['literalSwitchTargetRva']),source,pins['literalSwitchEntryRva'])
    raw=pe.bytes_at_va(pe.image_base+pins['literalResolverCallRva'],5)
    require(raw,b'\xe8'+struct.pack('<i',pins['literalResolverTargetRva']-pins['literalResolverCallRva']-5),source,pins['literalResolverCallRva'])
    windows=[]
    for rva,expected in pins['windows']:
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    selected=[]
    # Rows: [load RVA, literal index, exact ASCII literal].
    for rva,index,expected_text in pins['selected']:
        expected=expected_text.encode('ascii')
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        usage=pe.bytes_at_va(cell,8)
        actual=unresolved_usage_index(usage,count,tag=5,source=source,offset=cell)
        require(actual,index,source,cell)
        start,length=rows[actual]
        value=md.buf[pool_start+start:pool_start+start+length]
        require(value,expected,metadata_source,pool_start+start)
        selected.append({'rva':rva,'cellVa':cell,'usageRawHex':usage.hex().upper(),
                         'literalIndex':actual,'metadataOffset':pool_start+start,
                         'byteLength':length,'rawHex':value.hex().upper(),'ascii':value.decode('ascii')})
    return {'selected':selected,'windows':windows,
            'literalSweep':{'success':count,'failed':0,'unsupported':0,'rowStart':row_start,
                            'rowByteLength':row_size,'poolStart':pool_start,'poolByteLength':pool_size,
                            'rowsStartLength':rows},
            'level':'exact static literal bytes; direct conditional tag-5 pool-address connection',
            'boundary':'The usage resolver extracts tag and index, and tag 5 selects the literal resolver. Its cache-miss path uses header offsets +8/+16, an eight-byte row stride, row+4 pool-relative offset and row+0 byte length to call the string constructor. All literal rows have bounded pool intervals; aliases and unreferenced pool bytes are allowed, not claimed as an exclusive file partition. Six reviewed path-builder loads join four exact ASCII byte sequences containing braces and slashes. The existing builder windows store these load results into slot zero. These are static format inputs, not demonstrated output paths: cache initialization, string-constructor encoding/ABI, format-item parsing, nested formatter execution, getter values, branch selection and runtime file identity remain unresolved.'}
