"""Exact finite EntityPtr40 Module fields and their independent MC3 value.

The runtime ObjectPtr tail is copied unchanged and remains opaque. This lane
owns only named finite Module/Beacon callers, their actual closed MethodInfo,
whole setter, hidden/argument locals and all enclosing frames. It neither
widens the ordinary EntityPtr parent nor assigns a runtime reference map.
"""
from scripts.game_data.memorypack import generated_module_value_forwarder_sources as forwarder
from scripts.game_data.memorypack import generated_entity_ptr_field_sources as field
from scripts.game_data.memorypack import leveldata_entity_ptr_components as owner
from scripts.game_data.memorypack import leveldata_entity_ptr_value_bindings as ordinary

TYPE=field.TYPE
CAPABILITY=owner.CAP
CLOSED_RBP={('Beyond.Gameplay.RaceData','finalInteractive'),
    ('Beyond.Gameplay.TianshizhuangData','proxyInteractive')}
ORDINARY_MEMBERS={('Beyond.Gameplay.GuideButterflyModuleData','leaderButterflyEntityPtr'),
    ('Beyond.Gameplay.SuperPressureBoardGroupData','switchEntityPtr')}


def owns_member(parent,name,nominal):
    return forwarder.owns_closed_member(parent,name,nominal)or(nominal==TYPE and(parent,name)in ORDINARY_MEMBERS)


def need(check,condition):
    if not condition:raise ValueError('moduleEntityPtrValueBindings.'+check)


def _same(left,right):
    return ordinary.same(left,right)


def _regions(rows,windows,base,label):
    from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions
    return _owned_regions(rows,windows,base=base,label=label)


def _source(actual,pins):
    """Replay the actual closed forwarder and the independent hidden40 source."""
    if actual.get('schema')=='endfield.story-entity-ptr-value-source.v1':
        base=ordinary._read_source(actual,pins)
        return actual,None,base
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    need('own-closed-Entity40-source',actual.get('schema')==forwarder.SCHEMA
        and actual.get('status')=='proved-conditional-owned-Module-ReadValue-forwarder'
        and actual.get('nativeInputs')==pins and actual.get('typeName')==TYPE
        and actual.get('managedBytes')==40 and actual.get('resultAbi')=='hidden-local'
        and actual.get('sourceContextMode')==actual.get('contextMode')=='owned-closed-forwarder'
        and actual.get('actualSourceProved')is True and actual.get('pointerAliasClaimed')is False
        and actual.get('wireGrammarAdmitted')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False)
    proof=actual['proof'];nested=proof['nestedSource'];context=proof['internalContext']
    base=ordinary._read_source(nested,pins);forwarder.context_shape(context,TYPE)
    program=forwarder_program(_regions(proof['actualSourceRegions'],proof['actualWindows'],base,'Module-Entity-forwarder'),
        base+actual['sourceTargetRva'])
    need('whole-own-forwarder-byte-program',_same(program,proof['forwarderProgram'])
        and program['nestedTargetVa']==base+nested['sourceTargetRva']
        and program['contextInstructionVa']==base+context['instructionRva']
        and actual['readerMethodDefinition']==nested['readerMethodDefinition']==context['methodSpec'][0]
        and proof['typedRequest']==nested['proof']['typedRequest']
        and proof['actualFamily'].get('selectedPrimaryRva')==actual['sourceTargetRva'])
    request=proof['typedRequest'];raw=bytes.fromhex(context['instructionHex'])
    need('same-own-nominal-internal-R8-MethodInfo',
        all(context[k]==request[k]for k in('instructionRva','instructionHex','methodSpec'))
        and(request.get('tag'),request.get('typeName'),request.get('methodName'),request.get('classArguments'),request.get('methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
        and len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')
        and base+context['instructionRva']+7+int.from_bytes(raw[3:],'little',signed=True)
            ==context['cellVa']==base+request['usageCellRva'])
    return nested,context,base


def component(actual,pins):
    """The existing dedicated MC3 capability; no enclosing field grant."""
    nested,_,_=_source(actual,pins)
    return dict(schema='endfield.story-entity-ptr-value-component.v1',nativeInputs=pins,
        capabilities={CAPABILITY:owner.capability(nested)},proof=dict(readSource=nested),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def _setter(source,scope,read,setter,nested,base):
    from scripts.game_data.memorypack.generated_member_sources import coherent_getter_program
    method=setter.get('method',[]);member=setter.get('member',{});getter=setter.get('getter')or{}
    life=source.get('lifecycle',{});program=setter.get('program',{});index=read['memberIndex']
    need('same-whole-named-Entity40-setter',len(method)==4 and method[1]==source['wrapperName']
        and method[0]==member.get('methodIndex')and method[1]==member.get('declaringWrapper')
        and method[2]=='set___'+read['fieldName']+'__'and member.get('name')==read['fieldName']
        and setter.get('targetField')==source['wrappedType']+'::'+read['fieldName']
        and member.get('declaredType')==TYPE and setter.get('storedBytes')==40
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('childGrammarAdmitted')is False
        and setter.get('factoryAdmitted')is False
        and setter==scope['richSetters'][index]and _same(setter['managedValueLayout'],nested['proof']['layout']))
    field.validate_event(read,setter)
    raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('own-nominal-Entity40-setter-parameter',len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==nested['proof']['layout']['typeDefinition'])
    direct=source['wrappedType']in('Beyond.Gameplay.BeaconPoleControllerData+AltarInfo',
        'Beyond.Gameplay.BeaconPoleControllerData+BeaconPoleInfo',
        'Beyond.Gameplay.RollingStoneControllerData+LauncherData')
    if direct:
        holder=setter.get('directHolder')or{}
        holder_type=bytes.fromhex(holder.get('fieldTypeRecordHex',''))
        need('own-direct-Beacon-holder-without-cache-alias',setter.get('profile')=='direct-base-holder-setter'
            and not getter and life.get('directHolderMode')is True
            and life.get('typedCache')is None and life.get('coherentGetter')is None
            and holder.get('field')==[source['wrapperName'],source['wrappedType'],16]
            and holder.get('field')==life.get('baseHolder')
            and holder.get('ownerTypeDefinition')==life.get('typeDefinition')
            and len(holder_type)==16 and holder_type[10:12]==bytes((18,0))
            and holder.get('inheritedFieldAliasUsed')is False and holder.get('openGenericOffsetUsed')is False
            and ordinary.require_setter(setter)==base)
        return
    need('own-cached-Module-holder-profile',setter.get('profile')=='cached-getter-setter'
        and life.get('directHolderMode')is not True)
    getter_method=getter.get('method',[])
    need('same-source-owned-coherent-original',len(getter_method)==4 and getter_method[1]==source['wrapperName']
        and getter.get('coherentNonNullSamePointerReturn')is True
        and getter==life.get('coherentGetter')
        and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
        and getter['typedCache'][:2]==[source['wrapperName'],source['wrappedType']])
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    getter_regions=[(a,bytes.fromhex(h))for a,h in getter['program']['selectedBytes']]
    _owned_setter_trace(getter_regions,base+getter_method[3],getter['codeWindows'],base)
    # Replay the selected equality return with owned untaken branch extents;
    # no bytes are fabricated for a refresh or cold initialization body.
    candidates=[]
    for mode in('rbx','rdi'):
        try:candidates.append(coherent_getter_program(getter_regions,base+getter_method[3],
            base_slot=getter['baseHolder'][2],cache_slot=getter['typedCache'][2],mode=mode,
            path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,getter['codeWindows'],base)))
        except(ValueError,KeyError,IndexError):pass
    need('one-replayed-coherent-getter',len(candidates)==1 and _same(candidates[0],getter['program']))
    regions=_regions([(base+a,h)for a,h in setter['ordinarySourceRegions']],setter['codeWindows'],base,'Module-Entity-setter')
    replay=field.setter_program(regions,base+method[3],field=setter['fieldOffset'],
        barrier=program['barrierTargetVa'],getter=base+getter_method[3])
    need('whole-owned-setter-and-selected-barrier',_same(replay,program)
        and program['barrierTargetVa']==base+nested['proof']['layout']['runtimeOnlyObjectPtr']['barrierTargetRva'])


def _copy(scope,read,setter,base,*,rbp=False):
    """Actual RAX hidden80 -> argument32 -> exact named whole40 setter."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    selected=scope['richProgram']['selectedProgram'];at=read['instruction'][0]+5
    rows=[(base+a,bytes.fromhex(h))for a,h in selected]
    guard=next(h for a,h in selected if a==at).lower()
    need('finite-owned-wrapper-register',guard in('4885f6','4885ff','4885db'))
    g=BytesPath(rows,base+at);g.take(guard)
    head=bytes(g.bytes.get(g.at+i,0)for i in range(2));near=head[0]==15;opcode=head[1]if near else head[0]
    need('literal-owned-parent-null-edge',opcode in(132,133)if near else opcode in(116,117))
    target=g.relative(('0f'if near else'')+format(opcode,'02x'),4 if near else 1);fall=g.at
    null=target if opcode&15==4 else fall;g.at=fall if opcode&15==4 else target
    null_receipts=scope['richProgram']['ownedNullExits']
    need('same-source-owned-nonreturning-null-call',any(a==null-base and len(bytes.fromhex(h))==5
        and bytes.fromhex(h)[:1]==b'\xe8'for a,h in null_receipts))
    g.take('0f1000','4533c0','488d55f7'if rbp else'488d542420','0f104810',
        {'4885f6':'488bce','4885ff':'488bcf','4885db':'488bcb'}[guard])
    copies=[]
    def take(raw,offset,width,home):
        copies.append(dict(sourceOffset=offset,bytes=width,displacement=home,storeInstruction=[g.at-base,raw.upper()]))
        g.take(raw)
    take('0f2945f7'if rbp else'0f29442420',0,16,64 if rbp else 32);g.take('f20f104020')
    take('f20f114517'if rbp else'f20f11442440',32,8,96 if rbp else 64)
    take('0f294d07'if rbp else'0f294c2430',16,16,80 if rbp else 48)
    call=[g.at-base,next(h for a,h in selected if base+a==g.at)];g.call(base+setter['method'][3])
    fragment=selected[selected.index(read['instruction']):selected.index(call)+1]
    need('whole-contiguous-copy-fragment',all(a+len(bytes.fromhex(h))==b for(a,h),(b,_)in zip(fragment,fragment[1:]))
        and all([a-base,h.upper()]in selected for a,h in g.seen if len(h)>8))
    # The complete source owns the throwing body; this joins its recorded call
    # without fabricating bytes for an untaken INT3 or a cold path.
    return copies,call,fragment


def _inline(scope,read,setter,base):
    """Two ordinary Module callers use the coherent getter then inline40."""
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    selected=scope['selectedProgram'];g=_owned_setter_trace(
        [(base+a,bytes.fromhex(h))for a,h in selected],base+read['instruction'][0]+5,scope['codeWindows'],base)
    def nonnull():
        raw=bytes(g.bytes.get(g.at+i,0)for i in range(2))
        opcode='0f84'if raw==bytes.fromhex('0f84')else'74'
        need('own-inline-null-edge',raw==bytes.fromhex('0f84')or raw[:1]==b'\x74')
        g.branch(opcode,False,4 if opcode=='0f84'else 1)
    g.take('4885f6');nonnull();g.take('33d2','488bce');g.call(base+setter['getter']['method'][3])
    g.take('4885c0');nonnull();g.take('0f10442420',_displacement('488d48',setter['fieldOffset']+24),'0f104c2430')
    stores=[]
    for offset,size,prefix in((0,16,'0f1140'),(16,16,'0f1148'),(32,8,'f20f1140')):
        if offset==16:g.take('f20f10442440')
        at=g.at;raw=_displacement(prefix,setter['fieldOffset']+offset);g.take(raw)
        stores.append(dict(memberIndex=read['memberIndex'],instruction=[at-base,raw.upper()],sourceOffset=offset,storedBytes=size))
    end=[g.at-base,next(h for a,h in selected if base+a==g.at)];g.call(setter['program']['barrierTargetVa'])
    return stores,end,selected[selected.index(read['instruction']):selected.index(end)+1]


def bind(source,scope,read,pins,usage,child,capability):
    index=read.get('memberIndex')
    closed=forwarder.owns_closed_member(source.get('wrappedType'),read.get('fieldName'),TYPE)
    need('finite-exact-Module-Entity-parent',owns_member(source.get('wrappedType'),read.get('fieldName'),TYPE)
        and source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==child.get('nativeInputs')==pins
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False and source.get('sourceScope')==scope
        and type(index)is int and 0<=index<len(source['orderedSourceReads'])
        and source['orderedSourceReads'][index]==read and scope['events']==source['orderedSourceReads']
        and read.get('declaredType')==TYPE and read.get('kind')=='managed:'+TYPE
        and read.get('managedBytes')==40 and read.get('resultAbi')=='hidden-local'
        and(read.get('sourceContextMode')=='owned-closed-forwarder'and read.get('context')is None if closed
            else read.get('sourceContextMode')is None and isinstance(read.get('context'),dict)))
    actual=scope['managedValueSources'][str(index)];nested,context,base=_source(actual,pins)
    need('same-exact-independent-MC3-child',capability==CAPABILITY and child==component(actual,pins)
        and usage==actual['proof']['typedRequest']and(read.get('moduleClosedForwarderSource')==actual if closed else context is None))
    if not closed:
        context=read['context'];forwarder.context_shape(context,TYPE)
        raw=bytes.fromhex(context['instructionHex']);request=actual['proof']['typedRequest']
        need('ordinary-own-actual-R8-MethodInfo',len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')
            and all(context[k]==request[k]for k in('instructionRva','instructionHex','methodSpec'))
            and tuple(request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
                (6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
            and actual.get('readerMethodDefinition')==request['methodSpec'][0]
            and[context['instructionRva'],context['instructionHex']]in scope['selectedProgram']
            and base+context['instructionRva']+7+int.from_bytes(raw[3:],'little',signed=True)
                ==context['cellVa']==base+request['usageCellRva'])
    call=bytes.fromhex(read['instruction'][1])
    need('actual-outer-E8-not-pointer-alias',len(call)==5 and call[0]==232
        and read['instruction'][0]+5+int.from_bytes(call[1:],'little',signed=True)==actual['sourceTargetRva'])
    setter=source['setters'][index];_setter(source,scope,read,setter,nested,base)
    rich=scope['richProgram'];need('whole-rich-program',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')and rich.get('childGrammarAdmitted')is False
        and rich.get('wholeOwnerAdmitted')is False)
    rbp=(source['wrappedType'],read['fieldName'])in CLOSED_RBP
    if closed:
        copies,store,fragment=_copy(scope,read,setter,base,rbp=rbp)
        expected_stores=[dict(memberIndex=index,instruction=store,sourceOffset=0,storedBytes=40)]
    else:
        expected_stores,store,fragment=_inline(scope,read,setter,base);copies=[]
    need('whole40-field-stores',[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]==expected_stores)
    hidden_home=112 if rbp else 80 if closed else 32
    hidden=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
    need('own-hidden-opaque40-local',len(hidden)==1 and hidden[0].get('displacement')==hidden_home and hidden[0].get('bytes')==40
        and hidden[0].get('sourceInstruction')==read['instruction']and hidden[0].get('nominalTypeName')==TYPE
        and hidden[0].get('nominalTypeDefinition')==context['typeDefinition']
        and hidden[0].get('opaqueRuntimeStorageRanges')==[[24,40]]and hidden[0].get('selectedBarrierValueOffsets')==[24]
        and hidden[0].get('runtimeReferenceLayoutAdmitted')is False and hidden[0].get('completeRuntimePaddingMapAdmitted')is False)
    receipts=[r for r in rich.get('sourceLocalCopies',[])if r.get('memberIndex')==index]
    need('exact-copied-source-slices',len(receipts)==len(copies) and
        all(all(r.get(k)==c[k]for k in('displacement','bytes','storeInstruction'))for r,c in zip(receipts,copies)))
    for receipt,copy in zip(receipts,copies):
        if copy['bytes']==16:
            need('same-nominal-annotated-copy-slice',receipt.get('sourceOffset')==copy['sourceOffset']
                and receipt.get('sourceRegister')==('xmm0'if copy['sourceOffset']==0 else'xmm1')
                and receipt.get('nominalTypeName')==TYPE and receipt.get('nominalTypeDefinition')==context['typeDefinition']
                and(rbp or receipt.get('originalHiddenLocal')==dict(displacement=hidden_home,bytes=40)
                    and receipt.get('opaqueRuntimeBitsPreserved')is True))
    paths=source['programs'];frame_bytes=scope['headerProof']['nullFrameBytes']
    need('all-four-owned-complete-frames',len(paths)==4 and type(frame_bytes)is int and frame_bytes>=hidden_home+40
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    for path in paths:
        if path['wrapperNull']:continue
        selected=path['selectedProgram'];frame=path['frame']
        need('same-complete-copy-in-each-positive-frame',selected[selected.index(read['instruction']):selected.index(store)+1]==fragment
            and[hidden_home-frame_bytes,40]in frame.get('hiddenSourceLocalHomes',[])
            and all([c['displacement']-frame_bytes,c['bytes']]in frame.get('copiedSourceLocalHomes',[])for c in copies))
    return dict(fieldName=read['fieldName'],typeName=TYPE,capability=capability,
        readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'],
        completeFieldTransferAndFrameProved=True,storedBytes=40,managedBytes=40,
        selectedBarrierValueOffsets=[24],opaqueRuntimeStorageRanges=[[24,40]],
        runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False,
        actualCallbackEqualsProvedChildRequired=True,wholeOwnerAdmitted=False)
