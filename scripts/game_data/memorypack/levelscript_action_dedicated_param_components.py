"""Dedicated Param wire sources and canonical reference joins.

Each selected wire owner re-proves its exact reviewed/native programs. Its
distinct constant grammar joins a fresh closed Param carrier, whole-reference
getter and ordinary canonical adapter. Enclosing requests/fields stay separate.
Quaternion and List<PosRot> delegate only to their separate finite source owner.
"""
import copy,json

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack.levelscript_condition_param_sources import PREFIX

SCHEMA = 'endfield.actionmap-dedicated-param-components.v1'
CAP_SCHEMA = 'endfield.actionmap-dedicated-param-capability.v1'
SPECS = {
    'System.Collections.Generic.List`1<ulong>': dict(kind='owned-uint64-list',elementWireBytes=8,countLimit=4096),
    **{'System.Collections.Generic.List`1<Beyond.Gameplay.Actions.'+name+'+EnvTalkStruct>':
        dict(contract='levelscript_envtalk_native.json',kind='owned-envtalk-value-list',countLimit=4096,
             childMemberCount=2,childPositiveWireBytes=9,fieldOrder=['envTalkId','odds'])
       for name in ('NpcAtmosphericOverrideEnvTalk','NpcOverrideEnvTalk','NpcProxyOverrideEnvTalk')},
    'System.Collections.Generic.List`1<Beyond.BlackboardKVPair>': dict(contract='levelscript_blackboard_native.json',
        kind='owned-blackboard-list',countLimit=4096,childMemberCount=4,childPositiveWireBytes=14,
        fieldOrder=['key','useString','valueFloat','valueString']),
    'System.Collections.Generic.List`1<bool>': dict(kind='owned-Boolean-list',countLimit=4096),
    'System.Collections.Generic.List`1<Beyond.LangKey>': dict(kind='owned-lang-key-list',countLimit=4096),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GlobalBuffId>': dict(kind='owned-global-buff-id-list',countLimit=4096),
    'Beyond.LangKey': dict(contract='levelscript_nominal_key_param_native.json',kind='lang-key-mc1',constantMemberCount=1,keyField='key',constantNullAdmitted=True,managedKeyBytes=16,nonserializedRawText=True),
    'Beyond.Gameplay.Core.BuffPtr': dict(kind='buff-pointer-record'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffPtr>': dict(kind='null-buff-list', collectionCounts=[-1], positiveElementsAdmitted=False),
    'Beyond.Gameplay.AI.Config.NpcBehaviorTag': dict(kind='npc-behavior-tag-raw4', constantWireBytes=4),
    'Beyond.Gameplay.ForbidSettings+ForbidPhaseItem': dict(kind='forbid-phase-record'),
    'Beyond.Gameplay.Core.EventArgsPtr': dict(contract='levelscript_event_args_param_native.json', kind='event-args-key-mc1', constantMemberCount=1, keyField='key', constantNullAdmitted=False),
    'Beyond.CameraBlendCurveKey': dict(contract='levelscript_curve_key_param_native.json', kind='curve-key-mc1', constantMemberCount=1, keyField='key', constantNullAdmitted=True),
    'Beyond.Gameplay.CameraShakeConfigPtr': dict(contract='levelscript_camera_shake_param_native.json', kind='camera-shake-key-mc1', constantMemberCount=1, keyField='key', constantNullAdmitted=True),
    'Beyond.Gameplay.Core.GameplayTag': dict(contract='levelscript_gameplay_tag_param_native.json', kind='gameplay-tag-raw4', constantWireBytes=4),
    'Beyond.Gameplay.Core.GlobalBuffId': dict(contract='levelscript_global_buff_id_param_native.json', kind='global-buff-id-mc1', constantMemberCount=1, keyField='id', constantNullAdmitted=True),
    'Beyond.Gameplay.View.CameraControllerBase': dict(contract='levelscript_camera_controller_param_native.json', kind='reference-null-only', constantMarker=255, positiveConstantAdmitted=False),
    'Beyond.Gameplay.CommonMaskBlendData': dict(contract='levelscript_mask_param_native.json', kind='own-mask-and-curve', constantMemberCount=6),
    'System.Collections.Generic.List`1<int>': dict(contract='levelscript_numeric_list_param_native.json', kind='owned-int32-list', elementWireBytes=4, countLimit=4096),
    'System.Collections.Generic.List`1<float>': dict(kind='owned-float32-list', elementWireBytes=4, countLimit=4096),
    'System.Collections.Generic.List`1<UnityEngine.Vector3>': dict(kind='owned-vector3-list', elementWireBytes=12, countLimit=4096),
    'UnityEngine.Quaternion': dict(kind='quaternion-raw16', constantWireBytes=16),
    'System.Collections.Generic.List`1<Beyond.PosRot>': dict(kind='posrot-list', countLimit=4096,
        elementMemberCount=2, nullElementMarker=255, elementPositiveWireBytes=25, elementDefaultBytes=24,
        fieldOrder=['eulerAngles','position']),
}


def need(check, condition):
    if not condition:
        raise ValueError('actionDedicatedParam.' + check)


def wire_specification(value):
    need('finite-own-constant-domain',value in SPECS)
    return copy.deepcopy({key:item for key,item in SPECS[value].items() if key!='contract'})


def _contract(name, pins, captures):
    path = CONTRACTS_DIR/name
    raw = path.read_bytes()
    fact = json.loads(raw)
    selected = fact.get('nativeInputs')
    need('exact-reviewed-selected-source', fact.get('status') == 'exact-current-build'
         and isinstance(selected, dict) and {'GameAssembly.dll','global-metadata.dat'} <= set(selected)
         and set(selected) <= {'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
         and all(value == pins.get(key) for key,value in selected.items()))
    captures[path] = raw
    return fact


def _wire(image, pins, value, captures):
    spec = SPECS[value]
    if value == 'System.Collections.Generic.List`1<ulong>':
        from scripts.game_data.memorypack import levelscript_positive_ulong_list_sources as owner
        actual = owner.derive(image,pins)
        owner.validate(actual,pins)
        return dict(actualSource=actual,completeOwnValueAndParentSourceRevalidated=True)
    from scripts.game_data.memorypack.levelscript_action_value_list_sources import TYPES as VALUE_LISTS,derive_wire as derive_value_list
    if value in VALUE_LISTS:return derive_value_list(image,pins,value_type=value)
    from scripts.game_data.memorypack.levelscript_action_buff_param_sources import TYPES as BUFF_TYPES,derive_wire as derive_buff
    if value in BUFF_TYPES:return derive_buff(image,pins,value_type=value)
    from scripts.game_data.memorypack.levelscript_action_numeric_vector_list_sources import TYPES as LIST_TYPES,derive_wire as derive_list
    if value in LIST_TYPES:return derive_list(image,pins,value_type=value)
    from scripts.game_data.memorypack.levelscript_action_nominal_param_sources import TYPES,derive_wire as derive_nominal
    if value in TYPES:return derive_nominal(image,pins,value_type=value)
    if value in ('UnityEngine.Quaternion','System.Collections.Generic.List`1<Beyond.PosRot>'):
        from scripts.game_data.memorypack.levelscript_action_additional_param_sources import derive_wire
        return derive_wire(image,pins,value_type=value)
    fact = _contract(spec['contract'], pins, captures)
    if spec['kind'] == 'owned-envtalk-value-list':
        from scripts.game_data import levelscript_envtalk_native as owner
        need('own-EnvTalk-list-reviewed-domain',fact['schema']==owner.SCHEMA
             and fact['codecKinds']==['Param<List<'+name+'.EnvTalkStruct>>' for name in
                ('NpcAtmosphericOverrideEnvTalk','NpcOverrideEnvTalk','NpcProxyOverrideEnvTalk')]
             and fact['layout']==dict(paramMemberCount=4,childMemberCount=2,childManagedBytes=16,
                childPositiveWireBytes=9,stringEncoding='int32-pool-index',nullChild=dict(envTalkId=None,odds=0))
             and any(row['typeName']==PREFIX+value+'>' for row in fact['declarations']))
        owner._validate_native(image,fact)
        return dict(reviewedSource=fact,completeOwnValueAndParentAndCanonicalSourceRevalidated=True)
    if value == 'System.Collections.Generic.List`1<Beyond.BlackboardKVPair>':
        from scripts.game_data import levelscript_blackboard_native as owner
        need('own-Blackboard-list-reviewed-domain',fact['schema']==owner.SCHEMA
            and fact['codecKinds']==['Param<List<BlackboardKVPair>>']
            and fact['layout']==dict(stringEncoding='int32-pool-index',paramMemberCount=4,
                childMemberCount=4,childPositiveWireBytes=14,nullableClassMarker=255,nullChild=None,
                collectionCount='signed-int32,-1 null',fields=[['key','pooled-string'],
                    ['useString','normalized-byte'],['valueFloat','raw-float32'],['valueString','pooled-string']]))
        owner._validate_native(image,fact)
        return dict(reviewedSource=fact,completeOwnValueAndParentAndCanonicalSourceRevalidated=True)
    if value == 'Beyond.LangKey':
        from scripts.game_data import levelscript_nominal_key_param_native as owner
        need('own-LangKey-reviewed-domain',fact['schema']==owner.SCHEMA and fact['codecKinds']==['Param<LangKey>']
             and fact['layout']['managedKeyBytes']==16 and fact['layout']['nonserializedRawText'] is True)
        owner._validate_native(image,fact)
        return dict(reviewedSource=fact,completeOwnValueAndParentAndCanonicalSourceRevalidated=True)
    if value == 'Beyond.Gameplay.Core.EventArgsPtr':
        from scripts.game_data import levelscript_event_args_param_native as owner
        from scripts.game_data.memorypack import event_args_param
        need('own-EventArgs-reviewed-domain', fact['schema'] == owner.SCHEMA and fact['valueType'] == value
             and fact['codecKind'] == owner.KIND)
        actual = event_args_param.derive(image, pins, fact['profile'])
        from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
        validate_claims(fact['proof'], actual, label='actionDedicatedParam.EventArgs.source')
        validate_claims(actual, fact['proof'], label='actionDedicatedParam.EventArgs.declaration')
        return dict(reviewedSource=fact, actualSource=actual)
    if value == 'Beyond.CameraBlendCurveKey':
        from scripts.game_data import levelscript_curve_key_param_native as owner
        need('own-curve-key-reviewed-domain', fact['schema'] == owner.SCHEMA
             and fact['layout'] == dict(stringEncoding='int32-pool-index',parentMemberCount=4,
                 childMemberCount=1,positiveChildWireBytes=5,defaultChildWireBytes=1,
                 managedValueBytes=8,bindings=['raw-int32 idRef','raw-int32 paramSource','pooled path']))
        owner._validate_native(image,fact)
        return dict(reviewedSource=fact, completeOwnedWindowsAndContextsRevalidated=True)
    if value == 'Beyond.Gameplay.CameraShakeConfigPtr':
        from scripts.game_data import levelscript_camera_shake_param_native as owner
        need('own-camera-shake-reviewed-domain', fact['schema'] == owner.SCHEMA)
        owner._validate_native(image,fact)
        return dict(reviewedSource=fact, completeOwnSourceRevalidated=True)
    if value == 'Beyond.Gameplay.Core.GameplayTag':
        from scripts.game_data import levelscript_gameplay_tag_param_native as owner
        from scripts.game_data.memorypack import scalar_param_native,pooled_source_helper
        fact = scalar_param_native.read_scalar_contract(CONTRACTS_DIR/spec['contract'],
            schema=owner.SCHEMA,type_name=value,codec_kind='Param<GameplayTag>')
        target = fact['parameter']['orderedReads'][-1]['readCall'][2]
        strings = pooled_source_helper.validate_on_image(image,image.pe.image_base+target,pins)
        actual = scalar_param_native._composition(image,fact,strings,owner.SOURCE_PROOF,'actionDedicatedParam.GameplayTag')
        need('own-raw4-GameplayTag', actual['codecKind'] == 'Param<GameplayTag>' and actual['rawSize'] == 4)
        return dict(reviewedSource=fact,actualSource=actual)
    if value == 'Beyond.Gameplay.Core.GlobalBuffId':
        from scripts.game_data.memorypack import pooled_global_buff_id_sources
        need('own-GlobalBuff-reviewed-domain', fact['schema'] == 'endfield.levelscript-global-buff-id-param-native.v1'
             and fact['codecKinds'] == ['Param<GlobalBuffId>'])
        actual = pooled_global_buff_id_sources.validate_components(image,fact)
        need('whole-owned-GlobalBuffId-Param', actual['status'] == 'proved-current-selected-managed8'
             and actual['runtimeSelectionProved'] is False and actual['wholeOwnerAdmitted'] is False)
        return dict(reviewedSource=fact,actualSource=actual)
    if value == 'Beyond.Gameplay.View.CameraControllerBase':
        from scripts.game_data.memorypack import reference_null_param
        from scripts.game_data import levelscript_camera_controller_param_native as owner
        need('own-camera-null-reviewed-domain', fact['schema'] == owner.SCHEMA and fact['valueType'] == value
             and fact['layout'] == dict(codecKind='Param<CameraControllerBase>',memberCount=4,
                                      constantMarker=255,stringEncoding='int32-pool-index'))
        key = _contract('levelscript_nominal_key_param_native.json',pins,captures)
        actual = reference_null_param.derive(image,pins,fact,key)
        need('same-own-null-source-proof', actual == fact['proof'])
        return dict(reviewedSource=fact,actualSource=actual)
    if value == 'Beyond.Gameplay.CommonMaskBlendData':
        from scripts.game_data.memorypack import levelscript_mask_curve_sources as owner
        actual = owner.derive(image,pins,count_limit=4096)
        need('own-mask-and-curve-component',actual['nativeInputs'] == pins
             and actual['capabilities'][owner.CAPABILITY]['typeName'] == PREFIX+value+'>')
        return dict(reviewedSource=fact,actualSource=actual)
    from scripts.game_data import levelscript_numeric_list_param_native as owner
    from scripts.game_data import levelscript_int_list_native as integers
    from scripts.game_data.memorypack import numeric_list_sources
    from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
    need('own-numeric-list-reviewed-domain',fact['schema'] == owner.SCHEMA)
    row, = [row for row in fact['components'] if row.get('elementType') == 'int']
    need('own-int32-list-Param-domain',row['codecKind'] == 'Param<List<int>>')
    dependency = _contract('levelscript_int_list_native.json',pins,captures)
    integers._validate_native(image,dependency)
    actual = numeric_list_sources.derive(image,pins,row,dependency)
    validate_claims(row['proof'],actual,label='actionDedicatedParam.IntList.source')
    validate_claims(actual,row['proof'],label='actionDedicatedParam.IntList.declaration')
    need('own-positive-int32-list-source',actual['child']['positiveCountAdmitted'] is True
         and actual['child']['wireCountBytes'] == 4 and actual['child']['wireElementBytes'] == 4)
    return dict(reviewedSource=fact,actualSource=actual,listSource=dependency)


def capability(value, wire, reference, reader):
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _capability
    from scripts.game_data.codecs.levelscript.current_action_dedicated_param import validate
    need('finite-own-wire-capability',value in SPECS)
    spec=wire_specification(value)
    width=spec.get('constantWireBytes')
    cap=_capability(value,spec['kind'],0,reader,reference['adapter'])
    cap.update(schema=CAP_SCHEMA,constantSpecification=spec,constantWireBytes=width,
        positiveWireBytes=width+13 if width is not None else None,
        constantSourceAdmitted=True,canonicalAdapterAdmitted=True,constantValueEvaluationAdmitted=False)
    from scripts.game_data.memorypack.levelscript_action_value_list_sources import TYPES as VALUE_LISTS
    if value in VALUE_LISTS:cap['constantCapability']=wire['constantCapability']
    if value=='Beyond.Gameplay.CommonMaskBlendData':
        from scripts.game_data.memorypack.levelscript_mask_curve_sources import CAPABILITY
        cap['constantCapability']=wire['actualSource']['capabilities'][CAPABILITY]
    elif value in ('UnityEngine.Quaternion','System.Collections.Generic.List`1<Beyond.PosRot>','Beyond.Gameplay.AI.Config.NpcBehaviorTag','Beyond.Gameplay.ForbidSettings+ForbidPhaseItem'):
        cap['constantCapability']=wire['constantCapability']
    elif value in ('System.Collections.Generic.List`1<float>','System.Collections.Generic.List`1<UnityEngine.Vector3>'):
        cap['constantCapability']=wire['constantCapability']
    elif value in ('Beyond.Gameplay.Core.BuffPtr','System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffPtr>'):
        cap['constantCapability']=wire['constantCapability']
    validate(cap)
    return cap


def _derive_one(image,pins,type_name,reader):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reference_join
    need('finite-dedicated-Param-selector',type(type_name) is str and type_name.startswith(PREFIX) and type_name.endswith('>'))
    value=type_name[len(PREFIX):-1]
    need('independent-wire-owner-exists',value in SPECS)
    _publication_gate(image,pins)
    captures={}
    wire=_wire(image,pins,value,captures)
    from scripts.game_data.memorypack.levelscript_action_buff_param_sources import TYPES as BUFF_TYPES
    reference=wire['canonicalReference']if value in BUFF_TYPES else _reference_join(image,pins,value)
    need('own-actual-whole-Param-reference',reference['closedCarrier']['type'] == type_name
         and reference['closedCarrier']['argumentTypes'] == [value])
    cap=capability(value,wire,reference,reader)
    need('all-source-contract-bookends',all(path.read_bytes() == raw for path,raw in captures.items()))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(typeName=type_name,valueType=value,
        status='validated-conditional-Param-child',capability=cap,
        proof=dict(wrapperSource=wire,**{key:item for key,item in reference.items() if key!='getterMethodDefinition'}),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,runtimeEvaluationAdmitted=False)))


def derive_many(image,pins,*,parameter_types):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader,CAP_PREFIX
    need('finite-distinct-dedicated-selection',type(parameter_types)is list and 0<len(parameter_types)<=len(SPECS)
         and len(set(parameter_types))==len(parameter_types)
         and all(type(n)is str and n.startswith(PREFIX) and n.endswith('>') and n[len(PREFIX):-1]in SPECS for n in parameter_types))
    _publication_gate(image,pins);reader=_reader(image,pins);owners=[];caps={}
    for name in parameter_types:
        try:
            owner=_derive_one(image,pins,name,reader)
            caps[CAP_PREFIX+name]=owner['capability']
        except(ValueError,KeyError,IndexError,TypeError)as error:
            owner=dict(typeName=name,status='pendingReview',reason=str(error)[:2200],parentFieldAdmitted=False,wholeOwnerAdmitted=False)
        owners.append(owner)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,referenceReader=reader,capabilities=caps,
        owners=owners,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
