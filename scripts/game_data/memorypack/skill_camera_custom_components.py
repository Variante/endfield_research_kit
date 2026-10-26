"""Whole finite stored CameraControlStateCustomConfig34 below parent/EOF.

The own four-path MC34 source, ScriptableObject typed factory, plain holder
getter, ordinary canonical adapter and actual Reader identity stay distinct
from child grammar. Both InitialParam fields use their actual source-proved
raw24 program; no MC7 wrapper/FF or managed-padding inference is transferred.
The disabled-module enum list, thirteen-route ModuleConfig list, ordinary Unity
curves and two actual TransitionConditionAnd lists each join fresh nominal
MethodSpecs/E8 and complete independent child/count/callback source owners.

All source selections require coherent initialized original contexts/registries,
compatible callbacks and normal helpers/typed allocation, disabled collector,
opaque Unity ScriptableObject initialization and disjoint sufficient storage.
No camera execution, live provider replacement, enclosing action/root or file
EOF follows from this stored configuration capability.
"""
import json

from scripts.game_data.memorypack import skill_camera_custom_config_sources as owner
from scripts.game_data.memorypack import skill_camera_module_components as module
from scripts.game_data.memorypack import skill_camera_transition_sources as transition

SCHEMA='endfield.skill-camera-custom-components.v1'
TYPE=owner.TYPE
WRAPPER=owner.WRAPPER
CAPABILITY=owner.CAPABILITY
ENUM_LIST='skill-enum-list:'+owner.ENUM
ENUM_ELEMENT='skill-enum-callback:'+owner.ENUM
COLLECTIONS={owner.LIST(owner.ENUM):(ENUM_LIST,'camera-enum-list',ENUM_LIST),
    owner.LIST(owner.CONDITION):(transition.LIST,'camera-transition-list',transition.LIST),
    owner.LIST(owner.MODULE):(module.LIST,'camera-module-list',module.LIST)}


def need(check,condition):
    if not condition:raise ValueError('skillCameraCustomComponents.'+check)


def ordered_reads():
    result=[]
    for i,(field,typ)in enumerate(owner.MEMBERS):
        if typ==owner.CURVE:kind,child='curve-profile','curve-profile'
        elif typ in COLLECTIONS:_,kind,child=COLLECTIONS[typ]
        elif typ==owner.INITIAL:kind,child='camera-initial-raw24',None
        else:kind,child={'bool':'bool-byte','float':'float32-bits'}.get(typ,'scalar32'),None
        result.append(dict(memberIndex=i,fieldName=field,kind=kind,childCapability=child))
    return result


def bind_collection(pins,join,child,capability):
    from scripts.game_data.memorypack.skill_enum_list_codec import require_capability as enum_cap
    from scripts.game_data.memorypack.skill_camera_module_codec import require_collection as module_cap,require_union
    from scripts.game_data.memorypack.skill_camera_transition_codec import require_collection as transition_cap,require_and
    need('same-collection-native-inputs',child.get('nativeInputs')==pins)
    names={15:(owner.LIST(owner.ENUM),ENUM_LIST),19:(owner.LIST(owner.CONDITION),transition.LIST),
        25:(owner.LIST(owner.CONDITION),transition.LIST),26:(owner.LIST(owner.MODULE),module.LIST)}
    fields={owner.MEMBERS[i][0]:(nominal,cap)for i,(nominal,cap)in names.items()}
    need('finite-owned-list-field',join.get('fieldName')in fields)
    nominal,expected=fields[join['fieldName']];need('own-field-list-type',(join.get('typeName'),capability)==(nominal,expected))
    caps=child['capabilities'];cap=caps[capability];usage=join['typedRequest']
    if capability==ENUM_LIST:
        enum_cap(cap,caps[ENUM_ELEMENT],name=owner.ENUM)
        request=child['proof']['actualParentRequestBinding']
        need('same-enum-actual-parent',request['sourceRequest']==usage and request['collectionCapability']==cap
            and request['packableReaderTargetRva']==join['sourceTargetRva'])
        element=caps[ENUM_ELEMENT]
    else:
        if capability==module.LIST:
            module_cap(cap);require_union(caps[module.CAPABILITY]);element=caps[module.CAPABILITY]
        else:
            transition_cap(cap,outer=True);require_and(caps[transition.CAPABILITY]);element=caps[transition.CAPABILITY]
        witness=child['proof']['collection']['witnessComponent']
        need('same-list-source-owned-parent',witness['typedRequest']==usage and witness['callTargetRva']==join['sourceTargetRva'])
    need('actual-nominal-ReadPackable-identity',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal])
        and type(usage['methodSpec'][0])is int and usage['methodSpec'][0]==cap['packableReaderMethodDefinition']
        and type(join.get('sourceTargetRva'))is int and join['sourceTargetRva']==cap['packableReaderTargetRva'])
    return dict(fieldName=join['fieldName'],typeName=nominal,capability=capability,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
        collectionCapabilityShape=cap,elementCapabilityShape=element)


def bind_program(source,compiled,pins):
    owner.require_source(source,pins);order=ordered_reads()
    required=sorted({r['childCapability']for r in order if r['childCapability']is not None})
    need('complete-34-field-program',type(compiled.get('memberCount'))is int and compiled['memberCount']==34
        and compiled.get('reads')==order and all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    need('complete-exact-child-requirements',compiled.get('requiredCapabilities')==required)
    requested=[r for r in source['orderedSourceReads']if r['declaredType']==owner.CURVE or r['declaredType']in COLLECTIONS]
    bindings=compiled.get('childBindings',[])
    need('one-independent-binding-per-child',len(bindings)==len(requested))
    for read,binding in zip(requested,bindings):
        capability='curve-profile'if read['declaredType']==owner.CURVE else COLLECTIONS[read['declaredType']][0]
        need('actual-every-child-call:'+str(read['memberIndex']),
            (binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],read['declaredType'],capability)
            and binding.get('readerMethodDefinition')==read.get('context',{}).get('methodSpec',[None])[0]
            and binding.get('sourceTargetRva')==read.get('sourceTargetRva'))
    return order


def _derive_on_children(image,pins,*,curve,enums,modules,transitions):
    """Internal composition of dependencies freshly derived on the same image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability as curve_cap
    from scripts.game_data.memorypack.skill_camera_module_list_sources import _derive_on_union
    from scripts.game_data.memorypack.enum_list_native_sources import bind_request
    _publication_gate(image,pins)
    need('same-fresh-children-native-inputs',all(c.get('nativeInputs')==pins for c in(curve,enums,modules,transitions)))
    curve_shape=curve_cap(curve['capabilities']['curve-profile'])
    need('fresh-positive-module-transition-owners',modules.get('schema')==module.SCHEMA
        and modules.get('status')=='validated-conditional-camera-module-components'
        and transitions.get('schema')=='endfield.skill-camera-transition-sources.v1'
        and transitions.get('status')=='validated-conditional-camera-transitions')
    complete=owner.derive_source(image,pins);source=complete['proof']['source'];owner.require_source(source,pins)
    requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='cameraCustom.child')
        for r in source['orderedSourceReads']if r['declaredType']==owner.CURVE or r['declaredType']in COLLECTIONS}
    collections={};joined={};base=image.pe.image_base
    for index in(15,19,25,26):
        read=source['orderedSourceReads'][index];usage=requests[index];target=base+read['sourceTargetRva']
        if index==15:
            binding=bind_request(image,pins,enums,typed_request=usage,call_target=target,enum_type=owner.ENUM)
            child=dict(nativeInputs=pins,capabilities={k:enums['capabilities'][k]for k in(ENUM_LIST,ENUM_ELEMENT)},
                proof=dict(source=enums,actualParentRequestBinding=binding))
        elif index==26:child=_derive_on_union(image,pins,modules,typed_request=usage,call_target=target)
        else:child=transition._derive_list_on_child(image,pins,transitions,typed_request=usage,call_target=target)
        collections[index]=child;joined[str(index)]=child
    compiled,pending=compile_member_program(source,pins,wrapper_name=WRAPPER,type_name=TYPE,value4={},
        references={owner.CURVE:('curve-profile','curve-profile','curve-profile')},reference_children={owner.CURVE:curve},
        typed_requests=requests,collections=COLLECTIONS,collection_children=collections,collection_binder=bind_collection)
    need('all-34-child-grammar-joins',pending==[])
    order=bind_program(source,compiled,pins);caps={}
    for child in collections.values():
        for key,cap in child['capabilities'].items():
            need('same-shared-child-capability:'+key,key not in caps or caps[key]==cap);caps[key]=cap
    need('same-curve-shape-required-by-module-graph',modules['requiredExternalCapabilityIdentities']['curve-profile']==
        {k:curve_shape[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')})
    reader=complete['proof']['referenceReader']
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=34,orderedReads=order,nullable=True,nullMarker=255,
        nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        completeSourceOwnedProgram=True,opaqueUnityInitializationRequired=True,originalManagedConstructorInvoked=False,
        **{k:reader[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    caps[CAPABILITY]=cap
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-camera-custom-components',nativeInputs=pins,
        capabilities=caps,requiredExternalCapabilities=['byte-payload','curve-profile'],
        requiredExternalCapabilityShapes={'curve-profile':curve_shape},
        proof=dict(ownSource=complete,compiled=compiled,typedRequests=requests,collections=joined,
            curve=curve,moduleGraph=modules,transitionGraph=transitions,enumSource=enums),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Complete current34 source/lifecycle/ordinary ABI and every independently source-bound child/list/raw24 program.',
            conditional=__doc__,structuralOnly='Stored custom camera configuration.',
            unresolved=['runtime provider and camera behavior','enclosing action/root/EOF','growth/refill/failure paths']))))


def derive(image,pins):
    from scripts.game_data.memorypack.skill_animation_curve_sources import derive as curve_source
    from scripts.game_data.memorypack.enum_list_native_sources import derive as enum_source
    curve=curve_source(image,pins)
    curve=dict(nativeInputs=pins,capabilities={'curve-profile':curve['capabilities']['skill-animation-curve']},proof=curve)
    modules=module._derive_on_curve(image,pins,curve)
    return _derive_on_children(image,pins,curve=curve,enums=enum_source(image,pins),modules=modules,transitions=transition.derive(image,pins))
