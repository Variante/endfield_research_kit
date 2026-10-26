"""Cache migration controls, closed configuration exchange and selected copies.

Complete child controls are separate from occupied-node history, allocation
effects, custom predicates and successful named runtime class lookup.
"""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .type_data_initialization_instructions import decode_initialization_memory_update
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory
from .method_carrier_instructions import decode_carrier_vector_byte_shift
from .initializer_control import _ALIASES
from .class_name_lookup_control import _closed_interior

LABEL='nameCacheMigrationSwapControl'

def _part(rows,base,w):
    rr=[r for r in rows if base+w['startRva']<=int(r['va'],16)<base+w['endRva']]
    if not rr or int(rr[0]['va'],16)!=base+w['startRva'] or int(rr[-1]['va'],16)+len(bytes.fromhex(rr[-1]['bytes']))!=base+w['endRva']:
        raise ValueError(LABEL+'.projection-boundary')
    return rr

def _config(rows,l):
    g=_Grammar(rows,label=LABEL+'.configSwap');a,b,c,d=(l[k] for k in ('configByte','configDword','configQword','configNextQword'))
    if c+8!=d or l['fragmentShiftBytes']!=8:raise ValueError(LABEL+'.config-fragment-layout')
    _memory(g,'load','xmm0',16,'rcx',c);g.take(f'movzx eax, byte [rcx+0x{a:x}]','mov r10, rcx')
    _memory(g,'load','r9d',4,'rcx',b);g.take(f'movzx r8d, byte [rdx+0x{a:x}]');_memory(g,'store','r8b',1,'rcx',a)
    _memory(g,'load','r8d',4,'rdx',b);_memory(g,'store','r8d',4,'rcx',b)
    for offset in (c,d):
        _memory(g,'load','rcx',8,'rdx',offset);_memory(g,'store','rcx',8,'r10',offset)
    _memory(g,'store','al',1,'rdx',a);_memory(g,'store','xmm0',8,'rdx',c)
    row=g.row();raw=bytes.fromhex(row['bytes']);parsed=decode_carrier_vector_byte_shift(raw,0,int(row['va'],16));f=parsed[0].get('vectorByteShiftOperation',{}) if parsed and parsed[1]==len(raw) else {}
    if (f.get('register'),f.get('vectorBits'),f.get('effectiveByteCount'),f.get('zeroFillsHighBits'))!=('xmm0',128,8,True):g.fail('exact-high-qword-shift',8,row)
    _memory(g,'store','xmm0',8,'rdx',d);_memory(g,'store','r9d',4,'rdx',b);g.take('ret');g.finish()

def validate_name_cache_migration_swap(programs,*,image_base,contract):
    c=contract;base=image_base;roles=c['functions'];required={'migration','swap','configSwap','capacity','hash','allocation','iteratorCreate','iteratorNext'}
    if set(programs)!=required or set(roles)!=required:raise ValueError(LABEL+'.function-membership')
    graphs={role:_complete(rr,base+roles[role]['entryRva']) for role,rr in programs.items()};l=c['layout'];p=c['projections']
    if (l['nodeBytes'],l['nodeHeader'],l['nodeNamespace'],l['nodeName'],l['nodeRecord'])!=(32,0,8,16,24):raise ValueError(LABEL+'.key-record-node-layout')
    for role,f in roles.items():
        if f['ownershipKind']=='closedNoCallProgram' and (graphs[role]['calls'] or graphs[role]['traps']):raise ValueError(LABEL+'.closed-program-call-or-trap:'+role)
    _config(programs['configSwap'],l)
    # Every leaf instruction is checked above, including partial-register and
    # vector writes. Neither R11 nor RBX is written or implicitly consumed.
    for row in programs['configSwap']:
        if _ALIASES.get((row.get('write') or {}).get('register')) in ('r11','rbx'):raise ValueError(LABEL+'.config-preserved-register')
    rr=programs['swap'];block=_part(rr,base,p['swapPrefix']);g=_Grammar(block,label=LABEL+'.swapPrefix')
    g.take('push rbx','sub rsp, 0x20');_memory(g,'load','xmm0',16,'rdx',0);g.take('mov rbx, rcx','mov r11, rdx')
    _memory(g,'load','xmm2',16,'rcx',0);_memory(g,'load','xmm3',16,'rcx',16);_memory(g,'store','xmm0',16,'rcx',0)
    _memory(g,'load','xmm1',16,'rdx',16);_memory(g,'store','xmm1',16,'rcx',16);g.take(f'add rcx, 0x{l["configBase"]:x}')
    _memory(g,'store','xmm2',16,'rdx',0);_memory(g,'store','xmm3',16,'rdx',16);g.take(f'add rdx, 0x{l["configBase"]:x}');call=g.call(base+roles['configSwap']['entryRva']);g.finish()
    _closed_interior(rr,graphs['swap']['edges'],base,{'window':p['swapPrefix']})
    block=_part(rr,base,p['swapFields']);g=_Grammar(block,label=LABEL+'.swapFields')
    for offset in l['swapQwords']:
        _memory(g,'load','rax',8,'r11',offset);_memory(g,'load','rcx',8,'rbx',offset);_memory(g,'store','rax',8,'rbx',offset);_memory(g,'store','rcx',8,'r11',offset)
    _memory(g,'load','ecx',4,'rbx',l['swapMarker']);_memory(g,'load','xmm1',16,'rbx',l['swapStrings']);_memory(g,'load','rdx',8,'rbx',l['swapAuxiliary'])
    _memory(g,'load','eax',4,'r11',l['swapMarker']);_memory(g,'store','eax',4,'rbx',l['swapMarker']);_memory(g,'load','xmm0',16,'r11',l['swapStrings']);_memory(g,'store','xmm0',16,'rbx',l['swapStrings'])
    _memory(g,'load','rax',8,'r11',l['swapAuxiliary']);_memory(g,'store','rax',8,'rbx',l['swapAuxiliary']);_memory(g,'store','xmm1',16,'r11',l['swapStrings']);_memory(g,'store','ecx',4,'r11',l['swapMarker']);_memory(g,'store','rdx',8,'r11',l['swapAuxiliary']);g.take('xorps xmm1, xmm1')
    _memory(g,'load','rax',8,'r11',l['cacheNodes']);_memory(g,'load','rcx',8,'rbx',l['cacheNodes']);_memory(g,'store','rax',8,'rbx',l['cacheNodes']);_memory(g,'store','rcx',8,'r11',l['cacheNodes']);g.finish()
    _closed_interior(rr,graphs['swap']['edges'],base,{'window':p['swapFields']})
    # The leaf is the only CALL; later stores update threshold/config fields,
    # never the exchanged metadata/node pointers. Pointer origins persist to
    # those stores, independently of ordinary ABI's volatile R11 allowance.
    if graphs['swap']['calls']!=[{'siteVa':int(call['va'],16),'kind':'call','target':base+roles['configSwap']['entryRva']}]:raise ValueError(LABEL+'.swap-only-proved-child')
    prefix_ats={int(r['va'],16) for r in _part(rr,base,p['swapPrefix'])};end=base+p['swapFields']['endRva']
    for row in rr:
        at=int(row['va'],16);head,_,rest=row['text'].partition(' ');dest=_ALIASES.get(rest.split(',')[0])
        if at not in prefix_ats and dest in ('rbx','r11') and head not in ('cmp','test','push','pop'):raise ValueError(LABEL+'.swap-pointer-clobber')
    for store in graphs['swap']['stores']:
        if store['siteVa']<end:continue
        f=store['facts'];a=f.get('address',f.get('destinationAddress',{}));n=f.get('memoryBytes',f.get('memoryWriteBytes',0))
        if a.get('base') not in ('rbx','r11') or a.get('index') is not None or not n or a.get('displacement',0)+n>32:raise ValueError(LABEL+'.later-store-overwrites-exchanged-fields')
    block=_part(programs['migration'],base,p['migrationCopy']);g=_Grammar(block,label=LABEL+'.migrationCopy')
    _memory(g,'load','eax',4,'rdi',l['nodeHeader']);g.take('lea rcx, [rsp+0x30]','shl r9, 0x5',f'add r9, qword [rsi+0x{l["cacheNodes"]:x}]')
    _memory(g,'store','eax',4,'r9',l['nodeHeader']);_memory(g,'load','xmm0',16,'rdi',l['nodeNamespace']);_memory(g,'store','xmm0',16,'r9',l['nodeNamespace']);_memory(g,'load','rax',8,'rdi',l['nodeRecord']);g.take(f'add rdi, 0x{l["nodeBytes"]:x}');_memory(g,'store','rax',8,'r9',l['nodeRecord']);g.finish()
    _closed_interior(programs['migration'],graphs['migration']['edges'],base,{'window':p['migrationCopy']})
    block=_part(programs['iteratorCreate'],base,p['iteratorCreatePrefix']);g=_Grammar(block,label=LABEL+'.iteratorCreate')
    _memory(g,'store','rbx',8,'rsp',8);g.take('push rdi','sub rsp, 0x20');_memory(g,'store','rdx',8,'rcx',l['iteratorCache']);g.take('mov rdi, r9');_memory(g,'store','r8',8,'rcx',l['iteratorCursor']);g.take('mov rbx, rdx');_memory(g,'store','r9',8,'rcx',l['iteratorEnd']);g.take('mov r11, rcx','cmp r8, r9');g.finish()
    for role,site in c['iteratorStepSites'].items():
        row=next(r for r in programs[role] if int(r['va'],16)==base+site);raw=bytes.fromhex(row['bytes']);d=decode_initialization_memory_update(raw,0,int(row['va'],16));f=d[0]['initializationMemoryUpdateOperation'] if d and d[1]==len(raw) else {};a=f.get('destinationAddress',{})
        if (f.get('operation'),f.get('bits'),f.get('signedImmediate'),a.get('base'),a.get('index'),a.get('displacement'))!=('add',64,32,'r11',None,l['iteratorCursor']):raise ValueError(LABEL+'.iterator-node-step')
    return {'status':'migration-swap-controls-and-selected-field-preservation-proved','codeInstructions':sum(len(rr) for rr in programs.values()),'controls':{role:{k:g[k] for k in ('instructions','calls','stores','returns','traps','normalFramesProved')} for role,g in graphs.items()},
        'closedConfigLeafPreservesR11AndRbxProved':True,'selectedConfigByteDwordAndTwoQwordsExchangedProved':True,'swapPassesBothConfigSubobjectsToActualLeafProved':True,'cacheMetadataAndNodePointersExchangedAndNotLaterOverwrittenProved':True,
        'selectedMigrationPreservesNodeHeaderStringsAndRecordProved':True,'selectedMigrationAdvancesSourceCursorByNodeStrideProved':True,'iteratorCacheCursorEndOriginsAnd32ByteScanStepProved':True,
        'allOccupiedNodesEnumeratedAndMigratedProved':False,'allocationAndFreeMarkerEffectsProved':False,'iteratorCustomPredicatePreservesR11Proved':False,'duplicateKeyRecordHistoryProved':False,'hashCapacityOrProbeTerminationProved':False,
        'lookupReturnedSystemInt32ClassProved':False,'primitiveClassCellNonNullProved':False,'concreteDamageTypeSharingSelected':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
