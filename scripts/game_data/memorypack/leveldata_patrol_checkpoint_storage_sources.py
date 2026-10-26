"""Selected checkpoint string-key table effects, below live blackboard state.

This owner independently authenticates the string hash/equality callbacks,
ready class paths and the mode-one dictionary mutation source. It consumes no
saved report. Pool/heap initialization and nonselected resize/observer paths
remain separate from these selected source effects.
"""
import hashlib
import json

from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as callees
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as helpers

SCHEMA='endfield.story-patrol-checkpoint-storage-sources.v1'


def need(check,condition):
    if not condition:raise ValueError('patrolCheckpointStorage.'+check)


def norm(value):return json.loads(json.dumps(value))


def _prefix(image,entry,replayers):
    prefix=image.pe.bytes_at_va(entry,256);results=[f([(entry,prefix)],entry)for f in replayers]
    selected=[(at,len(bytes.fromhex(h)))for p in results for at,h in p['selectedBytes']]
    need('bounded-exact-prefix-with-entry',selected and min(a for a,_ in selected)==entry)
    end=max(a+n for a,n in selected)
    # Keep actual untaken target bytes in the authenticated prefix as well.
    # Their effects are not inferred; BytesPath checks every selected edge
    # against real captured bytes even when this normal program skips it.
    for result in results:
        seen=result['selectedBytes']
        for (at,h),(next_at,displacement)in zip(seen,seen[1:]):
            opcode=bytes.fromhex(h);raw=bytes.fromhex(displacement)
            conditional=(len(opcode)==1 and 112<=opcode[0]<=127 and len(raw)==1
                or len(opcode)==2 and opcode[0]==15 and 128<=opcode[1]<=143 and len(raw)==4)
            if conditional and next_at==at+len(opcode):
                target=next_at+len(raw)+int.from_bytes(raw,'little',signed=True)
                need('bounded-real-prefix-conditional-target',entry<=target<entry+256);end=max(end,target+1)
    need('bounded-prefix-extent',entry<end<=entry+256)
    raw=image.pe.bytes_at_va(entry,end-entry);base=image.pe.image_base
    return dict(entryRva=entry-base,regions=[[entry-base,raw.hex().upper()]],
        windows=[dict(startRva=entry-base,endRva=end-base,sha256=hashlib.sha256(raw).hexdigest().upper())],
        physicalFunctionExtentProved=False)


def _fixed_prefix(image,entry,length):
    base=image.pe.image_base;raw=image.pe.bytes_at_va(entry,length)
    return dict(entryRva=entry-base,regions=[[entry-base,raw.hex().upper()]],
        windows=[dict(startRva=entry-base,endRva=entry-base+length,sha256=hashlib.sha256(raw).hexdigest().upper())],
        physicalFunctionExtentProved=False)


def _merge(entry,*packets):
    value=dict(entryRva=entry,regions=[r for p in packets for r in p['regions']],
        windows=[w for p in packets for w in p['windows']],physicalFunctionExtentProved=False)
    helpers.verify_packet(value);return value


def _tail(image,at,prefix):
    expected=bytes.fromhex(prefix);raw=image.pe.bytes_at_va(at,len(expected)+4)
    need('exact-source-tail-prefix',raw[:len(expected)]==expected)
    return at+len(raw)+int.from_bytes(raw[-4:],'little',signed=True)


def _class_sources(image,base,source):
    from scripts.game_data.memorypack.leveldata_patrol_dictionary_lookup_programs import preparation_program
    own=source['proof'];values=own['values'];creates=own['creates']
    prepare_targets={v['prepareTargetRva']for v in values.values()};need('same-selected-class-preparation',len(prepare_targets)==1)
    prepare=base+next(iter(prepare_targets));inner=_tail(image,prepare,'488b4978e9')
    ready=_merge(prepare-base,_fixed_prefix(image,prepare,9),callees._body(image,inner))
    prep=[preparation_program(helpers.regions(ready,base),prepare,inner=inner,mode=m)for m in('initialized','being-initialized')]
    type_targets={c['symbolRvas']['type_from_context']for c in creates.values()};assign_targets={c['symbolRvas']['assignable']for c in creates.values()}
    need('same-own-class-compatibility-callees',len(type_targets)==len(assign_targets)==1)
    type_entry=base+next(iter(type_targets));class_entry=_tail(image,type_entry,'488bc14863ca488b0cc8e9')
    class_packet=_fixed_prefix(image,class_entry,20)
    type_packet=_merge(type_entry-base,_fixed_prefix(image,type_entry,15),class_packet)
    type_program=programs.ready_context_type_program(helpers.regions(type_packet,base),type_entry,inner=class_entry)
    assign=callees._body(image,base+next(iter(assign_targets)));matches=[]
    for _,target in dict.fromkeys(callees._calls(assign,base)):
        try:
            packet=callees._body(image,target);program=programs.class_ready_program(helpers.regions(packet,base),target)
            matches.append((target,packet,program))
        except(ValueError,KeyError,RuntimeError):continue
    need('one-actual-ready-assignability-child',len(matches)==1);target,child,child_program=matches[0]
    assign_program=programs.assignable_program(helpers.regions(assign,base),base+assign['entryRva'],prepare=target)
    return dict(preparation=ready,preparationInnerRva=inner-base,preparationPrograms=prep,
        contextType=type_packet,contextTypeInnerRva=class_entry-base,contextTypeProgram=type_program,
        assignable=assign,assignableProgram=assign_program,assignablePreparation=child,
        assignablePreparationProgram=child_program)


def _literal_domain(source):
    p=source['proof']['parent']['proof'];values={}
    for parent in(p['producerSource'],p['filterSource']):
        for name,value in parent['literals'].items():
            raw=bytes.fromhex(value['literalHex']);need('same-owned-literal-name-bytes',raw.decode('utf-8')==name)
            values[name]=value['literalHex']
    receiver=p['receiver']['literal'];raw=bytes.fromhex(receiver['literalHex']);values[raw.decode('utf-8')]=receiver['literalHex']
    result={}
    for name,h in sorted(values.items()):
        raw=bytes.fromhex(h);u=raw.decode('utf-8').encode('utf-16le');units=[int.from_bytes(u[i:i+2],'little')for i in range(0,len(u),2)]
        need('finite-nonzero-checkpoint-literal-units',0<len(units)<=64 and all(v>0 for v in units))
        result[name]=dict(literalHex=h,utf16Units=units,comparisonBytes=len(u))
    return result


def _ordinary(ctx,owner,name,slot,parameters,returns):
    method=callees._single_method(ctx,owner,name,len(parameters))
    need('own-ordinary-method-signature',(method.slot,callees._parameter_type(ctx,method),ctx.type_name(method.return_type))==(slot,parameters,returns))
    return dict(method=[method.index,owner,name],slot=slot,parameters=parameters,returns=returns,
        pointer=ctx.image.method_pointer_va(method),physicalBodyUniquenessClaimed=False)


def _string_sources(image,base,source,class_sources):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    ctx=NativeReferenceContext(image);domain=_literal_domain(source)
    md=image.metadata;td=ctx.index.types['System.String']
    hash_method=_ordinary(ctx,'System.String','GetHashCode',2,[],'int')
    # Equals(object) and Equals(string) have the same arity, distinct slots.
    methods=[m for m in md.methods_for(td)if md.string(m.name_index)=='Equals'and m.slot==0]
    need('one-own-object-Equals-declaration',len(methods)==1);equal=methods[0]
    need('own-object-Equals-signature',callees._parameter_type(ctx,equal)==['object']and ctx.type_name(equal.return_type)=='bool')
    equal_method=dict(method=[equal.index,'System.String','Equals'],slot=0,parameters=['object'],returns='bool',
        pointer=image.method_pointer_va(equal),physicalBodyUniquenessClaimed=False)
    hash_packet=_prefix(image,hash_method['pointer'],[lambda r,e,u=v['utf16Units']:programs.string_hash_program(r,e,units=u)for v in domain.values()])
    # The owned object-Equals prefix has one explicit ordinal comparison tail.
    prefix=image.pe.bytes_at_va(equal_method['pointer'],128);g=BytesPath([(equal_method['pointer'],prefix)],equal_method['pointer'])
    g.take('483bca');g.branch('74',False,1);g.take('4885d2');g.branch('74',False,1)
    class_site=g.at;g.relative('488b05');g.take('483902');g.branch('75',False,1)
    g.take('8b4210','394110');g.branch('75',False,1)
    g.take('4c634110','4883c214','4d03c0','4883c114','4533c9');compare=g.relative('e9')
    class_usage=derive_typed_usage_context(image,class_site-base,label='patrolCheckpointStorage.StringClass')
    need('own-selected-String-class-request',class_usage['tag']==1 and class_usage['typeName']=='string')
    modes=('same-reference','null','different-class','different-length','content')
    equal_packet=_prefix(image,equal_method['pointer'],[lambda r,e,m=m:programs.string_equals_program(r,e,compare=compare,mode=m)for m in modes])
    compare_packet=callees._body(image,compare);counts=sorted({v['comparisonBytes']for v in domain.values()})
    comparison={str(n):[programs.byte_equality_program(helpers.regions(compare_packet,base),compare,count=n,mismatch=m)
        for m in[None,*([*range(0,n-8,8),n-8]if n>=8 else list(range(n)))]]for n in counts}
    own_dict=source['proof']['dictionary'];hash_invoker=callees._body(image,base+own_dict['symbolRvas']['hash_invoke'])
    equal_invoker=callees._body(image,base+own_dict['symbolRvas']['equality_invoke'])
    rows=equal_invoker['rows'];lea=next(r for r in rows if bytes.fromhex(r['bytes'])[:3]==bytes.fromhex('488d05'))
    raw=bytes.fromhex(lea['bytes']);candidate=int(lea['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True)
    raw=image.pe.bytes_at_va(candidate,32);g=BytesPath([(candidate,raw)],candidate)
    g.take('4885d2');g.branch('74',False,1);g.take('4d85c0');g.branch('74',False,1);g.take('33c9');nested=g.relative('e9')
    candidate_packet=_prefix(image,candidate,[lambda r,e:programs.erased_comparer_equals_program(r,e,invoke=nested)])
    nested_packet=callees._body(image,nested);prepare=base+class_sources['preparation']['entryRva']
    getter=base+own_dict['symbolRvas']['comparer_getter'];factory=_tail(image,getter,'e9')
    factory_packet=callees._body(image,factory)
    result=dict(domain=domain,stringFields={name:list(ctx.field('System.String::'+name))for name in('_stringLength','_firstChar')},
        hashMethod=hash_method,equalsMethod=equal_method,stringClassUsage=class_usage,
        hash=hash_packet,equals=equal_packet,comparison=compare_packet,
        hashPrograms={name:programs.string_hash_program(helpers.regions(hash_packet,base),hash_method['pointer'],units=v['utf16Units'])for name,v in domain.items()},
        equalsPrograms=[programs.string_equals_program(helpers.regions(equal_packet,base),equal_method['pointer'],compare=compare,mode=m)for m in modes],
        comparisonPrograms=comparison,hashInvoker=hash_invoker,
        hashInvokerPrograms={name:programs.string_hash_invoker_program(helpers.regions(hash_invoker,base),base+hash_invoker['entryRva'],prepare=prepare,callback=hash_method['pointer'],units=v['utf16Units'])for name,v in domain.items()},
        equalityInvoker=equal_invoker,erasedEqualityCandidate=candidate_packet,nestedEqualsInvoker=nested_packet,
        erasedEqualityProgram=programs.erased_comparer_equals_program(helpers.regions(candidate_packet,base),candidate,invoke=nested),
        equalityInvokerProgram=programs.comparer_equals_invoker_program(helpers.regions(equal_invoker,base),base+equal_invoker['entryRva'],prepare=prepare,callback=candidate,invoke=nested),
        nestedEqualsInvokerProgram=programs.string_equals_invoker_program(helpers.regions(nested_packet,base),nested,prepare=prepare,callback=equal_method['pointer']),
        factoryThunk=_fixed_prefix(image,getter,5),factory=factory_packet,
        factoryProgram=programs.default_comparer_program(helpers.regions(factory_packet,base),factory,
            type_from_context=base+class_sources['contextType']['entryRva'],context_type=base+class_sources['contextTypeInnerRva']),
        erasedClosedPointerEquivalenceProved=False,actualComparerRuntimeNominalRequired='System.Collections.Generic.GenericEqualityComparer`1<string>')
    ge=GenericEntries(image)
    result['erasedCandidateDeclaration']=dict(owner='System.Collections.Generic.GenericEqualityComparer`1',method='Equals',
        registrations=ge.observe(callees._single_method(ctx,'System.Collections.Generic.GenericEqualityComparer`1','Equals',2).index,['string'],[]))
    return result


def _dictionary_sources(image,base,source,string_sources,class_sources):
    creates=source['proof']['creates'];target=creates['Beyond.Gameplay.Core.EntityPtr']['symbolRvas']['set_item']
    need('same-own-table-setter-all-three-values',all((c['newVariable']['symbolRvas']['set_item']if c['newVariable']else c['symbolRvas']['set_item'])==target for c in creates.values()))
    setter=callees._body(image,base+target);calls=callees._calls(setter,base);insert=callees._body(image,calls[0][1])
    candidates=[];rows=insert['rows']
    for i,row in enumerate(rows):
        raw=bytes.fromhex(row['bytes'])
        if raw[:1]==b'\xe8'and i>=2 and bytes.fromhex(rows[i-1]['bytes'])==bytes.fromhex('488bcb')and bytes.fromhex(rows[i-2]['bytes'])==bytes.fromhex('4863d7'):
            at=int(row['va'],16);candidates.append(at+5+int.from_bytes(raw[1:],'little',signed=True))
    need('one-actual-address-helper-for-both-update-stores',len(set(candidates))==1 and len(candidates)>=2)
    address=callees._body(image,candidates[0]);prepare=base+class_sources['preparation']['entryRva']
    symbols=dict(prepare=prepare,comparer_getter=base+string_sources['factory']['entryRva'],element_address=base+address['entryRva'])
    paths,induction=programs.try_insert_paths(helpers.regions(insert,base),base+insert['entryRva'],**symbols)
    return dict(setter=setter,setterProgram=programs.set_item_program(helpers.regions(setter,base),base+setter['entryRva'],insert=base+insert['entryRva']),
        insert=insert,insertPrograms=paths,induction=induction,symbolRvas={k:v-base for k,v in symbols.items()},
        entryAddress=address,entryAddressProgram=programs.entry_address_program(helpers.regions(address,base),base+address['entryRva']))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);source=callees.derive(image,pins);base=image.pe.image_base
    classes=_class_sources(image,base,source);strings=_string_sources(image,base,source,classes)
    dictionary=_dictionary_sources(image,base,source,strings,classes)
    value=norm(dict(schema=SCHEMA,status='validated-conditional-checkpoint-table-selected-effects',nativeInputs=pins,
        proof=dict(imageBase=base,calleeSource=source,classes=classes,strings=strings,dictionary=dictionary),
        selectedLiteralHashAndOrdinalEqualityEffectsProved=True,selectedDictionaryLookupAndModeOneMutationEffectsProved=True,
        selectedReadyClassAndCompatibilityEffectsProved=True,completePoolCreationEffectsProved=False,
        completeCheckpointCalleeEffectsProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Current literal-domain hash and ordinal equality leaves/virtual programs, full selected class-ready/hierarchy paths, typed string/reference lookup and mode1 update/no-free-entry spare-capacity insertion programs and bounded mixed-chain induction.',
            conditional='Exact same selected String and erased generic comparer callbacks/MethodInfos and nominal string comparer; ready source-selected contexts/static comparer, valid stable key/entry/bucket invariants, disabled collector, disjoint value/frame storage and no concurrent mutation. Only the actual checkpoint literal domain is admitted.',
            unresolved=['pool allocation/reuse, reset and compatible created-instance storage source','dictionary cold initialization, resize and free-list reuse','nonselected observer/event/replacement branches','actual callback/heap/table contents and checkpoint invocation/playback'])))
    validate(value);_publication_gate(image,pins);return value


def validate(value):
    from scripts.game_data.memorypack.leveldata_patrol_dictionary_lookup_programs import preparation_program
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('schema-status',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-checkpoint-table-selected-effects')
    proof=value['proof'];source=proof['calleeSource'];callees.validate(source);base=proof['imageBase']
    need('same-callee-native-inputs-and-image',value['nativeInputs']==source['nativeInputs']and base==source['proof']['imageBase'])
    c=proof['classes'];s=proof['strings'];d=proof['dictionary']
    for p in(c['preparation'],c['contextType'],c['assignable'],c['assignablePreparation'],
            s['hash'],s['equals'],s['comparison'],s['hashInvoker'],s['equalityInvoker'],s['erasedEqualityCandidate'],s['nestedEqualsInvoker'],s['factoryThunk'],s['factory'],
            d['setter'],d['insert'],d['entryAddress']):helpers.verify_packet(p)
    need('own-fresh-literal-domain',s['domain']==_literal_domain(source))
    need('own-String-layout',s['stringFields']=={'_stringLength':['System.String','int',16],'_firstChar':['System.String','char',20]})
    prepare=base+c['preparation']['entryRva'];hash_pointer=base+s['hash']['entryRva'];equal_pointer=base+s['equals']['entryRva'];compare=base+s['comparison']['entryRva']
    need('same-source-class-and-dictionary-callees',all(c['preparation']['entryRva']==v['prepareTargetRva']for v in source['proof']['values'].values())
        and all(c['contextType']['entryRva']==v['symbolRvas']['type_from_context']and c['assignable']['entryRva']==v['symbolRvas']['assignable']for v in source['proof']['creates'].values())
        and all(s[k]['entryRva']==source['proof']['dictionary']['symbolRvas'][symbol]for k,symbol in
            (('hashInvoker','hash_invoke'),('equalityInvoker','equality_invoke'),('factoryThunk','comparer_getter'))))
    creates=source['proof']['creates']
    need('same-actual-table-setter-all-created-values',all(
        (v['newVariable']['symbolRvas']['set_item']if v['newVariable']else v['symbolRvas']['set_item'])==d['setter']['entryRva']
        for v in creates.values()))
    need('same-selected-insertion-callee-packets',d['symbolRvas']=={
        'prepare':c['preparation']['entryRva'],'comparer_getter':s['factory']['entryRva'],
        'element_address':d['entryAddress']['entryRva']})
    thunk=BytesPath(helpers.regions(s['factoryThunk'],base),base+s['factoryThunk']['entryRva'])
    need('own-warm-comparer-thunk-target',thunk.relative('e9')==base+s['factory']['entryRva'])
    expected=[preparation_program(helpers.regions(c['preparation'],base),prepare,inner=base+c['preparationInnerRva'],mode=m)for m in('initialized','being-initialized')]
    need('complete-ready-preparation-program-replay',norm(expected)==c['preparationPrograms'])
    need('complete-context-type-program-replay',norm(programs.ready_context_type_program(helpers.regions(c['contextType'],base),base+c['contextType']['entryRva'],inner=base+c['contextTypeInnerRva']))==c['contextTypeProgram'])
    need('complete-assignability-preparation-program-replay',norm(programs.class_ready_program(helpers.regions(c['assignablePreparation'],base),base+c['assignablePreparation']['entryRva']))==c['assignablePreparationProgram'])
    need('complete-assignability-program-replay',norm(programs.assignable_program(helpers.regions(c['assignable'],base),base+c['assignable']['entryRva'],prepare=base+c['assignablePreparation']['entryRva']))==c['assignableProgram'])
    need('own-declared-String-method-pointers',s['hashMethod']['pointer']==hash_pointer and s['equalsMethod']['pointer']==equal_pointer
        and s['hashMethod']['slot']==2 and s['equalsMethod']['slot']==0)
    for name,v in s['domain'].items():
        h=programs.string_hash_program(helpers.regions(s['hash'],base),hash_pointer,units=v['utf16Units'])
        inline=programs.string_hash_invoker_program(helpers.regions(s['hashInvoker'],base),base+s['hashInvoker']['entryRva'],prepare=prepare,callback=hash_pointer,units=v['utf16Units'])
        need('literal-hash-leaf-and-invoker-replay',norm(h)==s['hashPrograms'][name]and norm(inline)==s['hashInvokerPrograms'][name]and h['resultBits']==inline['resultBits'])
    modes=('same-reference','null','different-class','different-length','content')
    need('String-Equals-program-replay',norm([programs.string_equals_program(helpers.regions(s['equals'],base),equal_pointer,compare=compare,mode=m)for m in modes])==s['equalsPrograms'])
    usage=s['stringClassUsage'];content=s['equalsPrograms'][-1]
    need('exact-own-String-class-usage',usage['tag']==1 and usage['typeName']=='string'
        and usage['instructionRva']==s['equals']['entryRva']+10 and usage['usageCellRva']==content['stringClassCellVa']-base)
    counts=sorted({v['comparisonBytes']for v in s['domain'].values()});need('exact-current-literal-comparison-lengths',set(s['comparisonPrograms'])=={str(n)for n in counts})
    for n in counts:
        paths=[programs.byte_equality_program(helpers.regions(s['comparison'],base),compare,count=n,mismatch=m)
            for m in[None,*([*range(0,n-8,8),n-8]if n>=8 else list(range(n)))]]
        need('complete-ordinal-byte-program-replay',norm(paths)==s['comparisonPrograms'][str(n)])
    candidate=base+s['erasedEqualityCandidate']['entryRva'];nested=base+s['nestedEqualsInvoker']['entryRva']
    need('erased-equality-program-replay',norm(programs.erased_comparer_equals_program(helpers.regions(s['erasedEqualityCandidate'],base),candidate,invoke=nested))==s['erasedEqualityProgram'])
    need('erased-invoker-program-replay',norm(programs.comparer_equals_invoker_program(helpers.regions(s['equalityInvoker'],base),base+s['equalityInvoker']['entryRva'],prepare=prepare,callback=candidate,invoke=nested))==s['equalityInvokerProgram'])
    need('String-Equals-invoker-program-replay',norm(programs.string_equals_invoker_program(helpers.regions(s['nestedEqualsInvoker'],base),nested,prepare=prepare,callback=equal_pointer))==s['nestedEqualsInvokerProgram'])
    need('warm-comparer-return-program-replay',norm(programs.default_comparer_program(helpers.regions(s['factory'],base),base+s['factory']['entryRva'],type_from_context=base+c['contextType']['entryRva'],context_type=base+c['contextTypeInnerRva']))==s['factoryProgram'])
    paths,induction=programs.try_insert_paths(helpers.regions(d['insert'],base),base+d['insert']['entryRva'],**{k:base+v for k,v in d['symbolRvas'].items()})
    need('dictionary-insertion-and-induction-program-replay',norm(paths)==d['insertPrograms']and norm(induction)==d['induction'])
    need('dictionary-setter-replay',norm(programs.set_item_program(helpers.regions(d['setter'],base),base+d['setter']['entryRva'],insert=base+d['insert']['entryRva']))==d['setterProgram'])
    need('dictionary-entry-address-replay',norm(programs.entry_address_program(helpers.regions(d['entryAddress'],base),base+d['entryAddress']['entryRva']))==d['entryAddressProgram'])
    need('no-unproved-pool-or-runtime-grant',all(value[k]is False for k in('completePoolCreationEffectsProved','completeCheckpointCalleeEffectsProved','runtimeInvocationObserved','playbackProved'))
        and s['erasedClosedPointerEquivalenceProved']is False)
    need('selected-storage-effects-required',all(value[k]is True for k in(
        'selectedLiteralHashAndOrdinalEqualityEffectsProved','selectedDictionaryLookupAndModeOneMutationEffectsProved',
        'selectedReadyClassAndCompatibilityEffectsProved')))
    return value
