"""Complete registration/initialization CFGs and conditional type-data fixup.

The initialized record pointer is a conditional result of the actual entry
program, not evidence that the client executed it or loaded the selected file.
"""
from __future__ import annotations
from collections import deque
from .integer_addressing import _address,_prefix,decode_lea_address
from .integer_source_operands import is_unknown_instruction
from .initializer_control import control_transfer,memory_effect,_register_copy,_ALIASES
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory,_global
from .relation_import_control import _memory as _absolute_memory
from .class_creation_control import _dominators
from .type_data_initialization_instructions import decode_initialization_memory_update

LABEL='typeDataInitializationControl'

def _flow(row,table_targets,no_return_calls):
    raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if at in no_return_calls:
        if len(raw)!=5 or raw[0]!=0xe8 or at+5+int.from_bytes(raw[1:],'little',signed=True)!=no_return_calls[at]:raise ValueError(LABEL+'.terminal-no-return-call')
        return {'kind':'conditionalNoReturnCall','target':no_return_calls[at]}
    if raw==b'\xff\xe2':
        if at not in table_targets:raise ValueError(LABEL+'.unproved-table-transfer')
        return {'kind':'table','targets':table_targets[at]}
    pos,rex=_prefix(raw,0)
    if pos+2<=len(raw) and raw[pos]==0xff and (raw[pos+1]>>3)&7==2:
        modrm=raw[pos+1];stop=pos+2
        if modrm>>6!=3:_,stop=_address(raw,stop,modrm,rex,0,'initialization-call')
        if stop!=len(raw) or rex&4:raise ValueError(LABEL+'.indirect-call-encoding')
        return {'kind':'opaqueCall'}
    return control_transfer(row)

def _complete(rows,entry,*,table_targets=None,no_return_calls=None):
    table_targets=table_targets or {};no_return_calls=no_return_calls or {};by={int(r['va'],16):r for r in rows};edges={};calls=[];stores=[];returns=[];traps=[]
    unknown=[{'va':r['va'],'bytes':r['bytes']} for r in rows if is_unknown_instruction(r)]
    if len(by)!=len(rows) or entry not in by or unknown:raise ValueError(LABEL+'.instruction-entry-or-unknown: entry='+hex(entry)+' rows='+str(len(rows))+' unique='+str(len(by))+' missingEntry='+str(entry not in by)+' unknown='+str(unknown[:4]))
    for at,row in by.items():
        f=_flow(row,table_targets,no_return_calls);kind=f['kind'];targets=set()
        if kind in ('next','call','opaqueCall','indirectCall','registerCall','conditional'):targets.add(at+len(bytes.fromhex(row['bytes'])))
        if kind in ('conditional','jump'):targets.add(f['target'])
        if kind=='table':targets.update(f['targets'])
        if kind in ('call','opaqueCall','indirectCall','registerCall','conditionalNoReturnCall'):
            if kind=='call' and f['target'] in by:raise ValueError(LABEL+'.call-into-owned-code')
            calls.append({'siteVa':at,**f})
        elif kind=='return':returns.append(at)
        elif kind=='trap':traps.append(at)
        elif kind not in ('next','conditional','jump','table'):raise ValueError(LABEL+'.control-kind')
        if not targets<=by.keys():raise ValueError(LABEL+'.local-boundary:'+hex(at))
        raw=bytes.fromhex(row['bytes']);parsed=decode_initialization_memory_update(raw,0,at)
        effect={'kind':'initializationMemoryUpdateOperation','facts':parsed[0]['initializationMemoryUpdateOperation']} if parsed and parsed[1]==len(raw) else memory_effect(row)
        if effect:stores.append({'siteVa':at,**effect})
        edges[at]=targets
    reached=set();pending=[entry]
    while pending:
        at=pending.pop()
        if at not in reached:reached.add(at);pending.extend(edges[at]-reached)
    if reached!=by.keys():raise ValueError(LABEL+'.unreachable-owned-code: entry='+hex(entry)+' expected='+str(len(by))+' reached='+str(len(reached))+' missing='+str([hex(v) for v in sorted(by.keys()-reached)[:8]]))
    states={entry:(0,None,None)};pending=deque(states);names=('rsp','rbp','r11')
    while pending:
        at=pending.popleft();row=by[at];state=dict(zip(names,states[at]));head,_,rest=row['text'].partition(' ')
        dest=rest.split(',')[0];parent=_ALIASES.get(dest);flow=_flow(row,table_targets,no_return_calls);kind=flow['kind'];raw=bytes.fromhex(row['bytes'])
        if head in ('push','pop'):
            if rest=='rsp':raise ValueError(LABEL+'.dynamic-stack')
            state['rsp']+=-8 if head=='push' else 8
            if head=='pop' and parent in names:state[parent]=None
        elif kind in ('call','opaqueCall','indirectCall','registerCall','conditionalNoReturnCall'):state['r11']=None
        elif parent in names and head not in ('cmp','test','bt'):
            if parent=='rsp' and head in ('add','sub') and rest.startswith('rsp, 0x'):
                amount=int(rest.split(', ')[1],16);state['rsp']+=amount if head=='add' else -amount
            else:
                copy=_register_copy(raw) if head=='mov' else None
                parsed=decode_lea_address(raw,0,at) if head=='lea' else None
                fact=parsed[0]['addressOperation'] if parsed and parsed[1]==len(raw) else {}
                if copy and copy[0] in names:state[parent]=state.get(copy[1])
                elif fact.get('destinationBits')==64 and fact.get('base') in names and fact.get('index') is None and not fact.get('ripRelative'):
                    origin=state[fact['base']];state[parent]=None if origin is None else origin+fact['displacement']
                else:state[parent]=None
        if state['rsp'] is None:raise ValueError(LABEL+'.unproved-stack')
        if kind in ('call','opaqueCall','indirectCall','registerCall','conditionalNoReturnCall') and ((8+state['rsp'])%16 or -state['rsp']<32):raise ValueError(LABEL+'.call-frame')
        if kind=='return' and state['rsp']!=0:raise ValueError(LABEL+'.return-frame')
        for target in edges[at]:
            value=tuple(state[n] for n in names);old=states.get(target)
            if old is not None:
                if old[0]!=value[0]:raise ValueError(LABEL+'.stack-join')
                value=tuple(a if a==b else None for a,b in zip(old,value))
            if old!=value:states[target]=value;pending.append(target)
    return {'instructions':len(rows),'edges':edges,'calls':calls,'stores':stores,'returns':returns,'traps':traps,
        'states':states,'normalFramesProved':True}

def _slice(rows,base,window):
    selected=[r for r in rows if base+window['startRva']<=int(r['va'],16)<base+window['endRva']]
    if not selected or int(selected[0]['va'],16)!=base+window['startRva'] or int(selected[-1]['va'],16)+len(bytes.fromhex(selected[-1]['bytes']))!=base+window['endRva']:raise ValueError(LABEL+'.projection-boundary')
    return selected

def _helper(rows,base,spec,globals):
    g=_Grammar(rows,label=LABEL+'.'+spec['role']);g.take('movsxd rdx, dword [rcx]','mov r8, rcx','cmp edx, -0x1')
    g.branch('jne','valid');g.take('mov qword [rcx], 0x0','ret');g.mark('valid')
    _global(g,'rax',8,base+globals['metadataHeader'])
    if spec['multiplyKind']=='imul':g.take(f'imul rdx, rdx, 0x{spec["recordBytes"]:x}')
    elif spec['multiplyKind']=='shift':
        if spec['recordBytes']!=1<<spec['shift']:raise ValueError(LABEL+'.alternate-record-stride')
        g.take(f'shl rdx, 0x{spec["shift"]:x}')
    else:raise ValueError(LABEL+'.record-multiply-kind')
    g.take(f'movsxd rcx, dword [rax+0x{spec["headerOffsetField"]:x}]',f'add rcx, qword [rip => {hex(base+globals["metadataBase"])}]','add rdx, rcx')
    _memory(g,'store','rdx',8,'r8',0);g.take('ret');g.finish()

def validate_type_data_initialization(programs,tables,*,image_base,contract,records):
    c=contract;base=image_base;roles=c['functions'];required={'publication','metadataEntry','metadataInitializer','typeLoop','recordFixup','alternateFixup','terminalHelper'}
    if set(programs)!=required or set(roles)!=required:raise ValueError(LABEL+'.function-membership')
    t=c['dispatch'];selector=tables['selector'];target_raw=tables['targets']
    if len(selector)!=t['maxKindIndex']+1 or len(target_raw)!=4*t['targetCount'] or selector!=bytes.fromhex(t['selectorHex']) or target_raw!=bytes.fromhex(t['targetsHex']):raise ValueError(LABEL+'.dispatch-data')
    destinations=[base+int.from_bytes(target_raw[i:i+4],'little',signed=True) for i in range(0,len(target_raw),4)]
    if destinations!=[base+r for r in t['targetRvas']] or not set(selector)<=set(range(len(destinations))):raise ValueError(LABEL+'.dispatch-targets')
    if set(selector)!=set(range(len(destinations))):raise ValueError(LABEL+'.unused-target')
    loop=programs['typeLoop'];g=_Grammar(loop,label=LABEL+'.loop');l=c['layout'];gl=c['globals']
    g.take('push rbx',f'sub rsp, 0x{l["loopFrameBytes"]:x}');_global(g,'r8',8,base+gl['metadataRegistration'])
    g.take('xor ebx, ebx',f'cmp dword [r8+0x{l["typesCount"]:x}], ebx');g.branch('jle','restore')
    _memory(g,'store','rsi',8,'rsp',l['savedRsi']);r=g.row();b=bytes.fromhex(r['bytes']);at=int(r['va'],16)
    if len(b)!=7 or b[:3]!=bytes.fromhex('488d35') or at+7+int.from_bytes(b[3:],'little',signed=True)!=base:raise ValueError(LABEL+'.image-base-origin')
    _memory(g,'store','rdi',8,'rsp',l['savedRdi']);g.take('mov edi, ebx','nop');g.mark('iteration')
    _memory(g,'load','rax',8,'r8',l['typesPointer']);g.take('mov rcx, [rdi+rax*1]',f'movsx eax, byte [rcx+0x{l["typeKind"]:x}]','dec eax',f'cmp eax, 0x{t["maxKindIndex"]:x}')
    g.branch('ja','increment');g.take('cdqe',f'movzx eax, byte [rsi+rax*1+0x{t["selectorRva"]:x}]',f'mov edx, [rsi+rax*4+0x{t["targetsRva"]:x}]','add rdx, rsi')
    jump=g.take('jmp rdx');jump_at=int(jump['va'],16)
    g.mark('record');g.call(base+roles['recordFixup']['entryRva']);g.branch('jmp','reload')
    g.mark('alternate');g.call(base+roles['alternateFixup']['entryRva']);g.mark('reload');_global(g,'r8',8,base+gl['metadataRegistration'])
    g.mark('increment');g.take('inc ebx',f'add rdi, 0x{l["typePointerStride"]:x}',f'cmp ebx, dword [r8+0x{l["typesCount"]:x}]');g.branch('jl','iteration')
    _memory(g,'load','rdi',8,'rsp',l['savedRdi']);_memory(g,'load','rsi',8,'rsp',l['savedRsi']);g.mark('restore');g.take(f'add rsp, 0x{l["loopFrameBytes"]:x}','pop rbx','ret');g.finish()
    if destinations!=[g.labels['record'],g.labels['alternate'],g.labels['increment']]:raise ValueError(LABEL+'.actual-dispatch-code-labels')
    if l['typePointerStride']!=8 or l['typeKind']!=10:raise ValueError(LABEL+'.type-table-layout')
    for role in ('recordFixup','alternateFixup'):_helper(programs[role],base,c['fixups'][role],gl)
    terminal=_complete(programs['terminalHelper'],base+roles['terminalHelper']['entryRva'])
    if terminal['returns'] or not terminal['traps']:raise ValueError(LABEL+'.terminal-helper-normal-return')
    nr=c['terminalCallProgram'];no_return={base+nr['callSiteRva']:base+roles['terminalHelper']['entryRva']}
    graphs={role:_complete(rows,base+roles[role]['entryRva'],table_targets={jump_at:set(destinations)} if role=='typeLoop' else None,
        no_return_calls=no_return if role=='metadataEntry' else None) for role,rows in programs.items()}
    # Both table loads and the indirect jump must be reached through the unsigned guard.
    loop_dom=_dominators(graphs['typeLoop']['edges'],base+roles['typeLoop']['entryRva']);guard=int(loop[16]['va'],16)
    for i in (17,18,19,20,21):
        if guard not in loop_dom[int(loop[i]['va'],16)]:raise ValueError(LABEL+'.dispatch-guard-dominance')
    publication=c['publicationProjection'];block=_slice(programs['publication'],base,publication['window']);g=_Grammar(block,label=LABEL+'.publication')
    for register,source,cell in (('rcx',c['staticRegistrations']['codeRva'],gl['codeRegistration']),('rax',c['staticRegistrations']['metadataRva'],gl['metadataRegistration'])):
        row=g.row();b=bytes.fromhex(row['bytes']);at=int(row['va'],16);prefix=bytes.fromhex('488d0d' if register=='rcx' else '488d05')
        if len(b)!=7 or b[:3]!=prefix or at+7+int.from_bytes(b[3:],'little',signed=True)!=base+source:raise ValueError(LABEL+'.static-registration-address')
        _absolute_memory(g,'store',register,8,absolute=base+cell)
    _absolute_memory(g,'store','rcx',8,absolute=base+gl['codeRegistrationAlias']);_absolute_memory(g,'store','rax',8,absolute=base+gl['metadataRegistrationAlias'])
    row=g.row();b=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(b)!=7 or b[:3]!=bytes.fromhex('488d05') or at+7+int.from_bytes(b[3:],'little',signed=True)!=base+c['staticRegistrations']['optionsRva']:raise ValueError(LABEL+'.options-address')
    _absolute_memory(g,'store','rax',8,absolute=base+gl['options']);call=g.call(base+roles['metadataEntry']['entryRva']);g.finish()
    store_at=int(block[3]['va'],16);call_at=int(call['va'],16)
    pub_dom=_dominators(graphs['publication']['edges'],base+roles['publication']['entryRva'])
    if store_at not in pub_dom[call_at]:raise ValueError(LABEL+'.registration-store-dominance')
    # Exclude all decoded explicit overlapping writes, not just scanner MOV candidates.
    overlaps=[]
    for s in graphs['publication']['stores']:
        facts=s['facts'];address=facts.get('address',facts.get('destinationAddress',{}));start=address.get('absoluteAddress');width=facts.get('memoryBytes',facts.get('memoryWriteBytes'))
        if address.get('ripRelative') and start is not None and width is not None and start<base+gl['metadataRegistration']+8 and base+gl['metadataRegistration']<start+width:overlaps.append(s['siteVa'])
    if overlaps!=[store_at]:raise ValueError(LABEL+'.registration-global-write-inventory')
    for role,key,target_role in (('metadataEntry','metadataInitializerCall','metadataInitializer'),('metadataInitializer','typeLoopCall','typeLoop')):
        site=base+c['actualCalls'][key];by={int(r['va'],16):r for r in programs[role]};g=_Grammar([by[site]],label=LABEL+'.'+key);g.call(base+roles[target_role]['entryRva']);g.finish()
    cases=[]
    for kind in range(256):
        signed=kind-256 if kind>=128 else kind;index=(signed-1)&0xffffffff
        cases.append(None if index>t['maxKindIndex'] else destinations[selector[index]]-base)
    if cases[c['selectedDamageType']['kindByte']]!=destinations[0]-base:raise ValueError(LABEL+'.damage-kind-dispatch')
    record=c['fixups']['recordFixup'];geometry=c['recordGeometry']
    if record['recordBytes']!=geometry['recordBytes'] or record['headerOffsetField']!=geometry['headerOffsetField'] or records<=0 or records-1>0x7fffffff:raise ValueError(LABEL+'.record-domain')
    return {'status':'complete-registration-and-type-data-initialization-programs-proved',
        'codeInstructions':sum(len(r) for r in programs.values()),'controls':{role:{k:g[k] for k in ('instructions','calls','stores','returns','traps','normalFramesProved')} for role,g in graphs.items()},
        'kindDispatch':cases,'completeDispatchGuardAndLoopChecked':True,'registrationStoreDominatesActualMetadataEntryCall':True,
        'selectedStaticRegistrationPublishedUnderNormalSelectedBlock':True,'actualMetadataInitializerAndTypeLoopCallsJoined':True,
        'recordFixupReadsSignedDwordAndWritesPointerQword':True,'minusOneIndexWritesNull':True,
        'negativeIndicesOtherThanMinusOneRejected':False,'typeLoopImplicitlyIdempotent':False,
        'validRecordIndexRange':[0,records-1],'typeDataIndexToRecordPointerJoinConditional':True,
        'actualTerminalHelperHasNoNormalReturn':True,'terminalNoReturnInferredFromImportName':False,
        'runtimeRegistrationOrLoadedMetadataIdentityObserved':False,'unknownChildAliasEffectsExcluded':False,
        'runtimeGlobalStabilityProved':False,'runtimeInitializationExecuted':False,'concreteDamageTypeClassOrSharingProved':False,
        'positiveStoredGrammarAdmitted':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}

