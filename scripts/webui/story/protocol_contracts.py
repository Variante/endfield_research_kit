"""Shared validation of Story and Mission Pipeline protocol projections."""
import re

REGISTRY_SCHEMA = 'endfieldProtocolRegistryAudit.v29'
START_POLICY_SCHEMA = 'levelScriptStartPolicy.v2'
START_POLICY_CLASSIFICATION = 'same_with_active_calls_prestart_setter_in_active_runtime_case'


def levelscript_start_policy_failures(contract):
    def fail(gate,expected,actual):return [dict(gate=gate,expected=expected,actual=actual)]
    if (contract.get('validation') or {}).get('status')!='validated':
        return fail('upstreamStartPolicyValidation','validated',(contract.get('validation') or {}).get('status'))
    shape=dict(schema=contract.get('schema'),classification=contract.get('classification'),
        objectIdentityInputs=(contract.get('discoveryPattern') or {}).get('objectIdentityInputs'))
    expected=dict(schema=START_POLICY_SCHEMA,classification=START_POLICY_CLASSIFICATION,objectIdentityInputs=[])
    if shape!=expected:return fail('currentStartPolicyShape',expected,shape)
    proof=contract.get('ordinaryEntryProof') or {}
    required=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,computedGuardsProved=True,
        selectedBasesProved=True,incomingReceiverAndZeroProved=True,originalGetterFieldReturnsProved=True,exceptionalOrResumptionPathsProved=False)
    actual={key:proof.get(key) for key in required}
    if any(actual[key] is not value if type(value) is bool else actual[key]!=value for key,value in required.items()):
        return fail('ordinaryStartPolicyProofScope',required,actual)
    gate=contract.get('runtimeStateGate') or {}
    value=((contract.get('enumValues') or {}).get('Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState') or {}).get('Active')
    if (type(value) is not int or not -(1<<31)<=value<(1<<31) or gate.get('runtimeStateName')!='Active'
            or type(gate.get('runtimeStateValue')) is not int or gate.get('runtimeStateValue')!=value
            or type(gate.get('tableOrdinal')) is not int or gate['tableOrdinal']<0
            or not re.fullmatch(r'0x[0-9a-f]+',str(gate.get('caseTargetVa') or ''))):
        return fail('ordinaryRuntimeActiveCase',dict(runtimeStateName='Active',runtimeStateValue=value),gate)
    return []


ACTIVATION_CONTROL_SCHEMA = 'levelScriptActivationControl.v10'


def activation_control_projection_failures(contract):
    def mapping(value):return value if isinstance(value,dict) else {}
    failures=[]
    def fail(gate,expected,actual):failures.append(dict(gate=gate,expected=expected,actual=actual))
    if contract.get('schema')!=ACTIVATION_CONTROL_SCHEMA:fail('currentActivationShape',ACTIVATION_CONTROL_SCHEMA,contract.get('schema'))
    selector=mapping(contract.get('activationSelectorFlow'));proof=mapping(selector.get('ordinaryEntryProof'))
    required=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,computedGuardsProved=True,
        selectedBasesProved=True,incomingReceiverProved=True,originalGetterFieldReturnProved=True,exceptionalOrResumptionPathsProved=False)
    actual={key:proof.get(key) for key in required}
    if any(actual[key] is not value if type(value) is bool else actual[key]!=value for key,value in required.items()):
        fail('ordinaryActivationSelectorProofScope',required,actual)
    enum=mapping(mapping(selector.get('enumValues')).get('Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState'))
    gates=selector.get('runtimeCaseGates');names=('Inactive','PreActiveEndSendActiveState')
    if (not isinstance(gates,list) or len(gates)!=2 or any(not isinstance(row,dict) for row in gates)
            or any(row.get('runtimeStateName')!=name or type(enum.get(name)) is not int or row.get('runtimeStateValue')!=enum[name]
                or type(row.get('runtimeStateValue')) is not int or type(row.get('tableOrdinal')) is not int or row['tableOrdinal']<0
                or type(row.get('indexBias')) is not int or row['runtimeStateValue']-row['indexBias']!=row['tableOrdinal']
                or not re.fullmatch(r'0x[0-9a-f]+',str(row.get('caseTargetVa') or '')) for row,name in zip(gates,names))):
        fail('ordinaryActivationCaseGates',list(names),str(gates)[:700])
    for family,roles in [('typedStateTransfers',('incrementalState','snapshotState')),('typedRequestSenders',('active','start'))]:
        parent='publicStateSourceFlow' if family=='typedStateTransfers' else 'clientRequestFlow'
        items=mapping(mapping(contract.get(parent)).get(family))
        for role in roles:
            row=mapping(items.get(role));scope=mapping(row.get('ordinaryEntryProof'))
            required=dict(status='validated',scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,exceptionalOrResumptionPathsProved=False)
            actual=dict(status=row.get('status'),**{key:scope.get(key) for key in required if key!='status'})
            if family=='typedRequestSenders':
                required['incomingReceiverAndFactoryReturnBitsProved']=True;actual['incomingReceiverAndFactoryReturnBitsProved']=row.get('incomingReceiverAndFactoryReturnBitsProved')
            if any(actual[key] is not value if type(value) is bool else actual[key]!=value for key,value in required.items()):
                fail(family+':'+role,required,dict(actual,detail=str(items.get('detail') or '')[:700]))
    area=mapping(contract.get('activeAreaFlow'));caller=mapping(area.get('typedCallerProof'));scope=mapping(caller.get('ordinaryEntryProof'))
    required=dict(status='validated',scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,computedGuardsProved=True,selectedBasesProved=True,incomingReceiverProved=True,exceptionalOrResumptionPathsProved=False)
    actual=dict(status=caller.get('status'),**{key:scope.get(key) for key in required if key!='status'})
    if any(actual[key] is not value if type(value) is bool else actual[key]!=value for key,value in required.items()):fail('ordinaryActiveAreaCallerProof',required,dict(actual,detail=str(caller.get('detail') or '')[:700]))
    empty=mapping(area.get('typedEmptyExitProof'));required=dict(status='validated',incomingCollectionAndMethodInfoBitsProved=True,invokerSlotZeroAndArgumentBitsProved=True,low32ZeroTestEquivalent=True,selectedExitArgumentBitsProved=True,trueResultReturnsFalse=True)
    actual={key:empty.get(key) for key in required}
    if any(actual[key] is not value if type(value) is bool else actual[key]!=value for key,value in required.items()):fail('typedEmptyExitProof',required,dict(actual,detail=str(empty.get('detail') or '')[:700]))
    identity=mapping(area.get('calleeRuleIdentityProof'))
    from scripts.game_data.levelscript_area_rule_native import projection_valid
    if not projection_valid(identity,caller.get('optimizedCalleeVa')):
        fail('optimizedAreaRuleIdentity','validated current named target or fully scoped original-rule equivalence',identity)
    return failures


QUEST_ENABLE_SCHEMA = 'questEnableLifecycleApplication.v2'


def quest_enable_matrix_failures(routes, *, enable, previous, paused, enum):
    expected={(e,s,p) for e in (False,True) for s in enum.values() for p in (False,True)}
    actual=[tuple(row['values'].get(key) for key in (enable,previous,paused)) for row in routes]
    failures=[]
    if (set(actual)!=expected or len(actual)!=len(expected)
            or any(type(e) is not bool or type(p) is not bool or type(s) is not int for e,s,p in actual)):
        failures.append(dict(gate='completeEnablePreviousStatePauseMatrix',expected=sorted(expected),actual=actual[:24]))
    for row in routes:
        values=row['values']; state=values[previous] if values[enable] else enum['Disabled']
        method='DisableQuest' if state==enum['Disabled'] else (
            'PauseQuest' if values[paused] else 'StartQuest') if state==enum['Processing'] else None
        calls=row.get('reachableLifecycleCalls') or []
        if [call.get('method') for call in calls]!=([method] if method else []):
            failures.append(dict(gate='effectiveStateLifecycleRoute',expected=method,actual=dict(values=values,calls=calls[:4])))
        if any(call.get('samePacketIdentity') is not True for call in calls):
            failures.append(dict(gate='samePacketIdentity',expected=True,actual=dict(values=values,calls=calls[:4])))
    return failures


def quest_enable_application_failures(contract):
    """Check the current published projection, including empty lifecycle sets."""
    def fail(gate,expected,actual):return [dict(gate=gate,expected=expected,actual=actual)]
    if not isinstance(contract,dict) or contract.get('schema')!=QUEST_ENABLE_SCHEMA:
        return fail('contractSchema',QUEST_ENABLE_SCHEMA,contract.get('schema') if isinstance(contract,dict) else type(contract).__name__)
    if any(not isinstance(contract.get(key) or {},dict) for key in ('validation','message','controlRoles','runtimeControl','stateEnum')):
        return fail('contractSectionTypes','named object sections',list(contract))
    native_failures=(contract.get('validation') or {}).get('failures') or []
    if not isinstance(native_failures,list) or any(not isinstance(row,dict) for row in native_failures):
        return fail('nativeValidationFailures','structured failure rows',str(native_failures)[:700])
    if (contract.get('validation') or {}).get('status')!='validated' or (contract.get('validation') or {}).get('failures'):
        return (contract.get('validation') or {}).get('failures') or fail('nativeValidation','validated',(contract.get('validation') or {}).get('status'))
    message=contract.get('message') or {}; roles=contract.get('controlRoles') or {}
    enable,previous,effective=(roles.get(key) for key in ('enable','previousState','effectiveState'))
    runtime=contract.get('runtimeControl') or {}; paused=runtime.get('field')
    if any(not isinstance(message.get(key) or [],list) or any(not isinstance(name,str) for name in message[key])
           for key in ('fields','consumedControlFields','unreadControlFields','successorLikeFields') if message.get(key)):
        return fail('packetFieldLists','lists of wire member names',str(message)[:700])
    if (any(not isinstance(name,str) or not name for name in (enable,previous,effective,paused))
            or len({enable,previous,effective,paused})!=4 or runtime.get('type')!='bool'
            or not isinstance(message.get('identityField'),str) or not message['identityField'] or len(message.get('consumedControlFields') or [])!=2
            or set(message.get('consumedControlFields') or [])!={enable,previous} or len(message.get('fields') or [])!=3
            or set(message.get('fields') or [])!={message.get('identityField'),enable,previous}
            or message.get('unreadControlFields') or message.get('successorLikeFields')):
        return fail('enableStateControlRoles','complete identity, two packet controls, derived state and runtime Boolean',
                    dict(roles=roles,runtime=runtime,fields=message.get('fields'),controls=message.get('consumedControlFields')))
    members=(contract.get('stateEnum') or {}).get('values') or []
    if (not isinstance(members,list) or not 2<=len(members)<=128 or any(not isinstance(row,dict)
            or not isinstance(row.get('name'),str) or type(row.get('id')) is not int
            or not -(1<<31)<=row['id']<(1<<31) for row in members)):
        return fail('declaredStateEnum','bounded named Int32 states',str(members)[:700])
    enum={row['name']:row['id'] for row in members}
    if not {'Disabled','Processing'}<=enum.keys() or len(enum)!=len(members) or len(set(enum.values()))!=len(members):
        return fail('declaredStateEnum','unique state names/values including Disabled and Processing',enum)
    offsets=message.get('fieldOffsets') or {}
    if not isinstance(offsets,dict):return fail('previousStateFieldOffset','field-offset object',str(offsets)[:700])
    offset=offsets.get(previous)
    if not isinstance(offset,str) or not re.fullmatch(r'0x[0-9a-f]+',offset,re.I):
        return fail('previousStateFieldOffset','selected packet field offset',offset)
    origin='low32(param:msg+'+hex(int(offset,16))+')'
    selections=contract.get('stateSelections') or []
    expected={False:(hex(enum['Disabled']),origin),True:(origin,hex(enum['Disabled']))}
    if (not isinstance(selections,list) or len(selections)!=2 or any(not isinstance(row,dict) or type(row.get('isEnable')) is not bool for row in selections)
            or {row['isEnable']:(row.get('stateStoreOrigin'),row.get('disableQuestPreviousStateOrigin')) for row in selections}!=expected):
        return fail('conditionalStateSources','opposite typed store/prior-state sources for both enable values',str(selections)[:700])
    routes=contract.get('routes') or []
    if not isinstance(routes,list) or len(routes)>4*len(enum) or any(not isinstance(row,dict) or not isinstance(row.get('values'),dict)
            or any(key not in row['values'] for key in (enable,previous,effective,paused))
            or type(row['values'][enable]) is not bool or type(row['values'][previous]) is not int or type(row['values'][paused]) is not bool
            or not isinstance(row.get('reachableLifecycleCalls'),list) or any(not isinstance(call,dict) for call in row['reachableLifecycleCalls']) for row in routes):
        return fail('enableStateRouteShape','typed enable/previous/effective/pause values and bounded call lists',str(routes)[:700])
    failures=quest_enable_matrix_failures(routes,enable=enable,previous=previous,paused=paused,enum=enum)
    for row in routes:
        values=row['values']; expected_state=values[previous] if values[enable] else enum['Disabled']
        if type(values[effective]) is not int or values[effective]!=expected_state:
            failures.append(dict(gate='derivedEffectiveState',expected=expected_state,actual=values))
    return failures
