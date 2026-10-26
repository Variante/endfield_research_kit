"""Actual SetValue<string> event-key request and selected reference storage.

The closed string registrations can be absent. Actual caller and generic
context facts remain distinct from independently authenticated reference-body
callbacks; their live selection is an explicit compatibility condition.
"""
import json

from scripts.game_data.memorypack import leveldata_patrol_executor_key_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as packets
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as values
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_pool_sources as pools
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_pool_programs as pool_programs
from scripts.game_data.memorypack import leveldata_patrol_event_params_programs as scope_programs
from scripts.game_data.memorypack import leveldata_patrol_event_sources as event
from scripts.game_data.memorypack.leveldata_patrol_concat_string_sources import locate,string_rows

SCHEMA='endfield.story-patrol-executor-key-sources.v2'
STATUS='validated-conditional-executor-string-key-effects'


def need(check,condition):
    if not condition:raise ValueError('patrolExecutorKey.'+check)


def norm(v):return json.loads(json.dumps(v))


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def same_packet(a,b):return all(same(a[k],b[k])for k in('entryRva','regions','windows'))



def _event_key_string_programs(p):
    """Extend only this request, without widening the checkpoint literal owner.

    Existing entries belong to the independently proved producer key domain.
    Each has a different UTF16 length from this new key, so even a hash
    collision follows the already authenticated String.Equals length-mismatch
    return. The missing-key path never selects a same-length content compare.
    """
    b=p['imageBase'];storage=p['poolSource']['proof']['storageSource']['proof']
    strings=storage['strings'];raw=bytes.fromhex(p['literal']['literalHex'])
    need('same-own-event-key-literal-string-bytes',raw==b'@event_key')
    utf16=raw.decode('utf-8').encode('utf-16le')
    units=[int.from_bytes(utf16[i:i+2],'little')for i in range(0,len(utf16),2)]
    need('bounded-nonzero-event-key-units',0<len(units)<=64 and all(0<v<=65535 for v in units))
    old=strings['domain'];lengths={k:len(v['utf16Units'])for k,v in old.items()}
    need('missing-new-key-and-different-owned-key-lengths','@event_key'not in old and old
        and all(n!=len(units)for n in lengths.values()))
    target=strings['hashMethod']['pointer'];prepare=b+storage['classes']['preparation']['entryRva']
    hash_program=values.programs.string_hash_program(packets.regions(strings['hash'],b),target,units=units)
    invoker=values.programs.string_hash_invoker_program(packets.regions(strings['hashInvoker'],b),
        b+strings['hashInvoker']['entryRva'],prepare=prepare,callback=target,units=units)
    need('same-event-key-leaf-and-inline-hash',hash_program['resultBits']==invoker['resultBits'])
    compare=b+strings['comparison']['entryRva']
    different_length=values.programs.string_equals_program(packets.regions(strings['equals'],b),
        strings['equalsMethod']['pointer'],compare=compare,mode='different-length')
    lookup=storage['calleeSource']['proof']['dictionary'];insert=storage['dictionary']
    masks={v['hashMask']for v in lookup['findPrograms']}|{v['hashMask']for v in insert['insertPrograms']}
    need('same-byte-proved-key-hash-mask',masks=={0x7fffffff})
    mask,=masks
    need('same-byte-proved-key-hash-callback-slots',all(v['hashInvocationSlot']==2 and v['entryHashOffset']==0 and v['entryStride']==24 for v in lookup['findPrograms'])
        and all(v['hashCallbackOffset']==352 and v['hashMethodInfoOffset']==360 and v['entryHashOffset']==0 and v['entryStride']==24 for v in insert['insertPrograms']))
    existing_hashes={k:strings['hashPrograms'][k]['resultBits']&mask for k in old}
    masked=hash_program['resultBits']&mask
    return dict(domain=dict(literalHex=raw.hex().upper(),utf16Units=units,comparisonBytes=len(utf16)),
        hash=hash_program,hashInvoker=invoker,dictionaryHashBits=masked,
        dictionaryApplication=dict(mask=mask,lookupHashSlot=2,insertHashCallbackOffset=352,insertMethodInfoOffset=360,
            entryHashOffset=0,entryStride=24,lookupCountLimit=lookup['induction']['countLimit'],
            insertionCountLimit=insert['induction']['countLimit'],
            sameComputedNonnegativeHashFeedsPositiveBucketRemainderAndEntryProbe=True,
            validStoredEntryHashesForOwnedLiteralKeysRequired=True),
        collisionEquality=dict(allowedExistingKeys=sorted(old),existingUtf16Lengths=lengths,
            existingDictionaryHashBits=existing_hashes,
            possibleHashMatchKeys=[k for k in sorted(old)if existing_hashes[k]==masked],
            differentLengthProgram=different_length,everyExistingKeyHasDifferentLength=True,
            onlyOwnedExistingKeyDomainRequired=True,normalSameStringClassRequired=True,
            missingNewKeyRequired=True,noSameLengthContentComparisonSelected=True,
            equalsResultOnAnyHashCollision=False),
        originalCheckpointKeyDomainChanged=False,runtimeStringStorageObserved=False)


def _programs(p):
    b=p['imageBase'];s=p['sources'];r=lambda k:packets.regions(s[k],b);e=lambda k:b+s[k]['entryRva']
    pp=p['poolSource']['proof'];cl=pp['storageSource']['proof']['classes']
    return dict(eventKeyStrings=_event_key_string_programs(p),request=programs.key_request(packets.regions(p['enclosingSource'],b),b+p['typedUsage']['instructionRva'],set_value=e('set')),
        set=programs.set_key(r('set'),e('set'),create=e('getOrCreate'),dispatch=e('dispatch')),
        getOrCreate=programs.missing_variable(r('getOrCreate'),e('getOrCreate'),lookup=e('lookup'),new=e('new')),
        new=programs.new_variable(r('new'),e('new'),allocate=e('allocate'),barrier=e('barrier'),dispatch=e('dispatch'),set_item=e('setItem')),
        invokers={str(slot):programs.invoke_reference(r('dispatch'),e('dispatch'),prepare=b+cl['preparation']['entryRva'],
            callback=e(key),slot=slot)for key,slot in(('property',15),('value',17))},
        property=programs.property_set(r('property'),e('property'),dispatch=e('dispatch')),
        value=programs.value_set(r('value'),e('value')),
        reset=programs.reset_reference(r('reset'),e('reset'),base_reset=b+pp['baseReset']['entryRva']),
        resetInvoker=pool_programs.reset_invoker_program(packets.regions(pp['resetInvoker'],b),b+pp['resetInvoker']['entryRva'],
            prepare=b+cl['preparation']['entryRva'],callback=e('reset')),
        barrier=scope_programs.disabled_barrier_program(r('barrier'),e('barrier')))


def _mvar(symbol,definition):
    raw=bytes.fromhex(symbol['rawHex']);owner=symbol.get('parameterOwner',{})
    return len(raw)==16 and raw[10]==30 and raw[11]==0 and owner.get('methodIndex')==definition and owner.get('ordinal')==0


def _contexts(p):
    cs=p['contexts'];nom=p['nominal'];values.require_nominal(nom)
    need('exact-variable-context',same(cs['variable'],nom['variableContext']))
    need('exact-pool-context',same(cs['pool'],p['poolSource']['proof']['metadata']['poolContext']))
    usage=p['typedUsage'];need('actual-string-SetValue-MethodSpec',usage['tag']==6 and usage['typeName']==values.BLACKBOARD
        and usage['methodName']=='SetValue'and usage['classArguments']==[]and usage['methodArguments']==['string'])
    def slot(context,n):return next(e for e in context['entries']if e['relativeSlot']==n)
    set_ctx=cs['set'];get_ctx=cs['getOrCreate'];new_ctx=cs['new']
    need('actual-set-method-context',set_ctx['definition']==usage['methodSpec'][0]and set_ctx['isMethod']is True
        and(set_ctx['typeName'],set_ctx['methodName'])==(values.BLACKBOARD,'SetValue'))
    for a,child,name in((set_ctx,get_ctx,'GetParamVariableOrNewOne'),(get_ctx,new_ctx,'NewParamVariable')):
        row=slot(a,0 if name=='GetParamVariableOrNewOne'else 1)
        need('reciprocal-method-substitution-'+name,row['kind']==3 and row['methodSpec'][0]==child['definition']
            and(row['typeName'],row['methodName'])==(values.BLACKBOARD,name)and row['classArguments']==[]
            and len(row['methodArguments'])==1 and _mvar(row['methodArguments'][0],a['definition']))
    for n,owner,name,index in((0,pools.POOL,'Allocate',p['poolSource']['proof']['metadata']['allocateMethod'][0]),
        (4,values.VARIABLE,'set_value',nom['methods']['set_value']['index'])):
        row=slot(new_ctx,n);need('reciprocal-new-class-substitution-'+name,row['kind']==3 and row['methodSpec'][0]==index
            and(row['typeName'],row['methodName'])==(owner,name)and row['methodArguments']==[]
            and len(row['classArguments'])==1 and _mvar(row['classArguments'][0],new_ctx['definition']))
    expected={'value':'SetValue','property':'set_value','reset':'OnAllocate'}
    for role,name in expected.items():
        cb=p['callbacks'][role];row=cb['registration'];args=row['classInstantiation']['arguments']
        need('own-unaliased-reference-body-'+role,cb['declaringType']==values.VARIABLE and cb['methodName']==name
            and cb['slot']=={'value':17,'property':15,'reset':7}[role]
            and cb['canonicalArguments']==['object']and cb['selectedClosedArguments']==['string']
            and cb['canonicalPointerEquivalenceProved']is False and cb['closedRegistrationAdmitted']is False
            and len(args)==1 and bytes.fromhex(args[0]['raw_type_record_hex'])[10]==28
            and cb['methodDefinition']in row['methodDefinitionIndices']
            and row['pointer']==p['imageBase']+p['sources'][role]['entryRva'])
        if role!='reset':need('own-reference-method-definition-'+role,cb['methodDefinition']==nom['methods'][name]['index'])
        else:need('own-reference-reset-definition',cb['methodDefinition']==p['poolSource']['proof']['metadata']['typedResetMethod'][0])
    for role in('lookup','setItem'):
        u=p['dictionaryRequests'][role]
        need('own-string-variable-dictionary-'+role,u['tag']==6 and u['typeName']==values.DICT
            and u['methodName']==('TryGetValue'if role=='lookup'else'set_Item')
            and u['classArguments']==['string',values.BASE_VARIABLE]and u['methodArguments']==[])


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
    from scripts.game_data.memorypack import leveldata_patrol_checkpoint_storage_sources as storage
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;b=image.pe.image_base
    symbols=ContextSymbols(image);ge=GenericEntries(image);pool=pools.derive(image,pins);s={}
    m,=[m for m in md.methods_for(ctx.index.types['Beyond.Gameplay.Actions.ActionExecutor'])if md.string(m.name_index)=='TryToInvoke']
    enclosing=packets.packet(image,image.method_pointer_va(m));site=locate(enclosing,b,'4c8bc0488b15')-7
    typed=derive_typed_usage_context(image,site-b,label='executorKey.actualStringSet')
    at=site+10;raw=image.pe.bytes_at_va(at,7);cell=at+7+int.from_bytes(raw[3:],'little',signed=True)
    usage_raw=image.pe.bytes_at_va(cell,8);table=md.sections['stringLiteral'];literal_pool=md.sections['stringLiteralData']
    index=unresolved_usage_index(usage_raw,table.size//8,tag=5,source='executorKey.literal',offset=cell)
    offset,length=literal_record(md.buf[table.offset+index*8:table.offset+(index+1)*8],literal_pool.size,source='executorKey.literal',offset=index*8)
    payload=md.buf[literal_pool.offset+offset:literal_pool.offset+offset+length]
    literal=dict(instructionRva=at-b,usageCellRva=cell-b,usageRawHex=usage_raw.hex().upper(),literalIndex=index,literalHex=payload.hex().upper())
    call=site+20;raw=image.pe.bytes_at_va(call,5);need('actual-enclosing-E8',raw[0]==232)
    s['set']=packets.packet(image,call+5+int.from_bytes(raw[1:],'little',signed=True))
    s['getOrCreate']=packets.packet(image,event._callee(s['set'],b,image.mapper))
    calls=event.actual_calls(s['getOrCreate'],b,image.mapper)
    s['lookup']=packets.packet(image,calls[0][1]);s['new']=packets.packet(image,calls[1][1])
    row,=[r for r in string_rows(s['set'],b,image.mapper)if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
    at=int(row['va'],16);raw=bytes.fromhex(row['bytes']);dispatch_at=at+5+int.from_bytes(raw[1:],'little',signed=True)
    s['dispatch']=packets.packet(image,dispatch_at);calls=event.actual_calls(s['new'],b,image.mapper)
    for role,i in(('allocate',0),('setItem',3)):s[role]=packets.packet(image,calls[i][1])
    s['barrier']=storage._prefix(image,calls[1][1],[scope_programs.disabled_barrier_program])
    callbacks={}
    for role,name,n in(('value','SetValue',1),('property','set_value',1),('reset','OnAllocate',0)):
        method=values._single_method(ctx,values.VARIABLE,name,n);rows=ge.observe(method.index,['object'],[])
        need('one-own-reference-body-'+role,len(rows)==1 and bool(rows[0].get('pointer')));reg=rows[0]
        s[role]=values._leaf(image,reg['pointer'],programs.property_set,dispatch=dispatch_at)if role=='property'else packets.packet(image,reg['pointer'])
        callbacks[role]=dict(declaringType=values.VARIABLE,methodName=name,methodDefinition=method.index,slot=method.slot,
            canonicalArguments=['object'],selectedClosedArguments=['string'],registration=reg,
            actualClosedRegistrations=ge.observe(method.index,['string'],[]),canonicalPointerEquivalenceProved=False,closedRegistrationAdmitted=False)
    cs={};cs['set']=symbols.context(typed['methodSpec'][0],is_method=True,slots=[0])
    cs['getOrCreate']=symbols.context(cs['set']['entries'][0]['methodSpec'][0],is_method=True,slots=[0,1])
    cs['new']=symbols.context(next(e for e in cs['getOrCreate']['entries']if e['relativeSlot']==1)['methodSpec'][0],is_method=True)
    nominal=values._nominal(image,ctx);cs['variable']=nominal['variableContext'];cs['pool']=symbols.context(ctx.index.types[pools.POOL].index)
    proof=dict(imageBase=b,enclosingSource=enclosing,typedUsage=typed,literal=literal,sources=s,callbacks=callbacks,
        contexts=cs,nominal=nominal,poolSource=pool)
    proof['programs']=_programs(proof)
    proof['dictionaryRequests']={key:derive_typed_usage_context(image,proof['programs'][role][field]-b,label='executorKey.'+key)
        for key,role,field in(('lookup','getOrCreate','lookupMethodInfoSiteVa'),('setItem','new','tableSetterMethodInfoSiteVa'))}
    value=norm(dict(schema=SCHEMA,status=STATUS,nativeInputs=pins,proof=proof,
        selectedEventKeyStringStoreEffectsProved=True,selectedActualEventKeyHashAndCollisionEffectsProved=True,selectedMissingKeyPoolReuseRequired=True,
        canonicalPointerEquivalenceProved=False,closedRegistrationAdmitted=False,runtimeSelectionObserved=False,
        runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Actual SetValue<string> MethodSpec and @event_key literal/hash/inlined hash dispatcher; different-length equality against the separate original key domain; reciprocal method/class contexts; missing-key lookup, typed reuse request, full base reset and reference reset, mode1 spare insertion and slot15/17 reference storage source.',
            conditional='Exact selected canonical reference-body callbacks and compatible string closed MethodInfos/storage, without a pointer-equivalence claim. Warm nonempty typed pool, distinct pool-owned variable, key absent, only the independently proved original producer keys present, and spare dictionary capacity, ready contexts/classes, disabled collector, absent replacement and no observers. All inherited string/table/pool conditions also apply.',
            unresolved=['actual callback, pool, variable and string identities or registration','nonselected existing-key, cold pool, allocation/growth and observer branches','actual authored action effects, activation and playback'])))
    validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
    need('schema-status-native-inputs',value.get('schema')==SCHEMA and value.get('status')==STATUS and value.get('nativeInputs')==pins)
    p=value['proof'];pools.validate(p['poolSource']);b=p['imageBase'];pp=p['poolSource']['proof']
    need('same-native-pool',p['poolSource']['nativeInputs']==pins and pp['imageBase']==b)
    packets.verify_packet(p['enclosingSource'])
    for source in p['sources'].values():packets.verify_packet(source)
    _contexts(p)
    need('actual-event-key-string-source-proof-present',isinstance(p.get('programs'),dict)
        and isinstance(p['programs'].get('eventKeyStrings'),dict))
    need('actual-event-key-string-effects-replay',same(_event_key_string_programs(p),p['programs']['eventKeyStrings']))
    need('all-source-programs-replay',same(_programs(p),p['programs']))
    def usage_site(packet,u,site,cell):
        cells={a+i:x for a,h in packet['regions']for i,x in enumerate(bytes.fromhex(h))};raw=bytes.fromhex(u['instructionHex'])
        encoded=bytes.fromhex(u['usageRawHex']);word=int.from_bytes(encoded,'little')
        need('exact-typed-usage-byte-site',u['instructionRva']==site-b and u['usageCellRva']==cell-b
            and raw==bytes(cells[u['instructionRva']+i]for i in range(len(raw)))and len(raw)==7
            and raw[:3]==bytes.fromhex('4c8b0d')and cell==site+7+int.from_bytes(raw[3:],'little',signed=True)
            and len(encoded)==8 and word>>32==0 and word>>29==6 and word&1==1
            and(word&0x1fffffff)>>1==u['methodSpecIndex'])
    f=p['programs'];usage_site(p['enclosingSource'],p['typedUsage'],f['request']['methodInfoSiteVa'],f['request']['methodInfoCellVa'])
    for role,source,program,site,cell in(('lookup','getOrCreate','getOrCreate','lookupMethodInfoSiteVa','lookupMethodInfoCellVa'),
        ('setItem','new','new','tableSetterMethodInfoSiteVa','tableSetterMethodInfoCellVa')):
        usage_site(p['sources'][source],p['dictionaryRequests'][role],f[program][site],f[program][cell])
    need('same-selected-disabled-collector',f['value']['collectorDisabledFlagVa']==f['barrier']['collectorDisabledFlagVa']==pp['baseResetProgram']['collectorDisabledFlagVa'])
    callee=pp['storageSource']['proof']['calleeSource']['proof'];table=pp['storageSource']['proof']['dictionary']
    for role,other in(('lookup',callee['dictionary']['lookup']),('setItem',table['setter']),('allocate',pp['allocate'])):
        need('same-actual-proved-table-pool-'+role,same_packet(p['sources'][role],other))
    at=b+p['typedUsage']['instructionRva'];target=next((t for a,t in event.actual_calls(p['enclosingSource'],b)if a==at+20),None)
    need('same-enclosing-key-request',target==b+p['sources']['set']['entryRva'])
    literal=p['literal'];raw=bytes.fromhex(literal['usageRawHex'])
    need('same-own-event-key-literal',literal['instructionRva']==p['typedUsage']['instructionRva']+10
        and literal['usageCellRva']==f['request']['keyCellVa']-b
        and bytes.fromhex(literal['literalHex'])==b'@event_key'and len(raw)==8
        and int.from_bytes(raw,'little')>>29==5 and(int.from_bytes(raw,'little')&0x1fffffff)>>1==literal['literalIndex'])
    need('exact-conditional-source-flags',value['selectedEventKeyStringStoreEffectsProved']is True
        and value.get('selectedActualEventKeyHashAndCollisionEffectsProved')is True
        and value['selectedMissingKeyPoolReuseRequired']is True
        and all(value[k]is False for k in('canonicalPointerEquivalenceProved','closedRegistrationAdmitted','runtimeSelectionObserved','runtimeInvocationObserved','playbackProved')))
    return value
