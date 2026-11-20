"""Authenticate bounded original Skill/HitStop clock arithmetic.

These rules accept explicit branch inputs. They do not prove live virtual
selection, scheduler order, curve samples, slot merging or control recovery.
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
from scripts.game_data.skill_timing_runtime_native import _require, _validate_fields

SCHEMA='endfield.skill-hitstop-clock-native-contract.v3'
AUDIT_SCHEMA='endfield.skill-hitstop-clock-native-audit.v3'
CONTRACT_PATH=CONTRACTS_DIR/'skill_hitstop_clock_native.json'
LABEL='skillHitstopClock'


def _validate_initialization(contract,methods,fields,operands,calls,windows):
    """Finite ordinary register/stack programs; helper effects stay conditional."""
    declaration=contract['initialization'];inst='Beyond.Gameplay.Core.EntityTimeDilationInst'
    raw=lambda role:bytes.fromhex(operands[role]['hex'])
    def program(role,expected,wildcards=()):
        actual=bytearray(raw(role))
        for offset in wildcards:actual[offset:offset+4]=bytes(4)
        _require(bytes(actual)==bytes.fromhex(expected),'clock-initialization-program',role,bytes(actual).hex())
    program('startInitializationProlog','48895c241048896c2418564883ec60488b0500000000',[18])
    program('resetInitializationProlog','405741554883ec78488b0500000000',[11])
    program('startEntryBindings','488be90f29742450418bd80f28f3488bf2')
    program('startResetBindings','488b8424a00000000f28d6448b8c2490000000488bd648c744243800000000488bcf4889442430488b8424980000004889442428895c2420e800000000',[57])
    program('startRegisterBindings','440fb68424a80000004533c9488bd7488bcde800000000',[19])
    program('resetEntryBindings','4c8be90f29742460418bf90f28f2')
    owner=fields[inst+'::m_owner']['offset'];curve=fields[inst+'::m_scaleCurve']['offset']
    duration=fields[inst+'::m_duration']['offset'];elapsed=fields[inst+'::m_elapsedTime']['offset']
    program('resetOwnerBindings',('4c8b0500000000488d4c24504889b424a0000000e8000000000f10442450498d4d'
        +bytes([owner]).hex()+'410f1145'+bytes([owner]).hex()+'e800000000'),[3,21,40])
    program('resetInitialBindings','488b8424b8000000498d4d'+bytes([curve]).hex()+'33f6498945'
        +bytes([curve]).hex()+'f3410f1175'+bytes([duration]).hex()+'418975'+bytes([elapsed]).hex()+'e800000000',[29])
    program('registerEntryBindings','4c8bf9450fb6e0488bea')
    slot=methods[declaration['tickMethod']]['slot']
    program('registerInitialTickBindings','498b8f880000004885c90f84000000004c8b0500000000488bd5e8000000004885ed0f8400000000b9'
        +struct.pack('<I',slot).hex()+'0f57d2488bd5e800000000',[12,19,27,36,52])
    program('initialTickDispatchProgram','48895c2408574883ec300fb7d9488bfa488b0a0f297424200f28f2e800000000488b07488d4b144803c94c8b0cc84c8b44c808488d05000000004c3bc87431488d05000000004c3bc8743a488d05000000004c3bc874640f28ce488bcf41ffd1488b5c24400f287424204883c4305fc3',[28,54,66,78])
    _require(declaration['dispatchSlot']==slot and declaration['dispatchVtableBase']==20*2*8
        and declaration['dispatchVtableStride']==2*8 and declaration['ownerCarrierBytes']==16
        and declaration['resetFrameBytes']==136 and declaration['startFrameBytes']==104,
        'clock-initialization-abi','selected slot and decoded win64 register/stack carrier layout',declaration)
    # CALLs are contiguous endpoints of the semantic programs above, not an
    # address-neighbourhood join. Their rel32 targets were checked separately.
    for role,program_role in [('startToReset','startResetBindings'),('startToAdd','startRegisterBindings'),
                              ('addToInitialTickDispatch','registerInitialTickBindings')]:
        _require(calls[role]['rva']+5==operands[program_role]['rva']+len(raw(program_role)),
            'clock-initialization-call-endpoint',role,program_role)
    _require(operands['startResetBindings']['rva']+len(raw('startResetBindings'))==operands['startRegisterBindings']['rva'],
        'clock-initialization-contiguous-start','Reset returns immediately to same-instance registration arguments',None)
    for key,window in [('startMethod','startEntity'),('resetMethod','entityReset'),('registrationMethod','addEntity')]:
        _require(declaration[key]==windows[window]['method'],'clock-initialization-method',window,declaration[key])
    _require(declaration['tickMethod']==inst+'.OnTick','clock-initialization-tick-method',inst+'.OnTick',declaration['tickMethod'])
    for prolog,body in [('startInitializationProlog','startEntryBindings'),('resetInitializationProlog','resetEntryBindings')]:
        _require(operands[prolog]['rva']==windows[operands[prolog]['window']]['startRva'] and
            operands[prolog]['rva']+len(raw(prolog))==operands[body]['rva'],
            'clock-initialization-frame-entry',prolog,body)
    dispatch=raw('initialTickDispatchProgram');entry=operands['initialTickDispatchProgram']['rva']
    fast=[]
    for offset in declaration['fastTargetLeaOffsets']:
        _require(dispatch[offset:offset+3]==bytes.fromhex('488d05'),'clock-initialization-fast-lea','LEA target',offset)
        fast.append(entry+offset+7+struct.unpack_from('<i',dispatch,offset+3)[0])
    _require(methods[declaration['tickMethod']]['identity'][3] not in fast
        and declaration['defaultCallOffset']==93 and declaration['defaultReturnOffset']==96
        and dispatch[93:96]==bytes.fromhex('41ffd1'),'clock-initialization-default-target','selected Entity OnTick uses generic default branch',fast)
    _require(declaration['zeroElapsedRaw32']==declaration['initialDeltaRaw32']==0
        and declaration['helperNoninterferenceRequired'] is True
        and declaration['ownerObjectPtrConstructionSemanticsConditional'] is True
        and declaration['slotAndPriorityAcceptancePredicted'] is False
        and declaration['allocationPredicted'] is False and declaration['allPathsIncludingIFixProved'] is False,
        'clock-initialization-boundary','ordinary selected path with explicit helper/owner/slot conditions',declaration)
    expected={'bindingLevel':'conditional-original-initialization-path','elapsedZeroWriteProved':True,
        'durationInputStoreProved':True,'curveInputStoreProved':True,'ownerInputToCarrierConstructorProved':True,
        'sameInstanceResetToZeroDeltaTickProved':True,'initialElapsedRaw32':0,'initialDeltaRaw32':0,
        'requiresOriginalSuccessfulResetAndRegistration':True,'requiresHelperNoninterference':True,
        'ownerCarrierConstructionConditional':True,'slotPriorityAcceptancePredicted':False,
        'runtimeInitializationObservedByNativeProof':False}
    _require(contract['nativeRules']['entityInitialization']==expected,'clock-initialization-rule',expected,
        contract['nativeRules']['entityInitialization'])
    return dict(resetIdentity=methods[declaration['resetMethod']]['identity'],
        zeroElapsedStoreRva=operands['resetElapsed']['rva'],setupDispatchSlot=slot,
        setupCallerReturnRva=entry+declaration['defaultReturnOffset'],
        helperNoninterferenceRequired=True,ownerCarrierConstructionConditional=True)


def _validate(image,contract):
    context=NativeReferenceContext(image);methods={}
    for row in contract['methods']:
        identity=row['identity'];index=image.validate_method_row(identity,label=LABEL)
        _require(row['id']==identity[1]+'.'+identity[2],'clock-method-nominal',identity[1]+'.'+identity[2],row['id'])
        method=image.metadata.methods[index]
        actual={'returnType':context.type_name(method.return_type),'parameterTypes':[context.type_name(p.type_index)
            for p in image.metadata.parameters_for(method)],'slot':method.slot,'isStatic':bool(method.flags&0x10),
            'parameterNames':[image.metadata.string(p.name_index)for p in image.metadata.parameters_for(method)]}
        _require(actual=={key:row[key]for key in actual},'clock-method-signature',row,actual)
        _require(row['id']not in methods,'clock-method-duplicate','unique ids',row['id']);methods[row['id']]=row
    fields=_validate_fields(image,contract['fields'])
    for row in fields.values():context.field(row['type']+'::'+row['name'])
    windows={row['role']:row for row in contract['codeWindows']}
    _require(len(windows)==len(contract['codeWindows']),'clock-window-duplicate','unique roles',list(windows))
    for row in windows.values():
        _require(row['method'] is None or row['method'] in methods,'clock-window-method',list(methods),row['method'])
        _require(0<row['endRva']-row['startRva']<=0x10000,'clock-window-size','bounded positive bytes',row)
    image.check_windows(list(windows.values()),label=LABEL)
    operands={}
    def checked(row):
        raw=bytes.fromhex(row['hex']);window=windows[row['window']]
        _require(window['startRva']<=row['rva'] and row['rva']+len(raw)<=window['endRva'],
                 'clock-operand-window',window['role'],row['rva'])
        actual=image.pe.bytes_at_va(image.pe.image_base+row['rva'],len(raw))
        _require(actual==raw,'clock-operand-bytes',raw.hex(),actual.hex())
        return raw
    for row in contract['operands']:
        _require(row['role']not in operands,'clock-operand-duplicate','unique role',row['role'])
        raw=checked(row)
        if 'field'in row:
            field=fields[row['field']];at=row['displacementOffset']
            _require(0<=at<len(raw) and raw[at]==field['offset'],'clock-field-operand',field['offset'],raw.hex())
        if 'literalRva'in row:
            _require(len(raw)==8 and raw[:3]in (bytes.fromhex('f30f58'),bytes.fromhex('f30f10')),
                     'clock-literal-opcode','reviewed RIP ADDSS/MOVSS',raw.hex())
            target=row['rva']+8+struct.unpack_from('<i',raw,4)[0]
            _require(target==row['literalRva'],'clock-literal-target',row['literalRva'],target)
            literal=image.pe.bytes_at_va(image.pe.image_base+target,4)
            _require(literal.hex()==row['literalHex'] and struct.unpack('<f',literal)[0]==row['float32'],
                     'clock-literal-value',(row['literalHex'],row['float32']),literal.hex())
        operands[row['role']]=row
    expected_calls={
        'startToReset':('startEntity','Beyond.Gameplay.Core.EntityTimeDilationInst.Reset'),
        'startToAdd':('startEntity','Beyond.Gameplay.Core.TimeDilationManager._AddNewEntityTimeDilationInst'),
        'tickToClear':('entityTick','Beyond.Gameplay.Core.EntityTimeDilationInst._ClearTimeScaleHandle'),
        'stopToClear':('entityStop','Beyond.Gameplay.Core.EntityTimeDilationInst._ClearTimeScaleHandle'),
        'managerToStop':('managerTick','Beyond.Gameplay.Core.EntityTimeDilationInst.Stop'),
        'abilityToSkill':('abilitySkillCall','Beyond.Gameplay.Core.Skill.OnTick')}
    expected_helpers={'tickToNormalizer':('entityTick','normalizeHelper'),
                      'normalizerToClamp':('normalizeHelper','clampHelper'),
                      'addToInitialTickDispatch':('addEntity','initialTickDispatch')}
    calls={}
    for row in contract['calls']:
        role=row['role'];raw=checked(row)
        _require(role not in calls,'clock-call-duplicate','unique role',role)
        _require(len(raw)==5 and raw[0]in (0xe8,0xe9),'clock-call-opcode','CALL/JMP rel32',raw.hex())
        if role in expected_calls:
            owner,target=expected_calls[role]
            _require(row['window']==owner and row['targetMethod']==target
                     and row['targetIdentity']==methods[target]['identity'],
                     'clock-call-method-join',(owner,methods[target]['identity']),row)
            image.validate_method_row(row['targetIdentity'],label=LABEL);expected=row['targetIdentity'][3]
        else:
            _require(role in expected_helpers,'clock-call-role',list(expected_calls)+list(expected_helpers),role)
            owner,target=expected_helpers[role]
            _require(row['window']==owner and row['targetWindow']==target
                     and row['targetRva']==windows[target]['startRva'],'clock-helper-join',(owner,target),row)
            expected=row['targetRva']
        actual=row['rva']+5+struct.unpack_from('<i',raw,1)[0]
        _require(actual==expected,'clock-call-target',expected,actual);calls[role]=row
    _require(set(calls)==set(expected_calls)|set(expected_helpers),'clock-call-coverage',list(expected_calls)+list(expected_helpers),list(calls))
    raw=lambda role:bytes.fromhex(operands[role]['hex'])
    offset=lambda owner,name:fields[owner+'::'+name]['offset']
    timer='Beyond.Gameplay.PeriodicTimer';period,remaining,passed=[offset(timer,name)for name in ('m_periodTime','m_remainingTime','m_passedTime')]
    # Complete call-free supported Update leaf; offsets are the selected named fields.
    body=(bytes.fromhex('f30f1051')+bytes([remaining])+bytes.fromhex('0f57c0f30f5cd1f30f5849')+bytes([passed])
          +bytes.fromhex('0f2fc2f30f1149')+bytes([passed])+bytes.fromhex('f30f1151')+bytes([remaining])
          +bytes.fromhex('730332c0c38b41')+bytes([period])+bytes.fromhex('8941')+bytes([passed])
          +bytes.fromhex('b001c741')+bytes([remaining])+bytes.fromhex('00000000c3'))
    _require(raw('periodicBody')==body,'clock-periodic-program','named Single subtract/add then terminal overwrite',raw('periodicBody').hex())
    inst='Beyond.Gameplay.Core.EntityTimeDilationInst'
    for name in ('m_duration','m_elapsedTime'):
        _require(fields[inst+'::'+name]['ordinaryKind']==12,'clock-field-type','Single',fields[inst+'::'+name])
    _require(fields[inst+'::m_timeScaleHandle']['ordinaryKind']==9,'clock-handle-type','UInt32',fields[inst+'::m_timeScaleHandle'])
    duration,elapsed,handle=[offset(inst,name)for name in ('m_duration','m_elapsedTime','m_timeScaleHandle')]
    _require(raw('validityDurationRead')==bytes.fromhex('f30f1073')+bytes([duration])
             and raw('validityElapsedRead')==bytes.fromhex('f30f107b')+bytes([elapsed]),
             'clock-validity-field-bindings','threshold duration and elapsed source fields',None)
    valid=raw('validityArithmetic');addition=raw('validityEpsilon');at=valid.index(addition)+len(addition)
    _require(valid[at:at+15]==bytes.fromhex('0f2ff70f287c24200f287424307311')
             and bytes.fromhex('0f57c00f2f43')+bytes([duration])+bytes.fromhex('7708') in valid,
             'clock-validity-program','inclusive threshold, then negative-duration branch',valid.hex())
    true_at=operands['validityArithmetic']['rva']+len(valid)
    _require(image.pe.bytes_at_va(image.pe.image_base+true_at,8)==bytes.fromhex('b0014883c4405bc3'),
             'clock-validity-true-return','Boolean true leaf',true_at)
    _require(raw('handleNonzero')[:4]==bytes.fromhex('837b')+bytes([handle,0]),
             'clock-handle-required','nonzero UInt32 scale handle',raw('handleNonzero').hex())
    _require(raw('tickDivide')==bytes.fromhex('f3410f5ef8')
             and raw('maxCurve')==bytes.fromhex('0f57fff3410f5ff8'),
             'clock-single-divide-max','DIVSS oldElapsed/duration and MAXSS(+0,curveResult)',None)
    _require(raw('incrementElapsed')==bytes.fromhex('f30f5873')+bytes([elapsed])+bytes.fromhex('f30f1173')+bytes([elapsed]),
             'clock-elapsed-update','Single add delta and store elapsed',raw('incrementElapsed').hex())
    _require(operands['tickDivide']['rva']<operands['maxCurve']['rva']<operands['incrementElapsed']['rva'],
             'clock-update-order','evaluate old elapsed before increment',None)
    _require(raw('resetDuration')==bytes.fromhex('f3410f1175')+bytes([duration])
             and raw('resetElapsed')==bytes.fromhex('418975')+bytes([elapsed]),
             'clock-reset-fields','incoming duration store and zeroed elapsed field',None)
    _require(raw('clampComparisons')[:4]==bytes.fromhex('440f2fc7')
             and bytes.fromhex('440f2fc677430f2ff77718') in raw('clampComparisons')
             and operands['clampOne']['float32']==1.0
             and bytes.fromhex('0f57c90f28c6') in raw('normalizerZeroAndOne'),
             'clock-normalizer','Single compare-style clamp with +0 and +1 bounds',None)
    # The concrete Evaluate wrapper and inlined Entity caller use the same
    # unresolved ICall cache and exact API literal, not a guessed callee name.
    targets={}
    for role,prefix in [('entityCurveCache','488b05'),('evaluateCurveCache','488b05'),
                        ('entityCurveIcall','488d0d'),('evaluateCurveIcall','488d0d')]:
        row=operands[role];code=raw(role)
        _require(len(code)==7 and code[:3]==bytes.fromhex(prefix),'clock-icall-encoding',prefix,code.hex())
        target=row['rva']+7+struct.unpack_from('<i',code,3)[0]
        _require(target==row['targetRva'],'clock-icall-target',row['targetRva'],target);targets[role]=target
    _require(targets['entityCurveCache']==targets['evaluateCurveCache']
             and targets['entityCurveIcall']==targets['evaluateCurveIcall'],
             'clock-curve-icall-join','same concrete Evaluate cache and API literal',targets)
    literal=contract['curveIcallName'].encode()+b'\0'
    _require(contract['curveIcallName']=='UnityEngine.AnimationCurve::Evaluate(System.Single)'
             and image.pe.bytes_at_va(image.pe.image_base+targets['entityCurveIcall'],len(literal))==literal,
             'clock-curve-icall-name','selected Single Evaluate ICall',contract['curveIcallName'])
    # A distinct selected scale fragment is checked independently of the later
    # Skill call. No register/stack continuity is inferred across the gap.
    ignore_field='Beyond.TickOwnerInfoGroup::m_ignoreGlobalTimeScale'
    global_field='Beyond.TimeManager::m_timeScale'
    self_field='Beyond.TickOwnerInfoGroup::m_selfTimeScaleCache'
    _require(operands['abilityIgnoreGlobal']['field']==ignore_field
             and operands['abilityGlobalScale']['field']==global_field
             and operands['abilitySelfScaleMul']['field']==self_field,
             'clock-delta-field-binding','typed ignore-global/global/self fields',None)
    _require(fields[ignore_field]['ordinaryKind']==2
             and fields[global_field]['ordinaryKind']==fields[self_field]['ordinaryKind']==12,
             'clock-delta-field-types','Boolean and two Singles',None)
    _require(raw('abilityInputDelta')==bytes.fromhex('0f28f1')
             and methods['Beyond.Gameplay.Core.AbilitySystem.PreLateTick']['parameterNames']==['deltaTime'],
             'clock-delta-input-abi','first explicit float saved in XMM6',None)
    formula=raw('abilityDeltaFormula')
    expected_selection=(bytes.fromhex('3846')+bytes([fields[ignore_field]['offset']])
                        +bytes.fromhex('7406410f28fbeb04410f28fc'))
    _require(formula[9:24]==expected_selection
             and formula[-9:]==bytes.fromhex('f30f59fef30f597b')+bytes([fields[self_field]['offset']])
             and raw('abilityGlobalScale')==bytes.fromhex('f3440f1066')+bytes([fields[global_field]['offset']]),
             'clock-delta-scale-program','conditional select, MULSS input, then MULSS self cache',formula.hex())
    _require(formula[:5]==bytes.fromhex('f3440f101d'),'clock-delta-one-opcode','MOVSS XMM11,[RIP]',formula.hex())
    one_target=operands['abilityDeltaFormula']['rva']+9+struct.unpack_from('<i',formula,5)[0]
    _require(image.pe.bytes_at_va(image.pe.image_base+one_target,4)==struct.pack('<f',1.0),
             'clock-delta-one-literal','Single +1 for ignore-global branch',one_target)
    rules=contract['nativeRules'];epsilon=operands['validityEpsilon']
    _require(rules['entityValidity']['epsilonHex']==epsilon['literalHex']
             and rules['entityValidity']['epsilonFloat32']==epsilon['float32']
             and rules['entityValidity']['comparison']=='elapsed <= Single(duration + epsilon) OR duration < 0'
             and rules['entityValidity']['equalityRemainsValid'] is True,'clock-validity-rule','native inclusive epsilon predicate',rules['entityValidity'])
    _require(rules['periodicTimerUpdate']['terminalComparison']=='remainingAfter <= 0'
             and rules['periodicTimerUpdate']['terminalPassed']=='period'
             and rules['entityOnTick']['updateAfterCurveApply'] is True
             and rules['entityOnTick']['normalizedTime']=='clamp01(Single(oldElapsed / duration))'
             and rules['entityOnTick']['nonnegativeScaleInstruction']=='MAXSS(+0, curveResult)',
             'clock-arithmetic-rules','supported reviewed arithmetic programs',rules)
    expected_periodic={'arithmetic':'Single','remainingOperation':'remaining - delta','passedOperation':'passed + delta',
        'terminalComparison':'remainingAfter <= 0','terminalRemaining':0.0,'terminalPassed':'period','terminalReturn':True}
    _require(rules['periodicTimerUpdate']==expected_periodic,'clock-periodic-rule-binding',expected_periodic,rules['periodicTimerUpdate'])
    _require(rules['entityValidity']['ownerHandleValidRequired'] is True
             and rules['entityValidity']['scaleHandleType']=='uint32'
             and rules['entityValidity']['scaleHandleNonzeroRequired'] is True,
             'clock-validity-preconditions','explicit owner validity and UInt32 nonzero handle',rules['entityValidity'])
    _require(rules['entityOnTick']['elapsedOperation']=='Single(oldElapsed + effectiveDelta)'
             and rules['entityOnTick']['effectiveDelta']=='incomingDelta unless influencedByGlobal, then Single(incomingDelta * globalScale)'
             and rules['entityOnTick']['globalScaleReceiverOwnershipProved'] is False,
             'clock-entity-rule-binding','explicit conditional incoming delta arithmetic',rules['entityOnTick'])
    _require(rules['skillDurationDelta']['sourceParameter']=='Skill.OnTick.deltaTime'
             and rules['skillDurationDelta']['unscaledParameterUsedByDurationLeaf'] is False
             and rules['skillDurationDelta']['requiresDefaultTimerImplementation'] is True
             and rules['skillDurationDelta']['requiresNoEarlierDeltaSuppression'] is True
             and rules['skillDurationDelta']['startFrameSuppressionProved'] is False
             and bytes.fromhex('0f28f9') in raw('skillDeltaAliases')
             and bytes.fromhex('f30f5ccf') in raw('skillDurationUpdate'),
             'clock-skill-delta-binding','first named delta under unsuppressed default timer leaf',rules['skillDurationDelta'])
    _require(rules['lifecycle']['managerChecksValidityBeforeTick'] is True
             and rules['lifecycle']['invalidBranchCallsStop'] is True
             and rules['lifecycle']['runtimeVirtualDispatchObserved'] is False
             and rules['lifecycle']['newInstanceInitialZeroDeltaTickProved'] is True,
             'clock-lifecycle-boundary','compiled ordinary manager branch only, concrete dispatch remains conditional',rules['lifecycle'])
    fragment=rules['skillDeltaScaleFragment']
    _require(fragment=={
        'bindingLevel':'conditional-local-arithmetic-fragment','arithmetic':'Single',
        'inputParameter':'Beyond.Gameplay.Core.AbilitySystem.PreLateTick.deltaTime',
        'ignoreGlobalField':ignore_field,'globalScaleField':global_field,'selfScaleField':self_field,
        'afterGlobal':'Single((ignoreGlobal ? 1 : globalScale) * inputDelta)',
        'result':'Single(afterGlobal * selfScale)',
        'methodEntryToFragmentContinuityProved':False,'fragmentToSkillCallContinuityProved':False},
        'clock-delta-fragment-rule','checked local arithmetic with unproved continuity',fragment)
    _require(rules['entityOnTick']['bindingLevel']=='conditional-local-arithmetic-fragments'
             and rules['entityOnTick']['completeOnTickDataflowProved'] is False
             and rules['entityOnTick']['requiresValidOwnerForIncrement'] is True
             and rules['entityOnTick']['requiresSuccessfulScaleRequestPath'] is True
             and rules['entityOnTick']['actualScaleApplicationProved'] is False,
             'clock-entity-fragment-boundary','local arithmetic, no closed OnTick replay',rules['entityOnTick'])
    bindings=contract['modelBindings']
    expected_bindings={'periodic_timer_update':('periodicTimerUpdate','complete-original-leaf'),
        'time_dilation_instance_valid':('entityValidity','conditional-original-predicate'),
        'time_dilation_on_tick':('entityOnTick','conditional-local-arithmetic-fragments'),
        'skill_delta_scale_fragment':('skillDeltaScaleFragment','conditional-local-arithmetic-fragment'),
        'time_dilation_instance_initialization':('entityInitialization','conditional-original-initialization-path')}
    _require(set(bindings)==set(expected_bindings),'clock-model-coverage',list(expected_bindings),list(bindings))
    for kind,(rule,scope)in expected_bindings.items():
        binding=bindings[kind]
        _require(binding.get('nativeRule')==rule and binding.get('scope')==scope and rule in rules,
                 'clock-model-rule-binding',(kind,rule,scope),binding)
        if kind in ('time_dilation_on_tick','skill_delta_scale_fragment'):
            _require(binding.get('completeMethodDataflowProved') is False
                     and isinstance(binding.get('opaqueInputs'),list) and bool(binding['opaqueInputs']),
                     'clock-model-fragment-boundary','explicit opaque inputs and incomplete method dataflow',binding)
    _require(rules['originalPathOnly'] is True and rules['actualControlRecoveryProved'] is False
             and rules['runtimeExecutionProved'] is False
             and rules['schedulerOrderBetweenManagerAndSkillsProved'] is False
             and rules['skillDurationDelta']['upstreamRegisterAndStackContinuityProved'] is False
             and rules['durationStackContinuity']['proved'] is False,
             'clock-evidence-boundary','explicit conditional fragments, no complete recovery claim',rules)
    initialization=_validate_initialization(contract,methods,fields,operands,calls,windows)
    return {'initializationBindings':initialization,'nativeRules':json.loads(json.dumps(rules)),'modelBindings':json.loads(json.dumps(bindings)),
            'rows':[{'id':'periodicTimerUpdate','evidence':'direct','methodIdentity':methods[timer+'.Update']['identity']},
                    {'id':'entityValidity','evidence':'conditional','methodIdentity':methods[inst+'.get_isValid']['identity']},
                    {'id':'entityOnTick','evidence':'conditional','methodIdentity':methods[inst+'.OnTick']['identity']},
                    {'id':'skillDurationDeltaFragment','evidence':'conditional','methodIdentity':methods['Beyond.Gameplay.Core.Skill.OnTick']['identity']}],
            'supportedModelKinds':['periodic_timer_update','time_dilation_instance_valid','time_dilation_on_tick','skill_delta_scale_fragment',
                'time_dilation_instance_initialization']}


def load_skill_hitstop_clock(contract_path:Path=CONTRACT_PATH,*,gameassembly:Path,metadata:Path):
    path=Path(contract_path);audit={'schema':AUDIT_SCHEMA,'status':'validation_failed','rows':[],'nativeRules':{},
        'supportedModelKinds':[],'modelBindings':{},'initializationBindings':{},'nativeInputs':{},'failures':[],'contract':str(path)}
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL)
        audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary'])
        pins=contract['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
            gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','clock-native-after','unchanged selected pair',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'clock-contract-after','unchanged contract bytes','changed')
        audit.update(result,status='validated',detail='',nativeInputs=dict(pins))
    except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:800],rows=[],nativeRules={},supportedModelKinds=[],modelBindings={},initializationBindings={},nativeInputs={})
        audit['failures'].append({'validator':LABEL,'check':str(error).split(':',1)[0],'source':str(path),'detail':str(error)[:800]})
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in ('reports','scratch','tmp')):
        parser.error('--output must stay under reports/, scratch/ or tmp/')
    audit=load_skill_hitstop_clock(args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({key:audit[key]for key in ('status','detail','failures')},indent=2))
    return 0 if audit['status']=='validated'else 1


if __name__=='__main__':raise SystemExit(main())
