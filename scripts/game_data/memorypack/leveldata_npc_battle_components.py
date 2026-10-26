"""Finite NPC battle/SkillBB/Collider grammar and their actual parent joins."""
from scripts.game_data.memorypack.leveldata_npc_battle_sources import BATTLE,SKILL,COLLIDER,PAIR,COUNT_LIMIT
from scripts.game_data.memorypack.leveldata_extended_record_sources import STRINGS,STRING_CAP,bind_strings

COLLIDER_CAP='story-npc-collider'
SKILL_CAP='story-npc-skill-blackboard'
SKILL_LIST_CAP=SKILL_CAP+'-list'
PAIR_CAP='skill-root-data-pair-list-positive'
COLLIDER_PLAN=(('_center','UnityEngine.Vector3','unity-vector3-raw12'),('_centerXKey','string','byte-payload'),
 ('_centerYKey','string','byte-payload'),('_centerZKey','string','byte-payload'),('_extent','UnityEngine.Vector3','unity-vector3-raw12'),
 ('_extentXKey','string','byte-payload'),('_extentYKey','string','byte-payload'),('_extentZKey','string','byte-payload'),
 ('_height','float','float32-bits'),('_heightKey','string','byte-payload'),('_radius','float','float32-bits'),
 ('_radiusKey','string','byte-payload'),('_rotationOffset','UnityEngine.Vector3','unity-vector3-raw12'),
 ('_shape','Beyond.Gameplay.ColliderShape','scalar32'),('_useCenterKey','bool','bool-byte'),('_useExtentKey','bool','bool-byte'))
PLANS={COLLIDER:COLLIDER_PLAN,
 SKILL:(('blackboard','System.Collections.Generic.List`1<'+PAIR+'>','data-pair-list'),('skillId','string','byte-payload')),
 BATTLE:(('activeSkillId',STRINGS,'pooled-string-list'),('battleShapeData',COLLIDER,'record'),
  ('blackboard','System.Collections.Generic.List`1<'+SKILL+'>','skill-blackboard-list'),('passiveSkillId',STRINGS,'pooled-string-list'))}


def bind_reference(pins,join,child,capability):
    cap=child['capabilities'][capability];usage=join['typedRequest']
    if (capability!=COLLIDER_CAP or child.get('nativeInputs')!=pins or join['typeName']!=COLLIDER
            or cap.get('typeName')!=COLLIDER or cap.get('profileAdmitted')is not True
            or cap.get('positiveAdmitted')is not True or cap.get('nullAdmitted')is not True
            or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(COLLIDER_PLAN)
            or [(r.get('memberIndex'),r.get('fieldName'),r.get('kind'))for r in cap.get('orderedReads',[])]!=[
                (i,n,k)for i,(n,_,k)in enumerate(COLLIDER_PLAN)]
            or cap.get('wholeGrammarAdmitted')is not False or cap.get('actualCallbackEqualsProvedChildRequired')is not True
            or any(type(cap.get(k))is not int for k in('referenceReaderMethodDefinition','referenceReaderTargetRva'))
            or(cap.get('referenceReaderMethodDefinition'),cap.get('referenceReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentNpcBattle.exact-Collider-profile-parent')
    return dict(fieldName=join['fieldName'],typeName=COLLIDER,capability=capability,
        readerMethodDefinition=cap['referenceReaderMethodDefinition'],sourceTargetRva=cap['referenceReaderTargetRva'],
        profileAdmitted=True,wholeGrammarAdmitted=False,actualCallbackEqualsProvedChildRequired=True)


def bind_skill_list(pins,join,child,capability):
    if capability==STRING_CAP:return bind_strings(pins,join,child,capability)
    cap=child['capabilities'][capability];usage=join['typedRequest'];declared='System.Collections.Generic.List`1<'+SKILL+'>'
    if (capability!=SKILL_LIST_CAP or child.get('nativeInputs')!=pins or join['typeName']!=declared
            or(cap.get('closedListType'),cap.get('elementType'),cap.get('countLimit'))!=(declared,SKILL,COUNT_LIMIT)
            or cap.get('elementValueType')is not False or cap.get('elementGrammarAdmitted')is not True
            or cap.get('nullable')is not True or cap.get('positiveCountsAdmitted')is not True
            or cap.get('elementCapability')!=SKILL_CAP
            or cap.get('actualCallbackEqualsProvedChildRequired')is not True
            or any(type(cap.get(k))is not int for k in('packableReaderMethodDefinition','packableReaderTargetRva','countLimit'))
            or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentNpcBattle.exact-SkillBB-list-parent')
    return dict(fieldName=join['fieldName'],typeName=declared,capability=capability,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
        countLimit=COUNT_LIMIT,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,npc):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.leveldata_npc_battle_sources import derive_lists
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    need=lambda k,e,a:scalar.need('currentNpcBattle',k,e,a)
    need('selected-base-NPC',pins,npc['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    lists=derive_lists(image,pins);wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in PLANS}
    collider=generated_reader_sources.derive(image,pins,wrappers[COLLIDER].name)
    sources={COLLIDER:collider,**lists['records']};abi=reference_reader_abi(image,pins);records={};caps={}
    reference_children={};collection_children={};requests={}
    for name in(COLLIDER,SKILL,BATTLE):
        source=sources[name];plan=PLANS[name]
        need('exact-finite-declared-plan:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
        references={};collections={};requests={};collection_children={}
        if name==SKILL:
            parent=lists['dataPairList'];read=source['orderedSourceReads'][0];requests[0]=parent['typedRequest']
            collections[read['declaredType']]=(PAIR_CAP,'data-pair-list',PAIR_CAP)
            collection_children[0]=parent['component']
        elif name==BATTLE:
            references[COLLIDER]=(COLLIDER_CAP,'record',COLLIDER_CAP)
            read=source['orderedSourceReads'][1]
            requests[1]=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentNpcBattle.Collider')
            for parent in lists['referenceParents']:
                index=next(r['memberIndex']for r in source['orderedSourceReads']if r['fieldName']==parent['fieldName'])
                requests[index]=parent['typedRequest'];witness=parent['collection'];element=parent['element']
                key=SKILL_LIST_CAP if element==SKILL else STRING_CAP
                cap=dict(closedListType=parent['typeName'],elementType=element,elementValueType=False,countLimit=COUNT_LIMIT,
                    nullable=True,positiveCountsAdmitted=True,elementGrammarAdmitted=True,
                    elementCapability=SKILL_CAP if element==SKILL else'byte-payload',
                    actualCallbackEqualsProvedChildRequired=True,actualCallbackEqualsPooledStringRequired=element=='string',
                    packableReaderMethodDefinition=parent['typedRequest']['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'])
                collections[parent['typeName']]=(key,'skill-blackboard-list'if element==SKILL else'pooled-string-list',key)
                collection_children[index]=dict(nativeInputs=pins,capabilities={key:cap})
        program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
            references=references,reference_children=reference_children,typed_requests=requests,
            collections=collections,collection_children=collection_children,
            collection_binder=bind_skill_list if name==BATTLE else None,reference_binder=bind_reference)
        need('complete-finite-program:'+name,[],pending)
        need('exact-finite-compiled-order:'+name,[(n,k)for n,t,k in plan],[(r['fieldName'],r['kind'])for r in program['reads']])
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
        need('complete-owned-GetValue',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('same-concrete-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        pooled={str(r['memberIndex']):pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
            for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
        enums={}
        if name==COLLIDER:
            enum='Beyond.Gameplay.ColliderShape';need('Collider-enum-parent','System.Enum',ctx.parent(enum))
            value=ctx.field(enum+'::value__');need('Collider-enum32-backing',True,value[1]in('int','uint'))
            enums['_shape']=dict(typeName=enum,backing=value[1],field=value)
        records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pooled,enumBackings=enums)
        key=COLLIDER_CAP if name==COLLIDER else SKILL_CAP if name==SKILL else'story-npc-battle'
        cap=dict(typeName=name,memberCount=len(plan),orderedReads=program['reads'],nullAdmitted=True,positiveAdmitted=True,
            profileAdmitted=True,wholeGrammarAdmitted=False,actualCallbackEqualsProvedChildRequired=True,
            referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'])
        caps[key]=cap;reference_children[name]=dict(nativeInputs=pins,capabilities={key:cap})
    transfer,=[r for r in npc['proof']['parent']['fieldTransfers']if r['field']=='battleData']
    usage=derive_typed_usage_context(image,int(transfer['contextLoad']['va'],16)-base,label='currentNpcBattle.parent')
    bind_typed_read(image,usage,method_name='ReadValue',argument=BATTLE,kind=18,reference=True)
    need('actual-NPC-Battle-parent-target',(transfer['target']-base,usage['methodSpec'][0]),
        (abi['referenceReaderTargetRva'],abi['referenceReaderMethodDefinition']))
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,capabilities=caps,
        collections=lists,parent=dict(source=transfer,typedRequest=usage),referenceABI=abi,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
