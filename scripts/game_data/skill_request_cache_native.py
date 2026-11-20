"""Authenticate selected original request replacement, cache selection and cleanup.

The returned rules require explicit provider results and normal helper returns.
They do not prove a cast, target reference counts or live iFix/config selection.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members
from scripts.game_data.skill_timing_runtime_native import _require, _validate_fields

SCHEMA='endfield.skill-request-cache-native-contract.v2'
AUDIT_SCHEMA='endfield.skill-request-cache-native-audit.v2'
CONTRACT_PATH=CONTRACTS_DIR/'skill_request_cache_native.json'
LABEL='skillRequestCache'
COMBO='Beyond.Gameplay.Core.AbilitySystem+ComboController'
REQUEST=COMBO+'+NextSkillRequest'
MODIFIER=COMBO+'+MappingModifier'
INPUT='Beyond.Gameplay.Core.SkillCastInputData'
VIEW='Beyond.Gameplay.Core.SkillCastInputView'
TARGET='Beyond.Gameplay.Core.TargetHandle'
CONFIG='Beyond.Gameplay.Core.BattleCommandMappingConfig'


def _branch(raw,rva):
    if len(raw)==2 and (0x70<=raw[0]<=0x7f or raw[0]==0xeb):
        return rva+2+int.from_bytes(raw[1:],'little',signed=True)
    if len(raw)==6 and raw[0]==0x0f and 0x80<=raw[1]<=0x8f:
        return rva+6+struct.unpack_from('<i',raw,2)[0]
    if len(raw)==5 and raw[0]in(0xe8,0xe9):return rva+5+struct.unpack_from('<i',raw,1)[0]
    raise ValueError('cache-branch-encoding: unsupported rel branch')


def _validate_rules(contract):
    rules=contract['rules']
    for key,value in {'originalPathOnly':True,'runtimeExecutionProved':False,'actualCastProved':False,
                      'completePlayerInputAcceptanceProved':False,'collectionAndPoolEffectsProved':False,
                      'targetLifetimeEffectsProved':False}.items():
        _require(rules.get(key)is value,'cache-rule-boundary',(key,value),rules.get(key))
    expected={
      'requestReplacement':{'scope':'conditional-selected-construction','requiresNonemptySelectedModifierSkillId':True,
        'oldInputDisposeRequestedBeforeReplacement':True,'oldInputDisposedOnlyIfBothNullableFlags':True,
        'remainingTime':'cacheSelectorReturnSingle','allowToCastNextSkill':False,'modifierInstId':'selectedModifier.instId',
        'nextSkillId':'selectedModifier.skillId','inputData':'CopyFrom(originalInputView) iff viewPresent',
        'oldNewSkillPriorityComparison':False,'returnsTrueAfterStore':True},
      'cacheTime':{'scope':'conditional-original-selector','arithmetic':'Single','default':'MappingModifier.cacheTime',
        'specialCommandValue':2,'movementModeValue':20,'movementOverride':'BattleCommandMappingConfig.attackCacheTimeInDash',
        'perfectDodgeRequiresCurrentSkill':True,'perfectDodgeOverride':'BattleCommandMappingConfig.attackCacheTimeInPerfectDodge',
        'precedence':['movementMode20','currentSkillAndPerfectDodge','modifier']},
      'inputCopy':{'scope':'conditional-selected-copy-requests','targetProviderReturn':'opaqueNonNullTargetHandle',
        'targetCopyRequestedWithOriginalViewTarget':True,'storesReturnedHandleAtTargetField':True,
        'targetHandleLifetimeEffectProved':False,'allFieldCopySemanticsProved':False},
      'inputDispose':{'scope':'conditional-original-local-clear','ifTargetNonNull':'request TargetHandle.Dispose',
        'then':'zero local targetHandle slot','otherFieldsCleared':False},
      'requestClear':{'scope':'conditional-original-local-clear','ifInputPresent':'request target Dispose on copied input',
        'then':'zero entire selected request Nullable','clearedBytes':128},
      'command2Mapping':{'scope':'conditional-original-command-selection','rawCommand':2,
        'commandEnum':'Beyond.Gameplay.PlayerCommandConfig+CmdType','commandName':'Attack','lookupKey':0,
        'lookupEnum':COMBO+'+BattleCommandType','lookupName':'Attack','receiverField':COMBO+'::m_realCommandMapping',
        'providedMethod':'System.Collections.Generic.CollectionExtensions.GetValueOrDefault',
        'physicalCallOutputIsSelectedModifier':True,'returnedModifierBytes':24,'newInputViewPresent':False,
        'collectionEffectsProved':False,'compiledTargetClosedDeclarationProved':False}}
    for key,value in expected.items():_require(rules[key]==value,'cache-rule-program',value,rules[key])
    facts={row['id']:row for row in contract['facts']}
    _require(len(facts)==len(contract['facts']) and set(facts)==set(expected),'cache-fact-coverage',list(expected),list(facts))
    for key in expected:
        _require(facts[key]['rule']==rules[key] and facts[key]['evidence']=='conditional' and facts[key]['boundary'],
                 'cache-fact-rule-join',rules[key],facts[key])
    _require(bool(contract['opaqueDependencies']),'cache-opaque-dependencies','explicit conditions',contract['opaqueDependencies'])
    return rules


def _check_construction(records,sections,layout,fields,locals_):
    """Propagate byte identities through the selected Win64 local copy paths.

    GC barrier-only intervals are explicit opaque normal-return/preservation
    conditions. This does not execute native code or infer target pool effects.
    """
    def symbolic(label,size):return [(label,index)for index in range(size)]
    def run(present):
        memory={};vectors={index:[('uninitialized',index,i)for i in range(16)]for index in range(8)}
        registers={0:0,1:0,2:0,3:locals_['outputObjectPointer'],4:0,5:locals_['framePointerBias'],6:0,7:0}
        def put(at,value):memory.update({at+i:byte for i,byte in enumerate(value)})
        def get(at,size):return [memory.get(at+i,('uninitializedMemory',at+i))for i in range(size)]
        identity=symbolic('selectedModifier.skillId',8);instance=symbolic('selectedModifier.instId',8)
        cache=symbolic('cacheSelectorReturnSingle',4);original=symbolic('originalInputView',layout['inputDataBytes'])
        copied=symbolic('CopyFromReturn',layout['inputDataBytes'])
        put(locals_['mapping'],identity+instance+[('modifierTail',i)for i in range(8)])
        put(locals_['inputPresent'],[1 if present else 0]);put(locals_['originalInputView'],original)
        vectors[7]=cache+[('xmm7High',i)for i in range(12)]
        def address(raw,at):
            modrm=raw[at];at+=1;mode=modrm>>6;reg=(modrm>>3)&7;base=modrm&7
            _require(mode in(0,1,2)and not(mode==0 and base==5),'cache-copy-memory','bounded base addressing',raw.hex())
            if base==4:
                _require(raw[at]==0x24,'cache-copy-sib','rsp without index',raw.hex());at+=1
            displacement=0
            if mode==1:displacement=int.from_bytes(raw[at:at+1],'little',signed=True);at+=1
            if mode==2:displacement=int.from_bytes(raw[at:at+4],'little',signed=True);at+=4
            _require(isinstance(registers[base],int),'cache-copy-base','known local/pointer address',registers[base])
            return reg,registers[base]+displacement,at
        def execute(row):
            raw=records[row];prefix=0;size=16
            if raw[0]in(0xf2,0xf3):size=8 if raw[0]==0xf2 else 4;prefix=1
            if raw[prefix:prefix+2]in(bytes.fromhex('0f10'),bytes.fromhex('0f11'),bytes.fromhex('0f28'),bytes.fromhex('0f29')):
                op=raw[prefix+1];modrm=raw[prefix+2]
                if modrm>>6==3:
                    _require(op in(0x10,0x28),'cache-copy-register-move','load direction',raw.hex())
                    vectors[(modrm>>3)&7]=vectors[modrm&7][:];return
                reg,at,end=address(raw,prefix+2);_require(end==len(raw),'cache-copy-move-length',end,len(raw))
                if op in(0x10,0x28):vectors[reg]=get(at,size)+[0]*(16-size)
                else:put(at,vectors[reg][:size])
                return
            if raw[:2]==bytes.fromhex('0f57'):
                _require(raw[2]>>6==3 and (raw[2]>>3)&7==raw[2]&7,'cache-copy-xor','same-vector zero',raw.hex())
                vectors[raw[2]&7]=[0]*16;return
            if raw[:2]in(bytes.fromhex('488b'),bytes.fromhex('4889')) and raw[2]>>6!=3 and not(raw[2]>>6==0 and raw[2]&7==5):
                reg,at,end=address(raw,2);_require(end==len(raw),'cache-copy-gpr-length',end,len(raw))
                if raw[1]==0x8b:registers[reg]=get(at,8)
                else:put(at,registers[reg]if isinstance(registers[reg],list)else [0]*8)
                return
            if raw[:1]==b'\xc6':
                reg,at,end=address(raw,1);_require(reg==0 and len(raw)==end+1,'cache-copy-byte-store','imm8 local store',raw.hex())
                put(at,[raw[-1]]);return
            if raw==bytes.fromhex('33c0'):registers[0]=0;return
            # Only comparisons/branches, address setup, stack-vector restore and
            # GC configuration reads remain; no unrecognized vector/write op.
            _require(raw[:1]in(b'\x80',b'\x83',b'\x39',b'\x74',b'\x75',b'\xeb')or raw[:2]==b'\x0f\x84'
                or raw[:2]in(bytes.fromhex('488d'),bytes.fromhex('4c8d'),bytes.fromhex('4533'))
                or raw[:3]==bytes.fromhex('488b44')or raw[:2]==bytes.fromhex('4889'),
                'cache-copy-supported-instruction','reviewed local copy/control instruction',raw.hex())
        def section(role):
            start,end=sections[role];at=start
            while at<end:execute(at);at+=len(records[at])
            _require(at==end,'cache-copy-section-end',end,at)
        section('commonInit');section('scalars')
        if present:
            section('copyArguments')
            _require(get(locals_['copyArgument'],layout['inputDataBytes'])==original,'cache-copy-original-input','same original view to CopyFrom',get(locals_['copyArgument'],layout['inputDataBytes']))
            registers[0]=locals_['copiedInputPointer'];put(registers[0],copied);section('copyReturn');section('inputPresent')
        else:section('inputAbsent')
        section('nestedStore');section('outerCopy');section('outerStore')
        base=fields[COMBO+'::m_nextSkillRequest']['offset'];value=base+layout['outerValueOffset']
        offset=lambda name:fields[REQUEST+'::'+name]['offset']-layout['objectHeaderBytes']
        output=locals_['outputObjectPointer']
        _require(get(output+base,1)==[1]and get(output+value+offset('nextSkillId'),8)==identity
            and get(output+value+offset('remainingTime'),4)==cache
            and get(output+value+offset('allowToCastNextSkill'),1)==[0]
            and get(output+value+offset('modifierInstId'),8)==instance,
            'cache-construction-scalar-propagation','named selected modifier/cache values reach actual output fields',get(output+base,32))
        nested=output+value+offset('skillCastInputData')
        _require(get(nested,1)==[1 if present else 0]
            and get(nested+layout['inputValueOffset'],layout['inputDataBytes'])==(copied if present else[0]*layout['inputDataBytes']),
            'cache-construction-input-propagation','complete returned input value or zero absent input',get(nested,96))
    run(False);run(True)


def _validate_declarations(image,contract):
    context=NativeReferenceContext(image);methods={}
    for row in contract['methods']:
        identity=row['identity'];index=image.validate_method_row(identity,label=LABEL);method=image.metadata.methods[index]
        _require(row['id']==identity[1]+'.'+identity[2] and row['id']not in methods,'cache-method-nominal','unique owner.method',row)
        actual={'returnType':context.type_name(method.return_type),'parameters':[{'name':image.metadata.string(p.name_index),
            'type':context.type_name(p.type_index)}for p in image.metadata.parameters_for(method)],'slot':method.slot,'isStatic':bool(method.flags&16)}
        _require(actual=={key:row[key]for key in actual},'cache-method-signature',row,actual);methods[row['id']]=row
    fields=_validate_fields(image,contract['fields'])
    for row in fields.values():
        td=image.named_types[row['type']];field=next(f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)==row['name'])
        _require(bool(context.field_attributes(field.type_index)&16)==row['static'],'cache-field-static',row['static'],row)
    field=lambda owner,name:fields[owner+'::'+name]
    _require(field(COMBO,'m_nextSkillRequest')['valueType']=='System.Nullable`1<'+REQUEST+'>'
        and field(REQUEST,'skillCastInputData')['valueType']=='System.Nullable`1<'+INPUT+'>',
        'cache-closed-nullable-arguments','selected actual request/input arguments',fields)
    _require(context.parent(COMBO)==COMBO.rsplit('+',1)[0]+'+SubFeature'
             and field(COMBO.rsplit('+',1)[0]+'+SubFeature','m_owner')['valueType']=='Beyond.Gameplay.Core.AbilitySystem',
             'cache-owner-chain','ComboController -> SubFeature.m_owner AbilitySystem',contract['parents'])
    # Open Nullable offsets are placeholders. Check declaration/type parameter, not their zero offsets.
    nullable=image.named_types['System.Nullable`1'];decl=[f for f in image.metadata.fields_for(nullable)if not context.field_attributes(f.type_index)&16]
    _require({image.metadata.string(f.name_index)for f in decl}=={'hasValue','value'},'cache-nullable-declaration','bool + VAR',decl)
    section=image.metadata.sections['genericContainers'];at=section.offset+nullable.generic_container_index*16
    _require(nullable.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16,'cache-nullable-container','bounded generic owner',at)
    owner,count,is_method,param=struct.unpack_from('<iiii',image.metadata.buf,at)
    _require((owner,count,is_method)==(nullable.index,1,0)and field('System.Nullable`1','value')['valueType']=='VAR['+str(param)+']',
             'cache-nullable-parameter','same sole class type parameter',(owner,count,is_method,param))
    layout=contract['layout'];expected_layout={'selectedNativeAbiOnly':True,'allNullableInstantiationsProved':False,
        'objectHeaderBytes':16,'closedValueAlignment':8,'inputDataBytes':88,'inputNullableBytes':96,'requestBytes':120,
        'requestNullableBytes':128,'outerHasValueOffset':0,'outerValueOffset':8,'inputHasValueOffset':0,'inputValueOffset':8}
    _require(layout==expected_layout,'cache-selected-layout','selected native copy geometry only',layout)
    sizes={}
    for row in contract['typeSizes']:
        td=image.named_types[row['type']];pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
        raw=image.pe.bytes_at_va(pointer,16)
        _require(raw.hex()==row['hex'] and context.is_value_type(row['type']) and row['valueType']is True
            and context.parent(row['type'])==row['parent']=='System.ValueType','cache-value-size',row,raw.hex())
        sizes[row['type']]=int.from_bytes(raw[:4],'little')-layout['objectHeaderBytes']
    _require(sizes=={INPUT:layout['inputDataBytes'],VIEW:layout['inputDataBytes'],REQUEST:layout['requestBytes']},
             'cache-size-geometry','named selected value extents',sizes)
    for owner,expected in [(REQUEST,{'nextSkillId':16,'remainingTime':24,'allowToCastNextSkill':28,'modifierInstId':32,'skillCastInputData':40}),
                           (INPUT,{'skillId':16,'targetHandle':24}), (VIEW,{'skillId':16,'targetHandleView':24}),
                           (MODIFIER,{'skillId':16,'instId':24,'cacheTime':36})]:
        _require(all(field(owner,name)['offset']==offset for name,offset in expected.items()),
                 'cache-value-field-geometry',(owner,expected),[(x['name'],x['offset'])for x in fields.values()if x['type']==owner])
    return methods,fields


def _validate_command_declarations(image,contract):
    entry=contract['command2Entry'];context=NativeReferenceContext(image);usage=entry['typedContext']
    actual=derive_typed_usage_context(image,usage['instructionRva'],label=LABEL)
    _require(actual==usage and usage['tag']==6 and usage['typeName']=='System.Collections.Generic.CollectionExtensions'
        and usage['methodName']=='GetValueOrDefault'and usage['classArguments']==[]
        and usage['methodArguments']==[COMBO+'+BattleCommandType',MODIFIER],
        'cache-command-methodinfo-context','same selected closed enum/value MethodSpec',actual)
    row=entry['genericDeclaration'];method=image.metadata.methods[row['metadataIndex']]
    actual={'metadataIndex':method.index,'type':image.metadata.type_full_name(image.metadata.types[method.declaring_type]),
        'method':image.metadata.string(method.name_index),'returnType':context.type_name(method.return_type),
        'parameters':[{'name':image.metadata.string(p.name_index),'type':context.type_name(p.type_index)}
            for p in image.metadata.parameters_for(method)],'isStatic':bool(method.flags&16)}
    _require(actual==row and row['metadataIndex']==usage['methodSpec'][0]and row['type']==usage['typeName']
        and row['method']==usage['methodName']and row['isStatic']is True and len(row['parameters'])==2,
        'cache-command-methodinfo-declaration','same current generic method declaration',actual)
    key=row['parameters'][1]['type'];value=row['returnType']
    _require(key.startswith('MVAR[')and value.startswith('MVAR[')and key!=value
        and row['parameters'][0]['type']=='System.Collections.Generic.IReadOnlyDictionary`2<'+key+','+value+'>',
        'cache-command-generic-signature','TValue GetValueOrDefault<TKey,TValue>(IReadOnlyDictionary<TKey,TValue>,TKey)',row)
    rules=contract['rules']['command2Mapping'];enums={r['type']:r for r in entry['enums']}
    _require(set(enums)=={rules['commandEnum'],rules['lookupEnum']},'cache-command-enum-coverage','both nominal enums',list(enums))
    defaults=field_defaults(image.metadata)
    for owner,row in enums.items():
        _require(context.is_enum(owner),'cache-command-enum-type','selected System.Enum',owner)
        actual=native_enum_members(image.metadata,defaults,image.pe,image.registration,owner)
        _require(actual==row['members'],'cache-command-enum-members',row['members'],actual)
    for enum,name,value in [(rules['commandEnum'],rules['commandName'],rules['rawCommand']),
                            (rules['lookupEnum'],rules['lookupName'],rules['lookupKey'])]:
        matching=[r for r in enums[enum]['members']if r['name']==name]
        _require(len(matching)==1 and matching[0]['id']==value,'cache-command-enum-role',(enum,name,value),matching)


def _validate_command2_program(contract,program,fields):
    entry=contract['command2Entry'];sections=entry['sections'];roles={'initialize','discriminate','key','lookupSetup','returnCopy'}
    _require(set(sections)==roles,'cache-command-section-coverage',roles,set(sections))
    def span(role):
        start,end=sections[role];at=start;raw=b''
        while at<end:raw+=program[at];at+=len(program[at])
        _require(at==end,'cache-command-section-continuity',end,at);return raw
    initialize=span('initialize');discriminate=span('discriminate');key=span('key');setup=span('lookupSetup');returned=span('returnCopy')
    # EDX raw command 2: signed (cmd-1)>3 is false; cmd-1 !=0;
    # subtract 1 yields zero, so the second JE reaches the key-zero producer.
    prefix=bytes.fromhex('83f8030f8f');middle=bytes.fromhex('8d4aff85c90f84');tail=bytes.fromhex('83e9010f84')
    _require(discriminate[:5]==prefix and discriminate[9:16]==middle and discriminate[20:25]==tail
        and _branch(discriminate[23:29],sections['discriminate'][0]+23)==sections['key'][0]
        and key[:3]==bytes.fromhex('4533c0')and key[3]==0xeb
        and _branch(key[3:],sections['key'][0]+3)==sections['lookupSetup'][0],
        'cache-command2-selector-program','raw Attack 2 reaches R8D=0 then shared lookup setup',discriminate.hex())
    bias=contract['constructionLocals']['framePointerBias'];flag=contract['constructionLocals']['inputPresent']-bias
    _require(initialize.startswith(bytes.fromhex('0f57c0'))and bytes.fromhex('8d42ff')in initialize
        and bytes.fromhex('0f1145')+bytes([flag])in initialize,
        'cache-command2-no-input-view','zero XMM0 initializes original view nullable before cmd2 branch',initialize.hex())
    usage=entry['typedContext'];context_raw=bytes.fromhex(usage['instructionHex']);receiver=fields[COMBO+'::m_realCommandMapping']
    _require(receiver['valueType']=='System.Collections.Generic.Dictionary`2<'+COMBO+'+BattleCommandType,'+MODIFIER+'>'
        and receiver['static']is False and entry['returnedBytes']==24,
        'cache-command2-receiver-type','actual closed real map field and MappingModifier24',receiver)
    buffer=entry['resultBufferStack'];mapping=contract['constructionLocals']['mapping']
    expected_setup=context_raw+bytes.fromhex('488d4c24')+bytes([buffer])+bytes.fromhex('488b53')+bytes([receiver['offset']])
    _require(setup[:-5]==expected_setup and usage['instructionRva']==sections['lookupSetup'][0]
        and entry['callRva']==sections['lookupSetup'][1]-5 and setup[-5]==0xe8
        and _branch(setup[-5:],entry['callRva'])==entry['physicalTargetRva'],
        'cache-command2-lookup-setup','R9 closed MethodInfo, RCX result buffer, RDX real map, key preserved zero',setup.hex())
    expected_return=(bytes.fromhex('0f104c24')+bytes([buffer])+bytes.fromhex('f20f104424')+bytes([buffer+16])
        +bytes.fromhex('0f114c24')+bytes([mapping])+bytes.fromhex('f20f114424')+bytes([mapping+16]))
    _require(returned==expected_return and sections['lookupSetup'][1]==sections['returnCopy'][0]
        and sections['returnCopy'][1]==contract['anchors']['refreshAccept']['rva'],
        'cache-command2-return-to-construction','same complete physical output24 reaches selected modifier buffer/XMM1',returned.hex())
    # The construction interpreter's seeds are precisely this returned buffer;
    # no second selector/provider or input view is inserted between them.
    return dict(rule=contract['rules']['command2Mapping'],physicalTargetRva=entry['physicalTargetRva'],
                providedClosedMethodInfo=usage,collectionEffectsProved=False,compiledTargetClosedDeclarationProved=False)


def _validate(image,contract):
    rules=_validate_rules(contract);methods,fields=_validate_declarations(image,contract)
    _validate_command_declarations(image,contract)
    field=lambda owner,name:fields[owner+'::'+name]
    layout=contract['layout']
    windows={row['role']:row for row in contract['codeWindows']}
    _require(set(windows)=={'refresh','cache','cacheCold','copy','dispose','clear'},'cache-window-coverage','six bounded programs',list(windows))
    image.check_windows(list(windows.values()),label=LABEL);records={};programs={}
    for role,rows in contract['programs'].items():
        window=windows[role];at=window['startRva'];programs[role]={}
        for row in rows:
            raw=bytes.fromhex(row['hex'])
            _require(row['rva']==at and 0<len(raw)<=15,'cache-program-continuity',at,row)
            actual=image.pe.bytes_at_va(image.pe.image_base+at,len(raw))
            _require(actual==raw,'cache-program-bytes',raw.hex(),actual.hex())
            records[at]=raw;programs[role][at]=raw;at+=len(raw)
        _require(at==window['endRva'],'cache-program-end',window['endRva'],at)
        if window['method']is not None:_require(window['startRva']==methods[window['method']]['identity'][3],
            'cache-window-method-entry',methods[window['method']]['identity'],window)
    _require(set(programs)==set(windows),'cache-program-coverage',list(windows),list(programs))
    anchors={}
    for role,row in contract['anchors'].items():
        raw=bytes.fromhex(row['hex']);at=row['rva'];parts=[]
        while sum(map(len,parts))<len(raw):parts.append(records[at]);at+=len(parts[-1])
        _require(b''.join(parts)==raw,'cache-anchor-program-join',raw.hex(),b''.join(parts).hex());anchors[role]=raw
    calls={};expected_calls={
      'refreshCache':('refresh',COMBO+'._GetCacheTime'),'refreshDispose':('refresh',INPUT+'.Dispose'),
      'refreshCopy':('refresh',INPUT+'.CopyFrom'),'copyTarget':('copy',TARGET+'.CopyFrom'),
      'disposeTarget':('dispose',TARGET+'.Dispose'),'clearTarget':('clear',TARGET+'.Dispose'),
      'cacheMove':('cache','Beyond.Gameplay.Core.MovementComponent.get_moveMode'),
      'cachePerfect':('cache','Beyond.Gameplay.Core.AbilitySystem.get_inPerfectDodge')}
    for row in contract['calls']:
        role=row['role'];window,target=expected_calls[role];raw=programs[window][row['rva']]
        _require(role not in calls and row['targetMethod']==target and row['targetIdentity']==methods[target]['identity']
            and len(raw)==5 and raw[0]==0xe8 and _branch(raw,row['rva'])==methods[target]['identity'][3],
            'cache-call-typed-join',(window,target,methods[target]['identity']),row);calls[role]=row
    _require(set(calls)==set(expected_calls),'cache-call-coverage',list(expected_calls),list(calls))
    def off(owner,name):return field(owner,name)['offset']
    base=off(COMBO,'m_nextSkillRequest');header=layout['objectHeaderBytes'];value=base+layout['outerValueOffset']
    nested=value+off(REQUEST,'skillCastInputData')-header;input_value=nested+layout['inputValueOffset']
    target_slot=off(INPUT,'targetHandle')-header
    # Exact call-free local Dispose program, with named unboxed target slot and checked branch joins.
    raw=anchors['disposeOrdinary'];want=(bytes.fromhex('488b4b')+bytes([target_slot])+bytes.fromhex('4885c9751c488d4b')
        +bytes([target_slot])+bytes.fromhex('48c743')+bytes([target_slot])+bytes.fromhex('000000004883c4205be9'))
    _require(raw[:-4]==want,'cache-dispose-program','nonnull target request, then only local target=0',raw.hex())
    dispose_call=contract['anchors']['disposeCall']['rva'];ordinary=contract['anchors']['disposeOrdinary']['rva']
    _require(_branch(raw[7:9],ordinary+7)==dispose_call and anchors['disposeCall'][:2]==bytes.fromhex('33d2')
        and _branch(anchors['disposeCall'][-2:],dispose_call+7)==ordinary+9,
        'cache-dispose-control','nonnull branch/call returns to clear',anchors['disposeCall'].hex())
    # Whole selected Nullable clear: eight ordered stores, no anonymous generic offsets used.
    zero=bytes.fromhex('0f57c0')
    for offset in range(base,base+layout['requestNullableBytes'],16):
        zero+=bytes.fromhex('0f1143')+bytes([offset]) if offset<128 else bytes.fromhex('0f1183')+struct.pack('<i',offset)
    zero+=bytes.fromhex('4881c4b00000005bc3')
    _require(anchors['clearZero']==zero,'cache-clear-program','zero selected Nullable extent then return',anchors['clearZero'].hex())
    # Cache selector input is MappingModifier.cacheTime (high Single in loaded qword).
    expected=bytes.fromhex('0f29742450f2410f1070')+bytes([off(MODIFIER,'cacheTime')-header-4])+bytes.fromhex('0fc6f65583fa020f85')
    _require(anchors['cacheDefault'][:-4]==expected,'cache-default-program','cacheTime Single, cmd!=2 bypass',anchors['cacheDefault'].hex())
    _require(_branch(anchors['cacheDefault'][-6:],contract['anchors']['cacheDefault']['rva']+len(expected)-2)
        ==contract['anchors']['cacheReturn']['rva'],'cache-default-return','direct same xmm6 return',anchors['cacheDefault'].hex())
    _require(anchors['cacheReturn']==bytes.fromhex('0f28c60f287424504883c4605bc3'),
             'cache-return-program','selected Single transferred xmm6 to xmm0',anchors['cacheReturn'].hex())
    for role,name in [('cacheDashRead','attackCacheTimeInDash'),('cachePerfectRead','attackCacheTimeInPerfectDodge')]:
        raw=anchors[role];_require(raw[:5]==bytes.fromhex('f30f1070')+bytes([off(CONFIG,name)])and raw[5]==0xe9
            and _branch(raw[5:],contract['anchors'][role]['rva']+5)==contract['anchors']['cacheReturn']['rva'],
            'cache-override-return',(name,'same xmm6 return'),raw.hex())
    for row in contract['typedContexts']:
        _require(derive_typed_usage_context(image,row['instructionRva'],label=LABEL)==row
            and row['typeName']=='Beyond.Gameplay.GameInstance','cache-config-typeinfo',row,'different context')
    _require(len(contract['typedContexts'])==2,'cache-config-context-coverage','both override paths',contract['typedContexts'])
    # Join every cold config receiver to the actual named static/instance fields.
    manager=off('Beyond.Gameplay.GameInstance','dataManager');config=off('Beyond.Gameplay.DataManager','<battleCommandMappingConfig>k__BackingField')
    for row in contract['typedContexts']:
        seq=programs['cacheCold'];start=row['instructionRva'];end=next(a['rva']for key,a in contract['anchors'].items()
            if key==('cacheDashRead'if start==contract['typedContexts'][0]['instructionRva']else'cachePerfectRead'))
        raw=b''.join(v for k,v in seq.items()if start<=k<end)
        _require(bytes.fromhex('488b80b8000000488b80')+struct.pack('<i',manager)in raw
            and bytes.fromhex('488b80')+struct.pack('<i',config)in raw,'cache-config-field-chain','TypeInfo.static_fields.dataManager.config',raw.hex())
    # Continuous selector: owner -> Entity -> Movement; non-dash -> Entity -> Ability.
    cache=programs['cache'];joined=b''.join(cache.values());sub=COMBO.rsplit('+',1)[0]+'+SubFeature'
    _require(bytes.fromhex('488b43')+bytes([off(sub,'m_owner')])+bytes.fromhex('4885c00f84')in joined
        and bytes.fromhex('488b48')+bytes([off('Beyond.Gameplay.Core.BaseComponent','<entity>k__BackingField')])in joined
        and bytes.fromhex('488b89')+struct.pack('<i',off('Beyond.Gameplay.Core.Entity','<movementComponent>k__BackingField'))in joined
        and bytes.fromhex('488b80')+struct.pack('<i',off('Beyond.Gameplay.Core.Entity','<abilityCom>k__BackingField'))in joined
        and bytes.fromhex('4883b8')+struct.pack('<i',off('Beyond.Gameplay.Core.AbilitySystem','<curSkill>k__BackingField'))+b'\0'in joined,
        'cache-selector-receivers','typed owner/entity/movement/ability/current skill chain',joined.hex())
    for role,prefix,cold_index in [('cacheMove',bytes.fromhex('83f8140f84'),0),('cachePerfect',bytes.fromhex('84c00f85'),1)]:
        at=calls[role]['rva']+5;parts=[]
        while len(b''.join(parts))<len(prefix)+4:parts.append(cache[at]);at+=len(parts[-1])
        raw=b''.join(parts);start=calls[role]['rva']+5
        _require(raw.startswith(prefix) and _branch(raw[len(prefix)-2:],start+len(prefix)-2)
            ==contract['typedContexts'][cold_index]['instructionRva'],
            'cache-selector-branch',(role,'matched result -> selected override'),raw.hex())
    # Construction markers consume the returned Single, selected mapping words and original input flag.
    accept=anchors['refreshAccept'];_require(accept.startswith(bytes.fromhex('66480f7ec84885c00f84'))
        and bytes.fromhex('837810000f86')in accept and bytes.fromhex('f20f10442440')in accept
        and bytes.fromhex('0f294c2450')in accept and bytes.fromhex('0f28f8')in accept
        and bytes.fromhex('807b')+bytes([base])+bytes.fromhex('00')in accept,
        'cache-refresh-accept-program','nonempty selected id, same mapping copy/cache return/old outer flag',accept.hex())
    _require(anchors['refreshOldInput'][:4]==bytes.fromhex('807b')+bytes([nested])+bytes.fromhex('00')
        and anchors['requestScalars'].startswith(bytes.fromhex('807d7000488b442438'))
        and bytes.fromhex('f30f117c2478')in anchors['requestScalars']
        and bytes.fromhex('48894580c644247c00')in anchors['requestScalars'],
        'cache-request-scalar-dataflow','view flag, modifier.instId, cache Single, allow false',anchors['requestScalars'].hex())
    store=anchors['requestStore'];_require(bytes.fromhex('c645f0010f2845f00f1143')+bytes([base])in store
        and len(store)>70,'cache-outer-nullable-store','true flag + complete copied payload',store.hex())
    _require(anchors['copySourceTarget'][:9]==bytes.fromhex('488b559f4533c0488b')
        and anchors['copyStoreTarget']==bytes.fromhex('488977')+bytes([target_slot])
        and anchors['copyReturn'][:3]==bytes.fromhex('488bc7'),
        'cache-input-target-dataflow','original view target -> named copy request, provider handle -> output slot',anchors['copySourceTarget'].hex())
    _require(anchors['refreshReturn'].startswith(bytes.fromhex('b001eb0232c0')),'cache-refresh-return','true after store, false before construction',anchors['refreshReturn'].hex())
    sections=contract['constructionProgram']
    _require(set(sections)=={'commonInit','scalars','copyArguments','copyReturn','inputPresent','inputAbsent','nestedStore','outerCopy','outerStore'},
             'cache-construction-section-coverage','complete selected copy paths',list(sections))
    for role,(start,end)in sections.items():
        _require(start in programs['refresh'] and end>start and end<=windows['refresh']['endRva'],
                 'cache-construction-section-boundary','bounded refresh instruction boundary',(role,start,end))
    _require(sections['copyArguments'][1]==calls['refreshCopy']['rva']
        and sections['copyReturn'][0]==calls['refreshCopy']['rva']+5
        and sections['scalars'][1]==sections['copyArguments'][0]
        and sections['inputPresent'][1]==sections['inputAbsent'][0]
        and sections['inputAbsent'][1]==sections['nestedStore'][0]
        and sections['outerStore']==[contract['anchors']['requestStore']['rva'],
            contract['anchors']['requestStore']['rva']+len(anchors['requestStore'])],
        'cache-construction-section-joins','selected actual call/branch/store sequence',sections)
    for source,target in [('commonInit','scalars'),('copyReturn','inputPresent'),('nestedStore','outerCopy'),('outerCopy','outerStore')]:
        at=sections[source][1];raw=records[at]
        _require(raw[0]==0x74 and _branch(raw,at)==sections[target][0],
                 'cache-gc-preservation-branch',(source,target),raw.hex())
    scalar_branch=next((at,raw)for at,raw in programs['refresh'].items()if at+len(raw)==sections['scalars'][1])
    present_branch=next((at,raw)for at,raw in programs['refresh'].items()if at+len(raw)==sections['inputPresent'][1])
    _require(scalar_branch[1][:2]==bytes.fromhex('0f84')and _branch(scalar_branch[1],scalar_branch[0])==sections['inputAbsent'][0]
        and present_branch[1][0]==0xeb and _branch(present_branch[1],present_branch[0])==sections['nestedStore'][0],
        'cache-input-nullable-branch','same flag selects CopyFrom or all-zero absent input',(scalar_branch,present_branch))
    locals_=contract['constructionLocals']
    _require(set(locals_)=={'framePointerBias','mapping','inputPresent','originalInputView','copyArgument','copiedInputPointer','outputObjectPointer'}
        and all(type(value)is int and value>=0 for value in locals_.values())
        and locals_['inputPresent']+layout['inputValueOffset']==locals_['originalInputView']
        and locals_['outputObjectPointer']>0x1000 and locals_['copiedInputPointer']>locals_['outputObjectPointer']+0x1000,
        'cache-construction-local-geometry','explicit bounded distinct symbolic local/object addresses',locals_)
    # RBP bias is proved from the actual prologue LEA and subsequent allocation.
    prologue=list(programs['refresh'].values())[:6]
    _require(prologue[3][:4]==bytes.fromhex('488dac24')and prologue[4][:3]==bytes.fromhex('4881ec')
        and struct.unpack('<i',prologue[3][4:])[0]+struct.unpack('<i',prologue[4][3:])[0]==locals_['framePointerBias'],
        'cache-frame-pointer-bias','actual selected prologue arithmetic',prologue)
    _check_construction(records,sections,layout,fields,locals_)
    command2=_validate_command2_program(contract,programs['refresh'],fields)
    return {'rules':json.loads(json.dumps(rules)),'facts':json.loads(json.dumps(contract['facts'])),
            'layout':dict(layout),'opaqueDependencies':list(contract['opaqueDependencies']),'command2Binding':command2}


def load_skill_request_cache(contract_path:Path=CONTRACT_PATH,*,gameassembly:Path,metadata:Path):
    path=Path(contract_path);audit={'schema':AUDIT_SCHEMA,'status':'validation_failed','nativeInputs':{},'rules':{},'facts':[],
        'layout':{},'opaqueDependencies':[],'command2Binding':{},'failures':[],'contract':str(path)}
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL)
        audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary']);pins=contract['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','cache-native-after','unchanged selected pair',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'cache-contract-after','unchanged operation bytes','changed')
        audit.update(result,status='validated',detail='',nativeInputs=dict(pins))
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:800],nativeInputs={},rules={},facts=[],layout={},opaqueDependencies=[],command2Binding={})
        audit['failures'].append({'validator':LABEL,'check':str(error).split(':',1)[0],'source':str(path),'detail':str(error)[:800]})
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in('reports','scratch','tmp')):parser.error('--output must stay under reports/, scratch/ or tmp/')
    audit=load_skill_request_cache(args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({key:audit[key]for key in('status','detail','failures')},indent=2));return 0 if audit['status']=='validated'else 1


if __name__=='__main__':raise SystemExit(main())
