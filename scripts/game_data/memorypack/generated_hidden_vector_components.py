"""Pure exact cached-setter joins for actual hidden Vector3 returns.

The source owns the full setter windows, getter, lifecycle and whole caller.
This replay checks the selected bytes and exact getter target independently;
its twelve-byte value coverage is not inferred from a flag on another setter
profile. Untaken edges retain owned extents without claiming their bodies.
"""


def need(check,condition):
    if not condition:raise ValueError('generatedHiddenVectorComponents.'+check)


def _inherited_observer_setter(source,read,setter,life,getter):
    """The two guide records execute Observer's own typed cached setter."""
    parents=('Beyond.Gameplay.Core.ShowGuideComponentData','Beyond.Gameplay.Core.ShowGuideWithConditionComponentData')
    original='Beyond.Gameplay.Core.ObserverComponentData'
    wrapper='Beyond.MemoryPack.Beyond_Gameplay_Core_ObserverComponentDataForMemoryPack'
    if source.get('wrappedType')not in parents:return False
    from scripts.game_data.memorypack.generated_reader_sources import constructed_getter_join
    construction=constructed_getter_join(life,source['setters'])
    joins=[r for r in construction.get('setters',[])if r.get('method')==setter.get('method')]
    refresh=getter.get('compatibleRefresh',{});paths=refresh.get('programs',[])
    fields={1:'center',4:'size'}
    return(read.get('memberIndex')in fields and read.get('fieldName')==fields[read['memberIndex']]
        and read.get('declaredType')=='UnityEngine.Vector3'
        and setter.get('method',[None,None])[1]==getter.get('method',[None,None])[1]==wrapper
        and setter.get('member',{}).get('declaringWrapper')==wrapper
        and setter.get('targetField')==original+'::'+read['fieldName']
        and getter.get('typedCache')==[wrapper,original,32]
        and getter.get('baseHolder')==life.get('baseHolder')
        and construction==source.get('constructedGetterJoin')
        and construction.get('inheritedCacheCoherenceAssumed')is False
        and joins==[dict(method=setter['method'],cacheOffset=32,mode='exact-compatible-refresh-from-constructed-base')]
        and refresh.get('initializedCompatibleNonNullBaseRequired')is True
        and refresh.get('emptyOrDifferentCacheAdmitted')is True
        and {p.get('path')for p in paths}=={'empty','different'}
        and len(paths)==2 and all(p.get('program',{}).get('baseSlot')==life['baseHolder'][2]
            and p.get('program',{}).get('cacheSlot')==32 for p in paths))


def cached_setter(source,scope,read,setter,pins,*,type_name='UnityEngine.Vector3',width=12):
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    from scripts.game_data.memorypack.generated_vector_member_sources import setter_program
    need('finite-named-vector-profile',(type_name,width)in(('UnityEngine.Vector3',12),('UnityEngine.Quaternion',16)))
    index=read.get('memberIndex');life=source.get('lifecycle',{});getter=setter.get('getter')or{}
    method=setter.get('method',[]);getter_method=getter.get('method',[]);program=setter.get('program',{})
    inherited=_inherited_observer_setter(source,read,setter,life,getter)
    need('same-actual-hidden-vector-source',source.get('nativeInputs')==scope.get('nativeInputs')==pins
        and source.get('sourceScope')==scope and type(index)is int and 0<=index<len(source.get('setters',[]))
        and index<len(scope.get('richSetters',[]))and source['setters'][index]==setter==scope['richSetters'][index]
        and read.get('declaredType')==type_name and read.get('kind')=='value'+str(width)+':'+type_name
        and read.get('mode')=='typed-hidden-value')
    selected=program.get('selectedBytes',[])
    need('literal-own-cached-setter',setter.get('profile')=='cached-getter-setter'
        and len(method)==len(getter_method)==4 and type(method[3])is int and method[3]>0
        and type(getter_method[3])is int and getter_method[3]>0 and bool(selected)
        and type(selected[0][0])is int and selected[0][0]>=method[3]
        and (inherited or method[1]==getter_method[1]==source.get('wrapperName')
            and setter.get('targetField')==source.get('wrappedType')+'::'+str(read.get('fieldName')))
        and type(setter.get('fieldOffset'))is int and setter['fieldOffset']>=16
        and type(setter.get('storedBytes'))is int and setter['storedBytes']==width
        and setter.get('member',{}).get('declaredType')==type_name
        and setter.get('incomingValueStoredUnchanged')is True
        and program.get('storedBytes')==width and program.get('fullValueStoredUnchanged')is True
        and program.get('normalFrameAndReturn')is True)
    need('same-own-coherent-getter-and-cache',(inherited or getter.get('method')==life.get('coherentGetter',{}).get('method')
        and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
        and isinstance(life.get('typedCache'),list)and len(life['typedCache'])==3
        and life['typedCache'][:2]==[source['wrapperName'],source['wrappedType']])
        and getter.get('coherentNonNullSamePointerReturn')is True
        and all(getter.get('program',{}).get(k)is True for k in
            ('fullSameReferenceReturned','entryRspRestored','normalReturn')))
    base=selected[0][0]-method[3]
    value=scope.get('valueTypeSources',{}).get(str(index),{});typed=value.get('typedSource',{})
    nominal=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('own-ordinary-vector-parameter',len(nominal)==16 and nominal[10:12]==bytes((17,128))
        and int.from_bytes(nominal[:8],'little')==value.get('layout',{}).get('typeDefinition'))
    entry_program=typed.get('proof',{}).get(
        'forwarderProgram'if typed.get('contextMode')=='owned-closed-forwarder'else'actualProgram',{})
    entry_bytes=entry_program.get('selectedBytes',[])
    need('same-actual-source-image-base',bool(entry_bytes)and type(typed.get('targetRva'))is int
        and entry_bytes[0][0]-typed['targetRva']==base)
    replay=setter_program([(at,bytes.fromhex(raw))for at,raw in selected],base+method[3],
        getter=base+getter_method[3],field=setter['fieldOffset'],width=width,
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,setter.get('codeWindows',[]),base))
    replay['selectedBytes']=[[at,raw]for at,raw in replay['selectedBytes']]
    need('whole-cached-vector-setter-replayed',replay==program)
