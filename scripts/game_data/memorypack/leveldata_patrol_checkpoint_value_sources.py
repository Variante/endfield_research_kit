"""Offline checkpoint value helper effects on selected normal source paths.

Object identity, class discriminator, coherent generic contexts, replacement
absence and stable compatible storage are explicit conditions. The byte
programs do not invoke the game or observe any receiver, table or event.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-checkpoint-value-sources.v1'
ENTITY='Beyond.Gameplay.Core.Entity'
ENTITY_PTR='Beyond.Gameplay.Core.EntityPtr'
ROOT='Beyond.Gameplay.Core.RootComponent'
OBJECT='Beyond.ObjectPtr`1'


def need(check,condition):
    if not condition:raise ValueError('patrolCheckpointValues.'+check)


def norm(value):return json.loads(json.dumps(value))


def receiver_adapter_program(regions,entry,*,set_entity):
    g=BytesPath(regions,entry)
    g.take('4883ec58','410f1000','410f104810','0f29442420','f2410f104020',
        '4c8d442420','f20f11442440','0f294c2430');g.call(set_entity)
    g.take('4883c458','c3')
    return dict(selectedBytes=g.seen,valueBytes=40,slices=[[0,16],[16,16],[32,8]],
        inputValueRegister='r8',argumentHome=[32,72],callShadow=[0,32],frameBytes=88,
        blackboardRcxKeyRdxAndContextR9Unchanged=True,allValueBitsUnchanged=True,
        setEntityTargetVa=set_entity,entryRspRestored=True,nonvolatilesUntouched=True,
        storageEffectsProved=False)


def position_program(regions,entry,*,root_offset,position_offset,replacement_present=False):
    need('literal-position-replacement-mode',type(replacement_present)is bool)
    need('own-position-offsets',all(type(v)is int and 128<=v<2**31 for v in(root_offset,position_offset)))
    g=BytesPath(regions,entry);g.take('4053','4883ec30');root=g.relative('488b05')
    g.take('488bd9','488b4868','4885c9');g.branch('0f85',replacement_present)
    if replacement_present:
        g.take('488b81506d0000','4885c0');g.branch('0f84',True)
    g.take('488b82'+root_offset.to_bytes(4,'little').hex(),'4885c0');g.branch('74',False,1)
    g.take('f20f1080'+position_offset.to_bytes(4,'little').hex(),
        '8b88'+(position_offset+8).to_bytes(4,'little').hex(),'f20f1103','894b08',
        '488bc3','4883c430','5b','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,replacementReceiverPresent=replacement_present,
        selectedReplacementAbsentRequired=True,entityRootFieldOffset=root_offset,rootPositionFieldOffset=position_offset,
        entityRootNonnullRequired=True,hiddenOutputRcxReturnedInRax=True,valueBytes=12,slices=[[0,8],[8,4]],
        positionBitsUnchanged=True,frameBytes=56,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx'],normalEffectCalls=0)


def implicit_program(regions,entry,*,prepare,uid,mode='nonnull'):
    need('finite-object-conversion-mode',mode in('null','zero-uid','nonnull'))
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','0f57c0','488bd9','0f1101',
        '498b4820','488bfa');g.call(prepare)
    g.take('4885ff');g.branch('74',mode=='null',1)
    if mode!='null':
        g.take('488bcf');g.call(uid);g.take('85c0');g.branch('74',mode=='zero-uid',1)
    flag=None
    if mode=='nonnull':
        flag=g.relative('833d')+1;g.take('00','48893b');g.branch('74',True,1)
        g.take('488bcf');g.call(uid);g.take('894308')
    else:g.take('33c0','488903','894308')
    g.take('488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,mode=mode,contextSlotOffset=32,preparationTargetVa=prepare,
        uidTargetVa=uid,collectorFlagVa=flag,collectorDisabledRequired=mode=='nonnull',
        inputEntityRegister='rdx',hiddenOutputRegister='rcx',sameOutputReturnedInRax=True,
        initialZeroBytes=16,entityReferenceOutputOffset=0,cachedUidOutputOffset=8,
        zeroPaddingRange=[12,16],outputBytes=16,uidCallCount=0 if mode=='null'else 2 if mode=='nonnull'else 1,
        stableSameEntityUidBetweenCallsRequired=mode=='nonnull',frameBytes=40,callShadow=[0,32],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rdi'],runtimeObjectResolutionObserved=False)


def valid_program(regions,entry,*,uid,nonnull):
    need('literal-object-validity-mode',type(nonnull)is bool)
    g=BytesPath(regions,entry);g.take('4053','4883ec20','48833900','488bd9');g.branch('74',not nonnull,1)
    if nonnull:g.take('488b09');g.call(uid);g.take('3b4308','0f94c0')
    else:g.take('32c0')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,nonnullObjectRequired=nonnull,uidTargetVa=uid,
        objectReferenceOffset=0,cachedUidOffset=8,returns='current UID equals cached UInt32'if nonnull else'literal false',
        currentUidNeedNotBeNonzero=True,returnsNormalizedBool=True,frameBytes=40,callShadow=[0,32],
        entryRspRestored=True,restoredNonvolatiles=['rbx'],nonframeWrites=0)


def uid_program(regions,entry,*,image_base,uid_offset):
    """One exact literal class-discriminator switch branch and field return.

    The class discriminator at +284 must select this literal branch. No
    equivalence to a metadata index or live class identity is inferred.
    """
    need('finite-uid-offset',type(uid_offset)is int and 16<=uid_offset<128)
    g=BytesPath(regions,entry)
    g.take('4053','55','56','57','4883ec68','488b01','488bd9','8b901c010000','81fa')
    lower=int.from_bytes(g.read(4),'little');g.branch('0f8f',True)
    g.take('81fa');upper=int.from_bytes(g.read(4),'little')
    g.branch('0f8f',False);g.branch('0f84',False);g.take('81ea');start=int.from_bytes(g.read(4),'little')
    g.take('81fa');maximum=int.from_bytes(g.read(4),'little')
    need('bounded-owned-switch',0<=maximum<=4096);g.branch('77',False,1)
    need('actual-switch-image-base',g.relative('488d35')==image_base);g.take('4863c2','0fb68406')
    byte_table=int.from_bytes(g.read(4),'little');g.take('8b8c86');target_table=int.from_bytes(g.read(4),'little')
    g.take('4803ce','ffe1');cells=g.bytes;cases=[]
    suffix=bytes.fromhex('8b43'+bytes((uid_offset,)).hex()+'4883c4685f5e5d5bc3')
    for i in range(maximum+1):
        try:
            slot=cells[image_base+byte_table+i]
            target=image_base+int.from_bytes(bytes(cells[image_base+target_table+slot*4+j]for j in range(4)),'little')
            if bytes(cells[target+j]for j in range(len(suffix)))==suffix:cases.append(i)
        except KeyError as error:raise ValueError('patrolCheckpointValues.unowned-switch-selection')from error
    need('unique-literal-selected-uid-field-case',len(cases)==1);index,=cases;class_id=start+index
    need('selected-class-between-owned-pivots',lower<class_id<upper)
    g.at=image_base+byte_table+index;slot=g.read(1)[0]
    g.at=image_base+target_table+slot*4;target=image_base+int.from_bytes(g.read(4),'little')
    g.at=target;g.take('8b43'+bytes((uid_offset,)).hex(),'4883c468','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,classDiscriminatorOffset=284,requiredClassDiscriminator=class_id,
        switchStart=start,switchMaximum=maximum,selectedByteIndex=index,selectedTargetSlot=slot,
        selectedFieldOffset=uid_offset,returnedBytes=4,frameBytes=136,callShadow=[0,32],
        nonframeWrites=0,normalEffectCalls=0,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'],
        liveClassDiscriminatorObserved=False,otherClassBranchesProved=False)


def object_equal_adapter_program(regions,entry,*,callback):
    g=BytesPath(regions,entry);g.take('4883ec38','0f2802','488d542420')
    site=g.at;cell=g.relative('4c8b05');g.take('660f7f442420');g.call(callback)
    g.take('4883c438','c3')
    return dict(selectedBytes=g.seen,contextInstructionVa=site,contextCellVa=cell,callbackTargetVa=callback,
        rightCopyBytes=16,rightHome=[32,48],leftPointerUnchanged=True,returnsCallbackBoolUnchanged=True,
        frameBytes=56,callShadow=[0,32],entryRspRestored=True,nonvolatilesUntouched=True)


def object_equal_program(regions,entry,*,prepare,valid,validity_equal):
    need('literal-ObjectPtr-equality-path',type(validity_equal)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec50','0f29742440','488bda','0f1031','498b4820');g.call(prepare)
    g.take('0f1003','660f7f742420','488b88c0000000','0f29442430','488b7928','488b4f20');g.call(prepare)
    g.take('488d4c2430','488b90c0000000','488b5208');g.call(valid)
    g.take('488b4f20','0fb6d8');g.call(prepare)
    g.take('488d4c2420','488b90c0000000','488b5208');g.call(valid)
    g.take('3ad8');g.branch('75',not validity_equal,1)
    if validity_equal:g.take('8b442428','39442438','0f94c0','488b5c2460')
    else:g.take('488b5c2460','32c0')
    g.take('0f28742440','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,validityResultsEqual=validity_equal,preparationTargetVa=prepare,
        validityTargetVa=valid,comparedCachedUidOffsets=[8,8],returnsNormalizedBool=True,
        result='equal validity results and equal cached UInt32'if validity_equal else'literal false',
        leftAndRightCopiedBytes=16,leftHome=[32,48],rightHome=[48,64],savedXmm6Home=[64,80],
        fullXmm6SavedAndRestored=True,frameBytes=88,callShadow=[0,32],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rdi','xmm6'],nonframeWrites=0,ownCoherentNestedContextsRequired=True)


def resolver_program(regions,entry,*,get_object,replacement_present=False):
    from scripts.game_data.memorypack.pooled_string_list_sources import flag
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec30')
    ready=flag(g);g.take('498bf0','408afa','488bd9');g.branch('75',True,1)
    root=g.relative('488b05');g.take('488b4868','4885c9');g.branch('74',not replacement_present,1)
    if replacement_present:g.take('488b8110a10000','4885c0');g.branch('74',True,1)
    g.take('0f104318');site=g.at;cell=g.relative('488b15')
    g.take('488d4c2420','f30f7f442420');g.call(get_object)
    g.take('4885c0');g.branch('0f85',True);g.take('488b4050','488b5c2440','488b742448','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlagVa=ready,replacementRootCellVa=root,
        selectedReplacementAbsentRequired=True,getObjectContextInstructionVa=site,getObjectContextCellVa=cell,
        getObjectTargetVa=get_object,objectPtrSourceOffset=24,objectPtrCopyBytes=16,objectPtrHome=[32,48],
        cachedObjectNonnullRequired=True,returnedObjectFieldOffset=80,frameBytes=56,callShadow=[0,32],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi'],nonframeWrites=0,
        uncachedResolutionEffectsProved=False)


def different_program(regions,entry,*,equal,replacement_present=False):
    need('literal-comparison-replacement-mode',type(replacement_present)is bool)
    g=BytesPath(regions,entry);g.take('4055','488bec','4881ec80000000');root=g.relative('488b05')
    g.take('4c8bc9','488b4868','4885c9');g.branch('74',not replacement_present,1)
    if replacement_present:g.take('488b8180a20000','4885c0');g.branch('74',True,1)
    g.take('0f1002','4533c0','498bc9','0f104a10','0f2945d0','f20f104220',
        '488d55d0','f20f1145f0','0f294de0');g.call(equal)
    g.take('3401','4881c480000000','5d','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,selectedReplacementAbsentRequired=True,
        equalityTargetVa=equal,leftInputRcxPreserved=True,rightCopiedSlices=[[0,16],[16,16],[32,8]],
        copiedRightHome=[80,120],frameBytes=136,callShadow=[0,32],ownMethodInfoZero=True,
        result='equality AL XOR 1',entryRspRestored=True,restoredNonvolatiles=['rbp'])


def equal_program(regions,entry,*,mode,replacement_present=False,object_equal=None,resolver=None):
    need('finite-entity-comparison-path',mode in('kind-mismatch','logic-match','logic-mismatch','slot-mismatch','zero-slot-logic-mismatch','zero-slot-object','resolved-mismatch','resolved-same','resolved-null-object'))
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec70');root=g.relative('488b05')
    g.take('488bf9','488bda','488b4868','4885c9');g.branch('0f85',replacement_present)
    if replacement_present:g.take('488b8140a20000','4885c0');g.branch('0f84',True)
    g.take('8b02','0f104210','3807');g.branch('75',mode=='kind-mismatch',1)
    result=False;object_call=False;resolve_call=False
    if mode!='kind-mismatch':
        slots=mode not in('logic-match','logic-mismatch')
        g.take('803f00');g.branch('0f85',slots)
        if not slots:
            g.take('488b4208','48394708');g.branch('74',mode=='logic-match',1);result=mode=='logic-match'
        else:
            g.take('660f7ec0','394710');g.branch('0f85',mode=='slot-mismatch')
            if mode!='slot-mismatch':
                resolved=mode.startswith('resolved-')
                g.take('837f1000');g.branch('75',resolved,1)
                if not resolved:
                    g.take('660f7ec0','85c0');g.branch('75',False,1)
                    g.take('488b4208','48394708');g.branch('0f85',mode=='zero-slot-logic-mismatch')
                    if mode=='zero-slot-object':
                        g.take('0f104a18','488d542430','0f104718','488d4c2420','0f294c2430','0f11442420')
                        g.call(object_equal);g.take('90');g.jump('e9');object_call=True
                else:
                    g.take('4533c0','4889b42480000000','33d2','488bcf');g.call(resolver)
                    g.take('4533c0','33d2','488bcb','488bf0');g.call(resolver)
                    g.take('483bf0');g.branch('74',mode!='resolved-mismatch',1)
                    if mode=='resolved-mismatch':g.take('32c0');g.jump('eb',1)
                    else:
                        g.take('4885f6');g.branch('74',mode=='resolved-null-object',1)
                        if mode=='resolved-same':g.take('b001');g.jump('eb',1);result=True
                        else:
                            g.take('0f104718','488d542430','0f104b18','488d4c2420','0f11442420','0f294c2430');g.call(object_equal);object_call=True
                    g.take('488bb42480000000');g.jump('e9');resolve_call=True
    if mode not in('zero-slot-object',)and not resolve_call:
        if result:g.take('488b9c2488000000','b001','4883c470','5f','c3')
        else:g.take('32c0','488b9c2488000000','4883c470','5f','c3')
    else:g.take('488b9c2488000000','4883c470','5f','c3')
    return dict(selectedBytes=g.seen,mode=mode,replacementRootCellVa=root,selectedReplacementAbsentRequired=True,
        comparedFields=dict(useSlotId=[0,1],logicId=[8,8],slotId=[16,4]),
        result='selected own ObjectPtr equality normalized Bool'if object_call else'selected resolved UInt64 equality'if resolve_call else str(result),
        objectEqualityCalled=object_call,resolverCalled=resolve_call,objectEqualityTargetVa=object_equal,resolverTargetVa=resolver,
        comparedObjectPtrOffset=24,objectCopies=[[0,16],[0,16]]if object_call else[],frameBytes=120,callShadow=[0,32],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rdi','rsi']if resolve_call else['rbx','rdi'],
        resultNormalizedBoolRequiredFromChild=object_call,resolutionEffectsProved=False)


def preparation_program(regions,entry):
    """Actual bounded twenty-byte class-ready identity helper, no extent claim."""
    g=BytesPath(regions,entry);g.take('f6813801000001');g.branch('74',False,1)
    g.take('488bc1');g.jump('eb',1);g.take('c3')
    return dict(selectedBytes=g.seen,readyFlagOffset=312,requiredReadyMask=1,
        returnsSameClassPointerInRax=True,nonframeWrites=0,effectCalls=0,
        stackAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False,coldPreparationEffectsProved=False)


def cached_object_program(regions,entry,*,prepare,valid,is_valid):
    need('literal-cached-object-mode',type(is_valid)is bool)
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','488b4a20');g.call(prepare)
    g.take('488bcb','488b90c0000000','488b5208');g.call(valid)
    g.take('84c0');g.branch('74',not is_valid,1)
    if is_valid:g.take('488b03')
    else:g.take('33c0');g.jump('eb',1)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,isValid=is_valid,preparationTargetVa=prepare,validityTargetVa=valid,
        contextRegister='rdx',contextSlotOffset=32,objectReferenceOffset=0,
        result='same stored object reference'if is_valid else'literal null',frameBytes=40,callShadow=[0,32],
        entryRspRestored=True,restoredNonvolatiles=['rbx'],nonframeWrites=0,ownCoherentNestedContextRequired=True)


def uid_getter_program(regions,entry,*,field_offset):
    need('own-short-UID-field',type(field_offset)is int and 16<=field_offset<128)
    g=BytesPath(regions,entry);g.take('8b41'+bytes((field_offset,)).hex(),'c3')
    return dict(selectedBytes=g.seen,fieldOffset=field_offset,resultBytes=4,nonframeWrites=0,
        effectCalls=0,stackAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False)


def _packet(image,at,*,span=None):
    import hashlib
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import packet
    if span is None:return packet(image,at)
    base=image.pe.image_base;raw=image.pe.bytes_at_va(at,span)
    return dict(entryRva=at-base,windows=[dict(startRva=at-base,endRva=at-base+span,sha256=hashlib.sha256(raw).hexdigest().upper())],
        regions=[[at-base,raw.hex().upper()]],boundary='declared-selected-leaf-span-no-physical-extent')


def _raw(own,base):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import verify_packet,regions
    verify_packet(own);return regions(own,base)


def _calls(image,at):
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import _calls as calls
    return calls([r for r in owned(image,at)['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'])


def _value_method_abi(image,ctx,m,owner,*,result,arguments,static):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need('owned-value-method-static-receiver-ABI',m.declaring_type==owner.index and ctx.is_value_type(ENTITY_PTR)
        and bool(m.flags&16)==static and m.generic_container_index==-1 and m.parameter_count==len(arguments))
    declared=[m.return_type,*[p.type_index for p in image.metadata.parameters_for(m)]]
    need('complete-owned-value-method-ABI',len(declared)==1+len(arguments))
    records=[]
    for index,(name,kind)in zip(declared,[result,*arguments],strict=True):
        scalar.ordinary(image,ctx.type_pointer(index),kind,'patrolCheckpointValues.valueMethod')
        need('owned-value-method-type',ctx.type_name(index)==name);records.append([name,kind])
    return dict(static=static,receiverValueType=True,declaredTypes=records)


def _programs(proof):
    base=proof['imageBase'];h=proof['helpers'];s={k:base+v['entryRva']for k,v in h.items()};f=proof['fields']
    def call(name,prover,**kw):return prover(_raw(h[name],base),s[name],**kw)
    parent=proof['checkpointSource']['proof']
    return norm(dict(
        receiverAdapter=call('receiverAdapter',receiver_adapter_program,set_entity=base+parent['producerSource']['symbolRvas']['setEntity']),
        position=[call('position',position_program,root_offset=f['root']['field'][2],position_offset=f['position']['field'][2],replacement_present=r)for r in(False,True)],
        implicit=[call('implicit',implicit_program,prepare=s['prepare'],uid=s['uid'],mode=mode)for mode in('null','zero-uid','nonnull')],
        valid=[call('valid',valid_program,uid=s['uid'],nonnull=n)for n in(False,True)],
        uid=call('uid',uid_program,image_base=base,uid_offset=f['uid']['field'][2]),
        uidGetter=call('uidGetter',uid_getter_program,field_offset=f['uid']['field'][2]),
        prepare=call('prepare',preparation_program),
        different=[call('different',different_program,equal=s['equal'],replacement_present=r)for r in(False,True)],
        equal=[call('equal',equal_program,mode=mode,replacement_present=r,object_equal=s['objectEqualAdapter'],resolver=s['resolver'])
            for r in(False,True)for mode in('kind-mismatch','logic-match','logic-mismatch','slot-mismatch','zero-slot-logic-mismatch','zero-slot-object','resolved-mismatch','resolved-same','resolved-null-object')],
        objectEqualAdapter=call('objectEqualAdapter',object_equal_adapter_program,callback=s['objectEqual']),
        objectEqual=[call('objectEqual',object_equal_program,prepare=s['prepare'],valid=s['valid'],validity_equal=v)for v in(False,True)],
        resolver=[call('resolver',resolver_program,get_object=s['getObject'],replacement_present=r)for r in(False,True)],
        getObject=[call('getObject',cached_object_program,prepare=s['prepare'],valid=s['valid'],is_valid=v)for v in(False,True)]))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as parent,scalar_param_native as scalar
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    source=parent.derive(image,pins);p=source['proof'];r=p['receiver'];rs={k:base+v for k,v in r['symbolRvas'].items()}
    targets=dict(implicit=rs['implicit'],prepare=rs['prepare'],valid=rs['valid'],receiverAdapter=rs['set_entity'],
        position=base+p['producerSource']['symbolRvas']['getPosition'],different=base+p['filterSource']['symbolRvas']['entityDifferent'])
    implicit_calls=_calls(image,targets['implicit']);valid_calls=_calls(image,targets['valid'])
    need('conversion-preparation-and-two-identical-UID-calls',len(implicit_calls)==3 and implicit_calls[0][1]==targets['prepare']
        and implicit_calls[1][1]==implicit_calls[2][1] and len(valid_calls)==1 and valid_calls[0][1]==implicit_calls[1][1])
    targets['uid']=implicit_calls[1][1]
    different_calls=_calls(image,targets['different']);need('one-actual-difference-equality-child',len(different_calls)==1)
    targets['equal']=different_calls[0][1];equal_calls=_calls(image,targets['equal'])
    need('same-object-comparison-and-resolver-children',len(equal_calls)==4 and equal_calls[0][1]==equal_calls[3][1]and equal_calls[1][1]==equal_calls[2][1])
    targets['objectEqualAdapter']=equal_calls[0][1];targets['resolver']=equal_calls[1][1]
    adapter_calls=_calls(image,targets['objectEqualAdapter']);need('one-actual-object-equality-child',len(adapter_calls)==1)
    targets['objectEqual']=adapter_calls[0][1];object_calls=_calls(image,targets['objectEqual'])
    need('own-nested-ObjectPtr-preparation-and-validity-targets',[t for _,t in object_calls]==[targets['prepare'],targets['prepare'],targets['valid'],targets['prepare'],targets['valid']])
    # Discover this actual cached getter from its complete selected prefix.
    resolver_packet=_packet(image,targets['resolver']);raw=_raw(resolver_packet,base)
    g=BytesPath(raw,targets['resolver']);g.take('48895c2408','4889742410','57','4883ec30')
    from scripts.game_data.memorypack.pooled_string_list_sources import flag
    flag(g);g.take('498bf0','408afa','488bd9');g.branch('75',True,1)
    g.relative('488b05');g.take('488b4868','4885c9');g.branch('74',True,1)
    g.take('0f104318');getter_usage=derive_typed_usage_context(image,g.at-base,label='patrolCheckpointValues.cachedObject')
    g.relative('488b15');g.take('488d4c2420','f30f7f442420');targets['getObject']=g.relative('e8')
    getter_calls=_calls(image,targets['getObject']);need('own-cached-getter-calls',[t for _,t in getter_calls]==[targets['prepare'],targets['valid']])
    fields={}
    for role,owner,name,kind in(('root',ENTITY,'<rootCom>k__BackingField',18),('position',ROOT,'m_position',17),
        ('uid',ENTITY,'<instanceUid>k__BackingField',9),('parentScriptId',ENTITY,'<parentScriptId>k__BackingField',11)):
        td=ctx.index.types[owner];f,=[f for f in md.fields_for(td)if md.string(f.name_index)==name]
        scalar.ordinary(image,ctx.type_pointer(f.type_index),kind,'patrolCheckpointValues.'+role,reference=kind==18)
        fields[role]=dict(name=name,field=list(ctx.field(owner+'::'+name)),typeDefinition=td.index)
    need('exact-owned-position-and-UID-field-types',[fields[k]['field'][:2]for k in('root','position','uid','parentScriptId')]==
        [[ENTITY,ROOT],[ROOT,'UnityEngine.Vector3'],[ENTITY,'uint'],[ENTITY,'ulong']])
    vector=ctx.index.types['UnityEngine.Vector3'];vf=[]
    for name in('x','y','z'):
        field,=[f for f in md.fields_for(vector)if md.string(f.name_index)==name]
        scalar.ordinary(image,ctx.type_pointer(field.type_index),12,'patrolCheckpointValues.Vector3')
        vf.append(list(ctx.field('UnityEngine.Vector3::'+name)))
    need('complete-three-Single-Vector3-slots',vf==[['UnityEngine.Vector3','float',16],['UnityEngine.Vector3','float',20],['UnityEngine.Vector3','float',24]])
    fields['vector']=vf;ep=ctx.index.types[ENTITY_PTR]
    fields['entityPtr']=[dict(name=md.string(f.name_index),field=list(ctx.field(ENTITY_PTR+'::'+md.string(f.name_index))))
        for f in md.fields_for(ep)if not ctx.field_attributes(f.type_index)&16]
    need('own-EntityPtr-physical-field-layout',[(v['name'],v['field'][1:])for v in fields['entityPtr']]==
        [('useSlotId',['bool',16]),('logicId',['ulong',24]),('slotId',['uint',32]),('<objectPtr>k__BackingField',[OBJECT+'<'+ENTITY+'>',40])])
    td=ctx.index.types[ENTITY];methods={}
    for name,result in(('get_position',('UnityEngine.Vector3',17,False)),('get_instanceUid',('uint',9,False))):
        m,=[m for m in md.methods_for(td)if md.string(m.name_index)==name]
        scalar.owned_method_abi(image,ctx,m.index,td.index,result,[],'patrolCheckpointValues.'+name)
        methods[name]=dict(method=[m.index,ENTITY,name,image.method_pointer_va(m)-base],slot=m.slot)
    need('actual-named-position-call',base+methods['get_position']['method'][3]==targets['position'])
    targets['uidGetter']=base+methods['get_instanceUid']['method'][3]
    m,=[m for m in md.methods_for(ep)if md.string(m.name_index)=='op_Inequality']
    different_abi=_value_method_abi(image,ctx,m,ep,result=('bool',2),arguments=[(ENTITY_PTR,17),(ENTITY_PTR,17)],static=True)
    need('actual-named-Inequality-call',image.method_pointer_va(m)==targets['different'])
    methods['different']=dict(method=[m.index,ENTITY_PTR,'op_Inequality',targets['different']-base],abi=different_abi)
    matches=[m for m in md.methods_for(ep)if image.method_pointer_va(m)==targets['resolver']]
    need('actual-named-UInt64-resolver',len(matches)==1);m=matches[0]
    resolver_abi=_value_method_abi(image,ctx,m,ep,result=('ulong',11),arguments=[('bool',2)],static=False)
    methods['resolver']=dict(method=[m.index,ENTITY_PTR,md.string(m.name_index),targets['resolver']-base],abi=resolver_abi)
    helpers={k:_packet(image,v,span=20 if k=='prepare'else 4 if k=='uidGetter'else None)for k,v in targets.items()}
    proof=dict(imageBase=base,checkpointSource=source,helpers=helpers,fields=fields,methods=methods)
    programs=_programs(proof);proof['programs']=programs
    eq_usage=derive_typed_usage_context(image,programs['objectEqualAdapter']['contextInstructionVa']-base,label='patrolCheckpointValues.objectEqual')
    usages=dict(implicit=r['typedRequests']['implicit'],objectEqual=eq_usage,getObject=getter_usage);joins={}
    for role,u in usages.items():
        need('own-closed-ObjectPtr-request-'+role,u['typeName']==OBJECT and u['classArguments']==[ENTITY]and not u['methodArguments'])
        joins[role]=dict(actualTargetRva=targets['objectEqual'if role=='objectEqual'else role]-base,
            canonicalRegistrationClaimed=False,canonicalPointerEquivalenceProved=False,
            boundary='Actual own closed caller context load and E8 plus complete independently replayed child bytes. No generic registration, adjustor or canonical entry identity is claimed.')
    need('actual-generic-comparison-method:'+eq_usage['methodName'],eq_usage['methodName']=='Equals')
    need('actual-producer-same-implicit-call',p['producerSource']['symbolRvas']['objectPtrImplicit']==helpers['implicit']['entryRva'])
    proof['typedRequests']=usages;proof['actualCallJoins']=joins
    result=norm(dict(schema=SCHEMA,status='validated-conditional-checkpoint-value-normal-sources',nativeInputs=pins,proof=proof,
        selectedReceiverAdapter40TransferProved=True,entityPositionFieldCopyProved=True,
        objectPtrConversionAndValidityProgramsProved=True,objectPtrCachedUidSourceProved=True,
        entityPtrComparisonNormalProgramsProved=True,wholeCheckpointProved=False,
        runtimeInvocationObserved=False,liveEntityResolutionObserved=False,playbackProved=False,
        conditions=['Selected replacement callbacks are absent; metadata and exact nested generic contexts are coherent and ready; the collector is disabled for the selected reference store.',
            'Nonnull compatible disjoint stable storage and normal Win64 callees. The UID-dispatch class predicate is a literal runtime condition, not a metadata-index or live-class identity claim.',
            'The Entity UID and object reference remain stable between reads. Cached logic-ID resolution requires a nonnull valid cached ObjectPtr and reads Entity.parentScriptId as UInt64, not an Entity reference.'],
        residualNativeSourceFrontiers=['Cold metadata/class initialization, dynamic replacements and nonselected UID class branches.',
            'Uncached logic-ID lookup/logging and exceptional invalid storage are outside the selected cached normal grant.',
            'Blackboard storage and event dispatch belong to separate owners; no current receiver, liveness, invocation or playback is observed.']))
    validate(result,pins);_publication_gate(image,pins);return result


def validate(value,pins):
    from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as parent
    need('source-envelope',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins
        and value.get('status')=='validated-conditional-checkpoint-value-normal-sources'
        and all(value.get(k)is True for k in('selectedReceiverAdapter40TransferProved','entityPositionFieldCopyProved',
            'objectPtrConversionAndValidityProgramsProved','objectPtrCachedUidSourceProved','entityPtrComparisonNormalProgramsProved'))
        and all(value.get(k)is False for k in('wholeCheckpointProved','runtimeInvocationObserved','liveEntityResolutionObserved','playbackProved')))
    p=value['proof'];base=p['imageBase'];need('image-base',type(base)is int and base>=1<<32)
    source=p['checkpointSource'];parent.validate(source);need('same-native-parent',source['nativeInputs']==pins)
    expected={'implicit','prepare','valid','receiverAdapter','position','different','uid','equal','objectEqualAdapter','resolver','objectEqual','getObject','uidGetter'}
    need('finite-actual-helper-set',set(p['helpers'])==expected)
    programs=_programs(p);need('all-selected-byte-programs-replay',programs==p['programs'])
    r=source['proof']['receiver'];h=p['helpers']
    need('actual-parent-target-seams',all(h[role]['entryRva']==r['symbolRvas'][key]for role,key in
        (('implicit','implicit'),('prepare','prepare'),('valid','valid'),('receiverAdapter','set_entity')))
        and h['position']['entryRva']==source['proof']['producerSource']['symbolRvas']['getPosition']
        and h['different']['entryRva']==source['proof']['filterSource']['symbolRvas']['entityDifferent']
        and h['implicit']['entryRva']==source['proof']['producerSource']['symbolRvas']['objectPtrImplicit'])
    need('own-named-Entity-fields',p['fields']['root']['field']==[ENTITY,ROOT,176]
        and p['fields']['position']['field']==[ROOT,'UnityEngine.Vector3',144]
        and p['fields']['uid']['field']==[ENTITY,'uint',24]
        and p['fields']['parentScriptId']['field']==[ENTITY,'ulong',80]
        and p['fields']['vector']==[['UnityEngine.Vector3','float',16],['UnityEngine.Vector3','float',20],['UnityEngine.Vector3','float',24]])
    need('own-value-field-slices',[v['field']for v in p['fields']['entityPtr']]==[
        [ENTITY_PTR,'bool',16],[ENTITY_PTR,'ulong',24],[ENTITY_PTR,'uint',32],[ENTITY_PTR,OBJECT+'<'+ENTITY+'>',40]])
    need('named-position-UID-and-resolver-entry-joins',all(h[k]['entryRva']==p['methods'][m]['method'][3]for k,m in
        (('position','get_position'),('uidGetter','get_instanceUid'),('different','different'),('resolver','resolver')))
        and p['methods']['get_position']['method'][1:3]==[ENTITY,'get_position']
        and p['methods']['get_instanceUid']['method'][1:3]==[ENTITY,'get_instanceUid']
        and p['methods']['different']['method'][1:3]==[ENTITY_PTR,'op_Inequality'])
    need('finite-own-named-fields',all(p['fields'][role]['name']==name for role,name in(
        ('root','<rootCom>k__BackingField'),('position','m_position'),('uid','<instanceUid>k__BackingField'),('parentScriptId','<parentScriptId>k__BackingField'))))
    need('finite-value-method-ABI',p['methods']['different']['abi']==dict(static=True,receiverValueType=True,
        declaredTypes=[['bool',2],[ENTITY_PTR,17],[ENTITY_PTR,17]])and p['methods']['resolver']['abi']==dict(
            static=False,receiverValueType=True,declaredTypes=[['ulong',11],['bool',2]])
        and p['methods']['resolver']['method'][1:3]==[ENTITY_PTR,'GetSlotParentScriptId'])
    need('own-parent-named-position-method',p['methods']['get_position']['method']==source['proof']['producerSource']['namedCalls']['getPosition']['method'])
    need('own-parent-implicit-context',p['typedRequests']['implicit']==r['typedRequests']['implicit'])
    need('finite-own-ObjectPtr-context-roles',set(p['typedRequests'])==set(p['actualCallJoins'])=={'implicit','objectEqual','getObject'})
    for role,u in p['typedRequests'].items():
        need('finite-ObjectPtr-request-'+role,u['tag']==6 and u['typeName']==OBJECT and u['classArguments']==[ENTITY]and u['methodArguments']==[]
            and u['methodName']=={'implicit':'op_Implicit','objectEqual':'Equals','getObject':'Lock'}[role])
        join=p['actualCallJoins'][role];key='objectEqual'if role=='objectEqual'else role
        need('actual-context-call-without-canonical-alias-'+role,join['actualTargetRva']==h[key]['entryRva']
            and join['canonicalPointerEquivalenceProved']is False and join['canonicalRegistrationClaimed']is False)
    need('ObjectPtr-comparison-context-site',p['typedRequests']['objectEqual']['methodName']=='Equals'
        and p['typedRequests']['objectEqual']['instructionRva']==programs['objectEqualAdapter']['contextInstructionVa']-base
        and p['typedRequests']['objectEqual']['usageCellRva']==programs['objectEqualAdapter']['contextCellVa']-base)
    need('cached-object-context-site',all(p['typedRequests']['getObject']['instructionRva']==g['getObjectContextInstructionVa']-base
        and p['typedRequests']['getObject']['usageCellRva']==g['getObjectContextCellVa']-base for g in programs['resolver']))
    for role,helper,prefix in(('objectEqual','objectEqualAdapter','4C8B05'),('getObject','resolver','488B15')):
        u=p['typedRequests'][role];cells={a+i:b for a,raw in _raw(h[helper],base)for i,b in enumerate(raw)}
        encoded=bytes(cells[base+u['instructionRva']+i]for i in range(7))
        need('complete-actual-context-load-'+role,encoded.hex().upper()==u['instructionHex'].upper()and encoded[:3]==bytes.fromhex(prefix)
            and base+u['usageCellRva']==base+u['instructionRva']+7+int.from_bytes(encoded[3:],'little',signed=True))
    need('exact-bounded-leaf-spans',len(h['prepare']['regions'])==len(h['prepare']['windows'])==1
        and len(bytes.fromhex(h['prepare']['regions'][0][1]))==20
        and len(h['uidGetter']['regions'])==len(h['uidGetter']['windows'])==1 and len(bytes.fromhex(h['uidGetter']['regions'][0][1]))==4)
    return dict(selectedReceiverAdapter40TransferProved=True,entityPositionFieldCopyProved=True,
        objectPtrConversionAndValidityProgramsProved=True,objectPtrCachedUidSourceProved=True,entityPtrComparisonNormalProgramsProved=True,
        actualUidClassDiscriminatorRequired=programs['uid']['requiredClassDiscriminator'],runtimeInvocationObserved=False,playbackProved=False)
