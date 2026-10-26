"""Selected normal checkpoint helper programs, independent of live dispatch.

Own typed requests and native byte programs prove only their stated transfers.
No event manager, controller, object lookup or game callback is invoked here.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-checkpoint-helper-sources.v2'


def need(check,condition):
    if not condition:raise ValueError('patrolCheckpointHelpers.'+check)


def norm(value):return json.loads(json.dumps(value))


def set_value_program(regions,entry,*,kind,get_or_create,invoke):
    """Warmed closed SetValue, through the actual slot-17 invocation request."""
    need('finite-own-value-kind',kind in ('int','UnityEngine.Vector3','Beyond.Gameplay.Core.EntityPtr'))
    integer=kind=='int';entity=kind=='Beyond.Gameplay.Core.EntityPtr'
    frame=32 if integer else 80 if entity else 48
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec'+bytes((frame,)).hex(),
        '4983793800','498bd9','418bf8'if integer else'498bf8','488bf2','488be9')
    g.branch('74',False,1);g.take('488b4338','4c8b08','4983792000');g.branch('74',False,1)
    g.take('4c8b4338','488bd6','488bcd','4d8b00');g.call(get_or_create)
    if kind=='UnityEngine.Vector3':g.take('488bd0')
    g.take('4885c0');g.branch('74',False,1)
    if integer:
        g.take('b911000000','448bc7','488bd0')
    elif entity:
        g.take('0f1007','b911000000','4c8d442420','0f104f10','488bd0',
            '0f29442420','f20f104720','f20f11442440','0f294c2430');g.call(invoke)
    else:
        g.take('f20f1007','4c8d442420','8b4708','b911000000',
            'f20f11442420','89442428');g.call(invoke)
    g.take('488b5c24'+bytes((frame+16,)).hex(),'488b6c24'+bytes((frame+24,)).hex(),
        '488b7424'+bytes((frame+32,)).hex(),'4883c4'+bytes((frame,)).hex(),'5f')
    if integer:need('actual-int-tail-invoke',g.relative('e9')==invoke)
    else:g.take('c3')
    return dict(selectedBytes=g.seen,kind=kind,frameBytes=frame+8,callShadow=[0,32],
        ownMethodInfoContextSlot=0,contextPointerOffset=56,contextReadyFieldOffset=32,
        getOrCreateArguments=dict(rcx='same incoming blackboard',rdx='same incoming key',r8='own method context slot0'),
        invocationSelector=17,invocationArguments=dict(rdx='same nonnull GetOrCreate result',
            r8='same incoming Int32 bits'if integer else'complete copied input value'),
        valueBytes=4 if integer else 40 if entity else 12,
        valueCopyBytes=[]if integer else[16,16,8]if entity else[8,4],
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'],
        normalReturn=True,invocationIsTailCall=integer,storageEffectsProved=False,
        condition='Warmed own MethodInfo context and nonnull GetOrCreate result; disjoint stable caller/frame/value storage; normal Win64 callee ABI. This program proves the exact calls and value transfer. The selected callback and blackboard table/storage effects are separate source joins.')


def get_value_program(regions,entry,*,kind,lookup,type_from_context,assignable,prepare=None,invoke=None,barrier=None):
    need('finite-get-value-kind',kind in('int','UnityEngine.Vector3','Beyond.Gameplay.Core.EntityPtr'))
    integer=kind=='int';entity=kind.endswith('EntityPtr');frame=144 if integer else 176 if entity else 160
    mi=frame+88;home=frame+48;g=BytesPath(regions,entry)
    g.take('48895c2420','4c89442418','56','57','4154','4156','4157','4881ec'+frame.to_bytes(4,'little').hex(),
        '450fb6f9','498bf8'if integer else'498bf0','4c8bf2','488bd9',
        ('488bb424'if integer else'488bbc24')+mi.to_bytes(4,'little').hex(),
        '48837e3800'if integer else'48837f3800');g.branch('0f84',False)
    g.take('33c0','48898424'+mi.to_bytes(4,'little').hex(),'48898424'+home.to_bytes(4,'little').hex(),'0f57c0')
    if kind=='UnityEngine.Vector3':g.take('0f11442470','0f11842480000000','4889842490000000','0f11442460')
    else:g.take('0f11442460','0f11442470','4889842480000000','0f11442450'if integer else'0f11442448')
    g.take('488b4b28','4885c9');g.branch('0f84',False)
    usage_instruction=g.at;usage=g.relative('4c8b0d')
    g.take('4c8d8424'+mi.to_bytes(4,'little').hex(),'498bd6');g.call(lookup)
    g.take('84c0');g.branch('74'if integer else'0f84',False,1 if integer else 4)
    g.take('488b9c24'+mi.to_bytes(4,'little').hex(),'33d2','488b4e38'if integer else'488b4f38');g.call(type_from_context)
    g.take('4885db');g.branch('74'if entity else'0f84',False,1 if entity else 4)
    g.take('488bd0','488b0b');g.call(assignable);g.take('84c0');g.branch('74'if entity else'0f84',False,1 if entity else 4)
    if integer:
        g.take('b90e000000','488bd3');g.call(invoke);g.take('8907')
    else:
        g.take('488b0b');g.call(prepare)
        g.take('4c8b03','498b8020020000','4d8b8028020000','488bd3',
            '488d8c2488000000'if entity else'488d4c2450','ffd0')
        if entity:
            g.take('0f1008','0f105010','f20f104020','0f110e','0f115610','f20f114620','488d4e18');g.call(barrier)
        else:g.take('8b4808','f20f1000','f20f1106','894e08')
    g.take('b001','488b9c24'+(frame+72).to_bytes(4,'little').hex(),
        '4881c4'+frame.to_bytes(4,'little').hex(),'415f','415e','415c','5f','5e','c3')
    return dict(selectedBytes=g.seen,kind=kind,frameBytes=frame+40,callShadow=[0,32],
        lookupContextSiteVa=usage_instruction,lookupContextCellVa=usage,
        blackboardTableFieldOffset=40,lookupArguments=dict(rcx='same blackboard table reference',rdx='same incoming key',r8='own cleared reference local',r9='own actual closed dictionary TryGetValue context'),
        typeContextSlot=0,lookupSuccessAndAssignableRequired=True,selectedGetterSlot=14,
        selectedGetterArguments=dict(receiver='same successful nonnull table result',methodInfo='same result class slot14 context',
            output='own hidden value local'if not integer else'register result'),
        valueBytes=4 if integer else 40 if entity else 12,valueCopyBytes=[4]if integer else[16,16,8]if entity else[8,4],
        outputValueBitsUnchanged=True,returnsLiteralTrue=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rsi','rdi','r12','r14','r15'],
        lookupAndSelectedCallbackEffectsProved=False,runtimeSelectionObserved=False)


def output_int_program(regions,entry,*,is_direct,set_direct):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','48897c2418','4c89742420','55','488d6c24a9','4881ecb0000000',
        '4983793800','498bd9','450fb6f0','8bf2','488bf9');g.branch('74',False,1)
    g.take('33c0','0f57c0','48894547','0f114527','0f114537','4885ff');g.branch('74',False,1)
    g.take('488b4338','488b4808','4883792000');g.branch('0f84',False)
    g.take('488b5338','488bcf','488b5208');g.call(is_direct)
    g.take('84c0','488b4338');g.branch('0f84',False)
    g.take('488b4810','4883792000');g.branch('74',False,1)
    g.take('4c8b4338','8bd6','488bcf','4d8b4010');g.call(set_direct)
    g.take('4c8d9c24b0000000','498b5b10','498b7318','498b7b20','4d8b7328','498be3','5d','c3')
    return dict(selectedBytes=g.seen,frameBytes=184,callShadow=[0,32],ownContextSlots=[1,2],
        selectedDirectOutputBranchRequired=True,sameOutputReceiverPassed=True,sameInt32BitsPassed=True,
        directPredicateArguments=dict(rcx='same incoming ParamOutput<int>',rdx='own context slot1'),
        directSetterArguments=dict(rcx='same incoming ParamOutput<int>',edx='same incoming Int32',r8='own context slot2'),
        directSetterEffectsProved=False,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],runtimeSelectionObserved=False)


def filter_constant_program(regions,entry,*,kind,barrier=None):
    need('finite-filter-value-kind',kind in('int','Beyond.Gameplay.Core.EntityPtr'))
    # This branch has no unknown effect calls: only the typed Param's direct
    # discriminator and full value read. All other Param kinds remain separate.
    integer=kind=='int';g=BytesPath(regions,entry)
    g.take('48895c2418','4889542410','56','57','4154','4156','4157','4881ecd0000000',
        '498bf9','450fb6f0'if integer else'450fb6f8','488bf2'if integer else'4c8bf2','488bd9','4983793800')
    g.branch('74'if integer else'0f84',False,1 if integer else 4)
    g.take('33c0','4889842418010000','4889842400010000','0f57c0','0f118424a0000000','0f118424b0000000',
        '48898424c0000000','4885db');g.branch('0f84',False)
    g.take('488b4738','488b4808','4883792000');g.branch('0f84',False)
    g.take('837b1000');g.branch('0f85'if integer else'0f84',not integer)
    if integer:g.take('8b4320','8906','b001')
    else:
        g.take('0f104b20','0f105330','f20f104340','410f110e','410f115610','f2410f114620','498d4e18');g.call(barrier)
        g.take('b001');g.jump('eb',1)
    g.take('488b9c2410010000','4881c4d0000000','415f','415e','415c','5f','5e','c3')
    return dict(selectedBytes=g.seen,kind=kind,frameBytes=248,callShadow=[0,32],
        ownReadyTypeContextSlot=1,discriminatorFieldOffset=16,requiredDiscriminator=0,valueFieldOffset=32,
        inputValueBytes=4 if integer else 40,valueCopyBytes=[4]if integer else[16,16,8],
        inputValueBitsCopiedUnchanged=True,returnsLiteralTrue=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rsi','rdi','r12','r14','r15'],nominalFieldJoinRequired=True,
        otherParamModesProved=False,runtimeSelectionObserved=False)


def receiver_program(regions,entry,*,implicit,barrier,prepare,valid,set_entity,
                     valid_result=True,nonnull=True,use_slot=False):
    need('finite-receiver-path',all(type(v)is bool for v in(valid_result,nonnull,use_slot))
        and(not use_slot or(valid_result and nonnull)))
    g=BytesPath(regions,entry)
    g.take('48895c2410','55','488d6c24a9','4881ec90000000','488bd9');root=g.relative('488b0d')
    g.take('488b4968','4885c9');g.branch('0f85',False)
    implicit_site=g.at;implicit_usage=g.relative('4c8b05')
    g.take('488d4de7','4889bc24a0000000');g.call(implicit)
    g.take('0f2845e7','488d4d0f','33ff','660f7f45e7','0f11450f','48897df7','48897dff','48897d07');g.call(barrier)
    type_site=g.at;type_usage=g.relative('488b0d');g.take('488b4920');g.call(prepare)
    g.take('488d4de7','488b90c0000000','488b5208');g.call(valid)
    g.take('84c0');g.branch('74',not valid_result,1)
    if valid_result:
        g.take('488b4de7','4885c9');g.branch('74',not nonnull,1)
    if valid_result and nonnull:
        g.take('397958');g.branch('75',use_slot,1)
        if use_slot:
            g.take('c645f701','488b4150','488945ff','8b4158','894507');g.jump('eb',1)
        else:g.take('40887df7','488b4130','488945ff','897d07')
    else:
        g.take('40887df7','48897dff');g.jump('eb',1);g.take('897d07')
    g.take('0f1045f7');set_site=g.at;set_usage=g.relative('4c8b0d')
    g.take('4c8d4527','0f104d07');key_site=g.at;key=g.relative('488b15')
    g.take('488bcb','0f294527','f20f104517','f20f114547','0f294d37');g.call(set_entity)
    g.take('488bbc24a0000000','488b9c24a8000000','4881c490000000','5d','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,objectPtrContextSiteVa=implicit_site,
        objectPtrContextCellVa=implicit_usage,typeContextSiteVa=type_site,typeContextCellVa=type_usage,
        setContextSiteVa=set_site,setContextCellVa=set_usage,literalKeySiteVa=key_site,literalKeyCellVa=key,
        validResult=valid_result,nonnullEntity=nonnull,useSlot=use_slot,frameBytes=152,callShadow=[0,32],
        sameIncomingEventParamsPassed=True,objectPtrInputSameIncomingEntity=True,
        selectedEntityReadOffsets=[80,88]if use_slot else[48]if valid_result and nonnull else[],
        selectedStoredUseSlot=use_slot,entityPtrValueBytes=40,setValueCopyBytes=[16,16,8],
        initializedReceiverScalarFields=True,opaqueRuntimeStoragePreserved=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rdi'],
        helperEffectsAndEntityResolutionProved=False,runtimeInvocationObserved=False)


def packet(image,at):
    from scripts.game_data.memorypack.pointer_param import owned
    base=image.pe.image_base;b=owned(image,at)
    return dict(entryRva=at-base,windows=b['windows'],regions=[[a-base,r.hex().upper()]for a,r in b['regions']])


def regions(packet,base):return [(base+a,bytes.fromhex(h))for a,h in packet['regions']]


def verify_packet(packet):
    need('owned-packet-shape',isinstance(packet,dict)and type(packet.get('entryRva'))is int
        and isinstance(packet.get('windows'),list)and isinstance(packet.get('regions'),list))
    cells={};spans=[]
    for at,h in packet['regions']:
        need('owned-region-coordinate',type(at)is int and at>=0 and isinstance(h,str))
        raw=bytes.fromhex(h);need('nonempty-owned-region',bool(raw));spans.append((at,len(raw)))
        for i,b in enumerate(raw):
            need('nonoverlapping-owned-regions',at+i not in cells);cells[at+i]=b
    need('one-window-per-owned-region',len(packet['windows'])==len(spans))
    expected=[]
    for at,length in spans:
        raw=bytes(cells[at+i]for i in range(length))
        expected.append((at,at+length,hashlib.sha256(raw).hexdigest().upper()))
    actual=[(w['startRva'],w['endRva'],w['sha256'])for w in packet['windows']]
    need('complete-owned-region-window-hashes',sorted(expected)==sorted(actual))
    need('entry-belongs-to-owned-region',packet['entryRva']in cells)


ROLES=(
    ('setEntity','setEntity','Beyond.Gameplay.Core.EntityPtr'),('setId','setInt','int'),
    ('setPosition','setPosition','UnityEngine.Vector3'),('getEntity','getEntity','Beyond.Gameplay.Core.EntityPtr'),
    ('getId','getInt','int'),('getPosition','getPosition','UnityEngine.Vector3'),('outputId','outputInt','int'),
    ('filterEntity','filterEntity','Beyond.Gameplay.Core.EntityPtr'),('filterId','filterInt','int'),
)


def _calls(rows):
    result=[]
    for row in rows:
        raw=bytes.fromhex(row['bytes'])
        if len(raw)==5 and raw[0]in(0xe8,0xe9):
            at=int(row['va'],16);result.append((row['offset'],at+5+int.from_bytes(raw[1:],'little',signed=True)))
    return result


def _replay(role,own,base,s):
    kind=next(k for r,_,k in ROLES if r==role);at=base+own['entryRva'];raw=regions(own,base)
    if role.startswith('set'):
        return set_value_program(raw,at,kind=kind,get_or_create=s['getOrCreate'],invoke=s['invoke'])
    if role.startswith('get'):
        return get_value_program(raw,at,kind=kind,lookup=s['lookup'],type_from_context=s['typeFromContext'],
            assignable=s['assignable'],prepare=s.get('prepare'),invoke=s.get('invoke'),barrier=s.get('barrier'))
    if role=='outputId':return output_int_program(raw,at,is_direct=s['isDirect'],set_direct=s['setDirect'])
    return filter_constant_program(raw,at,kind=kind,barrier=s.get('barrier'))


def _request_identity(role,usage,context):
    kind=next(k for r,_,k in ROLES if r==role)
    owner=('Beyond.Gameplay.ParamBlackboard'if role.startswith(('set','get'))else
        'Beyond.Gameplay.Actions.ParamOutputExtensions'if role=='outputId'else'Beyond.Gameplay.Actions.ParamExtensions')
    method='SetValue'if role.startswith('set')or role=='outputId'else'TryGetValue'
    need('exact-finite-typed-helper-request-'+role,tuple(usage.get(k)for k in
        ('tag','typeName','methodName','classArguments','methodArguments'))==(6,owner,method,[],[kind]))
    need('exact-own-helper-context-'+role,type(context.get('definition'))is int
        and context['definition']==usage['methodSpec'][0]and context.get('isMethod')is True
        and(context.get('typeName'),context.get('methodName'))==(owner,method))


def _symbol_names(role):
    if role.startswith('set'):return {'getOrCreate','invoke'}
    if role.startswith('get'):return {'lookup','typeFromContext','assignable'}|(
        {'invoke'}if role=='getId'else{'prepare','barrier'}if role=='getEntity'else{'prepare'})
    if role=='outputId':return {'isDirect','setDirect'}
    return {'barrier'}if role=='filterEntity'else set()


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
    from scripts.game_data.memorypack import leveldata_patrol_checkpoint_sources as producer
    from scripts.game_data.memorypack import leveldata_patrol_checkpoint_filter_sources as consumer
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base;p=producer.derive(image,pins);c=consumer.derive(image,pins)
    helpers={};programs={};contexts={};extra={};ge=GenericEntries(image)
    for role,symbol,kind in ROLES:
        parent=p if role.startswith('set')else c;entry=base+parent['symbolRvas'][symbol]
        body=owned(image,entry);calls=_calls(body['rows']);targets=dict(calls)
        if role.startswith('set'):
            s=dict(getOrCreate=targets[66],invoke=targets[107 if kind=='int'else 117 if kind.endswith('EntityPtr')else 106])
        elif role.startswith('get'):
            ordered=[target for _,target in calls]
            s=dict(lookup=ordered[0],typeFromContext=ordered[1],assignable=ordered[2])
            s['invoke'if kind=='int'else'prepare']=ordered[3]
            if kind.endswith('EntityPtr'):s['barrier']=ordered[4]
        elif role=='outputId':s=dict(isDirect=calls[0][1],setDirect=calls[1][1])
        elif role=='filterEntity':s=dict(barrier=next(target for offset,target in calls if offset==676))
        else:s={}
        own=packet(image,entry);helpers[role]=dict(packet=own,symbolRvas={k:v-base for k,v in s.items()})
        contexts[role]=ContextSymbols(image).context(parent['typedRequests'][role]['methodSpec'][0],is_method=True)
        program=_replay(role,own,base,s);programs[role]=program
        if role.startswith('get'):
            usage=derive_typed_usage_context(image,program['lookupContextSiteVa']-base,label='patrolCheckpointHelpers.'+role)
            need('own-lookup-typed-request-'+role,tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
                (6,'System.Collections.Generic.Dictionary`2','TryGetValue',['string','Beyond.Gameplay.ParamVariable'],[]))
            registrations=ge.observe(usage['methodSpec'][0],usage['classArguments'],[])
            extra[role]=dict(lookupUsage=usage,lookupActualEntryRva=s['lookup']-base,
                lookupRegistrations=registrations,lookupCanonicalPointerEquivalenceProved=False,
                boundary='Own typed request and actual call target only. Missing or shared canonical registrations supply no pointer alias or lookup effect proof.')
    receiver=packet(image,base+p['symbolRvas']['setReceiver']);rb=owned(image,base+receiver['entryRva'])
    rcalls=[target for _,target in _calls([row for row in rb['rows']
        if bytes.fromhex(row['bytes'])[:1]==b'\xe8'])];need('finite-receiver-direct-helpers',len(rcalls)==5)
    rs=dict(zip(('implicit','barrier','prepare','valid','set_entity'),rcalls))
    receiver_modes=[dict(valid_result=v,nonnull=n,use_slot=s)for v,n,s in
        ((False,False,False),(True,False,False),(True,True,False),(True,True,True))]
    receiver_programs=[receiver_program(rb['regions'],rb['pointer'],**rs,**mode)for mode in receiver_modes]
    receiver_usages={name:derive_typed_usage_context(image,receiver_programs[0][key]-base,label='patrolCheckpointHelpers.receiver.'+name)
        for name,key in(('implicit','objectPtrContextSiteVa'),('type','typeContextSiteVa'),('set','setContextSiteVa'))}
    need('same-receiver-SetValue-typed-request',all(receiver_usages['set'][k]==p['typedRequests']['setEntity'][k]
        for k in('tag','typeName','methodName','classArguments','methodArguments','methodSpec')))
    md=image.metadata;cell=receiver_programs[0]['literalKeyCellVa'];raw=image.pe.bytes_at_va(cell,8)
    table=md.sections['stringLiteral'];pool=md.sections['stringLiteralData']
    index=unresolved_usage_index(raw,table.size//8,tag=5,source='patrolCheckpointHelpers.receiverLiteral',offset=cell)
    offset,length=literal_record(md.buf[table.offset+index*8:table.offset+(index+1)*8],pool.size,source='patrolCheckpointHelpers.receiverLiteral',offset=index*8)
    literal=md.buf[pool.offset+offset:pool.offset+offset+length]
    need('own-receiver-literal',literal==b'@event_receiver')
    receiver_join=dict(packet=receiver,symbolRvas={k:v-base for k,v in rs.items()},programs=receiver_programs,
        typedRequests=receiver_usages,literal=dict(usageRawHex=raw.hex().upper(),literalIndex=index,literalHex=literal.hex().upper()),
        setValueCanonicalPointerEquivalenceProved=rs['set_entity']==p['closedSetValueRegistrations']['setEntity']['pointer'],
        setValueActualEntryPrefix=image.pe.bytes_at_va(rs['set_entity'],32).hex().upper())
    result=norm(dict(schema=SCHEMA,status='validated-conditional-checkpoint-helper-selected-programs',nativeInputs=pins,
        proof=dict(imageBase=base,producerSource=p,filterSource=c,helpers=helpers,contexts=contexts,programs=programs,
            extra=extra,receiver=receiver_join),
        selectedSetValueArgumentTransferProved=True,selectedReadOutputFilterTransfersProved=True,
        selectedReceiverConstructionSourceProved=True,blackboardStorageEffectsProved=False,
        checkpointProducerProved=False,checkpointFilterProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Own closed helper entries and contexts, selected warmed typed calls and complete value/return/frame transfers; receiver null/invalid/logic/slot programs and exact receiver key; consumer successful typed reads, direct Int32 output and constant Int32/Entity filter storage copies.',
            conditional='Compatible ready contexts/storage and normally returning exact helpers; own dictionary hit/assignability and selected callback identity; selected direct output or constant filter branch. Runtime contents, selection and invocation are not observed.',
            unresolved=['GetParamVariableOrNewOne table/storage and ParamVariable selected callback effects','dictionary lookup/type compatibility helper effects','receiver object validity/conversion and differing SetValue entry adapter','other output/filter modes and event-manager effects','actual event invocation and playback'])))
    validate(result);_publication_gate(image,pins);return result


def validate(value):
    need('schema',value.get('schema')==SCHEMA);proof=value['proof'];base=proof['imageBase']
    need('complete-finite-helper-roles',set(proof['helpers'])==set(proof['programs'])==set(proof['contexts'])=={r for r,_,_ in ROLES})
    for role,helper in proof['helpers'].items():
        own=helper['packet'];verify_packet(own)
        parent=proof['producerSource']if role.startswith('set')else proof['filterSource'];usage=parent['typedRequests'][role]
        _,symbol,kind=next(row for row in ROLES if row[0]==role)
        need('own-closed-entry-join',own['entryRva']==parent['symbolRvas'][symbol]and usage['methodArguments']==[kind])
        _request_identity(role,usage,proof['contexts'][role])
        need('exact-finite-helper-symbols-'+role,set(helper['symbolRvas'])==_symbol_names(role)
            and all(type(v)is int and v>0 for v in helper['symbolRvas'].values()))
        actual=_replay(role,own,base,{k:base+v for k,v in helper['symbolRvas'].items()})
        need('complete-helper-program-replay-'+role,norm(actual)==proof['programs'][role])
        if role.startswith('get'):
            extra=proof['extra'][role];u=extra['lookupUsage']
            need('own-get-lookup-request-join',u['instructionRva']==actual['lookupContextSiteVa']-base
                and u['usageCellRva']==actual['lookupContextCellVa']-base
                and(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments'])==
                ('System.Collections.Generic.Dictionary`2','TryGetValue',['string','Beyond.Gameplay.ParamVariable'],[])
                and extra['lookupActualEntryRva']==helper['symbolRvas']['lookup']
                and extra['lookupCanonicalPointerEquivalenceProved']is False)
    receiver=proof['receiver'];own=receiver['packet'];verify_packet(own)
    need('exact-receiver-helpers',set(receiver['symbolRvas'])=={'implicit','barrier','prepare','valid','set_entity'}
        and all(type(v)is int and v>0 for v in receiver['symbolRvas'].values()))
    need('own-receiver-entry',own['entryRva']==proof['producerSource']['symbolRvas']['setReceiver'])
    modes=[dict(valid_result=v,nonnull=n,use_slot=s)for v,n,s in
        ((False,False,False),(True,False,False),(True,True,False),(True,True,True))]
    actual=[receiver_program(regions(own,base),base+own['entryRva'],
        **{k:base+v for k,v in receiver['symbolRvas'].items()},**mode)for mode in modes]
    need('complete-receiver-program-replay',norm(actual)==receiver['programs'])
    need('exact-receiver-key',receiver['literal']['literalHex']==b'@event_receiver'.hex().upper())
    need('receiver-typed-request-join',all(receiver['typedRequests']['set'][k]==proof['producerSource']['typedRequests']['setEntity'][k]
        for k in('tag','typeName','methodName','classArguments','methodArguments','methodSpec')))
    for name,site,cell,owner,method,classes,arguments in(
        ('implicit','objectPtrContextSiteVa','objectPtrContextCellVa','Beyond.ObjectPtr`1','op_Implicit',['Beyond.Gameplay.Core.Entity'],[]),
        ('type','typeContextSiteVa','typeContextCellVa','Beyond.ObjectPtr`1','Lock',['Beyond.Gameplay.Core.Entity'],[]),
        ('set','setContextSiteVa','setContextCellVa','Beyond.Gameplay.ParamBlackboard','SetValue',[],['Beyond.Gameplay.Core.EntityPtr'])):
        usage=receiver['typedRequests'][name]
        need('receiver-exact-typed-site-'+name,tuple(usage.get(k)for k in
            ('tag','typeName','methodName','classArguments','methodArguments'))==(6,owner,method,classes,arguments)
            and all(p[site]==base+usage['instructionRva']and p[cell]==base+usage['usageCellRva']for p in actual))
    need('no-unproved-storage-or-runtime-grant',all(value[k]is True for k in
        ('selectedSetValueArgumentTransferProved','selectedReadOutputFilterTransfersProved','selectedReceiverConstructionSourceProved'))and all(value[k]is False for k in
        ('blackboardStorageEffectsProved','checkpointProducerProved','checkpointFilterProved','runtimeInvocationObserved','playbackProved')))
    return value
