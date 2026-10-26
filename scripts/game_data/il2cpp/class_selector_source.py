"""Anonymous metadata DWORD and conditional allocation-to-selector copy.

The inserted metadata column has no asserted semantic field name. Its type
row membership is exact stored evidence; binding a live receiver to an
allocation made from that row remains a separate, conditional join.
"""
import struct
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.class_creation_control import _prefix, _dominators
from scripts.game_data.il2cpp.field_setup_control import _graph, _frames
from scripts.game_data.il2cpp.initializer_control import _ALIASES, control_transfer

LABEL = 'classSelectorSource'

def metadata_selector_column(catalog, metadata):
    section=metadata.sections['typeDefinitions']; stride=metadata.type_record_size
    if stride != 92 or not metadata.types or section.size != stride*len(metadata.types):
        raise ValueError(LABEL+'.inserted-column-dialect-or-section-size')
    rows=[]; offset=None
    for ordinal, td in enumerate(metadata.types):
        if td.index != ordinal:
            raise ValueError(LABEL+'.type-row-index')
        at=section.offset+ordinal*stride
        prefix=catalog.parse_type_reference_prefix(metadata.buf,at,stride)
        tail=catalog.parse_type_layout_tail(metadata.buf,prefix[-1],stride)
        column_at=tail[-1]-24-4
        if tail[-1] != at+stride or column_at != prefix[-1]+4+8*4 or tail[2] is None:
            raise ValueError(LABEL+'.inserted-column-framing')
        if offset is None:offset=column_at-at
        if column_at-at != offset:
            raise ValueError(LABEL+'.inserted-column-offset-drift')
        value=struct.unpack_from('<I',metadata.buf,column_at)[0]
        if value != tail[2] & ((1<<32)-1):
            raise ValueError(LABEL+'.inserted-column-raw-value')
        rows.append({'typeDefinition':ordinal,'typeName':metadata.type_full_name(td),
                     'recordAbsoluteOffset':at,'selectorWord':value})
    return {'recordBytes':stride,'columnByteOffset':offset,'rows':rows,
            'columnSemanticNameProved':False,'runtimeRecordPointerIdentityProved':False}

def _memory(row, direction, register, base_register, displacement):
    raw=bytes.fromhex(row['bytes']);decoded=decode_memory_move(raw,0,int(row['va'],16))
    if decoded is None or decoded[1]!=len(raw):raise ValueError(LABEL+'.complete-dword-memory-operation')
    fact=decoded[0]['memoryOperation'];address=fact['address']
    if (fact['direction'],fact['register'],fact['registerBits'],fact['memoryBytes'],
        address['base'],address['index'],address['scale'],address['displacement'],address['ripRelative'],address['addressBits']) != (
        direction,register,32,4,base_register,None,1,displacement,False,64) or row['text']!=decoded[0]['text']:
        raise ValueError(LABEL+'.selected-dword-copy-operands: '+str(row)[:384])

def prove_creation_selector_copy(rows, base, contract, selector_offset, metadata_column_offset):
    function=contract['function'];p=function['sourceAllocationPrefix']
    edges,_,stores=_graph(rows,base,function);_frames(rows,edges,base,function)
    allocation=_prefix(rows,base,contract,function)
    overlapping=[]
    for store in stores:
        fact=store['facts'];address=fact.get('address',fact.get('destinationAddress',{}))
        size=fact.get('memoryBytes',fact.get('memoryWriteBytes'))
        if address.get('base')=='rbx' and address.get('index') is None and not address.get('ripRelative'):
            displacement=address['displacement']
            if size is None:raise ValueError(LABEL+'.unclassified-rbx-store-width')
            if displacement < selector_offset+4 and selector_offset < displacement+size:overlapping.append(store)
    if len(overlapping)!=1:raise ValueError(LABEL+'.unique-direct-selector-store')
    target=base+overlapping[0]['siteRva'];positions={int(row['va'],16):n for n,row in enumerate(rows)}
    n=positions[target]
    if n==0:raise ValueError(LABEL+'.missing-preceding-selector-source')
    source=rows[n-1];store=rows[n]
    if int(source['va'],16)+len(bytes.fromhex(source['bytes']))!=target:
        raise ValueError(LABEL+'.adjacent-read-store-transfer')
    _memory(source,'load','eax','rdi',metadata_column_offset)
    _memory(store,'store','eax','rbx',selector_offset)
    first_bound=base+p['window']['endRva'];source_at=int(source['va'],16)
    if not first_bound<=source_at<target:
        raise ValueError(LABEL+'.copy-before-proved-allocation-prefix')
    # Calls preserve these nonvolatile registers only on the stated normal ABI
    # path. Every other selected instruction is checked for a direct overwrite.
    readers={'cmp','test','bt','nop','push'}
    writers={'mov','movzx','movsx','movsxd','movups','lea','xor','and','or','add','sub','imul',
             'inc','dec','shl','shr','sar','neg','not','bts','cmovne','sete','pop'}
    for row in rows:
        at=int(row['va'],16)
        if not first_bound<=at<target:continue
        if control_transfer(row)['kind']!='next':continue
        head,_,rest=row['text'].partition(' ')
        if head in readers:continue
        if head not in writers:raise ValueError(LABEL+'.unreviewed-register-effect: '+row['text'])
        if _ALIASES.get(rest.split(',')[0]) in ('rdi','rbx'):
            raise ValueError(LABEL+'.saved-source-or-allocation-overwritten: '+row['text'])
    dom=_dominators(edges,base+function['entryRva'])
    if allocation not in dom[source_at] or source_at not in dom[target]:
        raise ValueError(LABEL+'.allocation-source-store-dominance')
    if not function['returnRvas'] or any(target not in dom[base+rva] for rva in function['returnRvas']):
        raise ValueError(LABEL+'.selector-store-does-not-dominate-normal-return')
    return {'freshSourceDwordCopiedToAllocationSelectorProved':True,
            'sourceColumnByteOffset':metadata_column_offset,'allocationSelectorByteOffset':selector_offset,
            'allocationCallRva':allocation-base,'sourceLoadRva':source_at-base,'selectorStoreRva':target-base,
            'sourceAndAllocationNonvolatileRegistersConditionallyPreserved':True,
            'selectorStoreDominatesEveryNormalLocalReturn':True,
            'uniqueDirectUnindexedAllocationStoreOverlappingSelector':True,
            'actualMetadataSourcePointerAndIndexProved':False,
            'selectorUnchangedByChildrenOrAliasesProved':False,
            'adapterReceiverIsThisAllocationProved':False,'wholeRootAdmitted':False}
