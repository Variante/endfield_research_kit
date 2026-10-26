"""Closed triple comparator, iterator constructor and empty-output bridge."""
from __future__ import annotations
from .owned_partition import BranchGrammar,rip_load
from .field_construction_control import _lea
from .descriptor_cache_lookup_control import _at,_slice
from .context_slot_initializer_control import validate_closed_initializer_graph
from .initializer_control import control_transfer


def validate_probe_leaf(program,*,entry_va,labels):
    rows=program['rows'];g=BranchGrammar(rows,label='descriptorProbeLeaf');g.labels={k:entry_va+v for k,v in labels.items()}
    if not program['closedReachableInstructionGraph'] or program['containsCalls']:
        raise ValueError('descriptorProbeLeaf.not-closed-leaf')
    g.take('mov eax, [r8]','cmp dword [rdx], eax');g.branch('jne','false')
    g.take('cmp dword [rdx], 0x0');g.branch('jne','true')
    g.take('mov rcx, [r8+0x8]','mov r8, [rdx+0x8]','mov rax, [rcx]','cmp qword [r8], rax');g.branch('je','remaining')
    _at(g,'false');g.take('xor al, al','ret')
    _at(g,'remaining');g.take('mov rax, [rcx+0x8]','cmp qword [r8+0x8], rax');g.branch('jne','false')
    g.take('mov rax, [rcx+0x10]','cmp qword [r8+0x10], rax');g.branch('jne','false')
    _at(g,'true');g.take('mov al, 0x1','ret');g.finish()
    graph=validate_closed_initializer_graph(rows,entry_va=entry_va)
    if graph['calls'] or graph['trapSites']:raise ValueError('descriptorProbeLeaf.unreviewed-call-or-trap')
    return {'instructionsChecked':len(rows),'closedEntryProgramProved':True,'physicalFunctionExtentProved':False,
        'memoryWrites':0,'preservedRegisters':['rdx','r9','r10','r11','rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        'clobberedGeneralRegisters':['rax','rcx','r8'],'returnWidthBits':8,'returnValues':[0,1],
        'fullRaxGuaranteedZeroOrOne':False,'wrapperMarkerWidthBits':32,'zeroMarkerTripleOffsets':[0,8,16],
        'nonzeroEqualMarkersBypassTripleReads':True,'graph':graph,'runtimeExecutionKnown':False,
        'conditions':'Readable coherent wrapper markers and, for the zero-marker branch, readable coherent triples. The compared pointer contents are sampled by separate reads.'}


def validate_iterator_constructor(rows,*,image_base,function,segments,labels,globals,probe_rva,probe):
    base=image_base;graph=validate_closed_initializer_graph(rows,entry_va=base+function['entryRva'])
    admitted={int(r['va'],16) for r in rows for a,b in segments.values() if base+a<=int(r['va'],16)<base+b}
    if admitted!={int(r['va'],16) for r in rows}:raise ValueError('descriptorIteratorConstructor.semantic-program-coverage')
    if not {'r9','r10','r11'}<=set(probe['preservedRegisters']) or probe['memoryWrites']!=0:
        raise ValueError('descriptorIteratorConstructor.probe-effects-not-joined')
    g=_slice(rows,base,segments['primary']);g.labels={k:base+v for k,v in labels.items()}
    g.take('sub rsp, 0x28','mov [rcx+0x8], r8');_lea(g,'rax',rip=base+globals['table'])
    g.take('mov [rcx], rax','mov r10, rcx','mov [rcx+0x10], r9','cmp r8, r9');g.branch('jne','optionalScan')
    _at(g,'return');g.take('mov rax, r10','add rsp, 0x28','ret')
    _at(g,'optionalScan');g.take('cmp byte [rsp+0x50], 0x0');g.branch('je','return')
    _at(g,'scan');g.take('mov rcx, [r10+0x8]')
    r=g.row();f=r.get('memoryOperation',{});a=f.get('address',{})
    if (f.get('direction'),f.get('register'),f.get('registerBits'),a.get('absoluteAddress'))!=('load','eax',32,base+globals['marker']):
        g.fail('marker-load',globals['marker'],r)
    g.take('cmp eax, dword [rcx]');g.branch('jne','otherMarker')
    g.take('test eax, eax');g.branch('jne','advance')
    g.take('mov rdx, [rcx+0x8]');rip_load(g,'rcx',base+globals['sentinelTriple'])
    g.take('mov rax, [rdx]','cmp qword [rcx], rax');g.branch('je','remaining')
    _at(g,'otherMarker');g.take(f'cmp qword [rip => 0x{base+globals["auxiliaryCount"]:x}], 0x0');g.branch('jbe','return');g.branch('jmp','coldProbe')
    _at(g,'remaining');g.take('mov rax, [rdx+0x8]','cmp qword [rcx+0x8], rax');g.branch('jne','mismatch')
    g.take('mov rax, [rdx+0x10]','cmp qword [rcx+0x10], rax');g.branch('jne','mismatch')
    g.take('mov al, 0x1');_at(g,'testMatch');g.take('test al, al');g.branch('je','otherMarker')
    _at(g,'advance');r=g.take('add [r10+0x8], 0x10')
    if bytes.fromhex(r['bytes'])!=bytes.fromhex('49 83 42 08 10'):g.fail('qword-current-step','ADD QWORD output+8, 16',r)
    g.take('cmp qword [r10+0x8], r9');g.branch('jne','scan');g.branch('jmp','return')
    _at(g,'mismatch');g.take('xor al, al');g.branch('jmp','testMatch');g.finish()
    g=_slice(rows,base,segments['coldProbe']);g.labels={k:base+v for k,v in labels.items()};_at(g,'coldProbe')
    g.take('mov r8, [r10+0x8]');_lea(g,'rdx',rip=base+globals['probeData'])
    g.call(base+probe_rva);g.take('test al, al');g.branch('je','return');g.branch('jmp','advance');g.finish()
    if len(graph['calls'])!=1 or graph['calls'][0]['target']!=base+probe_rva:
        raise ValueError('descriptorIteratorConstructor.complete-probe-call-inventory')
    return {'instructionsChecked':len(rows),'completeControlAndFramesChecked':True,'graph':graph,
        'outputFields':{'table':0,'current':8,'end':16},'outputInputAndNormalReturn':'entry RCX',
        'initialCurrentSource':'entry R8','initialEndSource':'entry R9','fifthArgumentStackOffset':40,
        'equalInitialCurrentAndEndSkipsScanning':True,'currentStepBytes':16,'scanTerminationProved':False,
        'r9EndPreservedAcrossProbe':True,'r10OutputPreservedAcrossProbe':True,'r11PreservedAcrossCompleteConstructor':True,
        'runtimeExecutionKnown':False,'conditions':'Valid disjoint writable output and readable coherent iterator/table/triple storage. Normal internal probe returns require its readable operands; equal-start/end path does not invoke the probe.'}


def validate_empty_output_bridge(rows,*,image_base,entry_rva,globals,constructor_rva,constructor):
    base=image_base;g=BranchGrammar(rows,label='descriptorEmptyOutput');graph=validate_closed_initializer_graph(rows,entry_va=base+entry_rva)
    g.take('sub rsp, 0x38');rip_load(g,'r8',base+globals['capacity'])
    g.take('mov rcx, rdx','mov r9, r8','mov byte [rsp+0x20], 0x1','shl r9, 0x4','mov r11, rdx',
        f'add r9, qword [rip => 0x{base+globals["begin"]:x}]','shl r8, 0x4',
        f'add r8, qword [rip => 0x{base+globals["begin"]:x}]')
    g.call(base+constructor_rva);g.take('mov rax, r11','add rsp, 0x38','ret');g.finish()
    if not constructor['r11PreservedAcrossCompleteConstructor'] or not constructor['equalInitialCurrentAndEndSkipsScanning']:
        raise ValueError('descriptorEmptyOutput.constructor-effects-not-joined')
    if constructor['fifthArgumentStackOffset']!=32+8:raise ValueError('descriptorEmptyOutput.fifth-argument-frame')
    return {'instructionsChecked':len(rows),'completeControlAndFramesChecked':True,'graph':graph,
        'outputInputAndNormalReturn':'entry RDX','normalReturnR11PreservationProved':True,
        'sameCapacitySampleForBothEnds':True,'distinctBeginGlobalReadsRequireStability':True,
        'coherentGlobalsProduceCurrentEqualToEnd':True,'coherentEqualEndsSkipConstructorScan':True,
        'runtimeExecutionKnown':False,
        'conditions':'Compatible disjoint output storage; the two begin-global reads agree, and the lookup/caller end comparisons use coherent compatible globals. This is a conditional raw-store/cache-join claim, not an observed runtime hit.'}
