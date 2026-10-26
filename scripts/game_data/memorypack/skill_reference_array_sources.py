"""Independent actual typed reference-array source, with bounded loop induction.

An actual ReadArray<CLASS> request and E8 target own the complete selected
buffered null/empty/fresh-positive source. The two overloads, allocated array,
provider and slot5 callback retain one reciprocal element MVAR. A reference
slot stride never supplies an element wire grammar. Every enclosing field and
concrete child requires its own source/capability join. Ready coherent contexts,
normal typed fresh allocation, compatible selected provider/callback effects,
disabled collector and disjoint buffered storage remain conditions. Runtime
selection, malformed/refill paths and enclosing owners/EOF are unresolved.
"""
import json

from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillReferenceArraySources'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def require_reference_element(raw,definition):
    """A closed CLASS record, independently of the array's slot width."""
    need('exact-nominal-class-element',True,
        len(raw)==16 and raw[10:12]==b'\x12\x00' and int.from_bytes(raw[:8],'little')==definition)


def array_program(regions,entry,offsets,symbols,*,count,count_limit):
    """Reuse an exact byte algorithm with no borrowed nominal identity."""
    from scripts.game_data.memorypack.skill_passive_map_sources import sequence_array_program
    return sequence_array_program(regions,entry,offsets,symbols,count=count,count_limit=count_limit)


def provider_program(regions,entry,symbols):
    """Complete selected current first-probe cache hit and compatible return."""
    from scripts.game_data.memorypack.module_structure_models import provider_cache_provider
    return provider_cache_provider(regions,entry,symbols)


def induction(programs,*,count_limit):
    """Normalize the strict fresh-array loop to the shared byte certificate."""
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('bounded-array-induction',True,type(count_limit)is int and 3<=count_limit<=10000)
    witnesses=[]
    for count in range(4):
        rows=[p for p in programs if p['countWitness']==count]
        need('one-fresh-array-witness',1,len(rows));p=rows[0]
        need('complete-array-source-return',True,p['completeSelectedReturn']is True and p['entryRspRestored']is True)
        need('reference-slot-only-not-element-grammar',(8,False),(p['referenceSlotBytes'],p['elementGrammarAdmitted']))
        witnesses.append(dict(selectedBytes=p['selectedBytes'],countWitness=count,newList=True,
            elementCallbackSites=p['callbackSites']))
    result=prove_induction(witnesses,initial='33f6',increment='ffc6',comparison='3bf5',
        counter='esi',saved_count='ebp',max_count=count_limit)
    for path in result['pathProofs']:
        need('fresh-allocation-profile',True,path.pop('newList'));path['freshArray']=True
    result['allocationKind']='fresh typed reference array; no existing array/list admission'
    return result


def derive(image,pins,*,typed_request,call_target,element_type,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs
    from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
    from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
    selected_inputs(pins);need('bounded-array-count',True,type(count_limit)is int and 0<=count_limit<=10000)
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    validate_typed_usage_context(image,typed_request,label=LABEL+'.caller')
    bind_typed_read(image,typed_request,method_name='ReadArray',argument=element_type,kind=18,reference=True)
    need('actual-reference-element',False,ctx.is_value_type(element_type))
    argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    require_reference_element(raw,ctx.index.types[element_type].index)
    body=owned(image,call_target)
    def call(source,offset):
        rows=[r for r in source['rows']if int(r['va'],16)==source['pointer']+offset]
        need('one-selected-E8-row',1,len(rows));row=rows[0];raw=bytes.fromhex(row['bytes'])
        need('actual-source-direct-call',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    s={name:call(body,offset)for name,offset in dict(arrayAllocate=247,provider=373,prepare=435).items()}
    offsets=scalar.reader_offsets(image,LABEL);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[array_program(body['regions'],call_target,offsets,s,count=n,count_limit=min(count_limit,3))
        for n in range(-1,min(count_limit,3)+1)]
    certificate=induction(programs,count_limit=count_limit)if count_limit>=3 else None
    nominal=derive_reference_null(image,pins,element_type)
    symbols=ContextSymbols(image);first=symbols.context(typed_request['methodSpec'][0],is_method=True)
    second=symbols.context(first['entries'][0]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[first,second],label=LABEL+'.array')
    context=validate_read_array_context(image,[first,second],typed_request,ge,argument.type_pointer_va,
        nominal['readerContextProof']['formatterDeserializeDefinition'],fail=need)
    provider=owned(image,s['provider'])
    ps={name:call(provider,offset)for name,offset in dict(classFromType=88,hash=145,compare=238,
        backend=376,indexedType=393,assignable=409).items()}
    provider_proof=provider_program(provider['regions'],s['provider'],ps)
    need('same-reference-reader-provider-and-cache',
        (nominal['readerProgram']['providerClassCell'],nominal['readerProgram']['cacheCell']),
        (provider_proof['providerClassCell'],provider_proof['cache']['cacheGlobalCell']))
    source_provider=None
    for program in programs:
        at=program['providerUsageInstruction']
        if at is None:continue
        u=derive_typed_usage_context(image,at-base,label=LABEL+'.provider')
        need('actual-array-provider-class',(1,'MemoryPack.MemoryPackFormatterProvider'),(u['tag'],u['typeName']))
        need('same-actual-provider-class-cell',base+u['usageCellRva'],provider_proof['providerClassCell']);source_provider=u
    # The independently reviewed collector component supplies the actual entry;
    # its disabled leaf is re-proved, and every array flag cell joins that leaf.
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    model=_load('model_view_state_controller_native.json',pins);barrier_target=model['collector']['entryRva']+base
    barrier=_barrier(image,barrier_target)
    for program in programs:need('same-disabled-collector',base+barrier['result']['disabledFlagRva'],program['collectorFlag'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-reference-array-component.v1',nativeInputs=pins,
        status='validated-conditional-reference-array-component',elementType=element_type,elementValueType=False,
        closedArrayType=element_type+'[]',typedRequest=typed_request,arrayReaderMethodDefinition=typed_request['methodSpec'][0],
        arrayReaderTargetRva=call_target-base,countLimit=count_limit,collectionCounts=[-1,0],nullable=True,
        positiveCountsAdmitted=count_limit>0,elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        programs=programs,induction=certificate,ownedContexts=[first,second],ownedArrayContext=context,
        elementNominalReference=nominal,sourceWindows=body['windows'],providerWindows=provider['windows'],
        providerProgram=provider_proof,providerHelperRvas={k:v-base for k,v in ps.items()},
        actualProviderUsage=source_provider,barrier=barrier,helperRvas={k:v-base for k,v in s.items()},
        evidenceBoundary=dict(exact='Actual independently typed CLASS reference ReadArray caller, reciprocal overload/MVAR/array/provider/slot5 contexts and complete selected buffered count/array/callback/return programs with bounded unchanged-count loop induction.',
            conditional=__doc__+' The provider takes its separately byte-proved first matching cache probe and successful nonnull compatible backend result; lock/cache/hash/class/backend/predicate effects and normal ABI remain conditions.',
            unresolved=['concrete child wire grammar/callback composition','enclosing field/owner source framing','runtime selection and other provider/cache paths','physical EOF']))))
