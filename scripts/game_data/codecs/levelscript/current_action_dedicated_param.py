"""Finite dedicated Param constants, preserving independent wire boundaries."""
from scripts.game_data.memorypack.levelscript_action_dedicated_param_components import SPECS,CAP_SCHEMA,wire_specification
from scripts.game_data.memorypack.levelscript_condition_param_sources import PREFIX


def validate(cap):
    if not isinstance(cap,dict)or cap.get('valueType')not in SPECS:
        raise ValueError('currentDedicatedParam.finite-own-constant-domain')
    value=cap['valueType'];spec=wire_specification(value)
    width=spec.get('constantWireBytes')
    expected=dict(schema=CAP_SCHEMA,typeName=PREFIX+value+'>',memberCount=4,
        fieldOrder=['constValue','idRef','paramSource','path'],constantWireKind=spec['kind'],
        constantSpecification=spec,constantWireBytes=width,
        positiveWireBytes=width+13 if width is not None else None,
        idRefWireKind='i32',paramSourceWireKind='i32',pathEncoding='int32-pool-index',nullWireBytes=1,
        nullOutput='reference-null',sourceReferenceKind=21,referenceOutputBytes=8)
    integers=['memberCount','nullWireBytes','sourceReferenceKind','referenceOutputBytes']
    if width is not None:integers+=['constantWireBytes','positiveWireBytes']
    if(any(cap.get(key)!=item for key,item in expected.items())or any(type(cap.get(k))is not int for k in integers)
       or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','wholeGrammarAdmitted','closedCarrierProved',
            'actualCallbackEqualsProvedChildRequired','constantSourceAdmitted','canonicalAdapterAdmitted'))
       or cap.get('liveFormatterSelectionObserved')is not False or cap.get('constantValueEvaluationAdmitted')is not False
       or type(cap.get('readerMethodDefinition'))is not int or cap['readerMethodDefinition']<0
       or any(type(cap.get(k))is not int or cap[k]<=0 for k in('sourceTargetRva','canonicalCallbackTargetRva'))):
        raise ValueError('currentDedicatedParam.exact-own-wire-and-canonical-source')
    # Dict equality does not distinguish Bool from int; the finite spec must.
    if any(type(cap['constantSpecification'][key])is not type(item)for key,item in spec.items()):
        raise ValueError('currentDedicatedParam.literal-constant-specification')
    from scripts.game_data.memorypack.levelscript_action_value_list_sources import TYPES as VALUE_LISTS,validate_constant as validate_list
    if value in VALUE_LISTS:validate_list(cap.get('constantCapability'),value)
    if value=='Beyond.Gameplay.CommonMaskBlendData':
        from scripts.game_data.codecs.levelscript.current_mask_curve_param import validate as mask
        mask(cap.get('constantCapability'))
    elif value in ('Beyond.Gameplay.AI.Config.NpcBehaviorTag','Beyond.Gameplay.ForbidSettings+ForbidPhaseItem'):
        from scripts.game_data.codecs.levelscript.current_action_nominal_param import validate_constant
        validate_constant(cap.get('constantCapability'),value)
    elif value in ('UnityEngine.Quaternion','System.Collections.Generic.List`1<Beyond.PosRot>'):
        from scripts.game_data.codecs.levelscript.current_action_additional_param import validate_constant
        validate_constant(cap.get('constantCapability'),value)
    elif value in ('System.Collections.Generic.List`1<float>','System.Collections.Generic.List`1<UnityEngine.Vector3>'):
        from scripts.game_data.memorypack.levelscript_action_numeric_vector_list_sources import validate_constant
        validate_constant(cap.get('constantCapability'),value)
    elif value in ('Beyond.Gameplay.Core.BuffPtr','System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffPtr>'):
        from scripts.game_data.memorypack.levelscript_action_buff_param_sources import validate_constant
        validate_constant(cap.get('constantCapability'),value)


def read(reader,field,cap):
    validate(cap);start=reader.offset;value=cap['valueType'];spec=cap['constantSpecification']
    if value=='Beyond.Gameplay.CommonMaskBlendData':
        from scripts.game_data.codecs.levelscript.current_mask_curve_param import read as mask
        result=mask(reader,field,cap['constantCapability'])
        if result is None:return None
        result['constValue']=result.pop('value');result.update(startOffset=start,endOffset=reader.offset,typeName=cap['typeName'])
        return result
    marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    if marker!=4:raise ValueError(field+':dedicated-Param-member-count')
    raw=None;was_null=None
    if spec['kind']=='gameplay-tag-raw4':
        at=reader.offset;constant=reader.number('<i',field+'.constValue');raw=bytes(reader.data[at:reader.offset]).hex().upper()
    elif spec['kind'] in ('npc-behavior-tag-raw4','forbid-phase-record'):
        from scripts.game_data.codecs.levelscript.current_action_nominal_param import read_constant
        constant=read_constant(reader,field+'.constValue',cap['constantCapability'],value)
    elif spec['kind'] in ('quaternion-raw16','posrot-list'):
        from scripts.game_data.codecs.levelscript.current_action_additional_param import read_constant
        constant=read_constant(reader,field+'.constValue',cap['constantCapability'],value)
    elif spec['kind'] in ('buff-pointer-record','null-buff-list'):
        from scripts.game_data.codecs.levelscript.current_action_buff_param import read_constant
        constant=read_constant(reader,field+'.constValue',cap['constantCapability'],value)
    elif spec['kind']=='owned-blackboard-list':
        count=reader.number('<i',field+'.constValue.count')
        if not -1<=count<=spec['countLimit']:raise ValueError(field+':own-Blackboard-list-count-limit')
        reader.need(max(count,0),field+'.constValue.minimum-element-headers')
        constant=None if count==-1 else []
        from scripts.game_data.codecs.levelscript.current_mask_curve_param import _float
        for i in range(max(count,0)):
            name=field+'.constValue['+str(i)+']'
            header=reader.number('<B',name+'.memberCount')
            if header==255:constant.append(None);continue
            if header!=spec['childMemberCount']:raise ValueError(name+':Blackboard-member-count')
            key=reader.string(name+'.key');use=reader.number('<B',name+'.useString')
            number=_float(reader,name+'.valueFloat');text=reader.string(name+'.valueString')
            constant.append(dict(key=key,useString=bool(use),useStringRawByte=use,valueFloat=number,valueString=text))
    elif spec['kind']in('owned-Boolean-list','owned-global-buff-id-list','owned-lang-key-list'):
        count=reader.number('<i',field+'.constValue.count')
        if not -1<=count<=spec['countLimit']:raise ValueError(field+':own-value-list-count-limit')
        reader.need(max(count,0),field+'.constValue.minimum-elements')
        constant=None if count==-1 else[]
        for i in range(max(count,0)):
            at=field+'.constValue['+str(i)+']'
            if spec['kind']=='owned-Boolean-list':
                constant.append(reader.number('<B',at))
            else:
                child=reader.number('<B',at+'.memberCount')
                if child not in(1,255):raise ValueError(at+':own-nominal-list-element-member-count')
                key='id'if spec['kind']=='owned-global-buff-id-list'else'key'
                constant.append({key:None if child==255 else reader.string(at+'.'+key),'wasNullMarker':child==255})
    elif spec['kind']=='owned-envtalk-value-list':
        count=reader.number('<i',field+'.constValue.count')
        if not -1<=count<=spec['countLimit']:raise ValueError(field+':own-EnvTalk-list-count-limit')
        reader.need(max(count,0),field+'.constValue.minimum-element-headers')
        constant=None if count==-1 else []
        for i in range(max(count,0)):
            at=field+'.constValue['+str(i)+']'
            header=reader.number('<B',at+'.memberCount')
            if header==255:
                constant.append(dict(envTalkId=None,odds=0,wasNullMarker=True));continue
            if header!=spec['childMemberCount']:raise ValueError(at+':EnvTalk-member-count')
            constant.append(dict(envTalkId=reader.string(at+'.envTalkId'),
                                 odds=reader.number('<i',at+'.odds'),wasNullMarker=False))
    elif spec['kind']in('owned-int32-list','owned-uint64-list'):
        count=reader.number('<i',field+'.constValue.count')
        if not -1<=count<=spec['countLimit']:raise ValueError(field+':own-integer-list-count-limit')
        reader.need(max(count,0)*spec['elementWireBytes'],field+'.constValue.elements')
        fmt='<Q'if spec['kind']=='owned-uint64-list'else'<i'
        constant=None if count==-1 else[reader.number(fmt,field+'.constValue['+str(i)+']')for i in range(count)]
    elif spec['kind'] in ('owned-float32-list','owned-vector3-list'):
        import math
        count=reader.number('<i',field+'.constValue.count')
        if not -1<=count<=spec['countLimit']:raise ValueError(field+':own-numeric-vector-list-count-limit')
        width=spec['elementWireBytes'];reader.need(max(count,0)*width,field+'.constValue.elements')
        constant=None if count==-1 else[];raw=None if count==-1 else[]
        for i in range(max(count,0)):
            at=reader.offset
            values=[reader.number('<f',field+'.constValue['+str(i)+'].'+axis) for axis in ('xyz' if width==12 else 'x')]
            if width==12 and not all(math.isfinite(v) for v in values):
                raise ValueError(field+':own-vector3-list-finite-domain')
            constant.append(dict(zip('xyz',values)) if width==12 else values[0])
            raw.append(bytes(reader.data[at:reader.offset]).hex().upper())
    elif spec['kind']=='reference-null-only':
        if reader.number('<B',field+'.constValue.memberCount')!=255:
            raise ValueError(field+':positive-CameraController-constant-unproved')
        constant=None;was_null=True
    else:
        child=reader.number('<B',field+'.constValue.memberCount');was_null=child==255
        if child==255:
            if not spec['constantNullAdmitted']:raise ValueError(field+':null-constant-source-unproved')
            constant={spec['keyField']:None}
        elif child==spec['constantMemberCount']:
            constant={spec['keyField']:reader.string(field+'.constValue.'+spec['keyField'])}
        else:raise ValueError(field+':own-key-constant-member-count')
    result=dict(startOffset=start,typeName=cap['typeName'],constValue=constant,
        idRef=reader.number('<i',field+'.idRef'),paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))
    if raw is not None:result['constantRawHex']=raw
    if was_null is not None:result['constantWasNullMarker']=was_null
    result['endOffset']=reader.offset
    return result
