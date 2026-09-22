"""Stream, VFS and UnityPlayer consumer validations.

Moved verbatim out of ``context_audit``; that module owns the audit
contract and the report it assembles.
"""
from __future__ import annotations

import hashlib
import struct
from scripts.game_data.il2cpp.context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.il2cpp.context import named_top_level_type
from scripts.game_data.il2cpp.context import method_pointer_indices, generic_method_candidates
from scripts.game_data.il2cpp.context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.il2cpp.context import literal_record
from scripts.game_data.il2cpp.context_audit_common import require
from scripts.game_data.il2cpp.context_audit_memorypack import module_methods


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


def vfs_stream_identity(pe,md,modules,image_owners,reg,*,source):
    """Normal allocation candidate plus independent token/parent/slot identities."""
    identity=named_top_level_type(md.buf,b'Common.Beyond.dll',b'Beyond.VFS',b'VFSFileReadStream',source=source)
    require((identity['typeDefinitionIndex'],identity['byvalTypeIndex']),(31896,147393),source)
    require(md.types[31896].parent_index,143204,source)
    require(143204<reg['typesCount'],True,source)
    parent_pointer=pe.u64_at_va(int(reg['types'],16)+143204*8)
    parent_raw=pe.bytes_at_va(parent_pointer,16)
    require(parent_raw,bytes.fromhex('07930000000000000000120000000000'),source,parent_pointer)
    cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+0x2D7A588,7),pe.image_base+0x2D7A588,source=source)
    raw=pe.bytes_at_va(cell,8)
    index=unresolved_usage_index(raw,reg['typesCount'],tag=1,source=source,offset=cell)
    require(index,identity['byvalTypeIndex'],source,cell)
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    type_raw=pe.bytes_at_va(pointer,16)
    require(type_raw,bytes.fromhex('987C0000000000000000120000000000'),source,pointer)
    methods=module_methods(pe,md,modules,image_owners,
        [(247416,'Beyond.VFS.VirtualFileSystem','GetAssetStream',0x2D7A4C0),
         (247418,'Beyond.VFS.VirtualFileSystem','GetAssetStream',0x3187CF0),
         (247484,'Beyond.VFS.VFSFileReadStream','.ctor',0x2D076C0),
         (247486,'Beyond.VFS.VFSFileReadStream','Read',0x2D06B70),
         (247495,'Beyond.VFS.VFSFileReadStream','get_Length',0x4A490D0),
         (247496,'Beyond.VFS.VFSFileReadStream','get_Position',0x3DBBDC0)],
        source=source,expected_image='Common.Beyond.dll')
    for index,slot in ((247486,35),(247495,11),(247496,12)):
        require(md.methods[index].slot,slot,source,index)
    return {'typeIdentity':identity,'parentTypePointerVa':parent_pointer,'parentTypeRawHex':parent_raw.hex().upper(),
            'allocationCellVa':cell,'allocationCellRawHex':raw.hex().upper(),
            'allocationTypePointerVa':pointer,'allocationTypeRawHex':type_raw.hex().upper(),'methods':methods,
            'level':'exact static type/parent/token/slot relation; conditional allocation connection',
            'boundary':'The allocation callsite loads a type usage for VFSFileReadStream and passes the returned object plus the same 32-byte descriptor and inner stream to its token-joined constructor. Metadata parent points to the separately joined Stream record. This identifies the normal construction path, not successful execution, resolved live type usage, replacement callbacks, selected source file or authenticated bytes.'}


def vfs_stream_consumer(pe,*,source):
    """Descriptor-to-state and nested stream relations on reviewed normal paths."""
    edges=[]
    for rva,target in ((0x2D7A580,0x2D7A640),(0x2D7A5A0,0x26060),(0x2D7A5DF,0x2D076C0),
                       (0x2D06BCA,0x3AF70),(0x3DBBE03,0x3AF70),(0x2D06C24,0x508E0),
                       (0x4C36099,0x3A8ADF0),(0x2D06CDE,0x2C97740)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D0770C,'410F1006488D4F4848895F48410F104E100F1147280F114F38'),
        (0x4A49105,'8B433C4883C4205BC3'),
        (0x3DBBE08,'8B4B38482BC14883C4205BC3'),
        (0x2D06BC2,'B90C000000488BD3'),
        (0x3DBBDF5,'488B53484885D27433B90C000000'),
        (0x2D06C15,'B9230000004C8D4424300F29442430'),
        (0x2D06C29,'8BF83B46080F87DCF4F201'),
        (0x50906,'498B80700300004D8B80780300000F29442420FFD0'),
        (0x2D06CE3,'8BC7488B7C2468488B5C24704883C4505EC3')):
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
    identity=named_top_level_type(md.buf,b'mscorlib.dll',b'System.IO',b'FileStream',source=source)
    require((identity['typeDefinitionIndex'],identity['byvalTypeIndex']),(37648,119269),source)
    require(md.types[37648].parent_index,143204,source)
    allocations=[]
    for rva in (0x2D7AD7F,0x5BBB5C0):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        raw=pe.bytes_at_va(cell,8)
        index=unresolved_usage_index(raw,reg['typesCount'],tag=1,source=source,offset=cell)
        require(index,identity['byvalTypeIndex'],source,cell)
        pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
        type_raw=pe.bytes_at_va(pointer,16)
        require(type_raw,bytes.fromhex('10930000000000000000120000000000'),source,pointer)
        allocations.append({'rva':rva,'cellVa':cell,'cellRawHex':raw.hex().upper(),
                             'typePointerVa':pointer,'typeRawHex':type_raw.hex().upper()})
    require(allocations[0]['cellVa'],allocations[1]['cellVa'],source)
    methods=module_methods(pe,md,modules,image_owners,
        [(247286,'Beyond.VFS.UnityFileLoaderHelper','ReadFileByStream',0x2D7A640),
         (247302,'Beyond.VFS.UnityPersistFileHelper','ReadPersistAssetFileByStream',0x5BBB52C),
         (247315,'Beyond.VFS.UnityStreamingFileHelper','ReadStreamAssetFileByStream',0x2D7ACD0)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(287703,'System.IO.FileStream','.ctor',0x30A4310),
         (287706,'System.IO.FileStream','.ctor',0x2DF9D00),
         (287727,'System.IO.FileStream','Seek',0x2FC8A30)],source=source,expected_image='mscorlib.dll')
    require(md.methods[287727].slot,32,source,287727)
    edges=[]
    for rva,target in ((0x2D7A716,0x2D7ACD0),(0x2D7A975,0x5BBB52C),
                       (0x2D7ADD5,0x2DF9D00),(0x5BBB607,0x30A4310),(0x5BBB61E,0x51D80)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D7A549,'8B6B10'),(0x2D7A68C,'4080FF010F84C60200004080FF027423'),
        (0x2D7ACEB,'4963F8'),(0x5BBB547,'4963F8'),
        (0x2D7ADDA,'85FF7425'),(0x5BBB60C,'85FF7E14'),
        (0x2D7ADE9,'498B8140030000488BD74D8B89480300004533C0488BCBFFD0'),
        (0x5BBB610,'4C8BC7B9200000004533C9488BD3'),
        (0x51DA9,'4C8D4B14448BC749C1E104488BD64D030E498BCE498B014D8B4908')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    switch=pe.bytes_at_va(pe.image_base+0x2D7ACA8,28)
    require(switch,bytes.fromhex('D0A9D702DFA9D702EEA9D70251AAD70260AAD702EEA9D70219ABD702'),source,0x2D7ACA8)
    return {'typeIdentity':identity,'allocations':allocations,'methodIdentities':methods,'edges':edges,
            'windows':windows,'switchData':{'rva':0x2D7ACA8,'rawHex':switch.hex().upper()},
            'level':'exact static allocation/method identity; direct conditional initial seek',
            'boundary':'Normal mode 1 and mode 2 select distinct token-joined helpers and FileStream constructors. The descriptor dword+0x10 reaches their offset argument and is sign-extended from int32. Mode 1 seeks only for positive offsets; mode 2 seeks for any nonzero offset. Both use declared FileStream.Seek slot 32 with numeric origin 0 and discard its return; the general dispatcher uses the low 16-bit slot number and preserves the supplied offset/origin. Normal return gives the constructed stream, not proof of a successful physical path/hash match or actual initial position. Root selection, path construction, FileStream constructor/Seek internals, replacement callbacks and authenticated logical-file bytes remain unresolved. Switch data is not code.'}


def vfs_descriptor_path(pe,md,modules,image_owners,*,source):
    """Normal descriptor lookup and mode projection, not a serialized BLC join."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247352,'Beyond.VFS.FVFBlockFileInfo','get_fileChunkMD5Name',0x2D751D0),
         (247359,'Beyond.VFS.FVFBlockFileInfo','get_loaderPosType',0x2D75510),
         (247371,'Beyond.VFS.FVFBlockFileInfo','GetRelativeChunkFilePath',0x2D7A040)],
        source=source,expected_image='Common.Beyond.dll')
    edges=[]
    for rva,target in ((0x2D7A52D,0x2D7A040),(0x2D7A53A,0x2D75510),
                       (0x2D7A13E,0x2D751D0),(0x2D752DE,0x3820560),
                       (0x4C48A6A,0x6DBEEC0)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D7557F,'8B4318C1E80A'),(0x2D7A546,'0FB6F0'),(0x2D7A56C,'440FB6C6'),
        (0x2D7A0DE,'F64718020F871810ED01'),
        (0x2D7A134,'4533C0488D4D20488BD7'),
        (0x2D75260,'837F08000F8CD837ED01'),
        (0x2D75285,'448B7708488B88B8000000488B5908'),
        (0x2D752CA,'418BD6488BCB'),
        (0x2D752E8,'85C00F885237ED01'),
        (0x2D752F0,'488B4B184885C90F849E0000003B41180F838F000000'),
        (0x2D75306,'489848C1E0050F10440830'),(0x2D7531E,'0F1106'),
        (0x4C48A6F,'0F57C0E99AC812FE')):
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
    methods=module_methods(pe,md,modules,image_owners,
        [(247351,'Beyond.VFS.FVFBlockFileInfo','_SetFileChunkMD5Name',0x2D755E0)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(286427,'System.Collections.Generic.Dictionary`2','TryGetValue',None),
         (286407,'System.Collections.Generic.Dictionary`2','set_Item',None)],
        source=source,expected_image='mscorlib.dll')
    value=named_top_level_type(md.buf,b'Beyond.Byte.dll',b'Beyond.Byte',b'UInt128',source=source)
    require(value['typeDefinitionIndex'],0xDF7E,source)
    int_raw='3B8D0000000000000000088000000000'
    value_raw='7EDF0000000000000000118000000000'
    instances=[]
    for index,expected in ((3297,[int_raw,value_raw]),(4291,[value_raw,int_raw])):
        instance=table.resolve(index)
        require([a.raw_type_record_hex for a in instance.arguments],expected,source)
        instances.append(instance.as_dict())
    usage=[]
    for rva,index,definition,ci in ((0x2D752A2,55461,286427,3297),
        (0x2D756A4,70920,286427,4291),(0x2D75759,70927,286407,4291),
        (0x2D757D4,55468,286407,3297)):
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
    for rva in (0x2D7527E,0x2D75689,0x2D757B9):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        require(cell,pe.image_base+0xD072F48,source,rva)
        storage.append({'rva':rva,'cellVa':cell})
    edges=[]
    for rva,target in ((0x2D756EB,0x2D79390),(0x2D757B4,0x3E1DF70),(0x2D75825,0x3820080)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in ((0x2D756F0,'85C0783D'),
        (0x2D75701,'3B41180F83FC010000489848C1E0058B5C0838895E08'),
        (0x2D75763,'8B5A202B5A28'),(0x2D7578A,'41B1010F104500448BC3498BCE'),
        (0x2D75801,'0F10450041B101498BCE'),(0x2D7581E,'8BD34889442420'),
        (0x2D7582A,'E9E5FEFFFF'),(0x2D756AB,'488B4720488B88C0000000488B81B0000000'),
        (0x2D75769,'488B4720488B88C0000000488B81C0000000')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'valueType':value,'instances':instances,'methodUsages':usage,
            'storageReferences':storage,'edges':edges,'windows':windows,
            'level':'exact static ordered instances and MethodSpec usages; direct conditional producer flow',
            'boundary':'The source usage cells name TryGetValue/set_Item, not FindEntry/TryInsert simply because the inlined call targets look like those helpers. Their MethodInfo+0x20 supplies the original Dictionary class before class RGCTX slots are loaded. Registered arguments are Int32/UInt128 and the exact reverse order. The setter probes static-carrier+0x10 using the incoming 16 bytes; a nonnegative result is bounds-checked and its indexed dword copied to descriptor+8. On a miss it computes dword+0x20 minus dword+0x28, supplies the same integer and 16-byte value in reverse orders to two helpers with numeric behavior 1, then stores that integer to descriptor+8. The second helper uses static-carrier+8, the same storage selected by the getter. Helper return values are not checked. Complete insertion/comparer/collision semantics, initialization, replacement paths, other mutations and actual reciprocal contents are unproved. UInt128 identity is not BLC MD5 provenance; serialized source/carrier/cursor and EOF remain unresolved.'}


def vfs_bytebuf_consumer(pe,md,modules,image_owners,reg,*,source):
    """Conditional serialized-input cursor path; native permissiveness is not validation."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247366,'Beyond.VFS.FVFBlockFileInfo','ReadFromByteBuf',0x2D76D10)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(449337,'Beyond.Byte.ByteHelper','ReadULong',0x2D78240)],source=source,expected_image='Beyond.Byte.dll')
    identity=named_top_level_type(md.buf,b'Beyond.Byte.dll',b'Beyond.Byte',b'ByteBufStream',source=source)
    require(identity['typeDefinitionIndex'],57215,source)
    method=md.methods[247366]
    require((method.parameter_start,method.parameter_count),(235374,2),source)
    require(235376<=len(md.parameters),True,source)
    require(md.parameters[235375].type_index,93608,source)
    require(93608<reg['typesCount'],True,source)
    pointer=pe.u64_at_va(int(reg['types'],16)+93608*8)
    type_raw=pe.bytes_at_va(pointer,16)
    require(type_raw,bytes.fromhex('7FDF0000000000000000112000000000'),source,pointer)
    edges=[]
    for rva,target in ((0x2D76F35,0x2D78240),(0x2D76FAD,0x2D78240),
        (0x2D76FC2,0x2D78240),(0x2D770CB,0x2D79390),
        (0x2D77847,0x3E1DF70),(0x2D778B2,0x3820080)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D76EB9,'66C1E108660BCA6683C1020FBFC10103'),
        (0x2D76F2A,'4533C941B0018BD6488BCF'),(0x2D76F3A,'830308'),
        (0x2D76FB2,'8D5608488945F74533C941B001488BCF'),
        (0x2D76FC7,'488945FF0F2875F7830310'),
        (0x2D770B1,'488D55F7488BCF660F7F75F7'),
        (0x2D770F4,'8B7C0838897D0F'),
        (0x2D776FE,'0F1045070F104D170F11000F114810'),
        (0x2D78298,'8D47073B43180F8D02010000'),
        (0x2D783A6,'33C0EBC3'),(0x2D782B1,'4084F60F84877ED701')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'sourceType':identity,'parameterTypePointerVa':pointer,
            'parameterTypeRawHex':type_raw.hex().upper(),'edges':edges,'windows':windows,
            'level':'exact static source-type identity; direct conditional cursor/value path',
            'boundary':'The selected source parameter joins ByteBufStream. On the reviewed no-replacement path R8 supplies a mutable carrier with cursor dword+0 and array object+8. Two initial bytes are assembled little-endian, incremented by 2 in 16 bits, then sign-extended before adding to the cursor. After an eight-byte helper call and cursor advance, two further helper calls at cursor and cursor+8 form the 16-byte container lookup input; the cursor advances 16. The same paired insertion targets are used on lookup miss, and the resulting integer enters the returned 32-byte descriptor. ReadULong with the supplied nonzero flag assembles eight bytes little-endian after per-byte index checks, but signed int32(offset+7) >= array count returns zero normally; callers still advance their cursor. Overflow and alternate flag/replacement paths are not generalized. This is not a fail-closed source-range validator or proof that returned zeros came from file bytes. Later skips, narrowed values, version/flag branches and cursor save/restore require their own closure. The array origin, authenticated BLC identity, complete carrier allocation, initial/final cursor and logical-file EOF remain unproved.'}


def vfs_block_cursor(pe,md,modules,image_owners,*,source):
    """Array -> shared cursor -> nested records; distinguish checksum and EOF."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247331,'Beyond.VFS.VFBlockMainInfo','ReadFromByteBuf',0x33AF150),
         (247335,'Beyond.VFS.FVFBlockChunkInfo','ReadFromByteBuf',0x2D76170)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(449333,'Beyond.Byte.ByteBufStream','CreateFromByte',0x449AEB0),
         (449317,'Beyond.Byte.ByteBufStream','ReadInt',0x2D76630)],source=source,expected_image='Beyond.Byte.dll')
    edges=[]
    for rva,target in ((0x33AF224,0x449AEB0),(0x33AF346,0x2D76170),
        (0x2D76351,0x2D76D10),(0x4D86E74,0x2D76630),
        (0x33AF1C4,0x2D767D0),(0x33AF1E8,0x2FE7660)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x449AEE1,'C744243400000000897C24304889742438'),
        (0x449AEF7,'0F10442430488B742468488BC30F1103'),
        (0x33AF21A,'488D4DB0458BC6488BD6'),
        (0x33AF33C,'4C8D45A08BD6488D4DC0'),
        (0x2D7634C,'4C8BC68BD5'),
        (0x2D76356,'0F10000F1048100F11030F114B104883C3204883EF0175C2'),
        (0x2D76249,'4C63F0'),(0x2D76286,'498BDE48C1E305'),
        (0x2D76326,'4585F67E43'),
        (0x33AF1A6,'8B5E18412BDE83EB0485DB0F8EEE7C9D01'),
        (0x33AF1ED,'3BF80F858A7C9D01'),
        (0x33AF3B0,'8B40182B45A085C0410F4EC685C07E0A837F48030F84A47A9D01'),
        (0x4D86E79,'90E94B8562FE'),(0x33AF3CA,'488BC7')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,
            'level':'exact static identities; direct conditional shared-cursor and return paths',
            'boundary':'The normal main-info entry passes its input array and supplied start index to CreateFromByte, which constructs 16 bytes: cursor dword, zero dword, original array pointer. Main, chunk and file readers share that same mutable carrier. Chunk processing sign-extends a ReadInt result and requests count*32 bytes before its positive-count loop; each file result is copied as 32 bytes. Allocation-helper behavior and negative-count rejection are not proved by this loop. Before parsing, main compares two helper results using array length minus start minus four and the selected tail position; helper algorithms and authenticated array provenance remain open. After the chunk loop, the normal remaining calculation clamps nonpositive array-length-minus-cursor to zero. Positive remaining with stored version 3 causes one ReadInt call, whose result is discarded before returning the object; other versions can return with positive remaining. No final equality check follows this extra read. This is not an EOF validator, even if the earlier comparison succeeds. Replacement callbacks, helper internals, upstream decryption/file identity, full record grammar and final source receipt remain unresolved.'}


def vfs_block_transform(pe,md,modules,image_owners,*,source):
    """Reviewed normal-path array aliasing, not a complete cipher implementation."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247532,'Beyond.VFS.VFSUtils','DecryptCreateBlockGroupInfo',0x318B640)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(452763,'Beyond.XXEnc.XXE1','TransformBytes',0x507D3C4),
         (452780,'Beyond.XXEnc.XXE1','WorkBytes',0x2C97EF0)],
        source=source,expected_image='Common.Beyond.XXEnc.dll')
    edges=[]
    for rva,target in ((0x318B91E,0x507D3C4),(0x507D3DE,0x2C97EF0),
        (0x318B93D,0x33AF150),(0x2C97FE6,0x2C97A90)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
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
        (0x2C97FB8,'8BC7412BC5885E30413BC47CAB')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    storage=[]
    for rva in (0x318B8F7,0x318B923):
        raw=pe.bytes_at_va(pe.image_base+rva,7)
        cell=rip_qword_load_target(raw,pe.image_base+rva,source=source)
        require(cell,pe.image_base+0xD0B9A10,source,rva)
        storage.append({'rva':rva,'cellVa':cell,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'staticStorage':storage,
            'level':'exact static identities; direct conditional in-place byte transform',
            'boundary':'On the reviewed non-replacement path, the entry retains its original array in RSI. It passes that array, static-carrier+0xE4 as offset and signed 32-bit array-length-minus-offset as count to TransformBytes. The wrapper forwards identical input/output array pointers and identical input/output offsets to WorkBytes. A positive-count normal loop reads one input byte, XORs it with a byte from state+0x28 array, and writes the same output index; its state byte counter is masked with 63 and zero invokes a separate block helper. Nonpositive count returns without validation. Initial length sums use signed 32-bit arithmetic; per-byte array indices also have unsigned bounds checks. This is not a reusable fail-closed range parser. After the transform returns, the same original array reaches the already pinned main-info reader, with a fresh +0xE4 load from the same static storage cell. No equality check proves the two runtime offset loads stayed identical. Static values, key/span and constructor ABI, state initialization/block generation, exceptional and replacement behavior, cipher parity with the maintained decoder, physical-file identity and actual execution remain unresolved. This establishes neither a complete decryption algorithm nor EOF consumption.'}


def vfs_block_file_source(pe,md,modules,image_owners,*,source):
    """File-read return carrier and loop; actual paths and Read override stay open."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247400,'Beyond.VFS.VirtualFileSystem','CreateBlockFromPersistAssetFile',0x318BC00),
         (247401,'Beyond.VFS.VirtualFileSystem','CreateFromStreamAssetFile',0x318BD20),
         (247301,'Beyond.VFS.UnityPersistFileHelper','ReadPersistAssetFileAllBytes',0x318BFA0),
         (247314,'Beyond.VFS.UnityStreamingFileHelper','ReadStreamAssetFileAllBytes',0x318C0C0)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(287401,'System.IO.File','ReadAllBytes',0x318C220),
         (287719,'System.IO.FileStream','Read',0x2FCA460)],source=source,expected_image='mscorlib.dll')
    require(md.methods[287719].slot,34,source,287719)
    require(md.methods[287719].parameter_count,3,source,287719)
    edges=[]
    for rva,target in ((0x318BC48,0x318BE20),(0x318BD63,0x318BE20),
        (0x318BC60,0x318BFA0),(0x318BD8F,0x318C0C0),
        (0x318BC8A,0x318B640),(0x318BDA9,0x318B640),
        (0x318C060,0x2D71FA0),(0x318C17E,0x2D71FA0),
        (0x318C06A,0x318C220),(0x318C188,0x318C220),
        (0x318C2BE,0x2DF9D00),(0x318C2F3,0x3AF70)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x318BC81,'4533C0488BD3488BC8'),(0x318BDA0,'4533C0488BD3488BC8'),
        (0x318C065,'33D2488BC8'),(0x318C06F,'488BF8'),(0x318C07D,'488BC7'),
        (0x318C183,'33D2488BC8'),(0x318C18D,'488BF8'),(0x318C19B,'488BC7'),
        (0x318C26A,'4533F6'),(0x318C2EE,'B90B000000'),
        (0x318C2F8,'488BF8483DFFFFFF7F0F8FB20000004885C00F8483000000'),
        (0x318C310,'8BD0'),(0x318C31E,'4C8BF885FF7E4D'),
        (0x318C341,'4C8B9060030000488B80680300004889442420448BCF458BC6498BD7488BCE41FFD2'),
        (0x318C363,'85C00F84AF0000004403F02BF8EBAF'),
        (0x318C372,'4C89BC24A0000000'),(0x318C3FB,'498BC7')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'readSlot':34,
            'level':'exact static identities; direct conditional read-loop and return-array chain',
            'boundary':'Both reviewed block constructors pass the returned array of their respective file helper directly to DecryptCreateBlockGroupInfo, after nonnull/nonempty checks. On the normal successful helper paths, a path-carrier conversion result is passed to System.IO.File.ReadAllBytes, whose returned array is preserved across cleanup and returned unchanged. The actual root strings, relative path construction, path-carrier conversion, selection/fallback and authenticated on-disk file/hash remain unresolved. ReadAllBytes calls a FileStream constructor and dispatches Length via numeric slot 11. Its positive signed length branch rejects values above INT32_MAX, requests an array of the narrowed length, and loops while signed remaining is positive. Each call uses class+0x360 and companion+0x368 (slot 34, not the previously reviewed slot 35), passes array/accumulated offset/remaining, then adds EAX to offset and subtracts EAX from remaining. Zero EAX branches to error helpers rather than the normal loop return. There is no local negative/oversized returned-count rejection or final equality check; full-fill reasoning requires the Read override contract. The registered FileStream Read definition independently declares slot 34 and three parameters, but concrete live dispatch, constructor/override internals, zero-length alternate helper, allocation/error/cleanup behavior and actual file execution are not proved. A length-based read loop is not a source-hash receipt or a serialized-reader EOF check.'}


def native_file_read(pe,md,modules,image_owners,*,source):
    """Static import/argument/count connection; no live OS or handle receipt."""
    methods=module_methods(pe,md,modules,image_owners,
        [(287719,'System.IO.FileStream','Read',0x2FCA460),
         (287775,'System.IO.MonoIO','Read',0x3AFCB00)],source=source,expected_image='mscorlib.dll')
    edges=[]
    for rva in (0x2FCA582,0x2FCA69D):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+0x3AFCB00,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':0x3AFCB00,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2FCA4BD,'85ED0F8826AACF0185DB0F88BAA9CF01418B46183BE80F8F55A9CF012BC33BE80F8FF2A8CF01'),
        (0x2FCA508,'412BFF3BDF7F028BFB'),
        (0x2FCA576,'448BC8498BCF4533C0498BD5'),
        (0x2FCA68C,'448BCB4889442420448BC5498BD6498BCF'),
        (0x2FCA6BC,'83F8FF0F848CA6CF014863C348014668E90DFFFFFF'),
        (0x2FCA5DE,'03DF8BC3'),
        (0x3AFCB1D,'418BD94963F04C8BF24533E4'),
        (0x3AFCB7A,'4C8B7810'),
        (0x3AFCB93,'488BBC24B00000004489278D041E413B46180F87AE000000'),
        (0x3AFCBAB,'488D56204903D644896424344C896424204C8D4C2434448BC3498BCF'),
        (0x3AFCBCD,'85C07508'),(0x3AFCBD7,'89078B5C2434'),
        (0x3AFCBF5,'B8FFFFFFFF833F000F45D8895C2438'),(0x3AFCC3C,'8BC3')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    # This selected-build witness authenticates the header directory reference,
    # first descriptor and two exact name thunks. Other imports stay opaque.
    optional=pe.u32_at_file(0x3C)+24
    require(pe.u32_at_file(optional+120),0xCF8EBC0,source,optional+120)
    require(pe.u32_at_file(optional+124),220,source,optional+124)
    require(pe.bytes_at_va(pe.image_base+0xCF8EBC0,20),
            struct.pack('<IIIII',0xCF8ECE8,0,0,0xCF8FE50,0xA82F048),source,0xCF8EBC0)
    require(pe.bytes_at_va(pe.image_base+0xCF8FE50,13),b'KERNEL32.dll\0',source,0xCF8FE50)
    imports=[]
    for rva,index,name_rva,hint,name in (
        (0x3AFCBC7,78,0xCF8FC30,0x4A9,b'ReadFile'),
        (0x3AFCBD1,4,0xCF8F668,0x28D,b'GetLastError')):
        raw=pe.bytes_at_va(pe.image_base+rva,6)
        require(len(raw),6,source,rva)
        require(raw[:2],b'\xff\x15',source,rva)
        slot=rva+6+struct.unpack_from('<i',raw,2)[0]
        require(slot,0xA82F048+index*8,source,rva)
        lookup=0xCF8ECE8+index*8
        require(pe.bytes_at_va(pe.image_base+lookup,8),struct.pack('<Q',name_rva),source,lookup)
        require(pe.bytes_at_va(pe.image_base+name_rva,len(name)+3),struct.pack('<H',hint)+name+b'\0',source,name_rva)
        imports.append({'callRva':rva,'iatSlotRva':slot,'lookupSlotRva':lookup,
                        'nameRva':name_rva,'name':name.decode('ascii'),'dll':'KERNEL32.dll'})
    return {'methods':methods,'edges':edges,'windows':windows,'selectedImports':imports,
            'level':'exact static import/identity joins; direct conditional buffer and returned-count flow',
            'boundary':'The reviewed FileStream array overload checks negative offset/count and offset against array length minus count before its normal buffered path. Buffered and direct reads call the same MonoIO helper. That helper extracts a handle carrier at +0x10, compares the 32-bit offset-plus-count against array length, then passes handle, array+0x20+sign-extended offset, count, address of a zeroed out DWORD and a zero fifth argument to the static ReadFile import slot. A zero API return calls the static GetLastError slot and stores its result through the supplied error pointer. The helper returns the out DWORD when that error word is zero, otherwise -1; it does not derive the count from the API boolean return. The direct FileStream branch records that count, tests its error and -1 paths, updates state position and adds already-buffered bytes for its normal return. This distinguishes API boolean, out-byte count, error and accumulated read count. Only two name thunks and their descriptor are joined, not the entire import directory; live IAT contents, imported function behavior, handle provenance, full buffered-state invariants, alternate async/error/cleanup paths and runtime execution remain unresolved. No authenticated-file receipt, unconditional full-read guarantee or serialized EOF follows.'}


def vfs_path_carrier(pe,md,modules,image_owners,*,source):
    """Four-slot path carrier construction/consumption, not concrete root identity."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247308,'Beyond.VFS.UnityPersistFileHelper','GetPersistAssetFilePath',0x2D7F920),
         (247322,'Beyond.VFS.UnityStreamingFileHelper','GetStreamAssetFilePath',0x2D7DBF0),
         (247278,'Beyond.VFS.UnityFileLoaderHelper','get_persistentDataPath',0x2D7FE70),
         (247272,'Beyond.VFS.UnityFileLoaderHelper','get_streamingAssetsPath',0x2F46C10)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(452858,'Beyond.VFS.ThreadUnsafeStringUtils','AppendPathInfo',0x2D7E480)],
        source=source,expected_image='Unsafe.VFS.dll')
    edges=[]
    for rva,target in ((0x318BFFA,0x2D7F770),(0x318C12E,0x2D7AE60),
        (0x2D7F7CB,0x2D7F920),(0x2D7AEC6,0x2D7DBF0),
        (0x2D7FB68,0x2D7FE70),(0x2D7FD10,0x2D7FE70),
        (0x2D7DF60,0x2F46C10),(0x2D7E0CC,0x2F46C10),(0x2D7E210,0x2F46C10),
        (0x318C03E,0x2D7E480),(0x318C15D,0x2D7E480),
        (0x2D7E601,0x2DF2AA0),(0x2D7E636,0x2D72FA0)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D7F7D3,'0F10000F1048100F11030F114B10'),
        (0x2D7AECE,'0F10000F1048100F11030F114B10'),
        (0x2D7FB6D,'4889442438'),(0x2D7FBCF,'4889742440'),(0x2D7FC2F,'4C897C2448'),
        (0x2D7FD15,'4889442438'),(0x2D7FD70,'4C897C2440'),
        (0x2D7FDE3,'498BC6410F1106410F114E10'),
        (0x2D7DF65,'488945C8'),(0x2D7DFBF,'4C8975D0'),(0x2D7E00F,'488975D8'),
        (0x2D7E215,'488945C8'),(0x2D7E26F,'488975D0'),
        (0x2D7E2D9,'410F1107410F114F10'),
        (0x2D7E58A,'488B7E08'),(0x2D7E5A4,'4C8B7610'),(0x2D7E5B7,'4C8B3E488B7618'),
        (0x2D7E5EE,'48897424204D8BCE4C8BC7498BD7488D4C2438'),
        (0x2D7E61E,'488D5020'),(0x2D7E62B,'4533C9448B442440488BCB')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'carrierByteLength':32,
            'level':'exact static identities; direct conditional four-slot carrier flow',
            'boundary':'The file-helper checks call two distinct builders and copy both 16-byte halves of their results into the caller-supplied 32-byte carrier. On the non-replacement builder paths, slot +0 comes from branch-selected static storage and slot +8 from the respective path getter. Nonempty first input normally fills +0x10 with that input and +0x18 with the second candidate; the empty/null first-input branch instead fills +0x10 with the second candidate and leaves +0x18 zero. Streaming can transform the second candidate before these stores; its helper behavior and predicate semantics remain unresolved. AppendPathInfo receives that carrier, skips work when slot +0 is null/empty, substitutes a shared static value for null slots +8/+0x10/+0x18, and forwards +0,+8,+0x10,+0x18 in that order to another helper with a separate stack companion. Its resulting temporary array+0x20 and temporary DWORD length are passed to the append consumer. The copy width and argument order do not establish formatting syntax, separators, string contents, final output length, concrete root, overlay selection or file/hash identity. Static values, getter initialization, formatting/append ABI and helper internals, replacements and runtime execution remain unresolved.'}


def vfs_path_format_context(pe,md,modules,image_owners,reg,table,*,source):
    """Original generic arguments and append units, not complete format grammar."""
    methods=module_methods(pe,md,modules,image_owners,
        [(443949,'Cysharp.Text.Utf16ValueStringBuilder','AppendFormat',None),
         (443868,'Beyond.UnSafeString','Append',0x2D72FA0)],source=source,expected_image='ZString.dll')
    rva=0x2D7E5E2
    cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
    require(cell,pe.image_base+0xD06A7F8,source,rva)
    raw=pe.bytes_at_va(cell,8)
    index=unresolved_usage_index(raw,reg['methodSpecsCount'],tag=6,source=source,offset=cell)
    require(index,627375,source,cell)
    va=int(reg['methodSpecs'],16)+index*12
    spec=pe.bytes_at_va(va,12)
    require(method_spec_record(spec,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
            (443949,-1,8335),source,va)
    instance=table.resolve(8335)
    require([a.raw_type_record_hex for a in instance.arguments],
            ['C78C00000000000000000E0000000000']*3,source)
    windows=[]
    for at,hex_bytes in (
        (0x2D7E5E9,'4889442428'),(0x2DF2AC1,'4C8B757F488BFA4C8BE1'),
        (0x2DF2B28,'4863C30FB74C47146683F97B'),
        (0x2DF2D9E,'488B457F488B556F488B4038488B4808'),
        (0x2DF2E0C,'488B457F488B5567488B4038488B08'),
        (0x2DF2E94,'488B457F488B5577488B4038488B4810'),
        (0x2DF2D43,'45017C2408'),
        (0x2D72FAD,'4C8BFA418BF0418BD0488BD9'),
        (0x2D73006,'488B43208B088D04364863E84863C14C8D3447'),
        (0x2D73029,'4C8BC5498BD7498BCEFFD0'),
        (0x2D73065,'488B43208B0003F0'),(0x2D73097,'488B43208930'),
        (0x2D730CE,'488B43208B003B43287D38'),
        (0x2D73103,'488B43208B00489833C966890C47')):
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
    windows=[]
    for at,expected in (
        (0x2DF760,'482BD14983F808'),(0x2DF790,'8A013A0411750C'),
        (0x2DF79F,'4833C0C31BC083D8FFC3'),
        (0x2DF814,'488B0C0A480FC8480FC9483BC11BC083D8FFC3'),
        (0x1F21F,'4C8BC7483BF74C0F42C6E832052C00'),
        (0x1F29C,'483BFE7293'),
        (0x1F264,'4C8BC6483BDE4C0F42C3E8ED042C00'),
        (0x1F42E,'483BF30F8349FEFFFF'),
        (0x1F36F,'4C8BC7483BF74C0F42C6E8E2032C00'),
        (0x1F3D5,'483BFE72AA'),(0x1F43C,'483BF3738B')):
        raw=pe.bytes_at_va(pe.image_base+at,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,at)
        windows.append({'rva':at,'rawHex':raw.hex().upper()})
    return {'windows':windows,'level':'direct conditional byte-order comparison',
            'boundary':'The complete comparator consumes the supplied byte count using alignment bytes, bounded qword groups and remaining bytes. Equal prefixes return zero. Byte mismatches return -1/+1 using unsigned comparison flags; qword mismatches byte-swap both operands before the same unsigned ordering, preserving first-byte lexicographic order. The resolver supplies the smaller key/query byte length, then uses length comparisons to order equal prefixes, for both original and transformed queries. Hence a matching prefix alone is not key equality. No character decoding, case folding or locale comparison occurs in this reviewed helper. Its count is not an independent allocation bound; valid pointer extents and string construction/copy, tree invariants, actual keys and execution remain prerequisites. This does not establish a live lookup result, formatter selection or file identity.'}


def resolver_prefix_query(pe,*,source):
    """Conditional prefix extent, not live key equality or lookup success."""
    windows=[]
    for at,expected in (
        (0x1F2D6,'BA28000000488BCBE85D052C00'),
        (0x1F2EC,'482BC34883F8FF'),
        (0x1F2F9,'4C8BC84533C0488D542440488D4C2420E892FDFFFF'),
        (0x1F30E,'488BD0488D4C2420E855460000'),
        (0x1F0BD,'4C3941100F828F7A2C00488B4110492BC0493BC14C0F42C8'),
        (0x1F0D5,'488379180F7603488B094A8D14014D8BC1488BCBE8E2570000'),
        (0x2399C,'0F10070F11030F104F100F114B10'),
        (0x24973,'4C8BC348894718488BD648895F10498BCEE897A32B00')):
        raw=pe.bytes_at_va(pe.image_base+at,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,at)
        windows.append({'rva':at,'rawHex':raw.hex().upper()})
    return {'windows':windows,'queryStart':0,'delimiterByte':40,
            'level':'direct conditional prefix-range construction',
            'boundary':'After a successful delimiter search the resolver subtracts the query data pointer from the result, supplies that difference as requested length and supplies start zero to the subrange helper. The helper unsigned-checks start<=length, clamps requested length to length-start, selects inline or pointer bytes by capacity>15 and forwards source+start with the bounded count to a constructor. Its result is moved as two 16-byte halves into the second query carrier. For a valid successful search of the first left parenthesis this requests exactly the bytes before that delimiter, excluding parentheses and their suffix; it does not simply remove two final bytes. The reviewed search uses scalar and SIMD matching; no arbitrary no-match return guarantee is promoted from undefined BSF-zero destination contents. Allocation/copy/comparison helper semantics, malformed carriers, actual cache/tree contents and successful lookup remain unresolved. This conditional extent does not establish live equivalence between the requested and registered names.'}


def unity_loader_conversion(pe,*,source):
    """Selected conversion counts and end pointer; no successful API receipt."""
    bodies=[]
    for start,end,expected in (
        (0x22A130,0x22A235,'AEF375DB6CF045093078E4299BCCB8EF554CF3E39C8F1682350D542BCD7A539B'),
        (0x22A090,0x22A0D5,'3B05F568B8ED9FA3D4F39B42D3765B62FF2DAD7A61D1B0425E1E8D57C411FF7F'),
        (0xEDA2CA,0xEDA2DD,'CDFAA7C4BF101716557C796C22B29B593F21B1181CD5CA0670E9AE8AFCA6BB17'),
        (0xEDA2F2,0xEDA305,'F141693EAD546988017B299AD444ECE651B9904562BE0654D0CEF9C165CDC250'),
        (0x3CE6A0,0x3CE6B8,'90A3B5C1237913A161A55C77A96688A23E1FAD0DA89E369F0C9DC40BF754F202')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    caller=bytes.fromhex('E805BEF2FF488D9424A0000000488D4C2430E853BDF2FF')
    require(pe.bytes_at_va(pe.image_base+0x2FE326,len(caller)),caller,source,0x2FE326)
    return {'bodies':bodies,'callerRva':0x2FE326,'callerRawHex':caller.hex().upper(),
            'codePageArgument':65001,'flagsArgument':0,'elementByteLength':2,
            'level':'direct conditional count, terminator and end-pointer flow',
            'boundary':'The converter receives a pointer-to-input-pointer, a 64-bit input count and an output representation. With nonzero count its first selected MultiByteToWideChar import call receives ECX=65001, EDX=0, R8=input data, R9D=low DWORD input count, a null output and zero output count. A nonpositive EAX goes to an unreviewed reset helper. A positive EAX is sign-extended and used for capacity selection, stored length (or inline 12-length WORD encoding), and a zero WORD at data+2*length before a second import call. The second call uses the same input bytes/count and a helper-derived output data/count; its EAX survives the epilogue but the module caller does not inspect it before calling the end-pointer helper. That helper selects inline/pointer data and writes data+2*representationLength into its output slot. Its length leaf returns QWORD +0x10 unless tag BYTE +0x20=1, when it returns 12-zero-extended WORD +0x18; it preserves the R8 data register used by the end-pointer caller. Tag-two cold branches call a capacity helper before rejoining. Capacity allocation, reset and tag mutation remain unresolved, so neither output bounds nor conversion success is asserted. Representation length and the subsequent slash-loop end are not validated against the second API return. This is not Unicode parity, an OS binding receipt, a loaded-image hash or a SkillData final cursor.'}


def unity_loader_input(pe,*,source):
    """Exact selected caller's fixed inline request, not loaded image identity."""
    windows=[]
    # These are selected path windows, not whole-function coverage. The helper's
    # other branches cannot be selected by this caller's explicit tag=1/count=16.
    for start,end,expected in (
        (0x5579C0,0x557A20,'C8C0DCA5C01C98FA0E86CCCFB3563C582786D42C411A9BFDA6A16F1A8625DC7A'),
        (0xF48826,0xF48830,'603B5330B684DA48E711384D93EC77A08D666CD2F2F778E33918B2CCF13A3B26'),
        (0x74A60,0x74A99,'4AA8D511727CC6C391DE9337AE1A5E47AF18F4F3EF3F9D70D2C8649BAFBE47B9')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        windows.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    literal=b'GameAssembly.dll'
    require(pe.bytes_at_va(pe.image_base+0x187F180,16),literal,source,0x187F180)
    return {'windows':windows,'literalRva':0x187F180,'requestedModuleName':literal.decode('ascii'),
            'requestByteLength':16,'loaderCallRva':0x557A1B,'loaderRva':0x31E6C0,
            'level':'direct selected caller inline-byte construction and argument flow',
            'boundary':'The caller initializes a stack representation with tag BYTE +0x20=1, then calls a helper with count 16. On these explicit inputs the reviewed helper path compares count against 24 and returns the original representation address without mutating it or invoking other callees. The caller copies the exact 16-byte GameAssembly.dll literal to that address and writes a separate zero byte at +16. Its tag-one cold branch sets BYTE +0x18=8, rejoins the hot path and passes the same representation address in RCX to the reviewed module loader. The previously verified length helper therefore computes 24-8=16 on this carrier. Other capacity/helper branches and the caller after the loader call are outside this claim. This proves a static basename request, not actual invocation, conversion correctness, the selected module-cache entry, Windows search-path resolution, loaded absolute path or loaded image hash. It cannot certify a current GameAssembly binding or any SkillData source/cursor.'}


def unity_module_lookup(pe,*,source):
    """Selected loader/lookup control flow and import identities, not live bindings."""
    bodies=[]
    # Include split hot fragments and their explicit cold branch destinations.
    # Callees are not included in these extents or implicitly given semantics.
    for start,end,expected in (
        (0x2FE290,0x2FE40F,'F3362A1AE0D28E3F6EA2F4C0606C3FCE395EEE92AC7ED140172969691E5C3064'),
        (0xEFE324,0xEFE37B,'7BCEC022B9ACAB3E5D1EACBF5F25CFEC4E492BB9BD213BF1596A6F12D2637756'),
        (0x31E670,0x31E6B3,'20303ED34206BCD416A1CA61BCCE44C1022E929A69844EE7C5A5F9D730776624'),
        (0xF00A86,0xF00AFF,'76809E14C42148522DF78F2C0594B126180942EBA7F4F23C4EF0F41BB38BCB78'),
        (0x31E6C0,0x31E6DA,'CA1191138A5ECBDBA6B4E705D8C9FCB3C17F96B47989FCEAB060605A3EAA1DC1')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    optional=pe.u32_at_file(0x3C)+24
    require(pe.u32_at_file(optional+120),0x1C3624C,source,optional+120)
    require(pe.u32_at_file(optional+124),420,source,optional+124)
    require(pe.bytes_at_va(pe.image_base+0x1C3624C,20),
            struct.pack('<IIIII',0x1C36648,0,0,0x1C38088,0x185B258),source,0x1C3624C)
    require(pe.bytes_at_va(pe.image_base+0x1C38088,13),b'KERNEL32.dll\0',source,0x1C38088)
    imports=[]
    for at,index,name_rva,hint,name in (
        (0x2FE388,207,0x1C37618,0x3F7,b'LoadLibraryW'),
        (0x31E689,211,0x1C375CE,0x2DD,b'GetProcAddress'),
        (0x22A16A,216,0x1C3756A,0x423,b'MultiByteToWideChar'),
        (0x22A1F5,216,0x1C3756A,0x423,b'MultiByteToWideChar')):
        raw=pe.bytes_at_va(pe.image_base+at,6)
        require(len(raw),6,source,at)
        require(raw[:2],b'\xff\x15',source,at)
        slot=at+6+struct.unpack_from('<i',raw,2)[0]
        require(slot,0x185B258+index*8,source,at)
        lookup=0x1C36648+index*8
        require(pe.bytes_at_va(pe.image_base+lookup,8),struct.pack('<Q',name_rva),source,lookup)
        require(pe.bytes_at_va(pe.image_base+name_rva,len(name)+3),
                struct.pack('<H',hint)+name+b'\0',source,name_rva)
        imports.append({'callRva':at,'iatSlotRva':slot,'lookupSlotRva':lookup,
                        'nameRva':name_rva,'name':name.decode('ascii'),'dll':'KERNEL32.dll'})
    return {'bodies':bodies,'selectedImports':imports,'moduleHandleCacheRva':0x1CF4C20,
            'level':'exact selected import identities; direct conditional handle and lookup-result flow',
            'boundary':'The loader entry forwards its incoming RCX to a module helper, stores the returned RAX in the shared module-handle cache and exits on zero before the export-request body. The helper has a runtime-cache branch that returns a qword supplied by another helper. Its other branch extracts input representation data/length, invokes conversion helpers, iterates two-byte elements up to a helper-supplied end pointer replacing 0x2F with 0x5C, selects inline or pointer storage and passes it as RCX to the selected static LoadLibraryW import slot. The imported return is preserved, optionally stored through a cache helper, and returned after cleanup. The export lookup helper preserves incoming module/name arguments for the selected GetProcAddress import, returns its nonzero result, or returns zero for a null module. On a zero imported result its cold branch calls diagnostic/cleanup helpers and rejoins the return of the saved zero, conditional on those calls returning normally. Only the first import descriptor and three selected name thunks are joined, including both conversion calls to MultiByteToWideChar, not complete import-table coverage or live IAT contents. Cache lookup/insertion and string conversion helper semantics, end-pointer validity, actual input module path, loaded image identity, successful binding and execution remain unresolved. No authenticated SkillData source, final cursor or terminal uniqueness follows.'}


def unity_conversion_exports(pe,unity,*,source,unity_source):
    """Two selected export chains and conditional output-slot write ABI."""
    requests=[]
    for at,rawhex,name_at,name,export_name_at,name_slot,ordinal_slot,function_slot,index,target in (
        (0x3205CD,'488B0D4C469D01488D150D6D6601E890E0FFFF488905D14A9D01',0x19872E8,
         'il2cpp_string_new_len',0xCF8DAF9,0xCF8BC5C,0xCF8C0EE,0xCF8B5E4,243,0x24AD0),
        (0x31FA06,'488B0D13529D01488D1544636601E857ECFFFF48890538519D01',0x1985D58,
         'il2cpp_gc_wbarrier_set_field',0xCF8D0D4,0xCF8BAD8,0xCF8C02C,0xCF8B460,146,0xE170)):
        raw=bytes.fromhex(rawhex);literal=name.encode('ascii')+b'\0'
        require(unity.bytes_at_va(unity.image_base+at,len(raw)),raw,unity_source,at)
        require(unity.bytes_at_va(unity.image_base+name_at,len(literal)),literal,unity_source,name_at)
        for slot,expected in ((name_slot,struct.pack('<I',export_name_at)),
                              (ordinal_slot,struct.pack('<H',index)),(function_slot,struct.pack('<I',target))):
            require(pe.bytes_at_va(pe.image_base+slot,len(expected)),expected,source,slot)
        require(pe.bytes_at_va(pe.image_base+export_name_at,len(literal)),literal,source,export_name_at)
        requests.append({'name':name,'loaderRva':at,'rawHex':rawhex,'exportTargetRva':target,'ordinal':index+1})
    require(pe.bytes_at_va(pe.image_base+0xE177,6),bytes.fromhex('4C8BCA4C8902'),source,0xE177)
    return {'requests':requests,'level':'exact selected export identities; direct conditional output-slot store',
            'boundary':'Unity requests string_new_len into the first conversion cache and gc_wbarrier_set_field into the second. Selected GameAssembly export name/ordinal/function slots join the former to the previously reviewed byte-to-string constructor, and the latter to a leaf that writes R8 into [RDX] before optional atomic bitmap marking. The caller passes the first result in R8 and its separate output slot in RDX, then reads that slot. Conditional on these dynamic bindings and successful calls, the returned qword is the first constructor result, not a second newly constructed object. The barrier marking branch and constructor internal allocation helpers are not a live GC receipt. Loader module identity, actual cache bindings, lifecycle, input validity, query normalization and concrete directory remain unresolved. Only selected export chains are joined, not full export coverage.'}


def unity_path_return(pe,*,source):
    """Selected return-slot and string representation, not runtime path value."""
    windows=[]
    for rva,expected in (
        (0x32BA24,'488D4C2420E822000000488BD0488D4C2460E88502FAFF'),
        (0x32BA3B,'488D4C2420E8CB8ED4FF488B442460'),
        (0x32BA63,'4C8D0596245401488BCB488D542420E819000000'),
        (0x2CBCC6,'488BD94C8BCA488BCAE81C8FDAFF'),
        (0x2CBCD4,'80792001751F448BC0488D4C2430498BD1E816000000'),
        (0x2CBCEA,'488B08488BC348890B'),(0x2CBCF9,'4D8B09EBDC'),
        (0x74BF0,'807920017405488B4110C3480FBE5118B818000000482BC2C3'),
        (0x2CBD06,'488B05AB93A2014C8BCA488BD9418BD0498BC9FFD0'),
        (0x2CBD1B,'4C8BC0488D54243033C9FF152D8EA201488B442430488903')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    literal=b'StreamingAssets\0'
    require(pe.bytes_at_va(pe.image_base+0x186DF00,len(literal)),literal,source,0x186DF00)
    return {'windows':windows,'literal':'StreamingAssets','representationTagOffset':32,
            'level':'direct conditional return-slot flow',
            'boundary':'The selected registered target builds a temporary representation, passes it to a converter with a separate output slot, cleans up the temporary and returns that output qword. A nested builder supplies the exact StreamingAssets literal to another helper, not proof of concatenation semantics or root value. The converter length helper returns QWORD +0x10 unless BYTE +0x20 equals one; on that branch it returns 24 minus sign-extended BYTE +0x18. The same tag chooses inline representation versus the pointer at +0. Only the low DWORD length reaches the next helper. That helper calls a dynamic function with data pointer and length, then forwards its result to a second dynamic function with a separate output slot and returns the slot qword. These calls are not yet verified managed-string constructors. Dynamic targets, allocation/cleanup and joining helpers, underlying path initialization, tag validity and actual execution remain unresolved; no authenticated file or runtime directory is asserted.'}


def unity_registration_pair(pe,*,source):
    """Shared native loop index proves static pairing, not active registration."""
    body=pe.bytes_at_va(pe.image_base+0x3BF7C0,0x53)
    require(hashlib.sha256(body).hexdigest().upper(),
            'DAA468EB7D4B399BCE0FCEB29186340606D92272D61C56D5D08D4FC158888AB7',source,0x3BF7C0)
    count=0xF7E;values_rva=0x19DD250;names_rva=0x19E4E40
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
    selected=rows[299]
    require(selected['nameVa'],pe.image_base+0x19F1D50,source,names_rva+299*8)
    require(selected['valueVa'],pe.image_base+0x32BA20,source,values_rva+299*8)
    literal=b'UnityEngine.Application::get_streamingAssetsPath\0'
    require(pe.bytes_at_va(selected['nameVa'],len(literal)),literal,source,0x19F1D50)
    return {'loopRva':0x3BF7C0,'loopSha256':hashlib.sha256(body).hexdigest().upper(),
            'namesRva':names_rva,'valuesRva':values_rva,'slotByteLength':8,
            'summary':{'success':count,'failed':0,'unsupported':0},'rows':rows,
            'selected':dict(selected,name=literal[:-1].decode('ascii')),
            'level':'direct static name/value argument pairing',
            'boundary':'The complete loop starts at index zero, derives image base with RIP-relative LEA, loads RDX and RCX from separate arrays using the same byte offset, calls the reviewed forwarder and advances by eight until 0xF7E entries. Both complete pointer vectors are bounded and every target is checked for one-byte addressability only; this is not complete string/body decoding. Entry 299 independently pairs the selected interface name with RVA 0x32BA20. The registered name lacks the parentheses in the resolver request, so matching still depends on the unclosed query helper path. Loop invocation, callback effects, dynamic export resolution, tree insertion, duplicate registrations and the selected target body/return ABI remain unresolved. No current directory or authenticated-file identity is inferred.'}


def unity_registration_forwarder(pe,*,source):
    """Selected dynamic export request and forwarding, not live binding."""
    raw=pe.bytes_at_va(pe.image_base+0x3BF270,0x6A)
    require(hashlib.sha256(raw).hexdigest().upper(),
            'B5EAB384DA5D794DB6D62A17D18789C09FB178E6BA346BB0EB3F12D1A739BCB3',source,0x3BF270)
    windows=[]
    for rva,value in ((0x31E8F9,'488B0D20639D01488D15F1536601E864FDFFFF488905AD669D01'),
                      (0x3BF2D3,'48FF25E65C9301')):
        chunk=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(value)))
        require(chunk,bytes.fromhex(value),source,rva)
        windows.append({'rva':rva,'rawHex':chunk.hex().upper()})
    name=b'il2cpp_add_internal_call\0'
    require(pe.bytes_at_va(pe.image_base+0x1983CF8,len(name)),name,source,0x1983CF8)
    return {'windows':windows,'forwarderRva':0x3BF270,'forwarderByteLength':len(raw),
            'forwarderSha256':hashlib.sha256(raw).hexdigest().upper(),
            'requestedExport':name[:-1].decode('ascii'),'functionCacheRva':0x1CF4FC0,
            'level':'exact static request; direct conditional two-argument forwarding',
            'boundary':'A selected loader window supplies a module-handle carrier and the NUL-terminated export name to a dynamic lookup helper, then stores its result in the function cache. The full reviewed forwarding function preserves the two entry arguments, passes them to each selected callback in a separately stored pointer array when its count is positive, then tail-jumps through that same function cache with the original arguments. The zero-callback branch reaches the same tail jump. This connects requested export name to a conditional cache consumer, not the actual module handle, resolved function identity, successful initialization or runtime execution. Callback identities/state, lookup helper cold paths, registration callers and concrete interface-name/function-value pairs remain unresolved. The nearby interface-name pointer array is only a lead and is not joined by position or matching counts.'}


def vfs_root_resolver(pe,*,source):
    """Static requested interface and conditional cache flow, not actual root."""
    windows=[]
    for rva,expected in (
        (0x2F46CD9,'E8325F9F00'),(0x2F46CE5,'488BD8'),
        (0x2F46CFD,'488B89B800000048895908'),
        (0x2F46CA7,'488B80B8000000488B4008'),
        (0x393CC14,'488B052D12570A4885C07407'),
        (0x393CC20,'4883C42848FFE0'),
        (0x393CC27,'488D0D1A7BEF06E87D256EFC'),
        (0x393CC3C,'4889050512570AEBDB'),
        (0x1F1DC,'4C8B2D7515E90D498B5D084D8BFD'),
        (0x1F293,'498B4740E957010000'),
        (0x1F2D6,'BA28000000488BCBE85D052C00'),
        (0x1F32A,'4C8B2D2714E90D498B5D084D8BFD'),
        (0x1F3CC,'4D3BFD751133DBEB11'),
        (0x1F3E2,'498B5F40'),(0x1F3F0,'488BC3'),
        (0x2E6B64,'48C7C0FFFFFFFFE97F87D3FF'),
        (0x2076F,'4889542410'),(0x2077D,'488BEC'),
        (0x207E6,'4C8B256BFFE80D'),
        (0x208BB,'488D1D96FEE80D'),
        (0x208CA,'B948000000E848301700'),
        (0x208DD,'0F1045D80F1140200F104DE80F114830'),
        (0x20924,'E837FCFFFF4C8BE8488B453849894540'),
        (0xF872C,'4889052580DB0D4889052680DB0D'),
        (0xF873F,'488900488940084889401066C7401801014889050180DB0D'),
        (0xCF8B1F0,'00000000FFFFFFFF0000000044C2F80C010000009E0100009E01000018B2F80C90B8F80C08BFF80C'),
        (0xCF8B914,'EFC4F80C'),(0xCF8BF4A,'2100'),
        (0xCF8B29C,'30050200'),(0x20530,'E92B020000')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    name=b'UnityEngine.Application::get_streamingAssetsPath()\0'
    require(pe.bytes_at_va(pe.image_base+0xA834748,len(name)),name,source,0xA834748)
    export_name=b'il2cpp_add_internal_call\0'
    require(pe.bytes_at_va(pe.image_base+0xCF8C4EF,len(export_name)),export_name,source,0xCF8C4EF)
    return {'windows':windows,'requestedInterface':name[:-1].decode('ascii'),
            'nameRva':0xA834748,'functionCacheRva':0xDEADE48,
            'lookupCarrierGlobalRva':0xDEB0758,'candidateValueOffset':64,
            'registrationWriterRva':0x20760,'sentinelInitializerRva':0xF8718,
            'selectedWriterExport':{'name':export_name[:-1].decode('ascii'),
                                    'ordinal':34,'stubRva':0x20530},
            'level':'exact static resolver name; direct conditional cache flow',
            'boundary':'The normal non-replacement streaming-path getter initialization branch calls the wrapper, preserves RAX in RBX and stores it in static carrier+8; the normal return reads that slot. The wrapper loads a cached function pointer and tail-jumps to it when nonnull. On cache miss it passes the exact NUL-terminated interface name to the resolver, checks the result, stores that result in the same function-pointer cell and tail-jumps. The requested name is not a verified resolved function identity, ABI or actual directory. The resolver loads a runtime tree carrier from a static global, follows child pointers using comparison helper results and returns candidate node+0x40 after its first lookup. If that lookup chooses the sentinel, it constructs a second query through helpers (including a search passed byte 0x28) and traverses the same carrier again; a final sentinel yields zero, otherwise node+0x40 supplies the result. The independently reviewed writer scans the first argument to a NUL byte, prepares a 32-byte key carrier and searches the same global tree. Its insertion path requests 0x48 bytes, copies the key carrier into node+0x20 and calls an insertion helper; both existing-candidate and returned-node paths store the original second argument into node+0x40. A separate initializer zeroes two global slots, requests 0x48 bytes, writes self pointers at node+0/+8/+0x10 and marker WORD 0x0101 at +0x18, then stores that pointer in the lookup global. Neither function being present proves initialization, insertion success or actual selected name/value pairs. The selected PE export header, name-pointer slot, ordinal-index slot and function slot independently join il2cpp_add_internal_call (ordinal 34) to a five-byte tail-jump stub into this writer, preserving incoming arguments. Only this selected export chain is certified, not complete export-table coverage; the stub is not assigned to the preceding pdata entry. Export callers and their actual name/value arguments, insertion/allocator internals, string construction/comparison/search/subrange helper semantics and live contents, replacement/cold failure paths, class initialization, comparison predicate semantics, live cache contents and the final path/file/hash connection remain unresolved.'}


def vfs_string_carrier(pe,*,source):
    """Conditional literal conversion and character-reader carrier connection."""
    windows=[]
    for rva,expected in (
        (0x2CB7624,'4C6341108BC2493BC07D0D4863C20FB7444114'),
        (0x24AD6,'448BC2488BD1488D4C2420E87A000000'),
        (0x24AE7,'488D4C242048837C243807480F474C24208B542430E86F0D0000'),
        (0x24BB2,'0FB60A80F980730C440FB6C141B901000000'),
        (0x24CC1,'0FB61E0FB60E80F9800F833C01000048FFC6'),
        (0x24CED,'488D480148894F10488BCF48837F18077603488B0F66891C416644896C4102'),
        (0x259DC,'897B10664489647B14'),
        (0x259FB,'4C8BC7488D4B144D03C0498BD6E813932B00')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'windows':windows,'lengthOffset':16,'elementDataOffset':20,'elementByteLength':2,
            'level':'direct conditional native carrier flow; ASCII widening branch',
            'boundary':'The format-item comma helper zero-extends the input DWORD index before comparing it with sign-extended carrier length at +0x10; for nonnegative length this rejects negative indices as well as indices at or above length. The accepted path returns the zero-extended WORD at carrier+0x14+index*2. Literal construction forwards its input pointer and zero-extended DWORD byte count into a temporary 32-byte conversion carrier. On the reviewed ASCII branch each byte below 0x80 becomes one 16-bit element, the temporary element count advances by one, and a following zero WORD is written. The wrapper chooses inline versus pointer storage by capacity>7 and forwards the low DWORD element count. The next helper writes result+0x10 length and a zero WORD at result+0x14+count*2 on its nonempty allocation path, then calls the copy helper with destination result+0x14, original element pointer and count*2. These offsets independently agree with the format-item reader. Allocation/capacity/copy helpers, empty singleton contents, non-ASCII cold/error branches, cache initialization and actual execution remain unresolved; this is not complete Unicode conversion parity or proof of a runtime output path.'}


def vfs_format_item(pe,*,source):
    """Local format-item return ABI; not whole-format or serialized EOF."""
    windows=[]
    for rva,expected in (
        (0x2DF2D39,'488D4DC7448BC3488BD7'),
        (0x2DF2D48,'E8131700000F10008B7018'),
        (0x2DF4468,'418BD8488BFA488BF1'),
        (0x2DF447F,'FFC348636A10'),
        (0x2DF44AF,'0FB75442148D42D06683F809'),
        (0x2DF4515,'4183FE10'),
        (0x2DF4594,'44895E04FFC3'),
        (0x2DF45AC,'448936'),
        (0x2DF45B4,'44897E1C'),
        (0x2DF45BD,'895E180F114608'),
        (0x2DF4639,'488D4F1444895C242C4A8D0C61896C242848894C24200F28442420'),
        (0x4C5DC40,'4183FE100F8C906819FE'),
        (0x4C5DD0E,'41F7DF4533DB')):
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
    require(pe.bytes_at_va(pe.image_base+0x4139C,4),struct.pack('<I',0x41331),source,0x4139C)
    raw=pe.bytes_at_va(pe.image_base+0x41333,5)
    require(raw,b'\xe8'+struct.pack('<i',0x2D8DE0-0x41333-5),source,0x41333)
    windows=[]
    for rva,expected in ((0x41280,'8BC1C1E81D8BF1D1EE81E6FFFFFF0FFFC8'),
        (0x2D8E1D,'48635008486340104903D0'),
        (0x2D8E2F,'4903C04A634C0204428B14024803C8')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    selected=[]
    for rva,index,expected in ((0x2D7FAB2,48841,b'{0}/{1}/{2}'),
        (0x2D7FB13,48957,b'{0}{1}{2}'),(0x2D7FC9C,48832,b'{0}/{1}'),
        (0x2D7DEEA,48841,b'{0}/{1}/{2}'),(0x2D7E068,48849,b'{0}/{1}{2}'),
        (0x2D7E188,48832,b'{0}/{1}')):
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
