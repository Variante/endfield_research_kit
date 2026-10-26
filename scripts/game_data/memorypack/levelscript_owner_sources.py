"""Exact initialized existing-wrapper LevelScript root/Brief source paths.

The ordered child requests do not grant any child grammar or live formatter
selection. Enclosing cursors must compose each reached child independently.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

ROOT = 'Beyond.Gameplay.LevelScriptData'
BRIEF = 'Beyond.Gameplay.LevelScriptBriefData'
ROOT_FIELDS = (
    ('actionMap','reference'),('activeShapeList','reference'),
    ('allowStartOnTravelPole','bool'),('allowTick','bool'),('enablePreload','bool'),
    ('endType','enum32'),('enemies','reference'),('exitBuffer','float'),
    ('exitBufferOverride','bool'),('interactiveActiveRiskEntityIdList','reference'),
    ('interactiveLocks','reference'),('interactives','reference'),
    ('levelScriptType','enum32'),('lstTemplatePath','pool'),('maxStage','int32'),
    ('modules','reference'),('npcs','reference'),('parentLevelScriptId','uint64'),
    ('properties','reference'),('propertyIdToKeyMap','reference'),
    ('refWorldEntityIdList','reference'),('resetModeWhenActive','enum32'),
    ('resetModeWhenEnd','enum32'),('scriptId','uint64'),('startShapeList','reference'),
    ('startType','enum32'),('taskMap','reference'),('triggerVolumes','reference'),
)
BRIEF_FIELDS = (
    ('dataPath','path-hash64'),('interactiveActiveRiskEntityIdList','reference'),
    ('levelScriptType','enum32'),('maxStage','int32'),('parentLevelScriptId','uint64'),
    ('properties','reference'),('propertyIdToKeyMap','reference'),
    ('refWorldEntityIdList','reference'),('scriptId','uint64'),
)


def owner_program(regions, entry, original, fields, offsets, *, image_base):
    """Complete selected normal return, including entry/header/cursor/frame."""
    if original not in (ROOT,BRIEF):raise ValueError('levelscriptOwner.closed-owner')
    plan=ROOT_FIELDS if original==ROOT else BRIEF_FIELDS;root=original==ROOT
    if [f['name']for f in fields]!=[name for name,_ in plan]:
        raise ValueError('levelscriptOwner.ordered-fields')
    if offsets!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:
        raise ValueError('levelscriptOwner.reader-layout')
    if any(type(f['offset'])is not int or not 16<=f['offset']<4096 for f in fields):
        raise ValueError('levelscriptOwner.field-offset')
    g=BytesPath(regions,entry);reads=[];flags=[];guards=[];prepared=False
    peek=lambda n=3:bytes(g.bytes.get(g.at+i,0)for i in range(n)).hex()
    def branch_false():
        prefix='74'if peek(1)=='74'else'0f84';width=1 if prefix=='74'else 4
        at=g.at;target=g.relative(prefix,width)
        if target not in g.bytes:raise ValueError('levelscriptOwner.unowned-null-guard')
        guards.append(dict(instruction=at,target=target))
    def flag():
        at=g.at;target=g.relative('833d');g.take('00');flags.append(target+1)
        return at
    def store(prefix8,prefix32,slot):
        g.take(prefix8+slot.to_bytes(1,'little').hex()if slot<128 else prefix32+slot.to_bytes(4,'little').hex())
    def setup():
        nonlocal prepared
        if prepared:
            prepared=False
            return None
        context=None;reader=holder=False
        while True:
            p=peek()
            if p==('498bcd'if root else'498bce'):
                if reader:raise ValueError('levelscriptOwner.duplicate-reader-setup')
                g.take(p);reader=True
            elif p=='498b1f':
                if holder:raise ValueError('levelscriptOwner.duplicate-holder-setup')
                g.take(p);holder=True
            elif p=='488b15'and context is None:
                at=g.at;context=dict(instruction=at,cell=g.relative(p))
            else:break
        if not reader or not holder:raise ValueError('levelscriptOwner.same-reader-holder-required')
        return context

    if root:
        g.take('48895c2410','4889742418','48897c2420','55','4154','4155','4156','4157',
            '488bec','4881ec80000000','33db')
    else:g.take('48895c2418','48896c2420','56','57','4154','4156','4157','4881ec80000000','33db')
    if g.relative('4c8d25')!=image_base:raise ValueError('levelscriptOwner.module-base-register')
    initialized=g.relative('381d');g.take('4c8bfa','4c8be9'if root else'4c8bf1');g.branch('0f85',True)
    g.take('41837d3001'if root else'41837e3001');g.branch('7d',True,1)
    g.take('498b4550','440fb630','418b7d30')if root else g.take('498b4650','0fb628','418b7e30')
    g.take('83ef01');g.branch('79',True,1)
    g.take('49ff4550','41ff4540','41ff4544','41897d30','4180feff')if root else g.take('49ff4650','41ff4640','41ff4644','41897e30','4080fdff')
    g.branch('0f84',False);g.take('49391f');g.branch('0f85',True)
    header=g.at;g.take('4180fe1c'if root else'4080fd09');g.branch('0f85',False)

    for index,(field,(name,kind))in enumerate(zip(fields,plan,strict=True)):
        slot=field['offset'];start=g.at
        if kind=='path-hash64':
            g.take('41837e3008','498b3f');g.branch('7d',True,1)
            g.take('498b5e50','ba08000000','498bce','488b1b');site=g.at;target=g.relative('e8')
            g.take('4885ff');branch_false();g.take('488b4710','4885c0');branch_false()
            store('488958','488998',slot)
            reads.append(dict(memberIndex=index,fieldName=name,kind=kind,sourceCall=site,
                sourceTarget=target,storeOffset=slot,wireBytes=8,typedUsage=None,sourceStart=start))
            continue
        context=setup();site=g.at;target=g.relative('e8')
        if (context is not None)!=(kind=='enum32'or kind=='reference'):
            raise ValueError('levelscriptOwner.typed-source-presence:'+name)
        g.take('4885db');branch_false()
        if kind in('reference','pool'):
            g.take('4c8b4310','4d85c0');branch_false();flag()
            store('498940','498980',slot)
            if peek(1)=='74':g.branch('74',True,1)
            else:g.branch('0f84',True)
        elif kind=='float':
            g.take('488b4310','4885c0');branch_false()
            # This reader prepares the next bool before storing XMM0. Exact
            # preparation may not be consumed again or cross a child call.
            g.take('498b1f','498bcd');store('f30f1140','f30f1180',slot)
        else:
            g.take('488b4b10','4885c9');branch_false()
            prefixes=('8841','8881')if kind=='bool'else('488941','488981')if kind=='uint64'else('8941','8981')
            store(*prefixes,slot)
        reads.append(dict(memberIndex=index,fieldName=name,kind=kind,sourceCall=site,
            sourceTarget=target,storeOffset=slot,wireBytes={'bool':1,'int32':4,'enum32':4,'uint64':8,'float':4,'pool':4}.get(kind),
            typedUsage=context,sourceStart=start))
        if kind=='float':
            # The following bool call uses the already authenticated setup.
            next_field=fields[index+1]
            if plan[index+1]!=(next_field['name'],'bool'):raise ValueError('levelscriptOwner.float-successor')
            reads[-1]['nextSetupPrepared']=True
            prepared=True
    if root:
        g.take('4c8d9c2480000000','498b5b38','498b7340','498b7b48',
            '498be3','415f','415e','415d','415c','5d','c3')
    else:
        g.jump('eb',1);g.take('4c8d9c2480000000','498b5b40','498b6b48','498be3',
            '415f','415e','415c','5f','5e','c3')
    if len(set(flags))!=1:raise ValueError('levelscriptOwner.same-disabled-collector')
    return dict(selectedBytes=g.seen,originalType=original,memberCount=len(plan),memberHeader=header,
        orderedReads=reads,initializedFlag=initialized,collectorDisabledFlag=flags[0],
        headerBytes=1,entryReader='rcx',entryWrapperOutput='rdx',headerCursorFields=4,
        normalReturn=True,entryFrameRestored=True,existingWrapper=True,
        childGrammarAdmitted=False,liveFormatterSelectionObserved=False,
        condition='Initialized current generated reader, existing compatible original/wrapper, sufficient stable disjoint buffered bytes/storage, disabled collector and typed normal child effects. Creation/initialization/refill/error/active collector/runtime provider selection remain separate.')


def derive(image,pins):
    """Authenticate both nominal owners and every selected source/store join."""
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.protocol import canonical_type_name,native_enum_members
    from scripts.game_data.levelscript_family_regenerate import Build
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param,pooled_source_helper
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    build=Build(image,pins);ctx=NativeReferenceContext(image);base=image.pe.image_base
    offsets=scalar.reader_offsets(image,'levelscriptOwner');record=vector_recorder(image)
    proofs={};targets={}
    for original,plan in((ROOT,ROOT_FIELDS),(BRIEF,BRIEF_FIELDS)):
        wrapper,=[w for w in build.wrappers.values()if w.wrapped_type==original]
        if ctx.is_value_type(original)or ctx.field(wrapper.name+'::__instance')!=(wrapper.name,original,16):
            raise ValueError('levelscriptOwner.reference-owner-holder')
        mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
        fields=[]
        for member,(name,kind)in zip(wrapper.members,plan,strict=True):
            if member.name!=name:raise ValueError('levelscriptOwner.metadata-order:'+original)
            owner=build.wrappers[member.declaring_wrapper].wrapped_type
            actual=ctx.field(owner+'::'+name)
            if actual[1]!=member.declared_type:raise ValueError('levelscriptOwner.metadata-field-type:'+name)
            fields.append(dict(name=name,typeName=member.declared_type,kind=kind,offset=actual[2]))
        method=mm['Deserialize'];entry=image.method_pointer_va(method);body=owned(image,entry)
        program=owner_program(body['regions'],entry,original,fields,offsets,image_base=base)
        usages=[]
        for field,read in zip(fields,program['orderedReads'],strict=True):
            kind=field['kind'];target=read['sourceTarget']
            if read['typedUsage']is not None:
                usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='levelscriptOwner')
                expected='ReadUnmanaged'if kind=='enum32'else'ReadValue'if field['name']=='actionMap'else'ReadPackable'
                if (usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),
                    [canonical_type_name(t)for t in usage.get('methodArguments',[])])!=(6,'MemoryPack.MemoryPackReader',expected,[],[canonical_type_name(field['typeName'])]):
                    raise ValueError('levelscriptOwner.exact-typed-request:'+field['name'])
                if expected!='ReadUnmanaged':build.prove_reader_clone_target(target,'MemoryPack.MemoryPackReader.'+expected,result_abi='reference')
                usages.append(usage)
            if kind=='enum32':
                underlying=ctx.field(field['typeName']+'::value__')
                if underlying[1]!='int' or not ctx.is_value_type(field['typeName']):
                    raise ValueError('levelscriptOwner.enum-int32-backing:'+field['name'])
            if kind!='reference':targets.setdefault(kind,set()).add(target)
        proofs[original]=dict(wrapperName=wrapper.name,fields=fields,
            method=[method.index,wrapper.name,'Deserialize',entry-base],windows=body['windows'],
            program=program,typedUsages=usages)
    primitives={}
    for kind,pointers in targets.items():
        if len(pointers)!=1:raise ValueError('levelscriptOwner.one-primitive-target:'+kind)
        target,=pointers;source=record(target-base)
        if kind=='pool':checked=pooled_source_helper.validate_on_image(image,target,pins)
        elif kind=='bool':checked=scalar.boolean_source(image,source,offsets,'levelscriptOwner.bool')
        elif kind in('int32','enum32','uint64'):
            checked=scalar.integer_source(image,source,offsets,'levelscriptOwner.'+kind,width=8 if kind=='uint64'else 4)
        elif kind=='float':checked=primitive_param.single_source(image,source,offsets)
        elif kind=='path-hash64':checked=scalar.advance_source(image,record(target-base,fragments=True),offsets,'levelscriptOwner.path-hash64')
        else:raise ValueError('levelscriptOwner.unreviewed-primitive:'+kind)
        primitives[kind]=dict(targetRva=target-base,source=source,proof=checked)
    import json
    component_enum='Beyond.Gameplay.InteractiveComponentType'
    component,=[r for r in native_enum_members(image.metadata,image.body_index.enum_defaults,
        image.pe,image.registration,component_enum)if r['name']=='NarrativeComponent']
    param_enum='Beyond.GEnums.ParamRealType'
    string_kind,=[r for r in native_enum_members(image.metadata,image.body_index.enum_defaults,
        image.pe,image.registration,param_enum)if r['name']=='String']
    if ctx.field(param_enum+'::value__')[1]!='int':
        raise ValueError('levelscriptOwner.param-string-enum-int32-backing')
    return json.loads(json.dumps(dict(nativeInputs=pins,owners=proofs,primitiveSources=primitives,
        narrativeComponent=dict(typeName=component_enum,**component),
        paramStringType=dict(typeName=param_enum,**string_kind),
        childGrammarAdmitted=False,wholeOwnerAdmitted=False)))
