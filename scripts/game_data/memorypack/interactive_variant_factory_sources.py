"""Variant's own inline dictionary/list initialization and direct holder.

Only its exact selected typed allocations, constructor contexts, initialized
collector guards and full stores/frame are admitted. Called constructors are
owned current bodies with normal noninterfering returns required; their live
effects and child wire grammars are not inferred from a pointer or a default.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Core.InteractiveTemplateVariant'
LIST='System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>'
DICTIONARY='Beyond.SerializeFieldDictionary`2<string,Beyond.Gameplay.ParamListForGraph>'


def need(check,condition):
    if not condition:raise ValueError('interactiveVariantFactory.'+check)


def program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2420','56','4883ec20')
    flag=g.relative('803d')+1;g.take('00','488bf1');g.branch('75',True,1)
    allocation=dict(site=g.at,cell=g.relative('488b0d'));g.call(s['allocate'])
    g.take('488bd8','4885c0');g.branch('0f84',False);children=[]
    for i,offset in enumerate((136,144,152)):
        usage=dict(site=g.at,cell=g.relative('488b0d'))
        if i==0:g.take('48897c2438')
        g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
        method=dict(site=g.at,cell=g.relative('488b15'));g.take('488bc8')
        if i==0:g.take('48896c2430')
        ctor=g.relative('e8')
        if i<2:
            cell=g.relative('833d')+1;need('same-own-collector-before-child-store',cell==s['disabled']);g.take('00')
            if i==0:g.relative('488d2d')
            g.take('4889bb'+offset.to_bytes(4,'little').hex());g.branch('74',True,1)
        else:
            cell=g.relative('8b05');need('same-own-collector-before-last-child-store',cell==s['disabled'])
            g.take('4889bb'+offset.to_bytes(4,'little').hex(),'85c0');g.branch('74',True,1)
        children.append(dict(allocation=usage,methodContext=method,constructorTargetVa=ctor,fieldOffset=offset))
    # The third disabled edge skips the enabled-path reload. EAX still holds
    # the exact last observed zero; the intervening MOV preserves its value.
    g.take('48895e10','85c0');g.branch('74',True,1)
    g.take('488b6c2430','488b7c2438','488b5c2448','4883c420','5e','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,allocation=allocation,allocationTarget=s['allocate'],
        childInitializations=children,baseHolderOffset=16,typedCacheOffset=None,
        inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],sameAllocatedOriginalStored=True,
        entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
        enabledCollectorAdmitted=False,childGrammarAdmitted=False,originalConstructorCalled=False)


def derive(image,ctx,wrapper,body,s,original_ctor):
    if wrapper.wrapped_type!=TYPE:return NotImplemented
    if not body['regions'][0][1].startswith(bytes.fromhex('48895c2420564883ec20')):return NotImplemented
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar,pointer_param as pointer
    proof=program(body['regions'],body['pointer'],s);base=image.pe.image_base;md=image.metadata
    original=derive_typed_usage_context(image,proof['allocation']['site']-base,label='interactiveVariantFactory.original')
    need('own-exact-original-allocation',(original['tag'],original['typeName'])==(1,TYPE))
    fields=[]
    for f in md.fields_for(ctx.index.types[TYPE]):
        if ctx.field_attributes(f.type_index)&16:continue
        name=md.string(f.name_index);fields.append((f,ctx.field(TYPE+'::'+name)))
    children=[]
    for row,expected in zip(proof['childInitializations'],(DICTIONARY,LIST,LIST),strict=True):
        allocated=derive_typed_usage_context(image,row['allocation']['site']-base,label='interactiveVariantFactory.collection')
        usage=derive_typed_usage_context(image,row['methodContext']['site']-base,label='interactiveVariantFactory.constructor')
        args=['string','Beyond.Gameplay.ParamListForGraph']if expected==DICTIONARY else['Beyond.Gameplay.ParamKeyValue']
        owner='Beyond.SerializeFieldDictionary`2'if expected==DICTIONARY else'System.Collections.Generic.List`1'
        need('exact-own-typed-collection-and-constructor',(allocated['tag'],allocated['typeName'])==(1,expected)
            and(usage['tag'],usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])==(6,owner,'.ctor',args,[]))
        method=md.methods[usage['methodSpec'][0]]
        scalar.owned_method_abi(image,ctx,method.index,ctx.index.types[owner].index,('void',1,False),[],'interactiveVariantFactory.constructor')
        matching=[(f,fact)for f,fact in fields if fact[2]==row['fieldOffset']]
        need('one-current-named-collection-field',len(matching)==1);field,fact=matching[0]
        need('same-exact-field-collection-type',fact[1]==expected)
        raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16);carrier=bytes.fromhex(allocated['typeRawHex'])
        need('same-closed-reference-carrier',raw[10:12]==carrier[10:12]==bytes((21,0))and raw[:8]==carrier[:8])
        actual=pointer.owned(image,row['constructorTargetVa'])
        children.append(dict(allocation=allocated,methodContext=usage,field=fact,
            actualConstructorTargetRva=actual['pointer']-base,actualConstructorWindows=actual['windows'],
            actualConstructorIsRegisteredPointerInferred=False,normalNoninterferingConstructorReturnRequired=True,
            constructorEffectsProved=False))
    return dict(program=proof,originalConstructor=None,proof=dict(wrapperName=wrapper.name,typeName=TYPE,
        completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,originalAllocation=original,
        collectionInitializations=children,condition=__doc__))
