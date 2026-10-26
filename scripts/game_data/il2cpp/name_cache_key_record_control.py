"""Complete cache construction controls and physical key/record node copies.

Typed key construction and a selected insertion copy are not a proof of all
growth/migration history or a successful named runtime class lookup.
"""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory,_global,_address
from .class_creation_control import _dominators
from .class_name_lookup_control import _vector,_closed_interior
from .backward_copy_instructions import decode_legacy_vector_move
from .scalar_memory_moves import decode_scalar_memory_move
from .initializer_control import _ALIASES

LABEL='nameCacheKeyRecordControl'
def _part(rows,base,w):
    rr=[r for r in rows if base+w['startRva']<=int(r['va'],16)<base+w['endRva']]
    if not rr or int(rr[0]['va'],16)!=base+w['startRva'] or int(rr[-1]['va'],16)+len(bytes.fromhex(rr[-1]['bytes']))!=base+w['endRva']:raise ValueError(LABEL+'.projection-boundary')
    return rr
def _indexed_vector(g,base_reg,index_reg,offset):
    r=g.row();b=bytes.fromhex(r['bytes']);d=decode_legacy_vector_move(b,0,int(r['va'],16));f=d[0].get('memoryOperation',{}) if d and d[1]==len(b) else {};a=f.get('address',{})
    if (f.get('direction'),f.get('register'),f.get('memoryBytes'),a.get('base'),a.get('index'),a.get('scale'),a.get('displacement'),a.get('ripRelative'))!=('store','xmm0',16,base_reg,index_reg,1,offset,False):g.fail('indexed-node-vector-copy',(base_reg,index_reg,offset),r)
def validate_name_cache_key_record(programs,*,image_base,contract):
    c=contract;base=image_base;roles=c['functions'];required={'caller','insert','growth','rehash'}
    if set(programs)!=required or set(roles)!=required:raise ValueError(LABEL+'.function-membership')
    # The common decoder recognizes MOVSD text without attaching its physical
    # store facts. Re-decode only that exact memory form from bytes before the
    # complete-program store check; no arithmetic or register form is admitted.
    classified={}
    for role,rows in programs.items():
        padding={base+w['startRva']:w for w in roles[role]['paddingWindows']}
        by={int(r['va'],16):r for r in rows}
        for at,w in padding.items():
            if w['kind']!='unreachable-owned-trap-padding' or w['rawHex']!='CC' or w['endRva']!=w['startRva']+1 or by.get(at,{}).get('bytes')!='cc':
                raise ValueError(LABEL+'.padding-partition')
        classified[role]=[]
        for row in rows:
            if int(row['va'],16) in padding:continue
            raw=bytes.fromhex(row['bytes'])
            parsed=decode_scalar_memory_move(raw,0,int(row['va'],16))
            if parsed is not None and parsed[1]==len(raw):
                row={**row,'memoryOperation':parsed[0]['memoryOperation']}
            classified[role].append(row)
    graphs={role:_complete(rows,base+roles[role]['entryRva']) for role,rows in classified.items()}
    rows=programs['caller'];p=c['keyConstruction'];l=c['layout'];block=_part(rows,base,p['window']);g=_Grammar(block,label=LABEL+'.keyConstruction')
    _global(g,'rcx',8,base+c['globals']['metadataHeader']);_address(g,'rdx','rsp',l['callerOutputSlot']);g.take('movsxd r8, dword [rbx]')
    g.take(f'mov dword [rsp+0x{l["callerKey"]:x}], 0x0');_memory(g,'store','rbx',8,'rsp',l['callerKey']+l['record'])
    g.take(f'movsxd rax, dword [rcx+0x{l["stringSectionHeader"]:x}]',f'add rax, qword [rip => {hex(base+c["globals"]["metadataBase"])}]','add r8, rax',
        f'movsxd rax, dword [rcx+0x{l["stringSectionHeader"]:x}]',f'add rax, qword [rip => {hex(base+c["globals"]["metadataBase"])}]','movsxd rcx, dword [rbx+0x4]','add rcx, rax')
    _memory(g,'store','r8',8,'rsp',l['temporaryStrings']+8);_memory(g,'store','rcx',8,'rsp',l['temporaryStrings']);_address(g,'r8','rsp',l['callerKey'])
    _vector(g,'load','rsp',l['temporaryStrings']);_memory(g,'load','rcx',8,'rdi',l['imageCache']);_vector(g,'store','rsp',l['callerKey']+l['namespace'])
    actual=g.call(base+roles['insert']['entryRva']);g.finish();_closed_interior(rows,graphs['caller']['edges'],base,p)
    # RBX/RDI come from the actual incoming record/image pointers, and must not
    # be overwritten before assembling the key under ordinary Win64 calls.
    prefix=_part(rows,base,c['callerOrigins']['window']);g=_Grammar(prefix,label=LABEL+'.callerOrigins');g.take('mov rbx, rdx','mov rdi, rcx');g.finish()
    dom=_dominators(graphs['caller']['edges'],base+roles['caller']['entryRva']);key_at=int(block[0]['va'],16)
    for r in prefix:
        if int(r['va'],16) not in dom[key_at]:raise ValueError(LABEL+'.caller-origin-dominance')
    start=int(prefix[-1]['va'],16);end=int(actual['va'],16)
    for r in rows:
        at=int(r['va'],16);head,_,rest=r['text'].partition(' ')
        if start<at<end and head not in ('cmp','test','call','push') and _ALIASES.get(rest.split(',')[0]) in ('rbx','rdi'):raise ValueError(LABEL+'.caller-origin-overwrite')
    insert=programs['insert'];p=c['nodeCopy'];block=_part(insert,base,p['window']);g=_Grammar(block,label=LABEL+'.nodeCopy')
    _memory(g,'load','eax',4,'r14',0);g.take('mov rcx, rdi',f'shl rcx, 0x{l["nodeShift"]:x}',f'shl rdi, 0x{l["nodeShift"]:x}','mov [rcx+rbp*1], eax')
    _vector(g,'load','r14',l['namespace']);_indexed_vector(g,'rcx','rbp',l['namespace']);_memory(g,'load','rax',8,'r14',l['record']);g.take(f'mov [rcx+rbp*1+0x{l["record"]:x}], rax');g.finish();_closed_interior(insert,graphs['insert']['edges'],base,p)
    # The full key survives in nonvolatile R14 after the actual entry copy.
    key_save=base+c['insertOrigins']['keySavedRva'];by={int(r['va'],16):r for r in insert}
    if by[key_save]['text']!='mov r14, r8':raise ValueError(LABEL+'.saved-key-origin')
    dom=_dominators(graphs['insert']['edges'],base+roles['insert']['entryRva'])
    if key_save not in dom[int(block[0]['va'],16)]:raise ValueError(LABEL+'.saved-key-dominance')
    for r in insert:
        at=int(r['va'],16);head,_,rest=r['text'].partition(' ')
        if key_save<at<=int(block[-1]['va'],16) and head not in ('cmp','test','call','push') and _ALIASES.get(rest.split(',')[0])=='r14':raise ValueError(LABEL+'.saved-key-overwrite')
    for caller,site,target in (('insert',c['actualCalls']['growthCallRva'],'growth'),('growth',c['actualCalls']['rehashCallRva'],'rehash')):
        by={int(r['va'],16):r for r in programs[caller]};g=_Grammar([by[base+site]],label=LABEL+'.actualCall');g.call(base+roles[target]['entryRva']);g.finish()
    return {'status':'complete-name-cache-construction-controls-and-key-record-copy-proved','codeInstructions':sum(len(r) for r in classified.values()),
        'ownedPaddingBytes':sum(len(f['paddingWindows']) for f in roles.values()),
        'controls':{role:{k:g[k] for k in ('instructions','calls','stores','returns','traps','normalFramesProved')} for role,g in graphs.items()},
        'zeroHeaderNamespaceNameAndRecordAssembledInSameKey':True,'sourceNameAndNamespaceOffsetsReadAsSignedDwords':True,
        'nameAndNamespaceUseFreshMetadataBaseHeaderViews':True,'savedRecordAndImageRegisterOriginsProvedUnderNormalAbi':True,
        'selectedInsertionCopiesHeaderStringsAndRecordIntoSameNode':True,'nodeStrideBytes':1<<l['nodeShift'],
        'actualGrowthAndRehashCallsJoined':True,'stringPointerBoundsOrLoadedSourceObserved':False,
        'allGrowthMigrationPreservesKeyRecordRelationshipProved':False,'duplicateKeyUpdatesRecordProved':False,
        'hashProbeTerminationOrInsertionSuccessObserved':False,'lookupReturnedSystemInt32ClassProved':False,
        'primitiveClassCellNonNullProved':False,'concreteDamageTypeSharingSelected':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
