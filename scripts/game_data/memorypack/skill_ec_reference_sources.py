"""Own current Target/Direction/Selector ordinary reference adapter sources.

Complete concrete callers and lifecycle are independently required. Selector's
actual formatter inlines three reference stores and its Finder provider call;
it does not tail-call the static reader. Child grammars and recursive finite
selector domains remain independent of these nominal adapter joins.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPES=('Beyond.Gameplay.Core.TargetSettings','Beyond.Gameplay.Core.DirectionSettings','Beyond.Gameplay.Core.Selector+SelectorData')


def selector_formatter_program(regions,entry,offsets,*,new=False,null=False):
    need('literal-selector-formatter-path',True,type(new)is bool and type(null)is bool)
    g=BytesPath(regions,entry);allocation=None;collectors=[];calls=[];usages=[]
    def usage(opcode):
        at=g.at;cell=g.relative(opcode);return dict(instruction=at,cell=cell)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2418','4889742420','57','4883ec20');ready=flag(g)
    g.take('498bf8','488bda');g.branch('75',True,1)
    wrapper_class=usage('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
    static_ready=flag(g);g.branch('75',True,1)
    g.take('837b'+rem+'01');g.branch('7d',True,1)
    g.take('488b43'+cur,'0fb628','8b73'+rem,'83ee01');g.branch('79',True,1)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'8973'+rem,'4080fdff');g.branch('0f84',null)
    barrier=None;provider_class=None;provider=None;dispatch=None;finder=None
    if null:
        g.take('488bcf','48c70700000000');barrier=g.relative('e8')
    else:
        g.take('48833f00');g.branch('75',not new,1)
        if new:
            allocation=usage('488b0d');allocate=g.relative('e8');g.take('488bf0','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');constructor=g.relative('e8');g.take('488bcf','488937');barrier=g.relative('e8')
            allocation.update(allocate=allocate,constructor=constructor)
        g.take('4080fd03');g.branch('0f85',False)
        finder=usage('488b35');g.take('488b2f','48837e3800');g.branch('75',True,1)
        provider_class=usage('488b0d');g.take('48c744243800000000','83b9e000000000');g.branch('75',True,1)
        g.take('488b4e38','488b09');provider=g.relative('e8');g.take('4885c0');g.branch('74',False,1)
        g.take('b905000000','4c8d4c2438','4c8bc3','488bd0');at=g.at;dispatch=g.relative('e8')
        calls.append(dict(fieldName='finderData',instruction=at,target=dispatch))
        g.take('4885ed');g.branch('0f84',False);g.take('4c8b4510','4d85c0');g.branch('0f84',False)
        collectors.append(flag(g,'833d'));bitmap=g.relative('488d2d')
        g.take('488b442438','49894010');g.branch('74',True,1)
        for index,(name,slot)in enumerate((('postProcessorData',32),('validatorData',24))):
            context=usage('488b15');context['fieldName']=name;usages.append(context)
            g.take('488bcb','488b37'if index==0 else'488b3f');at=g.at;target=g.relative('e8')
            calls.append(dict(fieldName=name,instruction=at,target=target))
            g.take('4885f6'if index==0 else'4885ff');g.branch('0f84',False)
            g.take('4c8b4610'if index==0 else'4c8b4710','4d85c0');g.branch('0f84',False)
            collectors.append(flag(g,'833d'));g.take('498940'+bytes((slot,)).hex());g.branch('74',True,1)
        need('one-selector-formatter-collector',1,len(set(collectors)))
        if bytes(g.bytes.get(g.at+i,0)for i in range(1))==b'\xeb':g.jump('eb',1)
    g.take('488b5c2430','488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,staticReaderReadyFlag=static_ready,
        wrapperClassUsage=wrapper_class,wrapperAllocation=allocation,barrierTarget=barrier,
        providerClassUsage=provider_class,providerTarget=provider,dispatchTarget=dispatch,
        finderUsage=finder,listUsages=usages,sourceCalls=calls,disabledCollector=collectors[0]if collectors else None,
        fieldReferenceOffsets=[16,32,24],finderOutputLocalDisplacement=56,finderOutputBytes=8,
        existingWrapper=not new,newWrapper=new,ff=null,normalReturn=True,entryRspRestored=True,
        directStaticReaderCallExecuted=False,childGrammarsAdmitted=False)


def derive_selector_formatter(image,pins,wrapper,reader,method,body):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar,buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    need('exact-inline-selector-owner',TYPES[2],wrapper.wrapped_type)
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    offsets=scalar.reader_offsets(image,'skillSelectorFormatter')
    programs=[selector_formatter_program(body['regions'],body['pointer'],offsets,**path)for path in({},{'new':True},{'null':True})]
    constructor,=[m for m in image.metadata.methods_for(image.metadata.types[wrapper.type_definition])if image.metadata.string(m.name_index)=='.ctor']
    need('actual-selector-wrapper-constructor',image.method_pointer_va(constructor),programs[1]['wrapperAllocation']['constructor'])
    barrier=programs[2]['barrierTarget'];barrier_windows,barrier_proof,_=_fast_barrier(image,barrier)
    clones=ec.clone_facts(image,pins);typed=[]
    fields=(('finderData','Beyond.Gameplay.Core.Selector+Finder+Data',16),
        ('postProcessorData','System.Collections.Generic.List`1<Beyond.Gameplay.Core.Selector+PostProcessor+Data>',32),
        ('validatorData','System.Collections.Generic.List`1<Beyond.Gameplay.Core.Selector+Validator+Data>',24))
    need('exact-selector-field-declarations',[(n,t)for n,t,_ in fields],[(m.name,m.declared_type)for m in wrapper.members])
    for name,typename,offset in fields:need('exact-selector-field:'+name,(TYPES[2],typename,offset),ctx.field(TYPES[2]+'::'+name))
    for program in programs:
        for usage,typename in((program['wrapperClassUsage'],wrapper.name),(program['wrapperAllocation'],wrapper.name),(program['providerClassUsage'],'MemoryPack.MemoryPackFormatterProvider')):
            if usage is None:continue
            request=derive_typed_usage_context(image,usage['instruction']-base,label='skillEcReference.class')
            need('same-selected-selector-class',(1,typename),(request['tag'],request['typeName']));typed.append(request)
        if program['barrierTarget']is not None:need('same-selector-formatter-barrier',barrier,program['barrierTarget'])
        if program['ff']:continue
        need('same-selector-disabled-collector',base+barrier_proof['disabledFlagRva'],program['disabledCollector'])
        need('actual-selected-finder-provider',clones['providerTarget'],program['providerTarget'])
        need('actual-selected-finder-dispatch',clones['dispatchTarget'],program['dispatchTarget'])
        actual=derive_typed_usage_context(image,program['finderUsage']['instruction']-base,label='skillEcReference.finder')
        need('exact-finder-request',('MemoryPack.MemoryPackReader','ReadValue',[],[fields[0][1]]),
            tuple(actual[k]for k in('typeName','methodName','classArguments','methodArguments')))
        need('exact-finder-reader-definition',clones['ReadValue']['equivalentMethod'][0],actual['methodSpec'][0]);typed.append(actual)
        for usage,call,(_,typename,_)in zip(program['listUsages'],program['sourceCalls'][1:],fields[1:],strict=True):
            request=derive_typed_usage_context(image,usage['instruction']-base,label='skillEcReference.list')
            need('exact-selector-list-request',('MemoryPack.MemoryPackReader','ReadPackable',[],[typename]),
                tuple(request[k]for k in('typeName','methodName','classArguments','methodArguments')))
            need('exact-list-reader-definition',clones['ReadPackable']['equivalentMethod'][0],request['methodSpec'][0])
            need('exact-selected-list-source',base+clones['ReadPackable']['targetRva'],call['target']);typed.append(request)
    return dict(kind='complete-inline-selector-formatter',programs=programs,typedUsages=typed,
        barrierWindows=barrier_windows,barrierProof=barrier_proof,
        completeSelectedFormatterAdmitted=True,childGrammarAdmitted=False,
        directStaticReaderCallExecuted=False,actualStaticReaderMethod=[reader.index,wrapper.name,'Deserialize',image.method_pointer_va(reader)-base])


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,generated_lifecycle_sources
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);base=image.pe.image_base;inventory={w.wrapped_type:w for w in image.memorypack_wrappers.values()}
    def formatter_prover(selected,wrapper,reader,method,body):
        if wrapper.wrapped_type==TYPES[2]:return derive_selector_formatter(selected,pins,wrapper,reader,method,body)
        strict=generated_lifecycle_sources._concrete_formatter(selected,NativeReferenceContext(selected),wrapper,reader)
        return dict(completeSelectedFormatterAdmitted=True,childGrammarAdmitted=False,programs=[strict['program']],strictForwarderProof=strict)
    selected=[inventory[name]for name in TYPES];source=generated_reader_sources.derive_many(image,pins,[w.name for w in selected],formatter_prover=formatter_prover)
    rows={r.get('proof',{}).get('wrappedType'):r for r in source['owners']}
    need('three-complete-ec-callers',True,set(rows)==set(TYPES)and all(r['status']=='complete-reader-source-proved'for r in rows.values()))
    abi=reference_reader_abi(image,pins);records={}
    for wrapper in selected:
        record=rows[wrapper.wrapped_type]['proof'];pair=derive_pair(image,wrapper.wrapped_type,wrapper.name)
        def prove_selector(selected_image,selected_pair,selected_wrapper):
            method=selected_pair['composition']['methods'][1];body=owned(selected_image,base+method[3])
            proof=derive_selector_formatter(selected_image,pins,selected_wrapper,methods(selected_image,selected_wrapper)['Deserialize'],image.metadata.methods[method[0]],body)
            allocator={factory['program']['allocationTarget']for factory in record['lifecycle']['factories']}
            need('one-selector-source-allocator',1,len(allocator))
            need('same-selector-formatter-allocator',next(iter(allocator)),proof['programs'][1]['wrapperAllocation']['allocate'])
            return dict(proof,method=method,sourceWindows=body['windows'])
        adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=prove_selector if wrapper.wrapped_type==TYPES[2]else None)
        records[wrapper.wrapped_type]=dict(source=record,pair=pair,adapter=adapter,
            referenceIdentity=dict(typeName=wrapper.wrapped_type,**{key:abi[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')}),
            ordinaryOriginalReadValueSourceProved=True,childGrammarsAdmitted=False,wholeGrammarAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-ec-reference-sources.v1',nativeInputs=pins,
        status='validated-conditional-ec-reference-sources',records=records,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Three complete current concrete callers/lifecycles and own nominal ordinary reference adapter/interface/conversion; Selector formatter has an independent complete inline source.',
            conditional=__doc__+' Coherent nominal callbacks/contexts, initialized classes, normal allocation/helpers and disabled collector.',
            unresolved=['delegated child grammar and actual source joins','recursive finite selector domain','runtime selection/evaluation','enclosing owner/EOF']))))
