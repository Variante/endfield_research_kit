"""Complete enum projection and named native API-entry programs.

Named exports bind field consumers. Separate class resolutions remain fresh;
on-disk type.data indexes are not substituted for live metadata-record pointers.
"""
from __future__ import annotations
from collections import deque
from .enum_underlying_instructions import decode_memory_immediate_test
from .initializer_control import control_transfer,memory_effect
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory,_global
from .record_index_geometry import prove_record_index_geometry

LABEL='enumUnderlyingControl'

def _graph(rows,base,f,tails):
    by_at={int(r['va'],16):r for r in rows}
    if len(by_at)!=len(rows) or base+f['entryRva'] not in by_at:raise ValueError(LABEL+'.entry-or-duplicate')
    edges={};calls=[];returns=[];tail_sites=[]
    for at,row in by_at.items():
        flow=control_transfer(row);kind=flow['kind'];dest=set()
        if kind in ('next','call','conditional'):dest.add(at+len(bytes.fromhex(row['bytes'])))
        if kind in ('jump','conditional'):
            t=flow['target']
            if kind=='jump' and t in tails:tail_sites.append({'siteRva':at-base,'targetRva':t-base})
            else:dest.add(t)
        if kind=='call':calls.append({'siteRva':at-base,'targetRva':flow['target']-base})
        elif kind=='return':returns.append(at-base)
        elif kind not in ('next','jump','conditional'):raise ValueError(LABEL+'.unreviewed-control')
        if not dest<=by_at.keys():raise ValueError(LABEL+'.local-boundary')
        if memory_effect(row) is not None:raise ValueError(LABEL+'.unexpected-explicit-memory-write')
        edges[at]=dest
    seen=set();pending=[base+f['entryRva']]
    while pending:
        at=pending.pop()
        if at not in seen:seen.add(at);pending.extend(edges[at]-seen)
    if seen!=by_at.keys():raise ValueError(LABEL+'.unreachable-entry-code')
    states={base+f['entryRva']:0};pending=deque(states)
    while pending:
        at=pending.popleft();r=by_at[at];sp=states[at];text=r['text'];kind=control_transfer(r)['kind']
        if text.startswith('push '):sp-=8
        elif text.startswith('pop '):sp+=8
        elif text.startswith(('sub rsp, 0x','add rsp, 0x')):
            n=int(text.split(', ')[1],16);sp+=n if text.startswith('add') else -n
        elif text.split(',')[0].endswith((' rsp',' esp',' sp',' spl')) and not text.startswith(('cmp ','test ')):
            raise ValueError(LABEL+'.unreviewed-stack-write')
        if kind=='call' and ((8+sp)%16 or -sp<32):raise ValueError(LABEL+'.call-frame')
        if kind=='return' or any(s['siteRva']==at-base for s in tail_sites):
            if sp!=0:raise ValueError(LABEL+'.exit-frame')
        for target in edges[at]:
            if target in states and states[target]!=sp:raise ValueError(LABEL+'.frame-join')
            if target not in states:states[target]=sp;pending.append(target)
    return {'instructions':len(rows),'directCalls':calls,'tailTransfers':tail_sites,'returns':returns,
        'explicitMemoryWrites':0,'normalExitStackRestored':True,'exceptionOwnedExtentClaimed':f['ownershipKind']=='exceptionFamily'}

def _test(g,register,layout):
    row=g.row();raw=bytes.fromhex(row['bytes']);r=decode_memory_immediate_test(raw,0,int(row['va'],16))
    fact=r[0]['memoryImmediateTestOperation'] if r and r[1]==len(raw) else {};a=fact.get('sourceAddress',{})
    if (fact.get('bits'),fact.get('effectiveImmediate'),fact.get('memoryWriteBytes'),a.get('base'),a.get('index'),a.get('displacement'),a.get('ripRelative'))!=(32,layout['typeFlagMask'],0,register,None,layout['typeFlags'],False):
        g.fail('type-flag-test','complete DWORD pure TEST with selected mask',row)

def validate_enum_underlying(programs,*,image_base,contract,metadata_records):
    c=contract;base=image_base;l=c['layout'];functions=c['functions']
    if set(programs)!=set(functions) or set(functions)!={'projection','enumBase','isEnum','getType','getElement','typeWrapper','descriptorWrapper','recordToClass'}:
        raise ValueError(LABEL+'.function-membership')
    roles={r:base+f['entryRva'] for r,f in functions.items()}
    tails=set(roles.values())|{base+c['classResolverRva']}
    controls={role:_graph(rows,base,functions[role],tails) for role,rows in programs.items()}
    g=_Grammar(programs['projection'],label=LABEL+'.projection')
    g.take('push rbx',f'sub rsp, 0x{l["frameBytes"]:x}',f'cmp byte [rcx+0x{l["kind"]:x}], 0x{c["kinds"]["enumRecord"]:x}','mov rbx, rcx')
    g.branch('je','enumRecord');g.mark('checkGeneric')
    g.take(f'cmp byte [rbx+0x{l["kind"]:x}], 0x{c["kinds"]["genericInstance"]:x}')
    g.branch('je','generic');g.mark('original');g.take('mov rax, rbx');g.mark('restore')
    g.take(f'add rsp, 0x{l["frameBytes"]:x}','pop rbx','ret');g.mark('enumRecord')
    _test(g,'rcx',l);g.branch('jne','checkGeneric');g.call(roles['typeWrapper'])
    g.take(f'test byte [rax+0x{l["classFlags"]:x}], 0x{l["classEnumMask"]:x}');g.branch('je','checkGeneric')
    g.take('mov rcx, rbx');g.call(roles['typeWrapper'])
    g.take(f'cmp qword [rax+0x{l["elementClass"]:x}], rax');g.branch('je','zero')
    _memory(g,'load','rax',8,'rax',l['elementClass']);g.take(f'add rax, 0x{l["valueType"]:x}',f'add rsp, 0x{l["frameBytes"]:x}','pop rbx','ret')
    g.mark('generic');_memory(g,'load','rcx',8,'rbx',l['typeData']);g.call(roles['descriptorWrapper'])
    g.take('test rax, rax');g.branch('je','original')
    g.take(f'test byte [rax+0x{l["classFlags"]:x}], 0x{l["classEnumMask"]:x}');g.branch('je','original')
    _test(g,'rbx',l);g.branch('jne','original')
    g.take('mov rcx, rax',f'add rsp, 0x{l["frameBytes"]:x}','pop rbx')
    tail=g.branch('jmp')
    if tail['target']!=roles['enumBase']:raise ValueError(LABEL+'.named-enum-tail')
    g.mark('zero');g.take('xor eax, eax');g.branch('jmp','restore');g.finish()
    g=_Grammar(programs['enumBase'],label=LABEL+'.enumBase')
    g.take(f'cmp qword [rcx+0x{l["elementClass"]:x}], rcx');g.branch('je','zero')
    _memory(g,'load','rax',8,'rcx',l['elementClass']);g.take(f'add rax, 0x{l["valueType"]:x}','ret')
    g.mark('zero');g.take('xor eax, eax','ret');g.finish()
    g=_Grammar(programs['isEnum'],label=LABEL+'.isEnum')
    g.take(f'movzx eax, byte [rcx+0x{l["classFlags"]:x}]',f'shr al, 0x{l["classEnumShift"]:x}','and al, 0x1','ret');g.finish()
    if l['classEnumMask']!=1<<l['classEnumShift']:raise ValueError(LABEL+'.named-enum-bit')
    g=_Grammar(programs['getElement'],label=LABEL+'.getElement')
    _memory(g,'load','rax',8,'rcx',l['elementClass']);g.take('ret');g.finish()
    g=_Grammar(programs['getType'],label=LABEL+'.getType')
    g.take(f'lea rax, [rcx+0x{l["valueType"]:x}]','ret');g.finish()
    g=_Grammar(programs['descriptorWrapper'],label=LABEL+'.descriptor')
    _memory(g,'load','rcx',8,'rcx',l['descriptorType']);r=g.branch('jmp');g.finish()
    if r['target']!=roles['typeWrapper']:raise ValueError(LABEL+'.descriptor-target')
    g=_Grammar(programs['typeWrapper'],label=LABEL+'.type')
    g.take('test rcx, rcx');g.branch('je','zero');_memory(g,'load','rcx',8,'rcx',l['typeData'])
    r=g.branch('jmp');g.mark('return');g.take('ret');g.mark('zero');g.take('xor eax, eax');g.branch('jmp','return');g.finish()
    if r['target']!=roles['recordToClass']:raise ValueError(LABEL+'.type-data-target')
    p=c['recordProjection'];g=_Grammar(programs['recordToClass'],label=LABEL+'.recordToClass')
    _global(g,'rax',8,base+p['metadataHeaderRva'])
    g.take(f'movsxd rdx, dword [rax+0x{p["headerTypeDefinitionsOffset"]:x}]',f'mov rax, 0x{p["multiplier"]&((1<<64)-1):x}','sub rcx, rdx',
        f'sub rcx, qword [rip => {hex(base+p["metadataBaseRva"])}]','imul rcx','add rdx, rcx',
        f'sar rdx, 0x{p["shift"]:x}','mov rcx, rdx','shr rcx, 0x3f','add rcx, rdx')
    r=g.branch('jmp');g.finish()
    if r['target']!=base+c['classResolverRva']:raise ValueError(LABEL+'.record-resolver-tail')
    geometry=prove_record_index_geometry(multiplier=p['multiplier'],shift=p['shift'],record_bytes=p['recordBytes'],records=metadata_records)
    return {'status':'complete-enum-projection-and-named-api-entry-programs-proved',
        'controls':controls,'codeInstructions':sum(len(rows) for rows in programs.values()),
        'namedEnumFlagAndElementClassAndTypeAddressJoined':True,'recordToClassGeometry':geometry,
        'typeDataConsumedAsMetadataRecordPointer':True,'bareOnDiskDataIndexUsedAsLivePointer':False,
        'kind17ClassResolutionCalls':2,'secondClassResolutionResultAssumedSame':False,'firstEnumFlagProvesSecondClassEnum':False,
        'genericEnumClassTailJoinedToNamedEnumBaseType':True,'namedEnumBaseTypeSelfElementReturnsZero':True,
        'typeInputAndChildEffectsProvedReadonly':False,'concreteDamageTypeUnderlyingResultProved':False,
        'typeDataInitializationJoinProved':False,'concreteDamageTypeSharingSelected':False,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
