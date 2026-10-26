"""ToggleBuffData MC2 with independently closed BuffInput/Condition lists.

Its complete generated source/lifecycle, typed constructor and holder getter
compose the ordinary canonical reference adapter/actual Reader source. Each
named field independently supplies its closed ReadPackable MethodSpec and E8;
finite count/loop/Add induction and the exact element callback grammars compose
without treating a reference stride as wire width. Conditions own both concrete
short routes and BlackboardDouble source. Ready matching runtime callbacks,
normal compatible allocations/helpers, selected exported pool, disabled GC
and disjoint buffered storage remain conditions. Runtime condition/buff effects,
other provider choices and root/whole owner/physical EOF are unproved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_root_attribute_components import reference_cap

TYPE='Beyond.Gameplay.Core.ToggleBuffData'
CAPABILITY='skill-root-toggle-buff'
LIST_CAP='skill-root-toggle-buff-list'
BUFF_TYPE='Beyond.Gameplay.Core.BuffInput'
CONDITION='Beyond.Gameplay.Core.Abilities.Condition.ConditionBase'
ORDER=[dict(fieldName=n,kind='reference-list',childCapability=c)for n,c in(
    ('buffs','skill-root-buff-input-list'),('conditions','skill-root-ability-condition-list'))]


def bind_list(pins,read,usage,child,capability):
    need('Toggle-same-list-pins',pins,child['nativeInputs']);cap=child['capabilities'][capability]
    need('Toggle-exact-closed-list',read['declaredType'],cap['closedListType'])
    need('Toggle-list-field-source-kind','reference:'+read['declaredType'],read['kind'])
    need('Toggle-list-context-owner',True,read['context']['methodOwner']=='MemoryPack.MemoryPackReader'
        and read['context']['methodName']=='ReadPackable'and read['context']['typeKind']==21
        and read['context']['fullTypeName']==read['declaredType']
        and read['context']['instructionRva']==usage['instructionRva']and read['context']['methodSpec']==usage['methodSpec'])
    need('Toggle-actual-typed-list',('MemoryPack.MemoryPackReader','ReadPackable',[],[cap['closedListType']]),
        tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments')))
    need('Toggle-literal-list-reader',True,all(type(cap.get(k))is int and cap[k]>0
        for k in('packableReaderMethodDefinition','packableReaderTargetRva')))
    need('Toggle-actual-list-definition-and-target',(usage['methodSpec'][0],read['sourceTargetRva']),
        (cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva']))
    need('Toggle-complete-list-child',True,cap.get('positiveCountsAdmitted')is True and cap.get('elementGrammarAdmitted')is True)
    return dict(fieldName=read['fieldName'],capability=capability,closedListType=cap['closedListType'],
        methodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'])


def derive(image,pins,*,buffs=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_reader_sources import derive as record_source
    from scripts.game_data.memorypack.skill_root_generated_reference import derive as reference_source
    from scripts.game_data.memorypack.skill_root_buff_input_components import derive_list as buff_lists
    from scripts.game_data.memorypack.skill_root_condition_components import derive_list as condition_lists
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    source=record_source(image,pins,wrapper.name);reads=source['orderedSourceReads'];base=image.pe.image_base
    need('Toggle-exact-owned-member-order',[('buffs','System.Collections.Generic.List`1<'+BUFF_TYPE+'>'),
        ('conditions','System.Collections.Generic.List`1<'+CONDITION+'>')],[(r['fieldName'],r['declaredType'])for r in reads])
    requests=[derive_typed_usage_context(image,r['context']['instructionRva'],label='Toggle.list')for r in reads]
    buffs=buff_lists(image,pins,typed_request=requests[0],call_target=base+reads[0]['sourceTargetRva'])if buffs is None else buffs
    conditions=condition_lists(image,pins,typed_request=requests[1],call_target=base+reads[1]['sourceTargetRva'])
    bindings=[bind_list(pins,read,usage,child,order['childCapability'])for read,usage,child,order in
        zip(reads,requests,(buffs,conditions),ORDER,strict=True)]
    reference=reference_source(image,pins,source);caps=dict(buffs['capabilities'])
    for name,cap in conditions['capabilities'].items():
        if name in caps:need('Toggle-shared-child-source:'+name,caps[name],cap)
        caps[name]=cap
    descriptor=dict(typeName=TYPE,wrapperName=source['wrapperName'],memberCount=2)
    caps[CAPABILITY]=reference_cap(descriptor,reference,ORDER);caps[CAPABILITY]['ordinaryOriginalReadValueAdmitted']=True
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-toggle-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,requiredExternalCapabilities=['byte-payload'],
        proof=dict(parent=source,parentReference=reference,buffs=buffs,conditions=conditions,bindings=bindings),
        evidenceBoundary=dict(exact='ToggleBuffData complete MC2/FF/new source/lifecycle/ordinary reference adapter, actual named BuffInput and AbilityCondition closed lists, finite induction and both independent positive element grammars.',
            conditional=__doc__,structuralOnly='Stored toggle configuration.',unresolved=['runtime buff/condition behavior','enclosing root/EOF']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000,buffs=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    child=derive(image,pins,buffs=buffs)
    collection=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    witness=collection['witnessComponent'];caps=dict(child['capabilities'])
    caps[LIST_CAP]=dict(elementType=TYPE,elementValueType=False,closedListType='System.Collections.Generic.List`1<'+TYPE+'>',
        collectionCounts=[-1,0],nullable=True,countLimit=count_limit,positiveCountsAdmitted=True,
        elementCapability=CAPABILITY,elementGrammarAdmitted=True,
        packableReaderMethodDefinition=witness['typedRequest']['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return dict(schema='endfield.skill-root-toggle-list-components.v1',nativeInputs=dict(pins),status='validated-conditional-components',
        capabilities=caps,proof=dict(child=child,collection=collection),requiredExternalCapabilities=['byte-payload'],
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=child['evidenceBoundary'])
