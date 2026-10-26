"""Current NPC hit/ability children: exact nominal source and parent joins."""
import copy

HIT='Beyond.Gameplay.Core.NpcHitData'
ABILITY='Beyond.Gameplay.Core.AbilityData'
PLANS={
 HIT:(('canBeHit','bool','bool-byte'),('center','UnityEngine.Vector3','unity-vector3-raw12'),
  ('direction',HIT+'+ECapsuleDirection','scalar32'),('extent','UnityEngine.Vector3','unity-vector3-raw12'),
  ('height','float','float32-bits'),('hitEffect','string','byte-payload'),('radius','float','float32-bits'),
  ('shape','Beyond.Gameplay.ColliderShape','scalar32')),
 ABILITY:(('enableAbilityOverride','bool','bool-byte'),('lookAheadTime','float','float32-bits'),
  ('reactionTime','float','float32-bits'))}
PARENTS={'hitData':HIT,'npcAbility':ABILITY}


def validate_profile(profile):
    if (not isinstance(profile,dict)or profile.get('profileId')!='current-owner-npc-hit-ability'
            or profile.get('profileAdmitted')is not True or profile.get('wholeGrammarAdmitted')is not False
            or profile.get('requiresFreshCurrentOwnerScope')is not True or profile.get('finiteFloatProfile')is not True
            or profile.get('liveFormatterSelectionObserved')is not False or set(profile.get('records',{}))!=set(PLANS)):
        raise ValueError('currentNpcExtra.exact-profile')
    for name,plan in PLANS.items():
        cap=profile['records'][name];program=cap.get('program',{})
        if (cap.get('typeName')!=name or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(plan)
                or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','actualCallbackEqualsProvedChildRequired'))
                or program.get('memberCount')!=len(plan)
                or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
                or [(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                    (i,n,k,'byte-payload'if k=='byte-payload'else None)for i,(n,_,k)in enumerate(plan)]
                or program.get('childBindings')!=[]
                or program.get('requiredCapabilities')!=(['byte-payload']if name==HIT else[])):
            raise ValueError('currentNpcExtra.exact-record-program:'+name)
        enums=cap.get('enumBackings',{});wanted={n:t for n,t,k in plan if k=='scalar32'}
        if set(enums)!=set(wanted):raise ValueError('currentNpcExtra.exact-enum-set:'+name)
        for field,typename in wanted.items():
            enum=enums[field]
            if (enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')
                    or enum.get('field')!=[typename,enum.get('backing'),16]):
                raise ValueError('currentNpcExtra.exact-nominal-enum:'+field)


def extend_layout(base,profile):
    validate_profile(profile);result=copy.deepcopy(base)
    for name,plan in PLANS.items():
        if name in result['records']:raise ValueError('currentNpcExtra.old-record-collision:'+name)
        enums=profile['records'][name]['enumBackings']
        result['records'][name]=[dict(name=n,type=t,wire='vector3'if k=='unity-vector3-raw12'
            else'pool'if k=='byte-payload'else'bool'if k=='bool-byte'else'f32'if k=='float32-bits'
            else'u32'if enums[n]['backing']=='uint'else'i32')for n,t,k in plan]
    for field,name in PARENTS.items():
        rows=[r for r in result['root']if r['name']==field]
        if len(rows)!=1 or(rows[0].get('type'),rows[0].get('wire'))!=(name,'null'):
            raise ValueError('currentNpcExtra.exact-old-null-parent:'+field)
        rows[0].update(wire='record',nullable=True)
    return result


def derive(image,pins,npc):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda k,e,a:scalar.need('currentNpcExtra',k,e,a)
    need('same-selected-NPC',pins,npc['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in PLANS}
    need('exact-two-child-wrappers',set(PLANS),set(wrappers))
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
    records={};caps={};parents=[];abi=reference_reader_abi(image,pins)
    for name,result in zip(PLANS,generated['owners'],strict=True):
        need('complete-child-source:'+name,'complete-reader-source-proved',
            result['status']if result['status']=='complete-reader-source-proved'else result)
        source=result['proof'];plan=PLANS[name]
        need('exact-nominal-member-order:'+name,[(n,t)for n,t,k in plan],
            [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
        program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,
            value4={},references={},reference_children={},collections={},collection_children={},typed_requests={})
        need('complete-finite-child:'+name,[],pending)
        need('exact-compiled-wire-order:'+name,[(n,k)for n,t,k in plan],[(r['fieldName'],r['kind'])for r in program['reads']])
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
        need('owned-GetValue-return',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('same-owned-concrete-slot5',source['lifecycle']['concreteFormatter']['method'][0],
            pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        pools={str(r['memberIndex']):pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
            for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
        enums={}
        for field,typename,kind in plan:
            if kind!='scalar32':continue
            need('nominal-enum-parent:'+typename,'System.Enum',ctx.parent(typename));value=ctx.field(typename+'::value__')
            need('nominal-four-byte-enum:'+typename,True,value[1]in('int','uint'))
            enums[field]=dict(typeName=typename,backing=value[1],field=value)
        records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pools,enumBackings=enums)
        caps[name]=dict(typeName=name,memberCount=len(plan),program=program,enumBackings=enums,
            nullAdmitted=True,positiveAdmitted=True,actualCallbackEqualsProvedChildRequired=True)
    for field,name in PARENTS.items():
        transfer,=[r for r in npc['proof']['parent']['fieldTransfers']if r['field']==field]
        usage=derive_typed_usage_context(image,int(transfer['contextLoad']['va'],16)-base,label='currentNpcExtra.parent')
        bind_typed_read(image,usage,method_name='ReadValue',argument=name,kind=18,reference=True)
        need('actual-nominal-NPC-parent:'+field,(transfer['target']-base,usage['methodSpec'][0]),
            (abi['referenceReaderTargetRva'],abi['referenceReaderMethodDefinition']))
        parents.append(dict(fieldName=field,typeName=name,source=transfer,typedRequest=usage))
    profile=dict(profileId='current-owner-npc-hit-ability',profileAdmitted=True,wholeGrammarAdmitted=False,
        requiresFreshCurrentOwnerScope=True,finiteFloatProfile=True,liveFormatterSelectionObserved=False,records=caps)
    profile=json.loads(json.dumps(profile));validate_profile(profile)
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,parents=parents,profile=profile,
        referenceABI=abi,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
