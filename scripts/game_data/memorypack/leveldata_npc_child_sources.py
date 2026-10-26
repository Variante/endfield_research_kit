"""Independent positive children for the current owner's bounded NPC profile.

The historical NPC v1 layout remains unchanged. This component joins each
selected nominal record to the freshly authenticated NPC parent's actual
ReadValue context and target. Unlisted reference children remain FF-only.
"""
INFO='Beyond.Gameplay.Core.NpcProxyInfoData'
RUNTIME='Beyond.Gameplay.Core.NpcRuntimeData'
PLANS={
    INFO:(('mapId','string','pool'),('npcId','string','pool'),('npcNameId','string','pool'),
        ('npcProxyType','Beyond.GEnums.NpcProxyType','i32')),
    RUNTIME:(('enableMagicaCloth','bool','bool'),('enableMorph','bool','bool'),('headIcon','string','pool'),
        ('interactRangeType','Beyond.GEnums.NpcInteractRangeType','i32'),('npcEntityId','string','pool'),
        ('npcNameId','string','pool'),('templateID','string','pool')),
}
PARENTS={'npcInfoData':INFO,'npcRuntimeData':RUNTIME}


def validate_plan(name,source):
    if (name not in PLANS or source.get('wrappedType')!=name
            or source.get('completeSelectedCallerAdmitted')is not True
            or [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']]!=[
                (field,declared)for field,declared,_ in PLANS[name]]
            or source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is not True):
        raise ValueError('currentNpcChildren.closed-record-plan:'+name)


def bind_parent(name,usage,transfer,reference_source,base):
    expected=PARENTS.get(name)
    if (expected is None or transfer.get('field')!=name or transfer.get('mode')!='ordinary'
            or (usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))!=(
                'MemoryPack.MemoryPackReader','ReadValue',[],[expected])):
        raise ValueError('currentNpcChildren.exact-nominal-parent:'+name)
    if (usage['instructionRva']+base!=int(transfer['contextLoad']['va'],16)
            or transfer['target']!=reference_source['selectedBytes'][0][0]):
        raise ValueError('currentNpcChildren.actual-parent-context-target:'+name)
    return dict(fieldName=name,typeName=expected,typedRequest=usage,source=transfer)


def extend_layout(layout,records,parents):
    """Build a new profile without changing the independent NPC v1 declaration."""
    import copy
    if (set(records)!=set(PLANS) or {p['fieldName']:p['typeName']for p in parents}!=PARENTS
            or len(parents)!=len(PARENTS)):
        raise ValueError('currentNpcChildren.complete-independent-components')
    result=copy.deepcopy(layout)
    for name,record in records.items():
        validate_plan(name,record['source'])
        if name in result['records']:raise ValueError('currentNpcChildren.old-record-collision:'+name)
        result['records'][name]=[dict(name=field,type=declared,wire=wire)for field,declared,wire in PLANS[name]]
    for field,name in PARENTS.items():
        matches=[r for r in result['root']if r['name']==field]
        if len(matches)!=1 or (matches[0]['type'],matches[0]['wire'])!=(name,'null'):
            raise ValueError('currentNpcChildren.old-null-only-parent:'+field)
        matches[0].update(wire='record',nullable=True)
    return result


def derive(image,pins,npc):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    need=lambda key,expected,actual:scalar.need('currentNpcChildren',key,expected,actual)
    need('selected-base-NPC',pins,npc['nativeInputs'])
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in PLANS}
    need('exact-closed-wrappers',set(PLANS),set(wrappers))
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
    offsets=scalar.reader_offsets(image,'currentNpcChildren');records={}
    for name,result in zip(PLANS,generated['owners'],strict=True):
        need('complete-generated-source:'+name,'complete-reader-source-proved',
            result['status']if result['status']=='complete-reader-source-proved'else result)
        source=result['proof'];validate_plan(name,source)
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
        need('same-complete-GetValue:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('same-concrete-slot5:'+name,source['lifecycle']['concreteFormatter']['method'][0],
            pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        primitives={}
        for read,(_,declared,wire)in zip(source['orderedSourceReads'],PLANS[name],strict=True):
            need('selected-source-kind:'+read['fieldName'],{'pool':'byte-payload','bool':'byte','i32':'scalar32'}[wire],read['kind'])
            if wire=='pool':
                primitives[read['fieldName']]=pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
                continue
            body=vector_recorder(image)(read['sourceTargetRva'])
            checked=scalar.boolean_source(image,body,offsets,'currentNpcChildren.bool')if wire=='bool'else scalar.integer_source(
                image,body,offsets,'currentNpcChildren.int32',width=4)
            enum=None
            if wire=='i32':
                enum=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentNpcChildren.enum')
                bind_typed_read(image,enum,method_name='ReadUnmanaged',argument=declared,kind=17,reference=False)
                need('nominal-enum-parent:'+declared,'System.Enum',ctx.parent(declared))
                need('exact-enum-int32-backing:'+declared,(declared,'int',16),ctx.field(declared+'::value__'))
            primitives[read['fieldName']]=dict(source=body,proof=checked,typedEnum=enum)
        records[name]=dict(source=source,pair=pair,adapter=adapter,primitives=primitives)
    parents=[];parent=npc['proof']['parent'];reference=npc['proof']['readValue']
    for field,name in PARENTS.items():
        transfer,=[r for r in parent['fieldTransfers']if r['field']==field]
        usage=derive_typed_usage_context(image,int(transfer['contextLoad']['va'],16)-base,label='currentNpcChildren.parent')
        bind_typed_read(image,usage,method_name='ReadValue',argument=name,kind=18,reference=True)
        parents.append(bind_parent(field,usage,transfer,reference,base))
    layout=extend_layout(npc['layout'],records,parents)
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,parents=parents,layout=layout,
        capability=dict(profileId='current-owner-npc-children',positiveReferenceFields=PARENTS,
            nullMarker=255,profileAdmitted=True,wholeGrammarAdmitted=False,
            requiresFreshCurrentOwnerScope=True,liveFormatterSelectionObserved=False),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
