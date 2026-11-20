"""Prove one closed CharacterAIMode carrier and conditional graph pool request.

The same-image API authenticates this contract without reopening native files.
Its caller owns selected-input and contract-byte before/after bookends.
"""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_extent
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp import protocol
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data.skill_ai_dispatch_native import _strict
from scripts.game_data.skill_request_cache_native import _branch
from scripts.game_data.skill_combo_acceptance_native import _written_register

SCHEMA='endfield.skill-ai-mode-layout-native-contract.v2'
AUDIT_SCHEMA='endfield.skill-ai-mode-layout-native-audit.v2'
CONTRACT_PATH=CONTRACTS_DIR/'skill_ai_mode_layout_native.json'
LABEL='skillAiModeLayout'
MODE='Beyond.Gameplay.AI.CharacterAIMode'
GENERIC='Beyond.Gameplay.AI.AIMode`1'
ENUM='Beyond.Gameplay.AI.CharacterAIModeType'
POOL='Beyond.Gameplay.AIClassPool'
GRAPH='Beyond.Gameplay.AI.AIGraph'


def _r15_effect(raw,rva):
    """Finite x64 GPR-write decoder; unsupported extended-register ops reject.

    SSE register destinations are separate from GPRs. Calls preserve R15 only
    under the stated normal Win64 nonvolatile-register premise.
    """
    at=0;legacy=[]
    while at<len(raw)and raw[at]in(0xf0,0xf2,0xf3,0x66,0x67,0x2e,0x36,0x3e,0x26,0x64,0x65):legacy.append(raw[at]);at+=1
    rex=raw[at]if at<len(raw)and 0x40<=raw[at]<=0x4f else 0
    if rex:at+=1
    _require(at<len(raw),'mode-flow-opcode','bounded instruction',raw.hex())
    op=raw[at];at+=1
    _require(op not in(0xc4,0xc5,0x62),'mode-flow-vector-prefix','reviewed legacy/REX framing',raw.hex())
    if not rex&5:return 'preserve'
    if 0x50<=op<=0x57:return 'preserve'
    if 0x58<=op<=0x5f:return 'unknown'if (op-0x58)+(8 if rex&1 else 0)==15 else'preserve'
    if 0xb8<=op<=0xbf:return 'unknown'if (op-0xb8)+(8 if rex&1 else 0)==15 else'preserve'
    if 0x90<=op<=0x97:return 'unknown'if (op-0x90)+(8 if rex&1 else 0)==15 else'preserve'
    if op in(0xe8,0xe9,0xeb,0xc3,0xc2,0xcc):return 'preserve'
    two=None
    if op==0x0f:
        _require(at<len(raw),'mode-flow-two-byte','complete opcode',raw.hex());two=raw[at];at+=1
        if 0x80<=two<=0x8f:return 'preserve'
    _require(at<len(raw),'mode-flow-modrm','complete reviewed ModRM',raw.hex())
    m=raw[at];mode=m>>6;reg=((m>>3)&7)+(8 if rex&4 else 0);rm=(m&7)+(8 if rex&1 else 0)
    write_reg=False;write_rm=False
    if two is None:
        if op in(0x8a,0x8b,0x8d,0x63,0x03,0x0b,0x13,0x1b,0x23,0x2b,0x33,0x69,0x6b):write_reg=True
        elif op in(0x88,0x89,0x01,0x09,0x11,0x19,0x21,0x29,0x31,0xc6,0xc7,0xc0,0xc1,0xd0,0xd1,0xd2,0xd3,0x8f):write_rm=True
        elif op in(0x86,0x87):write_reg=True;write_rm=True
        elif op in(0x80,0x81,0x83):write_rm=(m>>3)&7!=7
        elif op==0xff:write_rm=(m>>3)&7 in(0,1)
        elif op in(0xf6,0xf7):write_rm=(m>>3)&7 in(2,3)
        elif op in(0x84,0x85,0x38,0x39,0x3a,0x3b):pass
        else:raise ValueError('mode-flow-unsupported-extended-opcode: '+raw.hex())
    elif two in(0xb6,0xb7,0xbe,0xbf,0xaf,0x2c,0x2d,0x50,0xd7)or 0x40<=two<=0x4f:write_reg=True
    elif 0x90<=two<=0x9f or two in(0xb0,0xb1,0xab,0xb3,0xbb):write_rm=True
    elif two in(0xc0,0xc1):write_reg=True;write_rm=True
    elif two==0xba:write_rm=(m>>3)&7 in(5,6,7)
    elif two==0x7e:
        mandatory=[prefix for prefix in legacy if prefix in(0x66,0xf2,0xf3)]
        _require(mandatory in([], [0x66], [0xf3])and 0xf0 not in legacy,
                 'mode-flow-unsupported-movd-prefix','unprefixed MMX, 66 XMM store, or F3 XMM load',raw.hex())
        # Unprefixed MMX MOVD/MOVQ and 66 XMM MOVD/MOVQ both write r/m.
        # F3 MOVQ instead loads an XMM destination, never a GPR destination.
        write_rm=mandatory!=[0xf3]
    elif two in(0x10,0x11,0x28,0x29,0x2e,0x2f,0x54,0x55,0x56,0x57,0x58,0x59,0x5c,0x5e,0x6e,0x6f,0x7f,0x15,0x16,0x17,0xc6,0xef,0x18,0x1f,0xa3):pass
    else:raise ValueError('mode-flow-unsupported-extended-two-byte: '+raw.hex())
    if (write_reg and reg==15)or(write_rm and mode==3 and rm==15):
        if raw[:3]==bytes.fromhex('4c8d3d')and len(raw)==7 and rva+7+struct.unpack_from('<i',raw,3)[0]==0:return 'imageBase'
        return 'unknown'
    return 'preserve'


def prove_method_image_base_flow(records,spec,read_bytes):
    """Bounded single-method CFG, checked jump tables and R15 abstract states."""
    start,end=spec['codeStartRva'],spec['codeEndRva'];entry=spec['entryRva'];target=spec['targetRva']
    _require(type(start)is int and type(end)is int and 0<end-start<=0x10000 and entry==start
        and spec['normalCallsPreserveR15Required']is True and spec['completeMethodCodeFramingProved']is True
        and spec['runtimePathsObserved']is False,'mode-flow-scope','bounded complete method under explicit call premise',spec)
    selected={at:raw for at,raw in records.items()if start<=at<end};at=start
    while at<end:_require(at in selected,'mode-flow-code-gap','continuous instruction starts',at);at+=len(selected[at])
    _require(at==end and target in selected,'mode-flow-code-end',(end,target),at)
    tables={};guard_sequences=[]
    for row in spec['tables']:
        initial,compare,branch,repeat,sign,load,add,jump=[row[k]for k in('initialIndexRva','boundCompareRva','boundBranchRva','repeatIndexRva','signExtendRva','loadRva','addRva','jumpRva')]
        points=[initial,compare,branch,repeat,sign,load,add,jump]
        _require(all(a+len(selected[a])==b for a,b in zip(points,points[1:])),
                 'mode-flow-table-sequence','contiguous guard/index/load/add/jump',row)
        count=len(row['targets']);raw=read_bytes(row['tableRva'],4*count)
        _require(0<count<=128 and raw.hex()==row['tableHex']and list(struct.unpack('<'+'I'*count,raw))==row['targets']
            and all(t in selected for t in row['targets']),'mode-flow-table-bytes','actual uint32 RVA entries to method instructions',row)
        _require(selected[initial]==selected[repeat]and len(selected[initial])==3 and selected[initial][:1]==b'\x8d'
            and selected[initial][1]in(0x41,0x42,0x43,0x45,0x46,0x47)
            and selected[initial][-1]==0xff and selected[compare]==bytes.fromhex('83f8')+bytes([count-1])
            and (selected[branch][0]==0x77 or selected[branch][:2]==bytes.fromhex('0f87'))
            and _branch(selected[branch],branch)not in points,
            'mode-flow-table-bounds','same (source-1) index and unsigned upper bound',row)
        indexed=selected[load];_require(len(indexed)==8 and indexed[:3]==bytes.fromhex('418b84')
            and indexed[3]in(0x97,0x8f)and struct.unpack_from('<i',indexed,4)[0]==row['tableRva']
            and selected[sign]==(bytes.fromhex('4863d0')if indexed[3]==0x97 else bytes.fromhex('4863c8'))
            and selected[add]==bytes.fromhex('4903c7')and selected[jump]==bytes.fromhex('ffe0'),
            'mode-flow-table-addressing','bounded index -> uint32 load [R15+index*4+table] -> add R15 -> jump',row)
        _require(jump not in tables,'mode-flow-table-duplicate','one binding per indirect jump',jump)
        tables[jump]=row;guard_sequences.append(points)
    edges={};effects={}
    for at,raw in selected.items():
        effects[at]=_r15_effect(raw,at);next_at=at+len(raw)
        _require(raw[0]not in(0x9a,0xea,0xcf,0xcd,0xce,0xf4)and raw[:2]not in(bytes.fromhex('0f05'),bytes.fromhex('0f07'),bytes.fromhex('0f34'),bytes.fromhex('0f35')),
                 'mode-flow-unsupported-control','ordinary near calls/branches/returns only',raw.hex())
        if raw[0]in(0xc3,0xc2,0xcc)or raw[:2]==bytes.fromhex('0f0b'):succ=[]
        elif raw[0]in(0xe9,0xeb):succ=[_branch(raw,at)]
        elif (len(raw)==2 and 0x70<=raw[0]<=0x7f)or(raw[:1]==b'\x0f'and len(raw)==6 and 0x80<=raw[1]<=0x8f):succ=[next_at,_branch(raw,at)]
        elif raw[0]in(0xe0,0xe1,0xe2,0xe3):
            _require(len(raw)==2,'mode-flow-loop-encoding','rel8 loop/JCXZ framing',raw.hex());succ=[next_at,next_at+int.from_bytes(raw[1:],'little',signed=True)]
        else:
            pos=1 if 0x40<=raw[0]<=0x4f else 0
            if raw[pos:pos+1]==b'\xff'and (raw[pos+1]>>3)&7 in(3,5):raise ValueError('mode-flow-unsupported-far-transfer: '+raw.hex())
            if raw[pos:pos+1]==b'\xff'and (raw[pos+1]>>3)&7==4:
                _require(at in tables,'mode-flow-unresolved-indirect-jump','all indirect jumps have checked table patterns',at);succ=list(set(tables[at]['targets']))
            else:succ=[next_at]
        edges[at]=succ
    predecessors={at:set()for at in selected}
    for at,targets in edges.items():
        for dest in targets:
            if dest in predecessors:predecessors[dest].add(at)
    for points in guard_sequences:
        for previous,current in zip(points,points[1:]):
            _require(predecessors[current]=={previous},'mode-flow-table-guard-dominance',
                'no middle-of-index/table entry bypasses the bound',{'node':current,'predecessors':sorted(predecessors[current])})
    states={entry:{'unknown'}};queue=[entry]
    while queue:
        at=queue.pop();incoming=states[at];effect=effects[at];out=incoming if effect=='preserve'else{effect}
        if at in tables:_require(incoming=={'imageBase'},'mode-flow-jump-base-state','R15=imagebase at every reached indirect table jump',{'rva':at,'states':sorted(incoming)})
        for dest in edges[at]:
            _require(dest in selected,'mode-flow-external-reachable-edge','all reached normal control remains within framed method',{'from':at,'to':dest})
            before=states.get(dest,set());after=before|out
            if after!=before:states[dest]=after;queue.append(dest)
    _require(states.get(target)=={'imageBase'},'mode-flow-target-register-state','all reaching paths carry R15=imagebase',{'target':target,'states':sorted(states.get(target,set()))})
    return {'factoryImageBaseRegisterContinuityProved':True,'targetStates':['imageBase'],
        'reachableInstructionCount':len(states),'checkedTableCount':len(tables),
        'normalCallsPreserveR15Required':True,'runtimePathsObserved':False}


def _declarations(image,contract):
    md=image.metadata;c=NativeReferenceContext(image);fields={};sizes={};methods={}
    for row in contract['types']:
        owner=row['type'];td=image.named_types[owner];pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
        raw=image.pe.bytes_at_va(pointer,16)
        _require(c.parent(owner)==row['parent']and td.flags==row['flags']and td.bitfield==row['bitfield']
            and td.generic_container_index==row['genericContainerIndex']and raw.hex()==row['sizeRowHex']
            and int.from_bytes(raw[:4],'little')==row['instanceBytes'],'mode-layout-type-declaration',row,raw.hex())
        _require(td.flags&0x18==0 and td.bitfield&0x800,'mode-layout-default-packing','selected default instance layout',row)
        sizes[owner]=row['instanceBytes']
        actual=list(md.fields_for(td));expected=[f for f in contract['fields']if f['type']==owner]
        _require(len(actual)==len(expected),'mode-layout-complete-fields',len(expected),len(actual))
        offsets=protocol.runtime_type_field_offsets(md,image.pe,image.registration,td.index)
        for f,rowf in zip(actual,expected):
            value={'id':owner+'::'+md.string(f.name_index),'type':owner,'name':md.string(f.name_index),
                'valueType':c.type_name(f.type_index),'ordinaryKind':image.pe.bytes_at_va(c.type_pointer(f.type_index),16)[10],
                'attributes':c.field_attributes(f.type_index),'offset':offsets[md.string(f.name_index)]}
            c.require_ordinary_kind(f.type_index,value['ordinaryKind'])
            if value['ordinaryKind']==21:value['referenceExtent']=closed_generic_reference_extent(c,f.type_index)
            _require(_strict(value,rowf),'mode-layout-field-declaration',rowf,value);fields[value['id']]=rowf
    _require(set(sizes)=={MODE,GENERIC,ENUM,POOL},'mode-layout-type-coverage','complete concrete/generic/base/argument',list(sizes))
    td=image.named_types[GENERIC];section=md.sections['genericContainers'];at=section.offset+td.generic_container_index*16
    _require(td.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16,'mode-layout-generic-container','bounded actual class parameter',at)
    owner,count,is_method,param=struct.unpack_from('<iiii',md.buf,at)
    _require((owner,count,is_method)==(td.index,1,0)and fields[GENERIC+'::<modeType>k__BackingField']['valueType']=='VAR['+str(param)+']',
        'mode-layout-generic-binding','sole selected enum parameter',(owner,count,is_method,param))
    for row in contract['methods']:
        index=image.validate_method_row(row['identity'],label=LABEL);m=md.methods[index]
        actual={'id':md.type_full_name(md.types[m.declaring_type])+'.'+md.string(m.name_index),'identity':row['identity'],
            'returnType':c.type_name(m.return_type),'parameters':[{'name':md.string(p.name_index),'type':c.type_name(p.type_index)}for p in md.parameters_for(m)],
            'slot':m.slot,'isStatic':bool(m.flags&16)}
        _require(_strict(actual,row),'mode-layout-method-declaration',row,actual);methods[row['id']]=row
    return fields,sizes,methods


def _layout(contract,fields,sizes):
    layout=contract['layout'];pointer=layout['pointerBytes'];header=layout['objectHeaderBytes']
    _require(type(pointer)is int and pointer==8 and type(header)is int and header==16
        and layout['selectedClosedWitnessOnly']is True and layout['allGenericInstantiationsProved']is False,
        'mode-layout-scope','selected Win64 closed witness only',layout)
    declarations=lambda owner:[f for f in fields.values()if f['type']==owner and not f['attributes']&16]
    _require([(f['name'],f['offset'],f['ordinaryKind'])for f in declarations(POOL)]==[
        ('<poolDestroyTime>k__BackingField',header,12),('<inPool>k__BackingField',header+4,2)]
        and sizes[POOL]==layout['baseBytes']==((header+5+pointer-1)//pointer)*pointer,
        'mode-layout-base-complete','float/bool plus minimum required pointer alignment',sizes)
    _require(sizes[ENUM]-header==layout['enumBytes']==4 and fields[ENUM+'::value__']['valueType']=='int',
        'mode-layout-argument-storage','selected enum actual Int32 storage',sizes)
    suffix=declarations(MODE);_require([f['name']for f in suffix]==['m_data','m_originalBehavior']
        and [f['offset']for f in suffix]==[layout['prefixEnd'],layout['prefixEnd']+pointer]
        and suffix[0]['ordinaryKind']==18 and suffix[1]['referenceExtent']['bytes']==pointer
        and sizes[MODE]==layout['concreteBytes']==layout['prefixEnd']+2*pointer,
        'mode-layout-complete-suffix','all actual concrete instance fields occupy full suffix',suffix)
    declared=declarations(GENERIC);names=[f['name']for f in declared]
    required=['m_system','systemTypeIndexSet','<blackBoard>k__BackingField','<modeType>k__BackingField','<graph>k__BackingField']
    _require(names==required,'mode-layout-prefix-fields','all five generic declarations, no anonymous fields',names)
    rows={r['name']:r for r in layout['closedFields']}
    _require(set(rows)==set(required)and len(rows)==len(layout['closedFields']),'mode-layout-closed-field-coverage',required,list(rows))
    for f in declared:
        row=rows[f['name']];width=layout['enumBytes']if f['name']==required[3]else pointer
        _require(type(row['offset'])is int and type(row['bytes'])is int and row['bytes']==width
            and row['offset']%min(width,pointer)==0 and layout['baseBytes']<=row['offset']<row['offset']+width<=layout['prefixEnd'],
            'mode-layout-field-extent','bounded aligned selected field',row)
        if f['ordinaryKind']==21:_require(f['referenceExtent']['bytes']==pointer,'mode-layout-reference-width',pointer,f)
    _require(fields[GENERIC+'::<graph>k__BackingField']['valueType']==GRAPH,'mode-layout-graph-declaration',GRAPH,fields)
    known=[rows[n]for n in required[:-1]];occupied={i for r in known for i in range(r['offset'],r['offset']+r['bytes'])}
    _require(len(occupied)==sum(r['bytes']for r in known),'mode-layout-no-overlap','disjoint native-witnessed fields',known)
    candidates=[i for i in range(layout['baseBytes'],layout['prefixEnd']-pointer+1,pointer)if not occupied.intersection(range(i,i+pointer))]
    _require(candidates==[rows[required[-1]]['offset']],'mode-layout-graph-unique-slot','only remaining aligned reference slot',candidates)
    all_occupied={i for row in rows.values()for i in range(row['offset'],row['offset']+row['bytes'])}
    holes=[];at=layout['baseBytes']
    while at<layout['prefixEnd']:
        if at in all_occupied:at+=1;continue
        end=at+1
        while end<layout['prefixEnd']and end not in all_occupied:end+=1
        holes.append([at,end]);at=end
    _require(_strict(layout['requiredPadding'],[[header+5,layout['baseBytes']],*holes]),
             'mode-layout-required-padding','only computed base and enum/reference alignment holes',holes)
    # Neither the generic definition's zero size nor its placeholder offsets is used.
    return rows


def validate_skill_ai_mode_layout_image(image,contract):
    """Same opened image proof; caller must authenticate native/contract bookends."""
    fields,sizes,methods=_declarations(image,contract);slots=_layout(contract,fields,sizes);records={};windows={r['role']:r for r in contract['codeWindows']}
    _require(set(windows)==set(contract['programs']),'mode-layout-program-coverage','same bounded roles',windows)
    image.check_windows(list(windows.values()),label=LABEL)
    for role,rows in contract['programs'].items():
        window=windows[role];at=window['startRva'];_require(0<window['endRva']-at<=0x10000,'mode-layout-window-bound','bounded',window)
        if window['method']:
            family=image.unwind_index.family(methods[window['method']]['identity'][3])
            _require(any(r['runtimeTriple'][0]<=at and window['endRva']<=r['runtimeTriple'][1]for r in family['ranges']),
                'mode-layout-window-owner','actual named method unwind range',window)
        for row in rows:
            raw=bytes.fromhex(row['hex']);_require(row['rva']==at and 0<len(raw)<=15,'mode-layout-program-continuity',at,row)
            actual=image.pe.bytes_at_va(image.pe.image_base+at,len(raw));_require(actual==raw,'mode-layout-native-bytes',raw.hex(),actual.hex());records[at]=raw;at+=len(raw)
        _require(at==window['endRva'],'mode-layout-program-end',window['endRva'],at)
    contexts={r['role']:r['value']for r in contract['contexts']};operands=contract['operands']
    expected={'concreteBaseCtor':(GENERIC,'.ctor',[ENUM]),'systemsType':('System.Collections.Generic.List`1<Beyond.Gameplay.AI.AISystem>',None,None),
        'systemsCtor':('System.Collections.Generic.List`1','.ctor',['Beyond.Gameplay.AI.AISystem']),
        'setType':('System.Collections.Generic.HashSet`1<int>',None,None),'setCtor':('System.Collections.Generic.HashSet`1','.ctor',['int']),
        'blackboardType':('System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.AI.AIBlackBoard>',None,None),
        'blackboardCtor':('System.Collections.Generic.Dictionary`2','.ctor',['string','Beyond.Gameplay.AI.AIBlackBoard'])}
    _require(set(contexts)==set(expected)and len(contexts)==len(contract['contexts']),'mode-layout-context-coverage',list(expected),list(contexts))
    for role,(owner,name,args)in expected.items():
        ctx=contexts[role];actual=derive_typed_usage_context(image,ctx['instructionRva'],label=LABEL)
        _require(_strict(actual,ctx)and ctx['typeName']==owner and ctx['tag']==(1 if name is None else 6),
            'mode-layout-context-owner',(role,owner,name,args),actual)
        if name is not None:_require((ctx['methodName'],ctx['classArguments'],ctx['methodArguments'])==(name,args,[]),
            'mode-layout-context-arguments',(name,args,[]),ctx)
    tail=operands['baseCtorTailRva'];raw=records[tail]
    _require(raw[0]==0xe9 and _branch(raw,tail)==windows['physicalBaseCtor']['startRva']==operands['physicalCtorRva']
        and records[contexts['concreteBaseCtor']['instructionRva']].startswith(bytes.fromhex('488b15'))
        and records[operands['concreteReceiverSaveRva']]==bytes.fromhex('488bf9')
        and contexts['concreteBaseCtor']['instructionRva']+7==operands['baseReceiverRestoreRva']
        and records[operands['baseReceiverRestoreRva']]==bytes.fromhex('488bcf')
        and records[operands['physicalCtorReceiverSaveRva']]==bytes.fromhex('488bd9'),
        'mode-layout-constructor-physical-join','selected concrete tail + provided closed ctor context',raw.hex())
    pairs={'m_system':('systemsType','systemsCtor'),'systemTypeIndexSet':('setType','setCtor'),'<blackBoard>k__BackingField':('blackboardType','blackboardCtor')}
    for name,(type_role,ctor_role)in pairs.items():
        row=operands['constructorSlots'][name];tc=contexts[type_role];cc=contexts[ctor_role];at=operands['stores'][name];offset=slots[name]['offset']
        _require(fields[GENERIC+'::'+name]['valueType']==tc['typeName']and tc['instructionRva']+7==row['allocationRva']
            and records[row['allocationRva']][0]==0xe8 and row['allocationRva']+5==row['copyRva']
            and records[row['copyRva']]==bytes.fromhex('488bf8')and cc['instructionRva']+7+3==row['ctorCallRva']
            and records[row['ctorCallRva']][0]==0xe8 and row['ctorCallRva']+5+4==at
            and records[at]==bytes.fromhex('48897b')+bytes([offset]),
            'mode-layout-typed-allocation-store','same allocation result in nonvolatile RDI reaches unique declared field type',row)
    _require(records[operands['modeParameterSaveRva']]==bytes.fromhex('418bd8')
        and records[operands['receiverSaveRva']]==bytes.fromhex('4c8be9')
        and records[operands['stores']['<modeType>k__BackingField']]==bytes.fromhex('41895d')+bytes([slots['<modeType>k__BackingField']['offset']])
        and methods[MODE+'.InitData']['parameters'][1]=={'name':'key','type':ENUM},
        'mode-layout-formal-enum-store','typed third ABI argument R8D->EBX; selected receiver R13',operands)
    _require(records[operands['concreteDataStoreRva']]==bytes.fromhex('4d897d')+bytes([fields[MODE+'::m_data']['offset']])
        and records[operands['brainGraphReadRva']]==bytes.fromhex('488b48')+bytes([slots['<graph>k__BackingField']['offset']]),
        'mode-layout-named-suffix-and-reader','actual concrete prefix boundary and ordinary graph carrier read',operands)
    factory=contract['factory'];raw=image.pe.bytes_at_va(image.pe.image_base+factory['tableRva'],len(bytes.fromhex(factory['tableHex'])))
    _require(raw.hex()==factory['tableHex']and list(struct.unpack('<7i',raw))==factory['tableTargets']
        and factory['selectedGraphEnum']==7 and factory['tableTargets'][factory['selectedGraphEnum']-1]==factory['selectedCaseRva'],
        'mode-layout-factory-table','selected enum7 actual switch-table destination',factory)
    load=records[factory['tableLoadRva']]
    _require(load[:4]==bytes.fromhex('418b848f')and struct.unpack('<i',load[4:])[0]==factory['tableRva']
        and records[factory['boundsRva']]==bytes.fromhex('8d47ff')
        and records[factory['boundsRva']+3]==bytes.fromhex('83f806'),
        'mode-layout-factory-switch-operand','(graphEnum-1) <= 6 then actual indexed table load',load.hex())
    ctx=factory['poolContext'];_require(_strict(derive_typed_usage_context(image,ctx['instructionRva'],label=LABEL),ctx)
        and ctx['instructionRva']==factory['selectedCaseRva']and ctx['tag']==6
        and (ctx['typeName'],ctx['methodName'],ctx['classArguments'],ctx['methodArguments'])==('Beyond.Gameplay.AIManager','GetClassFromPool',[],['Beyond.Gameplay.AI.CharacterCastSkillGraph']),
        'mode-layout-factory-pool-context','actual provided closed graph pool request',ctx)
    call=factory['poolCallRva'];_require(ctx['instructionRva']+7+3==call and records[call][0]==0xe8
        and _branch(records[call],call)==factory['physicalPoolTargetRva']and call+5==factory['resultToCarrierRva']
        and records[call+5]==bytes.fromhex('488bd8')
        and records[factory['graphStoreRva']]==bytes.fromhex('49895d')+bytes([slots['<graph>k__BackingField']['offset']]),
        'mode-layout-factory-result-store','physical pool result RAX->RBX -> selected graph carrier slot',factory)
    at=factory['resultToCarrierRva']+len(records[factory['resultToCarrierRva']])
    _require(records[at]==bytes.fromhex('4885c0'),'mode-layout-factory-null-test','same physical result tested before use',records[at].hex())
    at+=len(records[at]);branch=records[at]
    _require(branch[:2]==bytes.fromhex('0f84')and _branch(branch,at)==factory['nullOrUnsupportedRva'],
             'mode-layout-factory-null-branch','null result leaves selected store path',branch.hex())
    at+=len(branch)
    while at<factory['graphStoreRva']:
        instruction=records[at]
        # Calls are explicit Win64 normal-return nonvolatile preservation premises.
        if instruction[0]!=0xe8:_require(_written_register(instruction)not in('rbx','r13'),
            'mode-layout-factory-result-preservation','same result/receiver registers until actual field store',instruction.hex())
        at+=len(instruction)
    _require(at==factory['graphStoreRva'],'mode-layout-factory-store-continuity','complete nonnull local path',at)
    flow_spec=contract['methodImageBaseFlow']
    _require(flow_spec['entryRva']==methods[MODE+'.InitData']['identity'][3]
        and flow_spec['targetRva']==factory['tableLoadRva']
        and flow_spec['codeStartRva']==windows['initDataImageBaseFlow']['startRva']
        and flow_spec['codeEndRva']==windows['initDataImageBaseFlow']['endRva'],
        'mode-flow-method-and-consumer-join','actual InitData entry and selected factory indexed load',flow_spec)
    flow=prove_method_image_base_flow(records,flow_spec,lambda at,size:image.pe.bytes_at_va(image.pe.image_base+at,size))
    rules=contract['rules'];expected_rules={'originalPathOnly':True,'closedModeGraphCarrierLayoutProved':True,'selectedWitness':MODE,
        'genericModeFieldOffsetsAreNotUsed':True,'graphCarrierOffset':slots['<graph>k__BackingField']['offset'],
        'modeTypeCarrierOffset':slots['<modeType>k__BackingField']['offset'],'providedClosedBaseConstructorContextProved':True,
        'compiledBaseConstructorDeclarationProved':False,'graphEnum7PoolRequestProved':True,
        'providedPoolArgument':'Beyond.Gameplay.AI.CharacterCastSkillGraph','compiledPoolClosedDeclarationProved':False,
        'physicalPoolResultIsGraphCarrierStore':True,'graphEnumVirtualResultBoundTo7Proved':False,
        'returnedGraphConcreteRuntimeTypeProved':False,'runtimeExecutionProved':False,'actualCastProved':False,
        'nonvolatileRbxAndR13PreservationRequired':True,'fullInitDataReceiverContinuityProved':False,
        'factoryImageBaseRegisterContinuityProved':True}
    _require(_strict(rules,expected_rules),'mode-layout-rules-boundary',expected_rules,rules)
    return {'rules':dict(rules),'closedFields':list(slots.values()),'evidence':'conditional','methodImageBaseFlow':flow,
        'conditions':['original path','compatible nonnull allocations','normal nonvolatile-register-preserving helper returns',
            'graphEnum getter result explicitly equals 7 for the factory fragment','full InitData receiver continuity remains a premise',
            'factory R15=imagebase is proved for all framed reaching paths under normal Win64 call preservation; runtime path selection remains unobserved']}


def load_skill_ai_mode_layout(contract_path:Path=CONTRACT_PATH,*,gameassembly:Path,metadata:Path):
    path=Path(contract_path);audit={'schema':AUDIT_SCHEMA,'status':'validation_failed','nativeInputs':{},'rules':{},'closedFields':[],'methodImageBaseFlow':{},'failures':[],'contract':str(path)}
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL);audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary']);pins=contract['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=validate_skill_ai_mode_layout_image(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','mode-layout-native-after','unchanged selected pair',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'mode-layout-contract-after','unchanged operation bytes','changed')
        audit.update(result,status='validated',detail='',nativeInputs=dict(pins))
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:800],nativeInputs={},rules={},closedFields=[],methodImageBaseFlow={})
        audit['failures'].append({'validator':LABEL,'check':str(error).split(':',1)[0],'source':str(path),'detail':str(error)[:800]})
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in('reports','scratch','tmp')):parser.error('--output must stay under reports/, scratch/ or tmp/')
    audit=load_skill_ai_mode_layout(args.contract,gameassembly=args.gameassembly,metadata=args.metadata);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps({k:audit[k]for k in('status','detail','failures')},indent=2));return 0 if audit['status']=='validated'else 1


if __name__=='__main__':raise SystemExit(main())
