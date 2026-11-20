"""Authenticate bounded conditional AI graph, behavior and callback requests.

Mode/graph runtime selection, generic mode-slot ownership and concrete behavior
effects are separate from these original local dispatch programs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.protocol import field_defaults,native_enum_members
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data.skill_request_cache_native import _branch
from scripts.game_data.skill_combo_acceptance_native import _written_register

SCHEMA='endfield.skill-ai-dispatch-native-contract.v2'
AUDIT_SCHEMA='endfield.skill-ai-dispatch-native-audit.v2'
CONTRACT_PATH=CONTRACTS_DIR/'skill_ai_dispatch_native.json'
LABEL='skillAiDispatch'
BRAIN='Beyond.Gameplay.AI.CharacterAIBrain'
GRAPH='Beyond.Gameplay.AI.AIGraph'
CAST='Beyond.Gameplay.AI.CharacterCastSkillGraph'
BEHAVIOR='Beyond.Gameplay.AI.AIBehavior'


def _strict(actual,expected):
    if type(actual)is not type(expected):return False
    if isinstance(expected,dict):return actual.keys()==expected.keys()and all(_strict(actual[k],v)for k,v in expected.items())
    if isinstance(expected,list):return len(actual)==len(expected)and all(_strict(a,b)for a,b in zip(actual,expected))
    return actual==expected


def _rules(contract):
    rules=contract['rules']
    for key,value in {'originalPathOnly':True,'runtimeExecutionProved':False,'actualCastProved':False,'selectedConcreteBehaviorProved':False}.items():
        _require(rules.get(key)is value,'ai-rule-boundary',(key,value),rules.get(key))
    expected={
      'resetSelection':{'scope':'conditional-original-reset','noSkillData':'ResetAIMode(false,null)','castTypeEquals':1,
        'whenEqualStaticField':BRAIN+'::s_plungingAttackTag','otherwiseStaticField':BRAIN+'::s_castSkillTag',
        'comparison':'int32-not-equal','comparisonFalse':'return','comparisonTrue':'SwitchAIBehavior(nullable-present,requestTag)',
        'postCallWrite':'independently reread selected static tag','staticReadStabilityProved':False},
      'brainForward':{'scope':'conditional-original-closed-mode-graph','nullMode':'return','nullGraph':'return',
        'request':'AIGraph.SwitchBehavior','force':True,'nullablePayloadPreserved':True,'closedModeGraphOwnershipProved':True},
      'enterRequests':{'scope':'conditional-original-collection-requests','clearCurrentBehaviorsBeforeLookup':True,
        'lookupOnlyIfTagPresent':True,'enterOnlyIfLookupTrue':True,'iteration':'ascending explicit item results',
        'request':'AIBehavior.Enter','writeTagAfterEnterRequests':True,'concreteBehaviorEntryProved':False,'collectionStabilityRequired':True},
      'finishCallback':{'scope':'conditional-original-callback-tail','requiresInitiallyPresentCallback':True,
        'requiresAllReachedCurrentBehaviorsFinished':True,'nullOrEmptyListSatisfied':True,
        'falseFinishReturnsWithoutClear':True,'invokeOnlyIfRereadCallbackNonnull':True,
        'clearAfterNormalInvokeOrNullReread':True,'callbackEffectProved':False,'collectionStabilityRequired':True},
      'mode5Lookup':{'scope':'conditional-original-lookup-request','mode':5,'enumName':'CastSkill',
        'receiverField':BRAIN+'::m_modeData','outField':BRAIN+'::m_curMode','lookupResultBoolNotBranchedOn':True,
        'collectionEffectProved':False,'dynamicGraphSelectionProved':False}}
    facts={r['id']:r for r in contract['facts']}
    _require(set(rules)==set(expected)|{'originalPathOnly','runtimeExecutionProved','actualCastProved','selectedConcreteBehaviorProved'},
             'ai-rule-keys','exact admitted rule keys',list(rules))
    _require(set(facts)==set(expected)and len(facts)==len(contract['facts']),'ai-fact-coverage',list(expected),list(facts))
    for key,value in expected.items():
        _require(set(facts[key])=={'id','evidence','rule','boundary'}and _strict(rules[key],value)and _strict(facts[key]['rule'],value)and facts[key]['evidence']=='conditional'and facts[key]['boundary'],
                 'ai-rule-fact-binding',value,rules[key])
    slots=contract['conditionalSlots']
    _require(slots['closedGenericOwnershipProved']is True and slots['graphConcreteRuntimeTypeProved']is False
        and slots['graphEntitySourceChainProvedHere']is False,'ai-slot-boundary','explicit unproved closed/runtime joins',slots)
    return rules


def _declarations(image,contract):
    context=NativeReferenceContext(image);methods={}
    for row in contract['methods']:
        identity=row['identity'];index=image.validate_method_row(identity,label=LABEL);method=image.metadata.methods[index]
        _require(row['id']==identity[1]+'.'+identity[2]and row['id']not in methods,'ai-method-nominal','unique nominal declaration',row)
        actual={'returnType':context.type_name(method.return_type),'parameters':[{'name':image.metadata.string(p.name_index),'type':context.type_name(p.type_index)}
            for p in image.metadata.parameters_for(method)],'slot':method.slot,'isStatic':bool(method.flags&16)}
        _require(_strict(actual,{key:row[key]for key in actual}),'ai-method-signature',row,actual);methods[row['id']]=row
    fields=_validate_fields(image,contract['fields'])
    for row in fields.values():
        td=image.named_types[row['type']];f=next(f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)==row['name'])
        _require(bool(context.field_attributes(f.type_index)&16)==row['static'],'ai-field-static',row['static'],row)
    for owner,parent in contract['parents'].items():
        _require(context.parent(owner)==parent,'ai-parent-edge',(owner,parent),context.parent(owner))
    enum=contract['enum'];actual=native_enum_members(image.metadata,field_defaults(image.metadata),image.pe,image.registration,enum['type'])
    _require(actual==enum['members']and any(x['id']==5 and x['name']=='CastSkill'for x in actual),
             'ai-mode-enum',enum,actual)
    return methods,fields


def _read_mode_layout(contract):
    # Local import avoids a cycle: the independent layout module uses _strict.
    from scripts.game_data import skill_ai_mode_layout_native as layout
    expected={'file':layout.CONTRACT_PATH.name,'schema':layout.SCHEMA,'consumption':'closed-carrier-layout-only'}
    _require(_strict(contract['modeLayoutContract'],expected),'ai-layout-link-declaration',expected,contract.get('modeLayoutContract'))
    linked,digest=read_reviewed_contract(layout.CONTRACT_PATH,schema=layout.SCHEMA,status='reviewed',label=LABEL+'.modeLayout')
    _require(_strict(linked['nativeInputs'],contract['nativeInputs']),'ai-layout-native-pins',contract['nativeInputs'],linked['nativeInputs'])
    return linked,digest,layout.CONTRACT_PATH


def _validate(image,contract,mode_layout=None):
    rules=_rules(contract);methods,fields=_declarations(image,contract);windows={r['role']:r for r in contract['codeWindows']}
    _require(len(windows)==len(contract['codeWindows'])and set(windows)==set(contract['programs']),
             'ai-program-coverage','unique reviewed windows/programs',list(windows))
    image.check_windows(list(windows.values()),label=LABEL);records={}
    families={}
    for role,rows in contract['programs'].items():
        window=windows[role];at=window['startRva']
        _require(0<window['endRva']-at<=0x10000,'ai-window-bound','bounded code fragment',window)
        _require(window['method']is None or window['method']in methods,'ai-window-method','known method or anonymous helper',window)
        if window['method']is not None:
            method=window['method'];entry=methods[method]['identity'][3]
            if method not in families:families[method]=image.unwind_index.family(entry)
            ranges={(r['runtimeTriple'][0],r['runtimeTriple'][1])for r in families[method]['ranges']}
            _require((window['startRva'],window['endRva'])in ranges,'ai-window-family-owner',(method,entry,ranges),window)
        for row in rows:
            raw=bytes.fromhex(row['hex']);_require(row['rva']==at and 0<len(raw)<=15,'ai-program-continuity',at,row)
            actual=image.pe.bytes_at_va(image.pe.image_base+at,len(raw));_require(actual==raw,'ai-program-bytes',raw.hex(),actual.hex())
            records[at]=raw;at+=len(raw)
        _require(at==window['endRva'],'ai-program-end',window['endRva'],at)
    anchors={}
    for role,row in contract['anchors'].items():
        raw=bytes.fromhex(row['hex']);parts=[];at=row['rva']
        while sum(map(len,parts))<len(raw):parts.append(records[at]);at+=len(parts[-1])
        _require(b''.join(parts)==raw,'ai-anchor-program-join',raw.hex(),b''.join(parts).hex());anchors[role]=raw
    expected={'brainToGraph':GRAPH+'.SwitchBehavior','graphToForce':GRAPH+'._SwitchBehaviorForce',
        'forceToNext':GRAPH+'._EnterNextBehavior','resetToData':BRAIN+'.GetComboSkillData','resetToMode':BRAIN+'.ResetAIMode',
        'resetToBrainCast':BRAIN+'.SwitchAIBehavior','resetToBrainPlunge':BRAIN+'.SwitchAIBehavior',
        'graphToBehaviorEnter':BEHAVIOR+'.Enter','castEnterToReset':CAST+'._ResetBehavior'}
    calls={}
    caller={'brainToGraph':BRAIN+'.SwitchAIBehavior','graphToForce':GRAPH+'.SwitchBehavior',
        'forceToNext':GRAPH+'._SwitchBehaviorForce','resetToData':CAST+'._ResetBehavior','resetToMode':CAST+'._ResetBehavior',
        'resetToBrainCast':CAST+'._ResetBehavior','resetToBrainPlunge':CAST+'._ResetBehavior',
        'graphToBehaviorEnter':GRAPH+'._EnterNextBehavior','castEnterToReset':CAST+'.OnEnter'}
    for row in contract['directCalls']:
        role=row['role'];target=expected[role];raw=records[row['rva']]
        owners=[w['method']for w in windows.values()if w['startRva']<=row['rva'] and row['rva']+len(raw)<=w['endRva']]
        _require(owners==[caller[role]]and role not in calls and row['targetMethod']==target and row['targetIdentity']==methods[target]['identity']
            and raw[0]in(0xe8,0xe9)and _branch(raw,row['rva'])==methods[target]['identity'][3],
            'ai-call-method-join',(role,target),row);calls[role]=row
    _require(set(calls)==set(expected),'ai-call-coverage',list(expected),list(calls))
    for row in contract['anonymousCalls']:
        raw=records[row['rva']]
        _require(row['window']=='tagCompare'and row['targetRva']==windows['tagCompare']['startRva']
            and raw[0]==0xe8 and _branch(raw,row['rva'])==row['targetRva'],
            'ai-anonymous-compare-target','same selected helper entry',row)
    _require({r['role']for r in contract['anonymousCalls']}=={'tagCompareCast','tagComparePlunge'},'ai-compare-call-coverage','both cast kinds',contract['anonymousCalls'])
    for row in contract['contexts']:
        _require(derive_typed_usage_context(image,row['instructionRva'],label=LABEL)==row,'ai-typed-context',row,'changed')
    expected_contexts={'modeLookup':(BRAIN+'.SwitchAIMode','System.Collections.Generic.Dictionary`2','TryGetValue',['Beyond.Gameplay.AI.CharacterAIModeType','Beyond.Gameplay.AI.CharacterAIMode'],'r9'),
        'exitMode':(BRAIN+'.SwitchAIMode','Beyond.Gameplay.AI.AIMode`1','ExitMode',['Beyond.Gameplay.AI.CharacterAIModeType'],'r8'),
        'enterMode':(BRAIN+'.SwitchAIMode','Beyond.Gameplay.AI.AIMode`1','EnterMode',['Beyond.Gameplay.AI.CharacterAIModeType'],'r8'),
        'behaviorLookup':(GRAPH+'._EnterNextBehavior','System.Collections.Generic.Dictionary`2','TryGetValue',['Beyond.Gameplay.Core.GameplayTag','System.Collections.Generic.List`1<'+BEHAVIOR+'>'],'r9'),
        'behaviorItem':(GRAPH+'._EnterNextBehavior','System.Collections.Generic.List`1','get_Item',[BEHAVIOR],'r8'),
        'callbackItem':(GRAPH+'._EnterNextBehavior','System.Collections.Generic.List`1','get_Item',[BEHAVIOR],'r8')}
    bindings={r['role']:r for r in contract['contextBindings']}
    _require(set(bindings)==set(expected_contexts)and len(bindings)==len(contract['contexts'])==len(contract['contextBindings']),
             'ai-context-role-coverage','complete current collection/mode consumers',list(bindings))
    for role,(owner,nominal,name,args,carrier)in expected_contexts.items():
        row=bindings[role];ctx=row['context'];at=ctx['instructionRva'];call=row['callRva']
        _require(ctx in contract['contexts']and (row['owner'],ctx['typeName'],ctx['methodName'],ctx['classArguments'],ctx['methodArguments'])
            ==(owner,nominal,name,args,[])and ctx['instructionHex'].startswith('4C8B0D'if carrier=='r9'else'4C8B05'),
            'ai-context-nominal-role',(owner,nominal,name,args,carrier),row)
        _require(any(w['method']==owner and w['startRva']<=at<call and call+5<=w['endRva']for w in windows.values()),
                 'ai-context-owner-call','same current native owner window',row)
        at+=len(records[at])
        while at<call:
            _require(_written_register(records[at])!=carrier,'ai-context-carrier-preservation',carrier,records[at].hex());at+=len(records[at])
        _require(at==call and records[call][0]==0xe8 and _branch(records[call],call)==row['physicalTargetRva'],
                 'ai-context-physical-call','same preserved MethodInfo reaches actual physical call',row)
        if role in('modeLookup','behaviorLookup','behaviorItem'):
            anchor=contract['anchors'][{'modeLookup':'modeLookup','behaviorLookup':'enterLookup','behaviorItem':'enterItem'}[role]]
            _require(anchor['rva']<=ctx['instructionRva']<call<anchor['rva']+len(bytes.fromhex(anchor['hex'])),
                     'ai-context-semantic-site','specific lookup/item consumer block',row)
        if role=='callbackItem':_require(call+5==contract['anchors']['callbackFlag']['rva'],
            'ai-context-semantic-site','actual callback completion item reaches finish flag test',row)
    off=lambda owner,name:fields[owner+'::'+name]['offset']
    operands=contract['operandDeclarations']
    def imm8(value):
        _require(type(value)is int and 0<=value<128,'ai-operand-imm8','nonnegative reviewed small displacement',value)
        return bytes([value])
    # Separate static reads before comparison, at switch request and after it.
    reads={row['role']:row for row in contract['tagReads']};expected_reads={a+b:('s_castSkillTag'if b=='Cast'else's_plungingAttackTag')
        for a in('compare','request','stored')for b in('Cast','Plunge')}
    _require(set(reads)==set(expected_reads),'ai-static-read-coverage',list(expected_reads),list(reads))
    for role,row in reads.items():
        ctx=row['typeContext'];_require(derive_typed_usage_context(image,ctx['instructionRva'],label=LABEL)==ctx
            and ctx['typeName']==BRAIN and ctx['tag']==1 and row['field']==BRAIN+'::'+expected_reads[role],
            'ai-static-read-owner',BRAIN,row)
        raw=records[row['readRva']];field=fields[row['field']]
        _require(field['static']is True and field['valueType']=='Beyond.Gameplay.Core.GameplayTag'
            and raw[:2]in(bytes.fromhex('8b5b'),bytes.fromhex('8b42'),bytes.fromhex('8b41'))and raw[2:]==bytes([field['offset']]),
            'ai-static-read-field',field,raw.hex())
        # Every source loads TypeInfo.static_fields before the selected field.
        _require(any(w['method']==CAST+'._ResetBehavior'and w['startRva']<=ctx['instructionRva']<row['readRva']<w['endRva']for w in windows.values()),
                 'ai-static-read-window','same contiguous ResetBehavior fragment',row)
        state={'rax':'selectedTypeInfo'};at=ctx['instructionRva']+len(records[ctx['instructionRva']])
        names=['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi']
        while at<row['readRva']:
            instruction=records[at]
            if instruction[:2]==bytes.fromhex('488b')and instruction[2]>>6!=3 and instruction[2]&7!=4:
                modrm=instruction[2];dest=names[(modrm>>3)&7];base=names[modrm&7]
                if modrm>>6==2 and instruction[3:]==struct.pack('<i',0xb8)and state.get(base)=='selectedTypeInfo':state[dest]='selectedStaticFields'
                else:state.pop(dest,None)
            else:
                changed=None if instruction[:1]==b'\xc6'or instruction[:2]==bytes.fromhex('48c7')else _written_register(instruction)
                if changed:state.pop(changed,None)
            at+=len(instruction)
        raw=records[at];_require(at==row['readRva']and state.get(names[raw[1]&7])=='selectedStaticFields',
                 'ai-static-fields-register-continuity','actual selected TypeInfo->static_fields->field base',state)
    loc=operands['tagCompare']
    compare=(bytes.fromhex('397c24')+imm8(loc['currentTagStack'])+bytes.fromhex('0f94c0488b5c24')+imm8(loc['savedRbxReturn'])
        +bytes.fromhex('84c00f94c04883c4')+imm8(loc['stackAllocation'])+bytes.fromhex('5fc3'))
    _require(anchors['tagUnequal']==compare,
             'ai-compare-program','CMP32; SETE; TEST; SETE; return',anchors['tagUnequal'].hex())
    cmpall=b''.join(bytes.fromhex(r['hex'])for r in contract['programs']['tagCompare'])
    _require(bytes.fromhex('8bfa8bd9')in cmpall and bytes.fromhex('895c24')+imm8(loc['currentTagStack'])in cmpall
        and cmpall.startswith(bytes.fromhex('48895c24')+imm8(loc['savedRbxEntry'])+bytes.fromhex('574883ec')+imm8(loc['stackAllocation']))
        and loc['savedRbxReturn']==loc['savedRbxEntry']+8+loc['stackAllocation'],
             'ai-compare-argument-preservation','EDX->EDI; ECX->EBX->same stack slot',cmpall.hex())
    _require(anchors['resetSelect'].startswith(bytes.fromhex('8bb5')+struct.pack('<i',off(CAST,'m_curBehaviorTag'))
        +bytes.fromhex('8378')+bytes([off('Beyond.Gameplay.AI.CharacterSkillSystem+SkillData','castType')])+b'\x01')
        and bytes.fromhex('8bd38bce')in anchors['resetSelect'],
        'ai-reset-cast-selection','current tag, castType==1, selected tag comparator arguments',anchors['resetSelect'].hex())
    _require(anchors['resetNoSkill'].startswith(bytes.fromhex('4533c94533c033d2'))and anchors['resetNoSkill'][8]==0xe8,
             'ai-reset-null-data','ResetAIMode(false,null)',anchors['resetNoSkill'].hex())
    for role,callrole in [('resetRequest','resetToBrainCast'),('resetPlungeRequest','resetToBrainPlunge')]:
        raw=anchors[role];local=operands['resetNullable'];stack=local['stackSlot'];value=stack+local['valueOffset']
        _require(local['valueOffset']==4 and bytes.fromhex('48c74424')+imm8(stack)+bytes(4)+bytes.fromhex('c64424')+imm8(stack)+b'\x01'in raw
            and bytes.fromhex('894424')+imm8(value)in raw and raw.endswith(bytes.fromhex('488b5424')+imm8(stack)+bytes.fromhex('4533c0488bcb')+records[calls[callrole]['rva']]),
            'ai-reset-nullable-request','HasValue=true, independently read tag as payload, same brain receiver',raw.hex())
    store=operands['resetNullable']['currentTagStoreRva']
    _require(records[store]==bytes.fromhex('8985')+struct.pack('<i',off(CAST,'m_curBehaviorTag'))
        and anchors['resetPlungeStore'][-5]==0xe9 and _branch(anchors['resetPlungeStore'][-5:],
            contract['anchors']['resetPlungeStore']['rva']+len(anchors['resetPlungeStore'])-5)
            ==store,
        'ai-reset-postcall-store','both independently read selected tags share actual named field store',anchors['resetPlungeStore'].hex())
    slot=contract['conditionalSlots']['selectedClosedModeGraphOffset']
    raw=anchors['brainForward'];start=contract['anchors']['brainForward']['rva'];alloc=operands['brainForward']['stackAllocation'];ret=operands['brainForward']['returnRva']
    _require(raw[:7]==bytes.fromhex('488b41')+imm8(off(BRAIN,'m_curMode'))+bytes.fromhex('4885c0')
        and raw[7]==0x74 and _branch(raw[7:9],start+7)==ret
        and raw[9:16]==bytes.fromhex('488b48')+imm8(slot)+bytes.fromhex('4885c9')
        and raw[16]==0x74 and _branch(raw[16:18],start+16)==ret
        and raw[18:29]==bytes.fromhex('4533c941b0014883c4')+imm8(alloc)+b'\xe9'
        and records[ret]==bytes.fromhex('4883c4')+imm8(alloc)and records[ret+4]==b'\xc3',
        'ai-brain-forward-program','same Nullable RDX preserved, force=true, both null checks return',raw.hex())
    raw=anchors['enterLookup'];_require(raw.startswith(bytes.fromhex('84db0f84'))and bytes.fromhex('488b4f')+bytes([off(GRAPH,'m_behaviors')])in raw
        and bytes.fromhex('4c8d47')+bytes([off(GRAPH,'m_curBehaviors')])in raw and raw[-4:-2]==bytes.fromhex('84c0')
        and raw[-2]==0x74 and _branch(raw[-2:],contract['anchors']['enterLookup']['rva']+len(raw)-2)==contract['anchors']['enterStore']['rva'],
        'ai-enter-lookup-program','present Nullable, actual map receiver/out current list, false skips entry',raw.hex())
    raw=anchors['enterItem'];_require(raw[-15:-2]==bytes.fromhex('33d2488bc8')+records[calls['graphToBehaviorEnter']['rva']]+bytes.fromhex('41ffc6')
        and raw[-2]==0xeb and _branch(raw[-2:],contract['anchors']['enterItem']['rva']+len(raw)-2)==operands['enterNext']['iterationStartRva'],
        'ai-enter-item-dispatch','same selected item RAX->RCX Enter; ascending index',raw.hex())
    _require(bytes.fromhex('48895f')+bytes([off(GRAPH,'m_curBehaviorType')])in anchors['enterStore']
        and bytes.fromhex('4883bf')+struct.pack('<i',off(GRAPH,'finishAction'))+b'\0'in anchors['enterStore'],
        'ai-enter-tag-then-callback','store Nullable then test actual finishAction',anchors['enterStore'].hex())
    raw=anchors['callbackFlag'];_require(bytes.fromhex('8078')+bytes([off(BEHAVIOR,'m_isFinish')])+b'\0'in raw
        and bytes.fromhex('0f84')in raw,'ai-callback-finish-field','reached item m_isFinish false returns',raw.hex())
    callback=off(GRAPH,'finishAction');raw=anchors['callbackInvoke']
    expected=(bytes.fromhex('488b8f')+struct.pack('<i',callback)+bytes.fromhex('4885c974')+raw[11:12]+bytes.fromhex('488b41')+bytes([off('System.Delegate','invoke_impl')])
        +bytes.fromhex('4c8b49')+bytes([off('System.Delegate','method')])+bytes.fromhex('488b49')+bytes([off('System.Delegate','method_code')])
        +bytes.fromhex('4c8b47')+bytes([off(GRAPH,'m_curBehaviorType')])+bytes.fromhex('488b57')+bytes([off(GRAPH,'m_entity')])+bytes.fromhex('ffd0')
        +bytes.fromhex('488d8f')+struct.pack('<i',callback)+bytes.fromhex('48c787')+struct.pack('<i',callback)+bytes(4))
    _require(raw.startswith(expected),'ai-callback-invoke-and-clear','reread callback; named invoke_impl/method/method_code and graph args; clear after normal result or null',raw.hex())
    nodes=contract['flowNodes'];edge_rules={'dataPresent':('resetSelect','notEqual'),'castTypeOne':('plungeSelect','equal'),
        'sameCastTag':('resetReturn','equal'),'samePlungeTag':('resetReturn','equal'),'tagAbsent':('enterTagStore','equal'),
        'lookupFalse':('enterTagStore','equal'),'callbackInitiallyPresent':('callbackStart','notEqual'),
        'unfinished':('enterReturn','equal'),'callbackRereadNull':('callbackClear','equal')}
    edges={r['role']:r for r in contract['flowEdges']}
    _require(set(edges)==set(edge_rules)and len(edges)==len(contract['flowEdges']),'ai-edge-coverage','all published short circuits',list(edges))
    for role,(target,condition)in edge_rules.items():
        row=edges[role];raw=records[row['rva']];opcode=raw[0]if len(raw)==2 else raw[1]-0x10
        _require(row['target']==target and opcode==({'equal':0x74,'notEqual':0x75}[condition])
            and _branch(raw,row['rva'])==nodes[target],'ai-edge-control',(role,target,condition),row)
    _require(nodes['enterTagStore']==contract['anchors']['enterStore']['rva']and nodes['resetSelect']==contract['anchors']['resetSelect']['rva']
        and nodes['resetReturn']==operands['resetNullable']['ordinaryReturnRva']and nodes['enterReturn']==operands['enterNext']['ordinaryReturnRva']
        and records[nodes['resetReturn']][:4]==bytes.fromhex('488b5c24')and records[nodes['enterReturn']][:4]==bytes.fromhex('488b7424')
        and records[nodes['callbackClear']]==bytes.fromhex('488d8f')+struct.pack('<i',callback),
        'ai-edge-semantic-targets','actual tag store, return restoration and callback clear blocks',nodes)
    clear=contract['fieldEffects']['clearCurrentBehaviorsRva']
    _require(records[clear]==bytes.fromhex('48c747')+bytes([off(GRAPH,'m_curBehaviors')])+bytes(4)
        and records[contract['fieldEffects']['enterParameterSaveRva']]==bytes.fromhex('488bda')
        and nodes['enterTagStore']>clear and bindings['behaviorLookup']['context']['instructionRva']>clear,
        'ai-enter-clear-and-input-binding','original nullable RDX->RBX; named current list clear before lookup',contract['fieldEffects'])
    raw=anchors['modeLookup'];_require(raw[:8]==bytes.fromhex('488b4b')+bytes([off(BRAIN,'m_modeData')])+bytes.fromhex('488b6b')+bytes([off(BRAIN,'m_curMode')])
        and bytes.fromhex('4c8d43')+bytes([off(BRAIN,'m_curMode')])+bytes.fromhex('8bd7')in raw
        and raw.endswith(bytes.fromhex('33ff')),'ai-mode-lookup-fields','same mode dictionary and direct m_curMode out pointer; no result test',raw.hex())
    from scripts.game_data import skill_ai_mode_layout_native as layout_module
    linked,digest,path=mode_layout if mode_layout is not None else _read_mode_layout(contract)
    proof=layout_module.validate_skill_ai_mode_layout_image(image,linked);admitted=proof['rules']
    _require(admitted['closedModeGraphCarrierLayoutProved']is True
        and admitted['selectedWitness']=='Beyond.Gameplay.AI.CharacterAIMode'
        and admitted['graphCarrierOffset']==contract['conditionalSlots']['selectedClosedModeGraphOffset']
        and admitted['modeTypeCarrierOffset']==contract['conditionalSlots']['selectedClosedModeTypeOffset']
        and admitted['fullInitDataReceiverContinuityProved']is False
        and admitted['returnedGraphConcreteRuntimeTypeProved']is False and admitted['runtimeExecutionProved']is False,
        'ai-layout-admission','same selected closed mode carrier only',admitted)
    _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'ai-layout-contract-after','unchanged linked contract bytes','changed')
    return {'rules':json.loads(json.dumps(rules)),'facts':json.loads(json.dumps(contract['facts'])),
        'conditionalSlots':dict(contract['conditionalSlots']),'supportedModelKinds':['cast_graph_reset','brain_switch_behavior','graph_enter_requests','graph_finish_callback'],
        'linkedModeLayout':{'status':'validated','contract':str(path),'contractSha256':digest,'layoutOnly':True,
            'graphCarrierOffset':admitted['graphCarrierOffset'],'modeTypeCarrierOffset':admitted['modeTypeCarrierOffset'],
            'fullInitDataReceiverContinuityProved':False,'runtimeDynamicSelectionProved':False}}


def load_skill_ai_dispatch(contract_path:Path=CONTRACT_PATH,*,gameassembly:Path,metadata:Path):
    path=Path(contract_path);audit={'schema':AUDIT_SCHEMA,'status':'validation_failed','nativeInputs':{},'rules':{},'facts':[],
        'conditionalSlots':{},'supportedModelKinds':[],'linkedModeLayout':{},'failures':[],'contract':str(path)}
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL)
        audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary']);pins=contract['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        mode_layout=_read_mode_layout(contract)
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),contract,mode_layout)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','ai-native-after','unchanged selected pair',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'ai-contract-after','unchanged operation bytes','changed')
        _require(hashlib.sha256(mode_layout[2].read_bytes()).hexdigest().upper()==mode_layout[1],
                 'ai-layout-contract-after','unchanged linked contract operation bytes','changed')
        audit.update(result,status='validated',detail='',nativeInputs=dict(pins))
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:800],nativeInputs={},rules={},facts=[],conditionalSlots={},supportedModelKinds=[],linkedModeLayout={})
        audit['failures'].append({'validator':LABEL,'check':str(error).split(':',1)[0],'source':str(path),'detail':str(error)[:800]})
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in('reports','scratch','tmp')):parser.error('--output must stay under reports/, scratch/ or tmp/')
    audit=load_skill_ai_dispatch(args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps({k:audit[k]for k in('status','detail','failures')},indent=2));return 0 if audit['status']=='validated'else 1


if __name__=='__main__':raise SystemExit(main())
