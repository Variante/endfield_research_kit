"""Own ordinary reference-key/GameplayTag dictionary source witness.

The object-key/Tag registration supplies a machine source, not a string-key
pointer alias. The actual closed string/Tag request and every typed helper and
callback remain separate. Normal compatible allocation, comparer, insertion
and provider selection are explicit conditions; only authored order is decoded.
"""
import copy,json

from scripts.game_data.memorypack import char_tag_dictionary_programs as paths

SCHEMA='endfield.char-tag-dictionary-source.v1'
PARENT='Beyond.Gameplay.Core.CharInteractPerform.CharNpcMontageActionData'
FIELD='template2Tag'
VALUE='Beyond.Gameplay.Core.GameplayTag'
TYPE='System.Collections.Generic.Dictionary`2<string,'+VALUE+'>'
OWNER='MemoryPack.Formatters.DictionaryFormatter`2'


def need(check,condition):
    if not condition:raise ValueError('charTagDictionarySource.'+check)


def norm(value):return json.loads(json.dumps(value))


def carrier_shape(carrier,value_index):
    need('exact-own-closed-dictionary',carrier.get('name')==TYPE
        and carrier.get('definition',{}).get('name')=='System.Collections.Generic.Dictionary`2'
        and len(carrier.get('classArguments',[]))==2)
    key,value=carrier['classArguments'];kr=bytes.fromhex(key.get('rawHex',''));vr=bytes.fromhex(value.get('rawHex',''))
    need('independent-STRING14-and-Tag17',key.get('name')=='string'and len(kr)==16 and kr[10:12]==bytes((14,0))
        and value.get('name')==VALUE and len(vr)==16 and vr[10:12]==bytes((17,128))
        and type(value_index)is int and int.from_bytes(vr[:8],'little')==value_index)
    return dict(typeName=TYPE,keyType='string',valueType=VALUE,keyTypeKind=14,valueTypeKind=17,valueTypeDefinition=value_index)


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,_vtable
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,modelview_packable_sources
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context,dictionary_header_program
    from scripts.game_data.memorypack.animation_int_curve_dictionary_sources import helper_context
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);cs=ContextSymbols(image);ge=GenericEntries(image)
    need('bounded-count-domain',type(count_limit)is int and 3<=count_limit<=4096)
    validate_typed_usage_context(image,typed_request,label='charTagDictionary.parent')
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=TYPE,kind=21,reference=True)
    arg,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    carrier=cs.type(arg.type_pointer_va);identity=carrier_shape(carrier,ctx.index.types[VALUE].index)
    extent=closed_generic_reference_pointer_extent(ctx,arg.type_pointer_va)
    resources=[CONTRACTS_DIR/n for n in('npc_runtime_native.json','leveldata_npc_patrol_native.json')]
    before={p:p.read_bytes()for p in resources};core,generic=[json.loads(before[p])for p in resources]
    need('same-reviewed-ordinary-source-inputs',core.get('nativeInputs')==generic.get('nativeInputs')==pins
        and call_target==base+core['readPackable']['entryRva'])
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    td=ctx.index.types[OWNER];method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    _vtable(image,td.index,5,method.index,'charTagDictionary')
    need('own-instance-void-two',not method.flags&16 and method.slot==5 and method.parameter_count==2
        and ctx.type_name(method.return_type)=='void')
    context=cs.context(td.index);validate_generic_contexts(image,[context],label='charTagDictionary')
    context_proof=dictionary_context(image,context);slots={r['relativeSlot']:r for r in context['entries']}
    reader,output=md.parameters_for(method);rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16)
    returned=image.pe.bytes_at_va(ctx.type_pointer(output.type_index),16);declared=image.pe.bytes_at_va(ctx.type_pointer(slots[3]['index']),16)
    need('owned-Reader-and-dictionary-output-byrefs',rr[10:12]==bytes((17,32))
        and int.from_bytes(rr[:8],'little')==ctx.index.types['MemoryPack.MemoryPackReader'].index
        and returned[10:12]==bytes((21,32))and returned[:8]==declared[:8])
    witness=ge.resolve(method.index,['object',VALUE],[]);body=pointer.owned(image,witness['pointer'])
    observations=ge.observe(method.index,['string',VALUE],[])
    need('no-contradictory-actual-closed-body',all(row.get('pointer')==witness['pointer']for row in observations))
    symbols=paths.symbols(body['regions'],body['pointer'])
    programs=[paths.program(body['regions'],body['pointer'],symbols,count=n)for n in(-1,0,1,2,3)]
    counted=paths.induction(programs,count_limit=count_limit);helpers={}
    for role in('header','constructor','keyProvider','valueProvider','keyValue','Add'):
        actual=pointer.owned(image,symbols[role]);helpers[role]=dict(entryRva=symbols[role]-base,
            windows=actual['windows'],regions=[[a-base,b.hex()]for a,b in actual['regions']],rows=actual['rows'])
    offsets=scalar.reader_offsets(image,'charTagDictionary');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    def call_after(role,text):
        rows=helpers[role]['rows'];found=[control_transfer(rows[i+1])['target']for i,row in enumerate(rows[:-1])
            if row.get('text')==text and len(bytes.fromhex(rows[i+1]['bytes']))==5 and bytes.fromhex(rows[i+1]['bytes'])[:1]==b'\xe8']
        need('one-actual-helper-call:'+role+':'+text,len(set(found))==1);return found[0]
    symbols.update(keyDispatch=call_after('keyValue','mov rdx, rbp'),valueDispatch=call_after('keyValue','mov rdx, rdi'),
        initialize=call_after('constructor','mov r8, [r8+0x8]'),defaultComparer=call_after('constructor','mov rcx, [rcx+0x10]'),
        insert=call_after('Add','mov [rsp+0x20], rax'))
    for role in('keyDispatch','valueDispatch'):
        actual=pointer.owned(image,symbols[role]);helpers[role]=dict(entryRva=symbols[role]-base,
            windows=actual['windows'],regions=[[a-base,b.hex()]for a,b in actual['regions']],rows=actual['rows'])
    def raw(role):return[(base+a,bytes.fromhex(h))for a,h in helpers[role]['regions']]
    header=dictionary_header_program(raw('header'),symbols['header'],offsets)
    pair=paths.pair_program(raw('keyValue'),symbols['keyValue'],key_dispatch=symbols['keyDispatch'],value_dispatch=symbols['valueDispatch'])
    constructors=[paths.constructor_program(raw('constructor'),symbols['constructor'],symbols,positive=p,same_comparer=s)
        for p in(False,True)for s in(False,True)]
    add=paths.add_program(raw('Add'),symbols['Add'],symbols['insert'])
    pair_method=md.methods[slots[8]['methodSpec'][0]];parameters=list(md.parameters_for(pair_method));owners=[]
    need('own-static-KeyValuePair-method',image.type_name(pair_method.declaring_type)=='MemoryPack.Formatters.KeyValuePairFormatter'
        and md.string(pair_method.name_index)=='Deserialize'and bool(pair_method.flags&16)
        and ctx.type_name(pair_method.return_type)=='void'and pair_method.parameter_count==len(parameters)==5)
    for i,p in enumerate(parameters):
        raw_type=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
        if i in(0,1):
            formal=cs.type(ctx.type_pointer(p.type_index));item,=formal['classArguments']
            need('own-pair-formatter-MVAR',formal['definition']['name']=='MemoryPack.MemoryPackFormatter`1'
                and(item['parameterOwner'].get('methodIndex'),item['parameterOwner'].get('ordinal'))==(pair_method.index,i))
            owners.append(formal)
        elif i==2:need('pair-own-Reader-byref',raw_type[10:12]==bytes((17,32))
            and int.from_bytes(raw_type[:8],'little')==ctx.index.types['MemoryPack.MemoryPackReader'].index)
        else:
            need('pair-owned-MVAR-byref',raw_type[10:12]==bytes((30,32)))
            owner=method_parameter_owner(md.buf,int.from_bytes(raw_type[:8],'little'),[m.generic_container_index for m in md.methods],source='charTagDictionary.pair')
            need('pair-own-output-ordinal',(owner.get('methodIndex'),owner.get('ordinal'))==(pair_method.index,i-3));owners.append(owner)
    dictionary_helpers=helper_context(image,md.methods[slots[4]['methodSpec'][0]].declaring_type)
    need('source-resource-bookends',all(p.read_bytes()==before[p]for p in resources));_publication_gate(image,pins)
    return norm(dict(schema=SCHEMA,status='validated-conditional-char-tag-dictionary-source',nativeInputs=pins,typeName=TYPE,
        keyType='string',valueType=VALUE,packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
        dictionaryFormatterMethodDefinition=method.index,dictionaryFormatterTargetRva=witness['pointer']-base,
        sourceWitnessClassArguments=['object',VALUE],closedPointerEquivalenceProved=False,callbackSelectionConditional=True,
        keyGrammarAdmitted=False,valueGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(typedRequest=typed_request,closedCarrier=carrier,nominalIdentity=identity,referenceExtent=extent,
            referenceReader=reference,registration=witness,closedObservations=observations,context=context,contextProof=context_proof,
            readerParameterRawHex=rr.hex(),outputParameterRawHex=returned.hex(),dictionaryHelperContext=dictionary_helpers,
            readerOffsets=offsets,windows=body['windows'],regions=[[a-base,b.hex()]for a,b in body['regions']],
            programs=programs,induction=counted,symbolRvas={k:v-base for k,v in symbols.items()},helpers=helpers,
            headerProgram=header,pairProgram=pair,pairParameterOwners=owners,constructorPrograms=constructors,addProgram=add,
            barrier=_barrier(image,symbols['barrier'])),evidenceBoundary=__doc__))
