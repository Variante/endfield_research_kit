"""Enum flag/element writes, complete type-helper control and class-cell request flow."""
from __future__ import annotations
from collections import deque
from .class_creation_control import _dominators
from .initializer_control import _ALIASES,control_transfer,memory_effect
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory,_global
from .relation_import_control import _memory as _absolute_memory
from .type_data_initialization_control import _complete
from .integer_source_operands import is_unknown_instruction

LABEL='classEnumFieldsControl'

def enum_flag_update(previous,bitfield,generic_present):
    if type(previous)!=int or not 0<=previous<256 or type(bitfield)!=int or not 0<=bitfield<1<<32 or type(generic_present)!=bool:raise ValueError(LABEL+'.flag-domain')
    cl=((bitfield>>1)&255)<<2&255
    cl=((cl^previous)&4)^previous
    return ((16 if generic_present else 0)|(cl&0xef))&255

def _slice(rows,base,w):
    selected=[r for r in rows if base+w['startRva']<=int(r['va'],16)<base+w['endRva']]
    if not selected or int(selected[0]['va'],16)!=base+w['startRva'] or int(selected[-1]['va'],16)+len(bytes.fromhex(selected[-1]['bytes']))!=base+w['endRva']:raise ValueError(LABEL+'.projection-boundary')
    return selected

def _closed_projection(rows,edges):
    owned={int(r['va'],16) for r in rows};entry=int(rows[0]['va'],16)
    for at in owned-{entry}:
        if any(source not in owned and at in targets for source,targets in edges.items()):raise ValueError(LABEL+'.projection-interior-entry:'+hex(at))

def _no_register_write(rows,start,end,parent,*,calls_allowed):
    for r in rows[start:end]:
        text=r['text'];head,_,rest=text.partition(' ');destination=rest.split(',')[0]
        if head=='call':
            if not calls_allowed:raise ValueError(LABEL+'.origin-crosses-opaque-call')
        elif head not in ('cmp','test','push','nop') and _ALIASES.get(destination)==parent:
            raise ValueError(LABEL+'.register-origin-overwritten:'+r['va']+':'+text)
        if head in ('mul','imul') and ',' not in rest and parent in ('rax','rdx'):raise ValueError(LABEL+'.implicit-register-origin-overwrite')

def _helper_graph(rows,base,c,tables):
    f=c['functions']['classHelper'];spec=c['helperDispatch'];by={int(r['va'],16):r for r in rows}
    if len(by)!=len(rows) or any(is_unknown_instruction(r) for r in rows):raise ValueError(LABEL+'.helper-inventory')
    selectors=tables['primitiveSelectors'];first=tables['primitiveTargets'];second=tables['complexTargets']
    if (len(selectors),len(first),len(second))!=(255,80,64) or max(selectors)>=20:raise ValueError(LABEL+'.helper-table-domain')
    if any(tables[k].hex().upper()!=v['rawHex'] for k,v in spec['tables'].items()):raise ValueError(LABEL+'.helper-table-bytes')
    target_sets={base+spec['primitiveJumpRva']:{base+int.from_bytes(first[i:i+4],'little',signed=True) for i in range(0,80,4)},
        base+spec['complexJumpRva']:{base+int.from_bytes(second[i:i+4],'little',signed=True) for i in range(0,64,4)}}
    tails={base+n for n in spec['externalTailRvas']};entry=base+f['entryRva'];edges={};calls=[];tail_sites=[];returns=[]
    for at,r in by.items():
        raw=bytes.fromhex(r['bytes']);dest=set();kind='next'
        if raw in (b'\xff\xe1',b'\xff\xe0'):
            if at not in target_sets:raise ValueError(LABEL+'.helper-unproved-table')
            kind='table';dest=target_sets[at]
        else:
            flow=control_transfer(r);kind=flow['kind']
            if kind in ('next','call','conditional'):dest.add(at+len(raw))
            if kind in ('jump','conditional'):
                target=flow['target']
                if kind=='jump' and target in tails:tail_sites.append({'siteVa':at,'targetVa':target})
                else:dest.add(target)
            if kind=='call':
                if flow['target']!=entry:raise ValueError(LABEL+'.helper-unreviewed-child')
                calls.append(at)
            elif kind=='return':returns.append(at)
            elif kind not in ('next','jump','conditional'):raise ValueError(LABEL+'.helper-control-kind')
        if not dest<=by.keys():raise ValueError(LABEL+'.helper-local-boundary:'+hex(at))
        if memory_effect(r):raise ValueError(LABEL+'.helper-unexpected-explicit-store')
        edges[at]=dest
    states={entry:0};pending=deque(states)
    while pending:
        at=pending.popleft();r=by[at];sp=states[at];text=r['text']
        if text=='push rbx':sp-=8
        elif text=='pop rbx':sp+=8
        elif text.startswith(('sub rsp, 0x','add rsp, 0x')):
            amount=int(text.split(', ')[1],16);sp+=amount if text.startswith('add') else -amount
        elif _ALIASES.get(text.partition(' ')[2].split(',')[0])=='rsp' and not text.startswith(('test ','cmp ')):raise ValueError(LABEL+'.helper-dynamic-stack')
        if at in calls and ((8+sp)%16 or -sp<32):raise ValueError(LABEL+'.helper-call-frame')
        if at in returns or any(t['siteVa']==at for t in tail_sites):
            if sp!=0:raise ValueError(LABEL+'.helper-exit-frame')
        for target in edges[at]:
            if target in states and states[target]!=sp:raise ValueError(LABEL+'.helper-stack-join')
            if target not in states:states[target]=sp;pending.append(target)
    if states.keys()!=by.keys():raise ValueError(LABEL+'.helper-unreachable-code')
    return {'edges':edges,'instructions':len(rows),'recursiveCalls':len(calls),'externalTails':tail_sites,'returns':returns,'normalFramesProved':True}

def validate_class_enum_fields(programs,tables,*,image_base,contract):
    c=contract;base=image_base;l=c['layout'];roles=c['functions']
    if set(programs)!=set(roles) or set(roles)!={'constructor','classHelper','apiWrapper','publication'}:raise ValueError(LABEL+'.function-membership')
    ctor=programs['constructor'];graph=_complete(ctor,base+roles['constructor']['entryRva']);pub=_complete(programs['publication'],base+roles['publication']['entryRva'])
    helper=_helper_graph(programs['classHelper'],base,c,tables);by={int(r['va'],16):r for r in ctor};dom=_dominators(graph['edges'],base+roles['constructor']['entryRva'])
    origins=c['origins'];rdi=base+origins['recordPointerDefinedRva'];rbx=base+origins['allocatedClassSavedRva'];zero=base+origins['zeroEbpRva'];edx=base+origins['genericFlagConstantRva']
    prefix=_slice(ctor,base,c['recordPrefix']);g=_Grammar(prefix,label=LABEL+'.recordPrefix')
    _global(g,'rax',8,base+c['globals']['metadataHeader']);g.take('movsxd rsi, ecx');_global(g,'rcx',8,base+c['globals']['allocatorContext'])
    g.take(f'imul rdi, rsi, 0x{l["recordBytes"]:x}',f'movsxd rdx, dword [rax+0x{l["typeDefinitionsHeader"]:x}]',f'add rdx, qword [rip => {hex(base+c["globals"]["metadataBase"])}]')
    _global(g,'rax',8,base+c['globals']['metadataRegistration']);defined=g.take('add rdi, rdx');g.finish()
    if int(defined['va'],16)!=rdi or by[rbx]['text']!='mov rbx, rax' or by[zero]['text']!='xor ebp, ebp' or by[edx]['text']!='mov edx, 0x10':raise ValueError(LABEL+'.declared-register-origin')
    call=by[base+origins['allocatorCallRva']];g=_Grammar([call],label=LABEL+'.allocator');g.call(base+origins['allocatorEntryRva']);g.finish()
    flag_rows=_slice(ctor,base,c['flagWindow']);g=_Grammar(flag_rows,label=LABEL+'.enumFlag')
    g.take(f'mov ecx, [rdi+0x{l["recordBitfield"]:x}]',f'movzx eax, byte [rbx+0x{l["classFlags"]:x}]','shr ecx, 0x1','shl cl, 0x2','xor cl, al','and cl, 0x4','xor cl, al','mov eax, ebp',
        f'mov [rbx+0x{l["classFlags"]:x}], cl',f'cmp dword [rdi+0x{l["genericContainer"]:x}], -0x1','cmovne eax, edx','and cl, 0xef','or al, cl',f'mov [rbx+0x{l["classFlags"]:x}], al');g.finish()
    flag_at=int(flag_rows[0]['va'],16);flag_last=int(flag_rows[-1]['va'],16);indices={int(r['va'],16):i for i,r in enumerate(ctor)}
    for definition in (rdi,rbx,zero,edx):
        if definition not in dom[flag_at]:raise ValueError(LABEL+'.flag-origin-dominance')
    _no_register_write(ctor,indices[rdi]+1,indices[flag_last]+1,'rdi',calls_allowed=True)
    _no_register_write(ctor,indices[rbx]+1,indices[flag_last]+1,'rbx',calls_allowed=True)
    _no_register_write(ctor,indices[zero]+1,indices[int(flag_rows[7]['va'],16)]+1,'rbp',calls_allowed=True)
    _no_register_write(ctor,indices[edx]+1,indices[int(flag_rows[10]['va'],16)]+1,'rdx',calls_allowed=False)
    if int(call['va'],16) not in dom[rbx]:raise ValueError(LABEL+'.allocator-result-dominance')
    # No volatile RAX replacement is permitted between allocation return and its RBX save.
    _no_register_write(ctor,indices[int(call['va'],16)]+1,indices[rbx],'rax',calls_allowed=False)
    elements=_slice(ctor,base,c['elementWindow']);g=_Grammar(elements,label=LABEL+'.element')
    g.take(f'test byte [rbx+0x{l["classFlags"]:x}], 0x4');_memory(g,'store','rbx',8,'rbx',l['elementClass']);_memory(g,'store','rbx',8,'rbx',l['castClass']);g.branch('je','after')
    g.take(f'movsxd rax, dword [rdi+0x{l["elementIndex"]:x}]','cmp eax, -0x1');g.branch('je','call');g.take('mov rdx, rax');_global(g,'rax',8,base+c['globals']['metadataRegistration'])
    _memory(g,'load','rcx',8,'rax',l['registrationTypes']);g.take('mov rbp, [rcx+rdx*8]');g.mark('call');g.take('mov dl, 0x1','mov rcx, rbp');element_call=g.call(base+roles['classHelper']['entryRva'])
    _memory(g,'store','rax',8,'rbx',l['elementClass']);_memory(g,'store','rax',8,'rbx',l['castClass']);g.mark('after');g.finish()
    _closed_projection(flag_rows,graph['edges']);_closed_projection(elements,graph['edges'])
    element_at=int(elements[0]['va'],16)
    if flag_last not in dom[element_at]:raise ValueError(LABEL+'.flag-store-before-element-test')
    _no_register_write(ctor,indices[rdi]+1,indices[int(elements[-1]['va'],16)]+1,'rdi',calls_allowed=True)
    _no_register_write(ctor,indices[rbx]+1,indices[int(elements[-1]['va'],16)]+1,'rbx',calls_allowed=True)
    _no_register_write(ctor,indices[zero]+1,indices[int(elements[10]['va'],16)],'rbp',calls_allowed=True)
    # Exact writes through the saved class base: exclude wider overlaps as well.
    flag_stores=[]
    for s in graph['stores']:
        f=s['facts'];a=f.get('address',f.get('destinationAddress',{}));width=f.get('memoryBytes',f.get('memoryWriteBytes'));disp=a.get('displacement')
        if a.get('base')=='rbx' and a.get('index') is None and disp is not None and width is not None and disp<=l['classFlags']<disp+width:flag_stores.append(s['siteVa'])
    if flag_stores!=[int(flag_rows[i]['va'],16) for i in (8,13)]:raise ValueError(LABEL+'.explicit-class-flag-write-inventory')
    # Native helper guard/loads are checked before interpreting the selected primitive trace.
    hp=c['helperDispatch'];h=programs['classHelper'];g=_Grammar(h[:17],label=LABEL+'.helperPrefix')
    g.take('push rbx','sub rsp, 0x20',f'movsx eax, byte [rcx+0x{l["typeKind"]:x}]');r=g.row();b=bytes.fromhex(r['bytes']);at=int(r['va'],16)
    if b[:3]!=bytes.fromhex('4c8d05') or len(b)!=7 or at+7+int.from_bytes(b[3:],'little',signed=True)!=base:raise ValueError(LABEL+'.helper-image-base')
    g.take('mov rbx, rcx','cmp eax, 0xf');g.branch('jl','primitive');g.take('cmp eax, 0x16');g.branch('jl','fallback');g.mark('primitive');g.take('dec eax','cmp eax, 0xfe');g.branch('ja','fallback')
    g.take('cdqe',f'movzx eax, byte [r8+rax*1+0x{hp["tables"]["primitiveSelectors"]["startRva"]:x}]',f'mov ecx, [r8+rax*4+0x{hp["tables"]["primitiveTargets"]["startRva"]:x}]','add rcx, r8','jmp rcx')
    g.labels['fallback']=base+hp['fallbackRva'];g.finish()
    selectors=tables['primitiveSelectors'];first=tables['primitiveTargets'];target=base+int.from_bytes(first[selectors[7]*4:selectors[7]*4+4],'little',signed=True)
    helper_by={int(r['va'],16):r for r in h};g=_Grammar(_slice(h,base,hp['kindEightLoadWindow']),label=LABEL+'.int32Load');load=g.row();b=bytes.fromhex(load['bytes']);at=int(load['va'],16)
    if at!=target or len(b)!=7 or b[:3]!=bytes.fromhex('488b05') or at+7+int.from_bytes(b[3:],'little',signed=True)!=base+c['globals']['primitiveInt32']:raise ValueError(LABEL+'.kind-eight-cell')
    jump=g.branch('jmp');g.finish()
    if jump['target']!=base+hp['primitiveTestRva']:raise ValueError(LABEL+'.primitive-test-target')
    g=_Grammar(_slice(h,base,hp['primitiveTestWindow']),label=LABEL+'.primitiveTest');g.take('test rax, rax');edge=g.branch('jne');g.finish()
    if edge['target']!=base+hp['restoreWindow']['startRva']:raise ValueError(LABEL+'.nonzero-cell-return')
    g=_Grammar(_slice(h,base,hp['fallbackWindow']),label=LABEL+'.fallback');g.take('movsx eax, byte [rbx+0xa]','cmp eax, 0x12');g.branch('jne','complex')
    g.take('mov rcx, rbx','add rsp, 0x20','pop rbx');edge=g.branch('jmp');g.labels['complex']=base+hp['complexWindow']['startRva'];g.finish()
    if edge['target']!=base+c['typeWrapperEntryRva']:raise ValueError(LABEL+'.class-record-tail')
    g=_Grammar(_slice(h,base,hp['complexWindow']),label=LABEL+'.complexGuard');g.take('sub eax, 0xf','cmp eax, 0xf');g.branch('ja','zero')
    g.take('movsxd rcx, eax',f'mov eax, [r8+rcx*4+0x{hp["tables"]["complexTargets"]["startRva"]:x}]','add rax, r8','jmp rax');g.labels['zero']=base+hp['zeroWindow']['startRva'];g.finish()
    g=_Grammar(_slice(h,base,hp['zeroWindow']),label=LABEL+'.zero');g.take('xor eax, eax');edge=g.branch('jmp');g.finish()
    if edge['target']!=base+hp['restoreWindow']['startRva']:raise ValueError(LABEL+'.zero-return-target')
    restore=_Grammar(_slice(h,base,hp['restoreWindow']),label=LABEL+'.helperRestore');restore.take('add rsp, 0x20','pop rbx','ret');restore.finish()
    g=_Grammar(programs['apiWrapper'],label=LABEL+'.apiWrapper');g.take('mov dl, 0x1');api_tail=g.branch('jmp');g.finish()
    if api_tail['target']!=base+roles['classHelper']['entryRva']:raise ValueError(LABEL+'.named-api-tail')
    request=_slice(programs['publication'],base,c['request']['window']);g=_Grammar(request,label=LABEL+'.int32Request')
    for register,prefix,literal in (('r8','4c8d05',c['request']['typeLiteral']),('rdx','488d15',c['request']['namespaceLiteral'])):
        r=g.row();b=bytes.fromhex(r['bytes']);at=int(r['va'],16)
        if b[:3]!=bytes.fromhex(prefix) or len(b)!=7 or at+7+int.from_bytes(b[3:],'little',signed=True)!=base+literal['rva']:raise ValueError(LABEL+'.request-literal-address')
    _global(g,'rcx',8,base+c['request']['imageCellRva']);g.call(base+c['request']['lookupEntryRva']);_absolute_memory(g,'store','rax',8,absolute=base+c['globals']['primitiveInt32']);g.finish();_closed_projection(request,pub['edges'])
    g=_Grammar(_slice(ctor,base,c['returnWindow']),label=LABEL+'.classReturn')
    _memory(g,'load','rbp',8,'rsp',l['restoreRbp']);g.take('mov rax, rbx');_memory(g,'load','rbx',8,'rsp',l['restoreRbx']);_memory(g,'load','rsi',8,'rsp',l['restoreRsi']);_memory(g,'load','rdi',8,'rsp',l['restoreRdi']);g.take('add rsp, 0x20','pop r14','ret');g.finish()
    truth_cases=0
    for previous in range(256):
        for bit in (0,1):
            for generic in (False,True):
                result=enum_flag_update(previous,bit<<1,generic)
                if bool(result&4)!=bool(bit) or bool(result&16)!=generic or result&0xeb!=previous&0xeb:raise ValueError(LABEL+'.flag-truth-table')
                truth_cases+=1
    return {'status':'complete-class-enum-fields-and-selected-primitive-cell-flow-proved',
        'codeInstructions':sum(len(r) for r in programs.values()),'constructorInstructions':len(ctor),'classHelperInstructions':len(h),
        'flagTruthCases':truth_cases,'recordAndAllocationRegisterOriginsProvedUnderNormalAbi':True,'classEnumBitAtStoreEqualsRecordBitOne':True,
        'classElementAndCastInitializeToSelfBeforeEnumBranch':True,'enumElementHelperResultAssignedToBothClassFields':True,
        'minusOneElementIndexUsesSavedZeroPointerArgument':True,'minusOneElementIndexProvesNullClassReturn':False,
        'primitiveKindEightReadsFreshClassCell':True,'primitiveInt32CellNamedByLiteralRequest':True,'namedClassFromTypeApiTailJoined':True,
        'primitiveKindEightReturnsItsOneFreshCellValueOrZero':True,'allocatedClassReturnedAfterElementStores':True,
        'primitiveKindEightNonNullClassGuaranteed':False,'lookupReturnedSystemInt32ClassProved':False,
        'opaqueChildrenOrAliasesCannotChangeEnumFlagProved':False,'actualElementClassIsSystemInt32Proved':False,
        'repeatedClassResultsEquated':False,'concreteDamageTypeSharingSelected':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
