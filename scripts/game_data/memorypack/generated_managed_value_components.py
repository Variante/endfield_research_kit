"""Typed managed-value compiler joins with an explicit domain-owned binder.

The common gate owns the actual nominal Reader request and E8. The callable
binder must separately prove its domain's exact source, caller local/field
transfer, frame and independent wire capability. Managed bytes never select
a wire width. This pure helper opens no native image and grants no admission.
"""
LABEL='generatedManagedValueComponents'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def require_transfer(source,scope,read,pins,*,source_context=None):
    """Join an already source-proved managed return to its complete field path.

    This pure check supplies no nominal wire grammar and accepts no width as a
    grammar. The domain binder still owns its exact value fields, padding and
    independent positive/default wire capability.
    """
    index=read.get('memberIndex');name=read.get('declaredType');width=read.get('managedBytes')
    declaration_context=read.get('context',{})
    if source_context is not None:
        actual=scope.get('managedValueSources',{}).get(str(index),{})
        if name=='Beyond.LangKey':
            from scripts.game_data.memorypack.module_lang_key_value_bindings import owns_member,require_source
            need('finite-explicit-internal-Module-LangKey-context',owns_member(source.get('wrappedType'),read.get('fieldName'),name)
                and source_context==actual.get('proof',{}).get('internalContext'))
            require_source(actual,read,pins,actual.get('proof',{}).get('typedRequest',{}))
        else:
            from scripts.game_data.memorypack.generated_managed_forwarder_components import TYPE,require_source
            need('finite-explicit-internal-Query-source-context',name==TYPE
                and read.get('sourceContextMode')=='owned-closed-forwarder'
                and source_context==actual.get('proof',{}).get('internalContext'))
            require_source(actual,read,pins,actual.get('proof',{}).get('typedRequest',{}))
        declaration_context=source_context
    need('complete-current-managed-parent',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==pins
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False and source.get('sourceScope')==scope
        and type(index)is int and index>=0 and type(width)is int and width in(8,16)
        and read.get('kind')=='managed:'+str(name)and read.get('mode')=='typed-managed-value'
        and read.get('actualSourceProved')is True and'wireBytes'not in read)
    reads=source.get('orderedSourceReads',[])
    need('same-owned-managed-member',index<len(reads)and reads[index]==read and scope.get('events')==reads)
    setters=source.get('setters',[]);rich_setters=scope.get('richSetters',[])
    need('same-fresh-managed-setter',index<len(setters)and index<len(rich_setters)and setters[index]==rich_setters[index])
    setter=setters[index];layout=setter.get('managedValueLayout',{});program=setter.get('program',{})
    lanes=read.get('referenceLaneOffsets');padding=layout.get('paddingByteRanges')
    need('literal-managed-reference-lanes',type(lanes)is list and bool(lanes)
        and all(type(n)is int and n>=0 and n+8<=width for n in lanes)
        and lanes==sorted(set(lanes))and all(a+8<=b for a,b in zip(lanes,lanes[1:])))
    need('exact-current-managed-layout',layout.get('typeName')==name and type(layout.get('managedBytes'))is int
        and layout['managedBytes']==width and layout.get('referenceLaneOffsets')==lanes
        and layout.get('wireGrammarAdmitted')is False and type(layout.get('typeDefinition'))is int
        and layout['typeDefinition']==declaration_context.get('typeDefinition'))
    need('literal-managed-padding',type(padding)is list and all(isinstance(p,list)and len(p)==2
        and all(type(n)is int for n in p)and 0<=p[0]<p[0]+p[1]<=width for p in padding))
    padding_bytes=[b for start,length in padding for b in range(start,start+length)]
    need('disjoint-managed-padding',len(padding_bytes)==len(set(padding_bytes))
        and not set(padding_bytes)&{b for lane in lanes for b in range(lane,lane+8)})
    method=setter.get('method',[]);member=setter.get('member',{});parameter=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('same-named-owned-managed-setter',len(method)==4 and type(method[0])is int and type(method[3])is int
        and method[0]==member.get('methodIndex')and method[1]==member.get('declaringWrapper')
        and method[2]=='set___'+str(read.get('fieldName'))+'__'
        and member.get('name')==read.get('fieldName')and member.get('declaredType')==name
        and type(setter.get('fieldOffset'))is int and setter['fieldOffset']>=16
        and type(setter.get('targetField'))is str and setter['targetField'].endswith('::'+str(read.get('fieldName')))
        and len(parameter)==16 and parameter[10:12]==bytes((17,128))
        and int.from_bytes(parameter[:8],'little')==layout['typeDefinition'])
    need('complete-unchanged-managed-setter',setter.get('incomingValueStoredUnchanged')is True
        and setter.get('childGrammarAdmitted')is False and setter.get('factoryAdmitted')is False
        and type(setter.get('storedBytes'))is int and setter['storedBytes']==width
        and type(program.get('storedBytes'))is int and program['storedBytes']==width
        and type(program.get('managedBytes'))is int and program['managedBytes']==width
        and program.get('referenceLaneOffsets')==lanes and type(program.get('barrierReferenceLaneOffset'))is int
        and program['barrierReferenceLaneOffset']in lanes and bool(program.get('selectedBytes'))
        and all(program.get(k)is True for k in('wholeInputBitsStoredUnchanged','disabledCollectorRequired',
            'entryRspRestored','normalReturnViaBarrier')))
    rich=scope.get('richProgram',{})
    need('complete-managed-rich-program',rich.get('completeSelectedNormalProgram')is True
        and rich.get('childGrammarAdmitted')is False and rich.get('wholeOwnerAdmitted')is False
        and bool(rich.get('selectedProgram')))
    sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    need('one-exact-managed-source',len(sources)==1 and sources[0].get('instruction')==read.get('instruction')
        and sources[0].get('resultAbi')==read.get('resultAbi')and read.get('resultAbi')==('rax'if width==8 else'hidden-local'))
    selected=rich['selectedProgram'];stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index];covered=[]
    for store in stores:
        start=store.get('sourceOffset');size=store.get('storedBytes')
        need('literal-managed-field-store',type(start)is int and type(size)is int and 0<=start<start+size<=width
            and store.get('instruction')in selected)
        covered.extend(range(start,start+size))
    need('complete-once-managed-field-coverage',len(covered)==width and sorted(covered)==list(range(width)))
    need('actual-managed-source-in-rich-path',read.get('instruction')in selected)
    paths=source.get('programs',[])
    need('complete-managed-new-existing-FF-frames',len(paths)==4
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
            and p.get('frame',{}).get('entryRspRestored')is True
            and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    hidden=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
    if width==16:
        need('exact-owned-hidden-managed-local',len(hidden)==1 and type(hidden[0].get('bytes'))is int
            and hidden[0]['bytes']==width and type(hidden[0].get('displacement'))is int
            and 32<=hidden[0]['displacement']<256 and hidden[0].get('sourceInstruction')==read['instruction'])
        need('hidden-managed-local-owned-by-full-frame',all(any(type(h[0])is int and type(h[1])is int and h[1]==width
            for h in p['frame'].get('hiddenSourceLocalHomes',[]))for p in paths if not p['wrapperNull']))
    else:need('RAX-managed-value-has-no-hidden-local',hidden==[])
    return dict(memberIndex=index,fieldName=read['fieldName'],typeName=name,managedBytes=width,resultAbi=read['resultAbi'],
        referenceLaneOffsets=lanes,paddingByteRanges=padding,sourceInstruction=read['instruction'],
        setterMethod=method,fieldOffset=setter['fieldOffset'],fieldStores=stores,hiddenSourceLocal=hidden[0]if hidden else None,
        completeFieldTransferAndFrameProved=True,wireGrammarAdmitted=False)


def bind_member(source,scope,read,pins,usage,component,capability,*,binder):
    need('callable-domain-binder',callable(binder))
    if read.get('declaredType')=='Beyond.Gameplay.View.Animation.AlphaBlend':
        from scripts.game_data.memorypack.alpha_blend_value_bindings import bind
        return bind(source,scope,read,pins,usage,component,capability)
    if read.get('declaredType')=='Beyond.Gameplay.BodyTypeDef':
        from scripts.game_data.memorypack.body_type_value_bindings import bind
        return bind(source,scope,read,pins,usage,component,capability)
    if read.get('declaredType')=='Beyond.LangKey'and read.get('sourceContextMode')=='owned-closed-forwarder':
        from scripts.game_data.memorypack.module_lang_key_value_bindings import owns_member,bind
        if owns_member(source.get('wrappedType'),read.get('fieldName'),read['declaredType']):
            return bind(source,scope,read,pins,usage,component,capability)
    if read.get('declaredType')=='Beyond.Gameplay.Core.EntityPtr':
        from scripts.game_data.memorypack.module_entity_ptr_value_bindings import owns_member,bind
        if owns_member(source.get('wrappedType'),read.get('fieldName'),read['declaredType']):
            return bind(source,scope,read,pins,usage,component,capability)
        from scripts.game_data.memorypack.leveldata_entity_ptr_value_bindings import bind
        return bind(source,scope,read,pins,usage,component,capability)
    if read.get('declaredType')=='Beyond.Gameplay.Core.SkMorphPlaySetting':
        from scripts.game_data.memorypack.sk_morph_value_bindings import bind
        return bind(source,scope,read,pins,usage,component,capability)
    # This explicit nominal owner proves its own forty-byte ABI. The ordinary
    # managed8/16 transfer gate below remains unchanged for every other type.
    if read.get('declaredType')=='Beyond.Gameplay.Core.SmartTargetSelectSetting':
        from scripts.game_data.memorypack.skill_smart_target_value_bindings import bind
        return bind(source,scope,read,pins,usage,component,capability)
    if read.get('declaredType')=='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition':
        from scripts.game_data.memorypack.skill_impulse_envelope_bindings import bind
        return bind(source,scope,read,pins,usage,component,capability)
    if read.get('declaredType')=='Beyond.Gameplay.Core.GameplayTagQuery'and read.get('sourceContextMode')=='owned-closed-forwarder':
        from scripts.game_data.memorypack.skill_action_managed_value_bindings import bind
        return bind(source,scope,read,pins,usage,component,capability)
    nominal=read['declaredType'];index=read['memberIndex'];context=read.get('context',{})
    actual=scope.get('managedValueSources',{}).get(str(index),{})
    need('exact-source-owned-managed-value',source.get('nativeInputs')==scope.get('nativeInputs')==actual.get('nativeInputs')==pins
        and type(index)is int and index>=0 and read.get('kind')=='managed:'+nominal
        and read.get('mode')=='typed-managed-value'and'wireBytes'not in read
        and type(read.get('managedBytes'))is int and read['managedBytes']in(8,16)
        and read.get('resultAbi')in('rax','hidden-local')
        and actual.get('typeName')==nominal and actual.get('managedBytes')==read['managedBytes']
        and actual.get('actualSourceProved')is True and actual.get('resultAbi')==read['resultAbi']
        and type(read.get('sourceTargetRva'))is int and read['sourceTargetRva']>0
        and actual.get('sourceTargetRva')==read['sourceTargetRva'])
    raw=bytes.fromhex(context.get('argumentRawHex',''));instruction=bytes.fromhex(context.get('instructionHex',''))
    prefix=bytes.fromhex('488B15'if read['resultAbi']=='rax'else'4C8B05')
    need('actual-ordinary-value-MethodInfo',len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==context.get('typeDefinition')
        and len(instruction)==7 and instruction[:3]==prefix
        and type(context.get('instructionRva'))is int and context['instructionRva']>=0
        and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('typeKind'))==
            ('MemoryPack.MemoryPackReader','ReadValue',nominal,17))
    need('same-actual-managed-value-request',actual.get('proof',{}).get('typedRequest')==usage
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
        and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadValue',[],[nominal])
        and isinstance(usage.get('methodSpec'),list)and len(usage['methodSpec'])==3
        and type(usage['methodSpec'][0])is int and usage['methodSpec'][0]>0
        and actual.get('readerMethodDefinition')==usage['methodSpec'][0])
    site,encoded=read['instruction'];call=bytes.fromhex(encoded)
    need('actual-managed-value-E8',type(site)is int and len(call)==5 and call[0]==232
        and site+5+int.from_bytes(call[1:],'little',signed=True)==read['sourceTargetRva'])
    cap=component.get('capabilities',{}).get(capability,{})
    need('independent-nominal-wire-child',component.get('nativeInputs')==pins and cap.get('typeName')==nominal)
    binding=binder(source,scope,read,pins,usage,component,capability)
    need('exact-domain-binding-result',isinstance(binding,dict)
        and(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],nominal,capability)
        and type(binding.get('readerMethodDefinition'))is int and binding['readerMethodDefinition']==usage['methodSpec'][0]
        and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==read['sourceTargetRva'])
    return binding
