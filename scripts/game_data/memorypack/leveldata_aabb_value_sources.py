"""Own inline AABB wrapper programs; canonical value and parent stay separate.

The stored wrapper reads max and min as two independently typed raw Vector2
sources. Its null marker clears the wrapper reference. An Original AABB default
and its managed16 return require a separate canonical-adapter proof; neither
is inferred from this wrapper's physical size or reference-null branch.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.AABB'
WRAPPER='Beyond.MemoryPack.Beyond_AABBForMemoryPack'
FIELDS=(('max','UnityEngine.Vector2',24),('min','UnityEngine.Vector2',16))


def need(check,condition):
    if not condition:raise ValueError('polylineAabbValue.'+check)


def wrapper_program(regions,entry,*,new=False,ff=False,symbols=None):
    """Complete own warmed wrapper path, including both source/store pairs."""
    need('literal-wrapper-path',type(new)is bool and type(ff)is bool and(symbols is None or type(symbols)is dict))
    g=BytesPath(regions,entry);roles={};reads=[];allocation=None
    def call(role):
        at=g.at;target=g.relative('e8')
        need('same-called-role:'+role,role not in roles or roles[role]==target)
        if symbols is not None:need('independent-called-role:'+role,symbols.get(role)==target)
        roles[role]=target;return at
    g.take('48895c2410','4889742418','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','488bda','488bf9');g.branch('75',True,1)
    g.take('488d542430','c644243000','488bcf');header=call('header');g.take('84c0');g.branch('0f84',ff)
    if ff:
        g.take('488bcb','48c70300000000');call('barrier')
    else:
        g.take('48833b00');g.branch('75',not new,1)
        if new:
            allocation=dict(instructionVa=g.at,classCellVa=g.relative('488b0d'))
            call('allocate');g.take('4885c0');g.branch('74',False,1)
            g.take('0f57c0','488bcb','0f114010','488903');call('barrier')
        g.take('807c243002');g.branch('75',False,1)
        for index,(name,declared,offset)in enumerate(FIELDS):
            context=dict(instructionVa=g.at,cellVa=g.relative('488b15'))
            if index==0:g.take('488bcf','488b33')
            else:g.take('488b1b')
            site=call('vector2');g.take('4889442430','4885f6'if index==0 else'4885db');g.branch('74',False,1)
            g.take('f30f10442430')
            if index==0:g.take('488bcf')
            g.take('f30f104c2434',('f30f1146'if index==0 else'f30f1143')+bytes((offset,)).hex(),
                ('f30f114e'if index==0 else'f30f114b')+bytes((offset+4,)).hex())
            reads.append(dict(fieldName=name,typeName=declared,context=context,sourceCallVa=site,
                managedInputBytes=8,sourceLocalRspRange=[48,56],stores=[[offset,4],[offset+4,4]],
                completeInputBitsStoredUnchanged=True))
        g.jump('eb',1)
    g.take('488b5c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlagVa=flag,newWrapper=new,wrapperFF=ff,headerCallVa=header,
        headerLocalRspRange=[48,49],typedAllocation=allocation,orderedReads=reads,symbolTargets=roles,
        inlineHolderOffset=16,managedBytes=16,wrapperReferenceClearedBytes=8 if ff else 0,
        canonicalOriginalDefaultAdmitted=False,wireGrammarAdmitted=False,parentFieldAdmitted=False,
        entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True)


def wrapper_frame(program):
    """The complete literal schedule owns header/raw8 lifetimes and saved homes."""
    need('whole-owned-wrapper-program',program.get('normalReturn')is True and program.get('entryRspRestored')is True
        and program.get('allIntegerNonvolatilesRestored')is True and type(program.get('wrapperFF'))is bool
        and type(program.get('newWrapper'))is bool and program.get('headerLocalRspRange')==[48,49])
    delta=-40;saved={'rbx':[16,24],'rsi':[24,32],'rdi':[-8,0]};header=[8,9]
    need('separate-header-and-saved-homes',all(header[1]<=a or b<=header[0]for a,b in saved.values()))
    reads=program.get('orderedReads',[])
    if program['wrapperFF']:need('FF-clears-reference-without-value-read',reads==[] and program.get('wrapperReferenceClearedBytes')==8)
    else:
        need('own-two-complete-vector2-fields',[(r.get('fieldName'),r.get('stores'),r.get('sourceLocalRspRange'))for r in reads]
            ==[(n,[[o,4],[o+4,4]],[48,56])for n,t,o in FIELDS])
        need('raw8-local-separate-from-all-saved-homes',all(16<=a or b<=8 for a,b in saved.values()))
    return dict(entryRspDelta=delta,savedEntryHomes=saved,headerEntryRange=header,
        raw8LocalEntryRange=None if program['wrapperFF']else[8,16],
        headerRetiredBeforeRaw8Reuse=not program['wrapperFF'],eachRaw8RetiredAfterBothNamedScalarStores=not program['wrapperFF'],
        callShadowRspRange=[0,32],entryRspRestored=True,allIntegerNonvolatilesRestored=True,
        compatibleNormalChildAbiPreservesFrameRequired=True,wholeSelectedWrapperFrameProved=True)


def layout(image,ctx):
    """Exact own two Vector2 fields and their independent native scalar layout."""
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('plain-current-AABB-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)and td.generic_container_index<0)
    scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,'polylineAabbValue.Original')
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]
    need('own-complete-two-fields',actual==[('min','UnityEngine.Vector2',16),('max','UnityEngine.Vector2',24)])
    for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),17,'polylineAabbValue.field')
    vector=ctx.index.types['UnityEngine.Vector2']
    vf=[f for f in md.fields_for(vector)if not ctx.field_attributes(f.type_index)&16]
    need('own-Vector2-scalar-layout',ctx.is_value_type('UnityEngine.Vector2')and vector.generic_container_index<0
        and[(md.string(f.name_index),*ctx.field('UnityEngine.Vector2::'+md.string(f.name_index))[1:])for f in vf]
            ==[('x','float',16),('y','float',20)])
    for field in vf:scalar.ordinary(image,ctx.type_pointer(field.type_index),12,'polylineAabbValue.Vector2Scalar')
    sizes={}
    for name,expected in((TYPE,(32,16)),('UnityEngine.Vector2',(24,8))):
        definition=ctx.index.types[name];need('own-size-row-index',0<=definition.index<image.registration['typeDefinitionsSizesCount'])
        at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
        pair=(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))
        need('own-size-row:'+name,pair==expected);sizes[name]=list(pair)
    return dict(typeName=TYPE,typeDefinition=td.index,fields=[list(r)for r in actual],managedBytes=16,
        referenceLaneOffsets=[],paddingByteRanges=[],sizeRows=sizes,wireGrammarAdmitted=False)


def derive_wrapper(image,pins):
    """Fresh own four wrapper paths and both independently typed Vector2 reads."""
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.vector2_source import validate_vector2_source
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE and w.name==WRAPPER]
    need('one-own-nominal-wrapper',len(wrappers)==1);wrapper,=wrappers
    need('exact-own-stored-field-order',[(m.name,m.declared_type)for m in wrapper.members]==[(n,t)for n,t,o in FIELDS])
    nominal=layout(image,ctx)
    need('own-inline-wrapper-holder',ctx.field(WRAPPER+'::__instance')==(WRAPPER,TYPE,16))
    wrapper_td=ctx.index.types[WRAPPER]
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+wrapper_td.index*8)
    need('own-wrapper-instance-size',image.pe.u32_at_va(size)==32)
    method=pointer.methods(image,wrapper)['Deserialize']
    primitive_param.reader_abi(image,ctx,method,wrapper);entry=image.method_pointer_va(method);body=pointer.owned(image,entry)
    first=wrapper_program(body['regions'],entry,new=True);symbols=first['symbolTargets']
    programs=[first]+[wrapper_program(body['regions'],entry,new=new,ff=ff,symbols=symbols)
        for new,ff in((False,False),(True,True),(False,True))]
    frames=[wrapper_frame(p)for p in programs]
    allocation=derive_typed_usage_context(image,first['typedAllocation']['instructionVa']-base,label='polylineAabbValue.allocation')
    need('own-typed-allocation',allocation.get('tag')==1 and allocation.get('typeName')==WRAPPER
        and base+allocation['usageCellRva']==first['typedAllocation']['classCellVa'])
    scalar.ordinary(image,ctx.type_pointer(allocation['typeIndex']),18,'polylineAabbValue.allocation',reference=True)
    vectors=[]
    for read in first['orderedReads']:
        usage=derive_typed_usage_context(image,read['context']['instructionVa']-base,label='polylineAabbValue.Vector2')
        need('actual-own-Vector2-MethodInfo',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],['UnityEngine.Vector2'])
            and base+usage['usageCellRva']==read['context']['cellVa'])
        child=validate_vector2_source(image,usage,symbols['vector2']-base)
        need('complete-own-Vector2-source',child.get('status')=='validated'and child.get('sourceRva')==symbols['vector2']-base)
        vectors.append(dict(fieldName=read['fieldName'],typedRequest=usage,source=child))
    recorder=vector_recorder(image);header=recorder(symbols['header']-base)
    offsets=scalar.reader_offsets(image,'polylineAabbValue')
    primitive_param.object_header_source(image,header,offsets)
    barrier,barrier_program,_=_fast_barrier(image,symbols['barrier'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.leveldata-AABB-wrapper-source.v1',
        status='proved-current-AABB-wrapper-source',nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,
        sourceMethod=[method.index,WRAPPER,'Deserialize',entry-base],nominal=nominal,allocation=allocation,
        programs=programs,frames=frames,vectors=vectors,header=header,readerOffsets=offsets,
        barrier=dict(source=barrier,program=barrier_program),sourceFamily=image.unwind_index.family(entry-base),
        sourceWindows=body['windows'],sourceRegions=[[a-base,b.hex().upper()]for a,b in body['regions']],
        symbolRvas={k:v-base for k,v in symbols.items()},
        wrapperSourceComplete=True,canonicalOriginalDefaultAdmitted=False,canonicalOriginalGetterAdmitted=False,
        wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own current inline-value wrapper declarations, all four warmed wrapper/FF paths, actual max/min raw8 Vector2 source calls and stores, own object header and reference clear, full saved integer homes and retired shared header/raw8 lifetimes.',
            conditional='Ready coherent exact metadata and normal valid typed allocation/Vector2/disabled-barrier helpers, stable disjoint Reader/wrapper/source/frame storage and sufficient buffered input.',
            unresolved=['canonical Original AABB default/return and provider selection','actual containing Node field transfer','whole Polyline grammar and EOF']))))
