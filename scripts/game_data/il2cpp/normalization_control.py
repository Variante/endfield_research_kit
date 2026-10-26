"""Complete physical generic normalization control, including dynamic frames.

Kind bytes, class cells and opaque child returns stay anonymous. Fixed input
counts, valid disjoint storage and finite ordinary returns are conditions, not
observed runtime facts. The stack probe's volatile preservation is checked
from its complete body rather than inferred from Win64.
"""
from __future__ import annotations

from collections import deque

from .integer_addressing import decode_lea_address
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _address, _global, _memory
from .normalization_instructions import decode_gs_absolute_load, decode_word_register_and
from .relation_control import transfer


def allocation_size(count):
    if type(count) is not int or not 0 <= count < 1 << 32:
        raise ValueError('normalization.count-not-dword')
    size = count*8
    return (size+15)&~15


def _probe(rows, base, c):
    p=c['probeLayout']
    g=_Grammar(rows,label='normalization.probe')
    g.take(f'sub rsp, 0x{p["frameBytes"]:x}')
    _memory(g,'store','r10',8,'rsp',p['savedR10'])
    _memory(g,'store','r11',8,'rsp',p['savedR11'])
    g.take('xor r11, r11')
    _address(g,'r10','rsp',p['callerSpFromFrame'])
    g.take('sub r10, rax','cmovb r10, r11')
    row=g.row();raw=bytes.fromhex(row['bytes'])
    result=decode_gs_absolute_load(raw,0,int(row['va'],16))
    f=result[0]['segmentMemoryLoadOperation'] if result else {}
    a=f.get('sourceAddress',{})
    if result is None or result[1]!=len(raw) or (f.get('register'),f.get('registerBits'),
            a.get('segment'),a.get('segmentBaseRuntime'),a.get('displacement'))!=('r11',64,'gs',True,p['gsCellOffset']):
        g.fail('runtime-segment-load','complete current GS QWORD load',row)
    g.take('cmp r10, r11');g.branch('jae','restore')
    row=g.row();raw=bytes.fromhex(row['bytes'])
    result=decode_word_register_and(raw,0,int(row['va'],16))
    f=result[0]['wordRegisterLogicalOperation'] if result else {}
    if result is None or result[1]!=len(raw) or (f.get('register'),f.get('bits'),f.get('immediateWord'),
            f.get('preservesBits16Through63'))!=('r10w',16,p['pageMaskWord'],True):
        g.fail('partial-word-page-mask','WORD mask preserving upper 48 bits',row)
    g.mark('touchPage')
    _address(g,'r11','r11',-p['pageBytes'])
    g.take('mov byte [r11], 0x0','cmp r10, r11');g.branch('jne','touchPage')
    g.mark('restore')
    _memory(g,'load','r10',8,'rsp',p['savedR10'])
    _memory(g,'load','r11',8,'rsp',p['savedR11'])
    g.take(f'add rsp, 0x{p["frameBytes"]:x}','ret');g.finish()
    return {'preservedRegisters':['rax','rcx','rdx','r8'],'preservationBits':64,
            'preservationRequiresFiniteNormalReturn':True,'opaqueChildCalls':0,
            'gsBaseOrCellValueObserved':False,'pageStoresAreConditionalStaticEffects':True,
            'allCallsIntoProbeEntryRequired':True}


def _allocation(g, base, c, key):
    f=c['functions'][key];a=c['allocation'][key]
    _memory(g,'load','eax',4,a['countRegister'],c['layout']['count'])
    g.take('shl rax, 0x3')
    _address(g,a['sizeRegister'],'rax',15)
    g.take(f'cmp {a["sizeRegister"]}, rax');g.branch('ja','roundAllocation')
    g.take(f'mov {a["sizeRegister"]}, {hex(c["allocationOverflowFallback"])}')
    g.mark('roundAllocation')
    g.take(f'and {a["sizeRegister"]}, -0x10',f'mov rax, {a["sizeRegister"]}')
    call=g.call(base+c['functions']['probe']['entryRva'])
    row=g.take(f'sub rsp, {a["sizeRegister"]}')
    if int(row['va'],16)-base!=a['allocationRva'] or int(call['va'],16)-base!=a['probeCallRva']:
        g.fail('allocation-sites',a,row)
    return {'countReadBytes':4,'pointerStrideBytes':8,'sizeAlignmentBytes':16,
            'sizeRegisterPreservedByCompleteProbe':a['sizeRegister'],
            'sizeFormula':'(zero-extended count * 8 + 15) & ~15',
            'overflowFallbackUnreachableForDwordCount':True,
            'maxSizeBytes':allocation_size((1<<32)-1),'allocationSuccessObserved':False}


def _first(rows, base, c):
    l=c['layout'];calls=c['calls'];k=c['kinds'];f=c['frames']['first']
    g=_Grammar(rows,label='normalization.first')
    g.take('push rbp','push r14','push r15',f'sub rsp, 0x{f["fixedLocalBytes"]:x}')
    _address(g,'rbp','rsp',f['bpFromFixedSp'])
    _memory(g,'store','rbx',8,'rbp',f['savedRbx'])
    _memory(g,'store','rsi',8,'rbp',f['savedRsi'])
    g.take('mov rsi, rcx')
    _memory(g,'store','rdi',8,'rbp',f['savedRdi'])
    g.take('test rcx, rcx');g.branch('jne','hasInput')
    g.take('xor eax, eax');g.branch('jmp','restore')
    g.mark('hasInput');allocation=_allocation(g,base,c,'first')
    g.take('xor edi, edi');_address(g,'r14','rsp',f['bufferFromSp'])
    g.take(f'cmp dword [rsi], edi');g.branch('jbe','internArray')
    _address(g,'r15',None,None,absolute=base)
    g.take('nop');g.mark('loop')
    _memory(g,'load','rax',8,'rsi',l['arguments'])
    g.take('lea rcx, [rdi*8]','mov rcx, [rcx+rax*1]','test rcx, rcx')
    g.branch('je','originalType')
    for kind in k['referenceCollapse']:
        g.take(f'cmp byte [rcx+0x{l["kind"]:x}], {hex(kind)}');g.branch('je','referenceType')
    g.take(f'cmp byte [rcx+0x{l["kind"]:x}], {hex(k["generic"])}');g.branch('jne','originalType')
    _memory(g,'load','rcx',8,'rcx',l['typeData'])
    g.call(base+calls['genericDescriptor'])
    _memory(g,'load','ecx',4,'rax',l['descriptorFlags'])
    g.take('shr ecx, 0x1f','test cl, cl');g.branch('je','referenceType')
    g.mark('originalType')
    _memory(g,'load','rbx',8,'rsi',l['arguments'])
    g.take('lea rax, [rdi*8]','mov rbx, [rax+rbx*1]')
    _global(g,'rax',8,base+c['globals']['configurationCellRva'])
    g.take('cmp byte [rax], 0x0');g.branch('je','recursiveKind')
    g.take(f'cmp byte [rbx+0x{l["kind"]:x}], {hex(k["value"])}');g.branch('jne','genericEnumCheck')
    _memory(g,'load','rcx',8,'rbx',l['typeData'])
    g.call(base+calls['classFromTypeData'])
    g.take(f'test byte [rax+0x{l["classFlags"]:x}], {hex(l["enumMask"])}')
    g.branch('jne','underlyingKind')
    g.mark('genericEnumCheck')
    g.take(f'cmp byte [rbx+0x{l["kind"]:x}], {hex(k["generic"])}');g.branch('jne','storeType')
    _memory(g,'load','rcx',8,'rbx',l['typeData'])
    g.call(base+calls['genericDescriptor'])
    _address(g,'rcx','rax',l['classTypePointer'])
    g.call(base+calls['genericEnumPredicate'])
    g.take('test al, al');g.branch('je','recursiveKind')
    g.mark('underlyingKind')
    g.take('mov rcx, rbx');g.call(base+calls['underlyingType'])
    table=c['table']
    g.take(f'movsx ecx, byte [rax+0x{l["kind"]:x}]',f'add ecx, {hex(-table["kindBias"])}',
           f'cmp ecx, {hex(len(table["targetsRva"])-1)}')
    guard=g.branch('ja','recursiveKind')
    jump=g.take('movsxd rax, ecx',f'mov ecx, [r15+rax*4+0x{table["startRva"]:x}]','add rcx, r15','jmp rcx')
    if (int(guard['va'],16)-base,int(rows[g.cursor-3]['va'],16)-base,int(jump['va'],16)-base)!=(
            table['guardRva'],table['loadRva'],table['jumpRva']):
        g.fail('table-guard-site',table['guardRva'],guard)
    for n,case in enumerate(table['casesInCodeOrder']):
        g.mark('case'+str(n))
        if int(rows[g.cursor]['va'],16)-base!=case['entryRva']:
            g.fail('case-entry',case['entryRva'],rows[g.cursor])
        _global(g,'rbx',8,base+case['cellRva'])
        if n+1<len(table['casesInCodeOrder']):g.branch('jmp','classTypeAddress')
    g.mark('classTypeAddress');g.take(f'add rbx, 0x{l["classTypePointer"]:x}')
    g.mark('recursiveKind')
    g.take(f'cmp byte [rbx+0x{l["kind"]:x}], {hex(k["generic"])}');g.branch('jne','storeType')
    _memory(g,'load','rcx',8,'rbx',l['typeData'])
    _memory(g,'load','rcx',8,'rcx',l['genericArguments'])
    g.call(base+c['functions']['first']['entryRva'])
    _memory(g,'load','rcx',8,'rbx',l['typeData'])
    g.take('mov rdx, rax');_memory(g,'load','rcx',8,'rcx',l['genericDefinition'])
    g.call(base+calls['composeGeneric'])
    g.take('mov rcx, rax');_memory(g,'load','rax',8,'rax',l['composedClass'])
    g.take('test rax, rax');g.branch('jne','haveClass')
    g.take('mov dl, 0x1');g.call(base+calls['resolveComposedClass'])
    g.mark('haveClass');_address(g,'rbx','rax',l['classTypePointer'])
    g.branch('jmp','storeType')
    g.mark('referenceType');_global(g,'rbx',8,base+c['globals']['referenceCellRva'])
    g.take(f'add rbx, 0x{l["classTypePointer"]:x}')
    g.mark('storeType')
    g.take('lea rax, [rdi*8]','inc edi','mov [r14+rax*1], rbx','cmp edi, dword [rsi]')
    g.branch('jb','loop')
    g.mark('internArray');_memory(g,'load','edx',4,'rsi',l['count'])
    g.take('mov rcx, r14');g.call(base+calls['internArguments'])
    g.mark('restore')
    for register,key in (('rbx','savedRbx'),('rsi','savedRsi'),('rdi','savedRdi')):
        _memory(g,'load',register,8,'rbp',f[key])
    g.take('mov rsp, rbp','pop r15','pop r14','pop rbp','ret');g.finish()
    return {'allocation':allocation,'configurationUsesFirstByteOfFreshPointer':True,
            'configurationZeroSkipsUnderlyingKindProjection':True,
            'referenceKindInputs':k['referenceCollapse'],
            'genericDescriptorHighBitZeroAlsoUsesReferenceCell':True,
            'underlyingTypeHelperReturnsOpaqueTypePointer':True,
            'guardedUnderlyingKindRange':[table['kindBias'],table['kindBias']+len(table['targetsRva'])-1],
            'recursiveCallTargetsThisCompleteNormalizer':True,
            'opaqueGenericCompositionReceivesOriginalDefinitionAndNormalizedChildren':True,
            'loopWritesOneQwordPerStableInputOrdinal':True,
            'concreteDamageTypeUnderlyingClassOrConfigurationValueProved':False}


def _second(rows, base, c):
    l=c['layout'];f=c['frames']['second'];g=_Grammar(rows,label='normalization.second')
    g.take('push rbp',f'sub rsp, 0x{f["fixedLocalBytes"]:x}')
    _address(g,'rbp','rsp',f['bpFromFixedSp'])
    for register,key in (('rbx','savedRbx'),('rsi','savedRsi'),('rdi','savedRdi')):
        _memory(g,'store',register,8,'rbp',f[key])
    g.take('mov rdi, rdx');_memory(g,'store','r14',8,'rbp',f['savedR14'])
    g.take('mov r14, rcx','test rdx, rdx');g.branch('je','nullReturn')
    row=g.row();fact=row.get('memoryImmediateComparisonOperation',{})
    if (fact.get('bits'),fact.get('immediateValue'),fact.get('sourceAddress',{}).get('absoluteAddress'))!=(
            64,0,base+c['globals']['secondGateRva']):
        g.fail('fresh-second-gate','current QWORD global zero comparison',row)
    g.branch('je','nullReturn');allocation=_allocation(g,base,c,'second')
    g.take('xor ebx, ebx');_address(g,'rsi','rsp',f['bufferFromSp'])
    g.take('cmp dword [rdx], ebx');g.branch('jbe','internArray')
    g.take('nop');g.mark('loop')
    _memory(g,'load','ecx',4,'r14',l['parameterStart'])
    g.take('add ecx, ebx','cmp ecx, -0x1');g.branch('jne','metadataPointer')
    g.take('xor ecx, ecx');g.branch('jmp','classify')
    g.mark('metadataPointer');_global(g,'rax',8,base+c['globals']['metadataHeaderCellRva'])
    g.take('movsxd rcx, ecx','shl rcx, 0x4',f'movsxd rdx, dword [rax+0x{l["parameterSection"]:x}]')
    g.take(f'add rdx, qword [rip => 0x{base+c["globals"]["metadataBaseCellRva"]:x}]','add rcx, rdx')
    g.mark('classify');g.call(base+c['calls']['classifyParameter'])
    g.take('sub eax, 0x1');g.branch('je','categoryOne')
    g.take('cmp eax, 0x1');g.branch('je','categoryTwo')
    _global(g,'rcx',8,base+c['globals']['secondCategoryCellsRva'][2]);g.branch('jmp','writeType')
    g.mark('categoryTwo');_global(g,'rcx',8,base+c['globals']['secondCategoryCellsRva'][1])
    g.branch('jmp','writeType')
    g.mark('categoryOne');_global(g,'rcx',8,base+c['globals']['secondCategoryCellsRva'][0])
    g.mark('writeType');g.take(f'add rcx, 0x{l["classTypePointer"]:x}','mov [rsi+rbx*8], rcx','inc ebx','cmp ebx, dword [rdi]')
    g.branch('jb','loop');g.mark('internArray')
    _memory(g,'load','edx',4,'rdi',l['count']);g.take('mov rcx, rsi')
    g.call(base+c['calls']['internArguments']);g.branch('jmp','restore')
    g.mark('nullReturn');g.take('xor eax, eax');g.mark('restore')
    for register,key in (('rbx','savedRbx'),('rsi','savedRsi'),('rdi','savedRdi'),('r14','savedR14')):
        _memory(g,'load',register,8,'rbp',f[key])
    g.take('mov rsp, rbp','pop rbp','ret');g.finish()
    return {'allocation':allocation,'nullInputOrZeroFreshGateReturnsZero':True,
            'inputInstantiationArgumentArrayRead':False,'inputInstantiationCountRead':True,
            'descriptorIndexIsDwordStartPlusOrdinalModulo2Pow32':True,
            'onlyMinusOneSentinelHasLocalCheck':True,'nonSentinelMetadataIndexBoundsChecked':False,
            'metadataIndexThenSignExtendedAndScaledBy16':True,
            'opaqueClassifierDwordCodesOneTwoAndOtherSelectThreeFreshCells':True,
            'loopWritesOneQwordPerStableInputOrdinal':True,'concreteConstraintClassesProved':False}


def _graph(rows, entry, table=None, base=0):
    by_at={int(r['va'],16):r for r in rows};edges={};calls=[]
    if len(by_at)!=len(rows) or entry not in by_at:raise ValueError('normalization.graph-entry-or-duplicate')
    for at,row in by_at.items():
        raw=bytes.fromhex(row['bytes']);end=at+len(raw)
        if table is not None and at==base+table['jumpRva']:
            if raw!=b'\xff\xe1':raise ValueError('normalization.table-transfer')
            targets=[base+rva for rva in table['targetsRva']]
        else:
            t=transfer(row);kind=t['kind'];targets=[]
            if kind in ('next','conditional','call'):targets.append(end)
            if kind in ('jump','conditional'):targets.append(t['target'])
            if kind=='call':calls.append((at,t['target']))
            elif kind not in ('next','jump','conditional','return'):raise ValueError('normalization.unsupported-control')
        if any(target not in by_at for target in targets):raise ValueError('normalization.local-boundary')
        edges[at]=set(targets)
    reached=set();pending=[entry]
    while pending:
        at=pending.pop()
        if at in reached:continue
        reached.add(at);pending.extend(edges[at]-reached)
    if reached!=set(by_at):raise ValueError('normalization.unreachable-code')
    if table is not None:
        guard=base+table['guardRva'];load=base+table['loadRva']
        # Removing the bounds guard must make the target load unreachable.
        seen=set();pending=[entry]
        while pending:
            at=pending.pop()
            if at==guard or at in seen:continue
            seen.add(at);pending.extend(edges[at]-seen)
        if load in seen:raise ValueError('normalization.table-guard-bypass')
        if any(target in by_at and target!=entry for _,target in calls):raise ValueError('normalization.call-into-interior')
    return edges,calls


def _frames(rows, edges, entry, allocation=None):
    """Carry both null and allocated states until RBP restores their common SP."""
    by_at={int(r['va'],16):r for r in rows};states={entry:{(0,0,None)}};pending=deque([entry])
    while pending:
        at=pending.popleft();row=by_at[at];head,_,rest=row['text'].partition(' ')
        destination=rest.split(',')[0];new_states=set()
        for sp,coefficient,bp in states[at]:
            if head=='push':sp-=8
            elif head=='pop':
                if rest=='rsp':raise ValueError('normalization.pop-rsp')
                sp+=8
                if rest=='rbp':bp=None
            elif allocation is not None and at==allocation['allocationVa']:
                coefficient-=1
            elif destination=='rsp':
                if head in ('add','sub') and rest.startswith('rsp, 0x'):
                    amount=int(rest.split(', ')[1],16);sp+=amount if head=='add' else -amount
                elif rest=='rsp, rbp' and head=='mov' and bp is not None:sp,coefficient=bp,0
                else:raise ValueError('normalization.unchecked-dynamic-sp')
            elif destination=='rbp':
                raw=bytes.fromhex(row['bytes']);result=decode_lea_address(raw,0,at) if head=='lea' else None
                f=result[0]['addressOperation'] if result else {}
                if result is None or result[1]!=len(raw) or coefficient or (f.get('base'),f.get('index'),f.get('destinationBits'))!=('rsp',None,64):
                    raise ValueError('normalization.unchecked-bp-write')
                bp=sp+f['displacement']
            elif head not in ('cmp','test') and destination in ('esp','sp','spl','ebp','bp','bpl'):
                raise ValueError('normalization.partial-frame-register-write')
            if head=='call' and ((8+sp)%16 or -sp<32 or coefficient>0):raise ValueError('normalization.call-frame')
            if head=='ret' and (sp or coefficient):raise ValueError('normalization.return-frame')
            new_states.add((sp,coefficient,bp))
        for target in edges[at]:
            previous=states.get(target,set());merged=previous|new_states
            if len(merged)>3:raise ValueError('normalization.unbounded-frame-states')
            if merged!=previous:states[target]=merged;pending.append(target)
    return {'allNormalReturnsRestoreEntryRsp':True,'dynamicAllocationSizeAligned16':allocation is not None,
            'normalCallsHaveAlignedHomeSpace':True,'nullAndAllocatedStatesJoinThroughRbpRestore':allocation is not None}


def validate_normalization(programs, *, image_base, contract):
    if set(programs)!={'first','second','probe'}:raise ValueError('normalization.program-set')
    c=contract;base=image_base
    probe=_probe(programs['probe'],base,c)
    first=_first(programs['first'],base,c)
    second=_second(programs['second'],base,c)
    controls={}
    for key,rows in programs.items():
        entry=base+c['functions'][key]['entryRva']
        edges,calls=_graph(rows,entry,c['table'] if key=='first' else None,base)
        allocation={'allocationVa':base+c['allocation'][key]['allocationRva']} if key!='probe' else None
        frames=_frames(rows,edges,entry,allocation)
        controls[key]={'instructions':len(rows),'allCodeInstructionsReachableInStaticGraph':True,
            'allLocalEdgesOnCodeInstructionBoundaries':True,'calls':calls,'frames':frames}
    return {'completeControls':controls,'stackProbe':probe,'firstNormalization':first,'secondNormalization':second,
            'completeCodeInstructions':sum(len(rows) for rows in programs.values()),
            'tableEntries':len(c['table']['targetsRva']),'tableGuardDominatesTargetLoad':True,
            'inputCountAndPointersMustRemainStable':True,'concreteGenericSharingSelected':False,
            'runtimeConfigurationOrRegistrationCellObserved':False,'runtimeExecutionKnown':False}
